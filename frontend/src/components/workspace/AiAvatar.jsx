import Icon from "../common/Icon";

// Логотип ассистента с вращающимся «гало» из точек.
export default function AiAvatar() {
  return (
    <div className="logo-wrap" aria-hidden="true">
      <span className="logo-halo">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <i key={i} className="halo-dot" />
        ))}
      </span>
      <span className="logo">
        <Icon name="spark" />
      </span>
    </div>
  );
}
