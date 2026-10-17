# Ola Support Intelligence — UI Design Specification: "The Dispatch Desk"

**Product**: Ola Support Intelligence  
**Role**: Customer Operations, Rider/Driver Policy Assistance & Ticket Tracking  
**Audience**: Stressed riders, drivers on mobile phones, dispatch operations staff  
**Tone**: Calm, plain, precise. Zero decorative filler. Zero emoji.

---

## 1. Design Philosophy: "The Dispatch Desk"

The interface is modeled on a physical ride-hailing support desk: road markings, taxi meters, printed dispatch slips, and physical ticket receipts. Every visual and interactive choice reinforces clarity, authority, and rapid resolution in a single exchange.

### Foundational Principles
1. **Boldness Spent in One Place**: The **Ticket Stub**. Everything else (top bar, composer, conversation history) is disciplined, quiet, and utilitarian.
2. **Structure is Information**: Dividers, borders, and perforations exist solely to demarcate discrete semantic units, never as decorative flourishes.
3. **No Fluff / No Emoji**: Professional operational interface. Statuses are indicated with precise typography, geometric markers, and tabular data.
4. **Self-Contained & Completely Offline**: Zero external network dependencies, CDNs, analytics, or remote assets. Fully operable in an isolated environment.

---

## 2. Color System & Token Architecture

The palette uses exactly six physical tokens derived from road and vehicle mechanics. Tints are generated programmatically only for low-opacity background fills.

### Color Tokens

| Token Name | Hex Code | Semantic Role | Contrast vs. Chalk / Asphalt |
|---|---|---|---|
| **Kerb chalk** | `#ECEEE8` | Page background (light), primary ink (dark) | 12.8:1 against Asphalt |
| **Asphalt** | `#1B2230` | Primary ink (light), page background (dark), dark surfaces | 12.8:1 against Chalk |
| **Lane yellow** | `#F4C20D` | Highlighter accent: focus rings, active ticket stage, attention | 3.5:1 against Asphalt (non-text UI / 7.2:1 against dark ink) |
| **Signal teal** | `#0E7C7B` | Verified policy adherence, grounded citations, success states | 4.8:1 on Chalk, 5.1:1 on dark slip |
| **Brake red** | `#C5412B` | Intercepted prompt injections, budget exhaustion, error alerts | 5.2:1 on Chalk, 4.9:1 on dark slip |
| **Verge grey** | `#8A9199` | Secondary metadata, captions, inactive ticket tracks | 4.6:1 on Asphalt, 4.5:1 on Chalk |

### Theme Remapping Matrix

Theme switching re-maps identical tokens rather than inventing separate color systems:

```css
:root, [data-theme="light"] {
  --color-page: #ECEEE8;              /* Kerb chalk */
  --color-surface: #FFFFFF;           /* Paper white for policy slip */
  --color-surface-sunken: #E2E5DC;    /* Recessed chalk */
  --color-ink: #1B2230;               /* Asphalt */
  --color-ink-secondary: #586069;     /* Deep verge */
  --color-ink-muted: #8A9199;         /* Verge grey */
  --color-border: #D1D6CC;            /* Solid road boundary */
  --color-accent: #F4C20D;            /* Lane yellow */
  --color-verified: #0E7C7B;          /* Signal teal */
  --color-blocked: #C5412B;           /* Brake red */
  --color-chip-user: #1B2230;         /* Asphalt */
  --color-chip-user-ink: #ECEEE8;     /* Kerb chalk */
  --glass-bg: rgba(236, 238, 232, 0.88);
  --glass-border: rgba(27, 34, 48, 0.12);
}

[data-theme="dark"] {
  --color-page: #121722;              /* Deep asphalt */
  --color-surface: #1B2230;           /* Asphalt surface */
  --color-surface-sunken: #151A24;    /* Pit dark */
  --color-ink: #ECEEE8;               /* Kerb chalk */
  --color-ink-secondary: #B0B7BF;     /* Light verge */
  --color-ink-muted: #8A9199;         /* Verge grey */
  --color-border: #2B3444;            /* Dark divider */
  --color-accent: #F4C20D;            /* Lane yellow */
  --color-verified: #18A9A8;          /* Lightened signal teal */
  --color-blocked: #E0533C;           /* Lightened brake red */
  --color-chip-user: #242D3D;         /* Elevated asphalt */
  --color-chip-user-ink: #ECEEE8;     /* Kerb chalk */
  --glass-bg: rgba(27, 34, 48, 0.88);
  --glass-border: rgba(236, 238, 232, 0.12);
}
```

### Prohibited Styles
- NO cream background with terracotta accent
- NO near-black with acid neon green
- NO purple/blue gradient washes
- NO identical rounded cards with soft floating grey box-shadows
- NO all-caps eyebrow labels over every heading
- NO spaced em dashes in labels

