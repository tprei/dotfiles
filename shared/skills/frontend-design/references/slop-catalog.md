# Slop catalog

Includes modified guidance from Impeccable and frontend-slop-guard. See [sources](SOURCES.md).

Use the catalog to inspect a surface, not to choose an aesthetic. A match is a reason to check the task, intent, and actual render. Distinguish a source clue, a rendered defect, and a design judgment. Check an absolute ban against the [craft floor](craft-floor.md), not against a permissive example. Explain intentional exceptions to defaults with evidence rather than hiding findings. See [attribution](SOURCES.md).

## Impeccable checks

The live catalog contains 62 detector rules and six design-review patterns. All 68 entries follow; a dagger (†) marks the six that require design judgment. Check source for declared patterns and the rendered result for things source does not establish, especially overflow, timing, and contrast over images.

### Design system

| Named check | Self-check | Fix |
|---|---|---|
| `design-system-font` | Is the computed face outside the approved role stack? | Use the approved face or add an agreed reusable role to the system. |
| `design-system-color` | Does this ink or surface bypass the documented palette? | Map to a semantic role; update the palette only for an intentional new role. |
| `design-system-radius` | Is this corner radius a local stray? | Choose the scale's matching shape or record a confirmed addition. |
| `design-system-font-size` | Does the computed size belong to the role scale? | Use the existing step; add a step only for a distinct repeated role. |

### Visual details

| Named check | Self-check | Fix |
|---|---|---|
| `codex-grid-background` | Is this hairline background grid a measurement surface, or a blueprint costume? | Remove it unless it guides a real canvas, map, chart, or measured task. |
| `hard-offset-shadow` | Is a crisp, unblurred shadow displaced 4px or more on a design that did not commit to neobrutalism? | Use tone, a fine edge, or a neutral offset soft shadow. |
| `border-accent-on-rounded` | Is a thick colored outline louder than the rounded card's content? | Use a fine neutral edge or let the field define the container. |
| `glassmorphism` † | Do blur, translucent cards, and glow borders imply no real layer? | Flatten ordinary surfaces; use material only for genuine overlap and depth. |
| `side-tab` | Does a one-sided stripe make a normal card look like an alert? | Remove side stripes on rounded containers; use a state label, icon, tint, or consistent full border. |
| `gpt-thin-border-wide-shadow` | Does a routine card use both a 1px hairline and broad diffuse shadow? | Choose one elevation signal; reserve combined treatment for a genuine floating layer. |
| `repeating-stripes-gradient` | Do repeating diagonal/horizontal stripes fill space without a task or material reason? | Use a plain field or a texture native to this subject. |
| `over-round` † | Do very large corners pinch a small container or turn every object into a pill? | Size corners to purpose and usable room; reserve pill geometry for pill-shaped roles. |
| `sketchy-svg` † | Does a crude hand-coded mascot, doodle, or noise-filter graphic weaken otherwise finished work? | Use deliberate art, a photograph, or omit the visual. |

### Typography

| Named check | Self-check | Fix |
|---|---|---|
| `kicker-above-heading` | Is there an extra label directly above a title? | Delete the decorative kicker; keep useful words in the heading or body, or a genuine breadcrumb. |
| `undersized-ui-text` | Do people need zoom to read controls, menu labels, or navigation? | Use a readable role size and larger hit area or restructure the controls. |
| `straggler` | Does prose end on one stranded word at a supported width? | Try `text-wrap: pretty`, change measure, or edit prose. Keep only a purposeful emphatic break. |
| `unbalanced-heading` | Does the last line of a heading look like an accidental stub? | Use `text-wrap: balance` or edit the phrase; check all widths. |
| `flat-type-hierarchy` | Do heading, subhead, and body look the same when you squint? | Differentiate roles through size, weight, and space, not arbitrary styling. |
| `icon-tile-stack` | Does each feature heading have a rounded square icon above it? | Remove the tile; put a meaningful icon beside the title or in the content. |
| `italic-serif-display` | Is an oversized italic serif supplying generic editorial mood rather than the subject's voice? | Choose the subject's lettering, usually roman or a different display treatment. |
| `hero-eyebrow-chip` | Does a detached pill over the H1 look clickable or distract from the offer? | Remove it; move meaningful information into the headline or support line. |
| `oversized-h1` | Does a long display headline fill the opening and push its proof or action out? | Shorten the claim, reduce display size, or restructure the fold. |
| `extreme-negative-tracking` | Do letters crowd or collide, especially at narrow sizes or below −0.04em? | Return toward the face's intended spacing and inspect actual glyphs. |
| `overused-font` | Is a familiar face such as Inter or Geist doing undifferentiated brand display duty? | Choose a voice for this brief; keep deliberate incumbent or platform families. |
| `single-font` † | Has one family made everything look flat, or does it already serve distinct roles? | Separate size, weight, and spacing first; add a second family only for a truly distinct role. |
| `all-caps-body` | Is running text in capitals, slowing recognition? | Set body in sentence case; reserve uppercase for necessary abbreviations or short, justified marks. |

