# ERP Surface Index — superfície de gestão agro existente

Inventário **factual** da superfície de ERP / gestão agro já existente no
repositório (backend, API e frontend) relacionada a **Gestão da banana** e a
**Solo por talhão**. Este documento **não define regra de negócio nova**: apenas
mapeia o que existe e cita o arquivo de origem. Onde a regra não está definida
no repositório, o item é marcado como **UNKNOWN / PENDENTE-GABARITO**.

Escopo desta primeira versão: os módulos por talhão expostos pela tela
"Gestão da banana" e o módulo de Solo (amostras e laudos por talhão).
`CHANGE_MODE=ADD_ONLY` — nenhum código foi alterado por este inventário.

---

## 1. Ponto de entrada (frontend)

| Item | Arquivo de origem |
|---|---|
| Tela "Gestão da banana" com abas por módulo | `frontend/src/pages/BananaManagementPage.tsx` |
| Navegação que monta a tela (`view === "BANANA"`) | `frontend/src/pages/PilotShell.tsx` |
| Rótulo do item de menu "Gestão da banana" | `frontend/src/pages/PilotShell.tsx` |

Abas declaradas em `BananaManagementPage.tsx` (`MODULES`, tipo `ModuleId`):

| Aba (id) | Rótulo | Painel montado | Arquivo do painel |
|---|---|---|---|
| `colheita` | Colheita | `HarvestPanel` | `frontend/src/features/harvest/HarvestPanel.tsx` |
| `adubacao` | Adubação | `FertilizationPanel` | `frontend/src/features/fertilization/FertilizationPanel.tsx` |
| `solo` | Solo | `SoilPanel` | `frontend/src/features/soil/SoilPanel.tsx` |
| `estoque` | Estoque | `StockPanel` | `frontend/src/features/stock/StockPanel.tsx` |
| `custos` | Custos | `CostPanel` | `frontend/src/features/costs/CostPanel.tsx` |
| `vendas` | Vendas | `SalesPanel` | `frontend/src/features/sales/SalesPanel.tsx` |
| `contador` | Contador | `AccountantReportPanel` | `frontend/src/features/accountant/AccountantReportPanel.tsx` |
| `correcoes` | Correções | `CorrectionsPanel` | `frontend/src/features/corrections/CorrectionsPanel.tsx` |

Clientes de API do frontend correspondentes:

- `frontend/src/api/harvest.ts`
- `frontend/src/api/fertilization.ts`
- `frontend/src/api/soil.ts`
- `frontend/src/api/stock.ts`
- `frontend/src/api/costs.ts`
- `frontend/src/api/sales.ts`
- `frontend/src/api/accountant.ts`
- `frontend/src/api/corrections.ts`

---

## 2. Módulos backend (`src/ribeira_platform`)

| Módulo | Responsabilidade (do docstring do arquivo) | Arquivo de origem |
|---|---|---|
| Solo / Soil Intelligence | Pontos de coleta georreferenciados, laudos de laboratório, índices agronômicos derivados | `src/ribeira_platform/soil.py` |
| Colheita / Harvest | Registros de colheita e descarte por talhão, append-only, correção por supersessão | `src/ribeira_platform/harvest.py` |
| Adubação / Fertilization | Registros de fertilização por talhão | `src/ribeira_platform/fertilization.py` |
| Custos / Cost | Lançamentos de custo por talhão e resumo | `src/ribeira_platform/costs.py` |
| Vendas / Sales | Vendas, recebimentos e resumo de recebíveis | `src/ribeira_platform/sales.py` |
| Estoque / Stock | Movimentos de estoque de insumos (IN/OUT), saldo por item | `src/ribeira_platform/stock.py` |
| Contador / Accountant Report | Pacote somente-leitura de vendas + custos do período | `src/ribeira_platform/service.py` (`accountant_report`) |
| Correções | Supersessão de registros sem apagar histórico | `src/ribeira_platform/service.py` (métodos `correct_*`) |

Repositórios instanciados no serviço de aplicação:
`src/ribeira_platform/service.py` (`self.soil`, `self.harvest`,
`self.fertilization`, `self.costs`, `self.sales`, `self.stock`).

Métodos de serviço relevantes por módulo:

| Módulo | Métodos (`src/ribeira_platform/service.py`) |
|---|---|
| Solo | `register_soil_sample_point`, `list_soil_sample_points`, `register_soil_lab_analysis`, `list_soil_lab_analyses` |
| Colheita | `register_harvest_record`, `correct_harvest_record`, `list_harvest_records`, `register_harvest_discard`, `correct_harvest_discard`, `list_harvest_discards`, `harvest_summary` |
| Adubação | `register_fertilization_record`, `correct_fertilization_record`, `list_fertilization_records`, `fertilization_summary` |
| Custos | `register_cost_entry`, `correct_cost_entry`, `list_cost_entries`, `cost_summary` |
| Vendas | `register_sale`, `correct_sale`, `list_sales`, `register_payment`, `correct_payment`, `list_payments`, `sales_summary` |
| Estoque | `register_stock_movement`, `correct_stock_movement`, `list_stock_movements`, `stock_summary` |
| Contador | `accountant_report` |

