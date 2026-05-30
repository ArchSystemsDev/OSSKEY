import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Credential:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    label: str = ""
    username: str = ""
    password: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class VaultManager:
    def __init__(self) -> None:
        self._credentials: list[Credential] = []

    def add(self, label: str, username: str, password: str) -> Credential:
        cred = Credential(label=label, username=username, password=password)
        self._credentials.append(cred)
        return cred

    def edit(self, cred_id: str, **kwargs: Any) -> Credential | None:
        for cred in self._credentials:
            if cred.id == cred_id:
                for key, value in kwargs.items():
                    if hasattr(cred, key):
                        setattr(cred, key, value)
                cred.updated_at = time.time()
                return cred
        return None

    def delete(self, cred_id: str) -> bool:
        for i, cred in enumerate(self._credentials):
            if cred.id == cred_id:
                del self._credentials[i]
                return True
        return False

    def search(self, query: str) -> list[Credential]:
        q = query.lower()
        return [
            c
            for c in self._credentials
            if q in c.label.lower() or q in c.username.lower()
        ]

    def get(self, cred_id: str) -> Credential | None:
        for c in self._credentials:
            if c.id == cred_id:
                return c
        return None

    def serialize(self) -> bytes:
        data = [asdict(c) for c in self._credentials]
        return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )

    def deserialize(self, data: bytes) -> list[Credential]:
        items = json.loads(data.decode("utf-8"))
        self._credentials = [Credential(**item) for item in items]
        return self._credentials

    def load(self, filepath: str) -> None:
        with open(filepath, "rb") as f:
            raw = f.read()
        self.deserialize(raw)

    def save(self, filepath: str) -> None:
        with open(filepath, "wb") as f:
            f.write(self.serialize())

    @property
    def credentials(self) -> list[Credential]:
        return self._credentials.copy()

    def __len__(self) -> int:
        return len(self._credentials)
