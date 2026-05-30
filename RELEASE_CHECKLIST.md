# OSSKEY Release Checklist

## 1. Hardware & Firmware Verification
- [ ] **Fresh Flash Test**: Reformat the RP2350-One flash, install CircuitPython 9.x/10.x, and copy production `boot.py` and `code.py`.
- [ ] **PUT_VAULT Stability**: Perform 5 consecutive vault saves with varying sizes (1KB to 10KB) to ensure the filesystem corruption issues from earlier builds are fully resolved by `dsrdtr=False`.
- [ ] **LED Status Audit**: Verify NeoPixel colors match the `LEDController` states (Idle, Ready, Injecting, Error).
- [ ] **PID Check**: Confirm `serial_comms.py` auto-detects the device on both USB 2.0 and USB 3.0 ports.

## 2. Host Application Validation
- [ ] **Clipboard Timeout**: Manually verify the clipboard clears exactly 30 seconds after an injection or copy operation.
- [ ] **Inactivity Lock**: Set the timeout to 1 minute in Settings and ensure the app returns to the `UnlockView` and zeroes the key in RAM.
- [ ] **Navigation Guard**: Confirm "Lock" and "Settings" buttons are visually disabled and unclickable when the vault is in the `LOCKED` state.
- [ ] **Fresh Install Flow**: Delete `%APPDATA%\OSSKEY\vault.enc` and ensure the app starts at the "Create Vault" screen rather than crashing.

## 3. Security Check (04_security_spec.md Alignment)
- [ ] **Key Erasure**: Verify `zero_key` is called in `app.py` `on_close()` and `crypto.py` logic.
- [ ] **Entropy Check**: Ensure `os.urandom(12)` is providing unique nonces for every injection attempt in `serial_comms.py`.
- [ ] **Duress/Wipe**: Test the `WIPE` command from the host to ensure `vault.bin` is physically removed from the device.

## 4. Packaging & Distribution
- [ ] **PyInstaller Build**: Run `pyinstaller --noconsole --onefile main.py`.
- [ ] **Resource Paths**: Run the resulting `.exe` and verify it correctly locates the user settings and vault file (should resolve to `%APPDATA%`, not the temp directory).
- [ ] **Dependency Audit**: Ensure `requirements.txt` is up to date and that `pynput` is properly bundled (some versions require hidden imports in PyInstaller).

## 5. Documentation
- [ ] **User Guide**: Update `USER_GUIDE.md` with instructions on how to recover if the device shows a "GP29 in use" error (singleton reset).
- [ ] **Git Cleanup**: Final check that `.gitignore` is catching `debug.txt`, `crash.txt`, and the `osskey-backup/` folder.