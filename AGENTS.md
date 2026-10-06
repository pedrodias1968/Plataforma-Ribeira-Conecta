# Ribeira Conecta — Autonomous Delivery Rules

This file defines the mandatory operating rules for every AI coding agent,
autonomous development cycle, refactor, implementation, test, documentation
update and architectural change performed in this repository.

These rules are not suggestions.

They exist to keep Ribeira Conecta coherent while autonomous development
continues for long periods without direct human supervision.

---

# 1. Product Mission

Ribeira Conecta is an operational intelligence platform for rural properties,
agriculture, territorial intelligence, environmental context, flood
intelligence, Digital Twin, telemetry and decision support.

The platform must transform heterogeneous observations into traceable,
actionable operational intelligence.

The canonical product chain is:

```text
asset
  ->
data
  ->
context
  ->
rule
  ->
decision
  ->
action
  ->
result
```

Every meaningful platform capability should strengthen this chain or clearly
support one of its stages.

Do not build disconnected demonstrations.

Do not optimize for visual complexity, number of screens, number of features,
or apparent completion percentage.

Optimize for a usable, traceable and operational product.

---

# 2. Product Invariant

Before implementing a feature, ask:

```text
What asset does this concern?
What data supports it?
What context changes its interpretation?
Which rules apply?
What decision can result?
What action can follow?
How is the result observed?
```

A dashboard, map layer, model, integration, score, alert or visualization that
cannot participate in this operational chain must either:

1. have a clearly documented supporting purpose; or
2. expose its current limitation explicitly.

Do not create isolated functionality merely because it looks useful.

---

# 3. Priority Hierarchy

Development priority is determined by operational value and dependencies.

Default priority order:

1. correctness and data integrity
2. security and tenant isolation
3. pilot blockers
4. broken production-critical workflows
5. core operational workflows
6. evidence/provenance
7. shared architectural foundations
8. customer-facing functionality
9. flood intelligence and official hydrology integrations
10. geospatial and Digital Twin capabilities
11. agriculture and soil intelligence
12. integrations and telemetry
13. automation
14. usability improvements
15. performance improvements
16. parity / convenience features
17. cosmetic improvements

This ordering is contextual, not absolute.

A lower category may become more important when it blocks several higher-value
capabilities.

Do not prioritize a visually impressive map feature over a broken core
workflow, missing provenance, security defect, pilot blocker or critical data
problem.

---

# 4. Canonical Documentation

Before selecting substantial work, read:

```text
docs/CODEX_AUTONOMOUS_DELIVERY.md
docs/PILOT_READINESS.md
docs/README.md
```

Then inspect the canonical documents relevant to the task under:

```text
docs/product/
docs/requirements/
docs/geospatial/
docs/data/
docs/provenance/
docs/domain/
docs/rules/
docs/agro/
docs/iot/
docs/integrations/
docs/security/
docs/architecture/
docs/contracts/
docs/operations/
docs/pilot/
docs/business/
docs/commercial/
```

For any work involving Flood, Environment, Hydrology or Farm360 hydrological
context, Section 42 of this file is mandatory and the repository should also
preserve/update the canonical hydrology integration document under
`docs/integrations/` when present.

Do not create a new canonical document when an existing canonical document
already owns the subject.

Prefer updating existing documentation over creating competing sources of
truth.

Preserve historical decisions when relevant.

If a decision is superseded, mark it as superseded and explain applicability
instead of silently deleting historical evidence.

---

# 5. Evidence First

Never fabricate:

- observations
- sensor values
- satellite observations
- flood conditions
- rainfall
- river levels
- coverage
- contacts
- customer facts
- property facts
- asset facts
- diagnoses
- confidence
- provider availability
- data freshness
- business needs
- model results
- source reliability

Unknown information remains unknown.

Use the project's explicit scientific/evidence states where available.

Examples:

```text
UNKNOWN
INCONCLUSIVE
OBSERVED
INFERRED
MODELLED
CONFIRMED
```

Do not silently convert missing information into assumptions.

---

# 6. Provenance Is Mandatory

Externally sourced or derived information must preserve applicable provenance.

Record where relevant:

```text
provider
source
source identifier
reference/acquisition timestamp
ingestion timestamp
spatial resolution
temporal resolution
CRS
transformation
processing method
rule version
model version
confidence / quality
limitations
license / use constraints
scope
tenant
property
talhão
asset
```

Derived information must remain traceable to its inputs.

Never display derived information as raw observation.

---

# 7. Scientific and Agronomic Discipline

Satellite-derived information is not automatically an agronomic diagnosis.

Remote sensing may provide evidence such as:

```text
vegetation condition
spectral changes
possible stress
moisture-related indicators
surface changes
temporal anomalies
```

It must not be silently presented as:

```text
confirmed disease
confirmed nutrient deficiency
confirmed pest
confirmed soil diagnosis
```

unless supporting evidence permits that conclusion.

Expose uncertainty and limitations.

---

# 8. Flood Intelligence Discipline

Flood analysis must separate distinct evidence classes.

Where applicable, represent separately:

```text
rainfall
upstream rainfall
river level
reservoir level
reservoir operations
dam/gate operations
soil saturation
terrain
basin characteristics
river geometry
historical events
ENSO / climate context
observed flooding
forecast information
```

Temporal association is not proof of causality.

Do not transform correlation into a causal statement without sufficient
evidence.

Causal hypotheses require explicit evidence states.

Provider restrictions are source-specific and must remain authoritative.

Do not conflate SAISP with the SP Águas SIBH public API. They are distinct
integration paths with different authorization states.

Current hydrology states are:

