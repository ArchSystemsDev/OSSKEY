# OSSKEY Developer Guide

## Repository Structure

```
OSSKEY/
├── docs/
│   ├── USER_GUIDE.md
│   ├── DEV_GUIDE.md
│   └── SECURITY_CHECKLIST.md
├── firmware/
│   ├── boot.py              # Disables USB drive, enables CDC serial + HID
│   ├── code.py              # Main state machine (IDLE→RECEIVING→READY→INJECTING→ERROR)
│   ├── hid_inject.py        # HID keyboard typing engine
│   ├── led.py               # NeoPixel WS2812B status LEDs
│   ├── serial_handler.py    # Serial framing, CRC-32, ACK/NAK responses
│   ├── vault.py             # Flash vault read/write/erase with atomic rename
│   └── FLASH_INSTRUCTIONS.md
├── host/
│   ├── main.py              # Entry point — launches the CustomTkinter GUI
│   ├── requirements.txt     # Python dependencies
│   ├── osskey/
│   │   ├── app.py           # Main App class — builds GUI, polls device
│   │   ├── app_state.py     # AppState dataclass (LOCKED/UNLOCKED, vault, key)
│   │   ├── config.py        # OS-appropriate paths for vault/settings files
│   │   ├── crypto.py        # derive_key, encrypt_vault, decrypt_vault, zero_key
│   │   ├── inactivity.py    # InactivityTimer — auto-lock on idle timeout
│   │   ├── serial_comms.py  # SerialComms — framed binary protocol, find_device
│   │   ├── vault.py         # VaultManager — Credential CRUD, serialize/deserialize
│   │   ├── __init__.py
│   │   └── views/
│   │       ├── __init__.py
│   │       ├── device_status.py       # Top-bar device status indicator
│   │       ├── dialogs.py             # confirm_dialog, message_dialog
│   │       ├── edit_credential_view.py # Add/Edit credential form
│   │       ├── settings_view.py       # PIN change, timeout, export, about
│   │       ├── unlock_view.py         # PIN entry, vault creation
│   │       └── vault_view.py          # Credential list, search, inject
│   └── tests/
│       ├── __init__.py
│       ├── test_crypto.py        # AES-GCM round trip, wrong PIN, key zeroing
│       ├── test_protocol.py      # Frame building, parsing, timeout, retry
│       ├── test_vault.py         # VaultManager CRUD, serialize/deserialize
│       └── test_integration.py   # End-to-end flows with mocked serial
├── plans/
│   ├── 01_architecture.md
│   ├── 02_firmware_spec.md
│   ├── 03_gui_spec.md
│   └── 04_security_spec.md
```

---

## How to Run Tests

### Prerequisites

```bash
cd host/
python -m venv venv
venv\Scripts\activate   # Windows
# or: source venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
pip install pytest
```

### Running All Tests

```bash
cd host/
python -m pytest tests/ -v
```

### Running a Specific Test File

```bash
python -m pytest tests/test_crypto.py -v
python -m pytest tests/test_protocol.py -v
python -m pytest tests/test_vault.py -v
python -m pytest tests/test_integration.py -v
```

### Running a Specific Test Class or Function

```bash
python -m pytest tests/test_crypto.py::TestEncryptDecryptRoundTrip -v
python -m pytest tests/test_crypto.py::TestWrongPINError::test_wrong_pin_raises_wrong_pin_error -v
```

### Test Output

Tests should all pass. Integration tests mock the serial layer so no physical hardware is required.

---

## How to Modify the Serial Protocol

The serial protocol is defined in two files that must be kept in sync:

| Role | File |
|------|------|
| Host framing + parsing | `host/osskey/serial_comms.py` |
| Device framing + parsing | `firmware/serial_handler.py` |

### Frame Format

```
Offset  Size  Field
0       1     STX (0x02)
1       1     FLAGS (0 = reserved)
2       2     Payload length (LE uint16)
4       1     Command opcode
5       N     Payload
5+N     4     CRC-32C of bytes 1..(4+N) (LE uint32)
5+N+4   1     ETX (0x03)
```

### Adding a New Command

1. Add the command opcode constant to both `serial_comms.py` and `serial_handler.py`.
2. Add a command handler in `firmware/code.py` main state machine loop.
3. Add a public method or update `send_command()` in `host/osskey/serial_comms.py`.
4. Add a test case in `tests/test_protocol.py` for the new command framing.
5. Add an integration test in `tests/test_integration.py`.

### Command Opcodes (Host → Device)

```
0x01  CMD_PING          No payload
0x02  CMD_PUT_VAULT     Encrypted vault blob
0x03  CMD_INJECT        1-byte index + 3 null-terminated strings
0x04  CMD_LOCK          No payload (device wipes session state)
0x05  CMD_WIPE          No payload (device erases vault from flash)
```

### Response Opcodes (Device → Host)

```
0x81  RSP_ACK           Success
0x82  RSP_NAK           Error with error code byte payload
```

### Important

- The CRC computation must match on both sides. The host uses `crc32c` library (CRC-32C). The device uses a software CRC-32 (Castagnoli polynomial) implementation in `serial_handler.py`.
- The minimum frame is 10 bytes (zero-length payload).
- The host retries up to 3 times on timeout before raising `DeviceTimeout`.
- Currently the protocol uses a simple framing with CRC but **no sequence numbers, no session keys, and no HMAC** (see Security Checklist for what remains to be implemented).

---

## How to Add Support for a New OS

The host application is a Python/CustomTkinter GUI that runs on any OS with Python 3.10+.

### Host OS Support

The host should work on Windows, macOS, and Linux without modification because it uses `pyserial` for serial and `customtkinter` (tkinter) for the GUI.

The only OS-specific code is in `host/osskey/config.py`:

```python
def _data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "OSSKEY"
    return Path.home() / ".local" / "share" / "osskey"
```

To add a new OS (e.g., FreeBSD): add an `elif` branch for the appropriate config path.

### Firmware (Device) OS

The firmware runs on the RP2350-One and does not need OS-specific code. The HID injection engine uses a US keyboard layout. To add a new keyboard layout:

1. Create a new lookup table in `firmware/hid_inject.py` (or a new file) for the target layout.
2. Add a command or configuration switch to select the layout.
3. Update the injection path in `code.py` to use the selected layout.

---

## How to Build Release Binaries with PyInstaller

### Windows

```bash
cd host/
pip install pyinstaller
pyinstaller --onefile --windowed --name osskey --icon assets/icon.ico main.py
```

The binary will be in `dist/osskey.exe`.

### macOS

```bash
cd host/
pip install pyinstaller
pyinstaller --onefile --windowed --name osskey --icon assets/icon.icns main.py
```

The binary will be in `dist/osskey.app`.

### Linux

```bash
cd host/
pip install pyinstaller
pyinstaller --onefile --windowed --name osskey main.py
```

The binary will be in `dist/osskey`.

### All Platforms

- Add `--add-data "osskey/views:osskey/views"` if assets are needed.
- Use `--hidden-import` for any module that PyInstaller might miss (e.g., `crc32c`, `serial`, `customtkinter`).
- Sign the binary after building (see Security Checklist, Section 4.1 Host GUI).
- Verify that `exclusive=True` is set on the serial port open (if implemented) to prevent other processes from accessing the device.

### Verification

```bash
# Check that the binary starts without errors
./dist/osskey --help

# Check that all imports resolve
python -c "import osskey.crypto; import osskey.serial_comms; import osskey.vault; print('OK')"
```
