import Icon from "../common/Icon";

export default function WorkspacePlaceholder({ icon, title, children }) {
  return (
    <div className="placeholder">
      <span className="ph-ic">
        <Icon name={icon} />
      </span>
      <h2>{title}</h2>
      <p className="muted">{children}</p>
    </div>
  );
}
