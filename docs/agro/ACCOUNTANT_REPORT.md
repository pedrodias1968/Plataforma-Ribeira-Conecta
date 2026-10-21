# Relatório para o contador (F-ACC-001)

Pacote somente leitura com as vendas, os recebimentos e os custos de um período, para entregar ao contador.

`GET /v1/tenants/{t}/properties/{p}/accountant-report?date_from=AAAA-MM-DD&date_to=AAAA-MM-DD[&as_of=AAAA-MM-DD]`

- Período obrigatório. Exige `sale:read` e `cost:read` (gerência e analista).
- Traz o resumo de vendas (`sales`: total, recebido, a receber, atrasado, por comprador) e o de custos (`costs`: por talhão, sítio inteiro, adubação), exatamente como nos módulos F-SALE-001 e F-COST-001.
- **Não calcula resultado nem margem**: vendas e custos do período não são pareados (safras e datas de pagamento diferentes).
- Valor sem registro continua desconhecido, não zero. Classificação `CALCULATED`, com limitações listadas.
- Não substitui escrituração contábil nem nota fiscal.

## Tela e planilha

O painel "Relatório para o contador" na Farm360 pede o período, mostra o resumo e baixa uma planilha CSV
(separador `;`, decimal com vírgula, abre direto no Excel). Valor sem registro sai como **célula vazia**,
nunca 0. A planilha é montada no navegador a partir do mesmo relatório, sem outro cálculo.

Limites: sem PDF. Testes: `tests/test_accountant_report.py`, `frontend/src/features/accountant/`.
