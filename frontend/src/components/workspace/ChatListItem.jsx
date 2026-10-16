import Icon from "../common/Icon";

export default function ChatListItem({
  chat,
  active,
  onSelect,
  onMove,
  onDelete,
}) {
  return (
    <li className="chat-item">
      <button
        type="button"
        className={`row${active ? " active" : ""}`}
        aria-current={active ? "page" : undefined}
        onClick={() => onSelect(chat.id)}
      >
        <Icon name="chat" />
        <span className="lbl">{chat.title}</span>
      </button>
      <div className="row-actions">
        <button
          type="button"
          className="act-btn"
          aria-label={`Переместить чат «${chat.title}» в проект`}
          onClick={() => onMove(chat.id)}
        >
          <Icon name="move" />
        </button>
        <button
          type="button"
          className="act-btn del-btn"
          aria-label={`Удалить чат «${chat.title}»`}
          onClick={() => onDelete(chat.id)}
        >
          <Icon name="trash" />
        </button>
      </div>
    </li>
  );
}
