# Ribeira Conecta — Visual Direction Document

**Date:** 2026-10-15  
**Version:** 1.0  
**Mission:** Premium Frontend Redesign and End-to-End Validation  
**Status:** APPROVED FOR IMPLEMENTATION

---

## 1. Executive Summary

This document establishes the visual direction for Ribeira Conecta's frontend redesign. The direction combines research from SpectraX (accessible reference) with industry best practices from SaaS, AgTech, and geospatial intelligence platforms.

**Design Philosophy:** Professional, trustworthy, intelligent, territorial.

**Core Principles:**
- Intelligence first — data clarity over visual complexity
- Territorial authenticity — earth tones, natural palette
- SaaS-grade quality — premium, polished, production-ready
- Accessible by design — WCAG 2.1 AA minimum
- Responsive everywhere — mobile, tablet, desktop

**This is NOT a design mockup.** This is a technical specification for implementation in the existing codebase.

---

## 2. Visual Identity

### 2.1 Brand Positioning

Ribeira Conecta is **NOT** a generic agricultural consulting site.

Ribeira Conecta is a **territorial and business intelligence platform** for rural properties, agriculture, and environmental monitoring.

**Brand Attributes (to be visually expressed):**
- Intelligence — data-driven, analytical, evidence-based
- Trust — professional, reliable, authoritative
- Geographic precision — territorial, spatial, land-focused
- Practical usefulness — operational, actionable, decision-support
- Technical mastery — modern, efficient, capable

**Avoid:**
- Generic templates or stock designs
- Excessive gradients or decorative elements
- "Farming clichés" (tractors, generic crops, stock photos)
- Invented metrics or fabricated data presentation
- Over-engineered interactions

### 2.2 Color Palette

**Primary Dark Theme (SaaS-Grade):**
```css
--color-bg-primary: #0a0e17;      /* Deep dark background */
--color-bg-secondary: #121824;    /* Card/container background */
--color-bg-tertiary: #1a2234;     /* Hover state */
--color-accent-primary: #22c55e;  /* Earth green (accent) */
--color-accent-secondary: #16a34a; /* Darker green (hover) */
--color-accent-success: #15803d;  /* Success state */
```

**Rural/Territorial Palette (Contextual):**
```css
--color-soil: #78350f;           /* Earth brown */
--color-vegetation: #4d7c0f;     /* Lime green */
--color-water: #0ea5e9;          /* Sky blue */
--color-terrain: #a8a29e;        /* Stone gray */
--color-shadow: rgba(0, 0, 0, 0.3); /* Default shadow */
```

**Text Palette:**
```css
--color-text-primary: #f8fafc;   /* Main text (light) */
--color-text-secondary: #94a3b8; /* Muted text */
--color-text-muted: #64748b;     /* Subtle text */
--color-text-accent: #22c55e;    /* Accent text */
```

**Border & Divider:**
```css
--color-border: #1e293b;         /* Dark border */
--color-border-light: #334155;   /* Lighter border */
```

**Contrast Requirements:**
- Text to background: 4.5:1 minimum (WCAG AA)
- Large text (18px+): 3:1 minimum
- UI elements to background: 3:1 minimum

### 2.3 Typography System

**Font Stack (System UI):**
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

**Type Scale:**
| Size | Pixels | REM | Use Case |
|------|--------|-----|----------|
| H1 | 48px | 3rem | Hero sections, main titles |
| H2 | 32px | 2rem | Section titles |
| H3 | 24px | 1.5rem | Subsection titles |
| H4 | 20px | 1.25rem | Panel titles |
| Body Lg | 18px | 1.125rem | Important body text |
| Body | 16px | 1rem | Standard body text |
| Body Sm | 14px | 0.875rem | Labels, metadata |
| Micro | 12px | 0.75rem | Captions, footnotes |
| XMicro | 11px | 0.6875rem | Tiny labels |

**Font Weights:**
- Headers (H1-H4): 700 (bold)
- Subheaders: 600 (semibold)
- Body text: 400 (regular)
- Labels: 500 (medium)
- Metadata: 400 (regular)

**Line Heights:**
- Headers: 1.15
- Body text: 1.6
- Spaced out: 1.8 (instructions, important notes)

**Letter Spacing:**
- Headers: -0.02em
- Body: 0em (normal)
- Labels: 0.01em

