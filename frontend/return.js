"use strict";

const orderId = param("id");
let order = null;

function lineUrl(lineUuid) {
  const base = `line.html?order=${encodeURIComponent(orderId)}`;
  return lineUuid ? withParam(base, "line", lineUuid) : base;
}

// One cover thumbnail plus a "+N" badge, so a line with many photos keeps a single-row height.
function photoCover(images) {
  if (!images.length) return "—";
  const cover = imageThumb(images[0], { openable: false });
  cover.classList.add("cover");
  if (images.length > 1) cover.append(h("span", { class: "thumb-count" }, `+${images.length - 1}`));
  cover.title = `Zdjęcia: ${images.length}`;
  return cover;
}

function viewUrl(lineUuid) {
  return withParam(`line-view.html?order=${encodeURIComponent(orderId)}`, "line", lineUuid);
}

function lineRow(line) {
  const open = () => (location.href = viewUrl(line.uuid));
  return h(
    "tr",
    {
      class: "clickable",
      tabindex: "0",
      title: "Pokaż pozycję",
      onclick: open,
      // Enter on the row itself only — not when a button inside it has focus.
      onkeydown: (e) => e.key === "Enter" && e.target === e.currentTarget && open(),
    },
    h("td", { "data-label": "Referencja" }, line.sku.trade_reference),
    h("td", { "data-label": "Produkt" }, line.sku.product_name),
    h("td", { "data-label": "Param." }, line.sku.is_parametrized ? "tak" : "nie"),
    h("td", { "data-label": "Ilość", class: "num" }, line.quantity),
    h("td", { "data-label": "Nośnik" }, LABELS.carrier[line.carrier_type]),
    h("td", { "data-label": "Klasyfikacja" }, conditionBadge(line.goods_condition)),
    h("td", { "data-label": "Opis uszkodzenia" }, line.damage_description || "—"),
    h("td", { "data-label": "Uwagi" }, line.remarks || "—"),
    h(
      "td",
      { "data-label": "Zdjęcia" },
      photoCover(line.images),
    ),
    h(
      "td",
      // The buttons act on their own; the click must not also open the line.
      { class: "actions-cell", onclick: (e) => e.stopPropagation() },
      h("a", { class: "btn secondary small", href: lineUrl(line.uuid) }, "Edytuj"),
      " ",
      h("button", { class: "danger small", onclick: (e) => deleteLine(line, e.currentTarget) }, "Usuń"),
    ),
  );
}

function render() {
  const title = `Zwrot ${orNoNumber(order.bo_wms_number)} / ${orNoNumber(order.tempo_number)}`;
  $("#title").textContent = title;
  document.title = `${title} — Zwroty e-com`;
  $("#s-date").textContent = formatDate(order.return_date);
  $("#s-bo").textContent = orNoNumber(order.bo_wms_number);
  $("#s-tempo").textContent = orNoNumber(order.tempo_number);
  $("#s-lines").textContent = order.lines.length;
  $("#s-pieces").textContent = order.lines.reduce((sum, line) => sum + line.quantity, 0);

  $("#lines").replaceChildren(
    ...(order.lines.length
      ? order.lines.map(lineRow)
      : [h("tr", {}, h("td", { colspan: "10", class: "empty" }, "Brak pozycji — dodaj pierwszą."))]),
  );
}

async function deleteLine(line, button) {
  if (!confirm(`Usunąć pozycję ${line.sku.trade_reference}?`)) return;
  await withBusy(button, async () => {
    try {
      order = await api(`/returns/${orderId}/lines/${line.uuid}`, { method: "DELETE" });
      render();
      toast("Pozycja usunięta");
    } catch (err) {
      showError(err);
    }
  });
}

$("#delete-order").addEventListener("click", async (event) => {
  const count = order.lines.length;
  if (!confirm(count ? `Usunąć zwrot razem z ${count} pozycjami?` : "Usunąć ten zwrot?")) return;
  await withBusy(event.currentTarget, async () => {
    try {
      await api(`/returns/${orderId}`, { method: "DELETE" });
      location.replace("returns.html");
    } catch (err) {
      showError(err);
    }
  });
});

async function init() {
  if (!orderId) {
    location.replace("returns.html");
    return;
  }
  await requireUser();
  $("#add-line").href = lineUrl();
  $("#edit-header").href = `return-form.html?id=${encodeURIComponent(orderId)}`;
  try {
    order = await api(`/returns/${orderId}`);
  } catch (err) {
    showError(err);
    if (err.status === 404 || err.status === 422) setTimeout(() => location.replace("returns.html"), 1500);
    return;
  }
  render();
}

init().catch(showError);