---

## 3. Typography & Typesetting System

Typography relies on two complementary typefaces: **Archivo** (expanded for wordmarks and headings, normal for UI controls) and **Source Serif 4** (for verified policy prose).

### Type Families
1. **Sans / Display**: `Archivo`, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif.
   - Variable width axis: `font-stretch: 125%` (expanded) for wordmarks and section titles.
   - Standard width: `font-stretch: 100%` for buttons, chips, form labels, and operational indicators.
2. **Serif / Content**: `Source Serif 4`, "Georgia", "Iowan Old Style", "Times New Roman", serif.
   - Used exclusively for policy answers, customer guidelines, and resolution text.
3. **Numbers & Timers**: All numerical readouts (tokens, SLA hours, days, percentages, ticket IDs) use `font-variant-numeric: tabular-nums` to prevent layout jitter.

### Modular Scale (Ratio: ~1.25, Base: 18px Desktop / 17px Mobile)

| Level | Size (rem / px) | Line Height | Family | Tracking | Purpose |
|---|---|---|---|---|---|
| **Display** | 1.50rem (27px) | 1.25 | Archivo Expanded (700) | -0.02em | Main Wordmark |
| **Heading** | 1.25rem (22.5px) | 1.30 | Archivo Expanded (600) | -0.01em | Drawer Titles, Ticket ID |
| **Body (Prose)** | 1.00rem (18px) | 1.60 | Source Serif 4 (400) | 0.00em | Policy slips, answer text |
| **Body (UI)** | 0.94rem (17px) | 1.45 | Archivo Normal (400) | 0.00em | Composer, options, alerts |
| **Control** | 0.88rem (15.8px) | 1.35 | Archivo Normal (500) | +0.01em | Buttons, chips, table headers |
| **Meta** | 0.75rem (13.5px) | 1.30 | Archivo Normal (500) | +0.02em | Token gauge, timestamps, SLA tags |

### Measure & Readability Rules
- Max measure for policy answers: **68 characters**.
- Max measure for conversational chips: **56 characters**.
- Tabular lining figures applied globally to meter readouts.

---

## 4. Spacing, Elevation & Shape Encoding

Shape radius communicates structural permanence and physical behavior:

### Radius Scale (Hierarchy Encoding)
- `4px` (`--radius-slip`): **Policy Slip & Ticket Stub** — crisp, mechanical receipt corners.
- `10px` (`--radius-control`): **Buttons, Inputs, Chips** — tactile, finger-friendly interactive controls.
- `20px` (`--radius-sheet`): **Settings Sheet / Drawers** — elevated overlay container.
- `100px` (`--radius-pill`): **Status Indicator & Badges** — operational state pills.

### Perforated Slip Styling
The policy slip and ticket stub feature a bottom perforated cut using CSS gradients:
```css
.perforated-edge {
  background: radial-gradient(circle at 10px -5px, transparent 6px, var(--color-surface) 7px) repeat-x;
  background-size: 16px 12px;
  height: 12px;
  width: 100%;
}
```

### Elevation & Glass Policy
- **The page itself is flat**: No drop shadows on stationary content cards.
- **Glass Blur**: Applied **only** to floating overlays (`.settings-sheet`, `.composer-dock`, `.toast-message`) using `backdrop-filter: blur(12px)`.
- **Solid Fallback**: `@supports not (backdrop-filter: blur(12px))` automatically reverts to solid background `--color-page` with strict 4.5:1 text contrast.

---

## 5. ASCII Wireframes

### Wireframe A: Mobile Viewport (360px × 640px)

```text
+------------------------------------------+
| [O] Ola Support Intelligence   * Online  [#] |
+------------------------------------------+
|                                          |
|  What do you need to know?               |
|  Ask about a policy, or give a ticket.   |
|                                          |
|  [ Sev-1 response times ]                |
|  [ Status of TKT-0007   ]                |
|  [ Refund rules         ]                |
|                                          |
|------------------------------------------|
|                                    (You) |
|                     [What is the Sev-1?] |
|                                          |
|  +------------------------------------+  |
|  | POLICY SLIP #18                    |  |
|  | - - - - - - - - - - - - - - - - - -|  |
|  | Sev-1 safety incidents require a   |  |
|  | mandatory first response within 15 |  |
|  | minutes and complete resolution    |  |
|  | within 4 hours.                    |  |
|  |                                    |  |
|  | From: SLA by Severity              |  |
|  | [teal check] Verified policy       |  |
|  | [grey check] Checked by reviewer   |  |
|  o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o  |
|                                          |
+------------------------------------------+
| [ Ask policy or ticket...        ] [Send]|
| [=====-------------------] 212 of 2,000  |
+------------------------------------------+
```

