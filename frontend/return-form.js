"use strict";

// One form for both creating a return and editing its header (?id=<uuid>).
const orderId = param("id");
const form = $("#order-form");

async function init() {
  await requireUser();
  if (!orderId) {
    form.return_date.value = todayIso();
    return;
  }
  const detailUrl = `return.html?id=${encodeURIComponent(orderId)}`;
  $("#back").href = detailUrl;
  $("#back").textContent = "‹ Wróć do zwrotu";
  $("#cancel").href = detailUrl;
  $("#title").textContent = "Edycja nagłówka";
  $("#submit").textContent = "Zapisz";
  document.title = "Edycja nagłówka — Zwroty e-com";

  const order = await api(`/returns/${orderId}`);
  form.bo_wms_number.value = order.bo_wms_number || "";
  form.tempo_number.value = order.tempo_number || "";
  form.return_date.value = formatDate(order.return_date);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.return_date.value) {
    toast("Podaj datę zwrotu", "error");
    form.return_date.focus();
    return;
  }
  const body = {
    bo_wms_number: nullIfBlank(form.bo_wms_number.value),
    tempo_number: nullIfBlank(form.tempo_number.value),
    return_date: form.return_date.value,
  };
  await withBusy($("#submit"), async () => {
    try {
      if (orderId) {
        await api(`/returns/${orderId}`, { method: "PATCH", body });
        location.href = `return.html?id=${encodeURIComponent(orderId)}`;
      } else {
        // A new return goes straight to receiving its first item.
        const order = await api("/returns", { method: "POST", body });
        location.href = `line.html?order=${encodeURIComponent(order.uuid)}`;
      }
    } catch (err) {
      showError(err);
    }
  });
});

init().catch(showError);
