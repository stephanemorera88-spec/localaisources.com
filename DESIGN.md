---
name: Local AI Sources
description: The directory of who the new directories recommend, set as one yellow book with two inks.
colors:
  paper: "#f3cf4a"
  ink: "#141414"
  ink-faded: "#4a3b10"
  red: "#b3121e"
  red-deep: "#8d0d17"
  ground: "#161616"
  white: "#ffffff"
typography:
  display:
    fontFamily: "League Gothic, Bebas Neue, Impact, Arial Narrow, sans-serif"
    fontSize: "2.97em"
    fontWeight: 400
    lineHeight: 0.9
    letterSpacing: "0.01em"
  headline:
    fontFamily: "Bebas Neue, League Gothic, Impact, Arial Narrow, sans-serif"
    fontSize: "1.2em"
    fontWeight: 400
    lineHeight: 1.18
    letterSpacing: "0.02em"
  title:
    fontFamily: "Bebas Neue, League Gothic, Impact, Arial Narrow, sans-serif"
    fontSize: "1.02em"
    fontWeight: 400
    lineHeight: 1.18
    letterSpacing: "0.02em"
  listing:
    fontFamily: "Bebas Neue, League Gothic, Impact, Arial Narrow, sans-serif"
    fontSize: "1em"
    fontWeight: 400
    lineHeight: 1.1
    letterSpacing: "0.012em"
  body:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "max(16px, 0.9em)"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "0em"
  label:
    fontFamily: "Bebas Neue, League Gothic, Impact, Arial Narrow, sans-serif"
    fontSize: "max(12px, 0.78em)"
    fontWeight: 400
    lineHeight: 1.15
    letterSpacing: "0.04em"
rounded:
  none: "0px"
  tab: "0 7px 7px 0"
spacing:
  row: "0.13em"
  listing-row: "0.3em"
  ad-inset: "0.55em 0.75em"
  lead-inset: "1em 0.95em 0.95em"
  ad-gap: "0.8em"
  head-above: "1.1em"
  head-below: "0.3em"
  month-gap: "1.6em"
  colophon-above: "2.2em"
  page-side: "clamp(28px, 7.6vw, 58px)"
  page-side-spread: "4.5%"
  spread-gutter: "9%"
  desk-margin: "60px"
  band-cell: "0.34em 0.5em 0.26em"
components:
  button-primary:
    backgroundColor: "{colors.red}"
    textColor: "{colors.paper}"
    typography: "{typography.listing}"
    rounded: "{rounded.none}"
    padding: "0.18em 0.5em 0.14em"
  button-primary-hover:
    backgroundColor: "{colors.red-deep}"
    textColor: "{colors.paper}"
  button-primary-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  select-finder:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.listing}"
    rounded: "{rounded.none}"
    padding: "0.22em 2.2em 0.2em 0.55em"
  ad-lead:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "{spacing.lead-inset}"
  ad-notice:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "{spacing.ad-inset}"
  tab:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.tab}"
    padding: "0.3em 0"
  tab-current:
    backgroundColor: "{colors.red}"
    textColor: "{colors.white}"
  band-cell:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.listing}"
    rounded: "{rounded.none}"
    padding: "{spacing.band-cell}"
  band-cell-hover:
    backgroundColor: "#000000"
    textColor: "{colors.white}"
  band-cell-current:
    backgroundColor: "{colors.red}"
    textColor: "{colors.white}"
---

# Design System: Local AI Sources

## Overview

**Creative North Star: "The Yellow Pages"**

The site is one book. Every page, from the home to a city-and-trade owner page to an engine or source page, is a spread of the same yellow directory printed in two inks. The identity is readable with all content removed. A yellow pulp ground, a black condensed caps face at directory density, red rules around boxed display ads, dotted leaders carrying the eye from a name to its figure, and black thumb tabs down the right edge, one per trade. On a phone the paper fills the screen. From 800px wide the book becomes an object on a dark desk, with a stack of page edges showing at its sides and foot, and the trade index printed as a black band under the running head. From 1100px it opens flat, two pages with a spine between them, and the content flows from the left page onto the right.

