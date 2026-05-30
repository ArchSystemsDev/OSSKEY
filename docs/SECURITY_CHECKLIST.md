# OSSKEY Security Checklist

This document evaluates every hardening requirement from [`plans/04_security_spec.md`](../plans/04_security_spec.md) against the current codebase. Each item is marked as **IMPLEMENTED**, **PARTIAL**, or **NOT IMPLEMENTED** with location, verification instructions, and risk rating where applicable.

---

## T1: Physical Theft of the Pico

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 1.1 | Vault AES-256 encrypted with PIN-derived key via PBKDF2 | **IMPLEMENTED** | `host/osskey/crypto.py:30-41` — `encrypt_vault()` uses AES-256-GCM with key from `derive_key()` | Call `derive_key("test", salt)`, verify `len(key) == 32`; encrypt and decrypt round-trip | PBKDF2-HMAC-SHA256 with 600,000 iterations |
| 1.2 | PIN never stored on device, only salt + nonce in header | **IMPLEMENTED** | `host/osskey/crypto.py:30-41` — salt is `os.urandom(16)`, stored in blob header; `unlock_view.py:118-127` — only salt+inner written to disk | Search code for any `write(pin)` — none found | PIN exists only in caller's local variable, zeroed after use |
| 1.3 | Flash mounted read-only by default | **IMPLEMENTED** | `firmware/boot.py:4` — `storage.disable_usb_drive()` | Read `boot.py`; verify `storage.disable_usb_drive()` is called | CircuitPython filesystem cannot be mounted as writable USB mass storage |
| 1.4 | RP2350 OTP secure boot signing | **NOT IMPLEMENTED** | — | — | **Risk: HIGH.** No OTP programming, boot signing, or debug interface disabling is configured. The firmware is trivially replaceable. See plans/03_gui_spec.md for OTP instructions. |
| 1.5 | On-device PIN rate limiting with exponential backoff | **NOT IMPLEMENTED** | — | — | **Risk: HIGH.** The device does not track failed decryption attempts or enforce delay. An attacker with serial access can brute-force PINs at full speed. |
| 1.6 | Duress PIN with decoy vault | **NOT IMPLEMENTED** | — | — | **Risk: LOW.** Nice-to-have; most users do not need this. |

---

## T2: Flash Memory Extraction (Chip-Off Attack)

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 2.1 | Vault encrypted with AES-256-GCM, ciphertext indistinguishable from random | **IMPLEMENTED** | `host/osskey/crypto.py:30-41` | Encrypt zeros; run statistical randomness test on output | GCM mode produces random-looking output per NIST SP 800-38D |
| 2.2 | No secret key material on flash | **IMPLEMENTED** | `host/osskey/crypto.py` — key derived at runtime from PIN + salt, never persisted | Search code for `key` being `write()`d — none found | `derived_key` lives in `AppState` RAM only |
| 2.3 | PBKDF2 iteration count >= 600,000 | **IMPLEMENTED** | `host/osskey/crypto.py:12` — `ITERATIONS = 600000` | Verify constant value | Meets OWASP 2024 recommendation for SHA-256 |
| 2.4 | Random nonce per vault write | **IMPLEMENTED** | `host/osskey/crypto.py:32` — `nonce = os.urandom(NONCE_LEN)` | Encrypt same plaintext twice; verify different nonces | GCM nonce reuse would be catastrophic; this is correctly random each time |
| 2.5 | OTP antifuse disable debug interfaces (SWD, UART boot) | **NOT IMPLEMENTED** | — | — | **Risk: CRITICAL.** Debug interfaces remain enabled; an attacker with a $20 probe can dump SRAM after the vault is decrypted in RAM. Requires OTP programming jig. |
| 2.6 | Use Argon2id (preferred over PBKDF2) | **NOT IMPLEMENTED** | — | — | **Risk: MEDIUM.** PBKDF2 is GPU-friendly; Argon2id would be significantly more resistant to offline brute force. Requires C module integration. |

---

