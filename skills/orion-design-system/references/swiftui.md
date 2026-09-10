# Design tokens in SwiftUI

Applies to `orion-ios`, `orion-sleep-test-ios`, `orion-sales-studio-ios`.
Assumes the shared rules in [../SKILL.md](../SKILL.md) are loaded.

## Contents

1. The `.cornerRadius` trap — read this first
2. Spacing
3. Radius
4. Colour
5. Typography
6. Shadow, blur, icons, control size
7. Strings are tokens too
8. Per-repo differences
9. What NOT to do

---

## 1. The `.cornerRadius` trap — read this first

**`.cornerRadius(.large)` compiles, runs, and gives you 24pt when you meant 20pt.**

`Spacing.generated.swift` extends `CGFloat` with static members
(`.small`, `.medium`, `.large`, …). `Radius.generated.swift` **does not**. So
when you write SwiftUI's built-in `.cornerRadius(_ radius: CGFloat)` and pass
`.large`, Swift resolves it against the only `CGFloat.large` in scope — which is
`Spacing.large` = **24**. `Radius.large` is **20**. No warning, no error, wrong
pixels.

```swift
.cornerRadius(.large)                    // ✗ 24pt — Spacing.large, and deprecated API
.continuousCornerRadius(.large)          // ✓ 20pt — Radius.large, continuous curve
.customContinuousCornerRadius(18)        // ✓ escape hatch for a genuine off-scale value
```

`orion-ios/README.md`, `orion-sleep-test-ios/README.md` and `.cursorrules` have
all documented the broken form at some point. They are wrong. There is a live
instance at
`orion-ios/Orion/Features/Onboarding V2/Views/OnboardingFlowProvisionView.swift:775`
whose own doc comment says "the standard large radius" while rendering 24.

Rule: **never call `.cornerRadius(` in this codebase.** Always
`.continuousCornerRadius(_:)`, which also gives you the continuous (squircle)
curve the design uses, or `.customContinuousCornerRadius(_:)` for an annotated
off-scale value.

## 2. Spacing

Generated: `Design Library/Primitives/Spacing.generated.swift`.

```swift
enum Spacing: CGFloat { case xxSmall = 4, xSmall = 8, small = 12, medium = 16,
                             large = 24, xLarge = 32, xxLarge = 48, xxxLarge = 64 }
extension CGFloat { static let medium: CGFloat = Spacing.medium.rawValue /* … */ }
```

Because of that `CGFloat` extension, spacing is bare dot-syntax at call sites:

```swift
VStack(spacing: .medium) { … }
HStack(spacing: .xxSmall) { … }
.padding(.horizontal, .large)
.padding(.bottom, .small)
VStack(spacing: .zero) { … }             // .zero is SwiftUI's, and fine
```

Two forms you need the enum for:

```swift
.padding(.horizontal, -Spacing.medium.value)   // negatives — .value unwraps the raw CGFloat
.frame(height: Spacing.xxLarge.value)          // where the parameter isn't inferring CGFloat
```

There is one convenience modifier: `.horizontalPadding()` == `.padding(.horizontal, .medium)`.

**There is no `.orionSpacing(…)` modifier.** If you have seen that name, it was invented.

## 3. Radius

Generated: `Design Library/Primitives/Radius.generated.swift`.

```swift
enum Radius: CGFloat { case small = 12, medium = 16, large = 20,
                            xLarge = 24, xxLarge = 32, infinity = 9999 }
extension View {
    func continuousCornerRadius(_ radius: Radius) -> some View
    func customContinuousCornerRadius(_ value: CGFloat) -> some View
}
```

`infinity = 9999` is injected by the generator, not present in the token
payload — use it for pills and circles rather than a literal `9999`.

For a shape you are drawing rather than clipping, pass the token's value:

```swift
RoundedRectangle(cornerRadius: Radius.medium.value, style: .continuous)
```

`RoundedRectangle(cornerRadius: 12)` with a bare integer is the second most
common violation in the Swift repos. The radius scale is 12/16/20/24/32 —
values like 6, 8, 14 are off-scale and need either a token or a comment.

## 4. Colour

Generated: `Design Library/Semantic Tokens/Color.generated.swift` (~1,300 tokens
per app). Tokens are **flat camelCase statics on `Color`**, built from the
4-level token path `group.element.property.state`:

```swift
Color.buttonsPrimaryBackgroundMain          // buttons.primary.background.main
Color.cardsDefaultBackgroundElevated
Color.fillsForegroundMain
Color.inputsTextInputBorderActive
Color.settingsCellForegroundIcon
```

**There is no nesting** — `Color.text.primary` does not exist. If you are
guessing at a name, grep the generated file:

```bash
grep -o 'static let [a-zA-Z0-9]*' "Orion/Design Library/Semantic Tokens/Color.generated.swift" | sort
```

Group prefixes in use: `avatar buttons cards carousel context device dial fills
information inputs insights insightsV3 maintenance mattress night overlay
progress segmented settings skeleton sleep sliders smart temperature toast
toggle welcome widget`.

Property vocabulary: `background foreground border shadow overlay divider
gradientN`. State vocabulary: `main disabled active selected loading secondary
elevated error placeholder`.

