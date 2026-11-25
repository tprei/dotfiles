---
name: frontend-design
description: Design, redesign, critique, or polish anything a user sees (web and native UI, dashboards, generated images, SVG reports, terminal UIs) so it reads as chosen rather than generated. Use before any visual edit, including small refinements.
---

# Frontend design

Design that reads as chosen, not generated. Distilled from [Impeccable](https://impeccable.style/) (Paul Bakaus, Apache-2.0), Anthropic's `frontend-design` skill, OpenAI's frontend guide, and [frontend-slop-guard](https://github.com/airtaxi/frontend-slop-guard).

## Process

1. Name the mode from the surface, not the product:
   - **Operate:** the user does a task: apps, dashboards, tools, status reports. Ambition shows as precision and restraint; familiar patterns earn their place.
   - **Read:** the user understands something: docs, articles.
   - **Persuade:** the user decides: landing pages, pricing. Full commitment and a point of view.
   - **Experience:** the work itself: portfolios, galleries.
2. Ground in the subject and the incumbent system. Read the existing tokens, components, and type before deciding. The brief wins over your taste: honor pinned fonts, palettes, and eras.
3. Plan before code. Write down:
   - 4 to 6 named colors, each with a role
   - 1 or 2 clearly different typefaces with their roles and a type scale
   - an ASCII layout sketch with alignment
   - the one memorable move

   Then compare the plan against the default you'd produce for any similar brief, and revise every part that matches it.
4. Build to the craft floor below.
5. Look at the rendered result at the size it ships at (browser screenshot, PNG, phone width). Batch fixes per look. Critique it against the refuse list, then remove one accessory before shipping.

## Craft floor

- **Contrast:** body text ≥ 4.5:1, large text ≥ 3:1. Secondary text on a colored surface is tinted from that hue, never gray.
- **Spacing:**
  - Tight groups, generous separation, and more space above a heading than below it.
  - Content never touches a container edge.
  - Equal gaps everywhere hide grouping.
- **Type:**
  - Product UI uses a 1.125 to 1.2 scale ratio; emphasis comes from weight and color, not giant sizes.
  - Use tabular figures for aligned numbers.
  - Prose runs 65 to 75 characters per line.
  - Choose a face with character for the subject; never fall back to a default stack (Inter, Roboto, Arial, DejaVu, the system font).
- **Depth:** neutral shadows with an offset and a soft blur. Declare elevation once: a border or a shadow, not both.
- **Color:** color carries meaning (state, category, identity). Follow 70-30-10, with one accent for action and state. Inactive states never get full saturation.
- **Icons:** one drawn set in a consistent stroke and weight, or real brand logos for real entities. Never emoji or Unicode glyphs standing in for icons.
- **States:** loading, empty, error, partial, stale, disabled. Empty states direct the next action; partial data is marked and never reads as zero.
- **Copy:** the product's own words. Each element does one job; cut until deleting more would lose meaning.
- **Motion:** it conveys state or answers an action, in 150 to 250 ms for product UI. Use one authored moment at most; never give every section the same entrance.

## Refuse

These are defaults, not choices. Use one only when the brief asks for it.

- **Gradients and glows:**
  - More than one gradient per screen, or a gradient that isn't on the focal point.
  - Gradient text.
  - Colored glows, radial halos, ambient blobs, glassmorphism as decoration, neon on dark.
- **Cards:**
  - Identical card grids as the page structure.
  - Nested cards.
  - An icon tile stacked above a heading.
  - A colored stripe down one side of a rounded box.
  - Thick colored borders on rounded cards.
- **Labels and headings:**
  - Eyebrow kickers above headings.
  - Section numbers unless the content is a real sequence.
  - A badge above the headline.
  - The hero-metric template (big number, small label, stat strip, accent) as a reflex.
  - One accented word in a headline.
  - All-caps labels.
- **Strings:**
  - Meta strings joined with middle dots (`A · B · C`); separate with layout.
  - `Word — fragment` labels.
  - `→` appended to every link.
- **Type and palette:**
  - Monospace as a "technical" costume; reserve it for code and measured data.
  - AI palettes by habit: purple to cyan on near-black, cream with a serif and terracotta, black with one acid accent.
  - Rainbow palettes where color means nothing.
- **Status and chrome:**
  - Status badges that never change.
  - Decorative dashboard chrome or sparklines that don't come from real data.
- **Motion:** pulsing dots, bounce, marquees, fake liveliness.

## Operate surfaces and data

- One family often carries everything. Size follows importance; the most actionable fact leads.
- Chunk into groups of 4 or fewer. One row per item when possible; secondary detail appears only when it changes a decision.
- Charts come from real data. Axes stay quiet; highlight the one thing that matters (today, the peak, the threshold).
- Visual metaphors that encode state (heat for heavy use, a reward accent for untapped capacity) beat ornament. Keep each metaphor consistent across every view.
- Show freshness: when the data was taken and which sources are missing.

## Critique checklist

- Can someone who scans only headings, labels, and numbers understand the screen in 5 seconds?
- Is there one primary element, 2 or 3 secondary, and everything else muted?
- Does every color, border, icon, and container earn its place? Remove any that don't.
- Does anything on the refuse list appear without the brief asking for it?
- Does it hold up at the shipping size, with real content, long names, and empty and error states?
