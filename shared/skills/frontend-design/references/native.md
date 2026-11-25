# Native platforms

Includes modified guidance from Impeccable and its [upstream platform design sources](SOURCES.md#apache-20-redistribution-notice).

Use the [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) on iOS/iPadOS and [Material Design 3](https://m3.material.io/) on Android. Native users know navigation, gestures, controls, and text scaling before opening your app. Keep those guarantees in every mode and theme the layer the platform leaves open. A Material-everywhere app on iPhone still owes iOS its safe areas, back gesture, text scaling, and Reduce Motion. Preserve input through gestures, dismissals, and interruptions or warn before loss.

## iOS and iPadOS

- Use a system tab bar for two to five top-level sections, not actions. Use a navigation stack for hierarchy and do not disable or cover the leading-edge back gesture. Use collapsing large titles on suitable top-level screens; keep deep detail inline. Use grouped/inset lists for settings instead of decorative stacks.
- Keep controls in safe areas, clear of notches, Dynamic Island, home indicator and rounded corners. Make every target at least 44×44 pt and leave separation. Use Dynamic Type roles rather than fixed sizes. Body is 17 pt and 11 pt is a floor, not a body default. Keep San Francisco for controls and ordinary roles; spend a brand face on intentional display while respecting scaling, including large accessibility categories.
- Use semantic system colors (for example `label`, `secondaryLabel`, `systemBackground`, `separator`, tint) and native materials for real translucent layers. Test light, dark and increased contrast. Use one interactive tint; use SF Symbols with coherent baseline, weight, and scale rather than mixed web icons.
- Use native switches, pickers, segments, steppers, swipe actions, menus, and alerts. Use sheets for self-contained dismissible tasks, clear Cancel/Done, and full-screen cover only for immersion. Honor swipe dismissal unless protecting unsaved work. Establish sensible VoiceOver reading and restored focus.
- Let a push slide and a sheet rise/dismiss in the familiar directions. Honor Reduce Motion with crossfade or instant state in place of strong travel. Check touch posture and gestures on hardware.

## Android

- Use a Material navigation bar for three to five compact destinations; adapt to rail or drawer as width expands. Use top app bar for context, and at most one FAB for the actual primary action. Honor system Back and predictive Back. Keep edge-to-edge rendering with status, navigation, cutout, hinge and IME insets applied to content.
- Make hit areas at least 48×48 dp with at least 8 dp separation. Use the Material Display, Headline, Title, Body and Label roles with large/medium/small as needed. Use `sp` for scalable type; keep Roboto for routine system voice or theme a readable brand face through the roles.
- Use Material `surface`, `on-*`, `outline`, error and action roles with light/dark and contrast variants. Use tonal elevation and the standard shadow only where meaningful. Dynamic Color on Android 12+ is optional where it suits; provide a static scheme for other contexts. Do not mechanically invert themes.
- Use standard filled, tonal, outlined and text buttons, Material switch/chips, sheets and dialogs; do not port Cupertino widgets. Use snackbars for transient feedback and an available action, not an actionable toast. Interrupt only for true decisions. Use container transform, shared-axis, or fade-through inside Material's language, with instant change or crossfade when Remove animations is on. Check TalkBack names, roles, states and logical focus.

## Adapt, don't stretch

- Use iOS size classes and Android window size classes, not model checks. A tablet multitasking window can be phone width. Restructure into list/detail, multiple columns, or sidebar/rail; replace a sheet with a popover where context permits. Keep one coherent information architecture.
- Test both orientations, Split View and Android multi-window when supported. On foldables, handle folded, expanded and tabletop postures with hinge-aware placement. Lock rotation only when the experience truly requires it, never to dodge a defect.
- Port from the web by translating navigation, gestures, input, units and components, not by wrapping a responsive website. Between platforms preserve brand intent but translate a switch, action sheet, tab, back gesture, type or transition into its native counterpart. Use share, camera, clipboard, and other device surfaces through platform affordances and explain needed permissions.

## Verify on the actual platform

Capture from a simulator, emulator or device, never browser emulation of native chrome. Use at least a phone and each other shipped device class. Test both appearances, enlarged Dynamic Type, Android font-scale stress such as 1.3 and larger where supported, large accessibility sizes, screen readers, system media and reduced-motion settings, keyboard/IME, back gestures, low power and interruptions. Restore settings changed for review. Emulators provide breadth; real hardware establishes touch posture, refresh-rate behavior, 60/120 Hz performance, and OS edge interactions. Report which produced the evidence. Use [audit](audit.md) for technical scoring; markup detectors have no verdict on native implementations.
