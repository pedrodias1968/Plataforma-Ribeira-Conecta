import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { CorrectionsApi, CorrectionsApiError, type RecordItem, type RecordKind } from "../../api/corrections";
import type { FieldContext } from "../../types/farm360";
import { buildPayload, KINDS } from "./kinds";

export function CorrectionsPanel({ fields, tenantId, propertyId, apiBaseUrl, token, api: injectedApi }: {
  fields: FieldContext[];
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: CorrectionsApi;
}) {
  const api = useMemo(() => injectedApi ?? new CorrectionsApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [kind, setKind] = useState<RecordKind>("sale");
  const [items, setItems] = useState<RecordItem[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "forbidden" | "error">("loading");
  const [editing, setEditing] = useState<RecordItem | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const config = KINDS[kind];
  const fieldName = useCallback(
    (id: unknown) => fields.find((field) => field.id === id)?.name ?? "talhão não identificado",
    [fields],
  );

  const load = useCallback(async () => {
    setLoadState("loading");
    try {
      setItems(await api.list(tenantId, propertyId, kind));
      setLoadState("ready");
    } catch (error) {
      setItems([]);
      setLoadState(error instanceof CorrectionsApiError && error.status === 403 ? "forbidden" : "error");
    }
  }, [api, tenantId, propertyId, kind]);

  useEffect(() => {
    setEditing(null);
    setMessage(null);
    void load();
  }, [load]);

  function startEditing(item: RecordItem) {
    const initial: Record<string, string> = {};
    for (const def of config.fields) {
      const value = item[def.key];
      initial[def.key] = value === null || value === undefined ? "" : String(value);
    }
    setValues(initial);
    setEditing(item);
    setMessage(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setMessage(null);
    const built = buildPayload(config, values);
    if ("error" in built) return setMessage(built.error);
    setSaving(true);
    try {
      await api.correct(tenantId, kind, editing.id, built.payload);
      setEditing(null);
      setMessage("Correção salva. O registro anterior continua no histórico.");
      await load();
    } catch (error) {
      if (error instanceof CorrectionsApiError && error.status === 403) {
        setMessage("Seu perfil não pode corrigir este tipo de registro.");
      } else if (error instanceof CorrectionsApiError && error.status === 409) {
        setMessage("Este registro já foi corrigido. A lista foi atualizada.");
        setEditing(null);
        await load();
      } else {
        setMessage("Não foi possível salvar a correção. Confira os dados e tente novamente.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="corrections-panel" aria-labelledby="corrections-title">
      <h2 id="corrections-title">Corrigir um registro</h2>
      <label>
        Tipo de registro
        <select value={kind} onChange={(event) => setKind(event.target.value as RecordKind)}>
          {(Object.keys(KINDS) as RecordKind[]).map((key) => (
            <option key={key} value={key}>{KINDS[key].label}</option>
          ))}
        </select>
      </label>
      {loadState === "loading" && <p>Carregando registros…</p>}
      {loadState === "forbidden" && <p>Seu perfil não tem acesso a estes registros.</p>}
      {loadState === "error" && <p>Não foi possível carregar os registros agora.</p>}
      {loadState === "ready" && items.length === 0 && <p>Nenhum registro para corrigir.</p>}
      {loadState === "ready" && items.length > 0 && (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              {config.describe(item, fieldName)}{" "}
              <button type="button" onClick={() => startEditing(item)}>Corrigir</button>
            </li>
          ))}
        </ul>
      )}
      <p className="limitations">A correção cria um novo registro; o original fica guardado no histórico e deixa de contar nos totais.</p>

      {editing && (
        <form onSubmit={submit} aria-label="Corrigir registro">
          <fieldset>
            <legend>Corrigir: {config.describe(editing, fieldName)}</legend>
            {config.fields.map((def) => (
              <label key={def.key}>
                {def.label}
                {def.kind === "select" ? (
                  <select value={values[def.key] ?? ""} onChange={(e) => setValues({ ...values, [def.key]: e.target.value })}>
                    {!def.required && <option value="">sem registro</option>}
                    {def.options?.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type={def.kind === "date" ? "date" : "text"}
                    inputMode={def.kind === "int" || def.kind === "number" ? "decimal" : undefined}
                    value={values[def.key] ?? ""}
                    onChange={(e) => setValues({ ...values, [def.key]: e.target.value })}
                  />
                )}
              </label>
            ))}
            <label>Motivo da correção<input value={values.correction_reason ?? ""} onChange={(e) => setValues({ ...values, correction_reason: e.target.value })} /></label>
            <label>Corrigido por<input value={values.recorded_by ?? ""} onChange={(e) => setValues({ ...values, recorded_by: e.target.value })} /></label>
            <label>Origem da correção<input value={values.source_reference ?? ""} onChange={(e) => setValues({ ...values, source_reference: e.target.value })} /></label>
            <button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar correção"}</button>
            <button type="button" onClick={() => setEditing(null)}>Cancelar</button>
          </fieldset>
        </form>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
