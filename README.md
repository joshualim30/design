# design

Orion Design System — the source of truth for both the design tokens and the
mobile engineering conventions.

```
semantic-tokens          the token payload every app generates from
skills/                  Claude skills, vendored into the four mobile apps
scripts/
  check_design.py        design-system linter (Swift + RN)
  check_skills_sync.py   verifies a vendored copy has not been hand-edited
  vendor_skills.py       copies skills + scripts into an app repo
```

## Tokens

`semantic-tokens` is a JSON payload in two tiers — `primitives` (spacing,
radius) and `semantic_tokens.{light,dark}` (colour, shadow, blur). There are no
typography, motion or z-index tokens; type is hand-maintained per app.

Consumers:

| App | How it pulls |
|---|---|
| orion-ios | `make tokens-update` (networked) writes the vendored `scripts/design-tokens.json`; `make all` regenerates offline from it. A bot syncs on pushes to `develop-working`. |
| orion-sleep-test-ios | Same, but `make tokens-update` is **disabled** — its payload carries app-specific tokens that a re-fetch wipes. Upstream them here first. |
| orion-sales-studio-ios | Generators still fetch this file over the network at generate time. |
| orion-react-native | `npm run sync:tokens` fetches this file and overwrites `unistyles.ts` wholesale. |

Both light and dark must define the same key set, colours must be `#rrggbb` or
4-component `rgba()`, and lengths must be `"NNpx"` strings — the iOS validator
rejects anything else before it generates.

## Skills

Six Claude skills carrying the mobile design and development conventions.
They are authored here and **vendored** into each app repo under
`.claude/skills/`, so they travel with a clone — and with a fork.

| Skill | Goes to |
|---|---|
| `orion-design-system` | all four apps |
| `orion-mobile-figma` | all four apps |
| `orion-handoff` | all four apps |
| `orion-onboard` | all four apps |
| `orion-ios-dev` | the three Swift apps |
| `orion-rn-dev` | orion-react-native |

### Changing a skill

Edit it here, then re-vendor and commit in each app repo:

```bash
python3 scripts/vendor_skills.py --all --root ..
```

Each app's CI runs `check_skills_sync.py`, which fails if a vendored copy was
edited in place. That check compares against hashes recorded at vendor time,
not against this repo — so pushing here never reddens an app's open PRs.
Picking up newer skills is always a deliberate re-vendor.

### Adding a skill

Create `skills/<name>/SKILL.md` with `name` and `description` frontmatter, add
it to `MANIFEST` in `vendor_skills.py`, re-vendor. Keep `SKILL.md` under ~500
lines and push depth into `references/` — the description is what decides
whether the skill fires at all, so spell out when to use it.

Descriptions must be under 1024 characters, must not contain angle brackets,
and must be quoted if they contain a colon.

`orion-onboard` carries `disable-model-invocation: true` and `argument-hint`,
which are Claude Code harness fields. skill-creator's `quick_validate.py` will
flag them as unexpected keys — that validator targets the Skills API upload
path, and these skills are loaded from disk by Claude Code. The fields are
correct here; don't remove them to quiet the validator.

## The linter

```bash
python3 scripts/check_design.py --platform swift          # from an app repo
python3 scripts/check_design.py --platform rn --budget scripts/design-budget.json
```

It is a **ratchet**: each app repo holds a `scripts/design-budget.json` of
current counts, and CI fails only when a count rises. Existing violations do
not block work; new ones do. Re-lock a reduced budget with `--update` — the
script refuses to raise one.
