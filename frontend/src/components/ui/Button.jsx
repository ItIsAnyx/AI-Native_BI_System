import { forwardRef } from "react";

const Button = forwardRef(function Button(
    { children, type = "button", ...props },
    ref
) {
    return (
        <button ref={ref} type={type} {...props}>
            {children}
        </button>
    );
});

export default Button;
