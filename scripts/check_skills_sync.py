#!/usr/bin/env python3
"""Verify the vendored Orion skills match what was vendored.

    python3 scripts/check_skills_sync.py

Reads .claude/skills/.vendored.json and re-hashes every file it lists. Fails
if anything was edited, added or removed locally.

The skills are authored in github.com/Orion-Sleep/design and copied here. A
local edit is lost the next time anyone re-vendors, and worse, it makes this
repo disagree with the other three about the same convention. Edit them at the
source instead:

    cd ../design
    $EDITOR skills/<skill>/SKILL.md
    python3 scripts/vendor_skills.py --all --root ..

This checks the copies against their recorded hashes rather than against the
design repo, so it needs no network and no cross-repo credentials -- and it
does not go red because someone pushed to the design repo. Picking up newer
skills is a deliberate re-vendor, not a drift.

Exit codes: 0 in sync, 1 out of sync, 2 nothing vendored.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

MANIFEST = os.path.join(".claude", "skills", ".vendored.json")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not os.path.exists(MANIFEST):
        print(f"{MANIFEST} not found -- nothing vendored in this repo.",
              file=sys.stderr)
        return 2

    with open(MANIFEST) as fh:
        data = json.load(fh)
    expected: dict[str, str] = data.get("files", {})
    if not expected:
        print(f"{MANIFEST} lists no files.", file=sys.stderr)
        return 2

    modified, missing = [], []
    for rel, want in sorted(expected.items()):
        if not os.path.exists(rel):
            missing.append(rel)
        elif sha256(rel) != want:
            modified.append(rel)

    # Anything under .claude/skills/ that the manifest does not know about.
    skills_root = os.path.join(".claude", "skills")
    extra = []
    for dirpath, dirnames, filenames in os.walk(skills_root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            rel = os.path.join(dirpath, fn).replace(os.sep, "/")
            if rel.endswith("/.vendored.json"):
                continue
            if rel not in expected:
                extra.append(rel)

    if not (modified or missing or extra):
        print(f"skills in sync: {len(expected)} files from "
              f"{data.get('source', '?')} @ {data.get('source_commit', '?')[:8]}")
        return 0

    print("::error::Vendored skills do not match .vendored.json.\n")
    for label, rows in (("modified locally", modified),
                        ("missing", missing),
                        ("not in the manifest", extra)):
        if rows:
            print(f"  {label}:")
            for r in sorted(rows):
                print(f"    {r}")
            print()
    print("These files are vendored from Orion-Sleep/design. Make the change "
          "there and re-vendor:\n")
    print("    cd ../design")
    print("    python3 scripts/vendor_skills.py --target <this repo>\n")
    print("To discard a local edit: git checkout -- .claude/skills")
    return 1


if __name__ == "__main__":
    sys.exit(main())
