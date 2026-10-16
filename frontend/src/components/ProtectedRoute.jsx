import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../hooks/useAuth";

export default function ProtectedRoute() {
    const location = useLocation();

    const { user, initialized } = useAuth();

    if (!initialized) {
        return <main className="status-screen" role="status">Проверяем вход…</main>;
    }

    if (!user) {
        return (
            <Navigate to="/login" replace state={{ from: location }} />
        );
    }

    return <Outlet />;
}
