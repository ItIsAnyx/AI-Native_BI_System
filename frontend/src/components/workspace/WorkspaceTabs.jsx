import { useRef } from "react";
import Icon from "../common/Icon";

const tabs = [
  { id: "chat", label: "Chat", icon: "chat" },
  { id: "dash", label: "Dashboard", icon: "grid" },
  { id: "data", label: "Data sources", icon: "db" },
];
export default function WorkspaceTabs({ value, onChange }) {
  const buttons = useRef([]);
  function onKey(event, index) {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft")
      next = (index + tabs.length - 1) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next === undefined) return;
    event.preventDefault();
    onChange(tabs[next].id);
    buttons.current[next]?.focus();
  }
  return (
    <div
      className="tabs"
      role="tablist"
      aria-label="Вкладки рабочего пространства"
    >
      {tabs.map((tab, index) => (
        <button
          key={tab.id}
          ref={(node) => {
            buttons.current[index] = node;
          }}
          type="button"
          role="tab"
          className="tab"
          id={`tab-${tab.id}`}
          aria-controls={`panel-${tab.id}`}
          aria-selected={value === tab.id}
          tabIndex={value === tab.id ? 0 : -1}
          onKeyDown={(event) => onKey(event, index)}
          onClick={() => onChange(tab.id)}
        >
          <Icon name={tab.icon} />
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}
