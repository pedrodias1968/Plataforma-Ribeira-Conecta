# Referências Técnicas e Decisões de UX

Este documento lista as referências públicas utilizadas como base para decisões de UX e arquitetura da Ribeira Conecta, com ênfase em práticas de desenvolvimento frontend moderno, especialmente para a landing page e plataforma geoespacial.

---

## 1. Vite — Next Generation Frontend Tooling

**URL:** https://vitejs.dev  
**Acesso:** 16 out 2026  
**Status:** ACESSÍVEL  

### Decisões de UX extraídas:

- **Hot Module Replacement (HMR) instantâneo:** O Vite serve arquivos sob demanda via ESM nativo, permitindo atualizações quase instantâneas durante o desenvolvimento. Isso sustenta o workflow iterativo de design e validação visual rápida.
- **Build otimizado por padrão:** Minificação, tree-shaking e code splitting integrados reduzem o bundle final, melhorando tempo to First Contentful Paint (FCP) e Time to Interactive (TTI).
- **Configuração minimalista:** Vite funciona sem configuração inicial, alinhando-se à estratégia de "convenção sobre configuração" para landing pages que precisam carregar rápido.

### Aplicação na Ribeira Conecta:

- Usado como bundler principal para frontend React
- Configuração atual minimalista em `frontend/vite.config.ts`
- Builds geram chunks otimizados em `frontend/dist/assets/`

---

## 2. React — Official Documentation

**URL:** https://react.dev  
**Acesso:** 16 out 2026  
**Status:** ACESSÍVEL  

### Decisões de UX extraídas:

- **Component-based architecture:** Encapsula lógica, estado e UI em componentes reutilizáveis, essencial para landing pages com seções modulares (features, hero, CTA).
- **Server-side rendering (SSR) e Static Site Generation (SSG):** Para landing pages públicas, pré-renderização melhora SEO e tempo de carregamento inicial.
- **Code splitting automático:** Importação dinâmica (`React.lazy` + `Suspense`) permite carregar apenas o necessário por rota.

### Aplicação na Ribeira Conecta:

- React 19.1.1 usado como framework principal
- Páginas separadas em `frontend/src/pages/` (LandingPage, Farm360Page, HomePage)
- **PENDÊNCIA:** Code splitting não implementado ainda — a landing e app compartilham o mesmo bundle

---

## 3. MapLibre GL JS — Open Source Mapping

**URL:** https://maplibre.org  
**Acesso:** 16 out 2026  
**Status:** ACESSÍVEL  

### Decisões de UX extraídas:

- **Vector tiles rendering via GPU:** Mapas interativos fluidos com zoom/pan sem degradar qualidade.
- **Custom styles e layers:** Permite sobrepor camadas temáticas (NDVI, inundação, talhões) sobre mapas base.
- **Worker-based architecture:** Renderização assíncrona evita bloqueio da main thread.

### Aplicação na Ribeira Conecta:

- `maplibre-gl` v6.10.0 é dependência principal
- MapCanvas component em `frontend/src/features/map/MapCanvas.tsx` (535 linhas)
- **Problemática identificada:** O worker do MapLibre é carregado como chunk separado (`maplibre-gl-worker-BBYVuMpd.js`, 509KB), mas ainda contribui para o bundle total.

---

## 4. TypeScript Handbook

**URL:** https://www.typescriptlang.org/docs/handbook/intro.html  
**Acesso:** 16 out 2026  
**Status:** ACESSÍVEL  

### Decisões de UX extraídas:

- **Type safety em tempo de desenvolvimento:** Reduz erros de runtime e melhora DX com autocompletar em IDEs.
- **JSDoc + interfaces:** Permite documentar componentes públicos e contratos de API diretamente no código.
- **Migração gradativa:** TypeScript pode ser adicionado a projetos JS existente incrementalmente.

### Aplicação na Ribeira Conecta:

- TypeScript 5.9.2 configurado em `tsconfig.app.json`
- Todos os arquivos `.tsx` têm tipagem explícita
- Tipos como `StatusBadgeProps`, `IconProps` em `LandingPage.tsx` seguem boas práticas

---

## 5. Web Content Accessibility Guidelines (WCAG) 2.1

**URL:** https://www.w3.org/WAI/standards-guidelines/wcag/  
**Acesso:** 16 out 2026  
**Status:** ACESSÍVEL  

### Decisões de UX extraídas:

- **Contraste mínimo de 4.5:1** para texto normal (nível AA)
- **Navegação por teclado** deve ser possível em todos os estados
- **Textos alternativos (alt)** para imagens e ícones não decorativos
- **Estrutura semântica HTML5** (header, main, footer, sections)

### Aplicação na Ribeira Conecta:

- **PENDÊNCIA:** Nenhum teste de acessibilidade (a11y) implementado ainda
- Ícones SVG em `LandingPage.tsx` não têm atributos `aria-label` ou `role`
- Contraste de cores deve ser auditado com ferramentas como axe-core ou Lighthouse

---

## 6. Lighthouse Performance Metrics

**URL:** https://developer.chrome.com/docs/lighthouse/performance/  
**Acesso:** 16 out 2026  
**Status:** ACESSÍVEL  

### Decisões de UX extraídas:

- **First Contentful Paint (FCP)** < 1.8s (bom)
- **Time to Interactive (TTI)** < 3.8s (bom)
- **Total Blocking Time (TBT)** < 200ms (bom)
- **LCP (Largest Contentful Paint)** < 2.5s (bom)

### Aplicação na Ribeira Conecta:

- **Problemática identificada:** Bundle JS inicial de 1.38MB (index-BTtBZG4i.js) vai violar todos os métricas acima em conexões lentas
- Code splitting é essencial para atingir métricas de "bom" ou "excelente"

---

## Referências Não Acessíveis / Limitações

| Referência | URL | Motivo | Status |
|-----------|-----|--------|--------|
| React Router DOM v6 | https://reactrouter.com | Acesso restrito por rate-limiting | ACESSO NEGADO |
| Vite code splitting guide | https://vitejs.dev/guide/features.html#code-splitting | Conteúdo truncado na webfetch | ACESSO PARCIAL |
| MapLibre API docs | https://maplibre.org/maplibre-gl-js-docs/api/ | 404 Not Found | ACESSO NEGADO |
| React.lazy docs | https://react.dev/reference/react/code-splitting | 404 Not Found | ACESSO NEGADO |
| WCAG 2.2 (latest) | https://www.w3.org/TR/WCAG22/ | Tempo de timeout excedido | TIMEOUT |
| Lighthouse CI docs | https://github.com/GoogleChrome/lighthouse-ci | Acesso limitado | ACESSO PARCIAL |

---

## Métricas Atuais do Bundle (antes do code splitting)

```
frontend/dist/assets/index-BTtBZG4i.js      1.38 MB  (JS principal)
frontend/dist/assets/index-R3TEyrTf.css      112 KB  (CSS)
frontend/dist/assets/maplibre-gl-worker-BBYVuMpd.js  509 KB  (worker separado)
TOTAL: 1.99 MB
```

### Decomposição provável do JS (1.38 MB):

- React 19 runtime + JSX Runtime: ~100 KB
- MapLibre GL JS: ~250 KB (incluído no bundle principal)
- TypeScript runtime helpers: ~20 KB
- Componentes do app (LandingPage, Farm360, etc.): ~800 KB+
- Dependencies e polyfills: ~110 KB

---

## Recomendações de UX Baseadas nas Referências

1. **Priorizar code splitting**
   - Separar landing (pública) do app (protegido)
   - Lazy-load de componentes pesados (MapCanvas, NDVI, Flood panels)
   - Alvo: reduzir JS inicial para < 200 KB

2. **Implementar lazy loading de imagens e fontes**
   - Usar `loading="lazy"` em `img` tags
   - Fontes com `display: swap` para evitar FOIT

3. **Adicionar a11y audit**
   - Ferramentas: axe-core, Lighthouse CI, DOM a11y plugin
   - Verificar contraste, navegação por teclado, labels

4. **Otimizar Google Fonts (se usado)**
   - Subset de caracteres (latim apenas)
   - Preload de fonts críticas

5. **Implementar SSR/SSG para landing**
   - Vite SSR ou gerar HTML estático
   - Melhora SEO e FCP

---

## Próximos Passos (Fase 3)

| Tarefa | Prioridade | Status |
|-------|-----------|--------|
| Criar REFERENCIAS.md | HIGH | ✅ CONCLUÍDO |
| VITE_RIBEIRA_PUBLIC_ORIGIN | HIGH | pendente validação |
| Code splitting | MEDIUM | pendente implementação |
| Screenshots validação | MEDIUM | pendente captura |
| Status honesto dos componentes | MEDIUM | pendente documentação |
