# Design tokens in React Native

Applies to `orion-react-native` (Android app; iOS ships from the Swift repos).
Assumes the shared rules in [../SKILL.md](../SKILL.md) are loaded.

## Contents

1. Where tokens live
2. The substitution table — the single highest-value section
3. Literals that are correct
4. The four styling idioms
5. Which system does this folder use?
6. Typography
7. Colour and translucency
8. Icons
9. Strings
10. What NOT to do

---

## 1. Where tokens live

`unistyles.ts` at the repo root — ~2,480 generated lines, with a do-not-edit
banner the generator writes. `npm run sync:tokens` overwrites it whole,
including the `StyleSheet.configure` call, the breakpoints, and the module
augmentation. Nothing you add there survives.

Five top-level keys: `blur`, `color`, `shadow`, `spacing`, `radius`.
**No typography** — type lives in the components (§6).

Shadows are `{ y: '4px', blur: '12px' }` — **strings, deliberately**. The
generator converts px to numbers for spacing/radius/blur but leaves shadow
values as strings, which is why `components/ui/buttons/shadowUtils.ts` parses
them back out. Do not "fix" this.

## 2. The substitution table

~170 magic numbers in `app/` + `components/` have a token sitting right there.
This is the most common thing an agent gets wrong, because 16 is what you would
write in any other codebase.

| Literal | Use instead |
|---|---|
| `4` | `theme.spacing['xx-small']` |
| `8` | `theme.spacing['x-small']` |
| `12` | `theme.spacing.small` |
| `16` | `theme.spacing.medium` |
| `24` | `theme.spacing.large` |
| `32` | `theme.spacing['x-large']` |
| `48` | `theme.spacing['xx-large']` |
| `64` | `theme.spacing['xxx-large']` |

| `borderRadius` literal | Use instead |
|---|---|
| `12` | `theme.radius.small` |
| `16` | `theme.radius.medium` |
| `20` | `theme.radius.large` |
| `24` | `theme.radius['x-large']` |
| `32` | `theme.radius['xx-large']` |

Note the kebab keys need bracket access. `theme.spacing.xSmall` is not a thing.

The commonest failure is *mixed mode* — tokens and magic numbers in one style
object, which reads as deliberate and isn't:

```ts
// app/(device-onboarding)/side-orientation.tsx — real example
container: {
  gap: theme.spacing['x-small'],   // ✓
  marginTop: 24,                   // ✗ theme.spacing.large
  paddingVertical: 24,             // ✗
  paddingHorizontal: 8,            // ✗ theme.spacing['x-small']
}
```

## 3. Literals that are correct

Not every number is a violation. These are house conventions, not drift:

- `0` — always fine.
- `borderRadius: 100` — the pill. (`9999` and `999` appear too; `100` is the
  convention. Prefer it.)
- `borderWidth: 1.2` — the button border.
- Sheet top corners `32`.
- Control heights `56` / `48` / `44` / `40` — button and input sizes.
- Values genuinely off the scale (`14`, `18`, `40`, …) — check Figma first, and
  if the design really wants it, leave a comment saying so.

## 4. The four styling idioms

`DESIGN.md` documents two. Four are in use, and all four are legitimate.

**A — memoized (241 files).** The default for anything with variants or state.

```ts
const { theme, rt } = useUnistyles();
const styles = useMemo(() => StyleSheet.create({ … }), [theme, size]);
```

**B — module-scope callback (80 files).** For static styling with no
computed dependency.

```ts
const styles = StyleSheet.create(theme => ({ … }));
```

**C — plain objects, no `StyleSheet.create` (e.g. `ThemedSafeAreaView.tsx`).**
Reading `theme.*` inside the hook is what makes it reactive; `StyleSheet.create`
is not required for that.

```ts
const { theme } = useUnistyles();
const styles = useMemo(() => ({ container: { backgroundColor: theme.color… } }), [theme]);
```

**D — `UnistylesRuntime.getTheme('dark')` (10+ sites).** Reads a theme outside
the reactive system. Used for module-scope palettes (`components/insights/palette.ts`)
and screens that render dark-scoped under a light app theme. Deliberate; don't
"fix" it into a hook.

Sub-idiom: deep-destructuring in the hook call rather than at use sites
(`SelectableCard.tsx`). Fine.

**Always import `StyleSheet` from `react-native-unistyles`, not `react-native`.**
Auto-import gets this wrong; 24 files are currently wrong because of it. The one
legitimate RN `StyleSheet` use is `absoluteFill` / `absoluteFillObject`, which
Unistyles has no equivalent for — 8 files do this correctly.

Theme branching uses `rt.themeName` from `useUnistyles()`. **Never
`useColorScheme()` from react-native** — it bypasses the user's light/dark
override and any `ScopedTheme`. There is exactly one instance
(`components/dot-matrix/DotMatrix.tsx`) and it is a bug.

Scoped overrides: `withDarkScope` HOC, `<ScopedTheme name="dark">`, or the
`themeOverride` prop on typography components.

## 5. Which system does this folder use?

The repo has parallel styling systems. Editing a file without knowing which one
it belongs to produces something that passes lint and tsc and looks wrong.

