# Relatório para o contador (F-ACC-001)

Pacote somente leitura com as vendas, os recebimentos e os custos de um período, para entregar ao contador.

`GET /v1/tenants/{t}/properties/{p}/accountant-report?date_from=AAAA-MM-DD&date_to=AAAA-MM-DD[&as_of=AAAA-MM-DD]`

- Período obrigatório. Exige `sale:read` e `cost:read` (gerência e analista).
- Traz o resumo de vendas (`sales`: total, recebido, a receber, atrasado, por comprador) e o de custos (`costs`: por talhão, sítio inteiro, adubação), exatamente como nos módulos F-SALE-001 e F-COST-001.
- **Não calcula resultado nem margem**: vendas e custos do período não são pareados (safras e datas de pagamento diferentes).
- Valor sem registro continua desconhecido, não zero. Classificação `CALCULATED`, com limitações listadas.
- Não substitui escrituração contábil nem nota fiscal.

Limites: sem tela nem exportação em arquivo (CSV/PDF) ainda. Teste: `tests/test_accountant_report.py`.
