"use strict";

// Create a user, or edit one with ?id=<user id>.
const userId = param("id");
const form = $("#user-form");

async function init() {
  await requireUser({ adminOnly: true });
  if (!userId) {
    form.full_name.focus();
    return;
  }

  const user = await api(`/users/${encodeURIComponent(userId)}`);
  const isSelf = user.id === currentUser.id;
  $("#title").textContent = `Edycja: ${user.full_name}`;
  document.title = "Edycja użytkownika — Zwroty e-com";
  $("#password-label").textContent = "Nowe hasło (puste = bez zmian)";
  // The e-mail is the login and stays fixed once the account exists.
  form.email.disabled = true;
  $("#active-field").classList.remove("hidden");
  // An admin can't lock themselves out.
  form.role.disabled = isSelf;
  form.is_active.disabled = isSelf;
  $("#self-note").classList.toggle("hidden", !isSelf);

  form.full_name.value = user.full_name;
  form.email.value = user.email;
  form.role.value = user.role;
  form.is_active.checked = user.is_active;
  form.full_name.focus();
}

function buildRequest() {
  const fullName = form.full_name.value.trim();
  const password = form.password.value;
  if (!fullName) return { error: "Podaj imię i nazwisko" };

  if (!userId) {
    const email = form.email.value.trim();
    if (!email || !password) return { error: "Podaj e-mail i hasło" };
    return { path: "/users", method: "POST", body: { full_name: fullName, email, role: form.role.value, password } };
  }

  const body = { full_name: fullName };
  if (!form.role.disabled) body.role = form.role.value;
  if (!form.is_active.disabled) body.is_active = form.is_active.checked;
  if (password) body.password = password;
  return { path: `/users/${encodeURIComponent(userId)}`, method: "PATCH", body };
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const request = buildRequest();
  if (request.error) {
    toast(request.error, "error");
    return;
  }
  await withBusy($("#submit"), async () => {
    try {
      await api(request.path, { method: request.method, body: request.body });
      location.href = "users.html";
    } catch (err) {
      showError(err);
    }
  });
});

init().catch(showError);