### Color and contrast

| Named check | Self-check | Fix |
|---|---|---|
| `radial-halo` | Is a bright radial wash behind the hero acting as a generic background? | Remove it; use a grounded field or an image that carries the subject. |
| `radial-spotlight-glow` | Does a faint spotlight emphasize a region without saying why? | Replace it with proximity, hierarchy, or contrast that guides the actual decision. |
| `ai-color-palette` | Are purple gradients or bright cyan on black doing all the identity work? | Derive hue, dosage, and contrast from the subject and use scene. |
| `dark-glow` | Do glowing edges and neon accents flatten hierarchy in a dark theme? | Keep dark when it fits but switch to tonal depth and solid purposeful color. |
| `gradient-text` | Do headings or numbers vary in ink color across the glyphs? | Set solid ink and use size, weight or placement for emphasis. |
| `gray-on-color` | Does neutral gray text wash out against a colored ground? | Use readable hue-related or light ink and measure the actual pair. |
| `cream-palette` | Did beige become the reflex substitute for choosing a background? | Keep it only if the world owns it; select the other roles and value contrast as deliberately as the ground. |

### Layout and space

| Named check | Self-check | Fix |
|---|---|---|
| `numbered-section-labels` | Would removing 01/02/03 lose an order the reader needs? | Remove the label unless it means steps, chronology, or another true sequence. |
| `edge-flush-cards` | Do first and last cards hit a scroller's edge at each end? | Give both ends matching inset room and reserve room for focus. |
| `text-occlusion` | Does a layer cover meaningful text at rest or while open? | Move the layer, constrain its bounds, or reserve space for the text. |
| `first-viewport-column-overflow` | Does one opening column extend well below its peer, leaving a dead gap? | Rebalance or move the long content beneath both columns. |
| `heading-rhythm` | Is the heading closer to the preceding block than to its own content? | Increase room above or reduce room below. |
| `hero-metric-layout` † | Could you replace the huge number, small label, and stat strip with an unrelated product's values? | Lead with this product's mechanism; retain a metric only with baseline, unit, period, and decision value. |
| `identical-card-grids` † | Does an icon/heading/text grid give important and minor claims identical weight? | Group ideas by job; use a table, list, proof example, or a region with a real lead. |
| `monotonous-spacing` | Do equal gaps conceal which details belong together? | Tighten within groups and create larger intervals between them. |
| `nested-cards` | Does a card's parent already frame that content as a card? | Flatten with alignment, type, or dividers. |
| `line-length` | Do readers lose their place on the return from a long prose line? | Start at 65–75ch, then tune for typeface, language, and width. |
| `text-overflow` | Does a label spill, get clipped, or make the entire page scroll sideways? | Let text wrap and tracks shrink; use a dedicated scroll region for truly wide content. |
| `clipped-overflow-container` | Is an open tooltip, menu, or popover cut off by an ancestor? | Use the top layer or a portal, or remove clipping where not needed. |

### Motion

| Named check | Self-check | Fix |
|---|---|---|
| `pulsing-dot` | Does unchanged status repeatedly ask for attention? | Keep it still unless a real event requires notice; show the state in words too. |
| `blinking-cursor` | Does static copy imply that visitors can type? | Remove the fake caret; keep a caret only in real editable content. |
| `marquee` | Does a logo or text strip set the reader's pace or hide content? | Show a static list or a purposeful user-controlled sequence with pause and navigation. |
| `bounce-easing` | Do elastic or overshoot curves make a routine dialog feel fussy? | Use a quick decelerating curve; save literal physics for interactions that warrant it. |

### Copy