Light and dark are resolved inside the token via `Color(light:dark:)`
(hand-written in `Utility/Color+Extensions.swift`, backed by
`UIColor(dynamicProvider:)`). **You do not branch on colour scheme yourself.**
Reading `@Environment(\.colorScheme)` to pick a colour is a bug — the token
already did it, and it resolves correctly in contexts where the environment
does not.

## 5. Typography

Hand-written: `Design Library/Semantic Tokens/Typography.swift`. **Not
generated** — there are no typography tokens in the payload.

Three orthogonal axes, applied with one modifier:

```swift
Text("Sleep score")
    .typography(.heading, size: .small, weight: .regular)
```

| Axis | Values |
|---|---|
| `TypographyStyle` | `paragraph` `heading` `mono` `label` `badge` (+ `headlineAccent` in sleep-test) |
| `TypographySize` | `xxxxLarge` `xxxLarge` `xxLarge` `xLarge` `large` `medium` `small` `xSmall` `xxSmall` |
| `TypographyWeight` | `light` `regular` `bold` |

Families are constants in `Typography.swift`: heading `Aeonik`, paragraph
`SF Pro Text`, mono `SF Pro Mono`, and in sleep-test `headlineAccent`
`Source Serif 4`.

For a view that takes a `Font` rather than accepting a modifier — `TextField`,
`UIViewRepresentable` — use the function, **and pass the environment's
dynamic type size**:

```swift
@Environment(\.dynamicTypeSize) private var dynamicTypeSize
…
typographyFont(style: .mono, size: .xLarge, weight: .regular,
               dynamicTypeSize: dynamicTypeSize)
```

The three-argument `typographyFont(style:size:weight:)` is `@available(*,
deprecated)`. It resolves through `UITraitCollection.current` and is blind to
any `.dynamicTypeSize(…)` ceiling set upstream. Do not call it.

Never `.font(.system(size:))`, `.font(.custom(…))`, or `.font(.body)`.

## 6. Shadow, blur, icons, control size

```swift
.shadow(.cardsDefaultDrop, color: .cardsDefaultShadowMain)   // location: .drop default, .inner available
.blur(.temperatureControlOverlay)                            // Blur values are halved from design px
Icon.chevronRight.image.iconSize(.small)                     // Icon.Size: xSmall 16 … xLarge 32
.circularControlSize()                                       // ControlSize.circular = 48
```

`Icon` is a generated `String` enum (165 cases) over the asset catalogue —
`Design Library/Components/Icon.generated.swift`. Adding an icon means adding
the asset and running `make icons`, not writing `Image("name")`.

## 7. Strings are tokens too

Same principle, different pipeline. User-facing copy is generated into
`Resources/Strings.generated.swift` from `Resources/Localizable.xcstrings`:

```swift
Text(Strings.Account.logoutConfirmationTitle)        // ✓
Text("Sign Out?")                                     // ✗
```

Add the key to the catalogue, run `make strings`, commit both files. Never edit
`Strings.generated.swift`. Parameterised strings are hand-written in
`Resources/StringsManual.swift`:

```swift
extension Strings.DeviceUserAccess {
    static func sleepingOnDevice(deviceName: String) -> String {
        String(localized: "DeviceUserAccess.sleepingOnDevice \(deviceName)", comment: "…")
    }
}
```

A bare `String(localized:)` in feature code is a smell — the generator is
supposed to write those.

## 8. Per-repo differences

The three Swift apps are forks and have drifted. Of 52 same-named Design
Library files shared between orion-ios and orion-sleep-test-ios, only 6 are
byte-identical. **Do not assume a component behaves the same across repos —
open the local one.**

| | orion-ios | orion-sleep-test-ios | orion-sales-studio-ios |
|---|---|---|---|
| Design Library components | 56 | 50 | 7 |
| `Typography.swift` | 5 styles | 6 (adds `headlineAccent`) | **none** |
| `Icon.generated.swift` | ✓ | ✓ | **none** |
| Localization | 1,797 keys | 708 keys | **none** |
| SwiftLint / SwiftFormat | none | both, CI-enforced | none |
| Vendored token payload | ✓ | ✓ (hand-extended) | **none — generators fetch over the network** |

`TypographyTriple` — `typealias (style:size:weight:)` for components that let a
caller override type — exists **only in sleep-test**. orion-ios spells the
tuple out.

**sales-studio is a different lineage.** No typography system, no strings, no
icons. Treat its 7-component library as its own thing; do not port orion-ios
patterns into it without checking they have a foundation to sit on.

## 9. What NOT to do

- `.cornerRadius(.large)` — see §1. Ever.
- `Color(red:green:blue:)` or a `#hex` string without a `/// GAP (tokens):` note.
- `.font(.system(size:))`, `.font(.custom(…))`, `.font(.body)`.
- `Color.red`, `Color.primary`, or any SwiftUI system colour. (There is one in
  `OrionLabel.swift` — it is a violation, not a precedent.)
- Editing any `*.generated.swift`.
- `@Environment(\.colorScheme)` to choose a colour.
- Searching or porting from `.claude/worktrees/**`. Every repo has one, they are
  full stale copies, and they will roughly 10× your grep results. Exclude them.
- Assuming widgets are exempt. `Widgets/LiveActivities/*` is largely untokenized
  today — that is drift to fix when you touch it, not a pattern to copy.