### Wireframe B: Desktop Viewport (1280px × 800px)

```text
+---------------------------------------------------------------------------------------------------+
|  [O] Ola Support Intelligence                              * Desk Online               [Settings] |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|                                   < max-width: 44rem (Centered) >                                 |
|                                                                                                   |
|                            What do you need to know?                                              |
|                            Ask about a policy, or give a ticket number.                           |
|                                                                                                   |
|             [ Sev-1 response times ]   [ Status of TKT-0007 ]   [ Cancellation refunds ]          |
|                                                                                                   |
|                                                                                                   |
|                                                                   +-----------------------------+ |
|                                                                   | Customer phone +91 98...    | |
|                                                                   +-----------------------------+ |
|                                                                                                   |
|       +-----------------------------------------------------------------------------------+       |
|       | POLICY SLIP #04                                                       OFFICIAL    |       |
|       | - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - |       |
|       | For customer contact privacy, all inquiries with phone numbers are masked upon    |       |
|       | receipt. The resolution SLA for standard ride queries is 24 hours.                |       |
|       |                                                                                   |       |
|       | From: Data Retention & Privacy Policy, SLA by Severity                            |       |
|       | [Teal Mark] Verified against official policy   •   Checked by secondary reviewer  |       |
|       o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o-o |       |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
|       | Ask about a policy or enter a ticket number...                           | [ Send ]       |
|       | [======------------------------------------------------] 384 of 2,000 tokens             |
+---------------------------------------------------------------------------------------------------+
```

### Wireframe C: The Ticket Stub (The Central Memorable Moment)

```text
+---------------------------------------------------------------+
| DISPATCH TICKET STUB                                          |
|                                                               |
| TKT-0007                                              Billing |
| = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = |
|                                                               |
| [o] Open ---- [o] In progress ---- [*] ESCALATED ---- [ ] Resolved ---- [ ] Closed
|                                     (Lane Yellow Lit)         |
|                                                               |
| Resolution SLA Target       18 hours                          |
| Ticket Elapsed Age          12 days                           |
| Priority Risk Rating        High                              |
|                                                               |
| ESCALATION RISK GAUGE                                         |
| 0.0          0.44 (Threshold)                       1.0       |
| [ ||||||||||||||||||||| | | | | | | ]   0.720                 |
|                        ^-- Breached threshold                 |
|                                                               |
| Recommendation: Escalate to a senior supervisor immediately   |
| - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - |
| Grounded reference: SLA Escalation Matrix                     |
+---------------------------------------------------------------+
\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\
                     (Perforated Tear Line)
```

### Wireframe D: The Settings Sheet (Drawer / Modal)

```text
+---------------------------------------------------------+
| SETTINGS & OPERATIONS                               [X] |
+---------------------------------------------------------+
| [Quick Actions] [Chat] [Appearance] [Connection] [Tickets] [Privacy] [Admin]
|---------------------------------------------------------|
| QUICK ACTIONS                                           |
| Tap any action to dispatch immediately:                 |
|                                                         |
| [ ⚡ Sev-1 SLA Rules                                  ] |
| [ 🎫 Check ticket TKT-0007                            ] |
| [ 💰 Cancellation refunds                             ] |
| [ ⭐ VIP Ola Select SLA                               ] |
| [ 🔒 Test privacy protection                          ] |
| [ 🛡️ Test security guardrail                          ] |
| [ ⚠️ Test payload budget                              ] |
|                                                         |
|---------------------------------------------------------|
| CONNECTION STATUS                                       |
| Desk Status:  🟢 Online                                 |
| Latency:      12 ms                                     |
| [ Check Connection ]                                    |
|                                                         |
| (No URLs, ports, or env variables displayed)            |
+---------------------------------------------------------+
```

---

## 6. Motion Specification & Choreography

Motion is disciplined and purposeful. No endless bouncing cards or gratuitous parallax.

### 1. The Ticket Print Sequence (The Single Orchestrated Moment)
- **Trigger**: When `/ask` returns a response containing ticket metadata (`ticket_id`).
- **Phase 1: Ejection** (`0ms - 450ms`):
  The ticket stub translates downward from a 1px slot divider (`transform: translateY(-24px)` to `translateY(0)`), with `clip-path` unmasking the paper. Cubic bezier curve: `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Phase 2: Status Track Ignition** (`450ms - 650ms`):
  The progress nodes light up sequentially up to the active status (`Open` -> `In Progress` -> `Escalated`). The active stage pulses once in **Lane Yellow** (`#F4C20D`).
- **Phase 3: Meter Segment Fill** (`650ms - 900ms`):
  The segmented taxi gauge blocks illuminate left-to-right until reaching the numeric score.

