# Princípios de Design

## 1. Heurísticas de Nielsen (10 itens)

### 1. Visibilidade do Estado do Sistema
**Regra**: O usuário deve sempre saber "o que está acontecendo"

**Aplicação à Ribeira Conecta**:
- Carregamento: "Buscando dados hidrológicos..." (não tela em branco)
- Dados desatualizados: "Última atualização: 2h atrás" (não dados antigos como se fossem novos)
- Erros: "Não foi possível carregar pluviometria" (não silêncio)

**Status de validação**:
- [ ] Hero carrega em <2s (conectividade rural)
- [ ] Estados de carregamento visíveis
- [ ] Mensagens de erro claras (não códigos HTTP)

---

### 2. Consistência e Normas
**Regra**: Mantenha padrões visuais e comportamentais

**Aplicação à Ribeira Conecta**:
- Botões: verde primário para ações principais, cinza para secundárias
- Ícones: mesma linguagem visual (SVG line icons)
- Cores: paleta fixa (verdes, cinzas, brancos)

**Status de validação**:
- [ ] Botão CTA primário sempre verde
- [ ] Ícones SVG, não fontes
- [ ] Cores fixas (não hex aleatórios)

---

### 3. Controle e Liberdade do Usuário
**Regra**: Usuários escolhem, não são forçados

**Aplicação à Ribeira Conecta**:
- Formulários: campos obrigatórios marcados (não bloqueio total)
- Fechar: botão "X" em every modal (não só Escape)
- Cancelar: botão de cancelar em every fluxo

**Status de validação**:
- [ ] Formulários mostram quais campos são obrigatórios
- [ ] Todos os modais têm botão de fechar
- [ ] Fluxos têm botão de cancelar

---

### 4. Reconhecimento em vez de Memorização
**Regra**: Minimize a carga cognitiva de memória

**Aplicação à Ribeira Conecta**:
- Navegação: menu visível (não só breadcrumbs)
- Contexto: "Você está em: Home / Casos de Uso"
- Formulários: placeholders claros (não só "Digite aqui")

**Status de validação**:
- [ ] Menu visível em todas as páginas
- [ ] Breadcrumbs em páginas internas
- [ ] Placeholders explicativos em formulários

---

### 5. Prevenção de Erros
**Regra**: Evite erros, não apenas mensagens

**Aplicação à Ribeira Conecta**:
- Formulários: validação em tempo real (não só submit)
- Botões: "Falar com equipe" (não "Enviar" vago)
- Confirm: "Você tem certeza?" antes de ações irreversíveis

**Status de validação**:
- [ ] Validador de e-mail em tempo real
- [ ] Botões com verbos claros
- [ ] Confirmação antes de ações críticas

---

### 6. Flexibilidade e Eficiência de Uso
**Regra**: Atenda usuários inexperientes e experts

**Aplicação à Ribeira Conecta**:
- Padrão: conteúdo simples (não especialista)
- Expert: links para documentos técnicos
- Acessibilidade: teclado, screen readers

**Status de validação**:
- [ ] Conteúdo acessível sem jargão
- [ ] Links para documentação técnica
- [ ] Navegação por teclado (Tab, Enter, Esc)

---

### 7. Estética e Design Minimalista
**Regra**: Menos é mais

**Aplicação à Ribeira Conecta**:
- Hero: uma ideia (problema + solução)
- Seções: uma ideia por seção
- Botões: um CTA primário por página

**Status de validação**:
- [ ] Hero com mensagem única
- [ ] Uma ideia por seção
- [ ] Um CTA primário por página

---

### 8. Ajuda ao Usuário
**Regra**: Suporte não substitui UX clara

**Aplicação à Ribeira Conecta**:
- FAQ: antecipar dúvidas antes do formulário
- Tooltips: explicar termos técnicos
- Feedback: "Obrigado, retornaremos em <24h"

**Status de validação**:
- [ ] FAQ antes de contato
- [ ] Tooltips em termos técnicos
- [ ] Feedback claro após ação

---

### 9. Design para Reconhecimento, não Memória
**Regra**: Interfaces devem reconhecer, não exigir memória

**Aplicação à Ribeira Conecta**:
- Formulários: prefilled quando possível (não vazio)
- Contexto: "Você está em: Propriedade X"
- Estado: "Última atualização: 2h atrás"

**Status de validação**:
- [ ] Formulários prefilled quando possível
- [ ] Contexto visualizado
- [ ] Estado visível (data/hora)

---

### 10. Ajuda e Documentação
**Regra**: Documentação clara, não substitui UX

**Aplicação à Ribeira Conecta**:
- FAQ: antecipar dúvidas
- Manual: link em every seção complexa
- Tutorial: onboarding de 30s

**Status de validação**:
- [ ] FAQ visível
- [ ] Links para documentação
- [ ] Tutorial rápido

---

## 2. WCAG 2.2 Nível AA

### 2.1 Contraste Mínimo
**Regra**: Texto normal ≥ 4.5:1, grande ≥ 3:1

**Aplicação à Ribeira Conecta**:
- Texto principal: #1e293b (slate-800) em #ffffff
- Texto secundário: #64748b (slate-500) em #ffffff
- Botão CTA: #16a34a (emerald-600) em #ffffff

**Status de validação**:
- [ ] Texto normal ≥ 4.5:1
- [ ] Texto grande ≥ 3:1
- [ ] Botão CTA com contraste adequado

---

### 2.2 Sem Cursos de Cor
**Regra**: Informação não deve depender apenas de cor

**Aplicação à Ribeira Conecta**:
- Status: ícone + texto (não apenas cor)
- Erros: ícone + mensagem + destaque do campo

**Status de validação**:
- [ ] Status com ícone + texto
- [ ] Erros com ícone + mensagem

