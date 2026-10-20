import { useRef } from "react";
import { Outlet, useLocation } from "react-router";
import ThemeToggle from "../components/auth/ThemeToggle";
import Brand from "../components/common/Brand";
import { useAuthScene } from "../hooks/useAuthScene";
import { useTheme } from "../hooks/useTheme";

const CORNERS = ["tl", "tr", "bl", "br"];

export default function MainLayout() {
  const { theme, toggleTheme } = useTheme();
  // Форма регистрации длиннее входа: ей нужна более широкая карточка (поля в две колонки).
  const wide = useLocation().pathname.startsWith("/register");
  const containerRef = useRef(null);
  const cardRef = useRef(null);
  const blobsRef = useRef(null);
  const gridRef = useRef(null);
  useAuthScene({ containerRef, cardRef, blobsRef, gridRef, theme });

  return (
    <main className="login" id="main-anchor" data-theme={theme} ref={containerRef}>
      <canvas className="bg-blobs" ref={blobsRef} aria-hidden="true" />
      <canvas className="bg-grid" ref={gridRef} aria-hidden="true" />
      <ThemeToggle theme={theme} onToggle={toggleTheme} />
      <div className={`login-card${wide ? " login-card--wide" : ""}`} ref={cardRef}>
        {CORNERS.map((corner) => (
          <span key={corner} className={`corner-deco ${corner}`} aria-hidden="true">
            ✻
          </span>
        ))}
        <Brand large />
        <Outlet />
      </div>
    </main>
  );
}
