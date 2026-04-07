# Frontend UI Prompt For Pencil.dev

Create a premium redesign of the current Amazon Review Intelligence frontend.

Critical instruction: **keep all current screens, states, components, and information architecture exactly the same**. This is a **visual upgrade only**, not a feature or flow rewrite.

## Product Positioning
Design this as an **Executive Intelligence Console**:
- trustworthy
- data-first
- calm but authoritative
- enterprise-grade polish

Tone should feel like a product used by category managers, growth leads, and CX decision-makers.

## Non-Negotiable Scope Rules
- Do not remove any existing screen/state/component.
- Do not change navigation logic.
- Do not introduce new product features.
- Do not merge screens that are currently separate.
- Preserve desktop + mobile responsiveness behavior already implemented.

---

## Theme Direction: Executive Indigo

### Design Principles
1. Clarity over decoration
2. Strong hierarchy for fast scanning
3. High trust visual language (clean, restrained, precise)
4. Consistent semantics (especially sentiment colors)
5. Accessible contrast and touch targets

### Typography
- Font family: `Inter`
- Weights used: 400, 500, 600, 700
- Type scale:
  - Display: 32/40, 700
  - H1: 28/36, 700
  - H2: 24/32, 700
  - H3: 20/28, 600
  - Body: 14/22, 400
  - Small/meta: 12/18, 500
  - Micro labels: 10/14, 500

### Spacing + Radius
- Base spacing scale: 4, 8, 12, 16, 24, 32, 40
- Card padding defaults:
  - desktop: 24
  - tablet: 16
  - mobile: 12
- Border radius:
  - input/button small: 8
  - cards/panels: 12
  - pills/badges: 9999

### Elevation
- Shadow / depth:
  - level 1 (default cards): subtle shadow
  - level 2 (hovered card): medium soft shadow
  - level 3 (sticky header / popover): stronger soft shadow + blur

---

## Color Tokens (Light + Dark)

### Light Theme Tokens
- `bg.canvas`: `#F8FAFC`
- `bg.surface`: `#FFFFFF`
- `bg.surfaceMuted`: `#F1F5F9`
- `bg.overlay`: `rgba(2, 6, 23, 0.55)`
- `text.primary`: `#0F172A`
- `text.secondary`: `#334155`
- `text.muted`: `#64748B`
- `border.default`: `#E2E8F0`
- `border.strong`: `#CBD5E1`
- `brand.primary`: `#1E3A8A`
- `brand.accent`: `#4F46E5`
- `brand.secondary`: `#0F766E`
- `focus.ring`: `#2563EB`

### Dark Theme Tokens
- `bg.canvas`: `#020617`
- `bg.surface`: `#0F172A`
- `bg.surfaceMuted`: `#1E293B`
- `bg.overlay`: `rgba(2, 6, 23, 0.7)`
- `text.primary`: `#E2E8F0`
- `text.secondary`: `#CBD5E1`
- `text.muted`: `#94A3B8`
- `border.default`: `#334155`
- `border.strong`: `#475569`
- `brand.primary`: `#60A5FA`
- `brand.accent`: `#818CF8`
- `brand.secondary`: `#2DD4BF`
- `focus.ring`: `#93C5FD`

### Semantic Status Colors
- `success`: `#16A34A`
- `warning`: `#CA8A04`
- `error`: `#DC2626`
- `info`: `#2563EB`

### Sentiment Colors (must stay consistent everywhere)
- `sentiment.positive`: `#16A34A`
- `sentiment.neutral`: `#CA8A04`
- `sentiment.negative`: `#DC2626`

### Chart Palette
Use this ordered palette for non-semantic comparison bars/lines:
1. `#1E3A8A`
2. `#4F46E5`
3. `#0F766E`
4. `#2563EB`
5. `#14B8A6`
6. `#9333EA`

Grid lines: low contrast (`12-18%` opacity).  
Axis labels: muted text color.  
Tooltip surface: elevated card with border + shadow.

---

## Existing Screen Inventory (must be recreated)

