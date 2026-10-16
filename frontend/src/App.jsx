import { useEffect } from "react";
import { Route, Routes } from "react-router";
import IconSprite from "./components/common/IconSprite";
import ProtectedRoute from "./components/ProtectedRoute";
import MainLayout from "./layouts/MainLayout";
import Login from "./pages/login";
import Register from "./pages/register";
import Workspace from "./pages/workspace";
import NotFound from "./pages/not-found";
import { useAuth } from "./hooks/useAuth";

export default function App() {
  const { initialize } = useAuth();
  useEffect(() => {
    void initialize();
  }, [initialize]);
  return (
    <>
      <IconSprite />
      <a className="skip-link" href="#main-anchor">
        Перейти к содержимому
      </a>
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>
        <Route path="/demo" element={<Workspace demo />} />
        <Route element={<ProtectedRoute />}>
          <Route index element={<Workspace />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}
