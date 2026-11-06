# ERP / Gestão Agro — Perguntas em aberto (lacunas de especificação)

Este documento é **factual e apenas de perguntas**. Ele consolida as lacunas de
especificação já registradas no repositório para a superfície de ERP / gestão
agro (Gestão da banana, Solo por talhão e módulos por talhão). Não define regra
de negócio, não propõe resposta e não cria requisito novo.

Origem primária: `docs/product/ERP_SURFACE_INDEX.md` (Seção 6 —
UNKNOWN / PENDENTE-GABARITO) e temas de banana/solo/talhão sem especificação
canônica completa sob `docs/`. Cada pergunta cita onde a lacuna foi observada.

Sem evidência, o estado permanece `UNKNOWN` / `PENDENTE-GABARITO`.

---

## 1. Identidade e escopo do "ERP"

1. Existe definição canônica do produto "ERP / gestão agro" como módulo nomeado?
   O termo "ERP da banana" hoje aparece apenas como comentário em
   `frontend/src/pages/BananaManagementPage.tsx`
   (ref. `docs/product/ERP_SURFACE_INDEX.md`, item 1).
2. Qual é o escopo oficial do ERP: apenas as abas de `BananaManagementPage.tsx`
   (`colheita`, `adubacao`, `solo`, `estoque`, `custos`, `vendas`, `contador`,
   `correcoes`) ou também outros módulos fora dessa tela?
3. O ERP é uma superfície de produto distinta do Farm360/Agro, ou um conjunto de
   painéis dentro do Farm360? Não há documento canônico que fixe essa relação.

---

## 2. Colheita, adubação, custo, venda, estoque e contador

4. Quais são os critérios agronômicos/comerciais que tornam um valor
   `unit_price_brl` válido em vendas? Os campos existem
   (`frontend/src/api/sales.ts`), mas não há definição canônica
   (ref. `ERP_SURFACE_INDEX.md`, item 2).
5. Qual é a regra de negócio de custo unitário por talhão aplicável aos
   lançamentos de custo?
6. O relatório do contador explicitamente **não** calcula resultado nem margem
   (`docs/agro/ACCOUNTANT_REPORT.md`). Se a apuração de resultado for
   necessária, qual é a regra? (ref. `ERP_SURFACE_INDEX.md`, item 5).
7. Qual é a regra de pareamento entre vendas e custos para eventual apuração de
   margem/lucro?
8. Existe modelo canônico de "safra" / período de apuração para agrupar
   registros por talhão? Não há no repositório
   (ref. `ERP_SURFACE_INDEX.md`, item 6).
9. Quais módulos exigem `field_id` (talhão obrigatório) e quais não exigem? Isso
   não está consolidado em documento único; hoje só pode ser inferido por
   endpoint/tabela (ref. `ERP_SURFACE_INDEX.md`, item 7).
10. Existe regra de fechamento de período, ou os lançamentos permanecem sempre
    abertos e corrigíveis por supersessão? A regra de correção existe
    (`CORRECTIONS_UI.md`), mas a de fechamento de período não está definida.

---

## 3. Solo (amostras, laudos e índices derivados)

11. Qual é a regra de densidade de amostragem e de seleção de zonas por talhão?
    O fluxo conceitual existe em `docs/agro/SMART_SOIL_SAMPLING.md`, mas
    thresholds e regra de seleção não estão definidos
    (ref. `ERP_SURFACE_INDEX.md`, item 3).
12. Qual é o vínculo oficial entre os índices derivados de solo
    (`compute_soil_derived_indices`, `src/ribeira_platform/soil.py:91` — SB, CTC,
    V%, m%) e uma decisão/recomendação agronômica versionada? Não há regra
    canônica que transforme índice em decisão
    (ref. `ERP_SURFACE_INDEX.md`, item 4).
13. Quais analitos são obrigatórios para considerar um laudo de solo completo?
    `docs/agro/SOIL_INTELLIGENCE.md` afirma que nenhum schema universal é
    assumido (`LABORATORY_SOIL_RESULT`).
14. Qual é o processo/limite de promoção de resultado preliminar
    (`PRELIMINARY_*`) para `VALIDATED_SUITABILITY`
    (`docs/agro/AGRICULTURAL_SUITABILITY.md`)? A promoção é explícita e
    auditável, mas os critérios concretos por cultura não estão definidos.

---

## 4. Banana / adequação agrícola

15. Quais são os fatores e thresholds agronômicos específicos da banana?
    `docs/agro/AGRICULTURAL_SUITABILITY.md` declara "No universal banana
    threshold is hardcoded" e exige regra/fonte agronômica aprovada.
16. Qual é a fonte/política agronômica aprovada para validação de doença e
    manejo da banana? O estado é `EXPERT_VALIDATION_REQUIRED`
    (`docs/agro/SOIL_INTELLIGENCE.md`; `docs/product/MODULE_CATALOG.md`,
    "Banana Intelligence").
17. O fluxo de inspeção de campo da banana (`F-BANANA-002`,
    `docs/product/FEATURE_CATALOG.md`, status `COMING_SOON`) terá especificação
    canônica? Hoje só existe o estado de catálogo.
18. Existe regra de `F-AGRO-008` (Banana suitability, `COMING_SOON`) além da
    dependência declarada ("Suitability + approved banana factors/expert
    policy")? Não há spec detalhada em `docs/`.

---

## 5. Talhão (field)

19. Qual é o contrato canônico de "talhão" para efeito de ERP? Existem
    referências a talhão em `docs/agro/*_BY_FIELD.md`,
    `docs/iot/FIELD_TELEMETRY.md` e no escopo de regra `FIELD`
    (`F-RULE-001`), mas não um documento único que consolide o contrato de
    campo aplicável ao ERP.
20. Um talhão pode pertencer a mais de uma safra/ciclo simultaneamente? Não há
    modelo temporal de talhão documentado.
21. Qual é a regra de herança de zona/cultura para talhão? `F-RULE-001` registra
    "Zone/crop inheritance remains pending"
    (`docs/product/FEATURE_CATALOG.md`).

---

## 6. Estados e evidência (transversal)

22. Como o ERP deve apresentar ausência de dado sem convertê-la em zero/falso?
    A regra geral existe (`docs/agro/SALES_RECEIVABLES.md`: "Desconhecido não é
    zero"), mas não há catálogo de estados ERP por módulo.
23. Quais estados de evidência são exigidos por tela do ERP, dado que os estados
    canônicos (`UNKNOWN`, `OBSERVED`, `INFERRED`, `MODELLED`, `CONFIRMED`,
    `DERIVED`, `CALCULATED`, `PRELIMINARY_*`, `VALIDATED_*`) variam por domínio?

---

## 7. Governança e documentação

24. Qual documento canônico deve passar a ser dono do tema "ERP / gestão agro"?
    Hoje não há documento que possua oficialmente o assunto
    (ref. `ERP_SURFACE_INDEX.md`, item 1).
25. Qual é a ordem de prioridade de especificação entre os itens em aberto
    acima, dado que nenhum possui gabarito definido no repositório?