## Core App States
1. Auth bootstrap loading: full-screen “Checking session...”
2. Logged-out auth screen (Login / Signup / Forgot)
3. Password reset completion screen (token flow)
4. Logged-in dashboard before analysis
5. Dashboard while analysis is running
6. Dashboard with analysis results
7. Dashboard with cache panel open
8. Detailed Insights screen (separate deep-dive layout)

## Reusable Components
- Top Navbar
- Sidebar Filters panel
- Graph/Charts area with tabs
- Insights side panel
- Cached results card grid
- User status/action strip
- Email verification warning banner
- Auth form card
- Password reset form card
- Detailed analysis cards
- Review sample cards
- Dropdowns (export/share)
- Tabs, badges, progress bars, slider, switch, select, toasts

---

## Desktop Screens (Here are the desktop screens)

### 1) Auth Screen (Desktop)
- Navbar at top with brand.
- Centered auth card (`max-width ~400px`).
- Modes: login / signup / forgot in same component.
- Fields:
  - Email
  - Password (except forgot mode)
  - Confirm Password (signup only)
- Actions:
  - Primary submit
  - Mode toggle (login <-> signup)
  - Forgot toggle

### 2) Password Reset Screen (Desktop)
- Centered “Set New Password” card.
- New password + confirm password.
- Primary reset button.

### 3) Main Dashboard Layout (Desktop, >=1024)
- Sticky navbar.
- Top user strip below navbar:
  - Logged-in identity text
  - Buttons: Cached Results, Verify Email (conditional), Logout All, Logout
- Optional amber verification-required banner.
- 3-column body:
  - Left sidebar filters (~320px; collapses to ~64px icon rail)
  - Center analysis canvas
  - Right insights panel (~320-384px)

### 4) Sidebar Filters (Desktop)
Sections separated by dividers:
1. Product Search
   - Input: “Enter ASIN or Amazon URL”
   - Helper text
   - AI analysis switch
   - Analyze button
2. Quick Examples (3 ASIN cards)
3. Max Reviews slider (10 to 100, step 10) + value badge
4. Region select (US, UK, DE, FR, JP, CA, IN)
5. Reset All button

Collapsed mode must show icon-only vertical rail with expand CTA.

### 5) Main Center Content (Desktop)
- Empty state: centered start-analysis form.
- Loading state: spinner + “Analyzing Reviews...”
- Result state:
  - Product header (title + ASIN)
  - 4 stat cards: total reviews, avg rating, positive %, key themes count
  - Tabs:
    - Overview: rating distribution, sentiment pie, top keywords, key themes
    - Sentiment: trend line chart
    - Emotions: radar chart
  - CTA button: “View Detailed Insights”

### 6) Insights Panel (Desktop Right)
States:
- loading skeleton
- empty helper
- filled content cards:
  - summary
  - sentiment breakdown progress bars
  - key themes badges
  - top keywords badges
  - AI insights list (when available)
  - data source/provider meta card

### 7) Cached Results Panel (Desktop)
- Expandable panel below top user strip.
- Header + Hide action.
- Card grid (up to 3 columns):
  - product title
  - ASIN + country
  - review count + avg rating
  - timestamp
  - CTA (Open Cached Analysis / No Payload)

### 8) Detailed Insights Screen (Desktop)
Header row:
- back button + page title + asin/review count
- share dropdown (link, twitter, linkedin, facebook, email)
- export dropdown (PDF, CSV, Excel)

Sections in order:
1. Product Info card (image optional, title, asin, avg rating)
2. Executive Summary card
3. Sentiment Breakdown (3 cards: positive/neutral/negative)
4. Key Insights grid
5. Top Keywords cluster
6. Review sample card pattern (positive/neutral/negative groups)

---

## Mobile Screens (Here are the mobile screens)

### Responsive Rules
- Main mobile threshold: `<768px`
- Chart density tiers:
  - mobile `<640px`
  - tablet `640-1023px`
- Navbar height: ~56px

### 1) Auth + Reset (Mobile)
- Same flows as desktop, single-column full-width padded cards.

