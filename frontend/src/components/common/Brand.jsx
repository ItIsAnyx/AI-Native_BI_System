import Icon from "./Icon";

export default function Brand({ large = false }) {
  return (
    <div className={`brand${large ? " brand-lg" : ""}`}>
      <span className="logo">
        <Icon name="spark" />
      </span>
      <span className="brand-name">Aster</span>
    </div>
  );
}
