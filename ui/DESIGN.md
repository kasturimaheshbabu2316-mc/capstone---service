---
name: Spatial Intelligence Desk
colors:
  surface: '#0f131d'
  surface-dim: '#0f131d'
  surface-bright: '#353944'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#171c25'
  surface-container: '#1b2029'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2f0'
  on-surface-variant: '#b9cacb'
  inverse-surface: '#dfe2f0'
  inverse-on-surface: '#2c303b'
  outline: '#849495'
  outline-variant: '#3a494b'
  surface-tint: '#00dce6'
  primary: '#e0fdff'
  on-primary: '#00373a'
  primary-container: '#00f2fe'
  on-primary-container: '#006a70'
  inverse-primary: '#00696f'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#fff5f4'
  on-tertiary: '#670211'
  tertiary-container: '#ffd0ce'
  on-tertiary-container: '#aa373b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6ff6ff'
  primary-fixed-dim: '#00dce6'
  on-primary-fixed: '#002022'
  on-primary-fixed-variant: '#004f53'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffdad8'
  tertiary-fixed-dim: '#ffb3b0'
  on-tertiary-fixed: '#410006'
  on-tertiary-fixed-variant: '#881d24'
  background: '#0f131d'
  on-background: '#dfe2f0'
  surface-variant: '#31353f'
typography:
  display:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.08em
  code-tabular:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 1.5rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes an ultra-refined, high-velocity mission-control experience for AI-augmented ride-hailing support and dispute intelligence operations. The aesthetic fuses **Spatial Glassmorphism** with **Precision Mission Critical Dark UI**. 

Designed for operations directors, incident triage teams, and automated policy adjudication bots, the interface eliminates cognitive friction across dense streams of live telematics, passenger-driver disputes, dynamic surcharge audits, and safety escalations.

The emotional tone balances institutional authority with cutting-edge real-time visibility:
- **Spatial Luminosity:** Translucent frosted planes hover over an infinite abyssal slate canvas, establishing distinct cognitive processing strata.
- **Surgical Precision:** Every analytical variable, GPS ping, SLA counter, and currency calculation carries unambiguous optical balance.
- **Controlled Urgency:** Vivid photonic beacons (Cyan, Emerald, Amber, Coral) pierce the layered glass only when human attention or intervention is mathematically required.

## Colors

The palette is engineered specifically for OLED/high-density professional displays in low-glare operations control rooms. Dark foundation layers prevent retinal fatigue during 12-hour operational shifts, while high-chroma cyan and status-bearing pigments provide zero-latency state recognition.

### Palette Architecture
- **Primary Canvas (`#070B14`):** The foundational substrate—a deep, light-absorbing slate navy void that anchors all spatial layers.
- **Primary Accent (`#00F2FE` - Hyper Cyan):** Used for AI inference highlights, active route trajectories, automated suggestions, focused interactive elements, and critical telemetry pathways.
- **Verified / Safe (`#10B981` - Verified Emerald):** Denotes automated claim approvals, verified identity tokens, completed routes, compliant driver metrics, and SLA adherence.
- **Warning / Scrutiny (`#F59E0B` - Amber Flare):** Flags route deviations, anomalous surcharge spikes, policy gray areas, and approaching SLA thresholds.
- **Alert / Violation (`#F87171` - Alert Coral):** Demands immediate triage—SOS trigger pings, safety incident escalations, chargeback disputes, and policy violations.

### Surface Color Semantics
- **Glass Base Canvas:** `rgba(15, 23, 42, 0.65)` layered over `#070B14`.
- **Glass Active Card:** `rgba(30, 41, 59, 0.45)` with top-lit gradient `linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%)`.
- **Receipt Slip High-Contrast Panel:** Dense solid contrast plate `#0F172A` with perimeter halo `rgba(0, 242, 254, 0.15)`.
- **Text Layers:** Primary text `rgba(255, 255, 255, 0.95)`, Secondary metadata `rgba(148, 163, 184, 0.80)`, Tertiary audit trail `rgba(100, 116, 139, 0.65)`.

## Typography

The typographic system relies on **Inter** configured with advanced OpenType feature flags. The goal is clinical legibility under rapid visual parsing.