### 2. Micro-Interactions (< 200ms)
- **Settings Sheet Opening**: `transform: translateX(100%) -> translateX(0)` (200ms `ease-out`).
- **Composer Focus**: Subtle outline illumination in Lane Yellow (`150ms`).
- **Button Press**: Scale down `0.98` (`80ms`).

### 3. Accessibility & Reduced Motion
- `@media (prefers-reduced-motion: reduce)`:
  - All transitions and translations are disabled (`animation: none !important; transition: none !important;`).
  - The ticket stub appears instantly in its final printed state with the active stage highlighted.

---

## 7. Privacy, Masking & Zero-Leak Architecture

The frontend communicates with the backend exclusively via **same-origin relative endpoints**:
- `POST /ask`
- `GET /health`
- `WS /ws/chat`

### Information Isolation Rules
1. **Zero Host/Port/URL Leaks**: The strings `127.0.0.1`, `localhost`, `onrender.com`, `8000`, `8501`, and `https://` never appear anywhere in the rendered HTML, CSS, JavaScript, console messages, tooltips, or exports.
2. **Client-Side Pure Masking Module (`mask.js`)**:
   - `maskPhoneNumbers(text)`: Replaces Indian 10-digit / +91 phone numbers with `[PHONE_MASKED]`.
   - `maskEmails(text)`: Replaces emails with `[EMAIL_MASKED]`.
   - `maskCardNumbers(text)`: Replaces 12-19 digit card patterns with `[CARD_MASKED]`.
   - `formatCustomerInitials(name)`: Converts `"Mahesh Babu"` into `"M. B."`.
3. **Clean Error Directives**:
   - `400`: *"This request was blocked by the safety policy. Rephrase your question."*
   - `413`: *"Your question is too long. Keep it under 2,000 tokens."*
   - `503`: *"The desk is warming up. Trying again."*
   - `500` / Connection: *"Something went wrong on our side. Try again in a moment."*
4. **Context Hygiene**:
   - Messages resulting in 400, 413, 500, or 503 are marked `rejected: true` and are **never** included in the conversational memory context sent to subsequent queries.

---

## 8. Self-Critique: Generic Template Antidotes

### Identified Generic Template Traps & How They Were Eliminated

| Common Generic Pattern | Why It Was Rejected | Our Deliberate Solution |
|---|---|---|
| **Purple/Cyan "AI" Gradient Glows** | Screams generic AI template; distracting and high cognitive load for stressed users. | Stripped completely. The page is flat Kerb chalk and Asphalt. The sole vibrant color is **Lane yellow**, reserved for focus and active ticket tracking. |
| **All-Caps Eyebrow Tags over Headings** | Useless visual clutter seen in every SaaS template (`// ENTERPRISE AI ASSISTANT`). | Removed. Headings state their content plainly in sentence case using expanded Archivo. |
| **Identical Rounded Cards with Fuzzy Shadows** | Makes ticket data look like a marketing blog post instead of official legal policy. | Replaced with the **Perforated Policy Slip** (paper-white, perforated edge, Source Serif 4 typography) and the **Printed Ticket Stub**. |
| **Emoji Everywhere (⚡ 🎫 💰 ⭐ 🛡️)** | Trivializes serious customer complaints (e.g. accidents, refund disputes). | Removed from chat and answers. Replaced with sharp, hand-crafted inline SVG icons where functional clarity is required. |
| **Streaming Text Hallucination / Fake Typing** | Adds latency and jitter; riders want their answer immediately without waiting for a cursor animation. | No fake typewriter delay. When `/ask` returns, the full verified policy slip renders immediately. |
| **Spaced Em Dashes & Arrows on Buttons (`Submit ->`)** | Superficial decoration that degrades button readability. | Clean, confident verbs: **Send**, **Check**, **Reset**. |

---

## 9. Next Steps (Pass 2 Build Roadmap)

Upon user approval of this design specification:
1. Create `static/css/tokens.css`, `static/css/base.css`, and `static/css/components.css`.
2. Implement vanilla JavaScript modules in `static/js/`:
   - `mask.js`: Pure regex masking functions for PII.
   - `api.js`: Fetch wrapper targeting relative endpoints with timeouts and status-specific handlers.
   - `state.js`: Local session state, preferences, and context hygiene.
   - `render.js`: Policy slip, ticket stub, status gauge, and message rendering.
   - `settings.js`: Drawer management, focus trapping, tab navigation, and admin controls.
   - `tickets.js`: Directory filtering and quick dispatch.
   - `main.js`: App initialization, token gauge, keyboard shortcuts, and auto-scroll.
3. Build `static/index.html` with inline SVGs, semantic landmarks, and strict CSP meta tags.
4. Mount `StaticFiles` in `api/main.py` ensuring API endpoints take precedence.
5. Execute end-to-end unit tests, AppTest/Playwright browser checks, and record output to `transcripts/27_web_ui.txt`.
