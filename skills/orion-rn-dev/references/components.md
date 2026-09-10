# RN component index

Assumes [../SKILL.md](../SKILL.md) is loaded.

`DESIGN.md` in the RN repo holds the detailed prop tables and stays the place
to look them up. **This file is the map into it, with the corrections the docs
have not caught up with.** Read the section of `DESIGN.md` named here rather
than trusting a section number quoted elsewhere — two cross-references in
`AGENTS.md` and `CLAUDE.md` point at the wrong sections.

## Where to look in DESIGN.md

| You need | DESIGN.md § |
|---|---|
| Token scales, surface/button/input/temperature colour tables | §3 Theme anatomy & scales |
| Font families and which block first paint | §4 Fonts |
| Typography variants, `TemperatureForeground` buckets | §5 Typography components |
| Styling idioms | §6 Styling idioms |
| All six button variants + `IconButton` sizes | §7 Buttons |
| `TextInput`, `OTPInput`, `PhoneNumberInput`, `DateInput`, `RadioButton`, `Slider`, `Switch`, `Calendar` | §8 Inputs & form controls |
| `SelectableCard`, the feature-card folder pattern, the card surface recipe | §9 Cards |
| Badge, `CircularProgress`, `Avatar`, `AvatarStack` | §10 Badges, progress, avatars |
| `NavigationBar`, `Header`, `SectionHeader`, `SegmentedControl`, `DropdownMenu`, `ActionsMenu`, `AnimatedTabBar`, `ContentLoader`, `KeyboardAvoidingContainer` | §11 Layout chrome |
| **The canonical form-screen skeleton** | §12 Safe-area views & screen scaffolds |
| Sheet architecture, store API, canonical anatomy, close choreography | §13 Bottom sheets |
| Modal architecture, "sheet or modal?" decision rule | §14 Modals |
| Toast helpers | §16 Toasts |
| Loading and empty states | §17 |
| Motion, and the four Reanimated-4 crash-avoidance rules | §18 |
| Haptics mapping | §19 |
| **The icon template** | §20 Icons & assets |
| Decision quick-map + new-UI checklist | §22 |

Note §12 is the screen scaffold (older docs say §8) and §20 is the icon
template (older docs say §10).

## Where things live

```
components/ui/
├── typography/  Heading Paragraph Label Mono Badge TemperatureForeground
├── buttons/     Primary Secondary Tertiary Destructive DestructiveUncontained IconButton
│                + buttonBorders, lottieColorUtils, shadowUtils, useButtonPressAnimation
├── inputs/      TextInput OTPInput PhoneNumberInput DateInput RadioButton
│                OthersRadioButton Slider Switch
├── cards/       SelectableCard OthersSelectableCard
├── views/       ThemedSafeAreaView ThemedSafeAreaScrollView
├── layout/      NavigationBar Header SectionHeader ActionsMenu AnimatedTabBar
│                BrightnessOverlay ContentLoader InitialAPI KeyboardAvoidingContainer
│                KeyboardLiftView NotificationDot DropdownMenu/ SegmentedControl/
├── sheets/      GlobalSheets + the sheet set
├── modals/      GlobalModals + the modal set
├── overlays/    ContextOverlay GlobalLoader
├── toast/       toast.tsx
├── calendar/ badges/ progress/
└── Avatar AvatarStack ErrorBoundary OrionWebView
```

**Read the directory for the inventory.** Every count in `DESIGN.md` and
`CLAUDE.md` has drifted — the sheet table says 23 where `GlobalSheets.tsx`
registers 27, the store count says 22 where there are 26, hooks say 24 where
there are 48.

## Undocumented in DESIGN.md

Things that exist and that you will otherwise reinvent:

- **`KeyboardLiftView`** and **`NotificationDot`** in `layout/` — no entry in
  §11.
- **The `light` (300) typography tier.** `AeonikLight`, `InterLight` and
  `InterMedium` are registered in `app/_layout.tsx` and present in
  `interfaces/ui/typography.ts`, but §5's variant tables list only
  `regular`/`bold`. `Heading` has 24 variants, not 16.
- **`Heading`'s `adjustsFontSizeToFit` and `minimumFontScale`** props.
- **The `color.insights_v3` token namespace** — a full cool/blue colourway.
  §3 documents `color.insights.*` and never mentions it.
- **`components/insights/palette.ts`** — `InsightsRamp`, `InsightsForeground`,
  `InsightsSurface`, `InsightsOverlay`, `InsightsHorizon`, `CloudGradient`,
  `stageColor()`, `biometricColor()`, `withAlpha()`. 66 files import from here
  instead of `theme.*`, deliberately.
- **Styling idioms C and D** — see the design-system RN reference §4.
- **The raw-`Text` exception** for nested inline rich text.
- **`ExitScheduleSetupSheet.tsx`** — §13 calls it `ScheduleSetupExitSheet`.
- **`Label` uses `InterRegular`**, not "Inter" as §5 says.

## Name collisions

- `components/ui/typography/Badge` (a text variant) vs
  `components/ui/badges/Badge` (a pill). Import by path and check which one you
  want.
- `app/(tabs)/insights/` and `app/(tabs)/insights-new/` are near-identical
  373-line siblings. Confirm which is live before editing.

## Adding a sheet or a modal

Sheets and modals are **store-driven, not routes**. Add the type to the store,
register the component in `GlobalSheets.tsx` / `GlobalModals.tsx`, and open it
through the store. DESIGN.md §13 has the "adding a sheet" recipe and the
canonical anatomy block; §14 has the decision rule for which of the two you
want.
