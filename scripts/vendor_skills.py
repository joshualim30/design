#!/usr/bin/env python3
"""Vendor the Orion mobile skills from this repo into an app repo.

    python3 scripts/vendor_skills.py --target ../orion-ios
    python3 scripts/vendor_skills.py --target ../orion-react-native --dry-run
    python3 scripts/vendor_skills.py --all --root ..

Writes, in the target repo:

    .claude/skills/<skill>/...        the skills for that repo
    .claude/skills/.vendored.json     manifest: source commit + sha256 per file
    scripts/check_design.py           the design linter
    scripts/check_skills_sync.py      verifies the manifest, run by CI

The manifest is what CI checks, not a re-clone of this repo. That is
deliberate: orion-ios already learned the cost of having CI depend on a moving
remote -- see scripts/token_fetch.py, "a push to the design repo instantly
reddened every unrelated PR". Verification against recorded hashes needs no
network and no cross-repo credentials, and it catches the failure that
actually happens, which is someone editing a vendored copy instead of the
source here.

Pulling a *newer* version of the skills is a deliberate act: re-run this
script and commit the result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Which skills each app repo gets.
MANIFEST: dict[str, list[str]] = {
    "orion-ios": [
        "orion-design-system", "orion-ios-dev", "orion-mobile-figma",
        "orion-handoff", "orion-onboard",
    ],
    "orion-sleep-test-ios": [
        "orion-design-system", "orion-ios-dev", "orion-mobile-figma",
        "orion-handoff", "orion-onboard",
    ],
    "orion-sales-studio-ios": [
        "orion-design-system", "orion-ios-dev", "orion-mobile-figma",
        "orion-handoff", "orion-onboard",
    ],
    "orion-react-native": [
        "orion-design-system", "orion-rn-dev", "orion-mobile-figma",
        "orion-handoff", "orion-onboard",
    ],
}

PLATFORM = {
    "orion-ios": "swift",
    "orion-sleep-test-ios": "swift",
    "orion-sales-studio-ios": "swift",
    "orion-react-native": "rn",
}

SCRIPTS = ("check_design.py", "check_skills_sync.py")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def source_commit() -> str:
    try:
        return subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"],
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def files_under(root: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {"__pycache__", ".git"}]
        for fn in sorted(filenames):
            if fn.startswith(".") or fn.endswith(".pyc"):
                continue
            out.append(os.path.join(dirpath, fn))
    return sorted(out)


def vendor(target: str, dry_run: bool = False) -> int:
    name = os.path.basename(os.path.abspath(target).rstrip(os.sep))
    if name not in MANIFEST:
        print(f"{name}: not a known Orion mobile repo. Known: "
              f"{', '.join(sorted(MANIFEST))}", file=sys.stderr)
        return 2
    if not os.path.isdir(target):
        print(f"{target}: no such directory", file=sys.stderr)
        return 2

    skills_src = os.path.join(HERE, "skills")
    skills_dst = os.path.join(target, ".claude", "skills")
    scripts_dst = os.path.join(target, "scripts")

    entries: dict[str, str] = {}
    planned: list[tuple[str, str]] = []

    for skill in MANIFEST[name]:
        src_root = os.path.join(skills_src, skill)
        if not os.path.isdir(src_root):
            print(f"missing skill in source: {skill}", file=sys.stderr)
            return 2
        for src in files_under(src_root):
            rel = os.path.relpath(src, skills_src)
            planned.append((src, os.path.join(skills_dst, rel)))
            entries[f".claude/skills/{rel}".replace(os.sep, "/")] = sha256(src)

    for script in SCRIPTS:
        src = os.path.join(HERE, "scripts", script)
        planned.append((src, os.path.join(scripts_dst, script)))
        entries[f"scripts/{script}"] = sha256(src)

    if dry_run:
        print(f"{name}: would write {len(planned)} files")
        for _, dst in planned:
            print(f"  {os.path.relpath(dst, target)}")
        return 0

    # Remove skills we previously vendored that are no longer in the manifest,
    # so a renamed or dropped skill does not linger.
    #
    # Scoped to what the last manifest actually recorded: an app-specific or
    # third-party skill under .claude/skills is not ours to delete.
    previous = os.path.join(skills_dst, ".vendored.json")
    if os.path.exists(previous):
        try:
            with open(previous) as fh:
                owned_before = json.load(fh).get("files", {})
        except (OSError, json.JSONDecodeError):
            owned_before = {}
        owned_dirs = {rel.split("/")[2] for rel in owned_before
                      if rel.startswith(".claude/skills/") and rel.count("/") > 2}
        for stale in sorted(owned_dirs - set(MANIFEST[name])):
            path = os.path.join(skills_dst, stale)
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"  removed skill we previously vendored: {stale}")

    for src, dst in planned:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        if dst.endswith(".py"):
            os.chmod(dst, 0o755)

    manifest_path = os.path.join(skills_dst, ".vendored.json")
    with open(manifest_path, "w") as fh:
        json.dump({
            "_comment": "Generated by vendor_skills.py in Orion-Sleep/design. "
                        "Do not edit these files here -- edit them in the design "
                        "repo and re-vendor, or CI's skills-sync check will fail.",
            "source": "Orion-Sleep/design",
            "source_commit": source_commit(),
            "repo": name,
            "platform": PLATFORM[name],
            "files": dict(sorted(entries.items())),
        }, fh, indent=2)
        fh.write("\n")

    print(f"{name}: vendored {len(MANIFEST[name])} skills, "
          f"{len(entries)} files, from {source_commit()[:8]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", help="path to one app repo")
    ap.add_argument("--all", action="store_true", help="every known repo under --root")
    ap.add_argument("--root", default="..", help="where the app repos live (with --all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.all:
        rc = 0
        for name in sorted(MANIFEST):
            path = os.path.join(args.root, name)
            if not os.path.isdir(path):
                print(f"{name}: not found under {args.root}, skipping")
                continue
            rc |= vendor(path, args.dry_run)
        return rc

    if not args.target:
        ap.error("pass --target <repo> or --all")
    return vendor(args.target, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
