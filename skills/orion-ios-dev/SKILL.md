---
name: orion-ios-dev
description: "Use this skill for any code work in the Orion Swift apps — orion-ios, orion-sleep-test-ios, orion-sales-studio-ios. It covers the MVVM + @Observable architecture, the @Dependency / @Navigation / @AppState property wrappers, the unified Route enum, the services layer, the Makefile targets, the localized-strings workflow, and how to verify a change. Load it when adding or editing a View or ViewModel, wiring a service or an API call, adding a screen to navigation, adding user-facing copy, adding an icon or asset, or when a build or CI check fails. Also load it before searching the repo, because every one of these repos contains stale full copies under .claude/worktrees that will corrupt your results. Pair it with orion-design-system for anything that renders."
---

# Orion iOS development

Three Swift apps, same shape, different maturity. `orion-ios` is the flagship
and the fork parent.

Read [../orion-design-system/references/swiftui.md](../orion-design-system/references/swiftui.md)
for anything that renders. This skill is the architecture and the workflow.

| Topic | Reference |
|---|---|
| MVVM, DI, navigation, services in depth | [references/architecture.md](references/architecture.md) |
| The mandatory View/ViewModel file skeleton | [references/file-templates.md](references/file-templates.md) |

## Before you search

**Every repo contains `.claude/worktrees/**` — full stale checkouts.** A naive
grep returns ~10× the real hits and you will read, or worse port from, an old
copy. Exclude it every time:

```bash
grep -r "pattern" --include="*.swift" . | grep -v '/.claude/worktrees/'
```

`orion-ios-strings` is not a strings repo — it is a **second clone of
orion-ios** on a different branch. Don't cross-reference it.

## Verifying a change

**Do not build.** `xcodebuild` is slow and almost never what the situation
needs. Read the code and the editor diagnostics instead.

**Do run on a simulator that already has the app installed**, when the change is
worth seeing. Launch and drive the installed build rather than compiling a new
one; report what you observed. Build only when the change genuinely cannot be
reasoned about — a risky refactor — or when asked.

For design fidelity specifically, the method that works here is *not* hunting in
a simulator. From `orion-sleep-test-ios/STATUS.md`:

> *"Do not drive a simulator to find defects — it is slow and it stalled five
> agents. Read the Figma node tree and compare it to the source."*

**There are no tests.** No test target, no XCTest, no Swift Testing in any of
the three repos. `orion-ios/README.md`'s "Testing" section shows
`XCTAssertTrue` examples for a target that does not exist — ignore it. Never
claim test coverage in a PR description.

**Linting:** `orion-sleep-test-ios` has SwiftLint + SwiftFormat, enforced by its
`build.yml` (`swiftlint lint --strict`, `swiftformat --lint .`). `orion-ios` and
`orion-sales-studio-ios` have **neither**. So the same code passes in one repo
and is unchecked in another — write to the stricter bar.

Where a `swiftlint:disable` and a `swiftformat:disable` sit together, they are a
pair. Removing one without the other restarts a fight between the two tools.

## Architecture in one screen

MVVM with `@Observable`, protocol-paired services, property-wrapper DI.

```swift
@Observable
final class FeatureViewModel {
    @ObservationIgnored @Dependency(\.networking) private var networking
    @ObservationIgnored @Navigation(.main) private var navigation
    private(set) var items: [Model] = []
}

struct FeatureView: View {
    @State private var viewModel = FeatureViewModel()
    var body: some View { … .task { viewModel.fetch() } }
}
```

**`@ObservationIgnored` is required** on `@Dependency` and `@Navigation`.
Omitting it causes re-render loops.

Wrappers: `@Dependency(\.key)`, `@Navigation(.router)`, `@AppState(\.key)`,
`@DynamicValue(\.flag)`, `@DefaultsState(\.key)`.

**Do not memorise the dependency keys or the service list — they drift.** The
`.cursorrules` copy is already missing `errorTracking`, `healthKit` and
`widgetToken`. Read the source:

```bash
ls Orion/Services                              # the services
cat Orion/Dependency/DependencyContainer.swift # the keys
```

Navigation is one unified `Route` enum with domain-prefixed cases
(`patch*`, `onboarding*`, `deviceSettings*`) across routers `.main .auth
.settings .patch .onboarding .deviceSettings .userInvite`.

```swift
navigation.navigate(to: .patchScanner)
```

Feature code lives in `Orion/Features/<Feature>/`, flat, with sub-folders for
sub-flows. API extensions are split out as `<Name>ViewModel+API.swift`.

## Adding files

**Xcode groups are filesystem-synchronized** (`PBXFileSystemSynchronizedRootGroup`).
Dropping a `.swift` file into a folder adds it to the target. **Never edit
`project.pbxproj`** — every handoff doc in these repos says so explicitly.

New Views and ViewModels follow the templates in `File Templates/`, which define
a mandatory `// MARK:` skeleton. SwiftFormat's `organizeDeclarations` is
disabled specifically to protect that order — see
[references/file-templates.md](references/file-templates.md).

## Generated files and `make`

Never hand-edit anything named `*.generated.swift`. Regenerate:

| Need | Command |
|---|---|
| Everything (offline, hermetic) | `make all` |
| One kind | `make color` · `spacing` · `radius` · `shadow` · `blur` · `icons` · `strings` |
| Pull new tokens from the design repo | `make tokens-update` — **never in orion-sleep-test-ios** |
| One-time local setup (merge driver, git hooks) | `make setup` |

`make tokens-update` in sleep-test has already wiped app-specific tokens in
production. See
[../orion-design-system/references/token-pipeline.md](../orion-design-system/references/token-pipeline.md).

CI (`validate-generated-files.yml`, job name `make`) fails the PR if `make all`
or `make strings` is not a no-op. Run it locally and commit the result.

## User-facing copy

```swift
Text(Strings.Account.logoutConfirmationTitle)     // ✓
Text("Sign Out?")                                  // ✗
```

Add the key to `Orion/Resources/Localizable.xcstrings`, run `make strings`,
commit both the catalogue and `Strings.generated.swift`. Parameterised strings
go in `Resources/StringsManual.swift` by hand.

The catalogue has an `xcstrings` merge driver registered by `make setup`, and a
pre-commit hook re-runs `make strings` and **fails rather than auto-staging**.

`orion-sales-studio-ios` has no localization at all — no catalogue, no
generated strings, no `make strings`. Literals there are the status quo, not a
thing to "fix" without adding the pipeline first.

## Git

`feature → develop-working → develop → main`. Conventional Commits with scopes:
`feat(settings):`, `fix(widget):`, `chore(design):`. `develop-working` is where
the design-token bot pushes, so rebase before you push.

## What NOT to do

- Build to verify. Run on an existing sim instead.
- Edit `project.pbxproj`.
- Edit any `*.generated.swift` or `Strings.generated.swift`.
- Run `make tokens-update` in orion-sleep-test-ios.
- Search or port from `.claude/worktrees/**`.
- Omit `@ObservationIgnored` on `@Dependency` / `@Navigation`.
- Trust `README.md` on testing (fiction), on sleep-test being "foundation only"
  (it has ~50k lines), or `buildServer.json` (hardcodes another developer's
  paths).
- Claim tests pass. There are none.
