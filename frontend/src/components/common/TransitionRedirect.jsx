import { useEffect } from "react";
import { useTransitionNavigate } from "../../hooks/useTransitionNavigate";

// Вместо <Navigate>: перенаправление с анимацией перехода.
export default function TransitionRedirect({ to }) {
  const navigate = useTransitionNavigate();
  useEffect(() => {
    navigate(to, { replace: true });
  }, [navigate, to]);
  return null;
}
