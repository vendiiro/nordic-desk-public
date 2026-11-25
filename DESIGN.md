---
name: Nordic Desk
description: A personal long-term stock research desk in euros; Huurre for desktop research, Aamu for the phone glance.
colors:
  paper: "oklch(98.5% 0.004 240)"
  paper-2: "oklch(96.5% 0.006 240)"
  paper-3: "oklch(92.5% 0.009 240)"
  ink: "oklch(21% 0.012 250)"
  ink-2: "oklch(36% 0.012 250)"
  muted: "oklch(50% 0.014 250)"
  rule: "oklch(90% 0.008 240)"
  rule-2: "oklch(80% 0.01 240)"
  accent: "oklch(46% 0.13 250)"
  accent-deep: "oklch(38% 0.12 250)"
  accent-ink: "oklch(98.5% 0.004 240)"
  focus: "oklch(55% 0.16 250)"
  sel: "oklch(94.5% 0.025 250)"
  own: "oklch(52% 0.13 70)"
  up: "oklch(50% 0.12 165)"
  down: "oklch(52% 0.17 25)"
  line: "oklch(30% 0.03 250)"
  s1: "oklch(42% 0.14 250)"
  s2: "oklch(56% 0.13 70)"
  s3: "oklch(55% 0.11 165)"
  s4: "oklch(62% 0.13 320)"
  s5: "oklch(70% 0.06 250)"
  s6: "oklch(82% 0.04 250)"
  aamu-paper: "oklch(98.5% 0.005 260)"
  aamu-ink: "oklch(16% 0.012 260)"
  aamu-ink-2: "oklch(30% 0.014 260)"
  aamu-muted: "oklch(46% 0.016 260)"
  aamu-accent: "oklch(42% 0.19 262)"
  aamu-focus: "oklch(58% 0.22 28)"
  aamu-up: "oklch(47% 0.12 160)"
  aamu-down: "oklch(52% 0.19 27)"
typography:
  display:
    fontFamily: "Host Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "2.488rem"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Host Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.728rem"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Host Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.2rem"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Host Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Host Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.5
  number:
    fontFamily: "Atkinson Hyperlegible Mono, ui-monospace, monospace"
    fontSize: "1rem"
    fontWeight: 400
    fontFeature: "tnum"
  aamu-display:
    fontFamily: "Barlow Condensed, ui-sans-serif, sans-serif"
    fontSize: "2.488rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.005em"
  aamu-body:
    fontFamily: "Barlow, ui-sans-serif, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  card: "8px"
  pill: "6px"
  aamu: "0px"
spacing:
  2xs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  2xl: "64px"
components:
  nav-link:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "4px 12px"
    height: "36px"
  nav-link-current:
    backgroundColor: "{colors.paper-3}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 12px"
    height: "36px"
  chip-selected:
    backgroundColor: "{colors.paper-3}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
  segment:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 12px"
    height: "36px"
  segment-pressed:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
  card:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.card}"
    padding: "16px"
  verdict:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.card}"
    padding: "12px 16px"
  search-input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 12px"
    height: "40px"
  badge-own:
    textColor: "{colors.own}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
---

# Design System: Nordic Desk

## Overview

**Creative North Star: "The Hoarfrost Ledger"**

Nordic Desk reads like a clean ledger on a frosty morning: cool, nearly white paper, hairline rules, and columns of tabular numbers that line up to the digit. The system is quiet on purpose. The owner comes here to make a calm long-term call, and the pages should feel like a research desk that has already done the arithmetic, not a trading screen asking for action.

Density is high but never cramped. Tables, small multiples and sparklines carry most of the information; prose is short and sits beside the number it explains. Colour is almost absent at rest. It appears only to carry meaning: up, down, the owner's own position, the selected series, and focus. Depth comes from paper tints and hairlines, never from resting shadows.

There are two looks over one engine. **Huurre** (hoarfrost) is the main system for desktop research: Host Grotesk with a mono for numbers, an 8 px card radius, a muted steel-blue accent. **Aamu** (morning) is a sibling colourway for the phone glance after the US close: Barlow Condensed headlines, square corners, a saturated Finnish blue. Both share the spacing, type scale and number formats.

**Key Characteristics:**
- Cool paper in three tints, ink in three weights, two hairline greys.
- Every figure in a tabular mono; proper minus sign; euros with thin-space thousands.
- Colour means something or it is not there.
- Flat at rest; a soft shadow only on layers that float above the page.
- Sentence-case labels, no tracked capitals.