| Named check | Self-check | Fix |
|---|---|---|
| `repeated-container-text` | Does the exact same status or label occupy several slots in one container? | Say it once where it aids the decision. |
| `em-dash-overuse` | Are consecutive phrases joined by dashes instead of deliberate sentence structure? | Split sentences or use punctuation that explains the relationship. |
| `marketing-buzzword` | Could the claim appear on any marketing page? | Replace vague praise with a concrete action, improvement, or proof. |
| `aphoristic-cadence` | Does section after section stage a short slogan and a rebuttal? | State the distinction directly; save the device for one earned line at most. |
| `theater-slop-phrase` | Does calling a practice “theater” stand in for an explanation? | Name what it misses and why that matters. |

### Imagery

| Named check | Self-check | Fix |
|---|---|---|
| `shape-assembled-illustration` | Does a pile of primitive shapes impersonate a person, device, or scene at hero size? | Use finished subject-specific art, a photograph, or no artwork; keep vectors for real geometry. |
| `organic-clip-path` | Does a polygon or crude mask approximate a torn or photographic edge? | Use an actual alpha matte or deliberate clean crop. |
| `buried-raster` | Does a nearly opaque overlay leave the image present only in source? | Restore its visible contribution or remove the asset. |
| `broken-image` | Does a missing/empty `src`, placeholder, or unresolved reference leave broken media? | Supply and load the intended asset, or remove it cleanly if not needed. |

### General quality

| Named check | Self-check | Fix |
|---|---|---|
| `script-error` | Does an uncaught error on load leave controls dead or content hidden? | Repair the cause and exercise the affected route and states before styling. |
| `content-hidden-at-rest` | Does content remain at zero opacity when animation or JavaScript fails? | Make the readable state the default and progress only if it can actually run. |
| `cramped-padding` | Is a line or icon pressed against its button or card, for example with only 2px vertical padding? | Add role-appropriate spacing and verify the touch target independently. |
| `body-text-viewport-edge` | Do paragraphs reach the viewport edge on mobile? | Add container gutters and safe-area room; verify narrow portrait and landscape. |
| `justified-text` | Are irregular gaps or rivers visible in a justified paragraph? | Start-align ordinary UI; if the editorial treatment needs justification, set language, hyphenate, and inspect. |
| `low-contrast` | Do actual text/background pairs fail 4.5:1 ordinary or 3:1 large? | Change ink or ground at the role level and remeasure the real state. |
| `skipped-heading` | Do headings skip hierarchy levels for visual size? | Reflect the document structure with heading levels and set size separately. |
| `tight-leading` | Can the eye track from line to line without effort? | Start at about 1.5 line height for body, then tune for measure and face. |
| `tiny-text` | Is required reading set like 9px fine print? | Start near 16px body and make secondary text readable as well. |
| `wide-tracking` | Does loose letter spacing disrupt word shapes in running copy? | Return body spacing toward its default; keep deliberate tracking to short display or labels. |

## Slop guard tells

This list preserves the guard's distinct self-checks without restating shared remedies. Follow the named checks above for the full fix when the symptoms overlap.