```text
SAISP automation:
NOT_APPROVED_FOR_AUTOMATION
FAIL_CLOSED

SP ÁGUAS SIBH:
STATUS=OFFICIAL_PUBLIC_API_AVAILABLE
AUTH=NONE
AUTOMATION=RECOMMENDED_BY_PROVIDER

ANA HIDROWEBSERVICE:
STATUS=ACCESS_APPROVED
AUTH=REQUIRED
AUTH_ROUTE=/EstacoesTelemetricas/OAUth/v1
AUTH_HEADERS=Identificador,Senha
AUTH_SCHEME=Bearer
DECLARED_TOKEN_TTL=60_MINUTES
TOKEN_REUSE=REQUIRED
HIGH_FREQUENCY_REAUTH=FORBIDDEN
BASE_URL=https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas
AUTOMATION=SUPPORTED
SECRETS=PROTECTED_RUNTIME_CONFIG_ONLY
OFFICIAL_MANUAL_VERSION=20.02.2026
```

Do not silently bypass these restrictions.

For Flood, Environment, Hydrology or Farm360 hydrological context work, the
official integration rules in Section 42 are mandatory.

When implementing ANA integration, the official HidroWebService manual version
20.02.2026 and the current ANA Swagger are provider-contract references. If they
conflict, preserve the discrepancy, validate the live contract safely, and
document the observed behavior instead of guessing.

---

# 9. Geospatial Capability Invariant

Ribeira Conecta is NOT a Google Earth clone.

Google Earth is a capability reference for the geospatial experience, not the
identity of the product and not an implementation dependency.

The primary product mission remains:

```text
asset -> data -> context -> rule -> decision -> action -> result
```

However, Ribeira Conecta must progressively provide the relevant capabilities
users expect from a Google-Earth-class geospatial workspace when those
capabilities support the product.

This requirement is mandatory.

It must not replace the operational product roadmap.

---

# 10. Google-Earth-Class Capability Target

The geospatial workspace should progressively support applicable capabilities
including:

## Navigation

- 2D map
- 3D globe
- pan
- zoom
- rotation
- tilt / pitch
- fly-to navigation
- coordinate display
- scale
- fullscreen
- terrain visualization

## Geometry

- Point
- LineString
- Polygon
- MultiPolygon
- property boundaries
- talhões
- operational assets
- infrastructure
- editable geometry
- geometry validation

## Measurements

- distance
- perimeter
- area
- elevation
- elevation profile
- slope where supported

## Terrain

- DEM
- terrain rendering
- altitude
- minimum elevation
- maximum elevation
- mean elevation
- contours
- slope
- aspect
- flow-related terrain analysis where applicable

## Layer management

- enable / disable
- opacity
- ordering
- styling
- legends
- filtering
- system layers
- customer layers
- user-created layers
- source metadata
- temporal metadata

## Search and navigation

- coordinates
- address when provider permits
- municipality
- locality
- property
- customer asset
- geographic feature
- applicable points of interest

## Import / export

- KML
- KMZ
- GeoJSON where useful
- geometry metadata
- style metadata when practical
- validation
- malformed-file handling
- provenance

## Temporal exploration

- imagery/reference date
- historical comparison
- timeline
- temporal layers
- before/after comparisons
- observed changes
- flood-event comparison
- land-cover changes
- vegetation changes where supported

## Satellite and imagery

- usable imagery layers
- acquisition/reference date
- provider
- resolution
- quality information
- cloud information where available
- latest usable observation
- historical imagery where permitted
- automated refresh according to provider availability

## Digital Twin

- property
- talhões
- terrain
- buildings
- roads
- internal infrastructure
- waterways
- drainage
- vegetation
- sensors
- operational assets
- risk zones
- business context
- telemetry overlays
- event overlays

---

# 11. KML Is Optional Input, Not a Dependency

A customer may already have a KML/KMZ created using Google Earth or another
geospatial tool.

Ribeira Conecta should support importing it where applicable.

However:

```text
KML/KMZ MUST NOT be required to use the platform.
```

The platform must also allow users to:

- locate an area
- create a property directly
- draw property boundaries
- edit boundaries
- create talhões
- add points
- add lines
- create assets
- create operational layers
- enrich the Digital Twin

without requiring an external KML file.

Where technically reliable and permitted by the data source, the platform may
assist in generating or suggesting geospatial layers automatically.

Automatic generation must expose uncertainty and must not invent boundaries or
facts.

---

# 12. Google Earth Comparison Discipline

When evaluating a Google Earth capability, classify it using an explicit state
when appropriate:

```text
IMPLEMENT_DIRECTLY
IMPLEMENT_EQUIVALENT
ALREADY_COVERED_BY_RIBEIRA
PLANNED
BLOCKED_BY_DATA
BLOCKED_BY_LICENSE
BLOCKED_BY_PROVIDER
BLOCKED_BY_TECHNOLOGY
NOT_RELEVANT_TO_PRODUCT
```

Do not silently discard relevant capabilities.

Do not create low-value parity work only to increase a feature count.

Do not call geospatial parity complete merely because a 3D globe is displayed.

A visual shell is not a completed capability.

---

# 13. Proprietary Data and Licensing

Never assume that Google-owned or other proprietary assets may be copied,
scraped, redistributed or embedded.

Examples include potentially restricted:

```text
imagery
Street View-like imagery
photogrammetry
3D building assets
terrain products
tiles
proprietary APIs
licensed datasets
```

Use:

- public datasets
- open datasets
- customer-provided datasets
- properly licensed commercial datasets
- officially permitted APIs

when available.

When exact parity depends on unavailable proprietary data, implement an
equivalent workflow where technically and legally appropriate and document the
difference.

---

# 14. Freshness and Satellite Data

Do not interpret "latest imagery" as invented real-time imagery.

"Latest" means:

```text
the latest usable observation available from configured and permitted sources
```

Every imagery-derived layer should expose applicable:

```text
source
acquisition/reference date
ingestion date
resolution
quality
cloud conditions
processing
limitations
```

Prefer automatic refresh where provider access, cost, licensing and operational
constraints permit.

---

# 15. Architecture

Production spatial storage remains PostgreSQL/PostGIS unless an explicitly
approved architecture decision changes it.

Preserve:

