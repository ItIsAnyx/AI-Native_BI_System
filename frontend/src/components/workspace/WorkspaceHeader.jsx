import Icon from "../common/Icon";
import ThemeToggle from "../auth/ThemeToggle";

export default function WorkspaceHeader({
  title,
  projectName,
  demo,
  drawer,
  onOpenMenu,
  theme,
  onToggleTheme,
}) {
  return (
    <header className="topbar">
      <button
        type="button"
        className="icon-btn only-mobile"
        aria-label="Открыть меню"
        aria-controls="sidebar"
        aria-expanded={drawer}
        onClick={onOpenMenu}
      >
        <Icon name="menu" />
      </button>
      <div className="title-block">
        <h1>{title || "Новый чат"}</h1>
        <p className="muted small">
          Рабочее пространство · {projectName || "Личное"}
          {demo && " · Демо"}
        </p>
      </div>
      <ThemeToggle theme={theme} onToggle={onToggleTheme} />
    </header>
  );
}
