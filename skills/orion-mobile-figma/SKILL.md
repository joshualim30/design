---
name: orion-mobile-figma
description: "Use this skill whenever Figma and an Orion mobile app meet — implementing a design in orion-ios, orion-sleep-test-ios, orion-sales-studio-ios or orion-react-native, checking an existing screen against the design, chasing a fidelity gap, or pushing code back into Figma. Load it when the user shares a figma.com link or a node id like 13218:5128, says match the design, design parity, pixel perfect, fidelity pass or looks wrong versus Figma, or asks to build a screen the designer has already drawn. It carries the two board URLs, the node-annotation convention roughly 500 places in the codebase already follow, and the comparison method that works here — which is reading the node tree against the source, not hunting in a simulator."
---

# Figma and Orion mobile

## The boards

| Board | File key | Used by |
|---|---|---|
| **Mobile-Design** | `3dYKdGTekawT3NfQQmrcG8` | orion-ios, orion-react-native |
| **Sleep-Test-App** | `x8XzQaqafc5hMUa2Dfe1HI` | orion-sleep-test-ios |

```
https://www.figma.com/design/3dYKdGTekawT3NfQQmrcG8/Mobile-Design?node-id=261-15074
https://www.figma.com/design/x8XzQaqafc5hMUa2Dfe1HI/Sleep-Test-App?node-id=16-11697
```

Neither URL is recorded in any repo, which is why this skill exists. Note the
URL uses `261-15074` while code comments use `261:15074` — same node.

## Annotate the node id in the code

Around 500 places already do this — 285 in orion-ios, 167 in sleep-test, 43 in
RN. It is the fastest way for the next reader to check the implementation
against the design, and it is how a fidelity pass finds its way back.

The convention is **node id plus what it specifies** — not a bare id:

```swift
// Figma 13218:5128 fills the sleep-window pill with insights_v3/background/light.
/// Figma 13858:109112 — every hero variant is the same fixed height so swapping
/// states doesn't reflow the card.
/// Figma `16:11697` → `Frame 1686557658`, 48×48. Not on the spacing scale.
```

```ts
// sleep-session editor (Figma 12716:7030) — a V3-styled sibling of the V1
```

Name the **token**, not the hex, when the note is about colour — the token is
what the code should use and what survives a theme change.

Where the design and the implementation deliberately differ, say so in the
annotation. That is what makes the difference reviewable instead of looking
like a bug:

```swift
/// GAP (tokens): `fillsForegroundDescription` is #798695 in dark, a blue-grey
/// that reads cold against this warm photograph. Hardcoded until a token lands.
```

## Pulling a design into code

Load the `figma-design-to-code` skill and call `get_design_context` — this
skill does not replace them, it tells you what to do with what they return.

1. **Get the node, not a screenshot.** `get_metadata` returns sparse metadata
   only; `get_design_context` is what gives you the tree.
2. **Translate to tokens, not to values.** The tool returns React + Tailwind
   with literal hex and px. That output is a *structural* reference. Every
   colour maps to an Orion token, every spacing to the scale, every corner to
   the radius scale. See the design-system skill for the mapping.
3. **Recognise the component, not the layer name.** A Figma frame called
   "Card / Large / Dark" is `ActionCard(type: .large)`, not a new view. Check
   the Design Library before building anything.
4. **A value off the token scale is a question.** Sometimes the design really
   does want 14pt. More often the designer nudged something. Ask, or annotate.
5. **Annotate the node id** as above.

Pair this with `figma-swiftui` for the Swift repos — it carries the
SwiftUI-specific translation guidance.

## Checking an existing screen against the design

**Do not drive a simulator to find defects.** From
`orion-sleep-test-ios/STATUS.md`, written after this went badly:

> *"Do not drive a simulator to find defects — it is slow and it stalled five
> agents. Read the Figma node tree and compare it to the source."*

The method that works:

1. Pull the node tree for the screen with `get_design_context`.
2. Open the implementing view.
3. Walk them together, property by property — spacing, radius, colour token,
   type style, weight.
4. Record each gap as `file:line`, the node id, and the exact fix.
5. **Write the findings to a file.** This is the failure mode STATUS.md names
   explicitly: three completed audits *"are in the previous session's
   transcript with `file:line`, node ids and exact fixes. They were not written
   to files."* An audit that lives only in a transcript is an audit nobody can
   act on. See the `orion-handoff` skill.

Running the app on a simulator to *see* a change you already reasoned about is
fine and often useful. Hunting for unknown defects by scrolling around is what
does not work.

## Pushing code into Figma

Less common here, but it happens — "add the sleep-test card to Figma",
"Settings UI polish + Figma component parity". Load `figma-use` first (it is a
mandatory prerequisite for `use_figma`), and `figma-swiftui`'s code-to-design
direction for the Swift repos.

Build from the design system's own components and variables where they exist,
rather than pushing flat rectangles.

## What NOT to do

- Cite a node id with no explanation of what it specifies.
- Copy hex values out of `get_design_context` into code.
- Copy the returned React/Tailwind structure literally — it is a reference for
  layout intent, not source.
- Build a component the Design Library already has.
- Hunt for fidelity defects in a simulator.
- Finish an audit without writing it to a file.
- Use the `Mobile-Design` board for sleep-test work, or vice versa.
