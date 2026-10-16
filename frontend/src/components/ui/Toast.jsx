export default function Toast({ message, onDismiss }) {
  if (!message) return null;
  return (
    <button
      type="button"
      className="toast"
      role="status"
      aria-live="polite"
      onClick={onDismiss}
    >
      {message}
    </button>
  );
}