- tenant isolation
- forced RLS
- least privilege
- migration integrity
- immutable migration checksums
- explicit contracts
- audit history
- bounded integrations
- provenance
- scoped rules

Do not introduce shadow data stores that silently become alternate sources of
truth.

---

# 16. Tenant Isolation

Every new feature must consider tenant isolation.

Never assume:

```text
tenant A may access tenant B
customer A may access customer B
property A may access property B
```

RLS and application-level authorization must remain aligned.

Never solve development friction by disabling tenant protections.

---

# 17. Rules Engine Discipline

Rules are:

```text
versioned
scoped
traceable
auditable
```

Never silently apply a global rule to a:

- tenant
- customer
- property
- talhão
- sensor
- asset

unless that scope is explicitly intended.

Every important decision generated from rules must be traceable to the rule
version and relevant inputs.

---

# 18. External Integrations

External adapters must be:

- provider-specific
- bounded
- allowlisted where appropriate
- timeout-controlled
- failure-aware
- observable
- fail-closed where required

Never put:

- API keys
- credentials
- OAuth tokens
- passwords
- private keys
- provider secrets

inside source code or browser bundles.

---

# 19. Current Operational Restrictions

Do not bypass explicit operator decisions.

Current known constraints include:

```text
Cloudflare:
AUTHORIZED_FOR_PILOT_ACCESS
named tunnel:
https://app.ribeiraconecta.com.br

Historical Quick Tunnel origins:
OBSOLETE

PostgreSQL:
PRIVATE

metrics:
PRIVATE

debug services:
PRIVATE

development services:
PRIVATE

SAISP automation:
NOT_APPROVED_FOR_AUTOMATION
FAIL_CLOSED

SP ÁGUAS SIBH:
OFFICIAL_PUBLIC_API_AVAILABLE
AUTH=NONE
AUTOMATION=RECOMMENDED_BY_PROVIDER

ANA HIDROWEBSERVICE:
ACCESS_APPROVED
AUTH=REQUIRED
AUTH_ROUTE=/EstacoesTelemetricas/OAUth/v1
AUTH_SCHEME=Bearer
DECLARED_TOKEN_TTL=60_MINUTES
TOKEN_REUSE=REQUIRED
HIGH_FREQUENCY_REAUTH=FORBIDDEN
BASE_URL=https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas
AUTOMATION=SUPPORTED
SECRETS=PROTECTED_RUNTIME_CONFIG_ONLY
OFFICIAL_MANUAL_VERSION=20.02.2026
```

If canonical documentation changes one of these states, follow the newer
explicit documented decision.

---

# 20. Autonomous Development Objective

The autonomous agent exists to move Ribeira Conecta toward a genuinely usable,
tested and deployable platform.

It must NOT optimize for:

- number of commits
- number of generated files
- number of TODOs closed
- visual feature count
- superficial percentage completion
- artificial roadmap progress

The objective is functional delivery.

Never reduce requirements merely to make completion appear higher.

---

# 21. Autonomous Cycle

Before each development cycle:

1. inspect repository status
2. inspect branch
3. read canonical autonomous-delivery guidance
4. inspect relevant documentation
5. inspect recent commits
6. inspect unresolved work
7. identify the highest-impact unblocked task
8. understand dependencies
9. implement the smallest coherent increment
10. run relevant validation
11. review the diff
12. update documentation/state if necessary
13. commit coherent verified work
14. push
15. select the next task

Do not blindly repeat the same action after failure.

---

# 22. Task Selection

Prefer tasks that:

- unblock multiple capabilities
- close pilot blockers
- fix broken workflows
- strengthen shared foundations
- reduce operational risk
- improve traceability
- connect isolated functionality into the operational chain
- turn prototypes into usable workflows
- add tests to unstable critical areas

Avoid spending autonomous cycles polishing low-value UI while higher-impact
work remains blocked.

---

# 23. Definition of Done

A capability is NOT complete merely because code exists.

Use states such as:

```text
NOT_STARTED
PLANNED
IN_PROGRESS
IMPLEMENTED
INTEGRATED
TESTED
VERIFIED
BLOCKED
```

`IMPLEMENTED` is not equivalent to `VERIFIED`.

A major capability is complete only when applicable requirements are covered:

- implementation
- integration
- persistence
- security
- provenance
- user workflow
- failure handling
- tests
- documentation
- operational assumptions
- limitations

---

# 24. Testing Discipline

Before committing, run the relevant subset of:

```text
unit tests
integration tests
contract tests
database tests
geospatial tests
security tests
lint
format checks
type checks
build
smoke tests
secret checks
```

Do not run expensive unrelated suites unnecessarily after every tiny change.

Before declaring a major milestone complete, run broader validation.

Never knowingly commit a broken build as completed work.

---

# 25. Failure Handling

Classify failures before retrying.

## Code failure

Investigate and fix.

## Test failure

Determine whether:

```text
implementation is wrong
test is wrong
environment is wrong
fixture is wrong
contract changed
```

Do not blindly weaken tests.

## Temporary provider/network failure

Retry with bounded exponential backoff.

## Rate limit / quota exhaustion

Do not retry every few seconds forever.

Pause appropriately or use an approved fallback route.

## Authentication failure

Stop repeated attempts and surface the issue.

## Git conflict

Stop automatic destructive operations.

Inspect carefully.

## Production health failure

Keep or restore the known-good version.

---

# 26. Git Discipline

Before changes:

```text
git status
git branch --show-current
```

Never:

- force-push
- rewrite published history
- delete unrelated work
- silently discard user changes
- commit secrets
- push directly to main unless explicitly authorized by repository policy

Prefer small coherent commits.

Examples:

```text
feat(geo): add KML property import validation

feat(flood): add river observation provenance

fix(api): enforce tenant scope on property query

test(geo): cover invalid polygon geometry

docs(data): document satellite acquisition metadata
```

---

# 27. Commit Discipline

A commit should represent one coherent increment.

Do not create meaningless commits such as:

```text
updates
changes
fix stuff
more work
misc
```