### 2) Mobile Dashboard Layout
Navbar includes:
- hamburger (opens sidebar drawer)
- brand
- theme toggle
- export icon dropdown

Below navbar:
- compact user strip
- optional verify-email banner

Sidebar behavior:
- slide-in drawer from left
- width ~85vw, max 320px
- dark overlay backdrop
- close control in sidebar header

### 3) Mobile Main Content
- Empty: centered quick-start form.
- Loading: centered spinner message.
- Results:
  - product header at top
  - charts/tabs stacked
  - “View Detailed Insights” visible below charts

Insights behavior on mobile/tablet:
- not fixed right column
- full-width panel below graph area
- max-height ~50vh with internal scroll

### 4) Mobile Cached Results
- Same cached panel behavior.
- 1-column cards on small widths, 2-column on larger mobile/tablet widths.
- Touch-friendly spacing and controls.

### 5) Mobile Detailed Insights
- Same content as desktop in single-column flow.
- Compact share/export actions remain available.

---

## Component Visual Specs

### Navbar
- Sticky, blurred, lightly translucent surface.
- Brand uses indigo accent with subtle active indicator pulse.
- Icon buttons are ghost style with strong hover/focus states.

### Cards
- Border-first design with restrained shadow.
- Increase shadow only on hover for interactive cards.
- Keep content paddings compact but breathable.

### Buttons
- Primary: indigo fill with high-contrast text.
- Secondary/outline: neutral border, tinted hover.
- Disabled: lowered opacity + no hover elevation.

### Forms (Input/Select/Slider/Switch)
- Inputs: quiet default borders, strong focus ring.
- Select dropdowns: same elevation language as cards.
- Slider and switch should use brand accent when active.

### Badges + Meta Chips
- Sentiment badges must use semantic colors.
- Neutral metadata badges should be low-saturation surfaces.

### Toasts
- Mobile top stack; desktop bottom-right stack.
- Destructive variant must use red semantic style.

---

## Motion & Interaction
- Keep animations purposeful and subtle:
  - card hover lift: very small translateY
  - button press: minor scale down
  - chart hover: highlight only, no noisy motion
- Avoid flashy transitions.
- Maintain fast perceived performance.

---

## Accessibility Requirements
- Maintain readable contrast in both themes (target WCAG AA).
- Never use color as the only status signal.
- Focus states must be clearly visible for keyboard use.
- Minimum mobile tap target size: 44x44 px.
- Preserve text readability at small dashboard sizes.

---

## Interaction & Behavior Notes (must match current app)
- Sidebar can collapse on desktop; tablet defaults to collapsed sidebar.
- Analyze button disabled for invalid/short input.
- Input accepts raw ASIN and full Amazon product URL.
- Default region is India (`IN`).
- Verify-email gating remains visible and enforced in UI states.
- Cached results support loading and empty states.
- Export actions available in navbar and detailed view.
- Detailed view entry: “View Detailed Insights”; exit with back arrow.

---

## Deliverables In Pencil
Create these frames/artboards:
1. Desktop – Auth (Login mode)
2. Desktop – Auth (Signup mode)
3. Desktop – Auth (Forgot mode)
4. Desktop – Reset Password
5. Desktop – Dashboard Empty
6. Desktop – Dashboard Loading
7. Desktop – Dashboard With Analysis
8. Desktop – Dashboard With Cache Open
9. Desktop – Detailed Insights
10. Mobile – Auth
11. Mobile – Reset Password
12. Mobile – Dashboard Empty
13. Mobile – Dashboard With Sidebar Open
14. Mobile – Dashboard With Analysis
15. Mobile – Detailed Insights

---

## Design QA Checklist (Pencil output must pass)
- All 15 frames exist and are named exactly.
- All required states are represented (loading/empty/filled/conditional).
- Sidebar drawer and desktop collapse variants are both shown.
- Light and dark variants are demonstrated for key dashboard frames.
- Sentiment colors are consistent across charts, badges, and progress bars.
- Desktop and mobile hierarchy remain equivalent to current product behavior.
