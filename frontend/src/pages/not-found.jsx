import { Link } from "react-router";
import Brand from "../components/common/Brand";
export default function NotFound() {
  return (
    <main className="status-screen" id="main-anchor">
      <Brand large />
      <h1>Страница не найдена</h1>
      <p className="muted">
        Проверьте адрес или вернитесь в рабочее пространство.
      </p>
      <Link className="btn btn-primary" to="/">
        На главную
      </Link>
    </main>
  );
}
