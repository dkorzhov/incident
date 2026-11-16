import { Link } from "react-router-dom";

import { PageHeader } from "../components/KpiCard";
import { StateMessage } from "../components/StateMessage";

/**
 * Заглушка формы создания инцидента — экран реализуется в DMI-9.
 * Роут и общая база (api.incidents.create, бейджи, стили) уже готовы.
 */
export function IncidentCreatePage() {
  return (
    <section className="page">
      <PageHeader
        title="Новый инцидент"
        description="Форма создания: title, description, category, priority и ответственный."
      />
      <div className="panel">
        <StateMessage
          title="Форма создания появится в DMI-9"
          text="API-метод api.incidents.create и валидация полей уже готовы — осталось собрать форму."
        />
        <p className="stub-actions">
          <Link className="button button--secondary" to="/incidents">
            Вернуться в реестр
          </Link>
        </p>
      </div>
    </section>
  );
}
