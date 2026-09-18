"use strict";

const PAGE_SIZE = 50;
const state = { page: 1, q: "" };

function skuRow(sku) {
  return h(
    "tr",
    {},
    h("td", { "data-label": "Referencja" }, sku.trade_reference),
    h("td", { "data-label": "EAN" }, sku.ean || "—"),
    h("td", { "data-label": "Nazwa" }, sku.product_name),
    h("td", { "data-label": "Sparametryzowany" }, sku.is_parametrized ? "tak" : "nie"),
    h(
      "td",
      { class: "actions-cell" },
      h("a", { class: "btn secondary small", href: `sku-form.html?id=${encodeURIComponent(sku.id)}` }, "Edytuj"),
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

$("#search").addEventListener("submit", (event) => {
  event.preventDefault();
  state.q = event.currentTarget.q.value.trim();
  state.page = 1;
  loadSkus();
});

requireUser().then(loadSkus).catch(showError);