Density is the point. The home page prints 100 city rows in two columns under ten category heads, with no cards, no stat tiles, and no imagery. The owner page lists businesses two lines each, the business in caps and the engines that named it in a smaller caps line beneath, then the sources each engine looked at as a run-in paragraph of domain names. Running prose, the only mixed-case text in the book, is reserved for explanation and the colophon and is set in Barlow Condensed so it reads as a different register, not a different world.

The shipped build settled three points the direction contract left open or stated differently. The owner page sits on the same yellow paper as every other page (the contract's white stock was reversed by the operator on 2026-11-02). Engine identity is carried by the engine's name in plain text, never by a mark, shape or coloured column. The display face is split by measurement, League Gothic for the one title in each lead box and Bebas Neue for every other caps setting.

**Key Characteristics:**
- One paper, two inks, one dark desk. No third hue on the paper, including links and focus.
- One condensed caps family for every size from thumb tab to title; Barlow Condensed only for mixed-case prose.
- Root type scales with the book width, 14.7px at 390 up to 20px from about 530px wide, and every other size is an em of that.
- Two boxed display ads lead every page, then plain ledger lines with dotted leaders.
- Zero radius except the phone thumb tabs. Nothing printed on the paper casts a shadow; the book itself does, from 800px, as an object on the desk.
- One trade index in two printings: fixed black thumb tabs down the right edge on a phone, a black band of trades under the running head from 800px; the current or targeted trade is red in both.
- From 1100px the spread is CSS multi-column, two pages with a drawn spine, no script.

## Colors

A single yellow paper, black and red inks, one faded brown for the smallest notes, and a near-black desk showing outside the book. The page-edge yellows and the desk gradient are not tokens; they exist only inside the book's shadow and the body background and are recorded in the sidecar.

### Primary
- **Red Ink** (`{colors.red}`, #b3121e): the second ink of the book. Draws the 3px rules of every display ad, the lead box's inner double rule, the See who AI names button, the tagline and question line in the lead box, the current section and current month in the running head, the current trade in the index (a thumb tab on a phone, a band cell from 800px), a targeted trade head with its rule and city labels and the matching index cell, the `.own` business-site marker in source paragraphs, hover colour on every link and listing, the focus ring, the text caret and text selection.
- **Red Ink, Deep** (`{colors.red-deep}`, #8d0d17): the primary button on hover and focus only.

### Neutral
- **Yellow Paper** (`{colors.paper}`, #f3cf4a): the ground of the whole book, including the owner page. Also the text colour on black tabs, on the red button, and on the skip link. The flat value sits under two tiled copies of `assets/plates/paper.svg` (a 32x160 crop of the approved comp's margin, drawn at 44x220 and again offset at 71x355) so the pulp grain never shows a lattice. In print the book goes white.
- **Black Ink** (`{colors.ink}`, #141414): the first ink. All listing text, heads, rules under heads, dotted leaders, the finder's select border and arrow, the thumb tabs at rest, the button in its pressed state, and the skip link ground.
- **Faded Ink** (`{colors.ink-faded}`, #4a3b10): mixed-case notes only, the `.prose.note` disclaimer under a page's listings and the `.prose.small` colophon paragraph.
- **Desk** (`{colors.ground}`, #161616): the body background on phones and the base under the desk gradient from 800px, where a fixed radial gradient lights the desk from the top centre (#2b2620 at the centre top, #1b1816 at 55%, #121110 at the edge).
- **White** (`{colors.white}`, #ffffff): text on a red index cell (the current or targeted trade), on a hovered band cell (which goes to pure #000 under it, the one non-token black in the build) and on red text selection. Never a surface.

### Named Rules
**The Two Inks Rule.** Everything on the paper is black or red. There is no engine colour, no link blue, no grey; the only softened value is Faded Ink, and it appears only in mixed-case notes under 16px. The darker yellows of the page stack sit outside the paper's edge and are never used for type or rules.

**The Red Is State Rule.** Red marks the live thing, the box around the ad, the action button, the current tab or month, the hovered line, the business's own site, and the trade a thumb tab or band cell has just opened (the `:target` head, its rule, its city labels and the matching index cell). It never fills an area larger than the button.

## Typography

**Display Font:** League Gothic 400 (with Bebas Neue, Impact, Arial Narrow)
**Caps Font:** Bebas Neue 400 (with League Gothic, Impact, Arial Narrow)
**Body Font:** Barlow Condensed 400 and 600 (with Arial Narrow)
**Code:** ui-monospace stack, 0.88em, inside prose only

All four files are self-hosted woff2 under `assets/fonts`, SIL OFL, `font-display: swap`; Bebas Neue is preloaded on every page because it carries the body.

**Character:** the whole book is condensed caps at one weight, so hierarchy is size and rule, never weight or a second family. The body element itself is uppercase Bebas Neue with tabular numerals, letter-spaced 0.012em, line height 1.18. Barlow Condensed is the exception, used only where a sentence needs to read as a sentence.

### Hierarchy
Sizes are ems of the root, which is `clamp(14.7px, 3.776vw, 20px)`: 14.73px at 390 wide, 20px from roughly 530px up (derived from the formula; the comp's 29px listing line at 768 wide is where the ratio comes from). The root does not grow again when the book opens at 1100px; the spread adds a second page, not larger type.

- **Display** (League Gothic 400, 2.97em, line height 0.9, 0.01em): the one `h1` inside the lead box, balanced wrap. 43.7px at 390, 59.4px on desktop. The owner page's `h1` joins trade and city with a red middle dot.
- **Headline** (Bebas Neue 400, 1.2em, 0.02em, 2px black rule beneath, margin 1.1em above and 0.3em below): the category head over each block of lines, the "Named by 3 of 4 engines" groups, "Where the engines looked". Prose sections use 1.33em with no rule.
- **Title** (Bebas Neue 400, 1.02em, 0.02em, 1px rule beneath): the `h3` sub-head. A red `.kind` tag at 0.7em and 0.05em may sit after a head's text.
- **Listing** (Bebas Neue 400, 1em, line height 1.1): every ledger row, the running head links, the finder labels. The business name on a two-line listing is 1.05em; the notice ad's sentence is 1.14em at line height 1.22; the finder select is 1.14em; the finder button is 1.55em.
- **Body** (Barlow Condensed 400, max(16px, 0.9em), line height 1.4, mixed case, measure 72ch): "About this book", the method page, any paragraph that explains. Strong is 600.
- **Label** (Bebas Neue 400, max(12px, 0.78em), 0.04em): the engine names under a business on a two-line listing; the engine model and date in a source paragraph are `small` at 0.75em; the `.legend` line is max(12px, 0.8em).
- **Note** (Barlow Condensed 400, max(14px, 0.78em) and max(13px, 0.72em), Faded Ink): the extraction disclaimer and the colophon paragraph.

### Named Rules
**The One Weight Rule.** Bebas Neue and League Gothic ship at 400 only and nothing is bolded; `b` inside a source paragraph is explicitly reset to 400. Emphasis is size, red, or an underline.

**The Caps Are Default Rule.** Uppercase is set once on `body`. Mixed case is opt-in through `.prose`, which also drops letter spacing to zero and swaps the family. A new surface that needs sentences wraps them in `.prose`; it does not restyle caps text piecemeal.

**The Pixel Floor Rule.** Any size below 1em is written as `max(Npx, Xem)` so the phone root of 14.7px never pushes small text under its floor (16px for prose, 14px for notes, 13px for the colophon, 12px for labels).

## Layout

The book is one centred column whose width is the custom property `--bookw`. It has three states and two breakpoints, 800px and 1100px; the phone state is the comp and is untouched by the other two.

**Phone, under 800px.** `--bookw` is 768px and the book is `max-width: 768px; min-height: 100vh` with no margin, so the paper fills the screen. Page padding is `0.7em` top, `clamp(28px, 7.6vw, 58px)` right, `1.6em` bottom, `clamp(28px, 7.8vw, 60px)` left; the right padding leaves room for the thumb tabs, which are fixed at `right: max(0px, calc((100% - var(--bookw)) / 2))`, `width: calc(min(100%, 768px) * 0.069)`, from 3.2em below the top of the window to 1.2em above the bottom. The home's city rows run in two CSS columns (`columns: 2; column-gap: 1.4em`) even at 390, which is the directory density the comp set.

**Closed book on the desk, 800px to 1099px.** `--bookw: min(768px, calc(100vw - 120px))`, a 60px desk margin each side, and the book sits `40px auto 56px` with `min-height: 0` and no transform. The body takes the fixed radial desk gradient and the book gains its page-stack edge and soft shadow (Elevation & Depth). The thumb index stops being fixed to the window and is printed on the page as a band: `.book .tabs` goes static and its list becomes a black grid under the running head, `display: grid; grid-template-columns: repeat(5, 1fr) on a single page and repeat(10, 1fr) in the spread, so the band never wraps unevenly; cell text min(.98em, 1.6vw), min(.98em, 1.15vw) in the spread; margin: -.45em 0 .9em; padding: 0 .2em; background: var(--ink)`, so the ten trades fill the width of the page and wrap to a second row when the page is narrow. Nothing sits beside the paper. Two-line listings fold onto one line with a dotted leader between name and engines.

**Open book, from 1100px.** `--bookw: min(1680px, calc(100vw - 120px))` and the padding becomes `0.7em 4.5% 1.6em 4.5%`. The spread is CSS multi-column with no script: `main { columns: 2; column-gap: 9%; column-fill: balance }`, so content flows down the left page and continues on the right. A spine is drawn by `.book::before`, a 120px-wide vertical band centred at 50% with a horizontal gradient from transparent through `rgba(0,0,0,.10)` at 35%, `rgba(60,40,0,.34)` at the centre, back to transparent. The running head spans the left page only (`margin-right: calc(50% + 4.5%)`) and the colophon the right page only (`margin-left: calc(50% + 4.5%)`). Break rules keep the book legible across the gutter: each `.listings > ol`, each `.lines li`, each `.ad`, each definition row and each source paragraph never splits (`break-inside: avoid`); `h2` and `h3` never end a page (`break-after: avoid`); direct children of `main` avoid splitting except the listings, month, prose and source blocks, which are allowed to flow. The trade band sits between the running head and `main`, outside the columns, and spans both pages (`margin-top: -.6em` in the spread) while the running head above it spans the left page only.

**Opening at a trade.** A thumb tab or band cell is a fragment link to the trade's `h2` on the home. `.listings h2` carries `scroll-margin-top: 1.2em`; the targeted head and its rule turn red (`.listings h2:target`), the city labels in the list under it turn red (`.listings h2:target + ol .k`), and one `.book:has(#trade:target) .tabs a[href$="#trade"]` selector per trade, ten in all, paints the matching index cell Red Ink with white text. No script is involved.

Vertical order on every page is the same in all three states. Running head (one or two lines, 2px rule beneath, 0.9em below), then the lead display ad, then the month's notice ad, then the heads and lines, then any prose, then the colophon 2.2em below a 2px rule. Rhythm is in ems of the root, not a pixel scale. Ledger rows pad 0.13em, two-line listings 0.3em over 0.32em, ads sit 0.8em apart, heads carry 1.1em above and 0.3em below, month blocks on the owner page are 1.6em apart. Prose is capped at 72ch. Nothing in the book is a grid or a card.

Phone (390x844) first viewport, as shipped: running head, the lead box with title, red tagline and the two selects over the red button, the top of the notice box, and the tab strip. The owner page at 390 shows running head, the trade-and-city title with the question, the notice, and the first listing group above the fold.

## Elevation & Depth

Depth belongs to the book as an object, never to anything printed on it. On the paper there are no drop shadows, gradients or layered surfaces; ink sits on paper, boxes are drawn with rules, and the single inset `box-shadow` on the lead ad (`inset 0 0 0 3px paper, inset 0 0 0 5px red`) is a printing device, not elevation. On a phone the whole screen is paper and nothing casts a shadow at all.

From 800px the book sits on the desk and one thing casts a shadow. The book carries a page-stack edge, a zero-blur stacked `box-shadow` of darker yellows stepping 2px at a time down and out to both sides, five steps on the closed book (`-2px 2px 0 #d8b83e, 2px 2px 0 #d8b83e` through `-10px 10px 0 #a88b23, 10px 10px 0 #a88b23`) and six on the open book (adding `12px 12px 0 #9b7f1f`), with one soft shadow underneath (`0 28px 70px rgba(0,0,0,.65)` closed, `0 32px 80px rgba(0,0,0,.7)` open). The trade band is printed on the page and carries no shadow. The desk itself is a fixed radial gradient lit from the top centre. The open book's spine is a translucent gradient band, a fold in the paper, not a lifted surface.

### Shadow Vocabulary
- **Page stack, closed** (`box-shadow: -2px 2px 0 #d8b83e, 2px 2px 0 #d8b83e, -4px 4px 0 #cdad36, 4px 4px 0 #cdad36, -6px 6px 0 #c1a22f, 6px 6px 0 #c1a22f, -8px 8px 0 #b59728, 8px 8px 0 #b59728, -10px 10px 0 #a88b23, 10px 10px 0 #a88b23, 0 28px 70px rgba(0,0,0,.65)`): the `.book` from 800px to 1099px.
- **Page stack, open** (the same series continued with `-12px 12px 0 #9b7f1f, 12px 12px 0 #9b7f1f`, soft shadow `0 32px 80px rgba(0,0,0,.7)`): the `.book` from 1100px.
- **Lead double rule** (`box-shadow: inset 0 0 0 3px #f3cf4a, inset 0 0 0 5px #b3121e`): the lead ad's second rule, at every width. Not a shadow in effect.

### Named Rules
**The Book Casts, Ink Does Not Rule.** The stacked hard shadow is the page edge of the book and is a property of the book object only. No element on the paper, no ad, button, head, line or prose block, gets a shadow, a glow or a gradient; a surface that needs to read as separate is boxed with a rule in one of the two inks.

## Shapes

Square. `border-radius: 0` is set explicitly on the select and the button, and every box, rule and listing is a hard rectangle. The one exception is the phone thumb tabs, rounded on their outer edge so they read as the cut index of a book, `0 7px 7px 0`; from 800px the index is a square black band whose cells are divided by 1px hairlines of translucent paper (`rgba(243,207,74,.28)`), none before the first cell. Rules come in three weights, 1px dotted black for leaders, 1px and 2px solid black under heads, the running head and the colophon, and 3px solid red around display ads, doubled on the lead ad by the inset shadow (3px paper, then 2px more red). The book's own silhouette on the desk is a rectangle with a stepped stack of page edges at its sides and foot, and from 1100px a soft spine down the middle. Links are underlined at 2px thickness with a 0.12em offset; inside source paragraphs the own-site link and its legend sample are 1px. The finder's select arrow is a 16x10 black triangle in a data URI, the only glyph in the build.

## Components

### Buttons
- **Shape:** square, no border (`border-radius: 0; border: 0`), full width of its ad.
- **Primary (See who AI names):** Red Ink ground, Yellow Paper text, Bebas Neue at 1.55em with 0.02em spacing, padding `0.18em 0.5em 0.14em`, 0.2em above. One per page and only in the lead box.
- **Hover / Focus:** ground to Red Ink Deep over 0.15s ease-out; focus-visible adds the global 3px red outline offset 2px.
- **Active:** ground flips to Black Ink, text stays paper.
- There is no secondary or ghost button in the build.

### Inputs / Fields
- **Style (finder select):** transparent ground on the paper, 2px Black Ink border, square, full width, uppercase Bebas Neue at 1.14em, padding `0.22em 2.2em 0.2em 0.55em`, native appearance off, black triangle arrow set `right 0.6em center` at 0.85em by 0.55em. Placeholder option reads in Black Ink, not grey (`:invalid` is pinned to ink).
- **Label:** visually hidden (`.vh`); the placeholder option carries the prompt. Fields stack with 0.4em between.
- **Focus:** global 3px red outline, offset 2px. No error state exists; the two selects are `required` and the submit script does nothing until both have a value.

### Display ads (the boxed containers)
- **Corner Style:** square.
- **Background:** the paper shows through; ads are never filled.
- **Border:** 3px Red Ink. The lead ad adds the inset double rule (3px paper, 2px red) and pads `1em 0.95em 0.95em`; the notice ad pads `0.55em 0.75em` and sets one sentence at 1.14em with underlined links.
- **Contents by page:** on the home the lead ad holds the title, the red tagline at 0.95em and the finder; on every other page it holds the page title, a red "Asked of" line at 1em and the quoted question at 1.25em. The notice ad always states the month, the engines, the date and the N.
- Ads sit 0.8em apart and are the only boxed containers; nothing else gets a border on all four sides. On the open book an ad never splits across the spine.

### Ledger lines (the signature component)
A row is label, dotted leader, value on one baseline. `display: flex; align-items: baseline; gap: 0.35em`, padding 0.13em, with a `::after` flex spacer carrying `1px dotted` Black Ink lifted 0.32em to sit on the baseline. The value is right-aligned and may carry a `small` unit at 0.72em. A linked row turns its label red on hover; links inside a label or value underline on hover. On the home the rows run two per line (`.lines.two`, 1.4em gutter, rows `break-inside: avoid`). Definition lists reuse the same rule set (`dl.lines`). On the open book a whole `.listings > ol` moves to the next page rather than splitting, and no single `li` ever splits. The `ledger` class that build.py adds to figure blocks has no rule of its own; those blocks render as plain lines.

### Two-line listings (owner page)
Business name on the first line at 1.05em, the engines that named it on the second in Label size, each row padded `0.3em 0 0.32em` with no leader. From 800px the row folds to one line, name then leader then engines, padded 0.2em. Hover turns the name red. Engine identity is the name as text; there is no mark, dot or column per engine.

### Source paragraphs (owner and engine pages)
One paragraph per engine, 0.95em, line height 1.3. The engine name is a link in normal weight, followed by the model id and collection date in `small` at 0.75em, a line break, then domain links separated by a middle dot. A domain classed `.own` is red and underlined at 1px with a visually hidden "(own site)" suffix, and the `.legend` line under the block spells out the convention in words (its `.legend-sample` carries the same 1px underline), so the colour never carries the meaning alone. A source paragraph never splits across the spine.

### Navigation
- **Running head:** a flex row at 1.1em, with the home link on the left and the month links on the right separated by black pipes (`::before` content "|"), then a second line of section links at `clamp(1em, 4.7vw, 1.34em)` with the same pipe separators. No underlines; the current month is red and underlined, the current section is red. A 2px black rule closes the head. On the open book it spans the left page only.
- **Thumb tabs, phone (under 800px):** a fixed vertical strip riding the right edge of the paper, 6.9% of the book wide, from 3.2em below the top of the window to 1.2em above the bottom, one tab per trade, each a flex-grown Black Ink block with paper text in `writing-mode: vertical-rl`, sized `max(8px, min(0.62em, 1.45vh))` with 0.05em spacing, 3px apart, rounded `0 7px 7px 0`. Hover slides 3px left and keeps paper text; the current trade's tab is Red Ink with white text.
- **Trade band, desk (from 800px):** the same `.tabs` markup printed as a band under the running head. The list is a Black Ink grid, `repeat(5, 1fr) on a single page and repeat(10, 1fr) in the spread, so the band never wraps unevenly; cell text min(.98em, 1.6vw), min(.98em, 1.15vw) in the spread`, no gap, `margin: -.45em 0 .9em` (`-.6em` top in the spread), `padding: 0 .2em`. Each cell is a horizontal, centred link in Yellow Paper on the ink, Bebas Neue at 0.98em with 0.05em tracking, no wrapping, padding `0.34em 0.5em 0.26em`, no radius, no shadow, no transform, with a 1px `rgba(243,207,74,.28)` hairline on its left except the first. Hover is white text on pure black (#000). The current trade (`aria-current`) and a targeted trade are Red Ink with white text, the one place red marks state in the band.
- The index is hidden in print.
- **Skip link:** black ground, paper text, parked at `left: -200vw` and brought to 0.5em on focus.

### Colophon
Every page ends with a 2px black rule, a centred "Published by EVOIX, DeLand, Florida" line at 0.97em in caps, and one Note-size Barlow paragraph in Faded Ink carrying licence, author and data date. On the open book it sits on the right page only.

## Do's and Don'ts

### Do:
- **Do** put every page on the same yellow paper (`{colors.paper}` under the two tiled plates) inside the book; the owner page is a spread of the book, not a white insert.
- **Do** lead every page with the two boxed display ads, 3px red, the lead one double-ruled, then move to plain heads and ledger lines.
- **Do** size everything in ems of the root `clamp(14.7px, 3.776vw, 20px)` and guard small sizes with a `max(Npx, Xem)` floor.
- **Do** set caps once on `body` and opt into mixed case only through `.prose`, which switches to Barlow Condensed and a 72ch measure.
- **Do** write engine identity and source class in words (the engine name under a listing, the "Red and underlined" legend) so colour never carries meaning alone.
- **Do** keep red for state and rules, black for text and structure, and let the paper show through every container.
- **Do** keep one trade index on every page, one cell per trade, black with paper text: fixed thumb tabs down the right edge on a phone, a printed band under the running head from 800px, with the current or targeted trade red in both.
- **Do** let a new section flow through the open book's two columns and mark its unsplittable units with `break-inside: avoid`, the way ads, list items and source paragraphs already are; the spread is CSS multi-column, never a script or a second DOM.

### Don't:
- **Don't** introduce a third hue, a grey, or a link blue on the paper; Faded Ink is the only softened value and it stays under 16px mixed-case notes.
- **Don't** draw engine marks, logos, coloured dots or labelled columns for the four engines; the build rejected them and PRODUCT.md forbids engine logos.
- **Don't** put a shadow, glow, gradient or radius on anything printed on the paper; the page-stack edge belongs to the book as an object on the desk and is not a treatment for other elements.
- **Don't** set Bebas Neue or League Gothic above 400 or bold anything; emphasis is size, red, or underline.
- **Don't** use cards, stat tiles, grids or a dashboard table for figures; figures are ledger lines with dotted leaders, and the home's rows run in two CSS columns.
- **Don't** use icons beyond the select's triangle; this includes glyph bullets and arrow icons on links.
- **Don't** fill an ad box or any other area with red; the primary button is the largest red surface allowed.
- **Don't** change the phone view to serve the desk or the spread; everything from 800px up is added inside media queries and the comp's phone state stays as built.
- **Don't** hang an index, rail or tab strip beside the paper on the desk; every side-index treatment was rejected on review and the index is printed on the page.
