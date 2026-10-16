export function readRegisterForm(formElement) {
  const form = new FormData(formElement);

  const username = String(form.get("username") || "").trim();
  const email = String(form.get("email") || "").trim();
  const password = String(form.get("password") || "");
  const confirmPassword = String(form.get("confirmPassword") || "");

  const nextErrors = {};
  if (username.length < 3) nextErrors.username = "Минимум 3 символа.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
    nextErrors.email = "Введите корректный email.";
  if (password.length < 8 || !password.trim())
    nextErrors.password = "Минимум 8 символов.";

  if (password !== confirmPassword) {
    nextErrors.confirmPassword = "Пароли не совпадают";
  }

  return {
    values: {
      login: username,
      email,
      password,
      repeat_password: confirmPassword,
    },
    errors: nextErrors,
  };
}