The commit should explain what changed.

Only commit when the repository is in a coherent state.

---

# 28. Push Discipline

Commit and push coherent source increments frequently enough to avoid losing
work.

Source delivery and production promotion are separate operations.

A pushed commit does not imply production deployment.

---

# 29. Production Promotion

Promote frontend or backend releases only after applicable checks pass.

For production-facing changes:

1. protected configuration exists
2. relevant tests pass
3. production build succeeds
4. isolated candidate smoke test succeeds
5. promotion occurs
6. post-promotion health check succeeds

If candidate or production health validation fails:

```text
retain or restore known-good release
```

Never knowingly replace a healthy release with a failing build.

---

# 30. Documentation Discipline

A major capability is not complete until its applicable documentation exists.

Document:

- purpose
- workflow
- business rules
- sources
- provenance
- architecture
- security assumptions
- integration behavior
- operational requirements
- known limitations
- tests

If documentation cannot be completed in the same increment, record explicit
documentation debt in the appropriate canonical catalogue.

---

# 31. Digital Twin Discipline

Digital Twin is not merely a 3D visualization.

It should progressively connect:

```text
property
terrain
talhões
infrastructure
water
vegetation
sensors
telemetry
events
rules
risk
decisions
actions
results
```

A Digital Twin object should participate in the operational model whenever
possible.

---

# 32. UI / UX Discipline

User interfaces should expose meaning, not merely data.

Prefer workflows such as:

```text
What happened?
Where?
When?
What evidence supports it?
How certain is it?
Which asset is affected?
Which rule applies?
What action is recommended or required?
What happened after the action?
```

Avoid dashboards consisting only of disconnected counters.

---

# 33. Performance

Geospatial and telemetry workloads must avoid unnecessary full-dataset
transfers.

Prefer where applicable:

- spatial indexes
- viewport queries
- pagination
- tiled rendering
- LOD
- progressive loading
- caching
- bounded queries
- background processing
- precomputation when justified

Do not optimize prematurely at the expense of correctness.

---

# 34. No Fake Completion

Never create fake implementations to satisfy a checklist.

Examples of unacceptable completion:

```text
button exists but does nothing
map control exists without implementation
mock data presented as real
placeholder API treated as integrated
hardcoded success state
empty test that always passes
visual KML button without actual parsing
3D globe counted as complete Digital Twin
```

If functionality is partial, mark it partial.

---

# 35. Preserve Existing Valid Work

Do not rewrite functioning subsystems without a concrete reason.

Before major refactors:

1. understand existing behavior
2. identify the actual problem
3. preserve contracts where possible
4. add tests around critical behavior
5. migrate incrementally

Prefer root-cause fixes over broad rewrites.

---

# 36. Security Stop Conditions

Stop autonomous changes and surface the problem if work would require:

- exposing credentials
- weakening RLS
- disabling authentication
- opening private databases publicly
- making debug services public
- bypassing tenant isolation
- committing secrets
- bypassing an explicit fail-closed integration restriction

Do not "temporarily" weaken these protections merely to make a test pass.

---

# 37. Human Decisions

Do not override explicit human product or operational decisions.

If documentation contains conflicting decisions:

1. identify the conflict
2. determine the newest applicable canonical decision if possible
3. preserve evidence
4. avoid silently choosing an irreversible interpretation

When materially ambiguous and high-risk, stop that specific path and continue
other unblocked work where possible.

---

# 38. Continuous Autonomous Operation

The agent may continue through multiple development cycles without waiting for
human approval when:

- the task is within documented scope
- requirements are sufficiently clear
- the change is reversible through Git
- security invariants remain intact
- tests can validate the result

Do not stop merely because one milestone or one invocation ended.

Continue with the next highest-value unblocked task.

---

# 39. Autonomous Stop Conditions

Stop the autonomous delivery loop only when one of these applies:

```text
project completion criteria are satisfied
critical human decision is required
security boundary blocks safe progress
credentials/authorization are required
repository state cannot be reconciled safely
all meaningful remaining work is externally blocked
operator-defined stop marker is present
```

Do NOT create a stop marker simply because:

- one task finished
- one feature finished
- one commit was pushed
- one invocation ended
- progress is temporarily difficult

---

# 40. Completion Claim

Do not claim Ribeira Conecta is complete based on a percentage alone.

A credible completion assessment should consider:

```text
requirements coverage
operational workflows
pilot readiness
data integrations
geospatial capability
Digital Twin
flood intelligence
agriculture
security
tenant isolation
provenance
tests
deployment
documentation
known blockers
```

If progress percentages are maintained, they must be evidence-backed.

Never inflate progress by subdividing trivial tasks or lowering acceptance
criteria.

---

# 41. Final Operating Principle

When choosing between:

```text
more features
```

and:

```text
a smaller number of features that are integrated, traceable, tested,
operational and useful
```

choose the second.

Ribeira Conecta must become a dependable operational intelligence platform,
not a collection of demos.

Google-Earth-class geospatial capability is an important mandatory platform
capability.

It is not the product's sole purpose.

Always preserve the canonical operational chain:

```text
asset -> data -> context -> rule -> decision -> action -> result
```

---

# 42. Official Hydrology Integration — SP Águas SIBH + ANA HidroWebService

This section is mandatory for autonomous work involving Hydrology, Flood,
Environment, Farm360 hydrological context, official river/rainfall/flow data,
or hydrological provider integration.

It supersedes older assumptions that ANA access is still pending. It does NOT
change the independent SAISP fail-closed restriction. SP Águas SIBH and SAISP
must never be treated as the same provider/integration path.

The following rules are incorporated from the approved hydrology integration
specification and are part of this AGENTS.md contract.

**Status:** PRIORIDADE ALTA  
**Implementação:** Pendente / em andamento  
**Princípio:** Evidence First

### 1. Objetivo

Integrar à Ribeira Conecta fontes hidrológicas oficiais para monitoramento contínuo do Vale do Ribeira, com foco em:

