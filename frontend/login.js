"use strict";

// Only follow redirects back into the cabinet, never to another site.
function nextPage() {
  const next = new URLSearchParams(location.search).get("next");
  return next && next.startsWith("/app/") && !next.startsWith("//") ? next : "/app/returns.html";
}

async function redirectIfLoggedIn() {
  if (!TOKEN.get()) return;
  try {
    await api("/auth/me");
    location.replace(nextPage());
  } catch {
    TOKEN.clear();
  }
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const errorBox = $("#login-error");
  errorBox.hidden = true;

  const email = form.email.value.trim();
  const password = form.password.value;
  if (!email || !password) {
    errorBox.textContent = "Podaj e-mail i hasło.";
    errorBox.hidden = false;
    return;
  }

  await withBusy(form.querySelector("button"), async () => {
    try {
      const data = await api("/auth/login", { method: "POST", body: { email, password } });
      TOKEN.set(data.access_token);
      location.replace(nextPage());
    } catch (err) {
      errorBox.textContent = err.status === 401 ? "Nieprawidłowy e-mail lub hasło." : err.message;
      errorBox.hidden = false;
      form.password.select();
    }
  });
});

redirectIfLoggedIn();
