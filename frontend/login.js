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

  const wmsLogin = form.wms_login.value.trim();
  const password = form.password.value;
  if (!wmsLogin || !password) {
    errorBox.textContent = "Podaj login WMS i hasło.";
    errorBox.hidden = false;
    return;
  }

  await withBusy(form.querySelector("button"), async () => {
    try {
      const data = await api("/auth/login", { method: "POST", body: { wms_login: wmsLogin, password } });
      TOKEN.set(data.access_token);
      location.replace(nextPage());
    } catch (err) {
      errorBox.textContent = err.status === 401 ? "Nieprawidłowy login lub hasło." : err.message;
      errorBox.hidden = false;
      form.password.select();
    }
  });
});

redirectIfLoggedIn();
