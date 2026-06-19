import json
import os
import time
from typing import List, Optional
from cryptography.fernet import Fernet

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "audit")
KEY_FILE = os.path.join(AUDIT_DIR, ".audit_key")
LOG_FILE = os.path.join(AUDIT_DIR, "audit_log.enc")


class AuditLog:
    def __init__(self, enabled: bool = True, key: Optional[bytes] = None):
        self.enabled = enabled
        if not enabled:
            self.cipher = None
            return
        os.makedirs(AUDIT_DIR, exist_ok=True)
        if key:
            self.cipher = Fernet(key)
        else:
            self.cipher = self._load_or_create_key()
        self._events: list = []

    def _load_or_create_key(self) -> Fernet:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(KEY_FILE, "wb") as f:
                f.write(key)
            os.chmod(KEY_FILE, 0o600)
        return Fernet(key)

    @classmethod
    def get_key_path(cls) -> str:
        return KEY_FILE

    def log_event(
        self,
        original_text: str,
        redacted_text: str,
        spans: list,
        speaker_info: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        if not self.enabled:
            return
        event = {
            "timestamp": time.time(),
            "session_id": session_id or "",
            "original_text": original_text[:200],
            "redacted_text": redacted_text[:200],
            "pii_detected": [
                {
                    "label": getattr(s, "label", s.get("label", "?")),
                    "text": getattr(s, "text", s.get("text", "")),
                    "context": getattr(s, "context", s.get("context", "")),
                }
                for s in spans
            ],
            "speaker": speaker_info or "",
        }
        self._events.append(event)

    def flush(self):
        if not self.enabled or not self._events:
            return
        existing = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "rb") as f:
                    encrypted = f.read()
                decrypted = self.cipher.decrypt(encrypted)
                existing = json.loads(decrypted.decode())
            except Exception:
                existing = []
        existing.extend(self._events)
        data = json.dumps(existing, indent=2).encode()
        encrypted = self.cipher.encrypt(data)
        with open(LOG_FILE, "wb") as f:
            f.write(encrypted)
        self._events = []

    @classmethod
    def view(cls, key_path: Optional[str] = None) -> list:
        kp = key_path or KEY_FILE
        if not os.path.exists(kp) or not os.path.exists(LOG_FILE):
            return []
        with open(kp, "rb") as f:
            key = f.read()
        cipher = Fernet(key)
        with open(LOG_FILE, "rb") as f:
            encrypted = f.read()
        decrypted = cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())

    @classmethod
    def print_log(cls, key_path: Optional[str] = None):
        events = cls.view(key_path)
        if not events:
            print("  No audit log entries found.")
            return
        print(f"\n  AUDIT LOG ({len(events)} entries)")
        print("  " + "=" * 60)
        for e in events:
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["timestamp"]))
            pii_types = ", ".join(
                sorted(set(p["label"] for p in e.get("pii_detected", [])))
            )
            print(f"  [{t}] {pii_types}")
            print(f"    Original: {e['original_text'][:80]}")
            print(f"    Redacted: {e['redacted_text'][:80]}")
            if e.get("speaker"):
                print(f"    Speaker:  {e['speaker']}")
            print()