- pluviometria;
- nível de rios;
- vazão;
- histórico hidrológico;
- acompanhamento em tempo real ou próximo do tempo real;
- contexto para risco de inundação;
- integração com Farm360, Flood/Environment, regras, alertas e relatórios.

A arquitetura deve ser provider-neutral e preservar integralmente a proveniência dos dados.

A ausência de dados nunca deve ser substituída por estimativa não identificada.

### 2. SP Águas — SIBH

A SP Águas confirmou oficialmente a existência de API pública para consulta dos dados disponibilizados no Sistema Integrado de Bacias Hidrográficas — SIBH.

#### 2.1 Endpoints oficiais

Estações:

```text
https://apps.spaguas.sp.gov.br/sibh/api/v2/stations
```

Medições:

```text
https://apps.spaguas.sp.gov.br/sibh/api/v2/measurements
```

#### 2.2 Parâmetros informados pela SP Águas

```text
start_date
end_date
group_type
station_prefixes_ids
format
```

`group_type`:

```text
minute
hour
day
month
```

`format`:

```text
json
csv
```

#### 2.3 Tipos de dados

Conforme estação e disponibilidade:

- pluviometria / chuva;
- fluviometria / nível;
- vazão.

#### 2.4 Autenticação

Segundo resposta oficial recebida da SP Águas, atualmente a API é pública e não exige usuário, senha, token ou credenciamento prévio.

#### 2.5 Uso automatizado

A SP Águas recomenda prioritariamente a utilização dos endpoints do SIBH para integração e obtenção periódica dos dados.

Consultas automatizadas devem ser realizadas de maneira responsável, evitando volume excessivo de requisições e polling desnecessariamente curto.

A Ribeira Conecta deve determinar a cadência real das estações antes de definir a frequência final de ingestão.

### 3. Validação obrigatória dos parâmetros de data

A resposta recebida da SP Águas descreveu:

```text
start_date - fim da série
end_date - começo da série
```

Essa descrição parece semanticamente invertida.

A implementação NÃO deve corrigir, inverter ou assumir comportamento sem validação.

Antes de definir o contrato canônico do adapter, testar empiricamente:

```text
start_date < end_date
start_date > end_date
```

Também validar:

- formato aceito de data/hora;
- timezone;
- inclusividade de início/fim;
- ordenação da resposta;
- paginação;
- limites máximos de intervalo;
- comportamento sem dados;
- comportamento com estação inválida;
- comportamento com múltiplas estações;
- diferenças entre JSON e CSV.

O comportamento verificado deve ser registrado na documentação técnica e em testes de contrato.

### 4. Estações do Vale do Ribeira

A SP Águas forneceu arquivo CSV com IDs/códigos das estações de pluviometria e fluviometria da região do Vale do Ribeira / UGRHI 11.

Quando esse arquivo estiver disponível no ambiente do projeto, ele deve ser importado por fluxo controlado e com proveniência.

Nunca fabricar IDs, códigos ou nomes de estação.

Persistir, quando fornecido:

```text
provider_station_id
station_code
station_name
station_type
river
basin
sub_basin
latitude
longitude
municipality
status
source
retrieved_at
raw_metadata
```

A importação deve ser idempotente.

### 5. Provider SP Águas

Implementar provider separado:

```text
SPAguaSIBHProvider
```

O provider deve ficar atrás da arquitetura provider-neutral de Hydrology / Environment.

Responsabilidades:

- listagem de estações;
- consulta de medições;
- ingestão de chuva;
- ingestão de nível;
- ingestão de vazão;
- normalização de unidade;
- preservação do payload/referência original;
- persistência;
- histórico;
- deduplicação;
- idempotência;
- atualização incremental;
- monitoramento de freshness;
- retry/backoff;
- classificação de falha do provider.

### 6. Modelo canônico de observação hidrológica

Cada observação normalizada deve preservar no mínimo:

```text
provider
provider_station_id
station_id
metric_type
value
unit
observed_at
received_at
ingested_at
quality
status
source_reference
raw_reference
provenance
```

Tipos mínimos de métrica:

```text
RAINFALL
RIVER_LEVEL
FLOW
```

Os tipos devem permanecer semanticamente distintos.

Nunca inferir nível → vazão ou vazão → nível sem curva-chave, modelo ou metodologia científica explicitamente registrada e versionada.

### 7. Semântica Evidence First

Estados mínimos:

```text
OBSERVED
OFFICIAL_SOURCE
CALCULATED
DERIVED
UNKNOWN
CONFLICTING
```

Sem medição:

```text
UNKNOWN
```

Fonte indisponível:

```text
SOURCE_UNAVAILABLE
```

Providers oficiais divergentes de maneira relevante:

```text
CONFLICTING
```

Nunca preencher lacunas com valor fabricado.

### 8. Ingestão automática

Integrar o SIBH ao scheduler e aos durable jobs existentes.

Fluxo canônico:

```text
provider/station
→ busca incremental
→ valida resposta
→ normaliza
→ deduplica
→ persiste observações
→ atualiza freshness
→ atualiza contexto hidrológico
→ disponibiliza Farm360/Flood
```

Persistir por provider/estação:

```text
last_attempt_at
last_success_at
latest_observation_at
next_refresh_at
provider_error
retry_state
consecutive_failures
```

A frequência deve considerar cadência real da estação, frequência de transmissão, criticidade operacional e uso responsável da API.

Não utilizar polling agressivo sem justificativa.

### 9. Relação estação ↔ propriedade

A Ribeira Conecta deve identificar quais estações são aplicáveis a uma propriedade.

Não assumir automaticamente:

```text
estação mais próxima = estação representativa
```

A seleção pode considerar:

- distância;
- bacia;
- sub-bacia;
- rio associado;
- montante/jusante;
- disponibilidade da métrica;
- freshness;
- qualidade;
- cobertura temporal;
- contexto topográfico/hidrológico.

Persistir:

