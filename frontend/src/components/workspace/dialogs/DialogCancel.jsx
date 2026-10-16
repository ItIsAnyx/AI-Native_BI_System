import Button from "../../ui/Button";

export default function DialogCancel({ busy, onClose }) {
  return (
    <Button variant="secondary" disabled={busy} onClick={onClose}>
      Отмена
    </Button>
  );
}
