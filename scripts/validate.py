#!/usr/bin/env python3
"""Check marketplace.json. Standard library only. `--live BASE` also asks each entry that differs from BASE's copy to answer discover."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "marketplace.json"
REQUIRED = ["name", "node", "store", "network", "topics", "publications", "price_usd", "listed"]
OPTIONAL = ["answer_price_usd", "down_since"]
NODE = re.compile(r"^https://[^/\s]+/mcp$")
NETWORK = re.compile(r"^eip155:[0-9]+$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
MAINNET = "eip155:8453"


class OptedOut(ValueError):
    """The node answered and said not to list it."""


class Node:
    """One seller's node, read over MCP the way an agent reads it."""

    def __init__(self, url: str):
        self.url = url

    def _post(self, message: dict, session: str | None = None):
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json", "User-Agent": "lore-marketplace"}
        if session:
            headers["Mcp-Session-Id"] = session
        return urllib.request.urlopen(urllib.request.Request(self.url, json.dumps(message).encode(), headers), timeout=20)

    @staticmethod
    def _payload(response) -> dict:
        text = response.read().decode()
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            text = next(line[6:] for line in text.splitlines() if line.startswith("data: "))
        return json.loads(text)

    def discover(self) -> dict:
        hello = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "lore-marketplace", "version": "1"}}
        with self._post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": hello}) as r:
            session = r.headers["Mcp-Session-Id"]
            self._payload(r)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, session).close()
        with self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "discover", "arguments": {}}}, session) as r:
            return json.loads(self._payload(r)["result"]["content"][0]["text"])

    def entry(self) -> dict:
        """The entry this node earns today, every field from its own discover. Raises ValueError with a plain reason when it earns none."""
        try:
            m = self.discover()
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"your store did not answer ({e})") from e
        if m.get("listed") is False:
            raise OptedOut("your store asked not to be listed")
        if m.get("listed") is not True or not str(m.get("name", "")).strip():
            raise ValueError("your store has not been switched on for the marketplace. Choose List in Settings in the Lore app")
        if m.get("network") != MAINNET:
            raise ValueError("your store takes test payments only")
        if not m.get("publication_count"):
            raise ValueError("your store has no publications yet")
        entry = {
            "name": m["name"].strip()[:80],
            "node": self.url,
            "store": self.url.removesuffix("mcp"),
            "network": m["network"],
            "topics": sorted(m["topics"]),
            "publications": m["publication_count"],
            "price_usd": m["price_usd"],
        }
        if isinstance(m.get("answer_price_usd"), (int, float)):
            entry["answer_price_usd"] = m["answer_price_usd"]
        return entry


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
        for key in ("listed", "down_since"):
            if key in s and not DATE.match(str(s[key])):
                errors.append(f"{where}: {key} must be YYYY-MM-DD")
        if not isinstance(s.get("name"), str) or not 0 < len(s.get("name", "")) <= 80:
            errors.append(f"{where}: name must be 1-80 characters")
    return errors


def changed(sellers: list[dict], base: str) -> list[dict]:
    shown = subprocess.run(["git", "show", f"{base}:marketplace.json"], cwd=ROOT, capture_output=True, text=True)
    before = json.loads(shown.stdout)["sellers"] if shown.returncode == 0 else []
    return [s for s in sellers if s not in before]


def live(sellers: list[dict]) -> list[str]:
    errors: list[str] = []
    for s in sellers:
        try:
            Node(s["node"]).entry()
        except ValueError as e:
            errors.append(f"{s['node']}: {e}")
    return errors


def main() -> int:
    data = json.loads(FILE.read_text())
    errors = check(data)
    if not errors and "--live" in sys.argv:
        errors = live(changed(data["sellers"], sys.argv[sys.argv.index("--live") + 1]))
    for e in errors:
        print(f"error: {e}")
    print(f"{len(data.get('sellers', []))} sellers, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