## T3: Host Machine Malware Intercepting Serial Traffic

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 3.1 | Vault decryption on-device, not host | **NOT IMPLEMENTED** | `host/osskey/views/unlock_view.py:147-182` — vault is decrypted on the host, not the device | Run app; verify decryption happens in host memory | **Risk: CRITICAL.** The host decrypts the vault using the PIN-derived key. The device is used only for storage and HID injection. |
| 3.2 | Session key / Diffie-Hellman exchange over serial | **NOT IMPLEMENTED** | — | — | **Risk: CRITICAL.** Serial traffic is plaintext with only CRC integrity. Any process with access to the serial port can read credential plaintext during injection. |
| 3.3 | HID injection bypasses host entirely (credential never reaches host as data) | **PARTIAL** | `firmware/hid_inject.py:24-34` — credentials typed from device directly; `host/osskey/views/vault_view.py:157-189` — credential sent over serial as plaintext to device | Code review: the host sends service/username/password as plaintext payload in `CMD_INJECT` | **Risk: HIGH.** The credential travels over USB serial in plaintext during injection. While the window is short, any process reading the serial port can capture it. |
| 3.4 | Command counter to prevent replay attacks | **NOT IMPLEMENTED** | — | — | **Risk: HIGH.** Serial commands have no sequence number. An attacker can replay captured frames. |

---

## T4: Brute Force PIN Attack

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 4.1 | Enforce minimum 8-character PIN | **NOT IMPLEMENTED** | `host/osskey/views/unlock_view.py:99` — minimum is 4 characters | Enter 4-char PIN in unlock view; it is accepted | **Risk: MEDIUM.** 4-character PIN (~10k combinations) is trivially brute-forced offline. Change `len(pin) < 4` to `len(pin) < 8`. |
| 4.2 | PBKDF2 iteration count >= 600,000 for SHA-256 | **IMPLEMENTED** | `host/osskey/crypto.py:12` | See T2.3 | |
| 4.3 | Device-side rate limiting with exponential backoff | **NOT IMPLEMENTED** | — | — | **Risk: HIGH.** See T1.5. |
| 4.4 | Host-side 1-second delay between PIN submissions | **NOT IMPLEMENTED** | `unlock_view.py:105-116` — `_do_action()` has no delay | Click unlock rapidly; no delay enforced | **Risk: MEDIUM.** Client-side only; a modified binary could bypass. |
| 4.5 | PIN stretching with additional SHA-256 round | **NOT IMPLEMENTED** | `derive_key()` returns raw PBKDF2 output | Code review | **Risk: LOW.** Adds minor overhead; not a substitute for iteration count. |

---

## T5: Evil Maid Attack on the Host App Binary

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 5.1 | Host GUI binary code-signed | **NOT IMPLEMENTED** | — | No signing infrastructure exists | **Risk: CRITICAL.** An attacker can replace the GUI binary with a trojaned version. Must be addressed before production release. |
| 5.2 | Detached signature + verification script | **NOT IMPLEMENTED** | — | — | **Risk: MEDIUM.** |
| 5.3 | PIN/encryption key never stored on host | **IMPLEMENTED** | `app_state.py:21-33` — key zeroed on lock; `unlock_view.py` — key exists only in local variable scope | Verify no `write()` call for `derived_key` | Key is in `AppState.derived_key` during unlocked session; zeroed on lock. |
| 5.4 | Integrity self-checks in GUI binary | **NOT IMPLEMENTED** | — | — | **Risk: MEDIUM.** |
| 5.5 | PyInstaller bundle with encrypted bytecode | **NOT IMPLEMENTED** | — | No PyInstaller build exists yet | **Risk: MEDIUM.** See DEV_GUIDE.md for build instructions. |

---

## T6: Man-in-the-Middle on USB Serial

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 6.1 | HMAC-authenticated commands with sequence numbers | **NOT IMPLEMENTED** | — | — | **Risk: CRITICAL.** No authentication, no sequence numbers. Entire protocol is plaintext with CRC integrity only. |
| 6.2 | Session key via ephemeral Diffie-Hellman | **NOT IMPLEMENTED** | — | — | **Risk: CRITICAL.** See T3.2. |
| 6.3 | Challenge-response for injection commands | **NOT IMPLEMENTED** | — | — | **Risk: HIGH.** Any process on the host can send an INJECT command. |
| 6.4 | HID as authoritative output channel | **PARTIAL** | `firmware/hid_inject.py` — credentials typed via HID; `vault_view.py:157-189` — but credentials sent over serial first | Credential flows: host memory → serial (plain) → device RAM → HID. Serial hop is unprotected. | **Risk: HIGH.** |

---

