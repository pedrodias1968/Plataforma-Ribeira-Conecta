import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import {
  SoilApi,
  SoilApiError,
  type SoilLabAnalysis,
  type SoilLabValueKey,
  type SoilSamplePoint,
} from "../../api/soil";
import type { FieldContext } from "../../types/farm360";
import { LAB_FIELDS, NUMBER, formatDate, parseOptional, todayIso, valueLabel } from "./labels";

export function SoilPanel({ fields, tenantId, propertyId, apiBaseUrl, token, api: injectedApi }: {
  fields: FieldContext[];
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: SoilApi;
}) {
  const api = useMemo(() => injectedApi ?? new SoilApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [samples, setSamples] = useState<SoilSamplePoint[]>([]);
  const [analyses, setAnalyses] = useState<Record<string, SoilLabAnalysis[]>>({});
  const [loadState, setLoadState] = useState<"loading" | "ready" | "forbidden" | "error">("loading");

  // Nova amostra
  const [sampleCode, setSampleCode] = useState("");
  const [fieldId, setFieldId] = useState("");
  const [collectionDate, setCollectionDate] = useState(todayIso());
  const [depthTop, setDepthTop] = useState("0");
  const [depthBottom, setDepthBottom] = useState("20");
  const [longitude, setLongitude] = useState("");
  const [latitude, setLatitude] = useState("");
  const [collector, setCollector] = useState("");
  const [sampleSource, setSampleSource] = useState("");
  const [savingSample, setSavingSample] = useState(false);
  const [sampleMessage, setSampleMessage] = useState<string | null>(null);

  // Novo laudo
  const [labSampleId, setLabSampleId] = useState("");
  const [labName, setLabName] = useState("");
  const [reportNumber, setReportNumber] = useState("");
  const [reportDate, setReportDate] = useState(todayIso());
  const [labValues, setLabValues] = useState<Partial<Record<SoilLabValueKey, string>>>({});
  const [savingLab, setSavingLab] = useState(false);
  const [labMessage, setLabMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const items = await api.samples(tenantId, propertyId);
      setSamples(items);
      const pairs = await Promise.all(items.map(async (item) => [item.id, await api.analyses(tenantId, item.id)] as const));
      setAnalyses(Object.fromEntries(pairs));
      setLoadState("ready");
    } catch (error) {
      setSamples([]);
      setAnalyses({});
      setLoadState(error instanceof SoilApiError && error.status === 403 ? "forbidden" : "error");
    }
  }, [api, tenantId, propertyId]);

  useEffect(() => {
    void load();
  }, [load]);

  const fieldName = (id: string | null) =>
    id ? fields.find((field) => field.id === id)?.name ?? "talhão não encontrado" : "propriedade (sem talhão)";

  async function submitSample(event: FormEvent) {
    event.preventDefault();
    setSampleMessage(null);
    if (!sampleCode.trim()) return setSampleMessage("Informe o código da amostra (o mesmo enviado ao laboratório).");
    if (!collector.trim() || !sampleSource.trim()) return setSampleMessage("Informe quem coletou e a origem do dado (ex.: GPS, caderno).");
    const top = parseOptional(depthTop);
    const bottom = parseOptional(depthBottom);
    if (top === null || bottom === null || Number.isNaN(top) || Number.isNaN(bottom) || top < 0 || bottom <= top) {
      return setSampleMessage("Informe a profundidade em cm, com o fim maior que o início (ex.: 0 a 20).");
    }
    const lon = parseOptional(longitude);
    const lat = parseOptional(latitude);
    if (lon === null || lat === null || Number.isNaN(lon) || Number.isNaN(lat) || lon < -180 || lon > 180 || lat < -90 || lat > 90) {
      return setSampleMessage("Informe longitude e latitude do ponto de coleta (graus decimais, WGS84).");
    }
    setSavingSample(true);
    try {
      await api.createSample(tenantId, propertyId, {
        sample_code: sampleCode.trim(),
        depth_top_cm: top,
        depth_bottom_cm: bottom,
        collection_date: collectionDate,
        collector_name: collector.trim(),
        location_geojson: { type: "Point", coordinates: [lon, lat] },
        location_crs: "EPSG:4326",
        source_reference: sampleSource.trim(),
        field_id: fieldId || null,
      });
      setSampleMessage("Amostra salva.");
      setSampleCode("");
      setLongitude("");
      setLatitude("");
      await load();
    } catch (error) {
      setSampleMessage(
        error instanceof SoilApiError && error.status === 403
          ? "Seu perfil não pode registrar amostras de solo."
          : error instanceof SoilApiError && error.status === 422
            ? "O ponto precisa estar dentro do limite da propriedade (e do talhão escolhido). Confira as coordenadas."
            : "Não foi possível salvar a amostra. Confira os dados e tente novamente.",
      );
    } finally {
      setSavingSample(false);
    }
  }

  async function submitLab(event: FormEvent) {
    event.preventDefault();
    setLabMessage(null);
    if (!labSampleId) return setLabMessage("Escolha a amostra do laudo.");
    if (!labName.trim() || !reportNumber.trim()) return setLabMessage("Informe o laboratório e o número do laudo.");
    const values: Partial<Record<SoilLabValueKey, number | null>> = {};
    for (const field of LAB_FIELDS) {
      const parsed = parseOptional(labValues[field.key] ?? "");
      if (parsed !== null && (Number.isNaN(parsed) || parsed < 0)) {
        return setLabMessage(`Valor inválido em “${field.label}”. Use números; deixe em branco o que o laudo não traz.`);
      }
      values[field.key] = parsed;
    }
    if (Object.values(values).every((value) => value === null)) {
      return setLabMessage("Informe ao menos um valor do laudo.");
    }
    setSavingLab(true);
    try {
      await api.createAnalysis(tenantId, labSampleId, {
        lab_name: labName.trim(),
        report_number: reportNumber.trim(),
        report_date: reportDate,
        ...values,
      });
      setLabMessage("Laudo salvo.");
      setReportNumber("");
      setLabValues({});
      await load();
    } catch (error) {
      setLabMessage(
        error instanceof SoilApiError && error.status === 403
          ? "Seu perfil não pode registrar laudos."
          : "Não foi possível salvar o laudo. Confira os dados e tente novamente.",
      );
    } finally {
      setSavingLab(false);
    }
  }

  return (
    <section className="soil-panel" aria-labelledby="soil-title">
      <h2 id="soil-title">Análise de solo por talhão</h2>
      {loadState === "loading" && <p>Carregando amostras de solo…</p>}
      {loadState === "forbidden" && <p>Seu perfil não tem acesso às análises de solo.</p>}
      {loadState === "error" && <p>Não foi possível carregar as amostras de solo agora.</p>}
      {loadState === "ready" && (
        <>
          {samples.length === 0 ? (
            <p>Nenhuma amostra de solo registrada.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Amostra</th>
                  <th>Talhão</th>
                  <th>Coleta</th>
                  <th>Profundidade</th>
                  <th>pH (água)</th>
                  <th>V%</th>
                  <th>CTC</th>
                  <th>Laudo</th>
                </tr>
              </thead>
              <tbody>
                {samples.map((sample) => {
                  const latest = (analyses[sample.id] ?? [])[0];
                  return (
                    <tr key={sample.id}>
                      <td>{sample.sample_code}</td>
                      <td>{fieldName(sample.field_id)}</td>
                      <td>{formatDate(sample.collection_date)}</td>
                      <td>{NUMBER.format(sample.depth_top_cm)}–{NUMBER.format(sample.depth_bottom_cm)} cm</td>
                      {latest ? (
                        <>
                          <td>{valueLabel(latest.ph_h2o, "")}</td>
                          <td>{valueLabel(latest.base_saturation_percent, "%")}</td>
                          <td>{valueLabel(latest.cation_exchange_capacity_cec, "cmolc/dm³")}</td>
                          <td>{latest.lab_name} · nº {latest.report_number} · {formatDate(latest.report_date)}</td>
                        </>
                      ) : (
                        <td colSpan={4}>aguardando laudo</td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
          <ul className="limitations">
            <li>O laudo vale só para o ponto, a profundidade e a data da amostra; não é a fertilidade do talhão inteiro.</li>
            <li>Valor que o laudo não traz fica “sem registro”, nunca zero. CTC e V% só são calculados com Ca, Mg, K e H+Al completos.</li>
            <li>Recomendação de calagem e adubação ainda não está disponível: depende de regra validada por agrônomo.</li>
          </ul>
        </>
      )}

      <form onSubmit={submitSample} aria-label="Registrar amostra de solo">
        <fieldset>
          <legend>Nova amostra</legend>
          <label>Código da amostra<input value={sampleCode} onChange={(e) => setSampleCode(e.target.value)} placeholder="Ex.: T1-0-20" /></label>
          <label>
            Talhão
            <select value={fieldId} onChange={(e) => setFieldId(e.target.value)}>
              <option value="">Propriedade (sem talhão)</option>
              {fields.map((field) => (
                <option key={field.id} value={field.id}>{field.name}</option>
              ))}
            </select>
          </label>
          <label>Data da coleta<input type="date" value={collectionDate} max={todayIso()} onChange={(e) => setCollectionDate(e.target.value)} /></label>
          <label>Profundidade inicial (cm)<input inputMode="decimal" value={depthTop} onChange={(e) => setDepthTop(e.target.value)} /></label>
          <label>Profundidade final (cm)<input inputMode="decimal" value={depthBottom} onChange={(e) => setDepthBottom(e.target.value)} /></label>
          <label>Longitude<input inputMode="decimal" value={longitude} onChange={(e) => setLongitude(e.target.value)} placeholder="-47,85" /></label>
          <label>Latitude<input inputMode="decimal" value={latitude} onChange={(e) => setLatitude(e.target.value)} placeholder="-24,49" /></label>
          <label>Coletado por<input value={collector} onChange={(e) => setCollector(e.target.value)} /></label>
          <label>Origem do dado (GPS, caderno…)<input value={sampleSource} onChange={(e) => setSampleSource(e.target.value)} /></label>
          <button type="submit" disabled={savingSample}>{savingSample ? "Salvando…" : "Salvar amostra"}</button>
          {sampleMessage && <p role="status">{sampleMessage}</p>}
        </fieldset>
      </form>

      {samples.length > 0 && (
        <form onSubmit={submitLab} aria-label="Registrar laudo de laboratório">
          <fieldset>
            <legend>Novo laudo</legend>
            <label>
              Amostra
              <select value={labSampleId} onChange={(e) => setLabSampleId(e.target.value)}>
                <option value="">Escolha…</option>
                {samples.map((sample) => (
                  <option key={sample.id} value={sample.id}>{sample.sample_code} · {fieldName(sample.field_id)}</option>
                ))}
              </select>
            </label>
            <label>Laboratório<input value={labName} onChange={(e) => setLabName(e.target.value)} /></label>
            <label>Número do laudo<input value={reportNumber} onChange={(e) => setReportNumber(e.target.value)} /></label>
            <label>Data do laudo<input type="date" value={reportDate} max={todayIso()} onChange={(e) => setReportDate(e.target.value)} /></label>
            {LAB_FIELDS.map((field) => (
              <label key={field.key}>
                {field.label}{field.unit ? ` (${field.unit})` : ""}
                <input
                  inputMode="decimal"
                  value={labValues[field.key] ?? ""}
                  onChange={(e) => setLabValues((current) => ({ ...current, [field.key]: e.target.value }))}
                />
              </label>
            ))}
            <button type="submit" disabled={savingLab}>{savingLab ? "Salvando…" : "Salvar laudo"}</button>
            {labMessage && <p role="status">{labMessage}</p>}
          </fieldset>
        </form>
      )}
    </section>
  );
}