## Colors

A near-monochrome cool palette (hue 240–250) with one restrained steel-blue accent and three semantic hues.

### Primary
- **Steel Hoarfrost Blue** (`accent`): the mark, the pressed segment, links that need weight, and hover borders on explainable boxes. Used sparingly; it marks the active choice, not decoration.
- **Deep Steel** (`accent-deep`): the pressed or hover state of accent elements.
- **Focus Blue** (`focus`): the 2 px focus ring on every interactive element.
- **Selection Frost** (`sel`): the background of a selected table row or item.

### Secondary
- **Amber Holding** (`own`): marks what the owner already holds (badges, the "own" line in charts). It is the one warm hue in Huurre and means "this is yours".

### Tertiary
- **Pine Up** (`up`) and **Brick Down** (`down`): gains and losses in text, sparklines and signal cells. Always paired with a sign or a word, never colour alone.
- **Series ramp** (`s1`–`s6`): steel blue, amber, pine, orchid, then two pale steels. Used in order for compared stocks and chart series; `s5`/`s6` are for context series.

### Neutral
- **Frost Paper** (`paper`): the page. **Paper 2** (`paper-2`): the top bar and quiet panels. **Paper 3** (`paper-3`): hover, the current nav link, a selected chip.
- **Ink** (`ink`): headings and numbers. **Ink 2** (`ink-2`): body copy in boxes, nav links. **Muted** (`muted`): captions, axis labels, sources, table headers.
- **Rule** (`rule`): table and card hairlines. **Rule 2** (`rule-2`): control borders, the stronger verdict border, chart baselines.
- **Chart Line** (`line`): the main price line, a near-ink steel.

### Aamu colourway
- **Aamu Snow** (`aamu-paper`), **Aamu Ink** (`aamu-ink`, `aamu-ink-2`, `aamu-muted`), **Finnish Blue** (`aamu-accent`, also its line and first series), **Signal Red-Orange** (`aamu-focus`), with its own `aamu-up` and `aamu-down`. Same roles as Huurre; only the values change.

### Named Rules
**The Meaning-Only Rule.** Colour at rest is reserved for up, down, own, series and focus. If a coloured element carries no meaning, it is grey.

**The Never-Alone Rule.** Up and down colours always come with a sign (+, −) or a word. A colour-blind reader loses nothing.

## Typography

**Display Font:** Host Grotesk (with ui-sans-serif, system-ui)
**Body Font:** Host Grotesk
**Number Font:** Atkinson Hyperlegible Mono (with ui-monospace), tabular figures

**Character:** a plain, slightly technical grotesk for words, and a highly legible mono for every number, so columns align and a 6 can never be read as an 8.