```text
property_id
station_id
relationship_type
distance
selection_reason
limitations
source
confirmed_at
```

### 10. Flood / Environment

Usar observações reais para construir contexto de:

- chuva;
- nível;
- vazão;
- tendência temporal;
- eventos hidrológicos;
- exposição da propriedade;
- exposição de ativos;
- regras;
- alertas;
- ações;
- resultados.

Cadeia canônica:

```text
observação
→ contexto
→ regra/modelo
→ avaliação
→ decisão
→ ação
→ resultado
```

Nunca promover correlação temporal automaticamente para causalidade.

### 11. ANA — HidroWebService

O acesso da Ribeira Conecta ao HidroWebService foi aprovado pela ANA.

A integração deve seguir o manual oficial:

```text
Tutorial de Serviço para Consumo de Dados — API HidroWebService
Versão 20.02.2026
```

Swagger informado no manual:

```text
https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html
```

Base URL usada no exemplo oficial de automação:

```text
https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas
```

Implementar provider separado:

```text
ANAHidroWebProvider
```

#### 11.1 Segurança

As credenciais da ANA são privadas.

Nunca:

- colocar identificador, senha ou token no Git;
- colocar senha/token na documentação;
- colocar senha/token no AGENTS.md;
- imprimir senha/token em logs;
- colocar senha/token em prompt;
- armazenar segredo no frontend;
- incluir segredo em fixtures.

Usar exclusivamente configuração protegida de runtime, por exemplo:

```text
/home/ribeira/.config/ribeira/
```

com permissões restritas.

O identificador de acesso é cadastrado junto à ANA e pode corresponder ao CPF ou
CNPJ autorizado. Não registrar o valor real do identificador neste arquivo.

#### 11.2 Contrato de autenticação oficial

Rota de autenticação:

```text
GET /EstacoesTelemetricas/OAUth/v1
```

O exemplo oficial envia as credenciais nos headers:

```text
Identificador: <protected-runtime-value>
Senha: <protected-runtime-value>
```

A resposta fornece `tokenautenticacao`, que deve ser usado nas consultas:

```text
Authorization: Bearer <tokenautenticacao>
```

O texto normativo do manual declara validade de:

```text
60 minutos
```

A aplicação deve gerenciar o ciclo de vida e reutilizar o token enquanto válido.
Não autenticar novamente antes de cada consulta/job.

Autenticações em alta frequência são explicitamente desaconselhadas pela ANA e
podem levar ao bloqueio automático do IP. Portanto:

```text
TOKEN_CACHE=REQUIRED
TOKEN_REUSE=REQUIRED
HIGH_FREQUENCY_REAUTH=FORBIDDEN
REFRESH_BEFORE_EXPIRY=BOUNDED_CONFIGURABLE_MARGIN
```

Há uma inconsistência documentada que deve ser preservada: o texto principal do
manual declara 60 minutos de validade, enquanto o exemplo Java do Anexo III
implementa uma verificação conservadora de 15 minutos. O provider não deve
silenciosamente redefinir o contrato para 15 minutos.

Regra de implementação:

- tratar 60 minutos como a validade declarada pelo manual;
- usar margem conservadora configurável para renovação;
- validar o comportamento real em contract tests;
- registrar qualquer divergência observada da API;
- nunca criar loop de reautenticação.

#### 11.3 Rotas oficiais prioritárias

Inventário de estações:

```text
GET /EstacoesTelemetricas/HidroInventarioEstacoes/v1
```

Série telemétrica adotada:

```text
GET /EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v1
```

O tutorial também demonstra uma rota de série telemétrica detalhada com
nomenclatura diferente no Swagger. Como o manual apresenta mais de uma forma de
nomear essa rota, o adapter deve validar o path real no Swagger/serviço antes de
hardcodá-lo em produção.

Não inventar rotas a partir de nomes aproximados.

#### 11.4 Semântica da série telemétrica adotada

O manual exemplifica os campos:

```text
Chuva_Adotada
Chuva_Adotada_Status
Cota_Adotada
Cota_Adotada_Status
Vazao_Adotada
Vazao_Adotada_Status
Data_Atualizacao
Data_Hora_Medicao
codigoestacao
```

Semântica informada:

```text
Chuva_Adotada = precipitação em mm
Cota_Adotada = cota em cm
Vazao_Adotada = vazão em m3/s
*_Status: 0=ok, 1=suspeito, 2=ruim
Data_Hora_Medicao = momento da medição/coleta
Data_Atualizacao = atualização do dado na base ANA
```

Mapeamento para o modelo canônico, preservando sempre os campos/raw payload
originais:

```text
Chuva_Adotada -> RAINFALL
Cota_Adotada -> RIVER_LEVEL
Vazao_Adotada -> FLOW
Data_Hora_Medicao -> observed_at
Data_Atualizacao -> provider_updated_at
codigoestacao -> provider_station_id
```

O status de qualidade da ANA deve ser persistido. Dado `suspeito` ou `ruim` não
deve ser silenciosamente tratado como observação de qualidade normal.

#### 11.5 Inventário ANA

A rota `HidroInventarioEstacoes` pode fornecer, entre outros campos:

```text
codigoestacao
Estacao_Nome
Latitude
Longitude
Municipio_Codigo
Municipio_Nome
Operadora_Codigo
Operadora_Sigla
Responsavel_Sigla
UF_Estacao
UF_Nome_Estacao
codigobacia
Operando
Tipo_Estacao
Altitude
Area_Drenagem
Bacia_Nome
Data_Ultima_Atualizacao
```

Preservar metadados adicionais no `raw_metadata` quando não houver coluna
canônica específica.

`Operando=1` no exemplo do manual representa estação ativa, mas o adapter deve
preservar o valor original e validar demais estados observados antes de criar
enumeração fechada.

#### 11.6 Consultas e filtros

O manual exige campos obrigatórios conforme a rota, incluindo código da estação
e data de busca em consultas de série.

O exemplo de automação usa:

