# Color and colorize

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Audit project assets, tokens, computed values, roles, themes, and states before adding a swatch. Separate binding brand and semantic roles from incidental grayscale or hard-coded drift. Name intended temperature, value contrast, dominant relationship and dosage. Describe the actual use scene and light; do not reach for dark mode by genre or assume light mode wins.

## Choose and map a strategy

- **Restrained:** quiet dominant field, supporting neutral, and one accent. Use the 70/30/10 rule of thumb for dominant, secondary, and accent areas. Most Operate and Read surfaces belong here; spend the accent on action, selection, or meaningful state, not decoration.
- **Committed:** one saturated color owns a deliberate 30–60% region. **Full palette:** three or four named roles carry different jobs. **Drenched:** the surface itself is the color. These are choices for a committed world, not excuses for many competing swatches. Impeccable treats percentages as contextual; the slop guard's 70/30/10 is a useful restrained starting point, not a measured quota. Keep one primary action accent unless the established system calls for more; state and data tokens need their own roles.
- Assign canvas, raised surface, primary and muted ink, outline, action, focus, selection, disabled, info, success, warning, and error. Remap semantic tokens per theme. A second subtly different neutral can identify navigation or an inspector without a border. Tint neutrals when that binds the brand; gray can be the right neutral but washed-out gray on an already colored ground rarely gives useful hierarchy. Use explicit ink values where alpha would depend on context.
- Use the existing color space; consider OKLCH for a new system. Bend chroma down near black and white, and check gamut in the shipping engine. Give category colors sufficient differences in lightness or chroma plus a label, mark, shape, or texture. Do not let inactive states take action saturation. Respect domain and platform semantics rather than reflexively using green or red everywhere.

## Resolve atmosphere guidance

OpenAI's visual-first skill encourages a relevant image, pattern, or atmospheric gradient instead of relying on a flat background for a branded hero. Its frontend prompt guide rejects gradient/SVG hero stand-ins and decorative orbs. Slop guard recommends one focal gradient, despite a more permissive checklist warning only beyond three. Use the stricter limit: default to flat role-based surfaces, including routine product controls and buttons. On expressive work use at most one focal gradient if the subject or state benefits from it; it may support imagery but cannot be the subject. One authored, domain-specific texture is another option. Never gradient-fill text or add decorative glows, radial halos, bokeh blobs, glow borders, or neon effects for atmosphere. Data ramps encode values and are not decorative gradients.

## Check perception and contrast

| Target | Minimum |
|---|---|
| Regular and placeholder text (WCAG AA) | 4.5:1 |
| Large text (at least 18pt/24px regular or 14pt/about 18.7px bold) | 3:1 |
| Required non-text control boundaries, meaningful graphics and focus marks | 3:1 against adjacent colors |
| Enhanced text contrast (AAA) | 7:1 regular, 4.5:1 large |

Verify computed foreground/background pairs in both appearances and all actionable, overlay, and image states; do not judge with the color picker alone. Inactive controls are exempt from the WCAG contrast minimum but still need intelligible context. Test common color-vision deficiencies, high contrast/forced colors, the actual ambient scene, and dark elevation on its own terms rather than as inverted light. If a color cannot be explained by role or subject, remove it. If a state becomes unreadable when the palette is desaturated, add a code other than color. Verify again after remapping tokens, then [polish](polish.md).
