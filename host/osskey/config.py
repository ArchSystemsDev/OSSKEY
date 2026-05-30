import sys
from pathlib import Path


def _data_dir() -> Path:
    if sys.platform == "win32":
        import os
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "OSSKEY"
    return Path.home() / ".local" / "share" / "osskey"


def vault_path() -> Path:
    return _data_dir() / "vault.enc"


def settings_path() -> Path:
    return _data_dir() / "settings.json"


KDF_SALT_FILE = "kdf_salt.bin"


def kdf_salt_path() -> Path:
    return _data_dir() / KDF_SALT_FILE


DEFAULT_SETTINGS: dict = {
    "timeout_minutes": 5,
    "auto_lock": True,
}
