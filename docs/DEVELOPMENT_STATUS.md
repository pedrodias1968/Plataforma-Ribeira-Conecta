# Status de Desenvolvimento — Ribeira Conecta Intelligence

**Data da Auditoria:** 25 de Setembro de 2026  
**Branch Atual:** `feat/phase-1f-quality-masked-temporal-delta`  
**Referência Canônica:** `docs/CODEX_AUTONOMOUS_DELIVERY.md`, `docs/PILOT_READINESS.md`, `docs/product/FEATURE_CATALOG.md`

---

## 1. Resumo Executivo da Auditoria

A plataforma Ribeira Conecta Intelligence encontra-se em estado funcional e estruturado, com uma base multi-tenant auditável, isolamento PostgreSQL RLS forçado, pipeline geoespacial PostGIS assíncrono e frontend React 19 / MapLibre GL.

### Indicadores de Qualidade e Integridade
- **Backend Unit Tests:** 151 aprovados (0 falhas).
- **Backend Integration Tests (PostgreSQL/PostGIS/RLS):** 41 aprovados, 2 skips controlados (CDSE externo).
- **Frontend Tests (Vitest):** 91 aprovados (29 suites, 0 falhas).
- **Frontend Typecheck (`tsc`) & Lint (`eslint`):** 0 erros.
- **Backend Linter (`ruff`) & Typecheck (`mypy`):** 0 erros em 54 arquivos fonte.
- **Migrations:** 46 migrations aplicadas sequencialmente sem falhas (`001_initial.sql` até `046_property_boundary_field_guard.sql`).
- **TODOs / FIXMEs no código ativo:** 0 pendências órfãs.

---

## 2. Onde o Desenvolvimento Parou

O último ciclo de desenvolvimento completou com sucesso a **Fase 1f (Quality-Masked Temporal Delta & Field Context)**:
- Vínculo imutável de talhões/campos (`field_context`) a propriedades com validação geométrica de contenção espacial e versionamento com rastreabilidade de correções (`045_field_boundary_correction_evidence`, `046_property_boundary_field_guard`).
- Execução de deltas temporais de NDVI com máscara de qualidade (SCL) recortados ao snapshot geométrico exato do talhão (`044_field_clipped_temporal_delta`).
- Avaliação de regras com escopo `FIELD` e persistência de contexto em decisões (`041_field_scoped_rules`, `043_field_decision_boundary_snapshot`).
- Proveniência e fechamento de resultados de ações pelo operador/produtor no Farm360 (`029_action_outcomes`, `e10b8ad feat(actions): expose result provenance`).

---

## 3. Classificação de Funcionalidades do Roadmap

| ID | Funcionalidade / Módulo | Status | Detalhes / Justificativa |
|---|---|---|---|
| **F-CORE-001** | Digital Twin / Maps / Farm360 (Propriedade e Ativos) | `COMPLETA` | Gestão de limites da propriedade (desenho, GeoJSON, KML/KMZ com aprovação), ativos físicos espaciais rastreáveis com proveniência e isolamento RLS. |
| **F-FIELD-001** | Contexto Operacional de Talhões / Campos | `COMPLETA` | Cadastro, desenho, validação de contenção espacial no servidor, versionamento imutável e correções de talhões. |
| **F-RULE-001** | Motor de Regras Escopadas, Decisões e Ações | `COMPLETA` | Regras escopadas (`GLOBAL`, `CUSTOMER`, `PROPERTY`, `ASSET`, `FIELD`), precedência determinística, avaliação sob demanda, registro de desfecho de ações. |
| **F-RS-001** | Catálogo Sentinel-2, Freshness e Índices | `PARCIAL` | Busca STAC CDSE, catálogo persistido, processamento assíncrono de NDVI, NDVI mascarado por qualidade e Delta temporal. Download S3 em tempo real de ativos CDSE aguarda credenciais de produção (`BLOCKED_BY_PROVIDER`). |
| **F-RS-002** | Par Registro Sentinel-1 V2 | `FOUNDATION` | Descoberta e pegada exata do par SAR de setembro de 2026 preservados. Processamento de raster SAR diferido conforme CODEX. |
| **F-FLOOD-001** | Inteligência de Inundações e Exposição | `COMPLETA` | Modelo factual Vale do Ribeira (Set 2026), hipóteses H1–H4 independentes, cálculo de exposição de propriedades/ativos implementado no backend (`030`). Visualização dedicada no frontend implementada com GET endpoint e FloodExposureAssessmentPanel. Avaliações de exposição são persistidas e listáveis com filtros por evento, tipo de sujeito, propriedade ou ativo. |
| **F-BUS-001** | Motor Comercial, Contratos e Simulação de Preços | `PARCIAL` | Entidades comerciais (clientes, contratos versionados, planos, simulação decimal de Capex/Opex/MRR) implementadas e testadas no backend. Interface visual de contratação planejada. |
| **F-TRACE-001** | Trilha de Auditoria e Proveniência | `COMPLETA` | Tabela imutável `audit_log`, logs estruturados, proveniência de dados brutos e derivados até o desfecho da ação. |
| **F-SOIL-001** | Soil Intelligence (Inteligência de Solo) | `PLANNED` | Especificações e ADRs concluídos (`docs/agro/SOIL_INTELLIGENCE.md`). Estrutura de dados de amostras de solo e análises laboratoriais em implementação. |
| **F-AGRO-001** | Adequação Agrícola (Land Suitability) | `PLANNED` | Módulo de terreno funcional (`terrain.py`). Regras agronômicas preliminares e políticas de aptidão da banana em planejamento. |
| **F-AGRO-003** | Amostragem Inteligente e Zonas de Manejo | `PLANNED` | Algoritmos de grade amostral e geração de zonas de manejo derivados de relevo e índices temporais planejados. |