## T7: Cold Boot Attack on Host RAM

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 7.1 | Vault never decrypted on host | **NOT IMPLEMENTED** | `unlock_view.py:147-182` — host decrypts the vault | See T3.1 | **Risk: CRITICAL.** Decrypted vault contents exist in host RAM while the app is unlocked. |
| 7.2 | Credential buffer zeroed after injection | **PARTIAL** | `serial_comms.py:207-210` — `payload` bytearray is zeroed in `finally` block of `inject()`; `vault_view.py` does not zero credential dict entries after use | Code review: `vault_dict` entries contain plaintext passwords indefinitely in RAM | **Risk: HIGH.** Passwords remain in `AppState.vault_dict` as Python strings (immutable, cannot be zeroed) for the entire unlocked session. |
| 7.3 | `bytearray()` used for credentials, not `str` | **NOT IMPLEMENTED** | `vault.py:12-15` — `Credential` stores password as `str` | `password: str = ""` in dataclass; `vault_dict` values are `str` | **Risk: HIGH.** Python strings are immutable; the plaintext password is scattered across RAM and cannot be reliably zeroed. |
| 7.4 | `memoryview` / `ctypes` for credential buffers | **NOT IMPLEMENTED** | All credential handling uses Python `str` | Code review | **Risk: MEDIUM.** |
| 7.5 | `gc.collect()` called after zeroing | **IMPLEMENTED** | `app_state.py:34` — `gc.collect()` in `zero_sensitive()` | Verify `gc.collect()` is called after `zero_key()` | But `zero_key()` is called on the key, not on credential strings. Strings remain unreachable but not zeroed. |

---

## T8: Malicious HID Injection from Another Device

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| 8.1 | Cryptographic challenge-response on serial CDC | **NOT IMPLEMENTED** | — | — | **Risk: CRITICAL.** Any USB device that appears as a serial CDC port and accepts commands could be used for injection. |
| 8.2 | USB VID/PID verification | **PARTIAL** | `serial_comms.py:19-20` — `OSSKEY_VID = 0x2E8A, OSSKEY_PID = 0x000F` — used in `find_device()` | Read `find_device()` | VID/PID check only for device discovery; no ongoing verification. Raspberry Pi VID is not unique. |
| 8.3 | HID authorization token / physical button press | **NOT IMPLEMENTED** | — | — | **Risk: MEDIUM.** |
| 8.4 | Unique product string in HID descriptor | **NOT IMPLEMENTED** | `firmware/boot.py` — no HID descriptor customization | Firmware uses CircuitPython default HID descriptor | **Risk: MEDIUM.** |

---

## 2. Cryptographic Recommendations

| # | Requirement | Status | Location | How to Verify | Notes |
|---|-------------|--------|----------|---------------|-------|
| CRYPTO-1 | PBKDF2-HMAC-SHA256 with 600,000 iterations | **IMPLEMENTED** | `crypto.py:12, 19-27` | Verify `ITERATIONS = 600000`, `hashes.SHA256()` | |
| CRYPTO-2 | Salt length >= 16 bytes | **IMPLEMENTED** | `crypto.py:8,31` — `SALT_LEN = 16`, `os.urandom(SALT_LEN)` | | 16 bytes meets minimum; 32 bytes recommended per spec |
| CRYPTO-3 | New salt on vault re-encryption (PIN change) | **IMPLEMENTED** | `unlock_view.py:216` — `new_kdf_salt = os.urandom(16)`; `settings_view.py:181` — same | Change PIN, examine vault file before/after | |
| CRYPTO-4 | AES-256-GCM for authenticated encryption | **IMPLEMENTED** | `crypto.py:34-41` — `modes.GCM(nonce)` | Code review | |
| CRYPTO-5 | Nonce generated fresh per encryption | **IMPLEMENTED** | `crypto.py:32` — `os.urandom(NONCE_LEN)` | Encrypt same plaintext twice; nonces differ | |
| CRYPTO-6 | GCM tag verification on decrypt | **IMPLEMENTED** | `crypto.py:52-61` — `modes.GCM(nonce, tag)`, exception caught | Tamper ciphertext byte; WrongPINError raised | |
| CRYPTO-7 | Constant-time tag comparison | **NOT IMPLEMENTED** | `crypto.py:57-61` — uses `decryptor.finalize()` from `cryptography` library | Review library source — `cryptography` uses C implementation with constant-time compare | **Risk: LOW.** The `cryptography` library's GCM implementation uses constant-time tag comparison via OpenSSL/BoringSSL. |
| CRYPTO-8 | Key zeroing with byte-by-byte write | **IMPLEMENTED** | `crypto.py:64-66` — `for i in range(len(key)): key[i] = 0` | Call `zero_key()` on a key, verify all bytes are `0` | |
| CRYPTO-9 | `os.urandom` for all randomness (not `random` module) | **IMPLEMENTED** | `crypto.py:1,31-32` — `import os`, `os.urandom()` | Search for `random` module usage in crypto code — none found | |
| CRYPTO-10 | No literal PIN/key in log or stdout | **IMPLEMENTED** | No print/log of sensitive data found | `grep -r "print.*pin\|print.*password\|print.*key"` | |

