# OSSKEY User Guide

## What OSSKEY Is

OSSKEY is a **hardware password vault** built on a Waveshare RP2350-One microcontroller. It stores your credentials encrypted (AES-256-GCM) on the device's flash and types them into any computer via USB HID (keyboard emulation). The host GUI lets you manage credentials and push them to the device, but all sensitive data is encrypted with a master PIN that only you know.

### What OSSKEY Is NOT

- **Not a cloud service** — credentials never leave your possession.
- **Not a password manager that autofills in the browser** — credentials are typed as keystrokes from a USB keyboard.
- **Not a cross-device sync service** — the vault lives on one device at a time. You can export the encrypted blob for backup, but there is no automatic cloud sync.
- **Not resistant to physical extraction without a PIN** — encryption is strong, but an attacker with the device and unlimited resources could brute-force a weak PIN.

---

## First-Time Setup

### 1. Flash CircuitPython 9.x to the RP2350-One

Follow the detailed instructions in [`firmware/FLASH_INSTRUCTIONS.md`](firmware/FLASH_INSTRUCTIONS.md).

In short:

1. Put the RP2350-One into bootloader mode (hold BOOT while plugging into USB).
2. Copy `circuitpython-9.x.uf2` to the `RPI-RP2` drive that appears.
3. The device reboots and mounts as `CIRCUITPY`.

### 2. Copy Firmware Files

1. Unzip `firmware_v1.0.0.zip`.
2. Copy all files from the `firmware_release/` folder to the `CIRCUITPY` drive:

```
firmware_release/
  boot.py
  code.py
  aes.py
  hid_inject.py
  led.py
  serial_handler.py
  vault.py
  lib/
    adafruit_hid/
    neopixel/
```

Create a `lib/` folder on `CIRCUITPY` if it does not exist and copy the `adafruit_hid` and `neopixel` libraries there.

### 3. Install the Host Application

#### Option A: Run the Pre-built Executable (Recommended for Windows)
1. Navigate to `host/dist/`.
2. Run `osskey.exe`. No installation or Python environment is required.

#### Option B: Run from Source (Cross-platform)
**Requirements:** Python 3.10+.

The GUI opens to a lock screen. If no vault file exists yet, you will see **"CREATE VAULT"**.

### 4. Create Your Vault

1. Enter a **master PIN** (8+ characters recommended; 4–32 allowed).
2. Click **"CREATE VAULT"**.
3. The vault is created encrypted on disk at:
   - Windows: `%APPDATA%\OSSKEY\vault.enc`
   - Linux/macOS: `~/.local/share/osskey/vault.enc`

---

## How to Add Credentials

1. Unlock the app with your PIN.
2. Click **"+ ADD"** in the vault view.
3. Enter the **Label** (e.g., `github.com`), **Username**, and **Password**.
4. Click **"Save"**.

The credential is stored in-memory and written to the encrypted vault file on disk.

To edit: click the **"Edit"** button next to a credential row.

To delete: click **"Del"** and confirm.

---

## How to Push to Device

1. Make sure the OSSKEY device is plugged into USB.
2. The device status indicator in the top bar should show **"Ready"** (green).
3. The vault is automatically encrypted and pushed when you save changes. To manually re-push, any save/edit operation in the vault view triggers a write to the encrypted file on disk and the device.

When you plug in the device, the host pushes the vault blob to the device via `CMD_PUT_VAULT`. The device stores it in flash as `vault.bin`.

---

## How to Inject a Password

1. Unlock the app and have the device connected and ready.
2. Place your cursor in the target field (username or password) on the computer you want to log into.
3. In the OSSKEY GUI, click **"Inject"** next to the credential you want to use.
4. Move your cursor to the target field within 1–2 seconds.
5. The device types the username, presses Tab, types the password, and presses Enter.

**Tip:** Practice with a text editor first to get used to the timing.

---

## If You Forget Your PIN

**OSSKEY cannot recover your PIN.** There is no backdoor, no reset question, no email recovery.

- If you have the vault file (encrypted on disk), it is permanently inaccessible without the correct PIN.
- You can **reset the device** by wiping the vault and creating a new one with a new PIN.
- The KDF salt is stored alongside the encrypted vault. Even if you have the salt, you still need the PIN.
- If you lose both the PIN and the device, all credentials are lost. Rotate every credential stored in the vault.

**To wipe and start over:**

```bash
# Delete the vault file on the host
rm %APPDATA%\OSSKEY\vault.enc   # Windows
rm ~/.local/share/osskey/vault.enc  # Linux/macOS
```

Then launch the GUI again — you will see **"CREATE VAULT"**.

To reset the device firmware, re-flash CircuitPython (see flash instructions).

---

## If the Device Is Lost or Stolen

1. **Do not panic.** The vault is encrypted with AES-256-GCM. Without the PIN, an attacker cannot read the contents.
2. **Begin rotating every credential** that was stored in the lost vault as soon as possible. Assume the attacker may eventually crack the PIN or discover a vulnerability.
3. **If you have a backup** of the encrypted vault file, you can restore it to a replacement device.
4. **Order a replacement device** and set it up with a new PIN. Do not reuse the old PIN.
5. **Report the loss** to your organization's security team if this is a corporate-managed device.

Even if the device is recovered, assume it has been compromised. Wipe it and re-initialize with a new PIN.

---

## Security Recommendations for Daily Use

### PIN Hygiene

- **Minimum 8 characters** — use 12+ for strong protection.
- Mix uppercase, lowercase, digits, and symbols (e.g., `k8#mP9$xL2@q`).
- Do **not** use dictionary words, dates, keyboard patterns, or personal information.
- Do **not** use the same PIN for OSSKEY that you use for any other service.
- Do **not** type your PIN where cameras or bystanders can see it.

### Physical Security

- **Lock your workstation** before plugging in or unplugging the OSSKEY device.
- Do **not** leave the device unattended.
- Do **not** plug the device into USB ports you do not physically control.
- Consider carrying the device on your person (keychain, Faraday bag).
- Use full-disk encryption on the host machine (BitLocker, FileVault, LUKS).
- Keep a spare device with an identical vault in a secure secondary location.

### Operational Security

- Always lock the app when you step away from your computer.
- Enable auto-lock (Settings → Inactivity Lock) with a short timeout (1–5 minutes).
- Do not update firmware from unofficial sources.
- Periodically back up the encrypted vault file via **Settings → Export Encrypted Vault**.
- Store the encrypted backup in a separate secure location (encrypted USB drive, safe).

### If You Suspect Compromise

- Change your PIN immediately.
- Re-encrypt the vault (PIN change automatically re-encrypts with a new salt).
- Rotate all credentials stored in the vault.
- If the device was physically out of your control, discard it and use a replacement.
