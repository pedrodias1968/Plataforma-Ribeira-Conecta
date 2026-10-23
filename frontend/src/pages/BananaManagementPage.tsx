import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import type { Farm360Api } from "../api/client";
import type { FieldContext, PortfolioProperty } from "../types/farm360";
import { AccountantReportPanel } from "../features/accountant/AccountantReportPanel";
import { CorrectionsPanel } from "../features/corrections/CorrectionsPanel";
import { CostPanel } from "../features/costs/CostPanel";
import { FertilizationPanel } from "../features/fertilization/FertilizationPanel";
import { HarvestPanel } from "../features/harvest/HarvestPanel";
import { SalesPanel } from "../features/sales/SalesPanel";
import { SoilPanel } from "../features/soil/SoilPanel";
import { StockPanel } from "../features/stock/StockPanel";
import { customerPropertyName } from "../presentation";
import "./BananaManagementPage.css";

type ModuleId = "colheita" | "adubacao" | "solo" | "estoque" | "custos" | "vendas" | "contador" | "correcoes";

const MODULES: Array<{ id: ModuleId; label: string; hint: string }> = [
  { id: "colheita", label: "Colheita", hint: "Cachos, caixas, peso e descarte por talhão." },
  { id: "adubacao", label: "Adubação", hint: "O que foi aplicado, em qual talhão e quando." },
  { id: "solo", label: "Solo", hint: "Amostras de solo georreferenciadas e laudos de laboratório por talhão." },
  { id: "estoque", label: "Estoque", hint: "Entradas, saídas e saldo de cada insumo." },
  { id: "custos", label: "Custos", hint: "Custo por talhão e por kg, só com dados completos." },
  { id: "vendas", label: "Vendas", hint: "Comprador, valor a receber, prazo e pagamentos." },
  { id: "contador", label: "Contador", hint: "Vendas e custos do período em planilha." },
  { id: "correcoes", label: "Correções", hint: "Corrija um registro sem apagar o histórico." },
];

/**
 * ERP da banana em tela própria: os mesmos painéis por talhão que antes ficavam
 * espremidos na lateral do Farm360, agora com espaço para tabelas e formulários.
 */
export function BananaManagementPage({
  api,
  apiBaseUrl,
  tenantId,
  token,
  propertyId,
  onSelectProperty,
}: {
  api: Farm360Api;
  apiBaseUrl: string;
  tenantId: string;
  token: string;
  propertyId?: string;
  onSelectProperty: (propertyId: string) => void;
}) {
  const [properties, setProperties] = useState<PortfolioProperty[]>([]);
  const [propertiesState, setPropertiesState] = useState<"loading" | "ready" | "error">("loading");
  const [fields, setFields] = useState<FieldContext[]>([]);
  const [fieldsState, setFieldsState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [active, setActive] = useState<ModuleId>("colheita");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const propertyIdRef = useRef(propertyId);
  propertyIdRef.current = propertyId;
  useEffect(() => {
    let alive = true;
    api.portfolio(tenantId).then((result) => {
      if (!alive) return;
      setProperties(result.items);
      setPropertiesState("ready");
      // Com uma única propriedade, ela já vem selecionada.
      if (!propertyIdRef.current && result.items.length === 1) onSelectProperty(result.items[0].id);
    }).catch(() => {
      if (alive) setPropertiesState("error");
    });
    return () => { alive = false; };
  }, [api, tenantId, onSelectProperty]);

  useEffect(() => {
    if (!propertyId) return;
    let alive = true;
    setFieldsState("loading");
    api.fields(tenantId, propertyId).then((result) => {
      if (!alive) return;
      setFields(result.items);
      setFieldsState("ready");
    }).catch(() => {
      if (alive) setFieldsState("error");
    });
    return () => { alive = false; };
  }, [api, tenantId, propertyId]);

  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!delta) return;
    event.preventDefault();
    const next = (index + delta + MODULES.length) % MODULES.length;
    setActive(MODULES[next].id);
    tabRefs.current[next]?.focus();
  };

  const property = properties.find((item) => item.id === propertyId);
  const module = MODULES.find((item) => item.id === active) ?? MODULES[0];
  const panelProps = { tenantId, propertyId: propertyId ?? "", apiBaseUrl, token };

  return (
    <main className="erp">
      <section className="erp-intro">
        <div>
          <p className="eyebrow">Gestão da banana</p>
          <h1>{property ? customerPropertyName(property.name) : "Escolha uma propriedade"}</h1>
          <p className="erp-intro-text">
            Tudo é registrado por talhão. O que não foi anotado aparece como “sem registro”: o sistema não inventa valores.
          </p>
        </div>
        <label className="erp-property">
          Propriedade
          <select
            value={propertyId ?? ""}
            onChange={(event) => event.target.value && onSelectProperty(event.target.value)}
            disabled={propertiesState !== "ready" || properties.length === 0}
          >
            <option value="">{propertiesState === "loading" ? "Carregando…" : "Selecione"}</option>
            {properties.map((item) => (
              <option key={item.id} value={item.id}>{customerPropertyName(item.name)}</option>
            ))}
          </select>
        </label>
      </section>

      {propertiesState === "error" && <p className="erp-notice" role="alert">Não foi possível carregar as propriedades agora.</p>}
      {propertiesState === "ready" && properties.length === 0 && <p className="erp-notice">Nenhuma propriedade disponível para este acesso.</p>}

      {propertyId && (
        <>
          <div className="erp-tabs" role="tablist" aria-label="Módulos da gestão da banana">
            {MODULES.map((item, index) => (
              <button
                key={item.id}
                ref={(element) => {
                  tabRefs.current[index] = element;
                }}
                type="button"
                role="tab"
                id={`erp-tab-${item.id}`}
                aria-selected={item.id === active}
                aria-controls="erp-panel"
                tabIndex={item.id === active ? 0 : -1}
                className={`erp-tab${item.id === active ? " is-active" : ""}`}
                onClick={() => setActive(item.id)}
                onKeyDown={(event) => onTabKey(event, index)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="erp-hint">{module.hint}</p>
          {fieldsState === "error" && <p className="erp-notice" role="alert">Não foi possível carregar os talhões agora. Os módulos sem talhão continuam disponíveis.</p>}
          {fieldsState === "ready" && fields.length === 0 && <p className="erp-notice">Esta propriedade ainda não tem talhões cadastrados. Cadastre os talhões no Farm360 para registrar por talhão.</p>}
          <div id="erp-panel" role="tabpanel" aria-labelledby={`erp-tab-${active}`} className="erp-panel" key={`${propertyId}-${active}`}>
            {active === "colheita" && <HarvestPanel fields={fields} {...panelProps} />}
            {active === "adubacao" && <FertilizationPanel fields={fields} {...panelProps} />}
            {active === "solo" && <SoilPanel fields={fields} {...panelProps} />}
            {active === "estoque" && <StockPanel {...panelProps} />}
            {active === "custos" && <CostPanel fields={fields} {...panelProps} />}
            {active === "vendas" && <SalesPanel {...panelProps} />}
            {active === "contador" && <AccountantReportPanel {...panelProps} />}
            {active === "correcoes" && <CorrectionsPanel fields={fields} {...panelProps} />}
          </div>
        </>
      )}
    </main>
  );
}
