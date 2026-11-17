import { Link, useParams } from "react-router-dom";

import { PageHeader } from "../components/KpiCard";
import { StateMessage } from "../components/StateMessage";

/**
 * Заглушка карточки инцидента — экран реализуется в DMI-9.
 * Роут `incidents/:id`, api.incidents.get и `allowed_transitions` уже готовы,
 * чтобы DMI-9 рисовал кнопки действий по ответу сервера.
 */
export function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <section className="page">
      <PageHeader
        title={id ? `Инцидент ${id}` : "Инцидент"}
        description="Карточка: информация, история и комментарии; действия — только допустимые переходы статусов."
      />
      <div className="panel">
        <StateMessage
          title="Карточка появится в DMI-9"
          text="api.incidents.get, смена статуса и комментарии уже типизированы; сервер отдаёт allowed_transitions."
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
