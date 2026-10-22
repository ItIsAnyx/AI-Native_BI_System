import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "aster-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function readStoredTheme() {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch {
    return null;
  }
}

function systemTheme() {
  return window.matchMedia?.(DARK_QUERY).matches ? "dark" : "light";
}

/**
 * Тема оформления страниц входа и регистрации.
 * Порядок выбора: сохранённый выбор пользователя → тема системы.
 * Пока пользователь сам не переключил тему, она следует за системной.
 */
export function useTheme() {
  const [theme, setTheme] = useState(() => readStoredTheme() ?? systemTheme());

  useEffect(() => {
    if (readStoredTheme()) return undefined;
    const media = window.matchMedia?.(DARK_QUERY);
    if (!media) return undefined;
    const onChange = () => {
      if (!readStoredTheme()) setTheme(media.matches ? "dark" : "light");
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Хранилище недоступно (например, приватный режим): тема просто не запомнится.
      }
      return next;
    });
  }, []);

  return { theme, toggleTheme };
}
