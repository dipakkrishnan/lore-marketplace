#!/usr/bin/env python3
"""Check marketplace.json. Standard library only. `--live` also asks each store to answer."""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["name", "node", "store", "network", "topics", "publications", "price_usd", "listed"]
OPTIONAL = ["answer_price_usd"]
NODE = re.compile(r"^https://[^/\s]+/mcp$")
NETWORK = re.compile(r"^eip155:[0-9]+$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def check(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must be 1")
    if not isinstance(data.get("name"), str) or not data["name"]:
        errors.append("name must be a non-empty string")
    sellers = data.get("sellers")
    if not isinstance(sellers, list):
        return errors + ["sellers must be a list"]
    seen: set[str] = set()
    for i, s in enumerate(sellers):
        where = f"sellers[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{where}: must be an object")
            continue
        for key in REQUIRED:
            if key not in s:
                errors.append(f"{where}: missing {key}")
        for key in s:
            if key not in REQUIRED + OPTIONAL:
                errors.append(f"{where}: unknown field {key}")
        node = s.get("node", "")
        if not NODE.match(str(node)):
            errors.append(f"{where}: node must be https://<host>/mcp")
        if node in seen:
            errors.append(f"{where}: duplicate node {node}")
        seen.add(node)
        if not str(s.get("store", "")).startswith("https://"):
            errors.append(f"{where}: store must be https")
        if not NETWORK.match(str(s.get("network", ""))):
            errors.append(f"{where}: network must look like eip155:8453")
        if not isinstance(s.get("topics"), list) or not all(isinstance(t, str) and t for t in s.get("topics", [])):
            errors.append(f"{where}: topics must be a list of non-empty strings")
        if not isinstance(s.get("publications"), int) or s.get("publications", -1) < 0:
            errors.append(f"{where}: publications must be a non-negative integer")
        for key in ("price_usd", "answer_price_usd"):
            if key in s and (not isinstance(s[key], (int, float)) or s[key] < 0):
                errors.append(f"{where}: {key} must be a non-negative number")
        if not DATE.match(str(s.get("listed", ""))):
            errors.append(f"{where}: listed must be YYYY-MM-DD")
        if not isinstance(s.get("name"), str) or not 0 < len(s.get("name", "")) <= 80:
            errors.append(f"{where}: name must be 1-80 characters")
    return errors


def live(sellers: list[dict]) -> list[str]:
    errors: list[str] = []
    for s in sellers:
        try:
            with urllib.request.urlopen(urllib.request.Request(s["store"], headers={"User-Agent": "lore-marketplace-validate"}), timeout=15) as r:
                if r.status != 200:
                    errors.append(f"{s['node']}: store answered {r.status}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{s['node']}: store did not answer ({e})")
    return errors


def main() -> int:
    data = json.loads((ROOT / "marketplace.json").read_text())
    errors = check(data)
    if not errors and "--live" in sys.argv:
        errors = live(data["sellers"])
    for e in errors:
        print(f"error: {e}")
    print(f"{len(data.get('sellers', []))} sellers, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
