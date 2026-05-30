from osskey.config import vault_path
from osskey.crypto import encrypt_vault


def save_vault(app_state) -> None:
    plaintext = app_state.vault_manager.serialize()
    key = app_state.derived_key
    inner = encrypt_vault(plaintext, key)
    full_blob = app_state.encrypted_blob[:16] + inner
    vault_path().write_bytes(full_blob)
    app_state.encrypted_blob = full_blob
