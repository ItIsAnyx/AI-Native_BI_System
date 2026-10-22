import { useState } from "react";
import { useLocation } from "react-router";
import { useTransitionNavigate } from "./useTransitionNavigate";
import { getAuthDestination } from "../features/auth/getAuthDestination";
import { getAuthErrors } from "../features/auth/getAuthErrors";

export function useAuthForm({ submit, readForm, failureMessage }) {
  const navigate = useTransitionNavigate();
  const location = useLocation();
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    const result = readForm(event.currentTarget);
    setErrors(result.errors);
    if (Object.keys(result.errors).length) return;
    setLoading(true);
    try {
      await submit(result.values);
      navigate(getAuthDestination(location.state?.from), { replace: true });
    } catch (error) {
      setErrors(getAuthErrors(error, failureMessage));
    } finally {
      setLoading(false);
    }
  }

  return { errors, setErrors, loading, handleSubmit };
}
