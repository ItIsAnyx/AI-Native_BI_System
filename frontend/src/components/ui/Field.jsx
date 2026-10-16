import { forwardRef, useId, useState } from "react";

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
        ...props
    },
    ref
) {
    const generatedId = useId();
    const fieldId = id ?? name ?? generatedId;
    const [showPassword, setShowPassword] = useState(false);
    const isPassword = type === "password";
    const inputType = isPassword && showPassword ? "text" : type;
    const descriptionId = error
        ? `${fieldId}-error`
        : hint
          ? `${fieldId}-hint`
          : undefined;

    return (
        <div>
            {label && <label htmlFor={fieldId}>{label}</label>}
            <input
                ref={ref}
                id={fieldId}
                name={name}
                type={inputType}
                required={required}
                disabled={disabled}
                aria-invalid={!!error}
                aria-describedby={descriptionId}
                {...props}
            />
            {isPassword && !disabled && (
                <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
                    aria-pressed={showPassword}
                >
                    {showPassword ? "Скрыть пароль" : "Показать пароль"}
                </button>
            )}
            {error ? (
                <p id={`${fieldId}-error`} role="alert">{error}</p>
            ) : hint ? (
                <p id={`${fieldId}-hint`}>{hint}</p>
            ) : null}
        </div>
    );
});

export default Field;
