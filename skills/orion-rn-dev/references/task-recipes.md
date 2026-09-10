# RN task recipes

Assumes [../SKILL.md](../SKILL.md) is loaded. Section references point at
[../../orion-design-system/references/react-native.md](../../orion-design-system/references/react-native.md),
not at `DESIGN.md` — the older docs' cross-references are wrong.

## Add a screen / route

1. Pick the route group in `app/`, or create one: folder `(group)/` +
   `_layout.tsx` with `<Stack screenOptions={{ headerShown: false }}>`, then
   register the group in the root Stack in `app/_layout.tsx` with its
   animation/presentation.
2. Skeleton: `ThemedSafeAreaView` (or `ThemedSafeAreaScrollView`) →
   `NavigationBar` (back button `disabled={!router.canGoBack()}`) → `Header`,
   or `Heading` + `Paragraph` → content → CTA.
3. Navigate with `router.push('/(group)/screen' as any)` — the `as any` is the
   accepted pattern for computed routes. Params via `{ pathname, params }`,
   read with `useLocalSearchParams()` and normalize
   `Array.isArray(x) ? x[0] : x`.
4. Strings → new or existing namespace in `locales/en/`. Screens inside an
   existing flow reuse its namespace (onboarding → `deviceOnboarding`,
   patch v2 → `patchFlow`). **If the screen renders on first paint, its
   namespace must be eager.**
5. Device-onboarding screens that should survive a crash: add the segment to
   `RecoverableOnboardingStep` in `interfaces/device-onboarding.ts`.

## Add a feature component

1. `components/<feature>/<Name>/` — `index.tsx` is the container (store and
   hook reads, branching `null | <NameLoading/> | <NameEmpty/> |
   <NameContent/>`), with presentational siblings beside it.
2. `interface NameProps` at the top, default-export the container, keep files
   under ~400 lines.
3. Style with the memoized `useUnistyles` idiom. The loading variant is a
   content-shaped placeholder, **not** a shimmer.
4. Check which styling system the folder uses before you start — `insights/`
   and `onboarding_v2/` are not on `theme.*`.

## Add or extend a Zustand store

```ts
create<XxxStore>()(persist(
  (set, get) => ({ … }),
  { name: 'orion_xxx',
    storage: createJSONStorage(() => mmkvStorageAdapter),
    partialize: s => ({ /* only durable fields */ }) },
));
```

Checklist:

- Don't persist transient flags unless you mean to. (Some stores persist
  `isLoading` deliberately, to drive skeletons on cold start.)
- `Map` / `Set` fields need an `onRehydrateStorage` re-init — copy
  `deviceControlStore.ts`.
- **User-scoped store ⇒ add it to `purgeAllStorage`** in
  `utils/storage/common.ts` — both `persist.clearStorage()` and the in-memory
  reset. Miss this and data leaks across logout and account-swap.
- If boot logic depends on it, add it to `waitForStoresHydration` in
  `utils/app/initializeApp.ts`. Only a handful are awaited today; each one you
  add costs startup time.
- For optimistic server writes reuse `utils/store/debouncedOptimisticUpdate.ts`
  (`setupDebounceTimer` + `executeDebouncedApiCall`). Canonical shape:
  `devicesStore.debouncedUpdateDevice` — rollback closure, `mutate('/v1/…')` on
  success, cleanup, `hasPendingUpdates`.

## Add an API endpoint

1. Function in the matching `network/<domain>.ts`:

   ```ts
   const res = await networkClient.networkInstance().post<Response<T>>('/v1/…', body);
   if (!res.success) …
   return res.response;
   ```

   Wire DTOs (snake_case) go in `interfaces/<domain>.ts`, plus a domain model
   and mapper if the shapes diverge.
2. Read paths that feed UI follow fetch-and-hydrate: lazy
   `await import('../store/xxxStore')`, `setIsLoading(!hasCached)`, write to the
   store, return the data. Wire it into
   `components/ui/layout/InitialAPI.tsx` if it should load at boot, otherwise
   `useSWR(isReady ? 'cache-key' : null, () => fetchFn(), …)` in a hook.
3. Mutations from screens:
   `useSWRMutationWithError('v1/…', () => fn(args), { showDefaultError | disableErrorHandling })`,
   then `mutate('<read key>')` to revalidate.

