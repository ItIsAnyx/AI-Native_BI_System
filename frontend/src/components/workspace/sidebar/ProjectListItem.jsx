import Icon from "../../common/Icon";

export default function ProjectListItem({
  project,
  chats,
  search,
  renderChat,
  onToggle,
  onNewChat,
  onDialog,
}) {
  const items = chats.filter(
    (chat) =>
      project.name.toLowerCase().includes(search) ||
      chat.title.toLowerCase().includes(search),
  );
  const expanded = search ? true : project.open;
  return (
    <li>
      <div className="chat-item">
        <button
          type="button"
          className="row"
          aria-expanded={expanded}
          onClick={() => onToggle(project.id)}
        >
          <Icon name="folder" />
          <span className="lbl">{project.name}</span>
          <span className="count">{chats.length}</span>
          <Icon name="chevron" className="chev" />
        </button>
        <div className="row-actions">
          <button
            type="button"
            className="act-btn"
            aria-label={`Новый чат в проекте «${project.name}»`}
            onClick={() => onNewChat(project.id)}
          >
            <Icon name="plus" />
          </button>
          <button
            type="button"
            className="act-btn del-btn"
            aria-label={`Удалить проект «${project.name}»`}
            onClick={() => onDialog({ type: "delete-project", id: project.id })}
          >
            <Icon name="trash" />
          </button>
        </div>
      </div>
      {expanded && (
        <ul className="sub">
          {items.length ? (
            items.map(renderChat)
          ) : (
            <li className="sub-empty">В проекте пока нет чатов</li>
          )}
        </ul>
      )}
    </li>
  );
}
