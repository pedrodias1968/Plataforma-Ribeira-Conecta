import { useState, useEffect } from "react";
import type { Farm360Api } from "../../api/client";
import type { ValeDoRibeiraSituation } from "../../types/farm360";

export function HydrologyPanel({ api, tenantId }: { api: Farm360Api; tenantId: string }) {
  const [situation, setSituation] = useState<ValeDoRibeiraSituation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSituation = async () => {
      try {
        setLoading(true);
        const result = await api.get<ValeDoRibeiraSituation>(
          `/v1/tenants/${encodeURIComponent(tenantId)}/vale-do-ribeira/situation`,
        );
        setSituation(result);
        setError(null);
      } catch {
        setError("Falha ao carregar situação hidrológica");
      } finally {
        setLoading(false);
      }
    };
    loadSituation();
  }, [api, tenantId]);

  if (loading) {
    return <section className="hydrology-panel"><p>Carregando situação hidrológica...</p></section>;
  }

  if (error) {
    return <section className="hydrology-panel"><p className="error">{error}</p></section>;
  }

  if (!situation) {
    return <section className="hydrology-panel"><p>Dados hidrológicos não disponíveis</p></section>;
  }

  const renderObservation = (title: string, summary: HydrologySummary) => {
    const statusMap: Record<string, { label: string; color: string }> = {
      AVAILABLE: { label: "Disponível", color: "success" },
      AUTH_REQUIRED: { label: "Credenciais pendentes", color: "warning" },
      INSUFFICIENT_LOCAL_DATA: { label: "Dados insuficientes", color: "warning" },
      UNKNOWN: { label: "Desconhecido", color: "default" },
    };
    const statusInfo = statusMap[summary.status] || { label: summary.status, color: "default" };

    return (
      <div className="hydrology-card">
        <h3>{title}</h3>
        <div className="hydrology-status">
          <span className={`status-badge status-${statusInfo.color}`}>{statusInfo.label}</span>
        </div>
        {summary.provider && <p>Fonte: {summary.provider}</p>}
        {summary.reason && <p className="reason">{summary.reason}</p>}
        {summary.latest_observation && <p>Última observação: {new Date(summary.latest_observation).toLocaleString("pt-BR")}</p>}
        {summary.observations !== undefined && <p>Total de observações: {summary.observations}</p>}
        {summary.quality && <p>Qualidade: {summary.quality}</p>}
      </div>
    );
  };

  const renderReservoirEvents = () => {
    if (!situation.reservoir_events || situation.reservoir_events.length === 0) {
      return <p>Nenhum evento de operação de reservatório registrado.</p>;
    }

    return (
      <ul className="hydrology-list">
        {situation.reservoir_events.map((event, idx) => (
          <li key={idx}>
            <strong>{event.event_type}</strong>
            {event.published_at && <span> em {new Date(event.published_at).toLocaleString("pt-BR")}</span>}
            {event.numeric_value !== undefined && event.unit && <span>: {event.numeric_value} {event.unit}</span>}
            {event.description_sanitized && <p>{event.description_sanitized}</p>}
            {event.source_reference && <small>Fonte: {event.source_reference}</small>}
          </li>
        ))}
      </ul>
    );
  };

  const renderClimateContext = () => {
    if (!situation.climate_context || situation.climate_context.length === 0) {
      return <p>Nenhum contexto climático disponível.</p>;
    }

    return (
      <ul className="hydrology-list">
        {situation.climate_context.map((ctx, idx) => (
          <li key={idx}>
            <strong>{ctx.provider}</strong>
            {ctx.issued_on && <span> emitido em {new Date(ctx.issued_on).toLocaleString("pt-BR")}</span>}
            {ctx.enso_state && <p>Estado ENSO: {ctx.enso_state}</p>}
            {ctx.probability !== undefined && <p>Probabilidade: {ctx.probability * 100}%</p>}
            {ctx.strength_category && <p>Intensidade: {ctx.strength_category}</p>}
            {ctx.source_reference && <small>Fonte: {ctx.source_reference}</small>}
          </li>
        ))}
      </ul>
    );
  };

  const renderActiveAlerts = () => {
    if (!situation.active_alerts || situation.active_alerts.length === 0) {
      return <p>Nenhum alerta ativo.</p>;
    }

    const severityMap: Record<string, string> = {
      critical: "severidade-crítica",
      high: "severidade-alta",
      medium: "severidade-média",
      low: "severidade-baixa",
    };

    return (
      <ul className="hydrology-list">
        {situation.active_alerts.map((alert) => (
          <li key={alert.id}>
            <span className={`alert-severity ${severityMap[alert.severity] || ""}`}>
              {alert.type}
            </span>
            <p>{alert.description}</p>
            <small>Origem: {alert.source} | Emitido em {new Date(alert.issued_at).toLocaleString("pt-BR")}</small>
          </li>
        ))}
      </ul>
    );
  };

  const renderUnknowns = () => {
    if (!situation.unknowns || situation.unknowns.length === 0) {
      return null;
    }

    return (
      <div className="hydrology-unknowns">
        <h4>Dados desconhecidos</h4>
        <ul>
          {situation.unknowns.map((unknown, idx) => (
            <li key={idx}>{unknown}</li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <section className="hydrology-panel">
      <h2>Hidrologia</h2>
      <p className="hydrology-generated">
        Última atualização: {new Date(situation.generated_at).toLocaleString("pt-BR")}
      </p>

      <div className="hydrology-cards">
        {renderObservation("Pluviometria", situation.rainfall_summary)}
        {renderObservation("Nível de Rios", situation.river_summary)}
      </div>

      {situation.reservoir_events && situation.reservoir_events.length > 0 && (
        <div className="hydrology-section">
          <h3>Eventos de Operação de Reservatórios</h3>
          {renderReservoirEvents()}
        </div>
      )}

      {situation.climate_context && situation.climate_context.length > 0 && (
        <div className="hydrology-section">
          <h3>Contexto Climático</h3>
          {renderClimateContext()}
        </div>
      )}

      {situation.active_alerts && situation.active_alerts.length > 0 && (
        <div className="hydrology-section">
          <h3>Alertas Ativos</h3>
          {renderActiveAlerts()}
        </div>
      )}

      {renderUnknowns()}
    </section>
  );
}
