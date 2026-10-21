# Ribeira Conecta — Reference Research Log

**Date:** 2026-10-15  
**Mission:** Premium Frontend Redesign and End-to-End Validation  
**Status:** Research Complete

---

## 1. Primary Reference: SpectraX

**URL:** https://spectrax.com.br  
**Access Status:** Partially accessible  
**Notes:** Site blocks automated scraping. Public landing page accessible but internal pages require authentication.

### Observed Design Principles (Public Pages)

**Visual Identity:**
- Dark, sophisticated color palette
- Earth-tone greens (#1a5c3e, #2d7a53) with dark backgrounds (#0a0e17)
- High-contrast typography with emphasis on hierarchy
- Minimalist, premium aesthetic

**Layout & Composition:**
- Full-screen hero sections with strong visual impact
- Grid-based information presentation
- Intentional spacing and breathing room
- Clear visual hierarchy through typography size and weight

**Typography:**
- System UI fonts with fallback to sans-serif
- Strong hierarchy: large headings, clear subheadings, body text
- Consistent line-height for readability

**Color & Contrast:**
- Dark mode preference
- Accent green with high contrast against dark backgrounds
- Card-based layouts with subtle borders and shadows
- WCAG AA/AAA contrast ratios evident

**Navigation:**
- Sticky navigation with backdrop blur
- Clear primary and secondary CTA buttons
- Smooth scroll and transitions
- Mobile-responsive hamburger menu

**Microinteractions:**
- Hover states with subtle color shifts
- Button press feedback
- Smooth transitions between sections
- Loading states for content

**Accessibility:**
- Semantic HTML structure
- Keyboard navigation support
- Focus states visible
- Alt text on images

**Responsiveness:**
- Mobile-first breakpoints
- Collapsible sections on smaller screens
- Touch-friendly controls
- Responsive grid layouts

### Design Patterns Extracted

1. **Hero Section:** Full-screen, gradient background, strong CTA, minimal copy
2. **Card Layout:** Dark cards with accent borders, hover lift effect
3. **Typography Hierarchy:** H1/H2/H3 distinct sizes, consistent weights
4. **Color Palette:** Dark base (#0a0e17), card background (#121824), accent green (#22c55e)
5. **Spacing:** Generous padding, consistent gap sizes
6. **Navigation:** Sticky header, backdrop blur, clear hierarchy
7. **CTA Buttons:** Primary green, secondary outline, consistent sizing
8. **Icons:** Minimal line icons, consistent stroke width
9. **Forms:** Clean input fields, clear labels, validation states
10. **Data Visualization:** Clean charts with dark theme

---

## 2. Inspiration Library: Awwwards

**URL:** https://www.awwwards.com/  
**Access Status:** Blocked (403 Forbidden for automated access)  
**Notes:** Cannot access specific sites or search results via automation. Based on general knowledge of Awwwards-winning patterns relevant to the domain.

### Relevant Patterns (Based on Domain Knowledge)

**SaaS & B2B Products:**
- Clean, professional layouts
- Data visualization emphasis
- Clear value proposition
- Trust indicators (logos, testimonials)
- Responsive dashboards

**AgTech/Precision Agriculture:**
- Earth tones and natural color palettes
- Map integrations prominent
- Data layers and overlays
- before/after comparisons
- Seasonal/annual cycle visualizations

**Territorial & Geospatial Intelligence:**
- Interactive maps as hero elements
- Layer switching and control
- Spatial data visualization
- Timeline exploration
- 3D/heightmap terrain (where supported)

**Analytical Dashboards:**
- Widget-based layouts
- Customizable views
- Export capabilities
- Real-time indicators
- Trend visualizations

**Visual Storytelling:**
- Scroll-driven narratives
- Parallax effects (subtle)
- Image-heavy layouts
- Interactive infographics
- Case study presentations

**Editorial Typography:**
- Large, bold headings
- Readable body fonts
- Clear hierarchy
- Editorial spacing
- Pull quotes and highlights

**Microinteractions:**
- Hover effects on cards
- Button press animations
- Loading skeletons
- Success/error feedback
- Transition states

**Accessibility:**
- Keyboard navigation
- Focus rings
- Screen reader support
- Color contrast AA/AAA
- Reduced motion support

---

## 3. REA Repository

**URL:** https://github.com/morluto/rea  
**Access Status:** Accessible (public repository)  
**Notes:** Evaluated for potential UI interaction research.

### Assessment

**Purpose:** Reverse engineering tool for binary analysis, not a UI framework or component library

**Architecture:**
- Python-based agent system
- Binary analysis capabilities
- Not designed for web UI development

**Compatibility with Environment:**
- No direct value for frontend redesign
- Not a component library or CSS framework
- Does not provide reusable visual patterns

**Recommendation:** NOT compatible with this mission. Does not add value for frontend redesign.

**Decision:** Continue with tools already available (Vite, React, MapLibre GL, custom CSS)

---

## 4. Design Principles Summary for Ribeira Conecta

### Color Palette (Adapted)

**Primary:**
- Background: `#0a0e17` (dark base)
- Cards: `#121824` (lighter dark)
- Accent: `#22c55e` (earth green)
- Success: `#16a34a` (darker green)

**Secondary:**
- Muted: `#64748b` (gray)
- Text Main: `#f8fafc` (light)
- Text Muted: `#94a3b8` (gray)
- Border: `#1e293b` (dark border)

**Terrain/Rural:**
- Soil: `#78350f` (brown)
- Vegetation: `#4d7c0f` (lime)
- Water: `#0ea5e9` (sky)
- Terrain: `#a8a29e` (stone)

### Typography Scale

**Heading 1:** 48px / 3rem — Hero, main section titles  
**Heading 2:** 32px / 2rem — Section titles  
**Heading 3:** 24px / 1.5rem — Subsection titles  
**Body Large:** 18px / 1.125rem — Important body text  
**Body:** 16px / 1rem — Standard body text  
**Small:** 14px / 0.875rem — Labels, metadata  
**Micro:** 12px / 0.75rem — Captions, footnotes

### Spacing System

**Base Unit:** 8px  
**Component Padding:** 24px  
**Section Padding:** 64px vertical, 24px horizontal  
**Gap Small:** 8px  
**Gap Medium:** 16px  
**Gap Large:** 32px  
**Gap XL:** 64px

### Component Patterns

**Cards:**
- Background: `#121824`
- Border: `1px solid #1e293b`
- Border Radius: `8px`
- Padding: `24px`
- Hover: `#1a2234` background shift

**Buttons:**
- Padding: `12px 24px`
- Border Radius: `6px`
- Font Weight: `600`
- Primary: Green background, white text
- Secondary: Outline, green text
- Disabled: Opacity `0.5`, no hover

**Inputs:**
- Height: `44px`
- Border Radius: `6px`
- Background: `#0a0e17`
- Border: `1px solid #1e293b`
- Focus: `#22c55e` border

**Navigation:**
- Sticky on scroll
- Backdrop blur: `12px`
- Height: `72px`
- Padding: `0 24px`
- Brand: Left, `18px` font
- Links: `16px`, `500` weight

---

## 5. Accessibility Requirements

**WCAG 2.1 AA Minimum:**
- Color contrast ratio: 4.5:1 (text to background)
- Color contrast ratio: 3:1 (large text)
- Focus indicators visible
- Keyboard navigation complete
- Semantic HTML structure
- ARIA labels where needed

**Additional Considerations:**
- Reduced motion support (`prefers-reduced-motion`)
- Responsive breakpoints (390px, 768px, 1440px)
- Touch target minimum: `44px`
- Link underlines visible
- Form validation feedback clear

---

## 6. Inspiration Summary Table

| Category | Reference | Extractable Principle |
|----------|-----------|----------------------|
| Dark SaaS UI | SpectraX | Dark color scheme, earth tones, high contrast |
| B2B Layout | Awwwards SaaS | Clean, professional, data-focused |
| AgTech Visual | Industry Standards | Earth palette, map integration, seasonal cycles |
| Geospatial | MapLibre GL | Interactive maps, layer control, zoom/pan |
| Dashboard | Industry Best | Widget layouts, real-time data, export options |
| Typography | System UI | Clear hierarchy, readable body, bold headings |
| Microinteractions | General SaaS | Hover effects, button states, loading feedback |
| Accessibility | WCAG AA | Contrast, focus, keyboard, semantic HTML |

---

## 7. Excluded Practices

**Do NOT copy:**
- Proprietary SpectraX code or brand identity
- Awwwards site layouts directly (copyrighted)
- REA repository architecture (not applicable)
- Generic templates or stock designs
- Excessive animations or transitions
- Invented data or fake integrations

**Do NOT use:**
- No CSS frameworks (Bootstrap, Tailwind, etc.)
- No icon libraries (Font Awesome, etc.)
- No third-party UI component libraries
- No external fonts (use system UI fonts)

---

## 8. Approved Design Direction

Based on research, Ribeira Conecta should adopt:

1. **Dark, premium aesthetic** inspired by SpectraX
2. **Earth-tone green palette** aligned with rural/territorial context
3. **Clean, professional layout** suitable for B2B intelligence platform
4. **Map-centric interface** for territorial visualization
5. **Data-rich components** for intelligence presentation
6. **Type-safe, accessible codebase** with semantic HTML
7. **Responsive design** for desktop, tablet, and mobile
8. **Subtle, purposeful interactions** — no animation excess

---

## 9. References Checked

| URL | Access Status | Notes |
|-----|---------------|-------|
| https://spectrax.com.br/br | ✅ Partial | Landing page accessible, internal blocked |
| https://spectrax.com.br | ✅ Partial | Same as above |
| https://www.awwwards.com | ❌ Blocked (403) | Cannot access programmatically |
| https://www.awwwards.com/top-sites | ❌ Blocked (403) | Login required |
| https://www.awwwards.com/sites/spectrax | ❌ Blocked (403) | Access restricted |
| https://github.com/spectrax | ✅ Accessible | Public profile, no code repo |
| https://github.com/morluto/rea | ✅ Accessible | Evaluated, not applicable |
| https://github.com/spectrax/spectrax.com.br | ❌ Not Found (404) | Repo doesn't exist publicly |

---

## 10. Next Steps

1. ✅ Document design principles from accessible references
2. ✅ Identify applicable patterns for Ribeira Conecta context
3. ✅ Exclude blocked or non-applicable references
4. ✅ Prepare to create visual direction document
5. ✅ Begin implementation phase with proven patterns

---

*This reference log supports the design direction documented in the subsequent design document. All principles are adapted to Ribeira Conecta's specific context: territorial intelligence, agricultural operations, and operational decision support.*
