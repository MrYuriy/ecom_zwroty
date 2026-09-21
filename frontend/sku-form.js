"use strict";

// Create (?ean= / ?ref= prefill) or edit (?id=) a product.
// ?back=<page> returns there afterwards with &sku=<id>, e.g. to continue receiving an item.
const skuId = param("id");
const back = safeBack(param("back"), null);
const form = $("#sku-form");

async function init() {
  await requireUser();
  const cancelUrl = back || "skus.html";
  $("#cancel").href = cancelUrl;
  if (back) {
    $("#back").href = back;
    $("#back").textContent = "‹ Wróć do przyjęcia";
  }

  if (skuId) {
    $("#title").textContent = "Edycja produktu";
    document.title = "Edycja produktu — Zwroty e-com";
    const sku = await api(`/skus/${encodeURIComponent(skuId)}`);
    form.trade_reference.value = sku.trade_reference;
    form.eans.value = sku.eans.join("\n");
    form.product_name.value = sku.product_name;
    form.is_parametrized.checked = sku.is_parametrized;
    form.product_name.focus();
    return;
  }

  form.eans.value = param("ean") || "";
  form.trade_reference.value = param("ref") || "";
  (form.trade_reference.value ? form.product_name : form.trade_reference).focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const body = {
    trade_reference: form.trade_reference.value.trim(),
    eans: form.eans.value
      .split(/[\s,;]+/)
      .map((code) => code.trim())
      .filter(Boolean),
    product_name: form.product_name.value.trim(),
    is_parametrized: form.is_parametrized.checked,
  };
  if (!body.trade_reference || !body.product_name) {
    toast("Podaj referencję i nazwę produktu", "error");
    return;
  }
  await withBusy($("#submit"), async () => {
    try {
      const sku = skuId
        ? await api(`/skus/${encodeURIComponent(skuId)}`, { method: "PATCH", body })
        : await api("/skus", { method: "POST", body });
      location.href = back ? withParam(back, "sku", sku.id) : "skus.html";
    } catch (err) {
      showError(err);
    }
  });
});

init().catch(showError);
