# Layout and spacing

Includes modified guidance from Impeccable and Anthropic. See [sources](SOURCES.md).

## Set the structure

Map primary reading or task path, lead and support, groups, and bearing axes. Compare visual, DOM, keyboard, touch, and assistive-technology order. Start with proximity, alignment, whitespace, columns, real section breaks, and size. Add a boundary only when it conveys grouping, action, or depth. Let repeated objects repeat; vary structure where priorities differ, not every time a new section begins. Squint: one primary, two or three subordinate, everything else quieter. Check for fit using actual content, not stub text.

- Use the existing grid and scale. A 4-unit base supplies useful intervals an 8-only scale misses. Use small steps within groups and larger intervals between; more room above a heading than between it and its content. Use `gap` for sibling rhythm, padding for containment, margin or gaps for group separation. Verify computed values; selector specificity can silently cancel section or CTA spacing.
- Use grid for two-dimensional alignment, flex for content-driven rows or columns, and intrinsic wrapping before exact positions. Use container queries for reusable parts. Select flexible tracks (`minmax(0, 1fr)` as fits), `min-inline-size: 0` where needed, and fit/max constraints. Grow the canvas or move one region rather than squeezing all text. Keep no unaccounted whitespace caused by one introductory column overrunning the other.
- Give screens and scroll regions inner gutters, plus matching end room for the first and last items; a flush hero image is not permission for flush text. Align icons optically in consistent nominal square boxes; align tables and labels by their meaningful baseline or edge. Remove excessive radii that pinch the usable area. OpenAI suggests 8px or less for routine cards unless the system says otherwise; use an intentional shape scale, not the same radius on chips, panels, and every button.
- Declare elevation once per ordinary surface: fine edge, tonal change, or neutral offset shadow. Menus and dialogs genuinely floating above can need both contour and shadow. Keep a panel plain if the surface treatment does not help interaction or understanding. Prefer full-width sections with readable inner widths, not a grid of floating feature panels.

## Compose a fold

For a branded, image-led landing page, let the hero ground run edge to edge; constrain only the inner action and text column. The visual should be one dominant plane, not a floating preview, split with card fragments, or media behind detachable stickers. A split can work when text sits on a calm, deliberately unified side. Impeccable allows working forms or a world-specific opening beyond image-first; choose the form that demonstrates the mechanism better. If a sticky header takes space, subtract it from a minimum like `calc(100svh - var(--header-height))` or safely overlay; avoid rigid heights that clip wrapped content. Show enough below to establish scrolling without sacrificing the action. Verify portrait, landscape, wider desktop and the user's actual viewport.

## Keep fixed-format elements stable

Give boards, tiles, counters, media, tools, and icon hit areas intentional size constraints: aspect ratio, grid tracks, tabular figures, min/max, container-aware dimensions, and reserved loading space. Labels, actions, hover, and fetches should not shift neighbors. Overlay menus or dialogs outside scroll clipping; constrain them by the viewport, not their card. Check sticky content and safe areas at zoom, with the keyboard visible, and at full content length. See [adapt](adapt.md).

## Verify the layout

Compare spacing by computed values and eyes, then check focus order, slow and empty states, localization, overflow, clipping, hierarchy and visual density against the real path at shipping widths. If layout treatment obscures the source order, fix the source instead of rewriting navigation with positive tab indexes. Keep repetition where it aids recognition. Route local cleanup to [polish](polish.md).
