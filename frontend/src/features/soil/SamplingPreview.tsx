import { useState } from "react";

import { SoilApiError, type SamplingGridPreview, type SoilApi } from "../../api/soil";
import type { FieldContext } from "../../types/farm360";

const PREVIEW_WARNING =
  "Prévia não salva. Os pontos são locais sugeridos (DERIVED_LOCATION), não são medições: confirme cada local no campo antes de coletar.";

function formatCoordinate(value: number): string {
  return value.toFixed(6);
}

export function SamplingPreview({ fields, tenantId, propertyId, api }: {
  fields: FieldContext[];
  tenantId: string;
  propertyId: string;
  api: SoilApi;
}) {
  const [fieldId, setFieldId] = useState("");
  const [spacing, setSpacing] = useState("");
  const [preview, setPreview] = useState<SamplingGridPreview | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const spacingValue = Number(spacing);
  const canGenerate = fieldId !== "" && spacing.trim() !== "" && Number.isFinite(spacingValue) && spacingValue > 0;

  async function generate() {
    if (!canGenerate) return;
    setMessage(null);
    setGenerating(true);
    try {
      const result = await api.samplingGridPreview(tenantId, propertyId, fieldId, spacingValue);
      setPreview(result);
    } catch (error) {
      setPreview(null);
      if (error instanceof SoilApiError) {
        if (error.status === 403) return setMessage("Sem permissão para ver a prévia de amostragem.");
        if (error.status === 404) return setMessage("Talhão não encontrado.");
        if (error.status === 422) return setMessage("Espaçamento inválido ou grade grande demais para este talhão.");
      }
      setMessage("Não foi possível gerar a prévia.");
    } finally {
      setGenerating(false);
    }
  }

  function downloadGeoJson() {
    if (!preview) return;
    const blob = new Blob([JSON.stringify(preview.points)], { type: "application/geo+json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `amostragem-previa-${preview.field_id}.geojson`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const coordinates = preview?.points.features.map((feature) => feature.geometry.coordinates) ?? [];

  return (
    <section className="sampling-preview" aria-labelledby="sampling-preview-title">
      <h3 id="sampling-preview-title">Prévia da grade de amostragem</h3>
      <p>{PREVIEW_WARNING}</p>
      <label>
        Talhão
        <select value={fieldId} onChange={(e) => setFieldId(e.target.value)}>
          <option value="">Escolha…</option>
          {fields.map((field) => (
            <option key={field.id} value={field.id}>{field.name}</option>
          ))}
        </select>
      </label>
      <label>
        Espaçamento (m)
        <input
          type="number"
          inputMode="decimal"
          min="0"
          value={spacing}
          onChange={(e) => setSpacing(e.target.value)}
        />
      </label>
      <button type="button" disabled={!canGenerate || generating} onClick={() => void generate()}>
        {generating ? "Gerando…" : "Gerar prévia"}
      </button>
      {message && <p role="status">{message}</p>}
      {preview && (
        <>
          <p role="status">
            {coordinates.length} ponto(s) sugerido(s). CRS projetado: {preview.projected_crs}.
          </p>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Longitude</th>
                <th>Latitude</th>
              </tr>
            </thead>
            <tbody>
              {coordinates.map(([longitude, latitude], index) => (
                <tr key={index}>
                  <td>{index + 1}</td>
                  <td>{formatCoordinate(longitude)}</td>
                  <td>{formatCoordinate(latitude)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" onClick={downloadGeoJson}>Baixar GeoJSON</button>
        </>
      )}
    </section>
  );
}
