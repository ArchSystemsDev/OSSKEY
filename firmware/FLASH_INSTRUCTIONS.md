# Flashing CircuitPython to Waveshare RP2350-One

> **Note for Release Users:** If you downloaded `firmware_v1.0.0.zip`, use the files in that archive for Step 3.

## Prerequisites

- **Waveshare RP2350-One** board
- **USB-C cable** (data-capable, not charge-only)
- **CircuitPython 9.x UF2 file** for RP2350 — download from [circuitpython.org](https://circuitpython.org/board/waveshare_rp2350_one/)
- **OSSKEY firmware files** from the `firmware/` directory

---

## Step 1: Enter Bootloader Mode

1. Unplug the RP2350-One from USB.
2. Press and hold the **BOOT** button (the small button on the board, near the USB connector).
3. While holding BOOT, plug the board into your computer via USB-C.
4. Continue holding BOOT for about 2 seconds, then release.
5. A mass storage drive called **`RPI-RP2`** should appear on your computer.

**Troubleshooting:**
- If `RPI-RP2` does not appear, try a different USB cable (some cables are charge-only).
- On Windows, check Device Manager for "RP2 Boot" under "Ports (COM & LPT)" or "Universal Serial Bus devices."
- If the board was previously flashed with CircuitPython, double-tap the **RST** button to enter bootloader mode (quick double-press of the reset button).

---

## Step 2: Flash CircuitPython

1. Download the **CircuitPython 9.x UF2** file for `Waveshare RP2350-One` from circuitpython.org.
   - Look for: `adafruit-circuitpython-waveshare_rp2350_one-en_US-9.x.x.uf2`
2. Copy (drag and drop) the `.uf2` file onto the `RPI-RP2` drive.
3. The drive will disappear and the board will reboot automatically.
4. A new drive called **`CIRCUITPY`** should appear. This is the device's writable filesystem.

**Verify:**
- `CIRCUITPY` drive is visible in your file explorer.
- The drive contains `boot_out.txt` with CircuitPython version info.
- The on-board NeoPixel (if any) may blink or remain off — this is normal until OSSKEY firmware is copied.

---

## Step 3: Copy Firmware Files

1. Open the `CIRCUITPY` drive.
2. Copy the following files from the `firmware/` directory to the root of `CIRCUITPY`:

```
firmware/
├── boot.py          →  /CIRCUITPY/boot.py
├── code.py          →  /CIRCUITPY/code.py
├── hid_inject.py    →  /CIRCUITPY/hid_inject.py
├── led.py           →  /CIRCUITPY/led.py
├── serial_handler.py→  /CIRCUITPY/serial_handler.py
└── vault.py         →  /CIRCUITPY/vault.py
```

3. Create a `lib/` directory on `CIRCUITPY` (if it doesn't already exist).
4. Copy the required CircuitPython libraries into `lib/`:

Required libraries (download from [circuitpython.org/libraries](https://circuitpython.org/libraries) — get the "Bundle for Version 9.x"):

```
adafruit_hid/       →  /CIRCUITPY/lib/adafruit_hid/
neopixel.mpy        →  /CIRCUITPY/lib/neopixel.mpy
```

The `adafruit_hid` folder should contain at minimum:
- `__init__.mpy`
- `keyboard.mpy`
- `keycode.mpy`
- `keyboard_layout_us.mpy`

5. Safely eject the `CIRCUITPY` drive.

---

## Step 4: Verify the Device Is Working

After copying the firmware and ejecting `CIRCUITPY`, the board will reset and begin running `code.py`.

### LED Pattern Verification

| LED Pattern | Meaning | How to Test |
|------------|---------|-------------|
| **Slow pulsing green** (breathing) | **IDLE** — waiting for serial connection | Plug in the board. The LED should start pulsing green within 2 seconds. |
| **Solid blue** | **CONNECTED** — serial link established | Connect the OSSKEY host app to the device. The host sends a `CMD_PING` and the device responds. |
| **Solid green** | **READY** — vault present on device | Push a vault from the host app. The LED blinks cyan briefly, then turns solid green. |
| **Fast blinking cyan** | **INJECTING** — typing credential | Click "Inject" in the host app for any credential. The LED blinks cyan during injection. |
| **Fast blinking red** | **ERROR** — something went wrong | If the LED goes red, unplug and re-plug the device. Check the serial connection. |

### Quick Serial Test (without host app)

Use a serial terminal (PuTTY, screen, or `serial.tools.miniterm`) to verify the device responds:

```
Port:        (the COM port reported by the device, e.g., COM5 on Windows)
Baud rate:   115200
Data bits:   8
Parity:      None
Stop bits:   1
Flow control: None
```

Send a PING command (hex):

```
02 00 00 00 01 1D CB 6E F7 03
```

The device should respond with a valid ACK frame. If the device responds, the firmware is working.

---

## Troubleshooting

### `CIRCUITPY` does not appear after flashing

- Re-enter bootloader mode and re-flash the UF2 file.
- The `boot.py` file disables the USB mass storage drive (`storage.disable_usb_drive()`). If you need to modify firmware files after the initial copy:
  1. Re-enter bootloader mode (BOOT + plug in).
  2. Flash CircuitPython again (this wipes the board clean).
  3. Copy firmware files again.
  - Alternatively, temporarily comment out `storage.disable_usb_drive()` in `boot.py`, copy files, then uncomment.

### "HID device not recognized" on Windows

- The device enumerates as a composite device (CDC + HID). Windows may need a driver.
- On Windows 10/11, the HID driver should install automatically. Check Device Manager under "Human Interface Devices" for "USB Input Device."

### Serial port not found

- Run `python -m serial.tools.list_ports -v` on the host.
- Look for "USB Serial Device" with VID `2E8A` and PID `000F`.
- If no serial port appears, the `boot.py` may not be enabling CDC: verify `usb_cdc.enable(console=True, data=True)` is in `boot.py`.

### LED does not light up

- The NeoPixel on RP2350-One is on **GP29**. Verify `led.py` pin configuration matches.
- Check wiring: RP2350-One uses GPIO29 for the on-board WS2812.

---

## Updating Firmware

To update the firmware:

1. Enter bootloader mode (BOOT + plug in) — this erases the existing firmware.
2. Flash the new CircuitPython UF2 if upgrading CircuitPython version.
3. Copy all firmware files again (`boot.py`, `code.py`, etc.).
4. Copy library files again (`adafruit_hid/`, `neopixel.mpy`).
5. Push the vault from the host app after the update.

**Note:** The vault on the device's internal flash (`/vault.bin`) is lost when re-flashing CircuitPython. You must re-push the vault from the host app after a firmware update.

---

## Library Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `adafruit_hid` | >= 6.0 | USB HID keyboard reports |
| `neopixel` (built-in `pixelio`) | — | WS2812B NeoPixel LED control |

These are available in the Adafruit CircuitPython Bundle 9.x from:
https://circuitpython.org/libraries
