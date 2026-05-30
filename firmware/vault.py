import os

VAULT_FILE = "/vault.bin"


def vault_exists():
    try:
        os.stat(VAULT_FILE)
        return True
    except OSError:
        return False


def read_vault():
    with open(VAULT_FILE, "rb") as f:
        return f.read()


def write_vault(data):
    with open(VAULT_FILE, "wb") as f:
        f.write(data)


def erase_vault():
    try:
        os.remove(VAULT_FILE)
    except OSError:
        pass
    try:
        os.remove("/vault.tmp")
    except OSError:
        pass
