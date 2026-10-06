# Integração Hidrológica Oficial — SP Águas SIBH + ANA HidroWebService

Status: PRIORIDADE ALTA
Implementação: pendente/em andamento
Princípio: Evidence First

## 1. SP Águas — SIBH

A SP Águas confirmou oficialmente a existência de API pública para consulta
dos dados disponibilizados no SIBH.

### Endpoints oficiais

Estações:

https://apps.spaguas.sp.gov.br/sibh/api/v2/stations

Medições:

https://apps.spaguas.sp.gov.br/sibh/api/v2/measurements

### Parâmetros informados pela SP Águas

- start_date
- end_date
- group_type
- station_prefix_ids (ARRAY TYPE - URL encoding format pending validation)
- format

group_type:

- minute
- hour
- day
- month

format:

- json
- csv

### Dados

- pluviometria / chuva
- fluviometria / nível
- vazão, quando disponível

A API é pública e atualmente não exige usuário, senha, token ou
credenciamento prévio.

A SP Águas recomenda oficialmente o uso dos endpoints do SIBH para
integração e obtenção periódica dos dados.

Consultas automatizadas devem ser responsáveis, evitando volume excessivo
ou intervalos desnecessariamente curtos.

## 2. Validação obrigatória de datas

O e-mail recebido descreveu:

start_date = fim da série
end_date = começo da série

Isso parece semanticamente invertido.

Não assumir comportamento.

Testar empiricamente a API e documentar:

- start < end
- start > end
- timezone
- inclusividade das datas
- ordenação
- paginação/limites se existirem

Só depois definir o contrato canônico do adapter.

## 3. Estações do Vale do Ribeira

A SP Águas forneceu CSV com os IDs das estações de pluviometria e
fluviometria do Vale do Ribeira / UGRHI 11.

Quando o arquivo estiver disponível no ambiente, importar por fluxo
controlado.

Nunca inventar IDs de estação.

Persistir quando fornecido:

- provider_station_id
- station_code
- station_name
- station_type
- river/basin
- latitude
- longitude
- municipality
- source
- status
- retrieved_at

## 4. Provider SP Águas

Implementar provider neutro:

SPAguaSIBHProvider

Capacidades:

- listar estações
- consultar medições
- chuva
- nível
- vazão
- normalização
- persistência
- histórico
- deduplicação
- idempotência
- falhas do provider
- retry/backoff
- atualização incremental

## 5. Observação hidrológica canônica

Persistir no mínimo:

- provider
- station_id
- metric_type
- value
- unit
- observed_at
- received_at, quando disponível
- ingested_at
- quality/status, quando disponível
- source_reference
- provenance

Tipos mínimos:

- RAINFALL
- RIVER_LEVEL
- FLOW

Nunca derivar vazão de nível ou vice-versa sem modelo científico explícito
e versionado.

## 6. Ingestão automática

Integrar ao scheduler e durable jobs existentes.

Fluxo:

station/provider
→ busca incremental
→ valida resposta
→ deduplica
→ persiste observações
→ atualiza freshness
→ contexto hidrológico
→ Farm360/Flood

Persistir:

- last_attempt
- last_success
- latest_observation
- next_refresh
- provider_error
- retry_state

A frequência deve respeitar a cadência real das estações e uso responsável
da API.

## 7. Relação estação ↔ propriedade

Não assumir automaticamente que a estação mais próxima representa a
propriedade.

A seleção pode considerar:

- distância
- bacia/sub-bacia
- rio
- montante/jusante
- métrica disponível
- freshness
- qualidade
- cobertura temporal

Persistir a justificativa e limitações da estação selecionada.

## 8. Flood / Environment

Usar observações reais para:

- chuva
- nível
- vazão
- linha do tempo
- contexto de evento
- exposição da propriedade
- exposição dos ativos
- regras
- alertas
- ações
- resultados

Nunca inferir causalidade apenas por correlação temporal.

Cadeia:

observação
→ contexto
→ regra/modelo
→ avaliação
→ decisão
→ ação
→ resultado

## 9. ANA HidroWebService

O acesso da Ribeira Conecta ao HidroWebService foi aprovado pela ANA.

Documentação oficial fornecida:

https://www.ana.gov.br/hidrowebservice/swagger-ui.html#/

Implementar provider separado:

ANAHidroWebProvider

Credenciais são privadas.

Nunca:

- colocar senha no Git
- colocar senha em documentação
- imprimir senha em logs
- pedir senha em prompt

Usar configuração protegida de runtime.

## 10. SP Águas e ANA são providers distintos

Não substituir um pelo outro.

SP Águas SIBH:

- fonte regional operacional
- Vale do Ribeira
- telemetria próxima do tempo real

ANA:

- cobertura nacional
- inventário
- histórico
- telemetria complementar/redundante

Preservar identidade da fonte.

## 11. Correlação entre providers

Não deduplicar apenas por:

- nome parecido
- coordenadas próximas

Criar mapeamento explícito quando houver evidência de que registros
representam a mesma estação física.

## 12. Farm360

Expor quando houver dados reais:

### Hidrologia

Chuva
- última observação
- estação
- fonte
- horário
- freshness

Nível do rio
- última observação
- estação
- fonte
- horário
- freshness

Vazão
- quando disponível

Permitir:

- 24h
- 7d
- 30d
- janela de evento
- histórico

## 13. Caso de validação

Usar o evento do Vale do Ribeira de setembro de 2026 como caso real de
validação quando houver observações disponíveis.

Hipóteses permanecem distintas:

- H1 chuva local
- H2 chuva a montante
- H3 influência de reservatório/Capivari
- H4 contexto ENSO

Nenhuma hipótese deve virar causalidade confirmada sem evidência.

## 14. Evidence First

Sem medição:
UNKNOWN

Provider indisponível:
SOURCE_UNAVAILABLE

Fontes em conflito:
CONFLICTING

Nunca preencher lacuna com observação fabricada.

## 15. Entregáveis

Implementar, testar, documentar, commitar e fazer push de:

- SPAguaSIBHProvider
- station catalogue
- rainfall ingestion
- river-level ingestion
- flow ingestion
- automatic refresh
- provenance
- time series
- property/station relationship
- Farm360 hydrology
- Flood integration
- ANA provider foundation
- protected ANA authentication
- tests
- runbooks
- source catalogue

Depois continuar o roadmap autônomo normalmente.
