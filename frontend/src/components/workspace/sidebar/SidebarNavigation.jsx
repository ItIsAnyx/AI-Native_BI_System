import Icon from "../../common/Icon";
import ChatListItem from "../ChatListItem";
import ProjectListItem from "./ProjectListItem";

export default function SidebarNavigation({
  workspace,
  query,
  onSelect,
  onNewChat,
  onDialog,
}) {
  const search = query.trim().toLowerCase();
  const matches = (chat) => chat.title.toLowerCase().includes(search);
  const recent = workspace.chats.filter((c) => !c.projectId && matches(c));
  const projects = workspace.projects.filter(
    (p) =>
      !search ||
      p.name.toLowerCase().includes(search) ||
      workspace.chats.some((c) => c.projectId === p.id && matches(c)),
  );
  const row = (chat) => (
    <ChatListItem
      key={chat.id}
      chat={chat}
      active={chat.id === workspace.activeId}
      onSelect={onSelect}
      onMove={(id) => onDialog({ type: "move", id })}
      onDelete={(id) => onDialog({ type: "delete-chat", id })}
    />
  );
  return (
    <nav className="side-scroll" aria-label="Чаты и проекты">
      <section>
        <div className="side-head">
          <h2 className="side-h">Проекты</h2>
          <button
            type="button"
            className="icon-btn sm"
            aria-label="Создать проект"
            onClick={() => onDialog({ type: "create-project" })}
          >
            <Icon name="plus" />
          </button>
        </div>
        <ul className="list">
          {projects.map((project) => (
            <ProjectListItem
              key={project.id}
              project={project}
              chats={workspace.chats.filter(
                (chat) => chat.projectId === project.id,
              )}
              search={search}
              renderChat={row}
              onToggle={workspace.toggleProject}
              onNewChat={onNewChat}
              onDialog={onDialog}
            />
          ))}
        </ul>
        {!workspace.projects.length && !search && (
          <p className="side-empty">Проектов пока нет.</p>
        )}
      </section>
      <div className="side-divider" aria-hidden="true">
        <i />
        <i />
        <i />
      </div>
      <section>
        <h2 className="side-h">Недавние</h2>
        <ul className="list">{recent.map(row)}</ul>
        {workspace.chatsLoading && (
          <p className="side-empty" role="status">
            Загрузка чатов…
          </p>
        )}
        {workspace.chatsError && (
          <p className="side-empty" role="alert">
            Не удалось загрузить чаты.{" "}
            <button
              type="button"
              className="link text-link"
              onClick={workspace.reloadChats}
            >
              Повторить
            </button>
          </p>
        )}
        {!workspace.chatsLoading &&
          !workspace.chatsError &&
          !recent.length &&
          !projects.length && (
            <p className="side-empty">
              {search ? "Ничего не найдено по запросу." : "Чатов пока нет."}
            </p>
          )}
      </section>
    </nav>
  );
}