---

### 2.3 Foco Visível
**Regra**: Indicador de foco em cada elemento interativo

**Aplicação à Ribeira Conecta**:
- Botões: outline 2px quando focado
- Inputs: outline 2px quando focado
- Links: underline + outline

**Status de validação**:
- [ ] Botões com outline 2px ao focar
- [ ] Inputs com outline 2px ao focar
- [ ] Links com underline + outline

---

### 2.4 Alvos de Toque
**Regra**: Mínimo 44x44px para touch

**Aplicação à Ribeira Conecta**:
- Botões: min 44px altura
- Links no menu: min 44px altura
- Formulários: min 44px altura

**Status de validação**:
- [ ] Botões ≥ 44px altura
- [ ] Links do menu ≥ 44px altura
- [ ] Inputs ≥ 44px altura

---

### 2.5 Teclado Acessível
**Regra**: Navegação completa via teclado

**Aplicação à Ribeira Conecta**:
- Tab: navega sequencial
- Enter: ação
- Esc: fechar modais

**Status de validação**:
- [ ] Tab navega sequencialmente
- [ ] Enter aciona botões
- [ ] Esc fecha modais

---

### 2.6 Texto Alternativo
**Regra**: Imagens têm alt descritivo

**Aplicação à Ribeira Conecta**:
- Mapa: "Mapa de propriedade rural com dados de NDVI"
- Icon: "Ícone de conectividade"

**Status de validação**:
- [ ] Todas as imagens têm alt
- [ ] Alt descritivo (não vazio)

---

### 2.7 prefers-reduced-motion
**Regra**: Respeitar preferência de movimento reduzido

**Aplicação à Ribeira Conecta**:
- Sem animações automáticas (carousel, scroll)
- Transições rápidas (<100ms)

**Status de validação**:
- [ ] Nenhum carousel automático
- [ ] Transições rápidas

---

## 3. Hierarquia Visual

### 3.1 Uma Ideia por Seção
**Regra**: Cada seção responde a uma dúvida específica

**Aplicação à Ribeira Conecta**:
- Hero: "O que é e para quem é"
- Problema: "Quais são os riscos"
- Solução: "Como a Ribeira resolve"
- Ecosistema: "Quais recursos estão disponíveis"

**Status de validação**:
- [ ] Cada seção com uma ideia
- [ ] Sem sobreposição de conteúdo

---

### 3.2 Um Foco Visual por Tela
**Regra**: Um elemento chama mais atenção (CTA primário)

**Aplicação à Ribeira Conecta**:
- Hero: botão "Falar com a equipe"
- Sobre: botão "Falar com a equipe"
- Contato: botão "Enviar"

**Status de validação**:
- [ ] Um CTA primário por página
- [ ] Outros botões secundários (menos destaque)

---

### 3.3 Texto Escaneável
**Regra**: Facilitar leitura rápida

**Aplicação à Ribeira Conecta**:
- Títulos: frases curtas
- Parágrafos: 3-5 linhas
- Lista: bullets, não parágrafos

**Status de validação**:
- [ ] Títulos ≤ 8 palavras
- [ ] Parágrafos ≤ 5 linhas
- [ ] Lista bullets onde couber

---

### 3.4 Linguagem Simples
**Regra**: Sem jargão sem explicação

**Aplicação à Ribeira Conecta**:
- NDVI: "Índice de vegetação" + tooltip
- Hidrologia: "Monitoramento de chuva e nível de rios"
- "Inteligência Territorial": "Decisões com base em dados"

**Status de validação**:
- [ ] Jargões explicados
- [ ] Tooltips em termos técnicos

---

## 4. Lei de Hick
**Regra**: Tempo de decisão aumenta com número de opções

**Aplicação à Ribeira Conecta**:
- Menu: 5 itens (não 10+)
- Seção de recursos: 5 pilares (não 10+)
- Formulários: campos essenciais (não 15+)

**Status de validação**:
- [ ] Menu ≤ 5 itens
- [ ] Seção de recursos ≤ 5 pilares
- [ ] Formulários ≤ 5 campos essenciais

---

## 5. Mobile-First

### 5.1 Ações ao Alcance do Polegar
**Regra**: CTA primário no topo da tela (mobile)

**Aplicação à Ribeira Conecta**:
- Hero CTA: fixo ou no topo (não rolagem longa)
- Menu mobile: topo da tela

**Status de validação**:
- [ ] Hero CTA visível sem rolagem (mobile)
- [ ] Menu mobile topo da tela

---

### 5.2 Pesquisa em Rede Lenta
**Regra**: Página leve (<1MB) e carga <3s

**Aplicação à Ribeira Conecta**:
- Imagens: otimizadas, dimensões fixas
- JS: code-splitting (lazy load)
- CSS: minimizado

**Status de validação**:
- [ ] Total <1MB (gzip)
- [ ] Carregamento <3s (3G)
- [ ] Imagens com dimensões fixas

---

## 6. Confiança

### 6.1 Status Honesto
**Regra**: DISPONÍVEL / EM DESENVOLVIMENTO / PLANEJADO

**Aplicação à Ribeira Conecta**:
- Sem métricas inventadas
- Sem depoimentos inventados
- Sem "em breve" sem data

**Status de validação**:
- [ ] Nenhum dado inventado
- [ ] Status explícito

---

### 6.2 Demonstrações Rotuladas
**Regra**: "Demonstração" em every dado simulado

**Aplicação à Ribeira Conecta**:
- Dados de exemplo: "Demonstração" ou "Fixtures"
- Vídeo: "Demonstração de interface"

**Status de validação**:
- [ ] Fixtures rotulados
- [ ] Vídeos rotulados

---

**Última atualização**: 2026-10-16  
**Próxima revisão**: Após first prototype e auditoria
