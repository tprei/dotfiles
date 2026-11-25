# Design systems

Includes modified guidance from Impeccable. See [sources](SOURCES.md).

Keep three forms of authority distinct. A product record says what is true and who it serves. The design system says how durable visual roles work. A surface brief says what a particular screen or artifact needs to do. Missing a document does not erase an established product or visual system. Capture the smallest useful record, at the repository's established location and only within scope.

## Record product truth

Consult docs, copy, workflows, roles, framework and platform, accessibility needs, and existing assets. Confirm material unknowns in rounds of no more than three focused questions; mark open questions and inferred facts. Record platform (web, iOS, Android, or genuinely adaptive), greenfield stack if not settled, users and context, purpose and success, distinctive mechanism and positioning, capabilities and limits, brand commitments, available evidence, and three to five durable principles. Keep surface strategy, imagined testimonials, and look exploration out. A mobile web view is not native merely because it has a wrapper. Preserve confirmed facts on redesign.

## Record the visual system

Read real custom properties, framework theme values, token files, reusable components, base CSS, and computed styles. Record source and semantically group what is actually reused: palette roles, type tiers, spacing and density, grid and breakpoints, shape and radius, layers and motion, canonical controls, state and variant behavior. Separate authorable seed direction from observed implementation; capture final rules after build. If a seed is all you have, state invariants and role relationships, omit unbuilt tokens and components, and record the implemented system after the first build. Preserve chosen system provenance unless the user replaces it. When an existing document would change, agree on whether to refresh, replace, or merge; do not silently canonize unresolved drift.

For projects using the [portable DESIGN.md format](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md), keep tokens normative in YAML and use prose to say when and why. Use real canonical CSS colors, typography roles, `rounded`, `spacing`, and `components`. Component references such as `{colors.primary}` resolve to primitives; primitives do not reference one another. Portable component fields are `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`, and `width`. Put extra motion, breakpoints, elevation and state guidance in prose or the existing project format, not fabricated YAML keys. Keep the canonical body order: Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts. Drop inapplicable sections. Name the visual thesis and one to three useful, testable rules where warranted. Document a range only when it is real: a tonal ramp may have eight steps from about 15% to 95% lightness with reduced chroma at the extremes, but never replace existing tonal values to fit an example.

## Extract only what repeats with the same purpose

1. Inventory existing component, variant, import, and token conventions. Identify the same role or pattern used at least three times: controls, type role, layout rhythm, form row, empty state, motion, or state pattern. Similar rendering with different intent is not evidence for one abstraction.
2. Plan exact primitives, semantic aliases, reusable components, needed variants, and every migration path. Document about five to ten representative components if the system warrants it, including real hover, focus, active, and error treatment and any signature control. Use short examples with the existing type, naming, and icon family. Avoid restating values in more than one authority or adding variants the real UI does not consume.
3. Migrate every relevant caller, preserve labels, focus, behavior and appearance, and remove dead versions. Inspect real instances rather than only an isolated example. If no coherent system exists, agree on a boundary before creating a competing one.

A defect is not a token merely because it ships. Record inconsistencies as such. Keep the [absolute bans](../SKILL.md#absolute-bans) out of the system, and keep the current task from turning into an unrelated documentation or migration project.
