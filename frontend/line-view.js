"use strict";

// Read-only view of one line with its photos at full size.
const orderId = param("order");
const lineId = param("line");
const orderUrl = `return.html?id=${encodeURIComponent(orderId || "")}`;

const state = { line: null, index: 0 };

function setText(id, value) {
  $(id).textContent = value === null || value === undefined || value === "" ? "—" : value;
}

function renderDetails(order, line) {
  $("#title").textContent = `${line.sku.trade_reference} — ${line.sku.product_name}`;
  document.title = `${line.sku.trade_reference} — Zwroty e-com`;
  $("#order-ref").textContent =
    `Zwrot ${orNoNumber(order.bo_wms_number)} / ${orNoNumber(order.tempo_number)} · ${formatDate(order.return_date)}`;
  setText("#v-reference", line.sku.trade_reference);
  setText("#v-product", line.sku.product_name);
  setText("#v-ean", line.sku.ean);
  setText("#v-param", line.sku.is_parametrized ? "tak" : "nie");
  setText("#v-quantity", line.quantity);
  setText("#v-carrier", LABELS.carrier[line.carrier_type]);
  $("#v-condition").replaceChildren(conditionBadge(line.goods_condition));
  setText("#v-damage", line.damage_description);
  setText("#v-remarks", line.remarks);
}

async function show(index) {
  const images = state.line.images;
  state.index = (index + images.length) % images.length;
  const image = images[state.index];
  $("#viewer-counter").textContent = images.length > 1 ? `${state.index + 1} / ${images.length}` : "";
  for (const [i, thumb] of [...$("#viewer-strip").children].entries()) {
    thumb.classList.toggle("selected", i === state.index);
  }
  try {
    const url = await imageObjectUrl(image.uuid);
    // A quick click on another thumbnail may have moved on while this one loaded.
    if (images[state.index] !== image) return;
    $("#viewer-img").src = url;
    $("#open-original").href = url;
  } catch (err) {
    showError(err);
  }
}

function renderPhotos() {
  const images = state.line.images;
  const hasPhotos = images.length > 0;
  $("#no-photos").classList.toggle("hidden", hasPhotos);
  $("#viewer").classList.toggle("hidden", !hasPhotos);
  $("#open-original").classList.toggle("hidden", !hasPhotos);
  // One photo needs no picker.
  $("#viewer-strip").replaceChildren(
    ...(images.length > 1
      ? images.map((image, i) =>
          h(
            "button",
            { type: "button", class: "strip-item", title: `Zdjęcie ${i + 1}`, onclick: () => show(i) },
            imageThumb(image, { openable: false }),
          ),
        )
      : []),
  );
  if (hasPhotos) show(0);
}

document.addEventListener("keydown", (event) => {
  if (!state.line || state.line.images.length < 2) return;
  if (event.key === "ArrowRight") show(state.index + 1);
  if (event.key === "ArrowLeft") show(state.index - 1);
});

async function init() {
  if (!orderId || !lineId) {
    location.replace("returns.html");
    return;
  }
  await requireUser();
  $("#back").href = orderUrl;
  $("#edit-line").href = withParam(`line.html?order=${encodeURIComponent(orderId)}`, "line", lineId);

  let order;
  try {
    order = await api(`/returns/${orderId}`);
  } catch (err) {
    showError(err);
    if (err.status === 404 || err.status === 422) setTimeout(() => location.replace("returns.html"), 1500);
    return;
  }
  state.line = order.lines.find((l) => l.uuid === lineId);
  if (!state.line) {
    location.replace(orderUrl);
    return;
  }
  renderDetails(order, state.line);
  renderPhotos();
}

init().catch(showError);
