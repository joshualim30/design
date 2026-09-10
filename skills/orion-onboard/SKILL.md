---
name: orion-onboard
description: "Orient someone — a new team member or a fresh agent session — in whichever Orion mobile repo they are standing in. Run it with /orion-onboard. It reports what the app is, how it is laid out, which conventions are enforced and which are only written down, what is currently stale or wrong in the repo's own docs, and what to read next."
disable-model-invocation: true
argument-hint: "[topic]"
---

# Orient in this repo

Run the commands below, read the results, then write the briefing. Do not
answer from memory — these repos have drifted from their own documentation and
the point of this skill is to report what is actually here.

If the user passed a topic (design, tokens, navigation, builds, strings,
testing…), keep the briefing to that topic and go deeper.

## Gather

```bash
basename "$PWD"
git branch --show-current
git log --oneline -8
ls
ls .claude/skills 2>/dev/null
```

Then, depending on which repo you are in:

```bash
# Swift repos
ls Orion*/Features 2>/dev/null || ls */Features 2>/dev/null
ls */Services 2>/dev/null
ls */"Design Library"/Components 2>/dev/null | head -20
grep -nE '^[a-z-]+:' Makefile
ls .github/workflows 2>/dev/null

# orion-react-native
ls app components/ui store network locales/en
node -e "console.log(Object.keys(require('./package.json').scripts).join('  '))"
ls .github/workflows 2>/dev/null
```

Check for stale copies, because they will affect everything the person greps:

```bash
ls -d .claude/worktrees/* 2>/dev/null | wc -l
```

## Brief

Cover these, grounded in what the commands returned:

**What this app is.** Orion Sleep System — a temperature-controlled mattress
topper (Smart Cover) and its base unit (Control Tower), with sleep schedules,
NFC patches and BLE onboarding. Then which of the apps this repo is:

| Repo | What it is |
|---|---|
| `orion-ios` | The flagship consumer iOS app. Fork parent for the others. |
| `orion-react-native` | The Android app. Expo/RN. iOS ships from the Swift repos. |
| `orion-sleep-test-ios` | The sleep-test product. Fork of orion-ios, heavy Figma-fidelity work. |
| `orion-sales-studio-ios` | Internal sales tool. Fork, but a thinner one — no typography system, no strings, no localization. |
| `orion-control-plane` | The Cloudflare Workers backend these all talk to. |

**Layout.** The directory tree you just listed, with what goes where.

**The skills in `.claude/skills/`** and when each fires. Point at
`orion-design-system` before anyone writes UI.

**What is enforced vs merely written.** Be specific and honest:

- Which CI workflows exist here, and what they gate.
- Whether this repo has a linter. `orion-sleep-test-ios` has SwiftLint +
  SwiftFormat; `orion-ios` and `orion-sales-studio-ios` have neither; RN has
  `eslint-config-expo` with no custom rules.
- **No repo has tests.** No test target on iOS, no jest in RN. Say so plainly —
  `orion-ios/README.md`'s Testing section describes a target that does not
  exist.

**Known-stale documentation**, so they don't trust it:

- `orion-ios`: `CLAUDE.md` is gitignored. `.cursorrules` names `OrionTextField`
  and `OrionCard`, which do not exist, and documents `.cornerRadius(.large)`,
  which silently renders 24pt instead of 20pt.
- `orion-react-native`: every count in `DESIGN.md` / `CLAUDE.md` / `AGENTS.md`
  has drifted. `hypnogram-chart-plan.md` is a React/Next.js spec sitting among
  RN porting guides.
- Any repo: `.claude/worktrees/**` holds full stale checkouts. Exclude them
  from every search.

**How to verify a change here.** Don't build — read the code and the editor
diagnostics. Run on a simulator or device that already has the app installed
when it is worth seeing. For design fidelity, read the Figma node tree against
the source rather than hunting in a simulator.

**What to read next**, in order, with paths — the skills first, then the
repo's own docs with the caveats above attached.

## Close

Offer the two things a newcomer most often wants next: a walk through one
feature end to end, or a first change with the conventions pointed out as they
come up.