### OpenType Execution Rules
- Always activate `cv05` (l with tail), `cv11` (single-storey a), and `zero` (slashed zero) to prevent character confusion during incident reviews.
- For all numerical streams (timestamps, trip fares, GPS coordinates, vehicle registrations, and SLA countdowns), strictly enforce OpenType `tnum` (Tabular Numbers) and `ss01` for absolute vertical alignment down multi-row data tables.

### Hierarchy & Scale Rules
- **Display & Headlines:** Used for live incident counts, city cluster names, and critical policy outcome summaries. Rendered with tight negative tracking to maintain punch and reduce headline footprint.
- **Labels & Micro-Data:** Set in uppercase with expanded positive tracking (`0.04em` to `0.08em`) to guarantee immediate decipherability even at 10px across transparent status badges and SLA track counters.

## Layout & Spacing

The layout is built upon an adaptive 12-column spatial canvas with a dense 4px baseline sub-grid. It optimizes horizontal data density without cluttering visual breathing room.

### Form Factor Adaptations
- **Desktop (1440px+):** Tri-panel operational layout.
  - Left panel (280px fixed): Queue status, policy rulesets, triage filters.
  - Center workspace (Flex 6-7 cols): Live spatial map overlay, real-time rider-driver communication streams, route breadcrumbs.
  - Right panel (380px fixed): AI adjudicator, receipt slip contrast breakdown, trip telemetry inspector, and one-click policy resolution triggers.
  - Layout: `gutter-lg` (24px), outer canvas `margin-lg` (32px).
- **Tablet (768px - 1439px):** Split-view. Navigation condenses to an icon-rail; center operational canvas and right inspection dock stack into tabbed spatial glass panes. Layout uses `gutter` (16px) and `margin-md` (24px).
- **Mobile (< 768px):** Single-column stacked stream. Map telematics converts into a collapsed drawer. Receipt slips and SLA countdowns lock to fixed bottom glass action sheets. Outer canvas uses `margin` (16px).

## Elevation & Depth

Spatial Glassmorphism in this design system is physical and layered, avoiding decorative ambiguity. Depth communicates priority, latency, and context stratification.

### The Glass Layer Stack
1. **Level 0 (Abyssal Void Canvas):** Solid background `#070B14` containing faint atmospheric radial gradients of deep indigo (`rgba(15, 23, 42, 0.40)`).
2. **Level 1 (Docked Shells & Data Rail Glass):** 
   - Background: `rgba(15, 23, 42, 0.60)`
   - Backdrop Filter: `blur(16px) saturate(180%)`
   - Border: `1px solid rgba(255, 255, 255, 0.08)`
   - Shadow: `0 4px 20px -2px rgba(0, 0, 0, 0.5)`
3. **Level 2 (Interactive Cards & Incident Panels):**
   - Background: `rgba(30, 41, 59, 0.45)`
   - Backdrop Filter: `blur(16px) saturate(190%)`
   - Border: `1px solid rgba(255, 255, 255, 0.12)`
   - Inset Highlight: `inset 0 1px 0 0 rgba(255, 255, 255, 0.10)`
   - Shadow: `0 8px 32px 0 rgba(0, 0, 0, 0.45)`
4. **Level 3 (Floating HUDs, Modals & Active Dispute Flyouts):**
   - Background: `rgba(15, 23, 42, 0.85)`
   - Backdrop Filter: `blur(24px) saturate(200%)`
   - Border: `1px solid rgba(0, 242, 254, 0.35)`
   - Shadow: `0 16px 48px -4px rgba(0, 0, 0, 0.75), 0 0 24px -2px rgba(0, 242, 254, 0.15)`
5. **Level 4 (Receipt Slip High-Contrast Plate):**
   - A specialized, semi-opaque tactile sheet (`#0F172A`) sitting with high planar elevation. It does not blur its underlay completely; it acts as an ink-like, high-contrast surface for auditable monetary and tariff ledgers.

## Shapes

The design system employs a structured, aerodynamic curvature profile that balances enterprise ergonomics with futuristic spatial aesthetics.

