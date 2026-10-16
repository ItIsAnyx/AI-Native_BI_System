import { forwardRef } from "react";

const Button = forwardRef(function Button(
  {
    children,
    type = "button",
    variant = "primary",
    loading = false,
    className = "",
    disabled,
    ...props
  },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`btn btn-${variant}${loading ? " loading" : ""} ${className}`.trim()}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
});
export default Button;
