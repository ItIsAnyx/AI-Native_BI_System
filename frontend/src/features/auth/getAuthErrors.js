import axios from "axios";

export function getAuthErrors(error, fallback) {
  const response = axios.isAxiosError(error) ? error.response : undefined;
  const detail = response?.data?.detail;
  if (Array.isArray(detail)) {
    const fields = {
      email: "email",
      login: "username",
      password: "password",
      repeat_password: "confirmPassword",
    };
    const validationErrors = {};
    for (const issue of detail) {
      const field = fields[issue.loc?.at(-1)] || "form";
      validationErrors[field] ??=
        typeof issue.msg === "string"
          ? issue.msg
          : "Проверьте введённое значение.";
    }
    return Object.keys(validationErrors).length
      ? validationErrors
      : { form: "Проверьте введённые данные." };
  } else {
    return {
      form:
        response?.status === 401
          ? "Неверный email или пароль."
          : response?.status === 409
            ? "Email или логин уже зарегистрирован."
            : axios.isAxiosError(error) && !response
              ? "Сервер не отвечает. Проверьте подключение и попробуйте ещё раз."
              : fallback,
    };
  }
}
