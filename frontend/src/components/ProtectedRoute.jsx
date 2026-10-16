import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../hooks/useAuth";

export default function ProtectedRoute() {
    const location = useLocation();

    const { user, initialized } = useAuth();

    if (!initialized) {
        return <p role="status">Проверяем сессию...</p>;
    }

    if (!user) {
        return (
            <Navigate to="/login" replace state={{ from: location }} />
        );
    }

    return <Outlet />;
}
