import Modal from "../../ui/Modal";
import Button from "../../ui/Button";
import DialogCancel from "./DialogCancel";
import { useDialogAction } from "../../../hooks/useDialogAction";
import DialogError from "./DialogError";

export default function DeleteProjectDialog({
  project,
  workspace,
  onClose,
  notify,
}) {
  const count = workspace.chats.filter(
    (chat) => chat.projectId === project.id,
  ).length;
  const { error, busy, perform } = useDialogAction({ onClose, notify });
  return (
    <Modal title="Удалить проект?" onClose={busy ? () => {} : onClose}>
      <p className="muted">
        {count
          ? `В проекте «${project.name}» чатов: ${count}. Оставить их в «Недавних» или удалить вместе с проектом?`
          : `Проект «${project.name}» пуст и будет удалён.`}
      </p>
      <DialogError error={error} />
      <div className="dialog-actions dialog-stack">
        <DialogCancel busy={busy} onClose={onClose} />
        {count > 0 && (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() =>
              perform(
                () => workspace.deleteProject(project.id, false),
                "Проект удалён. Чаты сохранены.",
              )
            }
          >
            Оставить чаты
          </Button>
        )}
        <Button
          variant="danger"
          loading={busy}
          onClick={() =>
            perform(
              () => workspace.deleteProject(project.id, true),
              "Проект удалён.",
            )
          }
        >
          {count ? "Удалить вместе с чатами" : "Удалить"}
        </Button>
      </div>
    </Modal>
  );
}
