import { Navigate, NavLink, useLocation } from "react-router";

import Button from "../components/ui/Button";
import Field from "../components/ui/Field";
import { useAuth } from "../hooks/useAuth";
import { useAuthForm } from "../hooks/useAuthForm";
import { readRegisterForm } from "../features/auth/registerForm";

export default function Register() {
  const { register, user, initialized } = useAuth();
  const location = useLocation();
  const { errors, loading, handleSubmit } = useAuthForm({
    submit: register,
    readForm: readRegisterForm,
    failureMessage: "Не удалось зарегистрироваться. Попробуйте ещё раз.",
  });

  if (initialized && user) return <Navigate to="/" replace />;

  return (
    <>
      <h1>Создайте аккаунт</h1>
      <p className="muted">
        Начните планировать, писать и исследовать с Aster.
      </p>
      <div>
        <form onSubmit={handleSubmit} noValidate aria-busy={loading}>
          <Field
            label="Имя пользователя"
            name="username"
            placeholder="Ваш логин"
            autoComplete="username"
            maxLength={255}
            error={errors.username}
          />

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
            placeholder="Придумайте пароль"
            autoComplete="new-password"
            hint="Минимум 8 символов"
            error={errors.password}
          />

          <Field
            label="Подтверждение пароля"
            name="confirmPassword"
            type="password"
            placeholder="Повторите пароль"
            autoComplete="new-password"
            error={errors.confirmPassword}
          />

          {errors.form && (
            <p className="banner banner-error" role="alert">
              {errors.form}
            </p>
          )}

          <Button type="submit" className="btn-block" loading={loading}>
            {loading ? "Регистрация..." : "Создать аккаунт"}
          </Button>
        </form>

        <div className="form-note">
          <p className="muted center small">
            Уже есть аккаунт?{" "}
            <NavLink className="link" to="/login" state={location.state}>
              Войти
            </NavLink>
          </p>
        </div>
      </div>
      <div className="divider">
        <span>или</span>
      </div>
      <NavLink to="/demo" className="btn btn-secondary btn-block">
        Войти в демо-режиме
      </NavLink>
      <p className="hint small center">
        Демо доступно без регистрации. Вход в аккаунт проверяется сервером.
      </p>
    </>
  );
}
