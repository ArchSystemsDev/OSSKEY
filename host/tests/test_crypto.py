import gc
import os

import pytest

from osskey.crypto import (
    NONCE_LEN,
    TAG_LEN,
    WrongPINError,
    decrypt_vault,
    derive_key,
    encrypt_vault,
    zero_key,
)


class TestEncryptDecryptRoundTrip:
    def test_encrypt_then_decrypt_returns_original(self):
        key = derive_key("test-pin-1234", b"\x00" * 16)
        plaintext = b'{"credentials":[{"label":"example.com","username":"alice","password":"s3cret"}]}'
        blob = encrypt_vault(plaintext, key)
        decrypted = decrypt_vault(blob, key)
        assert decrypted == plaintext

    def test_empty_plaintext(self):
        key = derive_key("mypin", b"\x01" * 16)
        blob = encrypt_vault(b"", key)
        decrypted = decrypt_vault(blob, key)
        assert decrypted == b""

    def test_large_plaintext(self):
        key = derive_key("large-test", b"\xab" * 16)
        plaintext = os.urandom(10000)
        blob = encrypt_vault(plaintext, key)
        decrypted = decrypt_vault(blob, key)
        assert decrypted == plaintext


class TestWrongPINError:
    def test_wrong_pin_raises_wrong_pin_error(self):
        key = derive_key("correct-pin", b"\x00" * 16)
        wrong_key = derive_key("wrong-pin", b"\x00" * 16)
        blob = encrypt_vault(b"sensitive data", key)
        with pytest.raises(WrongPINError):
            decrypt_vault(blob, wrong_key)

    def test_tampered_ciphertext_raises_wrong_pin_error(self):
        key = derive_key("my-pin", b"\x00" * 16)
        blob = encrypt_vault(b"important", key)
        tampered = bytearray(blob)
        mid = NONCE_LEN + 5
        tampered[mid] ^= 0xFF
        with pytest.raises(WrongPINError):
            decrypt_vault(bytes(tampered), key)

    def test_tampered_tag_raises_wrong_pin_error(self):
        key = derive_key("pin-123", b"\xaa" * 16)
        blob = bytearray(encrypt_vault(b"test data", key))
        blob[-1] ^= 0x01
        with pytest.raises(WrongPINError):
            decrypt_vault(bytes(blob), key)

    def test_tampered_nonce_raises_wrong_pin_error(self):
        key = derive_key("pin-456", b"\xbb" * 16)
        blob = bytearray(encrypt_vault(b"test data", key))
        blob[0] ^= 0x80
        with pytest.raises(WrongPINError):
            decrypt_vault(bytes(blob), key)


class TestNonceUnique:
    def test_every_encryption_produces_different_nonce(self):
        key = derive_key("fixed-pin", b"\xcc" * 16)
        plaintext = b"same data"
        blob1 = encrypt_vault(plaintext, key)
        blob2 = encrypt_vault(plaintext, key)
        nonce1 = blob1[:NONCE_LEN]
        nonce2 = blob2[:NONCE_LEN]
        assert nonce1 != nonce2, "Nonces must be unique per encryption"


class TestKeyZeroing:
    def test_zero_key_clears_all_bytes(self):
        key = derive_key("test-pin", b"\xee" * 16)
        assert any(b != 0 for b in key), "Key should have non-zero bytes"
        zero_key(key)
        assert all(b == 0 for b in key), "All key bytes must be zero after zero_key"

    def test_zero_key_on_empty_key(self):
        key = bytearray()
        zero_key(key)
        assert len(key) == 0, "Empty key should remain empty"

    def test_derive_key_returns_32_bytes(self):
        from osskey.crypto import KEY_LEN
        key = derive_key("test", b"\xff" * 16)
        assert len(key) == KEY_LEN


class TestEdgeCases:
    def test_blob_too_short_raises_wrong_pin_error(self):
        key = derive_key("pin", b"\x00" * 16)
        with pytest.raises(WrongPINError, match="Blob too short"):
            decrypt_vault(b"", key)

        with pytest.raises(WrongPINError, match="Blob too short"):
            decrypt_vault(b"\x00" * (NONCE_LEN + TAG_LEN - 1), key)

    def test_special_characters_in_pin(self):
        key = derive_key("\u2603!@#$%^&*()_+-=[]{}|;:',.<>?/~`", b"\x12\x34" * 8)
        plaintext = b"data with \x00 unicode \xc3\xa9"
        blob = encrypt_vault(plaintext, key)
        decrypted = decrypt_vault(blob, key)
        assert decrypted == plaintext

    def test_gc_collect_after_key_zeroing(self):
        key = derive_key("test", b"\x00" * 16)
        zero_key(key)
        gc.collect()
        assert all(b == 0 for b in key)
