# Vendas e recebimentos (F-SALE-001)

Registro das vendas de banana e do que já foi recebido, no lugar do caderno. Origem: entrevista com
produtor de banana (Eldorado/SP), que vende a atravessadores, trabalha com preço do dia e precisa saber
quanto tem a receber e quando.

## Princípios

- **Evidence First**: cada venda (`SALE_RECORD`) e cada recebimento (`PAYMENT_RECORD`) gera `Evidence` e auditoria.
- **Desconhecido não é zero**: venda sem valor total tem saldo desconhecido (`AMOUNT_UNKNOWN`), não zero.
- **Total nunca é calculado**: o total vale o que foi registrado; quantidade × preço não é usado para preenchê-lo.
- **Unidades não se misturam**: quantidade e preço têm unidade (`BOXES`, `KG`, `BUNCHES`) e são somados só por unidade.
- A venda exige quantidade ou valor total. Previsão de pagamento, quando informada, não pode ser anterior à venda.
- **Situação**: `AMOUNT_UNKNOWN`, `OPEN`, `PARTIAL`, `PAID`, `OVERPAID`. "Atrasado" só se há saldo, previsão
  informada e previsão anterior à data de referência (`as_of`, padrão hoje em UTC).
- **Append-only**: o papel da aplicação só tem `SELECT, INSERT`. Correção é um novo registro com
  `supersedes_id` (uma só correção por registro). Recebimento corrigido mantém a venda; correção de venda
  mantém o sítio. O resumo segue a cadeia de correções: recebimentos valem para a versão atual da venda.
- Recebimento contra venda já corrigida é recusado (409 `SALES_CONFLICT`); lance contra a versão atual.
- Classificação somente `OBSERVED` ou `MANUAL_CONFIRMED`; o resumo é `CALCULATED` e lista limitações.
- Datas futuras são recusadas. Comprador agrupado sem diferenciar maiúsculas.

## Dados e API

Migration `051_sales_receivables`: tabelas `sale_record` e `payment_record` (RLS forçada por tenant,
gatilhos de consistência de sítio/venda). A função de evidência mantém todos os tipos anteriores.

- `POST/GET /v1/tenants/{t}/properties/{p}/sale-records`
- `POST /v1/tenants/{t}/sale-records/{id}/corrections`
- `POST /v1/tenants/{t}/sale-records/{id}/payments`
- `GET /v1/tenants/{t}/properties/{p}/payment-records`
- `POST /v1/tenants/{t}/payment-records/{id}/corrections`
- `GET /v1/tenants/{t}/properties/{p}/sales-summary` (`date_from`, `date_to`, `as_of`)

Permissões `sale:read` (ANALYST, TENANT_ADMIN, MANAGER) e `sale:write` (TENANT_ADMIN, MANAGER): dado financeiro.

## Limites conhecidos

- Correção pelo painel “Corrigir um registro” da Farm360 ou pela API; o painel “Corrigir um registro” da Farm360 corrige vendas e recebimentos.
- Sem vínculo com talhão: a venda é do sítio. Sem emissão de nota nem conciliação bancária.
- Preço do dia é registrado por venda; não há tabela de cotações.

Testes: `tests/test_sales.py`, `tests/integration/test_sales_postgres.py`, `frontend/src/features/sales/`.
