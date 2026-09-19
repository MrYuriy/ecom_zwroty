"use strict";

const PAGE_SIZE = 50;
const state = { page: 1 };

function userRow(user) {
  return h(
    "tr",
    {},
    h("td", { "data-label": "Imię i nazwisko" }, user.full_name),
    h("td", { "data-label": "Login WMS" }, user.wms_login),
    h("td", { "data-label": "Rola" }, LABELS.role[user.role]),
    h(
      "td",
      { "data-label": "Status" },
      h("span", { class: `badge ${user.is_active ? "success" : "neutral"}` }, user.is_active ? "aktywny" : "nieaktywny"),
    ),
    h(
      "td",
      { class: "actions-cell" },
      h("a", { class: "btn secondary small", href: `user-form.html?id=${encodeURIComponent(user.id)}` }, "Edytuj"),
    ),
  );
}

async function loadUsers() {
  try {
    const page = await api("/users", { query: { page: state.page, limit: PAGE_SIZE } });
    $("#users").replaceChildren(...page.items.map(userRow));
    renderPager($("#pager"), page, (next) => {
      state.page = next;
      loadUsers();
    });
  } catch (err) {
    showError(err);
  }
}

requireUser({ adminOnly: true }).then(loadUsers).catch(showError);
