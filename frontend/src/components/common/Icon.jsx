export default function Icon({ name, className = "", ...props }) {
  return (
    <svg
      className={`ic ${className}`.trim()}
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <use href={`#i-${name}`} />
    </svg>
  );
}