- **Standard Containers & Cards (`rounded` - 8px / 0.5rem):** Used for analytical cards, chat interaction bubbles, tabular frames, and form inputs.
- **Glass Modals & Flyout Sheets (`rounded-lg` - 16px / 1rem):** Softens larger spatial planes to create floating cockpit visual affordances.
- **Telemetry Chips & SLA Badges (`rounded-full` / Pill-shape):** Micro-indicators, operational status tags, and time-remaining pills use full radial rounding to contrast against rectangular data modules.
- **Border Treatment:** All structural borders are hard-limited to `1px solid` with dynamic opacity masks (`rgba(255, 255, 255, 0.10)` default; elevated to `rgba(0, 242, 254, 0.40)` on hover or active AI inference states).

## Components

### 1. Buttons
- **Primary Cyber-Action (AI Override / Adjudicate):** Linear gradient background `linear-gradient(135deg, #00F2FE 0%, #00B4D8 100%)`, text `#070B14` (Font weight 700), subtle inner border highlight, external glow `0 0 16px rgba(0, 242, 254, 0.35)`.
- **Secondary Glass Button:** `rgba(255, 255, 255, 0.05)` fill, `1px solid rgba(255, 255, 255, 0.12)` border, text `#FFFFFF`. Hover: `rgba(255, 255, 255, 0.10)` fill with `rgba(0, 242, 254, 0.30)` border.
- **Destructive/Emergency Button:** `rgba(248, 113, 113, 0.15)` fill, `1px solid rgba(248, 113, 113, 0.40)` border, text `#F87171`. Glow on hover: `0 0 16px rgba(248, 113, 113, 0.35)`.

### 2. SLA Badges & Chips
- Compact pills (`h-6`, padding: `2px 8px`, `rounded-full`).
- **Critical Breached:** Fill `rgba(248, 113, 113, 0.12)`, text `#F87171`, border `rgba(248, 113, 113, 0.25)`, glowing pulsing dot at `4px` diameter.
- **Warning Approaching:** Fill `rgba(245, 158, 11, 0.12)`, text `#F59E0B`, border `rgba(245, 158, 11, 0.25)`.
- **Compliant:** Fill `rgba(16, 185, 129, 0.12)`, text `#10B981`, border `rgba(16, 185, 129, 0.25)`.
- Numbers set strictly with tabular alignment.

### 3. Status Tracks (Timeline & Dispute Lifecycle)
- A vertical or horizontal 2px line rendered with `rgba(255, 255, 255, 0.08)` track base.
- Step nodes consist of 10px concentric circles: `2px` core with glowing ring. Active step glows with Hyper Cyan (`#00F2FE`) drop shadow.
- Completed progress tracks illuminate in Verified Emerald (`#10B981`).

### 4. Receipt Slip Contrast Cards
- Dedicated high-contrast component for fare audits, driver payouts, and rider overcharges.
- Deep solid navy background `#0F172A` paired with a sharp 1px dashed separator (`rgba(255, 255, 255, 0.15)`).
- Top section contains tabular metadata: Base fare, Wait time, Surge multiplier (illuminated in `#F59E0B`), Toll charges, and Tax withholdings.
- Bottom section presents dynamic dispute delta calculations in high-visibility `#00F2FE` or `#10B981` typography.

### 5. Input Fields
- Fill: `rgba(7, 11, 20, 0.70)`.
- Border: `1px solid rgba(255, 255, 255, 0.10)`.
- Focus State: Border transitions to `#00F2FE` with an ambient glow of `0 0 12px rgba(0, 242, 254, 0.20)`. Text is pure white with tabular numerical alignment when parsing money or coordinate variables.

### 6. Lists & Incident Feeds
- Zebra striping is strictly forbidden. Rows use glass cards separated by `space-xs` (4px) or `space-sm` (8px).
- Row hover: Subtle translation `translateX(3px)` coupled with background brightness increase to `rgba(255, 255, 255, 0.06)` and left edge marker lighting up in `#00F2FE`.

### 7. Checkboxes & Switches
- Checkboxes: 16x16px, `rounded` (4px), dark substrate with 1px border. Checked state uses solid `#00F2FE` fill with `#070B14` bold checkmark glyph.
- Spatial Toggle Switch: Track `rgba(255, 255, 255, 0.10)`, thumb `#FFFFFF` with drop shadow. Active track glows `#00F2FE` with 30% alpha fill.