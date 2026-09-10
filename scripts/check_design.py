#!/usr/bin/env python3
"""Design-system linter for the Orion mobile apps.

Reports uses of raw values where a design token exists, plus a few
platform-specific traps that are silent at compile time.

    python3 scripts/check_design.py --platform swift
    python3 scripts/check_design.py --platform rn --budget scripts/design-budget.json
    python3 scripts/check_design.py --platform swift --budget <path> --update
    python3 scripts/check_design.py --platform swift --diff-base origin/develop-working

Exit codes:
    0  within budget (or no budget given and no violations)
    1  over budget, or violations found with no budget file
    2  usage error

A zero exit means "no new violations", not "no violations" -- the budget is a
ratchet, the same shape as orion-control-plane's check:eslint. And the linter
is a floor: it cannot tell you that you used the wrong token, only that you
used none.

Source of truth: github.com/Orion-Sleep/design. Edit it there, not in a
vendored copy -- CI checks the copies match.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict

# --------------------------------------------------------------------------
# Token scales, shared by both platforms because both are generated from the
# same payload in this repo.
# --------------------------------------------------------------------------

SPACING = {4: "xx-small", 8: "x-small", 12: "small", 16: "medium",
           24: "large", 32: "x-large", 48: "xx-large", 64: "xxx-large"}
RADIUS = {12: "small", 16: "medium", 20: "large", 24: "x-large", 32: "xx-large"}

SWIFT_SPACING = {4: ".xxSmall", 8: ".xSmall", 12: ".small", 16: ".medium",
                 24: ".large", 32: ".xLarge", 48: ".xxLarge", 64: ".xxxLarge"}
SWIFT_RADIUS = {12: "Radius.small", 16: "Radius.medium", 20: "Radius.large",
                24: "Radius.xLarge", 32: "Radius.xxLarge"}

# Literals that are house convention, not drift.
RN_OK_RADIUS = {0, 100}          # 100 is the pill
RN_OK_SPACING = {0}
SWIFT_OK_SPACING = {0}
SWIFT_OK_RADIUS = {0, 9999}      # Radius.infinity

# An annotated hardcode is tracked debt, not a violation. Look this far back.
#
# Only "GAP (tokens)" waives a rule. A bare Figma reference does NOT: there are
# ~500 of them in the mobile code and they record which node a value came from,
# which is provenance, not permission. Treating them as a waiver would silently
# exempt most of the codebase from the ratchet.
GAP_MARKER = re.compile(r"GAP \(tokens\)", re.I)
GAP_LOOKBACK = 6

# --------------------------------------------------------------------------
# Paths we never lint
# --------------------------------------------------------------------------

ALWAYS_SKIP = (
    "/.claude/worktrees/",
    "/node_modules/",
    "/.git/",
    "/Pods/",
    "/build/",
    "/DerivedData/",
    "/android/",
    "/ios/",
)

SWIFT_SKIP = (
    ".generated.swift",
    "/Design Library/",     # the library defines the tokens; §exempt by design
    "/File Templates/",
)

RN_SKIP = (
    "unistyles.ts",
    "unistyles.d.ts",
    "/components/insights/",     # owns palette.ts + the insights_v3 namespace
    "/components/onboarding_v2/",  # own hex family, matched to its neighbours
    "/components/debug/",          # deliberately unstyled
    "/icons/",                     # template-driven, checked by eye
    "/.expo/",
)

# Protected generated files, flagged when --diff-base shows them modified.
PROTECTED = {
    "swift": (".generated.swift", "Strings.generated.swift"),
    "rn": ("unistyles.ts",),
}

# ...unless the thing that generates that file changed in the same diff. A
# generated file moving alongside its own generator or input payload is a
# regeneration, which is the sanctioned way to change one; moving on its own is
# a hand-edit.
#
# Paired per protected file rather than diff-wide: changing generate_colors.py
# should not license an unrelated hand-edit to Strings.generated.swift.
GENERATORS = {
    "swift": (
        ("Strings.generated.swift", ("scripts/make_strings.py",
                                     "scripts/generate_strings.py",
                                     "scripts/format_strings.py",
                                     "Localizable.xcstrings")),
        (".generated.swift", ("scripts/generate_", "scripts/make_all.py",
                              "scripts/design-tokens.json",
                              "scripts/token_fetch.py",
                              "scripts/update_tokens.py")),
    ),
    "rn": (
        ("unistyles.ts", ("scripts/sync-tokens.js",)),
    ),
}


@dataclass
class Violation:
    rule: str
    file: str
    line: int
    text: str
    hint: str


# --------------------------------------------------------------------------
# Swift rules
# --------------------------------------------------------------------------

RE_CORNER_RADIUS = re.compile(r"(?<![.\w])\.cornerRadius\(")
RE_COLOR_LITERAL = re.compile(r"Color\(\s*(?:hex:|red:)")
RE_HEX_STRING = re.compile(r'"#[0-9A-Fa-f]{6,8}"')
RE_SYSTEM_FONT = re.compile(r"\.font\(\s*\.(?:system\(|custom\(|body|caption|title|headline|subheadline|footnote|largeTitle|callout)")
RE_ROUNDED_RECT = re.compile(r"RoundedRectangle\(\s*cornerRadius:\s*(\d+(?:\.\d+)?)")
RE_PADDING_BARE = re.compile(r"\.padding\(\s*(\d+)\s*\)")
RE_PADDING_EDGE = re.compile(r"\.padding\(\s*\.\w+\s*,\s*(\d+)\s*\)")
RE_SPACING_INT = re.compile(r"\bspacing:\s*(\d+)\b")
RE_TEXT_LITERAL = re.compile(r'\bText\(\s*"([^"]{2,})"')
RE_DEPRECATED_FONT = re.compile(r"typographyFont\(\s*style:[^)]*weight:\s*\.\w+\s*\)")


RE_PREVIEW_START = re.compile(r"^\s*(#Preview\b|struct\s+\w*_Previews\b)")
RE_INTERPOLATION = re.compile(r"\\\([^)]*\)")


def check_swift(path: str, lines: list[str]) -> list[Violation]:
    out: list[Violation] = []

    # Previews are throwaway sample content -- copy in them is not shipped and
    # does not need a string key. They live at the end of the file by
    # convention (the File Templates put them there).
    preview_from = len(lines)
    for i, l in enumerate(lines):
        if RE_PREVIEW_START.match(l):
            preview_from = i
            break

    def annotated(i: int) -> bool:
        lo = max(0, i - GAP_LOOKBACK)
        return any(GAP_MARKER.search(l) for l in lines[lo:i])

    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        n = i + 1
        short = line.strip()[:110]

        if RE_CORNER_RADIUS.search(line):
            out.append(Violation(
                "swift/cornerRadius", path, n, short,
                ".cornerRadius(.large) resolves to Spacing.large (24), not "
                "Radius.large (20). Use .continuousCornerRadius(_:)."))

        if (RE_COLOR_LITERAL.search(line) or RE_HEX_STRING.search(line)) and not annotated(i):
            out.append(Violation(
                "swift/color-literal", path, n, short,
                "Use a semantic token from Color.generated.swift, or annotate "
                "with '/// GAP (tokens): ...' if none exists."))

        if RE_SYSTEM_FONT.search(line):
            out.append(Violation(
                "swift/system-font", path, n, short,
                "Use .typography(style:size:weight:) or "
                "typographyFont(style:size:weight:dynamicTypeSize:)."))

        if RE_DEPRECATED_FONT.search(line):
            out.append(Violation(
                "swift/deprecated-typography-font", path, n, short,
                "The 3-arg typographyFont is deprecated -- it reads "
                "UITraitCollection.current and ignores .dynamicTypeSize(). "
                "Pass dynamicTypeSize:."))

        m = RE_ROUNDED_RECT.search(line)
        if m and not annotated(i):
            v = float(m.group(1))
            if v.is_integer() and int(v) not in SWIFT_OK_RADIUS:
                iv = int(v)
                tok = SWIFT_RADIUS.get(iv)
                out.append(Violation(
                    "swift/radius-literal", path, n, short,
                    f"Use {tok}.value." if tok
                    else f"{iv} is off the radius scale (12/16/20/24/32) -- "
                         "check Figma, then annotate if intended."))

        for rx, kind in ((RE_PADDING_BARE, "padding"), (RE_PADDING_EDGE, "padding"),
                         (RE_SPACING_INT, "spacing")):
            for m in rx.finditer(line):
                v = int(m.group(1))
                if v in SWIFT_OK_SPACING or annotated(i):
                    continue
                tok = SWIFT_SPACING.get(v)
                out.append(Violation(
                    f"swift/{kind}-literal", path, n, short,
                    f"Use {tok}." if tok
                    else f"{v} is off the spacing scale "
                         "(4/8/12/16/24/32/48/64) -- check Figma, then "
                         "annotate if intended."))

        m = RE_TEXT_LITERAL.search(line)
        if m and not annotated(i) and i < preview_from:
            # Strip interpolation first: Text("\(value) \(label)") is assembling
            # already-localized parts, not new copy.
            body = RE_INTERPOLATION.sub("", m.group(1)).strip()
            words = [w for w in re.split(r"\s+", body) if re.search(r"[A-Za-z]{2}", w)]
            if len(words) >= 2:
                out.append(Violation(
                    "swift/hardcoded-string", path, n, short,
                    "Add the key to Localizable.xcstrings, run 'make strings', "
                    "and use Strings.<Feature>.<key>."))
    return out


# --------------------------------------------------------------------------
# RN rules
# --------------------------------------------------------------------------

RE_RN_STYLESHEET = re.compile(r"import\s*\{[^}]*\bStyleSheet\b[^}]*\}\s*from\s*['\"]react-native['\"]")
RE_ABSOLUTE_FILL = re.compile(r"StyleSheet\.absoluteFill")
RE_STYLESHEET_CREATE = re.compile(r"StyleSheet\.create\s*\(")
RE_USE_COLOR_SCHEME = re.compile(r"\buseColorScheme\s*\(")
RE_RN_HEX = re.compile(r"['\"]#[0-9A-Fa-f]{3,8}['\"]")
RE_RN_RGBA = re.compile(r"\brgba?\(\s*\d")
RE_RAW_TEXT = re.compile(r"<Text[\s/>]")
RE_RN_SPACE = re.compile(r"\b(padding|paddingTop|paddingBottom|paddingLeft|paddingRight|"
                         r"paddingHorizontal|paddingVertical|margin|marginTop|marginBottom|"
                         r"marginLeft|marginRight|marginHorizontal|marginVertical|gap|"
                         r"rowGap|columnGap):\s*(\d+)\b")
RE_RN_RADIUS = re.compile(r"\b(borderRadius|borderTopLeftRadius|borderTopRightRadius|"
                          r"borderBottomLeftRadius|borderBottomRightRadius):\s*(\d+)\b")


def check_rn(path: str, lines: list[str]) -> list[Violation]:
    out: list[Violation] = []
    text = "".join(lines)
    # Importing RN's StyleSheet is fine when it is only there for
    # absoluteFill/absoluteFillObject, which unistyles has no equivalent for.
    # It is a violation when the file also builds styles with it.
    rn_stylesheet_ok = (RE_ABSOLUTE_FILL.search(text)
                        and not RE_STYLESHEET_CREATE.search(text))
    in_typography = "/components/ui/typography/" in path

    def annotated(i: int) -> bool:
        lo = max(0, i - GAP_LOOKBACK)
        return any(GAP_MARKER.search(l) for l in lines[lo:i])

    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        n = i + 1
        short = line.strip()[:110]

        if RE_RN_STYLESHEET.search(line) and not rn_stylesheet_ok:
            out.append(Violation(
                "rn/rn-stylesheet", path, n, short,
                "Import StyleSheet from 'react-native-unistyles'. The RN one is "
                "only for absoluteFill/absoluteFillObject."))

        if RE_USE_COLOR_SCHEME.search(line):
            out.append(Violation(
                "rn/use-color-scheme", path, n, short,
                "Use rt.themeName from useUnistyles() -- useColorScheme bypasses "
                "the user's override and ScopedTheme."))

        if (RE_RN_HEX.search(line) or RE_RN_RGBA.search(line)) and not annotated(i):
            out.append(Violation(
                "rn/color-literal", path, n, short,
                "Use a theme.color.* token. Dark-surface translucents are the "
                "rgba(219, 233, 253, ...) family, never pure white."))

        if RE_RAW_TEXT.search(line) and not in_typography and not annotated(i):
            out.append(Violation(
                "rn/raw-text", path, n, short,
                "Use Heading/Paragraph/Label/Mono/Badge. Raw Text is only for "
                "nested inline rich text -- annotate that case."))

        for m in RE_RN_SPACE.finditer(line):
            prop, v = m.group(1), int(m.group(2))
            if v in RN_OK_SPACING or annotated(i):
                continue
            tok = SPACING.get(v)
            out.append(Violation(
                "rn/spacing-literal", path, n, short,
                f"{prop}: theme.spacing['{tok}']" if tok
                else f"{v} is off the spacing scale (4/8/12/16/24/32/48/64) -- "
                     "check Figma, then annotate if intended."))

        for m in RE_RN_RADIUS.finditer(line):
            prop, v = m.group(1), int(m.group(2))
            if v in RN_OK_RADIUS or annotated(i):
                continue
            tok = RADIUS.get(v)
            out.append(Violation(
                "rn/radius-literal", path, n, short,
                f"{prop}: theme.radius['{tok}']" if tok
                else f"{v} is off the radius scale (12/16/20/24/32); the pill is "
                     "100 -- check Figma, then annotate if intended."))
    return out


# --------------------------------------------------------------------------
# Walking
# --------------------------------------------------------------------------

def wanted(path: str, platform: str) -> bool:
    p = path.replace(os.sep, "/")
    if any(s in p for s in ALWAYS_SKIP):
        return False
    if platform == "swift":
        if not p.endswith(".swift"):
            return False
        return not any(s in p for s in SWIFT_SKIP)
    if not (p.endswith(".ts") or p.endswith(".tsx")):
        return False
    if p.endswith(".d.ts"):
        return False
    return not any(s in p for s in RN_SKIP)


def roots_for(platform: str) -> list[str]:
    if platform == "rn":
        return [d for d in ("app", "components", "hooks", "utils", "store", "network") if os.path.isdir(d)]
    return ["."]


def collect(platform: str) -> list[Violation]:
    check = check_swift if platform == "swift" else check_rn
    found: list[Violation] = []
    for root in roots_for(platform):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if not any(s.strip("/") == d for s in ALWAYS_SKIP)]
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, ".").replace(os.sep, "/")
                if not wanted("/" + rel, platform):
                    continue
                try:
                    with open(path, encoding="utf-8") as fh:
                        lines = fh.readlines()
                except (OSError, UnicodeDecodeError):
                    continue
                found.extend(check(rel, lines))
    return found


def changed_files(base: str) -> list[str]:
    """Files touched vs `base`. Empty list if git can't tell us."""
    try:
        # splitlines(), not split(): the Swift repos have spaces in their
        # paths ("Orion Sleep Test/...", "Sales Studio/...") and whitespace
        # splitting silently fragments every one of them.
        return subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True, text=True, check=True).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def protected_touched(platform: str, base: str) -> list[Violation]:
    changed = changed_files(base)
    out = []
    for f in changed:
        # First matching rule wins, so the more specific entry
        # (Strings.generated.swift) must precede the general one.
        for marker, generators in GENERATORS[platform]:
            if not (f.endswith(marker) or marker in f):
                continue
            if any(any(g in c for g in generators) for c in changed):
                break        # regenerated -- expected
            out.append(Violation(
                f"{platform}/generated-file-edited", f, 0, f,
                "This file is generated and changed on its own -- neither its "
                "generator nor its input payload moved with it. Change the "
                "source in Orion-Sleep/design and regenerate."))
            break
    return out


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--platform", required=True, choices=("swift", "rn"))
    ap.add_argument("--budget", help="path to design-budget.json")
    ap.add_argument("--update", action="store_true",
                    help="rewrite the budget from the current counts (only ever downward)")
    ap.add_argument("--relock-reason", metavar="WHY",
                    help="allow --update to raise a count, recording WHY in the budget. "
                         "For when a rule got stricter, not for making CI pass.")
    ap.add_argument("--diff-base", help="also flag generated files modified vs this ref")
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    ap.add_argument("--limit", type=int, default=25, help="examples printed per rule")
    args = ap.parse_args()

    violations = collect(args.platform)
    if args.diff_base:
        violations += protected_touched(args.platform, args.diff_base)

    counts: dict[str, int] = {}
    for v in violations:
        counts[v.rule] = counts.get(v.rule, 0) + 1

    if args.json:
        print(json.dumps({"platform": args.platform,
                          "counts": counts,
                          "total": len(violations),
                          "violations": [asdict(v) for v in violations]}, indent=2))

    if args.update:
        if not args.budget:
            print("--update needs --budget", file=sys.stderr)
            return 2
        old, disabled = {}, {}
        if os.path.exists(args.budget):
            with open(args.budget) as fh:
                prev = json.load(fh)
            old = prev.get("counts", {})
            disabled = prev.get("disabled_rules", {})
        if disabled:
            counts = {r: c for r, c in counts.items() if r not in disabled}
        raised = {r: (old[r], counts[r]) for r in counts
                  if r in old and counts[r] > old[r]}
        if raised and not args.relock_reason:
            for r, (o, nnew) in sorted(raised.items()):
                print(f"refusing to raise {r}: {o} -> {nnew}", file=sys.stderr)
            print("\nThe budget only ratchets down. Fix the new violations "
                  "instead of re-locking.\n"
                  "\nIf a rule genuinely got stricter and the rise is that "
                  "change rather than new drift, say so:\n"
                  "  --update --relock-reason \"...\"", file=sys.stderr)
            return 1
        with open(args.budget, "w") as fh:
            doc = {"_comment": "Ratchet for check_design.py. Counts may fall, "
                               "never rise. Re-lock with --update after a cleanup.",
                   "platform": args.platform,
                   "counts": dict(sorted(counts.items()))}
            if disabled:
                doc["disabled_rules"] = disabled
            if raised:
                doc["_relocked_upward"] = {
                    "reason": args.relock_reason,
                    "rules": {r: f"{o} -> {n}" for r, (o, n) in sorted(raised.items())},
                }
            json.dump(doc, fh, indent=2)
            fh.write("\n")
        if raised:
            print(f"budget RAISED for {len(raised)} rule(s), recorded in the file:")
            for r, (o, n) in sorted(raised.items()):
                print(f"  {r}: {o} -> {n}")
            print(f"  reason: {args.relock_reason}")
        print(f"budget written: {args.budget} ({len(violations)} total)")
        return 0

    if not args.budget:
        if not args.json:
            report(violations, counts, args.limit)
        return 1 if violations else 0

    if not os.path.exists(args.budget):
        print(f"no budget at {args.budget} -- create one with --update", file=sys.stderr)
        return 2
    with open(args.budget) as fh:
        budget_doc = json.load(fh)
    budget = budget_doc.get("counts", {})

    # Some rules cannot be satisfied in some repos -- orion-sales-studio-ios has
    # no typography API at all, so swift/system-font has no correct alternative
    # to point at and freezing it would block every new screen. Disable such a
    # rule explicitly, with a reason, rather than pretending the budget holds.
    disabled = budget_doc.get("disabled_rules", {})
    if disabled:
        counts = {r: c for r, c in counts.items() if r not in disabled}
        violations = [v for v in violations if v.rule not in disabled]

    over = {r: (budget.get(r, 0), c) for r, c in counts.items() if c > budget.get(r, 0)}
    if not over:
        for rule, why in sorted(disabled.items()):
            print(f"note: {rule} is disabled here -- {why}")
        improved = {r: (b, counts.get(r, 0)) for r, b in budget.items()
                    if counts.get(r, 0) < b}
        print(f"design check: {len(violations)} violations, all within budget.")
        if improved:
            print("Improved since the budget was locked:")
            for r, (b, c) in sorted(improved.items()):
                print(f"  {r}: {b} -> {c}")
            print("Re-lock with: --budget <path> --update")
        return 0

    print("design check FAILED -- these rules went up:\n")
    for rule, (allowed, actual) in sorted(over.items()):
        print(f"  {rule}: {allowed} allowed, {actual} found  (+{actual - allowed})")
    print()

    shown = [v for v in violations if v.rule in over]
    # The budget records counts, not locations, so we cannot say exactly which
    # occurrence is new. Narrowing to the files this branch touched almost
    # always does, and turns a 56-line dump into the handful you added.
    if args.diff_base:
        touched = set(changed_files(args.diff_base))
        in_diff = [v for v in shown if v.file in touched]
        if in_diff:
            print(f"In files changed vs {args.diff_base} "
                  f"({len(in_diff)} of {len(shown)} for these rules):\n")
            shown = in_diff

    report(shown, {r: sum(1 for v in shown if v.rule == r) for r in over}, args.limit)
    print("Fix the new violations. Do not raise the budget to make CI pass.")
    return 1


def report(violations: list[Violation], counts: dict[str, int], limit: int) -> None:
    if not violations:
        print("design check: clean.")
        return
    for rule in sorted(counts):
        rows = [v for v in violations if v.rule == rule]
        print(f"{rule}  ({len(rows)})")
        print(f"  {rows[0].hint}")
        for v in rows[:limit]:
            where = f"{v.file}:{v.line}" if v.line else v.file
            print(f"    {where}\n      {v.text}")
        if len(rows) > limit:
            print(f"    ... and {len(rows) - limit} more")
        print()


if __name__ == "__main__":
    sys.exit(main())
