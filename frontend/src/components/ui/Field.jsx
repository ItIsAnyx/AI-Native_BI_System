import { forwardRef, useId, useState } from "react";
import Icon from "../common/Icon";

const Field = forwardRef(function Field(
  {
    label,
    type = "text",
    name,
    id,
    error,
    hint,
    required = false,
    disabled = false,
    icon,
    ...props
  },
  ref,
) {
  const generatedId = useId();
  const fieldId = id ?? name ?? generatedId;
  const [visible, setVisible] = useState(false);
  const password = type === "password";
  const description = error
    ? `${fieldId}-error`
    : hint
      ? `${fieldId}-hint`
      : undefined;
  return (
    <div className="field">
      <label htmlFor={fieldId}>{label}</label>
      <div
        className={`input-wrap${error ? " invalid" : ""}${password ? " is-password" : ""}`}
      >
        <Icon
          name={
            icon || (password ? "lock" : name === "email" ? "mail" : "check")
          }
          className="lead"
        />
        <input
          ref={ref}
          id={fieldId}
          name={name}
          type={password && visible ? "text" : type}
          required={required}
          disabled={disabled}
          aria-invalid={!!error}
          aria-describedby={description}
          {...props}
        />
        {password && (
          <button
            type="button"
            className="icon-btn in-input"
            disabled={disabled}
            onClick={() => setVisible(!visible)}
            aria-label={visible ? "Скрыть пароль" : "Показать пароль"}
            aria-pressed={visible}
          >
            <Icon name={visible ? "eyeoff" : "eye"} />
          </button>
        )}
      </div>
      {error ? (
        <p className="field-err" id={`${fieldId}-error`} role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="muted small" id={`${fieldId}-hint`}>
          {hint}
        </p>
      ) : null}
    </div>
  );
});
export default Field;
