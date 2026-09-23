"use strict";

const form = $("#report-form");

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const day = form.day.value;
  if (!day) return;
  // A cabinet page, not the PDF itself: reloading that tab rebuilds the report from current data.
  window.open(`report-view.html?day=${encodeURIComponent(day)}`, "_blank");
});

requireUser()
  .then(() => {
    form.day.value = todayIso();
  })
  .catch(showError);
