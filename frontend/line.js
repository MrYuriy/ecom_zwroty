"use strict";

// Receive items into a return: scan → fill the line (and photos) → back to scanning.
// ?line=<uuid> edits an existing line; ?sku=<id> arrives from the new-product form.
const orderId = param("order");
const lineId = param("line");
const orderUrl = `return.html?id=${encodeURIComponent(orderId || "")}`;

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_IMAGE_MB = 15;

const state = { order: null, sku: null, line: null, pending: [] };

const scanStep = $("#scan-step");
const lineStep = $("#line-step");
const scanInput = $("#scan-input");
const form = $("#line-form");
const photoInputs = [$("#camera-input"), $("#gallery-input")];

function lineEditUrl(uuid) {
  return withParam(`line.html?order=${encodeURIComponent(orderId)}`, "line", uuid);
}

// ---------- steps ----------
function showScanStep() {
  state.sku = null;
  lineStep.classList.add("hidden");
  $("#not-found").classList.add("hidden");
  scanStep.classList.remove("hidden");
  scanInput.value = "";
  scanInput.focus();
}

function showLineStep(sku) {
  state.sku = sku;
  scanStep.classList.add("hidden");
  $("#line-sku").replaceChildren(
    h("strong", {}, sku.trade_reference),
    h("span", {}, sku.product_name),
    sku.ean ? h("span", { class: "muted" }, `EAN ${sku.ean}`) : null,
    h(
      "span",
      { class: `badge ${sku.is_parametrized ? "success" : "neutral"}` },
      sku.is_parametrized ? "sparametryzowany" : "niesparametryzowany",
    ),
  );
  lineStep.classList.remove("hidden");
  form.quantity.focus();
  form.quantity.select();
}

// Carrier and condition carry over: several items from one parcel usually share them.
function clearLineFields() {
  form.quantity.value = 1;
  form.damage_description.value = "";
  form.remarks.value = "";
  clearPending();
}

function renderOrderInfo() {
  const lines = state.order.lines.length;
  $("#session-info").textContent = lines
    ? `Pozycji w zwrocie: ${lines}. Zeskanuj kolejny produkt lub kliknij „Zakończ”.`
    : "";
}

// ---------- photos ----------
function renderExistingImages() {
  const images = state.line ? state.line.images : [];
  $("#existing-images").replaceChildren(...images.map((image) => imageThumb(image, { onDelete: () => deleteImage(image) })));
}

function renderPending() {
  $("#pending-images").replaceChildren(
    ...state.pending.map((item, index) =>
      h(
        "div",
        { class: "thumb" },
        h("img", { src: item.url, alt: item.file.name }),
        h(
          "button",
          {
            type: "button",
            class: "thumb-delete",
            title: "Nie dodawaj tego zdjęcia",
            onclick: () => {
              URL.revokeObjectURL(item.url);
              state.pending.splice(index, 1);
              renderPending();
            },
          },
          "×",
        ),
      ),
    ),
  );
  $("#pending-note").textContent = state.pending.length
    ? `Nowe zdjęcia (${state.pending.length}) zostaną zapisane razem z pozycją.`
    : "";
}

function clearPending() {
  for (const item of state.pending) URL.revokeObjectURL(item.url);
  state.pending = [];
  for (const input of photoInputs) input.value = "";
  renderPending();
}

function addPhotos(input) {
  for (const file of input.files) {
    // Early feedback only; the server checks the real content and size again.
    if (!IMAGE_TYPES.includes(file.type)) {
      toast(`${file.name}: dozwolone są tylko JPG, PNG i WebP`, "error");
      continue;
    }
    if (file.size > MAX_IMAGE_MB * 1024 * 1024) {
      toast(`${file.name}: plik większy niż ${MAX_IMAGE_MB} MB`, "error");
      continue;
    }
    state.pending.push({ file, url: URL.createObjectURL(file) });
  }
  input.value = "";
  renderPending();
}

for (const input of photoInputs) input.addEventListener("change", () => addPhotos(input));

async function uploadPending(lineUuid) {
  if (!state.pending.length) return null;
  const data = new FormData();
  for (const item of state.pending) data.append("files", item.file, item.file.name);
  const order = await api(`/returns/${orderId}/lines/${lineUuid}/images`, { method: "POST", body: data });
  clearPending();
  return order;
}

async function deleteImage(image) {
  if (!confirm("Usunąć to zdjęcie?")) return;
  try {
    state.order = await api(`/returns/${orderId}/lines/${state.line.uuid}/images/${image.uuid}`, {
      method: "DELETE",
    });
    state.line = state.order.lines.find((l) => l.uuid === state.line.uuid);
    renderExistingImages();
    toast("Zdjęcie usunięte");
  } catch (err) {
    showError(err);
  }
}

// ---------- scanning ----------
async function findSku(code) {
  try {
    return await api(`/skus/by-ean/${encodeURIComponent(code)}`);
  } catch (err) {
    if (err.status !== 404) throw err;
  }
  // Not every product has an EAN — accept an exact trade reference as well.
  const page = await api("/skus", { query: { q: code, limit: 50 } });
  return page.items.find((sku) => sku.trade_reference === code) || null;
}

