import { Route, Routes } from "react-router";
import Home from "./pages/home.jsx";
import Login from "./pages/login.jsx";
import Register from "./pages/register.jsx";
import NotFound from "./pages/not-found.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Protected from "./pages/protected.jsx";
import MainLayout from "./layouts/MainLayout.jsx";
import { useAuth } from "./hooks/useAuth";
import { useEffect } from "react";

export default function App() {
    const { initialize } = useAuth();

    useEffect(() => {
        void initialize();
    }, [initialize]);

    return (
        <>
            <Routes>
                <Route element={<MainLayout />}>
                    <Route index element={<Home />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="*" element={<NotFound />} />

                    <Route element={<ProtectedRoute />}>
                        <Route path="/protected" element={<Protected />} />
                    </Route>
                    {/* 
                        Paste new routes here
                        Or look react router docs
                    */}
                </Route>
            </Routes>
        </>
    );
}

