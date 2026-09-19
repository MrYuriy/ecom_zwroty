"use strict";

const PAGE_SIZE = 50;
const state = { page: 1, q: "" };

function orderRow(order) {
  return h(
    "tr",
    {},
    h("td", { "data-label": "Numer BO/WMS" }, order.bo_wms_number),
    h("td", { "data-label": "Numer Tempo" }, orNoNumber(order.tempo_number)),
    h("td", { "data-label": "Dodano" }, formatDateTime(order.created_at)),
  );
}

async function loadOrders() {
  try {
    const page = await api("/wms-orders", { query: { q: state.q, page: state.page, limit: PAGE_SIZE } });
    $("#orders").replaceChildren(
      ...(page.items.length
        ? page.items.map(orderRow)
        : [h("tr", {}, h("td", { colspan: "3", class: "empty" }, "Brak zamówień."))]),
    );
    renderPager($("#pager"), page, (next) => {
      state.page = next;
      loadOrders();
    });
  } catch (err) {
    showError(err);
  }
}

$("#search").addEventListener("submit", (event) => {
  event.preventDefault();
  state.q = event.currentTarget.q.value.trim();
  state.page = 1;
  loadOrders();
});

$("#sync").addEventListener("click", async (event) => {
  await withBusy(event.currentTarget, async () => {
    try {
      const result = await api("/wms-orders/sync", { method: "POST" });
      toast(`Arkusz: ${result.rows} zamówień, nowych: ${result.added}`);
      if (result.added) {
        state.page = 1;
        loadOrders();
      }
    } catch (err) {
      showError(err);
    }
  });
});

requireUser({ adminOnly: true }).then(loadOrders).catch(showError);
