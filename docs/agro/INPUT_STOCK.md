# Estoque de insumos (F-STOCK-001)

Entradas e saídas de insumos (adubo, defensivos, embalagem etc.) com saldo por item, no lugar do caderno.

## Princípios

- **Evidence First**: cada movimentação (`STOCK_MOVEMENT`) gera `Evidence` e auditoria.
- **Saldo = entradas − saídas registradas**, por insumo (sem diferenciar maiúsculas) e por unidade (`KG`, `L`, `UNIT`). Unidades diferentes nunca são somadas.
- **Estoque inicial desconhecido não vira zero**: o saldo **nunca é truncado em zero**. Saída maior que as entradas registradas aparece como saldo negativo (`negative_balance`), sinal de que falta registrar uma entrada.
- Quantidade sempre maior que zero; o sentido vem do tipo (`IN`/`OUT`). Datas futuras recusadas.
- **Sem baixa automática**: a adubação registrada (F-FERT-001) não mexe no estoque; a saída é lançada à parte.
- **Append-only**: o papel da aplicação só tem `SELECT, INSERT`. Correção é uma nova movimentação com `supersedes_id`, mantendo o sítio; cada movimentação admite uma só correção (409 `STOCK_CONFLICT`).
- Classificação somente `OBSERVED` ou `MANUAL_CONFIRMED`; o resumo é `CALCULATED` e lista limitações.

## Dados e API

Migration `052_input_stock` (tabela `stock_movement`, RLS forçada, gatilho de consistência de sítio).

- `POST/GET /v1/tenants/{t}/properties/{p}/stock-movements`
- `POST /v1/tenants/{t}/stock-movements/{id}/corrections`
- `GET /v1/tenants/{t}/properties/{p}/stock-summary` (`as_of`, padrão hoje em UTC)

Permissões `stock:read` (ANALYST, OPERATOR, TENANT_ADMIN, MANAGER, AGRONOMIST, TECHNICIAN) e `stock:write` (todos exceto ANALYST): é dado operacional, como a colheita.

## Limites conhecidos

- Correção pelo painel “Corrigir um registro” da Farm360 ou pela API (o painel “Corrigir um registro” da Farm360 faz a correção).
- Sem estoque mínimo/alerta, sem custo médio, sem validade nem lote.
- Lista de unidades fixa (`KG`, `L`, `UNIT`).

Testes: `tests/test_stock.py`, `tests/integration/test_stock_postgres.py`, `frontend/src/features/stock/`.
