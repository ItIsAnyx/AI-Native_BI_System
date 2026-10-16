import Modal from "../../ui/Modal";
import Button from "../../ui/Button";
import DialogCancel from "./DialogCancel";
import { useDialogAction } from "../../../hooks/useDialogAction";
import DialogError from "./DialogError";
import Icon from "../../common/Icon";

export default function MoveChatDialog({
  chat,
  workspace,
  onClose,
  onDialog,
  notify,
}) {
  const { error, busy, perform } = useDialogAction({ onClose, notify });
  return (
    <Modal title="Переместить чат" onClose={busy ? () => {} : onClose}>
      <p className="muted">Куда переместить чат «{chat.title}»?</p>
      <ul className="pick-list">
        {[
          ...workspace.projects,
          { id: null, name: "Без проекта (Недавние)" },
        ].map((item) => (
          <li key={item.id ?? "recent"}>
            <button
              type="button"
              className="pick-item"
              aria-current={chat.projectId === item.id ? "true" : undefined}
              disabled={busy}
              onClick={() =>
                perform(
                  () => workspace.moveChat(chat.id, item.id),
                  "Чат перемещён.",
                )
              }
            >
              <Icon name={item.id ? "folder" : "chat"} />
              <span className="lbl">{item.name}</span>
              {chat.projectId === item.id && <Icon name="check" />}
            </button>
          </li>
        ))}
      </ul>
      {!workspace.projects.length && (
        <p className="muted small">Проектов пока нет — создайте первый.</p>
      )}
      <DialogError error={error} />
      <div className="dialog-actions dialog-stack">
        <DialogCancel busy={busy} onClose={onClose} />
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() => onDialog({ type: "create-project", chatId: chat.id })}
        >
          Новый проект…
        </Button>
      </div>
    </Modal>
  );
}
