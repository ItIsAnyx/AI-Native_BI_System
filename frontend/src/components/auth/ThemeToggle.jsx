import Icon from "../common/Icon";

export default function ThemeToggle({ theme, onToggle }) {
  const dark = theme === "dark";
  const label = dark ? "Включить светлую тему" : "Включить тёмную тему";
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={onToggle}
      aria-label={label}
      title={label}
    >
      <Icon name={dark ? "sun" : "moon"} />
    </button>
  );
}
