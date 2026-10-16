import Modal from "../../ui/Modal";
import Button from "../../ui/Button";
import DialogCancel from "./DialogCancel";
import { useDialogAction } from "../../../hooks/useDialogAction";
import DialogError from "./DialogError";

export default function DeleteChatDialog({ chat, workspace, onClose, notify }) {
  const { error, busy, perform } = useDialogAction({ onClose, notify });
  return (
    <Modal title="Удалить чат?" onClose={busy ? () => {} : onClose}>
      <p className="muted">
        Чат «{chat.title}» будет удалён без возможности восстановления.
      </p>
      <DialogError error={error} />
      <div className="dialog-actions">
        <DialogCancel busy={busy} onClose={onClose} />
        <Button
          variant="danger"
          loading={busy}
          onClick={() =>
            perform(() => workspace.deleteChat(chat.id), "Чат удалён.")
          }
        >
          Удалить
        </Button>
      </div>
    </Modal>
  );
}