```text
CodigoDaEstacao=<codigo>
TipoFiltroData=DATA_LEITURA
RangeIntervaloDeBusca=DIAS_30
```

Esses valores demonstram o contrato do exemplo oficial, mas não autorizam a
invenção de valores adicionais. Enumerations e limites devem ser validados no
Swagger/serviço e cobertos por contract tests.

#### 11.7 Falhas e comportamento operacional

O provider ANA deve:

- diferenciar falha de autenticação, autorização, validação, ausência de dados e
  erro de servidor;
- não converter resposta vazia em observação zero;
- usar retry/backoff somente para falhas transitórias;
- renovar token quando expirado ou próximo da expiração, de forma bounded;
- nunca registrar credenciais/token em exception messages;
- preservar histórico já ingerido quando a ANA estiver indisponível;
- não derrubar Farm360/Flood por indisponibilidade temporária do provider;
- manter observabilidade de `last_attempt_at`, `last_success_at`,
  `latest_observation_at`, `provider_error` e `consecutive_failures`.

#### 11.8 Contract tests obrigatórios para ANA

Adicionar testes para:

- autenticação com configuração protegida;
- parsing do `tokenautenticacao`;
- reutilização/caching de token;
- renovação bounded antes/depois da expiração;
- proteção contra reautenticação por request;
- tratamento da divergência documental 60 min vs exemplo 15 min;
- Bearer token nas consultas;
- inventário de estações;
- série telemétrica adotada;
- parsing de chuva/cota/vazão;
- unidades;
- QC `0/1/2`;
- timestamps de medição e atualização;
- resposta vazia;
- estação inválida;
- falhas 4xx/5xx;
- retry/backoff;
- secret redaction em logs;
- idempotência e deduplicação;
- provenance;
- tenant isolation/RLS onde o dado for associado ao contexto de tenant.

Fixtures ANA só podem existir em testes e devem ser explicitamente sintéticas.
Nunca usar exemplos do manual como dado real de produção.

### 12. Providers independentes

SP Águas e ANA devem permanecer providers distintos.

#### SP Águas / SIBH

Uso principal esperado:

- operação regional;
- Vale do Ribeira;
- chuva;
- nível;
- vazão;
- telemetria próxima do tempo real.

#### ANA / HidroWebService

Uso esperado:

- inventário nacional;
- séries históricas;
- telemetria complementar;
- redundância;
- contexto hidrológico nacional.

Uma fonte não substitui automaticamente a outra.

### 13. Correlação entre providers

A mesma estação física pode eventualmente aparecer em mais de uma rede ou base.

Não deduplicar exclusivamente por:

- nome semelhante;
- coordenadas próximas;
- rio semelhante.

Criar correlação explícita apenas quando houver evidência suficiente.

Persistir mapeamento:

```text
canonical_station_id
provider
provider_station_id
mapping_evidence
mapping_status
confirmed_at
```

### 14. Farm360 — Hidrologia

Quando existirem dados reais aplicáveis à propriedade, o Farm360 deve apresentar uma seção de Hidrologia.

#### 14.1 Chuva

Exibir:

- última observação;
- acumulado quando cientificamente válido;
- estação;
- fonte;
- timestamp;
- freshness;
- qualidade.

#### 14.2 Nível do rio

Exibir:

- última observação;
- estação;
- rio;
- fonte;
- timestamp;
- freshness;
- tendência quando derivada corretamente.

#### 14.3 Vazão

Exibir quando disponível:

- valor;
- unidade;
- estação;
- timestamp;
- fonte;
- freshness.

#### 14.4 Séries

Disponibilizar:

```text
24h
7d
30d
janela de evento
histórico
```

Não gerar histórico sintético.

### 15. Caso de validação — Vale do Ribeira / setembro de 2026

Utilizar o evento de setembro de 2026 como caso real de validação quando houver observações oficiais disponíveis.

Janela de referência já utilizada no projeto:

```text
2026-09-11T10:59:10Z
até
2026-09-14T20:00:00Z
```

Hipóteses permanecem independentes:

```text
H1 — chuva local
H2 — chuva a montante
H3 — reservatório / Capivari
H4 — contexto ENSO
```

Nenhuma hipótese deve ser promovida automaticamente para causalidade confirmada.

Resultado científico permitido:

```text
UNKNOWN
INCONCLUSIVE
PARTIALLY_SUPPORTED
SUPPORTED
```

conforme evidências efetivamente disponíveis.

### 16. Integração com regras

Regras hidrológicas devem ser versionadas.

Exemplo conceitual:

```text
observação oficial
→ contexto
→ regra versionada
→ decisão
```

Toda regra deve registrar:

- versão;
- parâmetros;
- fonte dos dados;
- período considerado;
- condição;
- resultado;
- limitações.

Não inserir thresholds arbitrários em produção sem aprovação/documentação.

### 17. Alertas

Alertas podem ser gerados somente quando houver regra/configuração aplicável.

Exemplos futuros:

- chuva acumulada elevada;
- elevação rápida do nível;
- nível acima de threshold;
- perda de telemetria;
- estação sem atualização;
- combinação de evidências.

Alertas devem apontar para a observação e regra que os originaram.

### 18. Freshness

Cada informação hidrológica deve apresentar freshness.

Persistir:

```text
observed_at
received_at
ingested_at
latest_available_at
latest_processed_at
```

A UI deve distinguir:

```text
Última observação
Última atualização da plataforma
Fonte indisponível
Dado desatualizado
```

Não tratar dado antigo como atual.

### 19. Histórico

Nunca sobrescrever observações anteriores.

Persistir séries temporais para permitir:

- timeline;
- comparação;
- tendências;
- análise de evento;
- validação retroativa;
- relatórios;
- regras temporais.

### 20. Falhas do provider

Estados mínimos de job/provider:

```text
QUEUED
RUNNING
SUCCEEDED
FAILED
RETRYABLE
BLOCKED
```

Falhas transitórias devem usar retry com backoff limitado.

Falhas persistentes devem ser registradas.

