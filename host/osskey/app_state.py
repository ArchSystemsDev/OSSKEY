import gc
import time
from dataclasses import dataclass, field
from typing import Any

from osskey.crypto import zero_key
from osskey.vault import VaultManager


@dataclass
class AppState:
    app: str = "LOCKED"
    device: str = "DISCONNECTED"
    vault_manager: VaultManager = field(default_factory=VaultManager)
    derived_key: bytearray = field(default_factory=bytearray)
    encrypted_blob: bytes = b""
    settings: dict[str, Any] = field(default_factory=dict)
    inactivity_timer_id: str | None = None
    last_interaction: float = field(default_factory=time.time)
    timeout_minutes: int = 5

    def lock(self) -> None:
        self.app = "LOCKED"
        self.zero_sensitive()

    def unlock(self) -> None:
        self.app = "UNLOCKED"

    def zero_sensitive(self) -> None:
        if self.derived_key:
            zero_key(self.derived_key)
        self.derived_key = bytearray()
        self.vault_manager = VaultManager()
        self.encrypted_blob = b""
        gc.collect()
