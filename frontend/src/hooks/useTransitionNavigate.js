import { useCallback } from "react";
import { flushSync } from "react-dom";
import { useNavigate } from "react-router";

// Пока идёт анимация, повторные переходы (например, автоматический редирект
// после входа) игнорируем, чтобы не прерывать её.
let inFlight = null;

/**
 * Как useNavigate, но страница сменяется с анимацией (View Transitions API).
 * В браузерах без поддержки или при prefers-reduced-motion переход мгновенный.
 */
export function useTransitionNavigate() {
  const navigate = useNavigate();

  return useCallback(
    (to, options) => {
      if (inFlight) return;
      const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      if (typeof document.startViewTransition !== "function" || reduce) {
        navigate(to, options);
        return;
      }
      const transition = document.startViewTransition(() => {
        flushSync(() => navigate(to, options));
      });
      inFlight = transition.finished.catch(() => {}).finally(() => {
        inFlight = null;
      });
    },
    [navigate],
  );
}
