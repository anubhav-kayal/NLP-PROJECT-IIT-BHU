import json
import os
from typing import Set, Optional

WHITELIST_PATH = os.path.join(os.path.dirname(__file__), "whitelist.json")


class Whitelist:
    def __init__(self, path: Optional[str] = None):
        self.path = path or WHITELIST_PATH
        self.entries: Set[str] = set()
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    data = json.load(f)
                self.entries = set(data.get("entries", []))
            except (json.JSONDecodeError, IOError):
                self.entries = set()

    def save(self):
        with open(self.path, "w") as f:
            json.dump({"entries": sorted(self.entries)}, f, indent=2)

    def add(self, term: str):
        self.entries.add(term.strip().lower())
        self.save()

    def remove(self, term: str):
        self.entries.discard(term.strip().lower())
        self.save()

    def is_whitelisted(self, text: str) -> bool:
        return text.strip().lower() in self.entries

    def list(self) -> list:
        return sorted(self.entries)

    def contains_any(self, text: str) -> bool:
        text_lower = text.lower()
        for entry in self.entries:
            if entry in text_lower:
                return True
        return False
