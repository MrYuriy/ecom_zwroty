"use strict";

const PAGE_SIZE = 50;
const state = { page: 1 };
const form = $("#job-form");

function jobRow(job) {
  return h(
    "tr",
    {},
    h("td", { "data-label": "Dzień" }, job.work_date),
    h("td", { "data-label": "Minuty" }, String(job.minutes)),
    h("td", { "data-label": "Zapisał" }, job.author_name || "—"),
    h(
      "td",
      { class: "actions-cell" },
      h("button", { class: "secondary small", onclick: () => edit(job) }, "Edytuj"),
      " ",
      h("button", { class: "danger small", onclick: (e) => remove(job, e.currentTarget) }, "Usuń"),
    ),
  );
}

async function loadJobs() {
  try {
    const page = await api("/work-logs", { query: { page: state.page, limit: PAGE_SIZE } });
    $("#jobs").replaceChildren(
      ...(page.items.length
        ? page.items.map(jobRow)
        : [h("tr", {}, h("td", { colspan: "4", class: "empty" }, "Brak wpisów."))]),
    );
    renderPager($("#pager"), page, (next) => {
      state.page = next;
      loadJobs();
    });
  } catch (err) {
    showError(err);
  }
}

function edit(job) {
  form.day.value = job.work_date;
  form.minutes.value = job.minutes;
  form.minutes.focus();
}

async function remove(job, button) {
  if (!confirm(`Usunąć wpis z dnia ${job.work_date}?`)) return;
  await withBusy(button, async () => {
    try {
      await api(`/work-logs/${job.work_date}`, { method: "DELETE" });
      toast("Wpis usunięty");
      loadJobs();
    } catch (err) {
      showError(err);
    }
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const day = form.day.value;
  await withBusy($("#submit"), async () => {
    try {
      await api(`/work-logs/${day}`, { method: "PUT", body: { minutes: Number(form.minutes.value) } });
      toast("Zapisano czas pracy");
      form.minutes.value = "";
      state.page = 1;
      loadJobs();
    } catch (err) {
      showError(err);
    }
  });
});

// A day already written down is shown, so a second entry corrects it instead of surprising the operator.
form.day.addEventListener("change", async () => {
  if (!form.day.value) return;
  try {
    const job = await api(`/work-logs/${form.day.value}`);
    form.minutes.value = job.minutes;
  } catch (err) {
    if (err.status !== 404) showError(err);
  }
});

requireUser()
  .then(() => {
    form.day.value = todayIso();
    form.day.dispatchEvent(new Event("change"));
    return loadJobs();
  })
  .catch(showError);
