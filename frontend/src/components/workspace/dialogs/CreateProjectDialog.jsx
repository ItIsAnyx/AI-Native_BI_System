import { useState } from "react";
import Modal from "../../ui/Modal";
import Button from "../../ui/Button";
import DialogCancel from "./DialogCancel";
import { useDialogAction } from "../../../hooks/useDialogAction";

export default function CreateProjectDialog({
  modal,
  workspace,
  onClose,
  notify,
  onProjectCreated,
}) {
  const [name, setName] = useState("");
  const { error, setError, busy, perform } = useDialogAction({
    onClose,
    notify,
  });
  return (
    <Modal title="Новый проект" onClose={busy ? () => {} : onClose}>
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void perform(
            async () => {
              await workspace.createProject(name, modal.chatId);
              onProjectCreated();
            },
            modal.chatId ? "Чат перемещён в новый проект." : "Проект создан.",
          );
        }}
      >
        {modal.chatId && (
          <p className="muted small">Чат будет перемещён в этот проект.</p>
        )}
        <label className="dialog-label" htmlFor="new-project-name">
          Название
        </label>
        <input
          className="text-input"
          id="new-project-name"
          maxLength={40}
          autoComplete="off"
          placeholder="Например, Запуск продукта"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setError("");
          }}
          aria-invalid={!!error}
          aria-describedby={error ? "new-project-error" : undefined}
          disabled={busy}
        />
        {error && (
          <p id="new-project-error" className="field-err" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <DialogCancel busy={busy} onClose={onClose} />
          <Button type="submit" loading={busy}>
            Создать
          </Button>
        </div>
      </form>
    </Modal>
  );
}
