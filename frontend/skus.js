"use strict";

const PAGE_SIZE = 50;
const state = { page: 1, q: "" };

function skuRow(sku) {
  return h(
    "tr",
    {},
    h("td", { "data-label": "Referencja" }, sku.trade_reference),
    h("td", { "data-label": "EAN", title: sku.eans.join("\n") }, eanSummary(sku.eans)),
    h("td", { "data-label": "Nazwa" }, sku.product_name),
    h("td", { "data-label": "Sparametryzowany" }, sku.is_parametrized ? "tak" : "nie"),
    h(
      "td",
      { class: "actions-cell" },
      h("a", { class: "btn secondary small", href: `sku-form.html?id=${encodeURIComponent(sku.id)}` }, "Edytuj"),
      " ",
      h("button", { class: "danger small", onclick: (e) => deleteSku(sku, e.currentTarget) }, "Usuń"),
    ),
  );
}

async function loadSkus() {
  try {
    const page = await api("/skus", { query: { q: state.q, page: state.page, limit: PAGE_SIZE } });
    $("#skus").replaceChildren(
      ...(page.items.length
        ? page.items.map(skuRow)
        : [h("tr", {}, h("td", { colspan: "5", class: "empty" }, "Brak produktów."))]),
    );
    renderPager($("#pager"), page, (next) => {
      state.page = next;
      loadSkus();
    });
  } catch (err) {
    showError(err);
  }
}

// ---------- delete ----------
function hideUsage() {
  $("#usage").classList.add("hidden");
  $("#usage").replaceChildren();
}

function usageItem(order) {
  const text =
    `${formatDate(order.return_date)} · BO/WMS ${orNoNumber(order.bo_wms_number)} · ` +
    `Tempo ${orNoNumber(order.tempo_number)} · pozycji: ${order.lines} · ${LABELS.status[order.status]}`;
  return h("li", {}, h("a", { href: `return.html?id=${encodeURIComponent(order.uuid)}` }, text));
}

function showUsage(sku, orders) {
  const box = $("#usage");
  box.replaceChildren(
    h(
      "p",
      {},
      h("strong", {}, `Nie można usunąć produktu ${sku.trade_reference}`),
      ` — jest użyty w zwrotach (${orders.length}). Usuń go najpierw z tych zwrotów:`,
    ),
    h("ul", {}, orders.map(usageItem)),
    h("button", { type: "button", class: "secondary small", onclick: hideUsage }, "Zamknij"),
  );
  box.classList.remove("hidden");
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function deleteSku(sku, button) {
  hideUsage();
  await withBusy(button, async () => {
    try {
      const orders = await api(`/skus/${sku.id}/usage`);
      if (orders.length) {
        showUsage(sku, orders);
        return;
      }
      if (!confirm(`Usunąć produkt ${sku.trade_reference} (${sku.product_name}) razem z jego kodami EAN?`)) return;
      await api(`/skus/${sku.id}`, { method: "DELETE" });
      toast("Produkt usunięty");
      loadSkus();
    } catch (err) {
      // Someone added it to a return in the meantime: show where.
      if (err.status === 409) {
        showUsage(sku, await api(`/skus/${sku.id}/usage`).catch(() => []));
        return;
      }
      showError(err);
    }
  });
}

$("#search").addEventListener("submit", (event) => {
  event.preventDefault();
  state.q = event.currentTarget.q.value.trim();
  state.page = 1;
  loadSkus();
});

// ---------- import (admin) ----------
let importTimer = null;

function describeImport(job) {
  const when = formatDateTime(job.finished_at || job.created_at);
  if (job.status === "PENDING" || job.status === "RUNNING") {
    const stage = job.stage || "w kolejce";
    const read = job.rows_read ? `, wierszy: ${job.rows_read}` : "";
    return { text: `Import „${job.file_name}” trwa (${stage}${read})…`, kind: "" };
  }
  if (job.status === "FAILED") {
    return { text: `Import „${job.file_name}” nie powiódł się (${when}): ${job.error}`, kind: "warn" };
  }
  return {
    text:
      `Ostatni import „${job.file_name}” (${when}): wierszy ${job.rows_read}, pominięto ${job.rows_skipped}; ` +
      `produkty nowe ${job.skus_created}, zmienione ${job.skus_updated}; ` +
      `kody nowe ${job.eans_created}, przeniesione ${job.eans_reassigned}.`,
    kind: "ok",
  };
}

async function refreshImport() {
  clearTimeout(importTimer);
  let job;
  try {
    job = await api("/sku-imports/latest");
  } catch (err) {
    showError(err);
    return;
  }
  const status = $("#import-status");
  if (!job) {
    status.textContent = "Nie było jeszcze importu.";
    status.className = "field-hint";
    return;
  }
  const { text, kind } = describeImport(job);
  status.textContent = text;
  status.className = `field-hint ${kind}`;
  const running = job.status === "PENDING" || job.status === "RUNNING";
  $("#import-submit").disabled = running;
  if (running) {
    importTimer = setTimeout(refreshImport, 2000);
  } else if (state.importing) {
    state.importing = false;
    loadSkus();
  }
}

$("#import-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = $("#import-file").files[0];
  if (!file) {
    toast("Wybierz plik", "error");
    return;
  }
  const data = new FormData();
  data.append("file", file, file.name);
  const status = $("#import-status");
  status.textContent = `Wysyłanie „${file.name}” (${(file.size / 1048576).toFixed(1)} MB)…`;
  status.className = "field-hint";
  await withBusy($("#import-submit"), async () => {
    try {
      await api("/sku-imports", { method: "POST", body: data });
      state.importing = true;
      $("#import-file").value = "";
      await refreshImport();
    } catch (err) {
      showError(err);
      status.textContent = "";
    }
  });
});

requireUser()
  .then((user) => {
    if (user.role === "ADMIN") {
      $("#import-card").classList.remove("hidden");
      refreshImport();
    }
    return loadSkus();
  })
  .catch(showError);