### 2.4 Spacing System (8px Base)

**Base Unit:** 8px

**Component Padding:**
- Small: 8px (1 unit)
- Medium: 16px (2 units)
- Large: 24px (3 units)
- XL: 32px (4 units)
- XXL: 48px (6 units)

**Section Spacing:**
- Vertical: 64px (8 units)
- Horizontal: 24px (3 units)

**Gap System:**
- Small: 8px
- Medium: 16px
- Large: 32px
- XL: 48px

**Container Widths:**
- Mobile: 100% (24px padding)
- Tablet: 768px max, centered
- Desktop: 1200px max, centered
- Wide: 1440px max (for dashboards)

---

## 3. Component Design Specification

### 3.1 Navigation Bar (Sticky)

**Structure:**
```html
<nav className="navbar">
  <div className="navbar-container">
    <div className="navbar-brand">
      <span className="brand-dot"></span>
      <span className="brand-text">Ribeira Conecta</span>
    </div>
    <div className="navbar-menu">
      <!-- Navigation links -->
      <a href="#platform">Plataforma</a>
      <a href="#reports">Relatórios</a>
      <a href="#contact">contato@ribeiraconecta.com.br</a>
      <a href="#pilot" className="btn-primary">Acessar Sistema</a>
    </div>
  </div>
</nav>
```

**Styling:**
- Position: fixed, top: 0
- Height: 72px
- Background: rgba(10, 14, 23, 0.85)
- Backdrop filter: blur(12px)
- Border bottom: 1px solid #1e293b
- Z-index: 1000
- Padding: 0 24px (mobile), 0 32px (desktop)
- Centered container: max-width 1200px

**Brand:**
- Font size: 18px
- Font weight: 700
- Display: flex, align-items: center
- Gap: 10px

**Brand Dot:**
- Width: 10px, height: 10px
- Background: #22c55e
- Border radius: 50%
- Box shadow: 0 0 10px rgba(34, 197, 94, 0.5)

**Menu:**
- Display: flex
- Gap: 24px
- Font size: 16px
- Font weight: 500
- Color: #f8fafc

**CTA Button (Acessar Sistema):**
- Background: #22c55e
- Color: #f8fafc
- Padding: 10px 20px
- Border radius: 6px
- Font weight: 600
- Hover: #16a34a background
- Active: scale(0.98)

**Mobile Menu:**
- Hamburger icon (3 lines)
- Overlay menu on click
- Close button (X icon)

### 3.2 Hero Section

**Structure:**
```html
<header className="hero">
  <div className="hero-badge">
    Piloto beta — Inteligência Agro-Territorial
  </div>
  <h1 className="hero-title">
    O território visto de cima.
    <br />
    <span className="hero-title-accent">Decisões precisas na bananicultura.</span>
  </h1>
  <p className="hero-subtitle">
    Transformamos imagens orbitais, dados geoespaciais e ambientais em relatórios de 
    inteligência acionáveis para o manejo, monitoramento de lavouras e expansão 
    sustentável no Vale do Ribeira.
  </p>
  <div className="hero-actions">
    <a href="#platform" className="btn-primary">Explorar Plataforma</a>
    <a href="#reports" className="btn-secondary">Ver Relatórios</a>
  </div>
</header>
```

**Styling:**
- Background: Linear gradient 135deg, #0a0e17 to #121824
- Padding: 120px 24px (mobile), 160px 32px (desktop)
- Text align: center
- Color: #f8fafc

**Badge:**
- Background: rgba(34, 197, 94, 0.1)
- Border: 1px solid rgba(34, 197, 94, 0.3)
- Border radius: 20px
- Padding: 6px 16px
- Font size: 12px
- Font weight: 600
- Color: #22c55e
- Display: inline-block
- Margin bottom: 24px

**Title:**
- Font size: 48px (mobile), 64px (desktop)
- Font weight: 700
- Line height: 1.15
- Margin bottom: 24px

