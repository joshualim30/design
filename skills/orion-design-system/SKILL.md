---
name: orion-design-system
description: "Use this skill whenever you write or edit UI in any Orion mobile app — orion-ios, orion-sleep-test-ios, orion-sales-studio-ios, or orion-react-native. It covers the design tokens (spacing, radius, colour, shadow, blur, typography), which files are generated and must never be hand-edited, and the exact call syntax for each platform, which is easy to guess wrong and wrong in the older docs. Load it for any request that adds a screen, card, sheet, button, list row, chart or icon; that adjusts padding, spacing, corner radius, colour, or font; that ports a screen between the apps; or that implements a Figma design. Also load it before running any token sync command. If you are about to type a number into a padding, spacing, frame or corner-radius argument, or a hex string into a colour, read this first."
---

# Orion design system

One design system, four apps, two platforms. Tokens are generated from this
repo (`Orion-Sleep/design`, file `semantic-tokens`) into each app.

**This file is a router.** It carries only what is true everywhere. Platform
detail lives in the references below — read the one for the repo you are in.

## Pick your reference

| You are in | Read |
|---|---|
| `orion-ios`, `orion-sleep-test-ios`, `orion-sales-studio-ios` | [references/swiftui.md](references/swiftui.md) |
| `orion-react-native` | [references/react-native.md](references/react-native.md) |
| Any token sync, or a generated file is out of date in CI | [references/token-pipeline.md](references/token-pipeline.md) |

Do not assume a reference's contents from its filename — read it.

Both platform references ship into every app on purpose: screens get ported
between these four repos constantly, and the other platform's reference is what
tells you what the thing you are porting was built out of.

## Rules that hold everywhere

**1. Never hand-edit a generated file.** The generator overwrites it and CI
fails the PR. On iOS that is anything named `*.generated.swift`. On RN it is
`unistyles.ts` — all 2,400+ lines of it.

Both carry a do-not-edit banner at the top, emitted by the generator itself —
if you are reading one and the banner is missing, the file predates that
change, not the rule.

To change a token, change it in this repo (`semantic-tokens`) and let the sync
bring it down. To change how a token is *rendered* into code, change the
generator in `scripts/`, never its output.

**2. Never type a raw number where a token exists.** Both platforms share one
scale, because both are generated from the same payload:

| | 4 | 8 | 12 | 16 | 24 | 32 | 48 | 64 |
|---|---|---|---|---|---|---|---|---|
| **spacing** | xx-small | x-small | small | medium | large | x-large | xx-large | xxx-large |

| | 12 | 16 | 20 | 24 | 32 |
|---|---|---|---|---|---|
| **radius** | small | medium | large | x-large | xx-large |

A value that is *not* on the scale is a signal, not a licence: check Figma
again, and if the design really does want an off-scale value, say so in a
comment rather than leaving a bare number.

**3. Never type a raw colour.** Colours are semantic and component-scoped —
`buttons.primary.background.main`, not `blue500`. There is a token for nearly
everything. If there genuinely isn't one, that is a gap in this repo: annotate
the hardcode so the next person can find it, using the form the codebase
already uses:

```swift
/// GAP (tokens): `fillsForegroundDescription` is #798695 in dark, a blue-grey
/// that reads cold against this warm photograph. Hardcoded until a token lands.
```

The annotation is what makes the linter allow it. An unannotated literal is a
violation; an annotated one is a tracked debt.

**4. Cite the Figma node.** Roughly 500 places in the mobile code already do
this, and it is the fastest way for the next reader to check your work against
the design:

```swift
// Figma 13218:5128 fills the sleep-window pill with insights_v3/background/light.
```

Node id *and* what it specifies. See the `orion-mobile-figma` skill for the
boards and the workflow.

**5. Reuse the Design Library before adding to it.** Every app has one
(`Design Library/Components/` on iOS, `components/ui/` on RN). Look there first.
If you add a component, it belongs in the library only if a second screen would
use it — otherwise keep it beside its feature.

## Checking your work

```bash
python3 scripts/check_design.py --platform swift   # or --platform rn
```

Run it before you hand back UI work. It reports violations as JSON with
`file:line`, and CI runs it against a budget — a count that may fall but never
rise. It exits 0 when the budget holds, 1 when it does not, and 2 on a usage
error, so a zero exit means "no new violations", not "no violations".

The linter is a floor, not a ceiling: it cannot tell you that you used
`cardsDefaultBackgroundMain` where the design wanted
`cardsDefaultBackgroundElevated`. Read the Figma node.

## What has no tokens

There are **no typography, motion, or z-index tokens** in the payload. Type is
hand-maintained Swift (`Typography.swift`) and hand-maintained TS (the
typography components). Motion values are conventions, documented per platform.
Do not go looking for `theme.typography` — it does not exist.
