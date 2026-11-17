import { Link } from "react-router-dom";

import { PageHeader } from "../components/KpiCard";
import { StateMessage } from "../components/StateMessage";

export function NotFoundPage() {
  return (
    <section className="page">
      <PageHeader title="Страница не найдена" />
      <div className="panel">
        <StateMessage title="Такого раздела нет" text="Проверьте адрес или вернитесь на дашборд." />
        <p className="stub-actions">
          <Link className="button button--secondary" to="/">
            Вернуться на дашборд
          </Link>
        </p>
      </div>
    </section>
  );
}
