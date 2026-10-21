# Direção Visual

## 1. Paleta de Cores

### Cores Principais

| Função | Hex | Uso | Contra-Exemplo |
|--------|-----|-----|----------------|
| **Verde Primário** | `#16a34a` (emerald-600) | Botões CTA primários, links ativos | N/A |
| **Verde Secundário** | `#15803d` (emerald-700) | Botões hover, badges "DISPONÍVEL" | N/A |
| **Verde Claro** | `#f0fdf4` (emerald-50) | Fundo de hero, destaques | N/A |
| **Cinza Escuro** | `#1e293b` (slate-800) | Texto principal, headings | N/A |
| **Cinza Médio** | `#64748b` (slate-500) | Texto secundário, labels | N/A |
| **Cinza Claro** | `#f1f5f9` (slate-100) | Fundo de cards, separadores | N/A |
| **Branco** | `#ffffff` | Fundo de body, modais | N/A |

### Cores de Status

| Status | Hex | Uso |
|--------|-----|-----|
| **DISPONÍVEL** | `#15803d` (emerald-700) | Badge, texto |
| **EM DESENVOLVIMENTO** | `#0ea5e9` (sky-500) | Badge, texto |
| **PLANEJADO** | `#64748b` (slate-500) | Badge, texto |
| **ERRO** | `#dc2626` (red-600) | Mensagens de erro |
| **AVISO** | `#f59e0b` (amber-500) | Avisos |