---

## 4.1 Build Agent Pre-Ship Checks — Vault Module (Pico)

| # | Requirement | Status | Location | Notes |
|---|-------------|--------|----------|-------|
| V-1 | Validate vault header magic/version before reading | **NOT IMPLEMENTED** | `firmware/vault.py` — no header validation; raw blob storage | **Risk: MEDIUM.** The device reads ciphertext without validating format. |
| V-2 | Explicit buffer size checks | **PARTIAL** | `firmware/serial_handler.py:61-88` — `_parse()` checks frame lengths | Payload length field is checked against buffer; no max-size check for vault data. |
| V-3 | PBKDF2 output exactly 32 bytes | **IMPLEMENTED** | `crypto.py:11,22` — `KEY_LEN = 32`, `length=KEY_LEN` | |
| V-4 | Nonce from vault header, not user-controlled | **IMPLEMENTED** | `crypto.py:48` — nonce extracted from blob | |
| V-5 | Tag verified before decrypted data is used | **IMPLEMENTED** | `crypto.py:57-61` — GCM mode verifies tag before returning plaintext | |
| V-6 | Generic error on decryption failure | **IMPLEMENTED** | `crypto.py:61` — `raise WrongPINError("Decryption failed: wrong PIN or corrupted data")` | |
| V-7 | Decryption key zeroed immediately after use | **PARTIAL** | `unlock_view.py:159-160` — key zeroed on WrongPINError; `unlock_view.py:214` — old key zeroed after change | **Risk:** The key remains in `AppState.derived_key` for the entire unlocked session and is only zeroed on lock. Not "immediately." |
| V-8 | On-device PIN attempt counter in flash | **NOT IMPLEMENTED** | — | No rate limiting at all. |
| V-9 | Exponential backoff non-bypassable by power cycle | **NOT IMPLEMENTED** | — | |
| V-10 | USB serial configured as CDC data, not REPL | **IMPLEMENTED** | `firmware/boot.py:6` — `usb_cdc.enable(console=True, data=True)` | Console is still enabled (REPL). Serial data is also enabled. |
| V-11 | USB HID descriptor matches OSSKEY product string | **NOT IMPLEMENTED** | `firmware/boot.py` — no custom HID descriptor | Uses CircuitPython default. |
| V-12 | Unused GPIOs set to high-impedance input | **NOT IMPLEMENTED** | — | |
| V-13 | OTP programming to disable SWD and secure boot | **NOT IMPLEMENTED** | — | **Risk: CRITICAL.** |

---

## 4.1 Build Agent Pre-Ship Checks — Host GUI Module

| # | Requirement | Status | Location | Notes |
|---|-------------|--------|----------|-------|
| H-1 | No credential/PIN/key persisted to disk | **IMPLEMENTED** | `app_state.py` — sensitive data only in RAM; only encrypted vault written to disk | |
| H-2 | No credential logged to stdout/stderr/syslog | **IMPLEMENTED** | No logging framework present in the codebase | |
| H-3 | GUI binary signed | **NOT IMPLEMENTED** | — | |
| H-4 | Serial port opened with exclusive access | **NOT IMPLEMENTED** | `serial_comms.py:112` — `serial.Serial(port, baudrate=BAUDRATE, timeout=self._timeout)` — no `exclusive=True` | **Risk: MEDIUM.** Another process could read the serial port simultaneously. |
| H-5 | HMAC-authenticated serial commands | **NOT IMPLEMENTED** | — | **Risk: CRITICAL.** |
| H-6 | Credential buffer zeroed after injection | **PARTIAL** | `serial_comms.py:207-210` — payload zeroed; `vault_view.py` — does not zero `cdata` after inject | |
| H-7 | Clipboard cleared after configurable timeout | **NOT IMPLEMENTED** | — | **Risk: HIGH.** The app does not interact with the clipboard at all (injection goes directly to HID), so this is not applicable to the current flow. If clipboard copy is added, this must be addressed. |
| H-8 | PIN not sent to Pico over plain serial | **IMPLEMENTED** | PIN is never sent to the device; only encrypted blob and credential plaintext | |
| H-9 | Dependency versions pinned in requirements.txt | **NOT IMPLEMENTED** | `requirements.txt` — no version pins | **Risk: MEDIUM.** `pip install -r requirements.txt` installs latest versions, which could introduce breaking changes or vulnerabilities. |
| H-10 | Static analysis passes (bandit, flake8, mypy) | **NOT IMPLEMENTED** | No CI or lint configuration | **Risk: MEDIUM.** |
| H-11 | `subprocess` calls use absolute paths and argument arrays | **IMPLEMENTED** | No `subprocess` calls exist in the codebase | |

