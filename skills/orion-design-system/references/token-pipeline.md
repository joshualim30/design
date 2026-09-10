# The token pipeline

How a colour someone picks in Figma becomes a constant in four apps — and the
two ways that has gone wrong in production.

Assumes the shared rules in [../SKILL.md](../SKILL.md) are loaded.

## Source of truth

`github.com/Orion-Sleep/design`, branch `main`, single file **`semantic-tokens`**
(JSON, no extension). Two tiers:

```
primitives.spacing.{xx-small … xxx-large}.value      = "16px"
primitives.radius.{small … xx-large}.value           = "12px"
semantic_tokens.{light,dark}.color.<group>.<element>.<property>.<state>.value
semantic_tokens.{light,dark}.shadow.<group>.…{drop|inner}.{x,y,blur}.value
semantic_tokens.{light,dark}.blur.<group>.….value
```

Only two colour literal forms are valid: `#rrggbb` (exactly six digits) and
`rgba(r, g, b, a.aaaa)` with 0–255 channels and four-decimal alpha. The
validator rejects anything else, including `#rgb` shorthand and 8-digit hex.

**No typography, motion, or z-index tokens.** Type is hand-maintained in each
app.

## iOS: two commands that do different jobs

| Command | Network | What it does |
|---|---|---|
| `make all` | **No** | Regenerates all 8 generated files from the *vendored* `scripts/design-tokens.json`. Hermetic, byte-identical on every machine. Safe to run any time. |
| `make tokens-update` | **Yes** | The only networked target. Resolves `design@main`, fetches, validates, atomically rewrites `design-tokens.json`, runs `make all`, writes provenance to `design-tokens.source.json`. Snapshots everything first and rolls back on any failure. |

Vendoring was deliberate. From `scripts/token_fetch.py`:

> *"when the generators downloaded from a moving branch pointer, a push to the
> design repo instantly reddened every unrelated PR."*

Per-token targets exist too — `make color spacing radius shadow blur icons
strings` — but `make all` is what CI checks.

`make setup` is a mandatory one-time local step: it registers the `xcstrings`
merge driver and points `core.hooksPath` at `scripts/git-hooks`.

## RN: one command, total overwrite

```bash
npm run sync:tokens        # node scripts/sync-tokens.js
```

Fetches `raw.githubusercontent.com/Orion-Sleep/design/main/semantic-tokens`,
strips `{value}` wrappers, reorders shadow keys, converts px→number for
spacing/radius/blur (**not** shadow), merges `primitives` into both themes, and
writes `unistyles.ts` — **full overwrite, no diff, no backup, no confirmation.**

There is no vendored payload on the RN side, so this always hits the network and
always takes whatever `main` says right now.

After a sync that touches accent or menu colours, re-run prebuild —
`withSystemAccentColor` and `withMenuBackgroundColor` read `unistyles.ts` at
prebuild time.

## Automation

`design-token-sync.yml` (orion-ios) runs on every push to `develop-working`. It
runs `make tokens-update`, **re-runs `make all` and refuses to push if that is
not a no-op**, then commits `chore(design): pull design tokens at <sha>` and
rebase-retries onto `develop-working`.

`validate-generated-files.yml` (name: `make`) runs on every PR: `make strings`
must be a no-op, `make all` must be a no-op, and no imageset may opt into lossy
compression. If it fails on your PR, run the command locally and commit the
result.

## Two failures that have already happened

### 1. `make tokens-update` in orion-sleep-test-ios wiped app-specific tokens

sleep-test hand-added tokens to its **vendored payload** rather than upstreaming
them here. A re-fetch replaced the payload wholesale. From commit `5a77c81`:

> *"it dropped every app-specific token and regenerated without them. Token
> count went 439 → 438, `fillsBackgroundFlow` went from defined to absent
> [while 10+ files still referenced it], and `buttons/primary/background/main`
> was repainted from the warm `#251b0a` to a blue. The provenance ref did not
> even change — only `fetched` — which is the tell."*

**Do not run `make tokens-update` in `orion-sleep-test-ios`.** Its workflow is
`workflow_dispatch:`-only for this reason. The precondition for re-enabling it
is written in that workflow's header: the app-specific tokens have to be
upstreamed into this repo first, and `make tokens-update` on a clean tree has to
produce no deletions.

Note what this teaches about the guard: the workflow's "regenerate twice and
compare" check **cannot** catch this class of bug. Regeneration was perfectly
consistent — with the wrong payload.

### 2. sales-studio never got vendoring

`orion-sales-studio-ios` has no `scripts/design-tokens.json`. Its generators
still fetch from the network at generate time
(`scripts/generate_colors.py`), which is the exact setup the other repos
migrated away from. Its `make` has only `color spacing radius shadow blur all
help` — no `strings`, `icons`, `setup`, or `tokens-update`.

## Adding or changing a token

1. Edit `semantic-tokens` in this repo. Both light and dark must define the same
   key set — the validator enforces it.
2. Merge to `main`.
3. iOS picks it up automatically on the next push to `develop-working`, or run
   `make tokens-update` locally (**not** in sleep-test).
4. RN: `npm run sync:tokens`, commit `unistyles.ts`.
5. If it is an app-specific token, it still belongs here — that is the lesson of
   `5a77c81`. Namespace it rather than keeping it local.
