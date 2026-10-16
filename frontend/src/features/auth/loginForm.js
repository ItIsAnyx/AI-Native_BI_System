export function readLoginForm(formElement) {
  const form = new FormData(formElement);

  const email = String(form.get("email") || "").trim();
  const password = String(form.get("password") || "");

  const nextErrors = {};
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
    nextErrors.email = "Введите корректный email.";
  if (!password.trim()) nextErrors.password = "Введите пароль.";

  return { values: { email, password }, errors: nextErrors };
}
