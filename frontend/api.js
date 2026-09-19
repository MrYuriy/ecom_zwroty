"use strict";

// Shared by every page: token, authenticated fetch, top bar, labels and DOM helpers.
const API_BASE = "/api";
const TOKEN_KEY = "zwroty_access";

const TOKEN = {
  get() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(value) {
    localStorage.setItem(TOKEN_KEY, value);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
};

// ---------- labels (API values → Polish UI text) ----------
const LABELS = {
  carrier: { PARCEL: "paczka", PALLET: "paleta" },
  condition: { DAMAGED: "uszkodzony", FULL_VALUE: "pełnowartościowy" },
  role: { OPERATOR: "Operator", ADMIN: "Administrator" },
  status: { OPEN: "w trakcie", CLOSED: "zamknięty" },
};

const NO_NUMBER = "brak";

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function goToLogin() {
  TOKEN.clear();
  const next = encodeURIComponent(location.pathname + location.search);
  location.replace(`/app/?next=${next}`);
}

function errorMessage(status, body) {
  const detail = body && body.detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: point at the fields, not at pydantic internals.
    const fields = detail.map((d) => (d.loc || []).slice(-1)[0]).filter(Boolean);
    return fields.length ? `Nieprawidłowe dane: ${fields.join(", ")}` : "Nieprawidłowe dane";
  }
  if (status === 404) return detail ? `Nie znaleziono (${detail})` : "Nie znaleziono";
  if (status === 409) return detail ? `Już istnieje (${detail})` : "Już istnieje";
  if (status === 403) return "Brak uprawnień";
  if (status >= 500) return "Błąd serwera — spróbuj ponownie";
  return detail || `Błąd ${status}`;
}

