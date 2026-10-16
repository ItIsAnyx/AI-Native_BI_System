import { useState } from "react";
import axios from "axios";
import { NavLink, useLocation, useNavigate } from "react-router";

import Button from "../components/ui/Button";
import Field from "../components/ui/Field";
import { useAuth } from "../hooks/useAuth";

export default function Register() {
    const { register } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e) {
        e.preventDefault();
        if (loading) return;

        const form = new FormData(e.currentTarget);

        const username = String(form.get("username") || "").trim();
        const email = String(form.get("email") || "").trim();
        const password = String(form.get("password") || "");
        const confirmPassword = String(
            form.get("confirmPassword") || ""
        );

        const nextErrors = {};

        if (password !== confirmPassword) {
            nextErrors.confirmPassword =
                "Пароли не совпадают";
        }

        setErrors(nextErrors);

        if (Object.keys(nextErrors).length > 0) return;

        setLoading(true);

        try {
            await register({
                login: username,
                email,
                password,
                repeat_password: confirmPassword,
            });
            const from = location.state?.from;
            const pathname = from?.pathname;
            const validDestination = typeof pathname === "string" &&
                pathname.startsWith("/") && !pathname.startsWith("//") &&
                !pathname.includes("\\") && !/^\/(login|register)\/?$/.test(pathname);
            navigate(validDestination ? {
                pathname,
                search: typeof from.search === "string" ? from.search : "",
                hash: typeof from.hash === "string" ? from.hash : "",
            } : "/", { replace: true });
        } catch (error) {
            const response = axios.isAxiosError(error) ? error.response : undefined;
            const detail = response?.data?.detail;
            if (Array.isArray(detail)) {
                const fields = { email: "email", login: "username", password: "password", repeat_password: "confirmPassword" };
                const validationErrors = {};
                for (const issue of detail) {
                    const field = fields[issue.loc?.at(-1)] || "form";
                    validationErrors[field] ??= typeof issue.msg === "string"
                        ? issue.msg : "Проверьте введённое значение.";
                }
                setErrors(Object.keys(validationErrors).length
                    ? validationErrors : { form: "Проверьте введённые данные." });
            } else {
                setErrors({ form: response?.status === 401
                    ? "Неверный email или пароль."
                    : response?.status === 409
                        ? "Email или логин уже зарегистрирован."
                        : axios.isAxiosError(error) && !response
                            ? "Сервер не отвечает. Проверьте подключение и попробуйте ещё раз."
                            : "Не удалось зарегистрироваться. Попробуйте ещё раз." });
            }
        } finally {
            setLoading(false);
        }
    }

    return (
        <main>
            <div>
                <div>
                    <h1>
                        Создать аккаунт
                    </h1>

                    <p>
                        Заполните поля для регистрации
                    </p>
                </div>

                <div>
                    <form
                        onSubmit={handleSubmit}
                        noValidate
                        aria-busy={loading}
                    >
                        <Field
                            label="Имя пользователя"
                            name="username"
                            placeholder="Ваш логин"
                            autoComplete="username"
                            error={errors.username}
                        />

                        <Field
                            label="Email"
                            name="email"
                            type="email"
                            placeholder="example@mail.com"
                            autoComplete="email"
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
                            <p role="alert">
                                {errors.form}
                            </p>
                        )}

                        <Button
                            type="submit"
                            disabled={loading}
                        >
                            {loading
                                ? "Регистрация..."
                                : "Создать аккаунт"}
                        </Button>
                    </form>

                    <div>
                        <p>
                            Уже есть аккаунт?{" "}
                            <NavLink
                                to="/login"
                                state={location.state}
                            >
                                Войти
                            </NavLink>
                        </p>
                    </div>
                </div>
            </div>
        </main>
    );
}

