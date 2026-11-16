import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="placeholder">
      <h2>Страница не найдена</h2>
      <p>
        Такого раздела нет. <Link to="/">Вернуться на дашборд</Link>
      </p>
    </section>
  );
}
