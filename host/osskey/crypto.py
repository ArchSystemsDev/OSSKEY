import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
KEY_LEN = 32
ITERATIONS = 600000


class WrongPINError(Exception):
    pass


def derive_key(pin: str, salt: bytes) -> bytearray:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend(),
    )
    return bytearray(kdf.derive(pin.encode("utf-8")))


def encrypt_vault(plaintext: bytes, key: bytearray) -> bytes:
    nonce = os.urandom(NONCE_LEN)
    key_bytes = bytes(key)
    cipher = Cipher(
        algorithms.AES(key_bytes),
        modes.GCM(nonce),
        backend=default_backend(),
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return nonce + ciphertext + encryptor.tag


def decrypt_vault(blob: bytes, key: bytearray) -> bytes:
    if len(blob) < NONCE_LEN + TAG_LEN:
        raise WrongPINError("Blob too short")
    nonce = blob[:NONCE_LEN]
    tag = blob[-TAG_LEN:]
    ciphertext = blob[NONCE_LEN:-TAG_LEN]
    key_bytes = bytes(key)
    cipher = Cipher(
        algorithms.AES(key_bytes),
        modes.GCM(nonce, tag),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()
    try:
        return decryptor.update(ciphertext) + decryptor.finalize()
    except Exception:
        raise WrongPINError("Decryption failed: wrong PIN or corrupted data") from None


def zero_key(key: bytearray) -> None:
    for i in range(len(key)):
        key[i] = 0
