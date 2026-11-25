# Craft floor

Includes modified guidance from Impeccable and Anthropic. See [sources](SOURCES.md).

Apply this after deciding the direction. Use computed values and rendered states, not assumptions from source. A confirmed brief may override a saturation warning or a design default; it does not override the absolute bans or accessible operation.

| Axis | Acceptance check |
|---|---|
| Contrast | Text and placeholders at least 4.5:1, large text at least 3:1, required non-text boundaries and focus marks at least 3:1. Check rendered colors, including images and overlays. Use a readable hue-related secondary ink on colored surfaces, not a washed-out gray. |
| Spacing | Group related elements tightly, separate groups generously, and leave more space above each heading than below it. Give page edges, containers, and both ends of scrollers breathing room. |
| Type | Build recognizable size and weight steps. Start prose around 16px and 65–75ch; use at most 6rem display type by default and never track tighter than −0.04em. Balance headings; test real wrapping, zoom, and user font sizes. |
| Depth | Use a tone shift, a border, or a neutral offset soft shadow to communicate depth. Do not use two devices for a routine boundary. A floating dialog can warrant both. |
| Assets | Use a coherent icon family and genuine logos. Choose the medium that fits the material. A photo needs real alpha or an honest crop, not a polygon approximating a silhouette. Keep artwork separate from live text and controls. |
| States | Cover default, hover where available, keyboard focus, active, selected, loading, empty, disabled, error, success, stale, partial, and permissions where applicable. Keep controls functional in context; protect unsaved work and reveal errors with recovery. |
| Motion | Keep default content visible. Make feedback immediate and explain the transition; author one focal sequence rather than repeating entrances. Preserve equivalent feedback with reduced motion. |
| Copy | Name the actual action and outcome in the user's language. Show real evidence and protect factual claims. Make every brief requirement findable in seconds. |

Theme text selection, input caret, focus ring, link underlines and offsets, and aligned numerals; keep scrollbar behavior native and change its ink only where it helps recognition without reducing access. Use platform control semantics, familiar affordances, and one vocabulary for like controls. Use icon buttons for familiar tools, with accessible names and focus-capable tooltips for unfamiliar tools, swatches for colors, segments for modes, checkboxes or switches for binary settings, the right numeric input for precision, menus for options, tabs for views, and named buttons for commands. A tooltip alone does not label a control.

Use the installed icon library rather than drawing near-copies of common marks. For a new web set, Lucide is one option; keep authentic brand marks and native symbols in their proper roles. Keep glyph size distinct from the hit area.

## Refuse the default, not the brief

- Do not scaffold a page with identical feature cards, cosmetic icon tiles, section numbers that do not convey order, a hero-metric template, or a modal that does not need protected focus. Use structure before chrome. Repeated independent items can earn a card; nested card shells do not.
- Do not use glass for atmosphere alone, colored shadows to feign depth, or hard block shadows outside a deliberately neobrutalist system. Use native system materials for true overlays. No decorative spotlight, orb, or halo. See [color](color.md) for narrow atmosphere permissions.
- Do not use a platform default face as an expressive new brand's display voice or monospace as a technical costume. Familiar faces are valid when serving established products or native controls.
- Do not use ornamental metrics, meaningless badges, a fake caret, or sparklines and gauges without real inputs. Never add unverified prices, customers, numbers, capabilities, or testimonials; mark demonstration data unmistakably.
- Do not use militarist, extremist, supremacy, or hate insignia and their stylized variants as decoration. Choose neutral forms from that world. Preserve truthful documentary material where the subject requires it.

The floor does not pick an aesthetic. After it passes, commit to the chosen world. Review full detail in the [catalog](slop-catalog.md) and [pre-ship checklist](pre-ship.md).
