import { useCallback, useEffect, useRef, useState } from "react";

export function useToast() {
  const [toast, setToast] = useState("");
  const timer = useRef(null);
  const dismissToast = useCallback(() => {
    clearTimeout(timer.current);
    setToast("");
  }, []);
  const notify = useCallback((message) => {
    clearTimeout(timer.current);
    setToast(message);
    timer.current = setTimeout(() => setToast(""), 3500);
  }, []);
  useEffect(() => () => clearTimeout(timer.current), []);
  return { toast, notify, dismissToast };
}
