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
  if (order.status === "CLOSED") {
    toast("Zwrot jest zamknięty — otwórz go ponownie, aby wprowadzić zmiany", "error");
    setTimeout(() => location.replace(detailUrl), 1500);
    return;
  }
  form.bo_wms_number.value = order.bo_wms_number || "";
  form.tempo_number.value = order.tempo_number || "";
  form.return_date.value = formatDate(order.return_date);
}

// ---------- Tempo number from the WMS sheet ----------
const tempoHint = $("#tempo-hint");
let autoFilledTempo = null; // what we filled in ourselves, so a number typed by hand is never overwritten
let lookupSeq = 0;
let lookupTimer = null;

function setHint(text, kind = "") {
  tempoHint.textContent = text;
  tempoHint.className = `field-hint wide ${kind}`;
}

function fillTempo(value) {
  form.tempo_number.value = value || "";
  autoFilledTempo = form.tempo_number.value;
}

async function lookupTempo() {
  clearTimeout(lookupTimer);
  const number = form.bo_wms_number.value.trim();
  const seq = ++lookupSeq;
  if (!number || number.toLowerCase() === NO_NUMBER) {
    setHint("");
    return false;
  }
  const typed = form.tempo_number.value.trim();
  const mayOverwrite = !typed || typed === autoFilledTempo;
  try {
    const wms = await api(`/wms-orders/${encodeURIComponent(number)}`);
    if (seq !== lookupSeq) return false; // the number changed while we were asking
    if (mayOverwrite) {
      fillTempo(wms.tempo_number);
      if (wms.tempo_number) setHint("Numer Tempo uzupełniony z arkusza WMS.", "ok");
      else setHint("Zamówienie jest w arkuszu WMS, ale bez numeru Tempo.");
      return Boolean(wms.tempo_number);
    }
    if (typed !== wms.tempo_number) setHint(`Uwaga: w arkuszu WMS numer Tempo to ${wms.tempo_number || "brak"}.`, "warn");
    else setHint("");
    return true;
  } catch (err) {
    if (seq !== lookupSeq) return false;
    if (err.status !== 404) {
      showError(err);
      return false;
    }
    if (mayOverwrite) fillTempo("");
    setHint("Brak tego numeru w arkuszu WMS — wpisz numer Tempo ręcznie.", "warn");
    return false;
  }
}

form.bo_wms_number.addEventListener("input", () => {
  clearTimeout(lookupTimer);
  lookupTimer = setTimeout(lookupTempo, 400);
});
form.bo_wms_number.addEventListener("change", lookupTempo);

// A scanner ends with Enter: look the number up instead of submitting, then move on.
form.bo_wms_number.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  const filled = await lookupTempo();
  (filled ? $("#submit") : form.tempo_number).focus();
});

form.tempo_number.addEventListener("input", () => {
  if (form.tempo_number.value.trim() !== autoFilledTempo) setHint("");
});

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
