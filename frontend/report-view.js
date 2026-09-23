"use strict";

// Shows the daily form for ?day=. The PDF needs the bearer token, so it is fetched here and
// displayed from a blob — but the tab's own address stays this page, so a reload rebuilds the report.
const day = param("day");

async function showReport() {
  await requireUser();
  if (!day) {
    location.replace("report.html");
    return;
  }
  document.title = `Raport dzienny ${day} — Zwroty e-com`;

  const resp = await fetch(`${API_BASE}/reports/day-pdf?day=${encodeURIComponent(day)}`, {
    headers: { Authorization: `Bearer ${TOKEN.get()}` },
  });
  if (!resp.ok) throw new ApiError(resp.status, "Nie udało się przygotować raportu");

  const url = URL.createObjectURL(await resp.blob());
  const frame = $("#pdf");
  frame.src = url;
  frame.hidden = false;
  $("#message").hidden = true;
  window.addEventListener("pagehide", () => URL.revokeObjectURL(url));
}

showReport().catch((err) => {
  $("#message").textContent =
    err instanceof ApiError ? err.message : "Nie udało się przygotować raportu";
  $("#message").className = "notice error";
  showError(err);
});