function showNotFound(code) {
  // A scanned code is almost always an EAN; a typed one may be the trade reference.
  const field = /^\d{8,14}$/.test(code) ? "ean" : "ref";
  const back = `line.html?order=${encodeURIComponent(orderId)}`;
  $("#not-found-text").textContent = `Nie znaleziono produktu „${code}”.`;
  $("#create-sku").href = withParam(withParam("sku-form.html", field, code), "back", back);
  $("#not-found").classList.remove("hidden");
  $("#create-sku").focus();
}

// Handle Enter explicitly: some scanners send only a keydown, which never triggers the form's own submit.
scanInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    $("#scan-form").requestSubmit();
  }
});

$("#scan-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const code = scanInput.value.trim();
  if (!code) return;
  $("#not-found").classList.add("hidden");
  await withBusy(event.currentTarget.querySelector("button"), async () => {
    try {
      const sku = await findSku(code);
      if (sku) {
        clearLineFields();
        showLineStep(sku);
      } else {
        showNotFound(code);
      }
    } catch (err) {
      showError(err);
    }
  });
});

// ---------- saving ----------
function lineBody() {
  return {
    quantity: Number(form.quantity.value),
    carrier_type: form.querySelector("input[name=carrier_type]:checked").value,
    goods_condition: form.querySelector("input[name=goods_condition]:checked").value,
    damage_description: nullIfBlank(form.damage_description.value),
    remarks: nullIfBlank(form.remarks.value),
  };
}

async function saveEdit(body) {
  await api(`/returns/${orderId}/lines/${state.line.uuid}`, { method: "PATCH", body });
  await uploadPending(state.line.uuid);
  location.href = orderUrl;
}

async function saveNew(body) {
  const before = new Set(state.order.lines.map((l) => l.uuid));
  state.order = await api(`/returns/${orderId}/lines`, { method: "POST", body: { ...body, sku_id: state.sku.id } });
  const created = state.order.lines.find((l) => !before.has(l.uuid));
  try {
    state.order = (await uploadPending(created.uuid)) || state.order;
  } catch (err) {
    // The line itself is saved; send the operator to it so the photos can be retried there.
    showError(err);
    setTimeout(() => (location.href = lineEditUrl(created.uuid)), 1500);
    return;
  }
  renderOrderInfo();
  toast(`Dodano: ${state.sku.trade_reference}`);
  showScanStep();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = lineBody();
  if (!Number.isInteger(body.quantity) || body.quantity < 1) {
    toast("Ilość musi być liczbą całkowitą ≥ 1", "error");
    form.quantity.focus();
    return;
  }
  await withBusy($("#line-submit"), async () => {
    try {
      await (state.line ? saveEdit(body) : saveNew(body));
    } catch (err) {
      showError(err);
    }
  });
});

$("#line-cancel").addEventListener("click", () => {
  if (state.line) {
    location.href = orderUrl;
  } else {
    clearPending();
    showScanStep();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !state.line && !lineStep.classList.contains("hidden")) {
    clearPending();
    showScanStep();
  }
});

// ---------- init ----------
function fillFromLine(line) {
  form.quantity.value = line.quantity;
  form.querySelector(`input[name=carrier_type][value=${line.carrier_type}]`).checked = true;
  form.querySelector(`input[name=goods_condition][value=${line.goods_condition}]`).checked = true;
  form.damage_description.value = line.damage_description || "";
  form.remarks.value = line.remarks || "";
}

async function init() {
  if (!orderId) {
    location.replace("returns.html");
    return;
  }
  await requireUser();
  $("#back").href = orderUrl;
  $("#finish").href = orderUrl;

  try {
    state.order = await api(`/returns/${orderId}`);
  } catch (err) {
    showError(err);
    if (err.status === 404 || err.status === 422) setTimeout(() => location.replace("returns.html"), 1500);
    return;
  }
  $("#order-ref").textContent =
    `Zwrot ${orNoNumber(state.order.bo_wms_number)} / ${orNoNumber(state.order.tempo_number)} · ` +
    formatDate(state.order.return_date);
  renderOrderInfo();

  if (lineId) {
    const line = state.order.lines.find((l) => l.uuid === lineId);
    if (!line) {
      location.replace(orderUrl);
      return;
    }
    state.line = line;
    $("#title").textContent = "Edycja pozycji";
    $("#line-submit").textContent = "Zapisz";
    $("#finish").classList.add("hidden");
    $("#next-order").classList.add("hidden");
    document.title = "Edycja pozycji — Zwroty e-com";
    fillFromLine(line);
    renderExistingImages();
    showLineStep(line.sku);
    return;
  }

  const skuId = param("sku");
  if (skuId) {
    // Back from creating a product: continue with it, and drop ?sku so a reload doesn't repeat this.
    history.replaceState(null, "", `line.html?order=${encodeURIComponent(orderId)}`);
    try {
      showLineStep(await api(`/skus/${encodeURIComponent(skuId)}`));
      return;
    } catch (err) {
      showError(err);
    }
  }
  showScanStep();
}

init().catch(showError);
