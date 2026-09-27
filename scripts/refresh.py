#!/usr/bin/env python3
"""Rewrite marketplace.json from each node's own discover. With `--request FILE`, first add the node named in that listing request and write the reply to it."""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys

from validate import FILE, Node, OptedOut

GRACE_DAYS = 7
NODE_IN_TEXT = re.compile(r"https://[^/\s]+/mcp\b")


class Registry:
    def __init__(self, today: datetime.date):
        self.data = json.loads(FILE.read_text())
        self.today = today

    @property
    def sellers(self) -> list[dict]:
        return self.data["sellers"]

    def refresh(self) -> None:
        kept = []
        for old in self.sellers:
            try:
                kept.append({**Node(old["node"]).entry(), "listed": old["listed"]})
            except OptedOut:
                pass
            except ValueError:
                since = old.get("down_since", self.today.isoformat())
                if (self.today - datetime.date.fromisoformat(since)).days < GRACE_DAYS:
                    kept.append({**old, "down_since": since})
        self.data["sellers"] = kept

    def request(self, text: str) -> tuple[bool, str]:
        found = NODE_IN_TEXT.search(text)
        if not found:
            return False, "Not listed: this request has no store address ending in /mcp."
        url = found.group(0)
        try:
            entry = Node(url).entry()
        except ValueError as e:
            return False, f"Not listed: {e}.\n\nOpen a new request once that changes."
        current = next((i for i, s in enumerate(self.sellers) if s["node"] == url), None)
        if current is not None:
            self.sellers[current] = {**entry, "listed": self.sellers[current]["listed"]}
            return True, "Already listed. Your entry now matches your store."
        self.sellers.append({**entry, "listed": self.today.isoformat()})
        return True, "Listed. Buyers can now find your store in the public list of Lore sellers. It stays in step with your store every day."

    def save(self) -> None:
        FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", metavar="FILE", help="a listing request's body; replaced by the reply")
    args = parser.parse_args()
    registry = Registry(datetime.date.today())
    if args.request:
        with open(args.request) as handle:
            ok, reply = registry.request(handle.read())
        with open(args.request, "w") as handle:
            handle.write(reply + "\n")
        registry.save()
        return 0 if ok else 1
    registry.refresh()
    registry.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
