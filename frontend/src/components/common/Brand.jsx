import Icon from "./Icon";

// sparkles — три мерцающих точки рядом с названием (декор боковой панели).
export default function Brand({ large = false, sparkles = false }) {
  return (
    <div className={`brand${large ? " brand-lg" : ""}`}>
      <span className="logo">
        <Icon name="spark" />
      </span>
      <span className="brand-name">Aster</span>
      {sparkles && (
        <span className="brand-sparkles" aria-hidden="true">
          <i className="sparkle" />
          <i className="sparkle" />
          <i className="sparkle" />
        </span>
      )}
    </div>
  );
}