Uma indisponibilidade da SP Águas ou ANA não deve derrubar Farm360 nem apagar dados históricos.

### 21. Segurança

Preservar:

- tenant isolation;
- RLS;
- RBAC;
- audit;
- secrets fora do Git;
- serviços internos em loopback;
- logs sem credenciais;
- Evidence First.

A API pública da SP Águas não deve ser usada como justificativa para expor endpoints internos da Ribeira.

### 22. Observabilidade

Monitorar internamente:

- última execução do provider;
- latência;
- HTTP status;
- quantidade de observações importadas;
- deduplicações;
- erros;
- stale stations;
- falhas consecutivas;
- duração do job.

Não expor observabilidade interna sensível publicamente.

### 23. Documentação obrigatória

Atualizar continuamente:

```text
docs/integrations/
docs/data/
docs/provenance/
docs/architecture/
docs/operations/
docs/product/
docs/pilot/
```

Registrar contratos observados, comportamento real da API, parâmetros, unidades, limitações, providers, refresh e proveniência.

### 24. Testes

Implementar no mínimo:

- contract tests do SIBH;
- adapter tests;
- parâmetros de data;
- parsing JSON;
- parsing CSV quando usado;
- normalização;
- unidade;
- idempotência;
- deduplicação;
- atualização incremental;
- retry/backoff;
- failure handling;
- time series;
- freshness;
- seleção estação/propriedade;
- RLS;
- tenant isolation;
- Flood context;
- Farm360 Hydrology.

Fixtures são permitidas somente em testes e devem ser explicitamente identificadas como sintéticas.

Nunca usar fixture como dado de produção.

### 25. Prioridade de implementação

Executar aproximadamente nesta ordem:

```text
1. Validar contrato real da API SIBH
2. Implementar SPAguaSIBHProvider
3. Persistir catálogo de estações
4. Importar lista oficial Vale do Ribeira quando disponível
5. Ingestão pluviométrica
6. Ingestão de nível
7. Ingestão de vazão
8. Refresh automático
9. Relação estação ↔ propriedade
10. Série temporal
11. Farm360 Hydrology
12. Flood integration
13. ANA provider foundation
14. ANA protected authentication
15. Correlação entre providers
16. Regras/alertas
17. Relatórios
```

Bloqueio da ANA por credencial nunca deve impedir o avanço independente do SIBH.

### 26. Requisito para o agente autônomo

Esta integração é uma prioridade ativa.

Antes de escolher novo incremento relacionado a:

```text
Flood
Environment
Hydrology
Farm360 hydrological context
```

o agente deve ler este documento.

A integração pública SIBH pode avançar independentemente de credenciais da ANA.

O agente deve:

```text
inspecionar
→ implementar
→ testar
→ documentar
→ revisar diff
→ verificar secrets
→ commit
→ push
→ continuar
```

Não parar após um milestone normal.

### 27. Critérios de aceite

#### SIBH

```text
SP_AGUAS_PROVIDER=IMPLEMENTED
STATION_CATALOGUE=IMPLEMENTED
RAINFALL_INGESTION=IMPLEMENTED
RIVER_LEVEL_INGESTION=IMPLEMENTED
FLOW_INGESTION=IMPLEMENTED_WHERE_AVAILABLE
AUTO_REFRESH=IMPLEMENTED
PROVENANCE=IMPLEMENTED
```

#### Farm360

```text
HYDROLOGY_SECTION=IMPLEMENTED
FRESHNESS=IMPLEMENTED
TIME_SERIES=IMPLEMENTED
STATION_SOURCE_VISIBLE=YES
```

#### Flood

```text
REAL_OBSERVATIONS_USED=YES
FABRICATED_VALUES=NO
CAUSALITY_INFERRED_WITHOUT_EVIDENCE=NO
```

#### ANA

```text
ANA_PROVIDER=IMPLEMENTED
ANA_SECRET_IN_GIT=NO
ANA_AUTH=PROTECTED_RUNTIME_CONFIG
ANA_AUTH_ROUTE=VERIFIED
ANA_BEARER_TOKEN=IMPLEMENTED
ANA_TOKEN_CACHE=IMPLEMENTED
ANA_HIGH_FREQUENCY_REAUTH=NO
ANA_STATION_INVENTORY=IMPLEMENTED
ANA_TELEMETRIC_SERIES=IMPLEMENTED
ANA_QC_PRESERVED=YES
ANA_PROVENANCE=IMPLEMENTED
```

### 28. Estado canônico das fontes

```text
SP ÁGUAS SIBH
STATUS=OFFICIAL_PUBLIC_API_AVAILABLE
AUTH=NONE
AUTOMATION=RECOMMENDED_BY_PROVIDER
DOCUMENTATION=PARTIAL/IN_DEVELOPMENT

ANA HIDROWEBSERVICE
STATUS=ACCESS_APPROVED
AUTH=REQUIRED
AUTH_ROUTE=/EstacoesTelemetricas/OAUth/v1
AUTH_SCHEME=Bearer
DECLARED_TOKEN_TTL=60_MINUTES
TOKEN_REUSE=REQUIRED
HIGH_FREQUENCY_REAUTH=FORBIDDEN
BASE_URL=https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas
PRIMARY_STATION_ROUTE=/EstacoesTelemetricas/HidroInventarioEstacoes/v1
PRIMARY_TELEMETRY_ROUTE=/EstacoesTelemetricas/HidroinfoanaSerieTelemetricaAdotada/v1
AUTOMATION=SUPPORTED
DOCUMENTATION=OFFICIAL_MANUAL_20.02.2026_AND_SWAGGER
```

### 29. Princípio final

A Ribeira Conecta deve usar dados hidrológicos oficiais como evidência operacional.

A plataforma nunca deve transformar:

```text
ausência de dados
```

em:

```text
ausência de risco
```

e nunca deve transformar:

```text
correlação
```

em:

```text
causalidade confirmada
```

sem evidência suficiente.
