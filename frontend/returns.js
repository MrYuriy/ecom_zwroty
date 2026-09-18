"use strict";

const PAGE_SIZE = 25;
const state = { page: 1, filters: {} };

function openOrder(uuid) {
  location.href = `return.html?id=${encodeURIComponent(uuid)}`;
}

function orderRow(order) {
  const pieces = order.lines.reduce((sum, line) => sum + line.quantity, 0);
  const damaged = order.lines.filter((line) => line.goods_condition === "DAMAGED").length;
  return h(
    "tr",
    {
      class: "clickable",
      tabindex: "0",
      onclick: () => openOrder(order.uuid),
      onkeydown: (e) => e.key === "Enter" && openOrder(order.uuid),
    },
    h("td", { "data-label": "Data zwrotu" }, formatDate(order.return_date)),
    h("td", { "data-label": "Numer BO/WMS" }, orNoNumber(order.bo_wms_number)),
    h("td", { "data-label": "Numer Tempo" }, orNoNumber(order.tempo_number)),
    h("td", { "data-label": "Pozycje", class: "num" }, order.lines.length),
    h("td", { "data-label": "Sztuk", class: "num" }, pieces),
    h("td", { "data-label": "Uszkodzone", class: "num" }, damaged ? h("span", { class: "badge danger" }, damaged) : "—"),
  );
}

async function loadOrders() {
  try {
    const page = await api("/returns", { query: { ...state.filters, page: state.page, limit: PAGE_SIZE } });
    $("#orders").replaceChildren(
      ...(page.items.length
        ? page.items.map(orderRow)
        : [h("tr", {}, h("td", { colspan: "6", class: "empty" }, "Brak zwrotów dla wybranych filtrów."))]),
    );
    renderPager($("#pager"), page, (next) => {
      state.page = next;
      loadOrders();
    });
  } catch (err) {
    showError(err);
  }
}

$("#filters").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  state.filters = {
    number: form.number.value.trim(),
    date_from: form.date_from.value,
    date_to: form.date_to.value,
  };
  state.page = 1;
  loadOrders();
});

$("#filters").addEventListener("reset", () => {
  state.filters = {};
  state.page = 1;
  // Let the browser clear the inputs first.
  setTimeout(loadOrders);
});

requireUser().then(loadOrders).catch(showError);
