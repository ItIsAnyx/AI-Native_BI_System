import Brand from "../common/Brand";
import Icon from "../common/Icon";
import { useDrawerFocus } from "../../hooks/useDrawerFocus";
import SidebarNavigation from "./sidebar/SidebarNavigation";
import SidebarAccount from "./sidebar/SidebarAccount";

export default function Sidebar({
  workspace,
  user,
  query,
  onQuery,
  open,
  onClose,
  onNewChat,
  onSelect,
  onDialog,
  onLogout,
  loggingOut,
}) {
  const sidebar = useDrawerFocus(open, onClose);

  return (
    <>
      {open && <div className="scrim" onClick={onClose} aria-hidden="true" />}
      <aside
        ref={sidebar}
        className={`sidebar${open ? " open" : ""}`}
        id="sidebar"
        aria-label="Боковая панель"
      >
        <div className="side-top">
          <Brand sparkles />
          <button
            type="button"
            className="icon-btn only-mobile"
            aria-label="Закрыть меню"
            onClick={onClose}
          >
            <Icon name="x" />
          </button>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-block"
          onClick={() => onNewChat()}
        >
          <Icon name="plus" />
          Новый чат
        </button>
        <div className="input-wrap search">
          <Icon name="search" className="lead" />
          <input
            type="search"
            placeholder="Поиск по чатам"
            aria-label="Поиск по чатам"
            value={query}
            onChange={(e) => onQuery(e.target.value)}
          />
        </div>
        <SidebarNavigation
          workspace={workspace}
          query={query}
          onSelect={onSelect}
          onNewChat={onNewChat}
          onDialog={onDialog}
        />
        <SidebarAccount
          user={user}
          loggingOut={loggingOut}
          onLogout={onLogout}
        />
      </aside>
    </>
  );
}