---

## 4.1 Build Agent Pre-Ship Checks — Serial Protocol Module

| # | Requirement | Status | Location | Notes |
|---|-------------|--------|----------|-------|
| S-1 | Sequence number + HMAC tag in every command frame | **NOT IMPLEMENTED** | — | **Risk: CRITICAL.** |
| S-2 | X25519 session key establishment | **NOT IMPLEMENTED** | — | |
| S-3 | Replay window rejects past sequence numbers | **NOT IMPLEMENTED** | — | |
| S-4 | Command response timeout (500 ms) | **PARTIAL** | `serial_comms.py:23` — `DEFAULT_TIMEOUT = 5.0` (5000 ms, not 500 ms) | Spec says 500ms, code uses 5s. |
| S-5 | Strict state machine parser, no buffer over-read | **PARTIAL** | `serial_handler.py:61-88` — parses frame with length checks | The firmware parser checks `len(self._rx) >= total` before reading CRC/ETX. Host parser in `_parse_response()` checks `len(data) < 9`. Both are safe. |
| S-6 | No debug commands or backdoors | **IMPLEMENTED** | Only documented commands are implemented | |

---

## Summary of Critical Gaps

| # | Finding | Risk | Recommended Action |
|---|---------|------|-------------------|
| G1 | Vault decrypted on host (not device) | CRITICAL | Implement on-device decryption: send only the encrypted blob + PIN-derived key to the device for decryption and injection |
| G2 | No serial authentication (no HMAC, no session key, no sequence numbers) | CRITICAL | Implement X25519 session key exchange + HMAC-SHA256 per-command authentication with sequence numbers |
| G3 | No on-device PIN rate limiting | CRITICAL | Implement exponential backoff (1s, 2s, 4s, ..., 1h) after N consecutive failed decryptions, stored in flash |
| G4 | No OTP programming (SWD/debug enabled, no secure boot) | CRITICAL | Program RP2350 OTP to disable SWD, enable secure boot, disable RISC-V fallback core |
| G5 | Minimum PIN length is 4 characters (not 8) | HIGH | Change `len(pin) < 4` to `len(pin) < 8` in `unlock_view.py:99` and `settings_view.py:162` |
| G6 | Credentials stored as Python `str` (immutable, unzeroable) | HIGH | Use `ctypes.create_string_buffer()` or `bytearray` for all credential data; convert Credential model to use mutable buffers |
| G7 | No clipboard clearing | HIGH | Add clipboard clear after configurable timeout (if clipboard features are added in future) |
| G8 | Credentials flow over serial as plaintext | HIGH | Implement session key encryption or eliminate the serial credential hop by having the device decrypt the vault internally |
| G9 | Dependency versions not pinned | MEDIUM | Pin versions in `requirements.txt` (e.g., `cryptography>=41.0.0,<42.0.0`) |
| G10 | Serial port not opened with exclusive access | MEDIUM | Add `exclusive=True` to `serial.Serial()` call in `serial_comms.py:112` |
| G11 | No PyInstaller build or code signing | MEDIUM | Set up CI build pipeline with code signing for release binaries |
| G12 | No static analysis CI | MEDIUM | Add `bandit`, `flake8`, `mypy` config and CI integration |
| G13 | Command timeout is 5s (spec says 500ms) | LOW | Align `DEFAULT_TIMEOUT` in `serial_comms.py:23` with spec if tighter timing is needed |
| G14 | USB REPL console still enabled | LOW | Add `usb_cdc.enable(console=False, data=True)` in `boot.py` to disable the serial REPL |
