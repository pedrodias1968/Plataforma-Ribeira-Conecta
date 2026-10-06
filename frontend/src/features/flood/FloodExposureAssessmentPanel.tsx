import { useState, useEffect } from "react";
import type { Farm360Api } from "../../api/client";
import type { FloodExposureAssessment } from "../../types/farm360";
import { Status } from "../../components/Status";

export function FloodExposureAssessmentPanel({ api, tenantId, propertyId }: { api: Farm360Api; tenantId: string; propertyId: string }) {
  const [assessments, setAssessments] = useState<FloodExposureAssessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAssessments = async () => {
      try {
        setLoading(true);
        const result = await api.floodExposureAssessments(tenantId, undefined, "PROPERTY", propertyId);
        setAssessments(result.items);
        setError(null);
      } catch {
        setError("Falha ao carregar avaliações de exposição a inundações");
      } finally {
        setLoading(false);
      }
    };
    loadAssessments();
  }, [api, tenantId, propertyId]);

  if (loading) {
    return <section className="flood-exposure-panel"><p>Carregando avaliações de exposição a inundações...</p></section>;
  }

  if (error) {
    return <section className="flood-exposure-panel"><p className="error">{error}</p></section>;
  }

  if (assessments.length === 0) {
    return <section className="flood-exposure-panel"><p>Ainda não há avaliações de exposição a inundações para esta propriedade.</p></section>;
  }

  return (
    <section className="flood-exposure-panel">
      <h2>Exposição a Inundações</h2>
      <ul>
        {assessments.map((assessment) => (
          <li key={assessment.id}>
            <p>
              <strong>{assessment.event_key}</strong>
            </p>
            <p>
              Status: <Status value={assessment.status} />
            </p>
            <p>
              Classificação: <Status value={assessment.classification} />
            </p>
            <p>Método: {assessment.method}</p>
            {assessment.intersection_km2 !== null && (
              <p>Área intersectada: {assessment.intersection_km2.toFixed(3)} km²</p>
            )}
            {assessment.limitations.length > 0 && (
              <p className="limitations">
                Limitações: {assessment.limitations.join(", ")}
              </p>
            )}
            <p className="timestamp">
              Avaliado em: {new Date(assessment.assessed_at).toLocaleString("pt-BR")}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
