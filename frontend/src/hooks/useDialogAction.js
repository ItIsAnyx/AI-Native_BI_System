import { useState } from "react";

export function useDialogAction({ onClose, notify }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function perform(action, message) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await action();
      onClose();
      if (message) notify(message);
    } catch (problem) {
      setError(problem.message || "Не удалось выполнить действие.");
    } finally {
      setBusy(false);
    }
  }

  return { error, setError, busy, perform };
}