### Regras de Aplicação
- **Hero**: Verde claro (#f0fdf4) como fundo, verde escuro (#15803d) para CTA
- **Cards**: Branco (#ffffff) com sombra leve (#0000000d)
- **Textos**: Cinza escuro (#1e293b) para primário, cinza médio (#64748b) para secundário
- **Links**: Verde primário (#16a34a)
- **Botões**: Verde primário (#16a34a) para CTA, verde escuro (#15803d) para hover

---

## 2. Tipografia

### Fonte Principal: Inter (Google Fonts)

| Uso | Tamanho | Peso | Line Height |
|-----|---------|------|-------------|
| **H1 (Hero)** | 48px | 700 | 56px |
| **H2** | 36px | 700 | 44px |
| **H3** | 28px | 600 | 36px |
| **H4** | 22px | 600 | 30px |
| **H5** | 18px | 600 | 26px |
| **H6** | 16px | 600 | 24px |
| **Body (p)** | 16px | 400 | 26px |
| **Body Small** | 14px | 400 | 22px |
| **Micro (labels)** | 12px | 500 | 18px |
| **CTA Button** | 16px | 600 | 24px |

### Regras de Hierarquia
- **Hero**: H1 com 48px, uma ideia (problema + solução)
- **Seções**: H2 com 36px, uma ideia por seção
- **Subseções**: H3 com 28px, detalhamento

---

## 3. Grid e Espaçamento

### Grid System
- **Container máximo**: 1180px (centro, 20px padding lateral)
- **Grid de cards**: 2 colunas (mobile: 1 coluna)
- **Gaps**: 20px entre elementos, 40px entre seções

### Escala de Espaçamento
| Nome | Valor | Uso |
|------|-------|-----|
| **xs** | 4px | Ícones pequenos, badge padding |
| **sm** | 8px | Botões pequenos, labels |
| **md** | 16px | Parágrafos, cards |
| **lg** | 24px | Títulos, seções pequenas |
| **xl** | 40px | Seções grandes, hero padding |
| **2xl** | 64px | Entre seções |

### Regras de Layout
- **Hero**: 64px padding top/bottom, 20px lateral
- **Cards**: 24px padding interno, 20px gap
- **Formulários**: 16px gap entre campos

---

## 4. Linguagem de Mapa/Território

### Elementos Visuais
- **Mapa**: MapLibre GL, estilo "outdoors" (verde para vegetação, azul para água)
- **Ícones**: SVG line icons (stroke: 2px, fill: none)
- **Cor de mapa**: Verde médio (#16a34a) para áreas verdes, azul claro (#bae6fd) para água

### Regras de Uso
- **Mapa no Hero**: Mapa simplificado com marker (não mapa complexo)
- **Mapa em demonstração**: Mapa interativo com camadas
- **Ícones**: SVG inline (não fontes), stroke: 2px

---

## 5. Tratamento de Imagens

### Fontes de Imagem
- **Mapas**: MapLibre GL (renderizado no navegador)
- **Ícones**: SVG inline (não arquivos externos)
- **Fotos de bananeira**: Imagens de alta qualidade, comprimidas (WebP)

### Regras
- **Sem imagens externas**: Todos os SVGs inline
- **Imagens otimizadas**: WebP, dimensões fixas
- **Lazy load**: Apenas imagens fora do viewport

---

## 6. Motion e Transições

### Regras de Motion
- **Sem carousels automáticos**: Usuários controlam
- **Transições rápidas**: <100ms (não >200ms)
- **Nenhum parallax**: Apenas transições simples
- **Respeitar prefers-reduced-motion**: Se o usuário pediu, não animar

### Exemplos de Motion
- **Hover botão**: Sombra + leve aumento (scale: 1.05)
- **Carregamento**: Ícone rotativo (SVG)
- **Formulário sucesso**: Checkmark (fade-in)

---

## 7. Tokens de Design (CSS Variables)

```css
:root {
  /* Cores */
  --color-primary: #16a34a;
  --color-primary-dark: #15803d;
  --color-primary-light: #f0fdf4;
  --color-slate-800: #1e293b;
  --color-slate-500: #64748b;
  --color-slate-100: #f1f5f9;
  --color-white: #ffffff;
  --color-red-600: #dc2626;
  --color-amber-500: #f59e0b;

  /* Tipografia */
  --font-family: 'Inter', sans-serif;
  --font-size-h1: 48px;
  --font-size-h2: 36px;
  --font-size-h3: 28px;
  --font-size-body: 16px;
  --font-size-micro: 12px;
  --font-weight-header: 700;
  --font-weight-label: 600;
  --font-weight-body: 400;
  --line-height-header: 1.15;
  --line-height-body: 1.625;
  --line-height-spaced: 1.375;

  /* Espaçamento */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 40px;
  --spacing-2xl: 64px;

  /* Border radius */
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 20px;

  /* Shadow */
  --shadow-sm: 0 1px 2px #0000000d;
  --shadow-md: 0 4px 6px -1px #0000001a, 0 2px 4px -1px #0000000d;
  --shadow-lg: 0 10px 15px -3px #0000001a, 0 4px 6px -2px #0000000d;
}
```

---

## 8. Mobile-First (Breakpoints)

| Dispositivo | Largura | Layout |
|-------------|---------|--------|
| **Mobile** | < 768px | 1 coluna, CTA no topo |
| **Tablet** | 768px - 1024px | 2 colunas, CTA fixo |
| **Desktop** | > 1024px | Container 1180px, CTA à direita |

### Regras de Responsividade
- **Mobile**: Botão CTA sempre visível (fixo ou no topo)
- **Tablet**: Menu collapse (hambúrguer)
- **Desktop**: Menu horizontal (não collapse)

---

## 9. Acessibilidade (WCAG 2.2 AA)

### Contraste Mínimo
- Texto normal: ≥ 4.5:1 (verificado)
- Texto grande: ≥ 3:1 (verificado)
- Botão CTA: ≥ 4.5:1 (verificado)

### Foco Visível
- Outline 2px em todos os elementos interativos
- Cor: #0096ff (azul claro)

### Alvos de Toque
- Mínimo 44x44px para touch (verificado)

---

## 10. Responsabilidades por Elemento

| Elemento | Responsável |
|----------|-------------|
| **Hero** | Product Designer + UX Lead |
| **Seções** | Product Designer + Frontend Engineer |
| **Formulários** | Frontend Engineer + Product Designer |
| **Mapa** | Frontend Engineer (MapLibre) |
| **Ícones** | Frontend Engineer (SVG) |

---

**Última atualização**: 2026-10-16  
**Próxima revisão**: Após primeira iteração de prototype
