# Typography and typeset

Includes modified guidance from Impeccable and Anthropic. See [sources](SOURCES.md).

## Assess independently

Inspect real pages before reading mechanical findings. Record families, loaded weights, computed sizes, roles, measure, heading wrapping, body contrast, zoom behavior, font loading and fallback. Then scan for arbitrary values, missing weights, weak hierarchy, size drift, spacing, overflow, or hidden text. Join the two assessments. A clean scan cannot tell you that a face belongs to the subject.

## Choose a role system

Use one family if it carries the roles. If two, make the voices clearly distinct; name what the second does that the first cannot. Plan display, headings, body, controls, labels, caption, and measured data as needed. Use semantic role tokens. Tune size, space, weight, width, and ink together instead of solving every distinction with size. On an existing surface improve within confirmed faces; reroute to [shape](shape.md) if replacing the typographic identity. On native, use [platform scaling](native.md).

- Operate: fixed rem roles, scale ratio 1.125–1.2, one workhorse family; save display type for display, never dense labels and inputs. Stable type supports dense tables and alignment. Read: predictable body size and hierarchy, a ratio and typeface that sustain reading. Persuade and Experience: a responsive display scale can carry the composition if the headline still fits the role. Default display ceiling 6rem; use actual content to size the frame.
- On the web start ordinary body at 1rem or 16px; reserve 14px for genuinely secondary copy. Use 16px or larger on mobile inputs to avoid iOS Safari focus zoom. A 45–75ch range serves varying copy and type; aim 65–75ch for normal prose, 60–75ch on docs, and under 80 characters by default. Tables can legitimately run 120ch or more. Set prose near 1.5 leading, then tune for face, contrast, width, and script; longer lines and many serif faces need more leading. Use paragraph spacing or indentation, not both by habit.
- Letter spacing: start with the face's metrics. OpenAI's prompt guide chooses fixed type roles and zero tracking; Impeccable allows deliberate display tuning down to −0.04em and responsive display sizing. Keep routine and body text stable and near default tracking. Make a responsive display exception only for justified expressive composition, preserve zoom, and inspect at all widths. On dark, add a little leading and tracking and one weight step only if needed optically.
- Use `font-variant-numeric: tabular-nums` for comparable values, timestamps, or counters; choose lining or old-style figures as the context warrants. Use mono for code, identifiers, and genuinely measured data, not because the subject is technology. Body in sentence case; avoid all-caps labels by default, oversized italic serif as automatic editorial voice, and a single colored or italic word in a headline as a template for emphasis.
- In branded display, question default Inter, Arial, Roboto, Geist, Plus Jakarta Sans, Outfit, DM Sans/Serif, Instrument Sans, Space Grotesk/Mono, IBM Plex, Syne, Fraunces, Playfair, Cormorant, Lora, Crimson, Newsreader, or Recoleta. Familiar native or established faces are legitimate when deliberate. Subject category alone is not a reason to choose a face. Sample its letters in the actual headline and text.

## Compose the text

Use `text-wrap: balance` for short headings and centered blocks; use `text-wrap: pretty` for prose where supported. A one-word tail usually needs a fix; two words are fine. In a narrow column widen it or edit the copy before forced breaks. If a one-word line is an intentional focal treatment, inspect it at every size and retain that intent. Put manual breaks at phrase boundaries. Left/start-align ordinary paragraphs; justify only when publication quality warrants it, with correct `lang`, hyphenation, and inspection for rivers. Do not infer semantic heading levels from visual size.

On a flex control, apply `text-box: trim-both cap alphabetic` to a block label child, not an anonymous text item or the entire button. Match fallback cap height with metric `size-adjust` if using trim; line-box ascent/descent adjustments do not change the optical cap center. Mixed-case words sit visually lower than all caps. Inspect actual labels and icons, not just boxes.

## Deliver and verify

Use WOFF2 where loading web faces, only used weights and script coverage, metric-compatible fallbacks, and `font-display: swap` or `optional` as appropriate. Preload justified critical faces only. Verify invisible text and reflow on throttled cold load. Check long names and headings, different scripts, translation expansion, 200% zoom, and extreme widths. Let text wrap and containers grow first. Never use a tiny font to squeeze routine copy into a broken grid. On meaningful truncation, preserve full text via a reachable display and distinguish otherwise identical names. Verify role distinction, rhythm, and glyph quality in both themes and rendered states, then [polish](polish.md).
