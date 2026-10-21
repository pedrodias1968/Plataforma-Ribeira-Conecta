# Custos por talhão e por kg (F-COST-001)

Lançamento de custos no lugar do caderno, com custo por talhão e custo por quilo colhido. Origem:
entrevista com produtor de banana (Eldorado/SP), cujas anotações de custo "são bem precárias" e que
cita um custo de referência por kg para comparar. Esse valor não está no código.

## Princípios

- **Evidence First**: cada lançamento gera `Evidence` (`COST_ENTRY`) e auditoria.
- **Desconhecido não é zero**: talhão sem custo registrado tem custo desconhecido, não nulo.
- **Sem rateio**: custo do sítio inteiro (`field_id` vazio) aparece à parte e nunca é distribuído
  entre talhões.
- **Sem contagem dupla**: custo de adubo vem de `fertilization_record`. A categoria `FERTILIZER` é
  recusada nos lançamentos manuais. Aplicações sem custo tornam o total do talhão **parcial**
  (`cost_is_partial`).
- **Custo por kg** só existe quando o talhão tem custo e **todos** os registros de colheita do período
  têm peso. Caso contrário vem vazio com o motivo: `NO_COST_DATA`, `NO_WEIGHT_DATA` ou
  `SOME_HARVEST_WITHOUT_WEIGHT`.
- **Append-only**: o papel da aplicação só tem `SELECT, INSERT`. Correção é um novo lançamento com
  `supersedes_id`, mantendo talhão (ou a ausência de talhão); cada lançamento admite uma só correção.
- **Classificação**: somente `OBSERVED` ou `MANUAL_CONFIRMED`. O resumo é `CALCULATED` e lista limitações.
- Categoria `OTHER` exige observação. Valor é arredondado a centavos.
- Custos e colheita são cruzados só pelo período de datas; um custo pago no período pode pertencer a
  outra safra.

## Dados

Migration `050_cost_by_field`: tabela `cost_entry` (categoria `LABOR`, `PESTICIDE`, `FUEL`,
`MAINTENANCE`, `PACKAGING`, `TRANSPORT`, `OTHER`; descrição; valor em R$; quem registrou; origem).
RLS forçada por tenant; gatilho garante que o talhão, quando informado, pertence ao sítio. A função
`enforce_evidence_reference_tenant()` é redefinida mantendo todos os ramos da 049.

## API

| Método | Rota | Permissão |
|---|---|---|
| POST/GET | `/v1/tenants/{t}/properties/{p}/cost-entries` | `cost:write` / `cost:read` |
| POST | `/v1/tenants/{t}/cost-entries/{id}/corrections` | `cost:write` |
| GET | `/v1/tenants/{t}/properties/{p}/cost-summary` | `cost:read` |

Filtros: `field_id`, `date_from`, `date_to`, `include_superseded`. Segunda correção retorna
`409 COST_CONFLICT`.

**Permissões**: custo é dado financeiro. Leem `TENANT_ADMIN`, `MANAGER` e `ANALYST`; escrevem
`TENANT_ADMIN` e `MANAGER`. `OPERATOR`, `TECHNICIAN`, `AGRONOMIST`, `VIEWER` e `COMMERCIAL` não têm acesso.

## Fora de escopo

Estoque, vendas e recebimentos, rateio de custos do sítio, depreciação de máquinas, comparação com
meta de custo por kg e correção pela tela (só pela API).
