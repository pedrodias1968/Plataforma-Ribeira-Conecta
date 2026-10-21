# Jornada e Arquitetura de Informação

## 1. Jornada do Visitante

```text
DESCOBRIR
   ↓
ENTENDER O VALOR
   ↓
CONFIAR
   ↓
AGIR
```

### Etapa 1: DESCobrir
**Objetivo**: Encontrar o site (SEO, referências, parcerias)

**Canais**:
- Busca Google ("monitoramento satelital bananicultura", "risco inundação Vale do Ribeira")
- Referências de parceiros (EMBRAPA, instituições de pesquisa)
- Feiras e eventos agropecuários
- Recomendação de extensionistas

**Experiência esperada**:
- Primeiro contato: landing page institucional
- Tempo de resposta: <2s (conectividade rural)
- Primeira impressão: "ferramenta de apoio à decisão", não "mais mapa"

### Etapa 2: ENTENDER O VALOR
**Objetivo**: Compreender em <30s o que a plataforma resolve

**Ponto de inflexão**: Hero section + demonstração funcional

**Conteúdo-chave**:
- Problema: "perda de colheita por inundação/clima"
- Solução: "monitoramento satelital + dados hidrológicos oficiais"
- Diferencial: "focado em bananicultura do Vale do Ribeira"

**CTA**: "Ver demonstração" → vídeo de 60s ou acesso demo

### Etapa 3: CONFIAR
**Objetivo**: Validar credibilidade antes de entrar em contato

**Elementos de prova**:
- Fontes de dados identificadas (SP Águas SIBH, ANA, Sentinel-2)
- Status honesto (disponível/em desenvolvimento)
- Transparência sobre limitações
- Contato com resposta rápida

**Objeções a enfrentar**:
- "Como garantem a qualidade dos dados?"
- "O que acontece se o sistema falhar?"
- "Vou ter que aprender tudo de novo?"

### Etapa 4: AGIR
**Objetivo**: Converter em contato ou trial

**CTA primário**: "Falar com a equipe" (formulário simples)
**CTA secundário**: "Agendar demonstração" (calendário)

**Fluxo de conversão**:
1. Formulário: nome, e-mail, telefone, propriedade (opcional)
2. Auto-resposta: "Recebemos seu contato, retornamos em <24h"
3. Agendamento: calendário integrado (Agile, Calendly)
4. Demo: 30 min focado em caso real do usuário

---

## 2. Arquitetura de Informação

### Estrutura de Navegação (máx. 5 itens no menu principal)

| Item | Destino | Justificativa | Ordem |
|------|---------|---------------|-------|
| **Home** | `/` | Ponto de entrada, reforça valor | 1 |
| **Casos de Uso** | `/casos-de-uso` | Prova de valor concreta | 2 |
| **Sobre** | `/sobre` | Credibilidade institucional | 3 |
| **Blog** | `/blog` | Prova de atividade contínua | 4 |
| **Contato** | `/contato` | Conversão | 5 |

**Menu mobile**: Hambúrguer com lista collapse

### Ordem das Seções na Landing Page

```text
HERO (problema + solução + CTA primário)
   ↓
PROBLEMA (detalhamento do problema do bananicultor)
   ↓
SOLUÇÃO (o que a Ribeira Conecta faz)
   ↓
ECOSISTEMA (5 pilares com status de disponibilidade)
   ↓
PROVAS (fontes de dados, parceiros, status honesto)
   ↓
CONTATO (formulário + CTAs)
```

### Páginas Internas (pós-landing)

| Página | URL | Conteúdo | CTA |
|--------|-----|----------|-----|
| **Home** | `/` | Resumo executivo | Falar com equipe |
| **Casos de Uso** | `/casos-de-uso` | 3-5 casos concretos | Agendar demo |
| **Sobre** | `/sobre` | Missão, time, tecnologia | Falar com equipe |
| **Blog** | `/blog` | Artigos técnicos e notícias | Compartilhar |
| **Contato** | `/contato` | Formulário + info | Enviar |

---

## 3. Roteiro de Navegação

### Rota 1: Avaliador rápido (3 min)
```
Home → Casos de Uso → Sobre → Contato
```
**Foco**: TAM, diferenciação, prova social

### Rota 2: Bananicultor interessado (5 min)
```
Home → Solução → Ecosistema → Casos de Uso → Contato
```
**Foco**: Funcionalidades, valor operacional, confiança

### Rota 3: Parceiro técnico (7 min)
```
Home → Sobre → Blog → Contato
```
**Foco**: Arquitetura, dados, integração

---

## 4. Estratégia de CTAs

### CTA Primário (único por página)
**Objetivo**: Conversão direta (contato/demo)

**Locais**:
- Hero: "Falar com a equipe" (topo, centalizado)
- Sobre: "Falar com a equipe" (topo, direita)
- Contato: "Enviar" (botão de destaque)

**Estados**:
- Normal: Botão verde primário
- Hover: Sombra + leve aumento
- Loading: Ícone de carregamento
- Sucesso: "Enviado! Em breve retornaremos"

### CTA Secundário (contextual)
**Objetivo**: Valor educacional (demo, caso, conteúdo)

**Locais**:
- Hero: "Ver demonstração" (vídeo 60s)
- Casos de Uso: "Ler caso completo" (PDF)
- Blog: "Baixar PDF" (artigo)

---

## 5. Metrificação de Conversão

| Etapa | KPI | Meta inicial | Melhoria |
|-------|-----|--------------|----------|
| Visitas únicas | >500/mês | - | SEO + parcerias |
| Taxa de rejeição <70% | >50% | - | Hero claro |
| Tempo médio >90s | >30% | - | Conteúdo valioso |
| Formulários preenchidos | >20/mês | - | CTAs claros |
| Taxa de abertura e-mail | >40% | - | Segmentação |
| Taxa de agendamento | >30% | - | Follow-up |

---

**Última atualização**: 2026-10-16  
**Próxima revisão**: Após primeira iteração de prototype e testes com 5 usuários
