# Colheita por talhão (F-HARV-001)

Registro do que foi colhido, embalado e descartado em cada talhão, com origem e evidência.
Origem: entrevista com produtor de banana (Eldorado/SP), que hoje anota colheita em caderno e
não controla o descarte.

## Princípios

- **Evidence First**: cada registro gera `Evidence` (`HARVEST_RECORD` / `HARVEST_DISCARD`) e auditoria.
- **Desconhecido não é zero**: medida não informada fica `NULL`. Zero só quando informado.
- **Sem mistura de unidades**: descarte em `BOXES`, `KG` ou `BUNCHES`, nunca somados entre si.
- **Sem percentual de descarte**: não há base confiável de denominador; só quantidades.
- **Append-only**: o papel da aplicação só tem `SELECT, INSERT`. Correção é um novo registro com
  `supersedes_id`; cada registro admite uma única correção.
- **Classificação**: somente `OBSERVED` ou `MANUAL_CONFIRMED`. O resumo é `CALCULATED` e lista limitações.
- **Datas futuras** (> hoje UTC + 1 dia) são rejeitadas.

## Dados

Migration `048_harvest_by_field` — tabelas `harvest_record` (cachos colhidos, caixas embaladas,
peso em kg, critério de corte; ao menos uma medida) e `harvest_discard` (motivo `STAIN`,
`MECHANICAL_DAMAGE`, `CALIBER`, `OTHER`; observação obrigatória em `OTHER`). RLS forçada por tenant;
gatilhos garantem que o talhão pertence ao sítio e que a correção preserva sítio e talhão.

A 048 também redefine `enforce_evidence_reference_tenant()` restaurando o ramo
`FIELD_BOUNDARY_CORRECTION`, removido por engano na 047.

## API

| Método | Rota | Permissão |
|---|---|---|
| POST/GET | `/v1/tenants/{t}/properties/{p}/harvest-records` | `harvest:write` / `harvest:read` |
| POST | `/v1/tenants/{t}/harvest-records/{id}/corrections` | `harvest:write` |
| POST/GET | `/v1/tenants/{t}/properties/{p}/harvest-discards` | `harvest:write` / `harvest:read` |
| POST | `/v1/tenants/{t}/harvest-discards/{id}/corrections` | `harvest:write` |
| GET | `/v1/tenants/{t}/properties/{p}/harvest-summary` | `harvest:read` |

Filtros: `field_id`, `date_from`, `date_to`, `include_superseded`. Segunda correção do mesmo
registro retorna `409 HARVEST_CONFLICT`. `VIEWER` e `COMMERCIAL` não têm acesso.

## Fora de escopo

Rastreabilidade de lote/venda, preço, estimativa de safra e integração com balança.
