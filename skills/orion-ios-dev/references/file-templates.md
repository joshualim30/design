# View and ViewModel file skeleton

Assumes [../SKILL.md](../SKILL.md) is loaded.

The canonical templates live in `File Templates/_ViewFileTemplate.swift` and
`File Templates/_ViewModelFileTemplate.swift` in the repo. Read those; this
explains why they matter and what breaks if you ignore them.

## The View skeleton

```swift
import SwiftUI

struct FeatureView: View {
    // MARK: - Dependencies

    // MARK: - App State

    // MARK: - Dynamic Values

    // MARK: - State & Environment

    // MARK: - Properties

    // MARK: - Initialization
    init() {}

    // MARK: - Scene
    var body: some View {
        Text("Hello")
    }

    // MARK: - View Helpers

    // MARK: - Helpers
}

// MARK: - Preview
#Preview {
    FeatureView()
}
```

The order is load-bearing, not decorative. Every View in the codebase reads
top-to-bottom as: what it depends on → what state it holds → how it is built →
what it renders → private helpers. Someone opening an unfamiliar screen knows
where to look before they start reading.

Keep the `// MARK:` headers even when a section is empty. An empty
`// MARK: - App State` tells the reader this view holds none; a missing one
tells them nothing.

## SwiftFormat will not reorder this for you

`.swiftformat` in `orion-sleep-test-ios` carries:

```
--disable redundantType,organizeDeclarations
```

`organizeDeclarations` is disabled **specifically to protect this skeleton** —
left on, it regroups members by type and visibility and destroys the order.
Do not re-enable it, and do not "tidy" a file by moving members out of their
sections.

`orion-ios` and `orion-sales-studio-ios` have no SwiftFormat at all, so nothing
enforces the skeleton there. Follow it anyway — the three apps get ported
between each other constantly, and a file that doesn't match costs the porter
time.

## The ViewModel shape

```swift
@Observable
final class FeatureViewModel {
    // MARK: - Dependencies
    @ObservationIgnored @Dependency(\.networking) private var networking
    @ObservationIgnored @Dependency(\.persistence) private var persistence

    // MARK: - Properties
    private(set) var items: [Model] = []

    // MARK: - Helpers
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
}
```

Three things that are conventions, not accidents:

- **`@ObservationIgnored` on every `@Dependency` and `@Navigation`.** Without
  it the wrapper's storage participates in observation and you get re-render
  loops.
- **`private(set)`** on published state. Views read; the ViewModel writes.
- **Cache-then-fetch.** Read from `PersistenceService` first so the screen
  paints, then refresh from the network and write back.

Split large ViewModels by concern into `FeatureViewModel+API.swift`,
`FeatureViewModel+Analytics.swift` — the codebase already does this
(`SleepSchedulesViewModel+API.swift`, `ReferralViewModel+API.swift`).

## Adding the file

Drop it in the right `Features/<Feature>/` folder. Xcode groups are
filesystem-synchronized, so it joins the target automatically. **Do not touch
`project.pbxproj`.**

## Previews

57 of 76 Design Library files carry a `#Preview`. New Design Library components
should have one — it is how anyone reviews a component without launching the
app. Feature views don't need one unless the view is genuinely reusable or has
states that are hard to reach.