async function api(path, { method = "GET", body, query } = {}) {
  let url = `${API_BASE}${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") params.set(key, value);
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }
  const headers = {};
  const isForm = body instanceof FormData;
  // FormData sets its own multipart Content-Type (with the boundary); JSON needs it spelled out.
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  const token = TOKEN.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let resp;
  try {
    const payload = body === undefined || isForm ? body : JSON.stringify(body);
    resp = await fetch(url, { method, headers, body: payload });
  } catch {
    throw new ApiError(0, "Brak połączenia z serwerem");
  }

  // The shift token expired or the account was deactivated.
  if (resp.status === 401 && path !== "/auth/login") {
    goToLogin();
    throw new ApiError(401, "Sesja wygasła");
  }
  if (resp.status === 204) return null;

  const data = await resp.json().catch(() => null);
  if (!resp.ok) throw new ApiError(resp.status, errorMessage(resp.status, data));
  return data;
}

// ---------- DOM ----------
// Builds elements with textContent only, so user data can never become markup.
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child === undefined || child === null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

function $(selector, root = document) {
  return root.querySelector(selector);
}

function param(name) {
  return new URLSearchParams(location.search).get(name);
}

// A "back" link taken from the URL may only point at another cabinet page, never at another site.
const CABINET_PAGE = /^[a-z0-9-]+\.html(\?[^#]*)?$/;

function safeBack(url, fallback) {
  return url && CABINET_PAGE.test(url) ? url : fallback;
}

function withParam(url, name, value) {
  return `${url}${url.includes("?") ? "&" : "?"}${name}=${encodeURIComponent(value)}`;
}

let toastTimer = null;

function toast(message, kind = "info") {
  let el = $("#toast");
  if (!el) {
    el = h("div", { id: "toast", role: "status", "aria-live": "polite" });
    document.body.append(el);
  }
  el.textContent = message;
  el.className = kind === "error" ? "error" : "";
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), kind === "error" ? 5000 : 2500);
}

function showError(err) {
  toast(err instanceof ApiError ? err.message : "Nieoczekiwany błąd", "error");
  if (!(err instanceof ApiError)) console.error(err);
}

// Disable a button while an async action runs, so a double click can't submit twice.
async function withBusy(button, fn) {
  if (button) button.disabled = true;
  try {
    return await fn();
  } finally {
    if (button) button.disabled = false;
  }
}

// ---------- line images ----------
// <img> can't send the bearer token, so images are fetched with it and shown from blob URLs.
const imageUrls = new Map();

function imageObjectUrl(uuid) {
  if (!imageUrls.has(uuid)) {
    const promise = fetch(`${API_BASE}/images/${uuid}`, { headers: { Authorization: `Bearer ${TOKEN.get()}` } })
      .then((resp) => {
        if (!resp.ok) throw new ApiError(resp.status, "Nie udało się wczytać zdjęcia");
        return resp.blob();
      })
      .then((blob) => URL.createObjectURL(blob));
    promise.catch(() => imageUrls.delete(uuid));
    imageUrls.set(uuid, promise);
  }
  return imageUrls.get(uuid);
}

// A photo thumbnail. `openable` makes it a link to the full photo in a new tab;
// without it the click is left to the surrounding element (e.g. a clickable table row).
function imageThumb(image, { onDelete = null, openable = true } = {}) {
  const img = h("img", { alt: "Zdjęcie pozycji", loading: "lazy" });
  const link = openable
    ? h(
        "a",
        {
          href: "#",
          class: "thumb-link",
          title: "Otwórz zdjęcie",
          onclick: (e) => link.getAttribute("href") === "#" && e.preventDefault(),
        },
        img,
      )
    : null;
  imageObjectUrl(image.uuid)
    .then((url) => {
      img.src = url;
      if (link) {
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener";
      }
    })
    .catch(() => img.replaceWith(h("span", { class: "thumb-missing" }, "brak")));
  return h(
    "div",
    { class: "thumb" },
    link || img,
    onDelete ? h("button", { type: "button", class: "thumb-delete", title: "Usuń zdjęcie", onclick: onDelete }, "×") : null,
  );
}

// ---------- formatting ----------
function orNoNumber(value) {
  return value || NO_NUMBER;
}

function formatDate(iso) {
  return iso ? iso.slice(0, 10) : "";
}

// "2026-09-19T17:47:42.99" → "2026-09-19 17:47" (server timestamps are shown as stored).
function formatDateTime(iso) {
  return iso ? iso.slice(0, 16).replace("T", " ") : "";
}

function todayIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function statusBadge(status) {
  return h("span", { class: `badge ${status === "CLOSED" ? "neutral" : "warning"}` }, LABELS.status[status]);
}

function conditionBadge(condition) {
  return h("span", { class: `badge ${condition === "DAMAGED" ? "danger" : "success"}` }, LABELS.condition[condition]);
}

// Map "" to null so optional text fields are cleared instead of stored as empty strings.
function nullIfBlank(value) {
  const trimmed = (value || "").trim();
  return trimmed === "" ? null : trimmed;
}

function renderPager(container, page, onPage) {
  container.replaceChildren();
  const pages = Math.max(1, Math.ceil(page.total / page.limit));
  container.append(
    h("span", {}, `Razem: ${page.total}`),
    h(
      "div",
      { class: "actions" },
      h("button", { class: "secondary small", disabled: page.page <= 1, onclick: () => onPage(page.page - 1) }, "‹ Poprzednia"),
      h("span", {}, `${page.page} / ${pages}`),
      h("button", { class: "secondary small", disabled: page.page >= pages, onclick: () => onPage(page.page + 1) }, "Następna ›"),
    ),
  );
}

// ---------- session + top bar ----------
let currentUser = null;

async function requireUser({ adminOnly = false } = {}) {
  if (!TOKEN.get()) {
    goToLogin();
    return new Promise(() => {});
  }
  currentUser = await api("/auth/me");
  if (adminOnly && currentUser.role !== "ADMIN") {
    location.replace("/app/returns.html");
    return new Promise(() => {});
  }
  renderTopbar();
  return currentUser;
}

// Which top-bar section each page belongs to.
const SECTIONS = {
  "returns.html": ["returns.html", "return.html", "return-form.html", "line.html", "line-view.html"],
  "skus.html": ["skus.html", "sku-form.html"],
  "users.html": ["users.html", "user-form.html"],
  "wms-orders.html": ["wms-orders.html"],
};

function renderTopbar() {
  const bar = $("#topbar");
  if (!bar) return;
  const here = location.pathname.split("/").pop();
  const link = (href, text) => h("a", { href, class: SECTIONS[href].includes(here) ? "active" : null }, text);

  bar.replaceChildren(
    h("a", { href: "returns.html", class: "brand" }, "Zwroty e-com"),
    h(
      "nav",
      {},
      link("returns.html", "Zwroty"),
      link("skus.html", "Produkty (SKU)"),
      currentUser.role === "ADMIN" ? link("wms-orders.html", "Zamówienia WMS") : null,
      currentUser.role === "ADMIN" ? link("users.html", "Użytkownicy") : null,
    ),
    h(
      "div",
      { class: "user" },
      h("span", {}, currentUser.full_name),
      h("button", { class: "secondary small", onclick: () => goToLogin() }, "Wyloguj"),
    ),
  );
}