**SWR keys are cache ids, not URLs** — `/v1/schedules` is the key for an
endpoint actually at `/v1/sleep-schedules`. And always pass an explicit
fetcher; the default one is unauthenticated raw `fetch`.

## Add translations

1. Keys go in `locales/en/<ns>.json`. `{{var}}` for interpolation, plurals via
   `key_one` / `key_other` + `{{count}}`.
2. New namespace: create the JSON, then register it in `i18n/index.ts` —
   **eager only if it renders on splash or first home paint**, otherwise add it
   to `loadDeferredI18nNamespaces()`. Getting this wrong shows raw keys
   permanently, not briefly. Leave a comment saying why, as the existing eager
   eight do.
3. Watch the three namespace↔filename mismatches: `deviceOnboarding`,
   `patchHome`, `onboardingV2`.
4. Components use `useTranslation('ns')`; non-component code uses
   `i18n.t('key', { ns })`.

## Add an icon

Copy the icon template (see the design-system RN reference §8) into
`icons/<Name>.tsx` — 24×24, `fill="none"`, themed default fill via
`useUnistyles`, `SvgProps` spread, PascalCase with an `Outlined`/`Filled`
suffix, default export.

Larger branded art → `native-assets/`. Native-surface icons (menu, notification)
→ `assets/xml-icons/*.xml`, registered in the `withAndroidDrawables` plugin
options in `app.config.js`, then **prebuild**.

## Add a feature flag

```ts
// config/featureFlags.ts
public readonly myFeature: FeatureFlagKey<boolean> =
  { key: 'my-feature', defaultValue: false, platform: 'both' };

// hooks/useLaunchDarkly.ts
export function useMyFeature() {
  return useFeatureFlag(FeatureFlags.myFeature.key, FeatureFlags.myFeature.defaultValue);
}
```

Gate UI and routes with the hook. Create the flag in the LaunchDarkly dashboard
for **all three environments**. The base hooks already handle the
MMKV persisted-fallback-until-client-ready behaviour.

## Device-control work

Temperature, power, LED, quiet mode, thermal relief.

- **Read** from `useDeviceControlStore` (`liveDevice`, `zoneStates`,
  `deviceStatus`, `connectionState`). Never from the WebSocket context — its
  value is intentionally empty.
- **Write** through `hooks/useDeviceControl.ts`, or extend its four-phase
  pattern: optimistic local update → `lockProperties` → 1s debounce → REST
  (`network/liveDevice.ts`) → 5s post-API lock → unlock. **The locks are what
  stop incoming WS frames reverting the optimistic UI.**
- Respect `useControlsDisabled` (research and sham devices) and
  `useHasDeviceIssue` gating.
- New live-device fields: extend `interfaces/websocket.ts`, handle in
  `syncFromWebSocket`, and add an in-flight lock if the field is user-writable.

## Native change

1. Kotlin sources → `native-modules/**` (the plugin copies them in and rewrites
   package names); TS bindings → `native/`. Manifest, gradle and resource
   changes → a config plugin in `plugins/`, registered in `app.config.js`.
2. `npx expo prebuild --platform android` (`--clean` for structural changes),
   rebuild, then **verify the change survives a second prebuild** — idempotency
   is the bug you are looking for.
3. Health Connect data types must change in **both**
   `plugins/withHealthConnect.js` (permissions) and
   `services/healthSync/healthConnectDescriptor.ts` (`KNOWN_RECORD_TYPES` +
   `READ_PERMISSION_BY_RECORD_TYPE`). The declared set is deliberately exactly
   the backend plan's 28 permissions — **Play rejected build 65** for declaring
   10 types no plan row requested. Don't re-widen the manifest without a
   matching Play declaration.
4. NFC library changes: rebuild the AAR via `npm run build:nfctlog-aar`.
5. Upgrading `react-native-ble-plx`, `react-native-health-connect` or
   `react-native-nitro-fetch`: re-validate the diffs in `patches/` first.

## Version bump / release

Bump `version` and `versionCode` in `app.config.js` — both hardcoded, and
`versionCode` must increase monotonically (EAS does not auto-increment).
Prebuild propagates them into `android/app/build.gradle`. Then
`npm run android:bundle:release`, or the EAS `production` profile.
