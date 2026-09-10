---
name: orion-handoff
description: "Use this skill when work in an Orion mobile repo needs to outlive the session — finishing a substantial piece of work, running an audit or fidelity pass, pausing mid-task, handing to another person or agent, or coordinating several agents working in parallel on one app. Load it when asked to write a handoff, a status doc, or a summary of where things stand; when asked where did we leave off or to pick up someone else's work; or when you have produced findings with file paths and line numbers that would otherwise exist only in this conversation. It carries the artifact contract distilled from STATUS.md and the twelve W-HANDOFF files, and the file-ownership protocol for parallel work."
---

# Handoff and status in Orion mobile

The failure mode this exists to prevent is written down in
`orion-sleep-test-ios/STATUS.md`:

> *"[Three completed audits] are in the previous session's transcript with
> `file:line`, node ids and exact fixes. **They were not written to files.**"*

Three finished audits, unrecoverable. Findings that live only in a transcript
did not happen.

**If you produced findings with file paths, write them to a file before you
finish.** Not a summary in chat — a file in the repo.

## Which artifact

| Situation | Artifact |
|---|---|
| Where the whole app stands right now | `STATUS.md` at repo root — one per repo, overwritten |
| One workstream is done and someone else picks up | `<STREAM>-HANDOFF.md` at repo root |
| An audit or fidelity pass produced findings | A findings file, or rows in STATUS.md if short |

`orion-sleep-test-ios` has twelve `W*-HANDOFF.md` files from a parallel port and
one `STATUS.md` rolling them up. That is the shape.

## The handoff contract

Every one of the twelve carries these, and each exists because it was missed
once:

**1. Header — verifiable, not narrative.** Branch, what it branched from, file
and line counts, and a status line someone can re-run:

> `swiftlint --strict` clean (0 violations / 126 files), `swiftformat --lint`
> clean (0/126). `xcodebuild -scheme "Orion Sleep Test Debug" …` → **BUILD
> SUCCEEDED**, with zero warnings originating in W15 files.

Name the command. "Builds fine" is not a status.

**2. Reference-tree declaration.** Where you ported *from*, and that it was
read-only:

> Reference tree: `/Users/joshualim/Orion/orion-ios` (read-only; ported from
> the main tree only, never from its `.claude/worktrees/**`).

This line is in three of the handoffs verbatim because agents kept porting
from stale worktree copies.

**3. What you did not touch.** `project.pbxproj` was NOT touched. No
`.swiftlint.yml` / `.swiftformat` exclude entries were added. Say it explicitly
— it is the first thing a reviewer checks.

**4. Read this first if you own another stream.** Cross-stream warnings, as
instructions rather than observations:

> **W3** (auth) — **Do NOT port `updateBiologicalData` or `enterDOB` into
> `NetworkingService+Auth.swift`.** … A second copy is a redeclaration error.

**5. File provenance.** A table of `Target | Origin | Lines`, split into
*verbatim* and *trimmed or adapted*. A reviewer needs to know which files to
read closely.

**6. The files you touched outside your own paths**, with the justification.

**7. Deliberately skipped / does not compile yet / gaps** — with the owning
stream named. One handoff's section is titled exactly "Does not compile yet".
Honest and useful beats tidy.

**8. Verification performed.** What you actually ran, and what you did not.

## STATUS.md

The rollup. Beyond the per-stream contract it adds:

- **START HERE** — the one thing the next session should do first.
- **The method that works** — hard-won process notes, e.g. *"Do not drive a
  simulator to find defects."*
- **Reference the next session should not re-derive** — the spacing scale, the
  type scale, resolved token values. Cheap to write, expensive to rediscover.
- **Traps already paid for** — bugs someone burned time on. This is the
  highest-value section in the file.
- **Per-screen or per-area status table.**
- **Blocked on you** — what needs a human decision.

Keep it current rather than appending. STATUS.md describes now; the handoffs
are the history.

## Parallel agents on one app

- **Exclusive paths.** Each stream owns a set of files. Declare them up front.
- **Shared files are append-only.** `Route`, `DependencyContainer`,
  `NetworkingServiceProtocol`, `GlobalSheets.tsx`, `purgeAllStorage` — several
  streams need these. Append a `// MARK:`-separated block at the end rather
  than inserting into the middle; two inserts in the same region conflict,
  two appends usually don't.
- **Reference trees are read-only.** Port from the main checkout, never from a
  `.claude/worktrees/**` copy.
- **Don't touch `project.pbxproj`.** Xcode groups are filesystem-synchronized;
  every concurrent edit to that file is a conflict for nothing.

## Before you finish

- [ ] Findings with `file:line` written to a file, not left in chat
- [ ] Status line names the command that produced it
- [ ] Reference tree declared, and it wasn't a worktree copy
- [ ] Known-broken listed, with an owner
- [ ] Cross-stream warnings written as instructions
- [ ] `STATUS.md` updated if the overall picture moved
