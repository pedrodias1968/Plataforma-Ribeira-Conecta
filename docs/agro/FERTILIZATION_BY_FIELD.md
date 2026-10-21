# Adubação e insumos por talhão (F-FERT-001)

Registro de cada aplicação de adubo ou insumo em um talhão, com produto, quantidade, quem aplicou,
custo e origem do dado. Origem: entrevista com produtor de banana (Eldorado/SP), que diz que "não há
muitos registros" de adubação e hoje não consegue achar o que foi aplicado meses atrás.

## Princípios

- **Evidence First**: cada registro gera `Evidence` (`FERTILIZATION_RECORD`) e auditoria.
- **Desconhecido não é zero**: quantidade, área e custo não informados ficam `NULL`.
  Zero só quando informado.
- **Quantidade e unidade andam juntas** (`KG`, `G`, `L`, `ML`): ou as duas, ou nenhuma.
- **Sem mistura de unidades** e **sem dose por hectare**: a área aplicada muitas vezes não é anotada.
- **Append-only**: o papel da aplicação só tem `SELECT, INSERT`. Correção é um novo registro com
  `supersedes_id`; cada registro admite uma única correção.
- **Classificação**: somente `OBSERVED` ou `MANUAL_CONFIRMED`. O resumo é `CALCULATED` e lista limitações.
- **Datas futuras** (> hoje UTC + 1 dia) são rejeitadas.
- Tipo `OTHER` exige observação.

## Dados

Migration `049_fertilization_by_field`: tabela `fertilization_record` (produto, tipo, quantidade,
unidade, área aplicada, forma de aplicação, custo em R$, quem aplicou, quem registrou, origem).
RLS forçada por tenant; gatilho garante que o talhão pertence ao sítio e que a correção preserva
sítio e talhão. A função `enforce_evidence_reference_tenant()` é redefinida mantendo todos os ramos
da 048.

## API

| Método | Rota | Permissão |
|---|---|---|
| POST/GET | `/v1/tenants/{t}/properties/{p}/fertilization-records` | `fertilization:write` / `fertilization:read` |
| POST | `/v1/tenants/{t}/fertilization-records/{id}/corrections` | `fertilization:write` |
| GET | `/v1/tenants/{t}/properties/{p}/fertilization-summary` | `fertilization:read` |

Filtros: `field_id`, `date_from`, `date_to`, `include_superseded`. Segunda correção do mesmo registro
retorna `409 FERTILIZATION_CONFLICT`. Mesmos perfis da colheita; `VIEWER` e `COMMERCIAL` não têm acesso.

## Fora de escopo

Estoque de insumos (módulo próprio), recomendação de adubação, análise de solo cruzada com aplicação
e custo consolidado por talhão e por kg (módulo de custos).