---

## 4. Plano de Execução Priorizado

Objetivo: Avançar a plataforma operacionalmente, fortalecendo a cadeia de valor canônica:  
`asset -> data -> context -> rule -> decision -> action -> result`.

### Ciclo 1: Base de Inteligência de Solo e Amostragem (F-SOIL-001 & F-AGRO-003)
1. **Modelagem e Persistência de Dados de Solo:**
   - Amostras de solo georreferenciadas vinculadas a talhão/propriedade (`soil_sample_point`).
   - Resultados de análises laboratoriais rastreáveis com laboratório, data do laudo, parâmetros químicos/físicos (pH, matéria orgânica, fósforo, potássio, CTC, saturação por bases V%).
   - Proveniência obrigatória (distinção estrita entre `OBSERVED_LAB`, `INFERRED` e `MODELLED`).
2. **Migrations & Regras RLS:**
   - Criação da tabela e índices PostGIS com isolamento multi-tenant forçado.
3. **Serviço e Rotas de API:**
   - Endpoints para registro de pontos de amostragem e importação de laudos laboratoriais.
4. **Testes:**
   - Testes unitários e de integração PostgreSQL cobrindo validação de coordenadas dentro do talhão, imutabilidade e RLS.

### Ciclo 2: Avaliação de Adequação Agrícola e Regras de Solo para Banana (F-AGRO-001 / F-AGRO-002)
1. **Regras de Recomendação de Manejo do Solo:**
   - Calagem e adubação com escopo `FIELD` baseadas nos laudos e na cultura da banana no Vale do Ribeira.
2. **Integração com Motor de Decisões:**
   - Transformação dos laudos de solo em contexto para geração de decisões e ações rastreáveis.
3. **Frontend Farm360:**
   - Painel de Solo e Amostragem com visualização de pontos no mapa e laudos vinculados.

### Ciclo 3: Visualização e Exposição de Risco de Inundação no Farm360 (F-FLOOD-001)
1. **Exposição Visual do Evento de Inundação:**
   - Exibir avaliação de exposição a cheias no Farm360 com base nas zonas verificadas do evento de setembro de 2026.
   - Apresentar status das hipóteses H1–H4 de forma neutra e orientada a evidências.

---

## 5. Histórico de Alterações Recentes

| Data | Arquivos Alterados | Descrição |
|---|---|---|
| 2026-09-25 | `tests/integration/test_*.py` | Correção da ordem de fechamento do store no `tearDown()` para prevenir contenção de locks exclusivos durante exclusão de tenants de teste. |
| 2026-09-25 | `docs/DEVELOPMENT_STATUS.md` | Criação do documento oficial de status de desenvolvimento e auditoria completa do repositório. |
