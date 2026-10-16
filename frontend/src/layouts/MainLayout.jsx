import { Outlet } from "react-router";
import Brand from "../components/common/Brand";

export default function MainLayout() {
  return (
    <main className="login" id="main-anchor">
      <div className="login-card">
        <Brand large />
        <Outlet />
      </div>
    </main>
  );
}