| Tell | Self-check | Fix |
|---|---|---|
| 1. Gradients everywhere | Count focal gradients and inspect `background-clip: text` or a gradient foreground brush. Would solids carry the screen? | Allow at most one focal gradient. Never gradient-fill type. Use solid controls, canvas, and text by default (`gradient-text`, `ai-color-palette`). |
| 2. Rainbow palette | Can you name each swatch's role in one sentence? Are categories only color-coded? | Start near 70/30/10; use spacing, labels, lines, or type for separation (`ai-color-palette`). |
| 3. Pulsing and redundant badges | Can **Active** ever be false here? Who verified it? Is the status repeated three times? | Delete always-true/unsupported badges, surface the meaningful exception, and remove routine pulse (`pulsing-dot`, `repeated-container-text`). |
| 4. Fingernail cards | Inspect one-sided borders over 1px, logical borders, inset effects, or one-sided XAML `BorderThickness`. Does the stripe label a real state? | Replace with tone, label, icon, or full fine edge. Do not put side stripes on rounded boxes (`side-tab`, `border-accent-on-rounded`). |
| 5. Emoji and glyph icons | Would removing the emoji change meaning? Does a check, bolt, or arrow glyph look like an accidental second icon set? | Remove decoration; use drawn icons at consistent size/weight. Preserve emoji that are actual content or explicit identity. |
| 6. Misalignment | Do time labels, dots, illustrations, ASCII art, and icons share an optical edge or baseline? | Give icons stable square bounds and align individually against the reading axis. |
| 7. Lazy fonts and slash gimmicks | Did the brief earn the default family, italic hero, mono, and each `//`? | Choose faces for this subject; keep real code markers in code and keep platform faces for native chrome (`overused-font`, `italic-serif-display`). |
| 8. Prompt-leaked text | Does build tooling, editor choice, internal consolidation, or prompt wording affect a user decision? | Delete it or replace with a specific benefit the product can prove. Keep development rationale out of all shipped artifacts. |
| 9. Glass and cloned brutalism | Does the design work with no glass? Is that hard offset shadow part of an entire intentional system? | Reserve translucency for real layers; vary material, type and structure when neobrutalism is expressly intended (`glassmorphism`, `hard-offset-shadow`). |
| 10. Hype and taglines | Try removing the gray subtitle, welcome banner, or words like elevate, seamless, supercharge, unleash, empower, revolutionize, streamline, next-generation, world-class, enterprise-grade, and cutting-edge. Count short contrast slogans. | Replace empty words with a concrete verb and object; omit redundant subtitles and greetings; keep at most one earned contrast (`marketing-buzzword`, `aphoristic-cadence`, `theater-slop-phrase`). |
| 11. Middle-dot separators | Search for U+00B7, `&middot;`, `&#183;`, and bullet look-alikes such as `•`, `∙`, and `⋅`. Is each genuine language or supplied content? | Use layout gaps, separators, or breadcrumb chevrons; use commas and conjunctions in prose, including Korean. Keep Catalan `l·l`, brand, or user content intact. |
| 12. Card overuse and icon tiles | Remove a container mentally. Does the group still read? Is a nested card or boxed icon doing nothing? | Flatten; keep cards for independent, interactive, repeatable objects (`nested-cards`, `identical-card-grids`, `icon-tile-stack`). |
| 13. Colored glows and radial halos | Look for zero-offset colored shadows and radial gradients fading to transparent behind content. Is there an actual material/light source? | Use a neutral offset shadow or tone shift for depth; reject the background aura (`radial-halo`, `radial-spotlight-glow`, `dark-glow`). |
| 14. Ghost cards | Do repeated cards define the same edge with both hairline and wide shadow? | Keep one. A floating menu or dialog can justify both (`gpt-thin-border-wide-shadow`). |
| 15. Eyebrows and numbers | Is the element above the heading a tiny tracked label or badge? Do numbers communicate an order? | Delete/merge kickers, keep actual breadcrumbs, and number only true sequences (`kicker-above-heading`, `hero-eyebrow-chip`, `numbered-section-labels`). |
| 16. Decorative backgrounds | Check repeating gradients, fixed-size gradient grids, and habitual cream. Does the background sit on a real measuring surface or come from the subject? | Use a solid palette ground or a real material; keep functional grids only (`codex-grid-background`, `repeating-stripes-gradient`, `cream-palette`). |
| 17. Fake liveliness | Look for overshooting easing values, elastic or bounce, looping translation, fake caret blink, or repeated entrances. Does anything real change? | Use still content or one authored sequence, real input carets, and a bounded, quiet response for actual state (`bounce-easing`, `marquee`, `blinking-cursor`, `content-hidden-at-rest`). |
| 18. Decorative dashboard chrome | For every stat, sparkline or ring, what would the user do differently? Are source, comparison, and time frame known? | Cut chrome that carries no decision. Draw real data at readable size and label examples as synthetic (`hero-metric-layout`). |
| 19. Shape-assembled illustrations | Does a large SVG, doodle, or `feTurbulence` scene stand in for a missing subject asset? | Use real art or a visibly marked slot only if the user must supply the asset; keep SVG for icons, logos, charts, and intentional vector geometry (`shape-assembled-illustration`, `sketchy-svg`, `organic-clip-path`). |

## Review mode

For each verified finding give the named rule, surface and location, why it matters, and a concrete fix. Classify as **breaks function**, **hurts trust**, or **taste**. Keep taste as advice, and do not confuse it with a [P0–P3](critique-rubric.md#rank-and-report) user-impact rating. Inspect both individual signals and the overall default: even a pattern-free design can be interchangeable. Compare the catalog's purple/glass/neon, warm cream editorial, and boxed neobrutalist examples to see how the costume changes while the underlying habits repeat.