---

## 3. Endpoints da API (`src/ribeira_platform/api.py`)

### 3.1 Solo (amostras e laudos por talhão)

| Método | Rota | Permissão | Linha |
|---|---|---|---|
| POST | `/v1/tenants/{tenant_id}/properties/{property_id}/soil-samples` | `soil:write` | `api.py:1734` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/soil-samples` | `soil:read` | `api.py:1765` |
| POST | `/v1/tenants/{tenant_id}/soil-samples/{sample_id}/lab-analyses` | `soil:write` | `api.py:1787` |
| GET | `/v1/tenants/{tenant_id}/soil-samples/{sample_id}/lab-analyses` | `soil:read` | `api.py:1826` |

### 3.2 Colheita

| Método | Rota | Permissão | Linha |
|---|---|---|---|
| POST | `/v1/tenants/{tenant_id}/properties/{property_id}/harvest-records` | `harvest:write` | `api.py:1844` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/harvest-records` | `harvest:read` | `api.py:1874` |
| POST | `/v1/tenants/{tenant_id}/harvest-records/{record_id}/corrections` | `harvest:write` | `api.py:1902` |
| POST | `/v1/tenants/{tenant_id}/properties/{property_id}/harvest-discards` | `harvest:write` | `api.py:1932` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/harvest-discards` | `harvest:read` | `api.py:1961` |
| POST | `/v1/tenants/{tenant_id}/harvest-discards/{discard_id}/corrections` | `harvest:write` | `api.py:1989` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/harvest-summary` | `harvest:read` | `api.py:2018` |

### 3.3 Adubação

| Método | Rota | Permissão | Linha |
|---|---|---|---|
| POST | `/v1/tenants/{tenant_id}/properties/{property_id}/fertilization-records` | `fertilization:write` | `api.py:2040` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/fertilization-records` | `fertilization:read` | `api.py:2074` |
| POST | `/v1/tenants/{tenant_id}/fertilization-records/{record_id}/corrections` | `fertilization:write` | `api.py:2102` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/fertilization-summary` | `fertilization:read` | `api.py:2136` |

### 3.4 Custos

| Método | Rota | Permissão | Linha |
|---|---|---|---|
| POST | `/v1/tenants/{tenant_id}/properties/{property_id}/cost-entries` | `cost:write` | `api.py:2158` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/cost-entries` | `cost:read` | `api.py:2187` |
| POST | `/v1/tenants/{tenant_id}/cost-entries/{entry_id}/corrections` | `cost:write` | `api.py:2215` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/cost-summary` | `cost:read` | `api.py:2244` |

### 3.5 Vendas e recebimentos