### Hierarchy
The scale is a 1.2 ratio from 1 rem: `xs` 0.8125, `sm` 0.875, `md` 1, `lg` 1.2, `xl` 1.44, `2xl` 1.728, `3xl` 2.488 rem.
- **Display** (500, 2.488 rem, 1.1, −0.02 em): the one headline figure or name on a page (a stock's name, the portfolio value).
- **Headline** (500, 1.728 rem, 1.1): a verdict word, a section's lead figure.
- **Title** (500, 1.2 rem, 1.1): section headings (h2).
- **Body** (400, 1 rem, 1.5): explanations; keep to about 70 characters a line.
- **Label** (500, 0.875 rem): table headers, captions, sources, chips; muted.
- **Number** (mono, tabular): every price, return, percentage and amount, at the size of its context. Tickers are mono 600.
- **Chart axis** (mono, 11 px): SVG axis labels only. The one fixed pixel size, because chart text scales with the SVG.

### Named Rules
**The Mono-for-Money Rule.** Any figure a reader might compare goes in the number face with tabular figures. Words never use the mono.

**The Sentence-Case Rule.** Labels and headings are sentence case. No all-caps, no letter-spaced eyebrows.

## Layout

Pages sit in a centred container (max 1440 px) with 40 px gutters, 16 px below 60 rem. Grids use a 24 px gap. Spacing follows a 4/8 rhythm: 4, 8, 12, 16, 24, 40, 64 px.

The top bar (60 px, `paper-2`, hairline below) holds the mark, the page nav and the market clock (US close, New York open in Helsinki time, EUR/USD). The footer always names the sources and says "Not investment advice."

Desktop (about 1280 px) is the research scene: tables at full width, charts with a side column for facts. Phone (390 px) is the glance scene: one column, wide tables scroll inside `.table-wrap`, controls stay at least 36 px tall. Every page must work at both widths.

## Elevation & Depth

Flat by default. Surfaces separate through the three paper tints and 1 px hairlines (`rule`, `rule-2`). Shadows exist only on layers that float above the page.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 6px 24px color-mix(in oklab, var(--color-ink) 14%, transparent)`): hover explanations and popovers on the Analysis page.
- **Float tight** (`box-shadow: 0 8px 24px -8px color-mix(in oklab, var(--color-ink) 25%, transparent)`): small fixed tooltips over tables.
- **Sticky** (`box-shadow: 0 1px 2px color-mix(in oklab, var(--color-ink) 6%, transparent), 0 8px 24px -12px color-mix(in oklab, var(--color-ink) 18%, transparent)`): a bar that sticks while content scrolls under it.

### Named Rules
**The Flat-at-Rest Rule.** Cards, boxes, verdicts and tables never carry a resting shadow. If something needs to stand out, give it a stronger hairline (`rule-2`) or a paper tint.

## Shapes

Gently rounded in Huurre: 8 px on cards, boxes, verdicts and floating layers; 6 px on controls (nav links, chips, segments, inputs, badges). Legend swatches (2 px), loading skeleton bars (3 px) and range marks use 1–3 px. Pills that are fully round (999 px) are rare and only for tiny status dots. Aamu is square: 0 radius everywhere.

Borders are 1 px hairlines. The 52-week range is drawn as a hairline with a 3 px ink tick; sparklines are 1.5 px strokes, chart lines 2 px.

## Components

Refined and restrained: controls look like parts of a well-made instrument, never like marketing buttons.

### Navigation
- **Style:** text links in `ink-2`, 36 px tall, 6 px radius, 4/12 px padding.
- **Hover / current:** `paper-3` background and `ink` text; the current page carries `aria-current="page"`.
- **Phone:** the nav wraps onto a second line; the clock moves under it.

### Chips
- **Style:** `paper` background, 1 px `rule-2` border, 6 px radius, 36 px tall, label size.
- **Hover:** border to `muted`. **Selected:** `paper-3` background, `ink-2` border. **Disabled:** 55% opacity. A hidden radio or checkbox inside carries the state and the focus ring.

### Segmented control
- **Style:** a row of buttons inside one 1 px `rule-2` frame with 6 px corners, hairlines between.
- **Pressed:** `accent` background, `accent-ink` text. Used for the horizon switch, periods and modes.

### Cards / Containers
- **Corner Style:** 8 px. **Background:** `paper`. **Border:** 1 px `rule`. **Internal padding:** 16 px; 12/16 px for verdicts and boxes. No resting shadow.

### Inputs / Fields
- **Style:** search field 40 px tall, `paper` background, 1 px `rule-2` border, 6 px radius, body size.
- **Hover:** border to `muted`. **Focus:** the 2 px `focus` ring, inset by 2 px.

### Verdict box (signature)
A card with the stronger `rule-2` border: a muted label, the verdict word at headline size, then a short list of reasons each led by a 14 px mark and a mono figure, and a fine-print line on sources.

### Explainable box (signature)
A small card with a value in mono at title size and one line of `ink-2` text. It has `cursor: help`; on hover or focus its border and info icon turn `accent` and a floating explanation appears.

### Tables, sparklines and range bars (signature)
Hairline rows, muted 0.875 rem headers, right-aligned mono numbers, nowrap cells. A 96 × 32 sparkline per row in `up`, `down` or `muted`, and an 88 px 52-week range bar.

## Do's and Don'ts

### Do:
- **Do** take every colour, face, radius and space from the tokens in `views/core.py`; no literal values in page CSS.
- **Do** put every number in the mono face with tabular figures, a proper minus sign (−) and thin-space thousands.
- **Do** pair up/down colour with a sign or a word.
- **Do** show where the numbers come from and "Not investment advice." on every page.
- **Do** check every page at 1280 px and 390 px.
- **Do** use `sel` for a selected row and `paper-3` for hover, so selection and hover never look the same.

### Don't:
- **Don't** put a resting shadow on a card, box or table.
- **Don't** use colour for decoration, gradients, or a second accent in Huurre.
- **Don't** use all-caps or letter-spaced labels.
- **Don't** mix the Aamu tokens into Huurre pages, or the reverse.
- **Don't** write promise wording ("will return") or call-to-trade buttons.