**Title Accent:**
- Background: linear-gradient(135deg, #22c55e, #16a34a)
- Background clip: text
- Color: transparent
- Text gradient: #22c55e → #16a34a

**Subtitle:**
- Font size: 18px
- Line height: 1.6
- Color: #94a3b8
- Max width: 640px
- Margin: 0 auto 48px

**Actions:**
- Display: flex
- Gap: 16px
- Justify center
- Flex wrap: wrap

### 3.3 Cards

**Structure:**
```html
<div className="card">
  <div className="card-header">
    <h3 className="card-title">Nível do Rio</h3>
    <span className="card-status">Última atualização: 2h atrás</span>
  </div>
  <div className="card-body">
    <div className="metric">
      <span className="metric-value">2.34m</span>
      <span className="metric-label">Cota atual</span>
    </div>
    <div className="metric-trend">
      <span className="trend-up">↑ 12cm nas últimas 24h</span>
    </div>
  </div>
</div>
```

**Styling:**
- Background: #121824
- Border: 1px solid #1e293b
- Border radius: 8px
- Padding: 24px
- Transition: all 0.2s ease

**Hover State:**
- Background: #1a2234
- Transform: translateY(-2px)
- Box shadow: 0 8px 24px rgba(0, 0, 0, 0.2)

**Header:**
- Display: flex
- Justify space-between
- Align items: center
- Margin bottom: 16px

**Title:**
- Font size: 18px
- Font weight: 600
- Color: #f8fafc

**Status:**
- Font size: 12px
- Color: #64748b

**Body:**
- Display: grid
- Gap: 12px

**Metric Value:**
- Font size: 36px
- Font weight: 700
- Color: #22c55e
- Line height: 1

**Metric Label:**
- Font size: 12px
- Font weight: 500
- Color: #64748b
- Margin top: 4px

**Trend:**
- Font size: 14px
- Font weight: 500
- Display: flex
- Align items: center
- Gap: 6px

### 3.4 Buttons

**Primary Button:**
```css
.btn-primary {
  background: #22c55e;
  color: #f8fafc;
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: #16a34a;
  transform: translateY(-1px);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-primary:disabled {
  background: #334155;
  cursor: not-allowed;
  transform: none;
}
```

**Secondary Button:**
```css
.btn-secondary {
  background: transparent;
  border: 1px solid #1e293b;
  color: #22c55e;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  border-color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.btn-secondary:active {
  transform: translateY(0);
}

.btn-secondary:disabled {
  border-color: #334155;
  color: #64748b;
  cursor: not-allowed;
}
```

**Ghost Button:**
```css
.btn-ghost {
  background: transparent;
  color: #94a3b8;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #f8fafc;
}

.btn-ghost:disabled {
  color: #334155;
  cursor: not-allowed;
}
```

**Icon Button:**
```css
.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  border-radius: 6px;
  background: #121824;
  border: 1px solid #1e293b;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-icon:hover {
  background: #1a2234;
  color: #f8fafc;
}

.btn-icon:active {
  transform: scale(0.95);
}
```

### 3.5 Forms

**Input:**
```css
.input {
  width: 100%;
  padding: 12px 16px;
  font-size: 16px;
  font-family: inherit;
  background: #0a0e17;
  border: 1px solid #1e293b;
  border-radius: 6px;
  color: #f8fafc;
  transition: all 0.2s ease;
}

.input:focus {
  outline: none;
  border-color: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
}

.input::placeholder {
  color: #64748b;
}

.input:disabled {
  background: #0a0e17;
  border-color: #334155;
  color: #64748b;
  cursor: not-allowed;
}
```

**Label:**
```css
.label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #94a3b8;
}

.label-required::after {
  content: ' *';
  color: #ef4444;
}
```

**Textarea:**
```css
.textarea {
  width: 100%;
  min-height: 120px;
  padding: 12px 16px;
  font-size: 16px;
  font-family: inherit;
  background: #0a0e17;
  border: 1px solid #1e293b;
  border-radius: 6px;
  color: #f8fafc;
  resize: vertical;
  transition: all 0.2s ease;
}

.textarea:focus {
  outline: none;
  border-color: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
}

.textarea::placeholder {
  color: #64748b;
}
```

**Select:**
```css
.select {
  width: 100%;
  padding: 12px 16px;
  font-size: 16px;
  font-family: inherit;
  background: #0a0e17;
  border: 1px solid #1e293b;
  border-radius: 6px;
  color: #f8fafc;
  cursor: pointer;
  transition: all 0.2s ease;
}

.select:focus {
  outline: none;
  border-color: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
}

.select:disabled {
  background: #0a0e17;
  border-color: #334155;
  color: #64748b;
  cursor: not-allowed;
}
```

### 3.6 Badges

**Status Badge:**
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 20px;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.badge-status-ready {
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
}

.badge-status-pending {
  background: rgba(251, 191, 36, 0.1);
  color: #fbbf24;
}

.badge-status-error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.badge-status-info {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}
```

**Metric Badge:**
```css
.badge-metric {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #121824;
  border: 1px solid #1e293b;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #f8fafc;
}
```

### 3.7 Tabs

**Structure:**
```html
<div className="tabs">
  <div className="tabs-nav">
    <button className="tab active" data-tab="satellite">Satélite</button>
    <button className="tab" data-tab="ndvi">NDVI</button>
    <button className="tab" data-tab="hydrology">Hidrologia</button>
    <button className="tab" data-tab="flood">Inundações</button>
  </div>
  <div className="tabs-content">
    <!-- Tab content -->
  </div>
</div>
```

**Styling:**
```css
.tabs {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tabs-nav {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: #0a0e17;
  border-radius: 8px;
  border: 1px solid #1e293b;
}

.tab {
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  color: #94a3b8;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab:hover {
  color: #f8fafc;
}

.tab.active {
  background: #22c55e;
  color: #f8fafc;
}

.tabs-content {
  min-height: 400px;
}
```

### 3.8 Map Controls (MapLibre GL)

**Structure:**
```html
<div className="map-controls">
  <div className="map-control-group">
    <button className="map-control" data-action="zoom-in">
      <span className="icon-plus"></span>
    </button>
    <button className="map-control" data-action="zoom-out">
      <span className="icon-minus"></span>
    </button>
  </div>
  <div className="map-control-group">
    <button className="map-control" data-action="rotate">
      <span className="icon-rotate"></span>
    </button>
    <button className="map-control" data-action="pitch">
      <span className="icon-pitch"></span>
    </button>
  </div>
</div>
```

**Styling:**
```css
.map-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 10;
}

.map-control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.map-control {
  width: 40px;
  height: 40px;
  padding: 0;
  background: #121824;
  border: 1px solid #1e293b;
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.map-control:hover {
  background: #1a2234;
  color: #f8fafc;
  transform: translateY(-1px);
}

.map-control:active {
  transform: translateY(0);
}
```

### 3.9 Loading States

**Skeleton Card:**
```css
.skeleton {
  background: linear-gradient(
    90deg,
    #121824 0%,
    #1a2234 20%,
    #121824 40%,
    #121824 100%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.skeleton-title {
  height: 24px;
  width: 60%;
  margin-bottom: 16px;
  border-radius: 4px;
}

.skeleton-value {
  height: 48px;
  width: 100%;
  margin-bottom: 12px;
  border-radius: 4px;
}

.skeleton-label {
  height: 14px;
  width: 40%;
  border-radius: 4px;
}
```

**Spinner:**
```css
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #22c55e;
  border-radius: 50%;
  animation: spinner 1s linear infinite;
}

@keyframes spinner {
  to { transform: rotate(360deg); }
}
```

### 3.10 Data Tables

**Structure:**
```html
<div className="data-table">
  <div className="table-header">
    <h3 className="table-title">Propriedades</h3>
    <div className="table-controls">
      <input 
        type="text" 
        className="input-search" 
        placeholder="Buscar propriedade..."
      />
      <button className="btn-icon">
        <span className="icon-filter"></span>
      </button>
      <button className="btn-icon">
        <span className="icon-refresh"></span>
      </button>
    </div>
  </div>
  <table className="table">
    <thead>
      <tr>
        <th>Nome</th>
        <th>Área</th>
        <th>Classificação</th>
        <th>Status</th>
        <th>Última atualização</th>
      </tr>
    </thead>
    <tbody>
      <!-- Table rows -->
    </tbody>
  </table>
</div>
```

**Styling:**
```css
.data-table {
  background: #121824;
  border: 1px solid #1e293b;
  border-radius: 8px;
  overflow: hidden;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #1e293b;
}

.table-title {
  font-size: 18px;
  font-weight: 600;
  color: #f8fafc;
  margin: 0;
}

.table-controls {
  display: flex;
  gap: 8px;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 14px 24px;
  text-align: left;
  font-size: 14px;
}

.table th {
  background: #0a0e17;
  font-weight: 600;
  color: #94a3b8;
  border-bottom: 1px solid #1e293b;
}

.table td {
  border-bottom: 1px solid #1e293b;
  color: #f8fafc;
}

.table tr:hover td {
  background: rgba(34, 197, 94, 0.05);
}

.table tr:last-child td {
  border-bottom: none;
}

.input-search {
  width: 240px;
  padding: 10px 14px;
  background: #0a0e17;
  border: 1px solid #1e293b;
  border-radius: 6px;
  color: #f8fafc;
  font-size: 14px;
}

.input-search:focus {
  outline: none;
  border-color: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
}
```

---

## 4. Layout Specifications

### 4.1 Page Layout (Desktop)

```css
.page {
  min-height: 100vh;
  background: #0a0e17;
  display: flex;
  flex-direction: column;
}

.page-content {
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 64px 24px 96px;
  width: 100%;
}

.page-section {
  margin-bottom: 64px;
}

.page-section:last-child {
  margin-bottom: 0;
}
```

### 4.2 Dashboard Layout (Farm360)

```css
.workspace {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a0e17;
}

.workspace-header {
  height: 56px;
  background: #121824;
  border-bottom: 1px solid #1e293b;
  display: flex;
  align-items: center;
  padding: 0 24px;
  justify-content: space-between;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 320px 1fr 320px;
  flex: 1;
  overflow: hidden;
}

.workspace-sidebar {
  border-right: 1px solid #1e293b;
  overflow-y: auto;
  padding: 24px;
}

.workspace-main {
  background: #0a0e17;
  position: relative;
  overflow: hidden;
}

.workspace-panel {
  border-left: 1px solid #1e293b;
  overflow-y: auto;
  padding: 24px;
}
```

### 4.3 Mobile Layout

```css
@media (max-width: 768px) {
  .workspace-grid {
    display: flex;
    flex-direction: column;
  }

  .workspace-sidebar,
  .workspace-panel {
    width: 100%;
    max-height: 40vh;
    border: none;
  }

  .page-content {
    padding: 48px 16px 64px;
  }

  .hero {
    padding: 80px 16px 64px;
  }

  .hero-title {
    font-size: 36px;
  }

  .card {
    padding: 16px;
  }
}
```

---

## 5. Animation & Microinteractions

### 5.1 Animation Principles

**General Rules:**
- Purposeful, not decorative
- Subtle and quick (150-300ms)
- Respect prefers-reduced-motion
- Smooth easing (cubic-bezier)
- Consistent across components

**Easing Functions:**
```css
--easing-default: cubic-bezier(0.4, 0, 0.2, 1);
--easing-smooth: cubic-bezier(0.25, 1, 0.5, 1);
--easing-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

### 5.2 Component Animations

**Button Hover:**
```css
.btn-primary:hover {
  transform: translateY(-1px);
  transition: transform 0.2s var(--easing-default);
}

.btn-primary:active {
  transform: translateY(0);
}
```

**Card Hover:**
```css
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  transition: all 0.3s var(--easing-default);
}
```

**Fade In:**
```css
.fade-in {
  animation: fadeIn 0.5s var(--easing-default) forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**Slide In:**
```css
.slide-in {
  animation: slideIn 0.4s var(--easing-default) forwards;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
```

### 5.3 Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 6. Responsive Breakpoints

| Breakpoint | Width | Description |
|------------|-------|-------------|
| Mobile | 390px | Small mobile (iPhone SE, etc.) |
| Mobile Lg | 480px | Larger mobile (iPhone 12-14, etc.) |
| Tablet | 768px | Portrait tablet, landscape phone |
| Tablet Lg | 1024px | Landscape tablet |
| Desktop | 1440px | Desktop, laptop |
| Desktop Lg | 1920px | Large desktop |

**Breakpoint Variables:**
```css
--breakpoint-mobile: 390px;
--breakpoint-mobile-lg: 480px;
--breakpoint-tablet: 768px;
--breakpoint-tablet-lg: 1024px;
--breakpoint-desktop: 1440px;
--breakpoint-desktop-lg: 1920px;
```

**Mobile-First Approach:**
- Start with mobile styles
- Use min-width media queries
- Progressive enhancement

---

## 7. Accessibility Specifications

### 7.1 Keyboard Navigation

**Focus Styles:**
```css
:focus {
  outline: 2px solid #22c55e;
  outline-offset: 2px;
}

:focus:not(:focus-visible) {
  outline: none;
}

:focus-visible {
  outline: 2px solid #22c55e;
  outline-offset: 2px;
}
```

**Focus Order:**
- Logical, predictable order
- Skip links for navigation
- Focus trapped in modals
- Focus restored on modal close

### 7.2 Screen Reader Support

**ARIA Labels:**
```html
<button aria-label="Zoom in" className="map-control">
  <span className="icon-plus" aria-hidden="true"></span>
</button>

<span className="visually-hidden">Última atualização: 2 horas atrás</span>
```

**Landmarks:**
```html
<header className="site-header" role="banner">
  <!-- Header content -->
</header>

<nav className="site-nav" role="navigation">
  <!-- Navigation -->
</nav>

<main className="site-main" role="main">
  <!-- Main content -->
</main>

<footer className="site-footer" role="contentinfo">
  <!-- Footer content -->
</footer>
```

### 7.3 Color Contrast

**Minimum Ratios:**
- Text to background: 4.5:1 (normal text)
- Text to background: 3:1 (large text 18px+)
- UI elements: 3:1
- Focus indicators: visible against all backgrounds

**Contrast Checker:**
- Test all color combinations
- Verify AA compliance
- Test in high contrast mode

### 7.4 Interactive Elements

**Touch Targets:**
- Minimum 44px × 44px
- Adequate spacing (8px minimum)
- No touch target overlap

**Hover States:**
- Also provide keyboard focus
- Consider hover-only features carefully
- Ensure functionality without hover

---

## 8. Performance Considerations

### 8.1 CSS Optimization

**Minimize:**
- Unused styles
- Deep selectors (avoid > 3 levels)
- Repetitive declarations
- Critical CSS inline

**Optimize:**
- Use CSS variables for theming
- Use flexbox/grid over floats
- Use transform/opacity for animations
- Lazy load non-critical styles

### 8.2 Loading Performance

**Critical CSS:**
- Inline essential styles
- Defer non-critical stylesheets
- Preload critical fonts

**Images:**
- Use modern formats (WebP, AVIF)
- Responsive images
- Lazy loading
- Proper sizing

**Fonts:**
- Use system UI fonts where possible
- Preload custom fonts
- Use font-display: swap
- Subset fonts when possible

---

## 9. Implementation Checklist

### 9.1 Components to Implement

- [ ] Navigation bar (sticky, responsive)
- [ ] Hero section
- [ ] Feature cards
- [ ] Data table
- [ ] Status badges
- [ ] CTA buttons (primary, secondary, ghost)
- [ ] Form inputs (text, textarea, select)
- [ ] Map controls (zoom, rotate, pitch)
- [ ] Loading states (skeleton, spinner)
- [ ] Tabs
- [ ] Modals
- [ ] Toast notifications
- [ ] Pagination
- [ ] Search input
- [ ] Filter controls

### 9.2 Pages to Redesign

- [ ] Landing page (HomePage)
- [ ] Workspace shell (PilotShell)
- [ ] Property workspace (PropertyWorkspace)
- [ ] Farm360 main (Farm360Page)
- [ ] All feature panels (map, ndvi, hydrology, etc.)

### 9.3 Responsive Breakpoints

- [ ] Mobile (390px)
- [ ] Tablet (768px)
- [ ] Desktop (1440px)

### 9.4 Accessibility Checks

- [ ] Keyboard navigation
- [ ] Focus states
- [ ] ARIA labels
- [ ] Color contrast
- [ ] Screen reader test
- [ ] Reduced motion support

---

## 10. Design Principles Summary

**Remember:**
1. Intelligence first — data clarity over visual complexity
2. Territorial authenticity — earth tones, natural palette
3. SaaS-grade quality — premium, polished, production-ready
4. Accessible by design — WCAG 2.1 AA minimum
5. Responsive everywhere — mobile, tablet, desktop

**Avoid:**
- Generic templates
- Excessive gradients
- "Farming clichés"
- Invented data
- Over-engineered interactions

**Focus on:**
- Data presentation
- Territorial context
- Operational utility
- Professional quality
- Trust signals

---

**Document Status:** APPROVED FOR IMPLEMENTATION  
**Next Phase:** Phase 4 — Implementation  
**Version:** 1.0  
**Date:** 2026-10-15
