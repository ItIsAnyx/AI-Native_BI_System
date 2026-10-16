import Icon from "../../common/Icon";

export default function SidebarAccount({ user, demo, loggingOut, onLogout }) {
  const name = user?.login || user?.email?.split("@")[0] || "Гость";
  return (
    <div className="side-bottom">
      <div className="account">
        <span className="avatar" aria-hidden="true">
          {(name.match(/\p{L}/gu) || ["A"]).slice(0, 2).join("").toUpperCase()}
        </span>
        <div className="account-info">
          <p className="account-name">
            {name}
            {demo && <span className="session-badge">Демо</span>}
          </p>
          <p className="muted small">{user?.email}</p>
        </div>
        <button
          type="button"
          className="icon-btn"
          aria-label="Выйти из аккаунта"
          disabled={loggingOut}
          onClick={onLogout}
        >
          <Icon name="logout" />
        </button>
      </div>
    </div>
  );
}
