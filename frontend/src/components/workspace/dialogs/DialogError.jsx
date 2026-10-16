export default function DialogError({ error }) {
  return error ? (
    <p className="field-err" role="alert">
      {error}
    </p>
  ) : null;
}