| Folder | System |
|---|---|
| most of `app/`, `components/` | `theme.*` via Unistyles — the default |
| `components/insights/**` (66 files) | **`palette.ts`** — `InsightsSurface`, `InsightsRamp`, `InsightsForeground`, `stageColor()`, `biometricColor()`, `withAlpha()`, plus the `color.insights_v3` token namespace. Import from the palette, not `theme.color.fills.*`. |
| `components/onboarding_v2/**` | Own hex arrays and own `withAlpha`. Match the neighbours. |
| `components/debug/**` | Deliberately unstyled. Leave it. |

`insights_v3` is a whole token namespace that `DESIGN.md` never mentions. It
exists in `unistyles.ts` and is what the Insights v3 surfaces use.

## 6. Typography

Five components in `components/ui/typography/`: `Heading`, `Paragraph`, `Label`,
`Mono`, `Badge`, plus `TemperatureForeground`.

```tsx
<Heading variant="medium.regular">Sleep score</Heading>
<Paragraph variant="small.light">…</Paragraph>
```

Variants are `'<size>.<weight>'`, weight ∈ `light | regular | bold`. `Heading`
has 24 variants (8 sizes × 3 weights); the `light` (300) tier is real and
registered (`AeonikLight`, `InterLight`) even though older doc tables omit it.
The union types are in `interfaces/ui/typography.ts`.

All five take `themeOverride`, `style`, `numberOfLines`, `ellipsizeMode`.
`Heading` additionally takes `adjustsFontSizeToFit` and `minimumFontScale`.
Style array order is `[base, variant, colour, style]` — **a caller's `style`
always wins**.

`headingConfig`, `paragraphConfig` and `monoConfig` are exported and consumed by
the input components, so a scale change propagates into `TextInput`, `OTPInput`,
`DateInput`, `PhoneNumberInput`.

**Do not use raw `Text` from react-native** — with one exception: nested inline
rich text, where a link or a differently-coloured span sits inside a sentence.
React Native requires nested `Text` for that, and the typography components
can't express it. Five files do this correctly (e.g. `app/(auth)/enter-code.tsx`).
Outside that case, use the components.

## 7. Colour and translucency

Component-scoped semantic paths:

```ts
theme.color.fills.background.main
theme.color.buttons.primary.background.disabled
theme.color.inputs.text_input.border.active
theme.color.cards.default.background.elevated
```

`color.fills.*` is the closest thing to a global palette. Multi-word segments
are `snake_case` (`text_input`, `night_mode`, `main_transparent`).

**Translucent surfaces in dark contexts are tinted, never pure white.** The
house family is `rgba(219, 233, 253, …)`. `rgba(255,255,255,0.2)` on a
dark-capable surface is a violation even though it "looks fine" in isolation.

Do not write `theme.color.x?.y ?? '#10b981'`. The token exists; the fallback is
a different palette leaking in. Two files do this with a Tailwind green.

## 8. Icons

118 icon components in `icons/`, 111 following the template exactly. The
template: 24×24, `fill="none"`, `useUnistyles()` for colour, PascalCase name
with an `Outlined` / `Filled` suffix, default export. The seven exceptions are
signal-strength icons that take explicit fills.

Native drawables live in `assets/xml-icons/` and **require a prebuild** after
changes.

## 9. Strings

`i18next` with 18 namespaces under `locales/en/`. English only today, but the
indirection is load-bearing — 311 files use `useTranslation`.

```tsx
const { t } = useTranslation('settings');
<Paragraph variant="medium.regular">{t('profile.title')}</Paragraph>
```

Non-component code: `import i18n from '@/i18n'` then `i18n.t('key', { ns })`.

Three namespaces have filenames that differ from the namespace key:
`deviceOnboarding` → `device-onboarding.json`, `patchHome` → `patch-home.json`,
`onboardingV2` → `onboarding-v2.json`.

**Eight namespaces are eagerly loaded** (`common`, `auth`, `home`, `healthSync`,
`insights`, `onboardingV2`, `scheduleSetup`, `deviceOnboarding`) and each has a
comment in `i18n/index.ts` explaining why. The reasons are hard-won: a deferred
namespace on a first-paint surface shows **raw keys permanently**, not briefly,
because `bindI18nStore` is off. If you add a first-paint surface, its namespace
must be eager.

## 10. What NOT to do

- Editing `unistyles.ts`. It is regenerated wholesale.
- `import { StyleSheet } from 'react-native'` — except for `absoluteFill`.
- `useColorScheme()` from react-native.
- Magic numbers where §2 has a token; especially mixing them with tokens in one
  object.
- `rgba(255,255,255,…)` for a dark-surface translucent.
- Raw `Text` outside the inline-rich-text case.
- Hardcoded user-facing copy. Six exist; don't add a seventh.
- Trusting counts in `DESIGN.md` / `CLAUDE.md` / `AGENTS.md`. Every tally in
  them has drifted (22 stores → 26, 24 hooks → 48, 23 sheets → 27). Read the
  directory.
- Searching `.claude/worktrees/**`. Three full checkouts live there, so a naive
  grep returns four copies of every file.
