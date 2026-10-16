import { useEffect, useRef } from "react";

export function useDrawerFocus(open, onClose) {
  const sidebar = useRef(null);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement;
    sidebar.current?.querySelector("button")?.focus();
    const onKey = (event) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const nodes = [
        ...sidebar.current.querySelectorAll(
          "button:not(:disabled), input, a[href]",
        ),
      ].filter((node) => node.getClientRects().length);
      const first = nodes[0],
        last = nodes.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      if (previous?.isConnected) previous.focus();
    };
  }, [open, onClose]);

  return sidebar;
}
