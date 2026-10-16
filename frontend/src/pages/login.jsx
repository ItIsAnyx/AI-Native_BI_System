import { useState } from "react";
import axios from "axios";
import { NavLink, useLocation, useNavigate } from "react-router";

import Button from "../components/ui/Button";
import Field from "../components/ui/Field";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e) {
        e.preventDefault();
        if (loading) return;

        const form = new FormData(e.currentTarget);

        const email = String(form.get("email") || "").trim();
        const password = String(form.get("password") || "");

        setErrors({});

        setLoading(true);

        try {
            await login({ email, password });
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
                const fields = { email: "email", password: "password" };
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
                            : "Не удалось войти. Попробуйте ещё раз." });
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
                        С возвращением!
                    </h1>

                    <p>
                        Войдите в свой аккаунт, чтобы продолжить
                    </p>
                </div>

                <div>
                    <form
                        onSubmit={handleSubmit}
                        noValidate
                        aria-busy={loading}
                    >
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
                            placeholder="Введите пароль"
                            autoComplete="current-password"
                            error={errors.password}
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
                            {loading ? "Вход..." : "Войти"}
                        </Button>
                    </form>

                    <div>
                        <p>
                            Нет аккаунта?{" "}
                            <NavLink
                                to="/register"
                                state={location.state}
                            >
                                Зарегистрироваться
                            </NavLink>
                        </p>
                    </div>
                </div>
            </div>
        </main>
    );
}

