import { NavLink, useLocation } from "react-router";
import TransitionRedirect from "../components/common/TransitionRedirect";

import Button from "../components/ui/Button";
import Field from "../components/ui/Field";
import { useAuth } from "../hooks/useAuth";
import { useAuthForm } from "../hooks/useAuthForm";
import { readLoginForm } from "../features/auth/loginForm";

export default function Login() {
  const { login, user, initialized } = useAuth();
  const location = useLocation();
  const { errors, setErrors, loading, handleSubmit } = useAuthForm({
    submit: login,
    readForm: readLoginForm,
    failureMessage: "Не удалось войти. Попробуйте ещё раз.",
  });

  if (initialized && user) return <TransitionRedirect to="/" />;

  return (
    <>
      <h1>С возвращением</h1>
      <p className="muted">
        Войдите, чтобы продолжить планирование, письмо и исследования.
      </p>
      <div>
        <form onSubmit={handleSubmit} noValidate aria-busy={loading}>
          <Field
            label="Email"
            name="email"
            type="email"
            placeholder="example@mail.com"
            autoComplete="email"
            maxLength={255}
            error={errors.email}
          />

          <Field
            label="Пароль"
            name="password"
            type="password"
            placeholder="Введите пароль"
            autoComplete="current-password"
            error={errors.password}
          />

          <p className="small" style={{ textAlign: "right", marginBottom: 16 }}>
            <button
              type="button"
              className="link text-link"
              onClick={() =>
                setErrors({
                  form: "Восстановление пароля пока не подключено. Обратитесь к администратору.",
                })
              }
            >
              Забыли пароль?
            </button>
          </p>
          {errors.form && (
            <p className="banner banner-error" role="alert">
              {errors.form}
            </p>
          )}

          <Button type="submit" className="btn-block" loading={loading}>
            {loading ? "Вход..." : "Войти"}
          </Button>
        </form>

        <div className="form-note">
          <p className="muted center small">
            Нет аккаунта?{" "}
            <NavLink className="link" to="/register" state={location.state}>
              Зарегистрироваться
            </NavLink>
          </p>
        </div>
      </div>
    </>
  );
}
