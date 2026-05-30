import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location("aes", os.path.join(FW, "aes.py"))
aes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aes)
aes_gcm_decrypt = aes.aes_gcm_decrypt
aes_mac = aes.aes_mac

import os as _os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM


def _encrypt(key, plaintext):
    nonce = _os.urandom(12)
    aesgcm = _AESGCM(key)
    ct_tag = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ct_tag[:-16], ct_tag[-16:]


def test_decrypt_hello_world():
    key = _os.urandom(32)
    nonce, ct, tag = _encrypt(key, b"Hello, World!")
    result = aes_gcm_decrypt(key, nonce, ct, tag)
    assert result == b"Hello, World!"


def test_decrypt_unicode():
    key = _os.urandom(32)
    plaintext = "hello\u2603world".encode("utf-8")
    nonce, ct, tag = _encrypt(key, plaintext)
    result = aes_gcm_decrypt(key, nonce, ct, tag)
    assert result == plaintext


def test_decrypt_empty():
    key = _os.urandom(32)
    nonce, ct, tag = _encrypt(key, b"")
    result = aes_gcm_decrypt(key, nonce, ct, tag)
    assert result == b""


def test_decrypt_large():
    key = _os.urandom(32)
    plaintext = b"x" * 4096
    nonce, ct, tag = _encrypt(key, plaintext)
    result = aes_gcm_decrypt(key, nonce, ct, tag)
    assert result == plaintext


def test_decrypt_binary():
    key = _os.urandom(32)
    plaintext = bytes(range(256))
    nonce, ct, tag = _encrypt(key, plaintext)
    result = aes_gcm_decrypt(key, nonce, ct, tag)
    assert result == plaintext


def test_decrypt_wrong_key():
    key = _os.urandom(32)
    nonce, ct, tag = _encrypt(key, b"secret data")
    result = aes_gcm_decrypt(_os.urandom(32), nonce, ct, tag)
    assert result is None


def test_decrypt_tampered_ct():
    key = _os.urandom(32)
    nonce, ct, tag = _encrypt(key, b"secret data")
    ct = bytearray(ct)
    ct[0] ^= 1
    result = aes_gcm_decrypt(key, nonce, bytes(ct), tag)
    assert result is None


def test_decrypt_tampered_tag():
    key = _os.urandom(32)
    nonce, ct, tag = _encrypt(key, b"secret data")
    tag = bytearray(tag)
    tag[0] ^= 1
    result = aes_gcm_decrypt(key, nonce, ct, bytes(tag))
    assert result is None


def test_decrypt_invalid_key():
    assert aes_gcm_decrypt(b"", b"\x00" * 12, b"abc", b"\x00" * 16) is None
    assert aes_gcm_decrypt(b"\x00" * 32, b"\x00" * 13, b"abc", b"\x00" * 16) is None
    assert aes_gcm_decrypt(b"\x00" * 32, b"\x00" * 12, b"abc", b"\x00" * 15) is None


def test_decrypt_aad():
    key = _os.urandom(32)
    nonce = _os.urandom(12)
    aesgcm = _AESGCM(key)
    ct_tag = aesgcm.encrypt(nonce, b"data", b"aad")
    result = aes_gcm_decrypt(key, nonce, ct_tag[:-16], ct_tag[-16:], aad=b"aad")
    assert result == b"data"


def test_decrypt_wrong_aad():
    key = _os.urandom(32)
    nonce = _os.urandom(12)
    aesgcm = _AESGCM(key)
    ct_tag = aesgcm.encrypt(nonce, b"data", b"correct_aad")
    result = aes_gcm_decrypt(key, nonce, ct_tag[:-16], ct_tag[-16:], aad=b"wrong_aad")
    assert result is None


def test_decrypt_many():
    key = _os.urandom(32)
    for i in range(20):
        pt = _os.urandom(i * 17)
        nonce, ct, tag = _encrypt(key, pt)
        assert aes_gcm_decrypt(key, nonce, ct, tag) == pt


def test_mac_empty():
    key = b"\x00" * 32
    tag = aes_mac(key, b"")
    assert tag is not None and len(tag) == 4


def test_mac_same():
    key = _os.urandom(32)
    assert aes_mac(key, b"hello") == aes_mac(key, b"hello")


def test_mac_different_key():
    k1 = _os.urandom(32)
    k2 = _os.urandom(32)
    assert aes_mac(k1, b"data") != aes_mac(k2, b"data")


def test_mac_different_data():
    key = _os.urandom(32)
    assert aes_mac(key, b"data1") != aes_mac(key, b"data2")


def test_mac_invalid_key():
    assert aes_mac(b"", b"data") is None


def test_mac_matches_host():
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    key = _os.urandom(32)
    data = _os.urandom(100)
    ecb = Cipher(algorithms.AES256(key), modes.ECB())
    enc = ecb.encryptor()
    x = bytes(16)
    for i in range(0, len(data), 16):
        block = data[i:i + 16]
        if len(block) < 16:
            block = block + b"\x80" + b"\x00" * (15 - len(block))
        xored = bytes(a ^ b for a, b in zip(x, block))
        x = enc.update(xored)
    enc.finalize()
    expected = x[:4]
    assert aes_mac(key, data) == expected


def test_mac_empty_all_zeros():
    key = _os.urandom(32)
    assert aes_mac(key, b"") == b"\x00\x00\x00\x00"