| Método | Rota | Permissão | Linha |
|---|---|---|---|
| POST | `/v1/tenants/{tenant_id}/properties/{property_id}/sale-records` | `sale:write` | `api.py:2266` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/sale-records` | `sale:read` | `api.py:2287` |
| POST | `/v1/tenants/{tenant_id}/sale-records/{sale_id}/corrections` | `sale:write` | `api.py:2313` |
| POST | `/v1/tenants/{tenant_id}/sale-records/{sale_id}/payments` | `sale:write` | `api.py:2334` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/payment-records` | `sale:read` | `api.py:2355` |
| POST | `/v1/tenants/{tenant_id}/payment-records/{payment_id}/corrections` | `sale:write` | `api.py:2383` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/sales-summary` | `sale:read` | `api.py:2405` |

### 3.6 Estoque

| Método | Rota | Permissão | Linha |
|---|---|---|---|
| POST | `/v1/tenants/{tenant_id}/properties/{property_id}/stock-movements` | `stock:write` | `api.py:2450` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/stock-movements` | `stock:read` | `api.py:2471` |
| POST | `/v1/tenants/{tenant_id}/stock-movements/{movement_id}/corrections` | `stock:write` | `api.py:2497` |
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/stock-summary` | `stock:read` | `api.py:2518` |

### 3.7 Contador

| Método | Rota | Permissão | Linha |
|---|---|---|---|
| GET | `/v1/tenants/{tenant_id}/properties/{property_id}/accountant-report` | `sale:read` + `cost:read` | `api.py:2427` |

---

## 4. Persistência e evidência

| Migration | Tabelas | Arquivo de origem |
|---|---|---|
| 047 | `soil_sample_point`, laudos de laboratório | `db/migrations/047_soil_intelligence_foundation.sql` |
| 048 | `harvest_record`, `harvest_discard` | `db/migrations/048_harvest_by_field.sql` |
| 049 | registros de fertilização | `db/migrations/049_fertilization_by_field.sql` |
| 050 | lançamentos de custo | `db/migrations/050_cost_by_field.sql` |
| 051 | vendas e recebíveis | `db/migrations/051_sales_receivables.sql` |
| 052 | estoque de insumos | `db/migrations/052_input_stock.sql` |

---

## 5. Documentação de regra existente

| Módulo | Documento canônico | Feature ID |
|---|---|---|
| Colheita por talhão | `docs/agro/HARVEST_BY_FIELD.md` | `F-HARV-001` |
| Adubação por talhão | `docs/agro/FERTILIZATION_BY_FIELD.md` | `F-FERT-001` |
| Custo por talhão | `docs/agro/COST_BY_FIELD.md` | `F-COST-001` |
| Vendas e recebíveis | `docs/agro/SALES_RECEIVABLES.md` | `F-SALE-001` |
| Estoque de insumos | `docs/agro/INPUT_STOCK.md` | `F-STOCK-001` |
| Relatório do contador | `docs/agro/ACCOUNTANT_REPORT.md` | `F-ACC-001` |
| Correções (UI única) | `docs/agro/CORRECTIONS_UI.md` | — |
| Soil Intelligence | `docs/agro/SOIL_INTELLIGENCE.md` | `F-SOIL-001` |
| Amostragem inteligente e zonas | `docs/agro/SMART_SOIL_SAMPLING.md` | `SMART_SOIL_SAMPLING` |
| Catálogo de features | `docs/product/FEATURE_CATALOG.md` | `F-SOIL-001`, `F-FIELD-001`, `F-MAPS-005` |

Regra de solo definida no repositório, citada em `src/ribeira_platform/soil.py`
e `docs/agro/SOIL_INTELLIGENCE.md`:

- Índices derivados determinísticos: SB (Soma de Bases), CTC, V%, m%
  (`compute_soil_derived_indices`, `src/ribeira_platform/soil.py:91`).
- Ausência de insumo **nunca** vira zero: índice sem dado fica `None`
  (`src/ribeira_platform/soil.py:124`).
- Satélite/modelo não é medição de laboratório/in-situ
  (`docs/agro/SOIL_INTELLIGENCE.md`).

---

## 6. UNKNOWN / PENDENTE-GABARITO

Os itens abaixo **não** estão definidos de forma completa no repositório e
ficam explicitamente marcados para decisão de negócio (gabarito). Nada foi
inventado.

1. **Identidade formal do produto "ERP"** — o termo "ERP da banana" aparece
   apenas como comentário em `frontend/src/pages/BananaManagementPage.tsx`.
   Não há documento canônico que defina o ERP como módulo de produto nomeado ou
   seu escopo oficial. Status: **UNKNOWN / PENDENTE-GABARITO**.
2. **Regras de negócio de precificação/custo unitário por talhão** — os campos
   existem (`unit_price_brl`, etc. em `frontend/src/api/sales.ts`), mas os
   critérios agronômicos/comerciais de quais valores são válidos não estão
   definidos em documento canônico. Status: **UNKNOWN / PENDENTE-GABARITO**.
3. **Critérios de amostragem de solo e densidade por talhão** — o fluxo
   conceitual existe em `docs/agro/SMART_SOIL_SAMPLING.md`, mas thresholds e
   a regra de seleção de zonas não estão definidos no repo. Status:
   **UNKNOWN / PENDENTE-GABARITO**.
4. **Vínculo oficial entre módulo de Solo e decisão/regra agronômica** — há
   índices derivados (`soil.py`), porém não há regra versionada canônica que
   transforme esses índices em decisão/recomendação. Status:
   **UNKNOWN / PENDENTE-GABARITO**.
5. **Pareamento resultado (margem/lucro) entre vendas e custos** — o relatório
   do contador explicitamente **não** calcula resultado nem margem
   (`docs/agro/ACCOUNTANT_REPORT.md`). A regra de apuração de resultado, se
   necessária, não está definida. Status: **UNKNOWN / PENDENTE-GABARITO**.
6. **Definição de "safra"/período de apuração** — não há modelo canônico de
   safra no repositório para agrupar os registros por talhão. Status:
   **UNKNOWN / PENDENTE-GABARITO**.
7. **Regra de representatividade/talhão obrigatório por módulo** — quais
   módulos exigem ou não `field_id` (talhão) não está consolidado em documento
   único; verificar por endpoint/tabela. Status: **UNKNOWN / PENDENTE-GABARITO**.
