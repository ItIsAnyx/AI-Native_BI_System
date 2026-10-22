import { NavLink } from "react-router";
import { useTransitionNavigate } from "../../hooks/useTransitionNavigate";

// NavLink, который переходит на страницу с анимацией.
export default function TransitionLink({ to, onClick, ...props }) {
  const navigate = useTransitionNavigate();
  return (
    <NavLink
      to={to}
      {...props}
      onClick={(event) => {
        onClick?.(event);
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return;
        }
        event.preventDefault();
        navigate(to);
      }}
    />
  );
}
