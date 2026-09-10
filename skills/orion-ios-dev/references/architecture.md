# Orion iOS architecture

Assumes [../SKILL.md](../SKILL.md) is loaded. Paths are `orion-ios`; the other
two apps mirror the shape with fewer parts.

## Contents

1. Directory layout
2. Dependency injection
3. The other property wrappers
4. Navigation
5. Services layer
6. Networking and persistence
7. Where things go

---

## 1. Directory layout

```
Orion/
├── Dependency/      DependencyContainer.swift, Dependency.swift
├── Design Library/  Animations/ Components/ Primitives/ "Semantic Tokens"/
├── Features/        one folder per feature, flat, sub-folders for sub-flows
├── Models/          domain models, flat
├── Resources/       Assets.xcassets, Fonts, Animations, Localizable.xcstrings,
│                    Strings.generated.swift, StringsManual.swift, Info.plist
├── Services/        one folder each: <Name>Service.swift + <Name>ServiceProtocol.swift
└── Utility/         extensions and helpers
```

Plus target folders outside `Orion/`: `Widgets/`,
`OneSignalNotificationServiceExtension/`.

Read the directory rather than a list in a doc — the service and feature sets
change, and every written inventory in these repos has drifted.

## 2. Dependency injection

Services are resolved through a keypath property wrapper backed by
`DependencyContainer`:

```swift
@ObservationIgnored @Dependency(\.networking) private var networking
@ObservationIgnored @Dependency(\.toast) private var toast
```

`@ObservationIgnored` is mandatory inside an `@Observable` type. Without it the
wrapper's storage is observed and you get re-render loops.

To see the available keys, read `Orion/Dependency/DependencyContainer.swift`.
Do not copy a list from a doc — `.cursorrules` is currently missing
`errorTracking`, `healthKit` and `widgetToken`.

Every service is protocol-paired (`NetworkingService` +
`NetworkingServiceProtocol`) so the container can hold a different
implementation. When you add a service, add both files and register the key.

**Registering a new key touches a shared file.** If several people or agents are
working in parallel, append your entry as its own `// MARK:`-separated block
rather than inserting into the middle — that is what the parallel-port
workstreams did to keep merges clean.

## 3. The other property wrappers

| Wrapper | Reads | Example |
|---|---|---|
| `@AppState(\.key)` | reactive app-wide state (`AppStateService`) | current device, session |
| `@DynamicValue(\.flag)` | LaunchDarkly flags (`DynamicValueService`) | feature gating |
| `@DefaultsState(\.key)` | `UserDefaults` (`DefaultsService`) | small persisted prefs |
| `@Navigation(.router)` | a navigation router | see below |

All four take `@ObservationIgnored` inside an `@Observable`.

## 4. Navigation

One unified `Route` enum for the whole app, with domain-prefixed cases, across
seven routers:

```swift
@ObservationIgnored @Navigation(.main) private var navigation
// routers: .main .auth .settings .patch .onboarding .deviceSettings .userInvite

navigation.navigate(to: .patchScanner)
navigation.navigate(to: .onboardingNetworkSelect)
navigation.navigate(to: .deviceSettingsNetwork)
```

Case names carry their domain as a prefix (`patch*`, `onboarding*`,
`deviceSettings*`, `auth*`) so the flat enum stays readable.

The stack is wired once:

```swift
NavigationStack(path: $navigation.path) {
    RootView()
        .orionNavigationDestination(patchViewModel: patchViewModel)
}
```

Adding a screen means: add the case to `Route`, add its branch to the
destination modifier, and navigate to it. The `Route` enum is another shared
file — append rather than insert when working in parallel.

## 5. Services layer

Each service is a folder under `Services/` holding `<Name>Service.swift` and
`<Name>ServiceProtocol.swift`. `ls Orion/Services` is the inventory.

Broad shape of what exists: networking (REST + WebSocket with token refresh),
persistence (SwiftData, cache-then-fetch), defaults, app state, navigation,
analytics and session replay, push notifications, error tracking, haptics,
toasts, deep links, Intercom, HealthKit, device info, feature flags, NFC for
patches, BLE/Wi-Fi accessory setup, and several widget/live-activity services.

Conventions that hold across all of them:

- **Errors surface through `toast.showError(error)`** rather than being
  swallowed or printed.
- **Analytics is explicit** — track through `AnalyticsService`, don't
  instrument ad hoc.
- **Haptics come from the service**: `haptics.success()`, `.impact(.medium)`,
  `.tickerChange()`. Every new interactive element gets one.

## 6. Networking and persistence

The canonical read is cache-then-fetch:

```swift
func fetch() {
    Task {
        if let cached = await persistence.fetch(Response.self, forKey: .key) {
            items = cached.items.map(Model.init(from:))
        }
        let response = try await networking.fetchData()
        items = response.items.map(Model.init(from:))
        try? await persistence.save(response, forKey: .key)
    }
}
```

The screen paints from cache, then refreshes. Skipping the cache read is the
difference between an instant screen and a spinner.

WebSocket work goes through `networking.openLiveDeviceStream()` and **must be
cancelled in `.onDisappear`**. A leaked stream keeps the device awake.

API response models are `<Name>Response.swift` under
`Services/NetworkingService/Models/`, and are mapped into domain models in
`Models/` rather than used directly in views.

## 7. Where things go

| Thing | Location | Naming |
|---|---|---|
| Screen | `Features/<Feature>/` | `FeatureNameView.swift` |
| Its view model | same folder | `FeatureNameViewModel.swift` |
| A large view model's API half | same folder | `FeatureNameViewModel+API.swift` |
| Reusable UI | `Design Library/Components/` | descriptive, `Orion` prefix where it is an Orion-specific take on a standard control |
| Domain model | `Models/` | `ModelName.swift` |
| API response | `Services/NetworkingService/Models/` | `ModelNameResponse.swift` |
| Service | `Services/<Name>Service/` | `NameService.swift` + `NameServiceProtocol.swift` |
| Extension / helper | `Utility/` | `Type+Purpose.swift` |

A component belongs in the Design Library only if a second screen would use it.
Otherwise keep it next to its feature — the library is already 56 files in
orion-ios and every entry is something the other apps may have to port.
