# OSSKEY - Open Source Hardware Security Key

OSSKEY is a high-security hardware credential vault built on the Waveshare RP2350-One. It stores your passwords encrypted with AES-256-GCM and injects them via USB HID (keyboard emulation) for maximum compatibility.

## 🚀 Quick Start (Release v1.0.0)

### 1. Flash the Hardware
1. Download `firmware_v1.0.0.zip`.
2. Follow the [Flash Instructions](firmware/FLASH_INSTRUCTIONS.md) to install CircuitPython and copy the OSSKEY firmware to your RP2350-One.

### 2. Run the GUI
1. Go to `host/dist/osskey.exe`.
2. Run the application (no installation required).
3. Create your master PIN and start adding credentials.

## 📁 Repository Structure
- `firmware/`: CircuitPython source code for the RP2350-One.
- `host/`: Python/CustomTkinter source code for the cross-platform GUI.
- `docs/`: Detailed user and developer documentation.
- `firmware_v1.0.0.zip`: Production-ready firmware package.
- `host/dist/osskey.exe`: Standalone Windows executable.

## 📖 Documentation
- [User Guide](docs/USER_GUIDE.md): How to use the vault, manage credentials, and security best practices.
- [Flash Instructions](firmware/FLASH_INSTRUCTIONS.md): How to set up your hardware.
- [Developer Guide](docs/DEV_GUIDE.md): How to build from source and contribute.

## 🔒 Security
OSSKEY uses industry-standard AES-256-GCM encryption. All sensitive data is zeroed in RAM immediately after use. Your master PIN never leaves the host application and is never stored on the hardware device.

---
*OSSKEY is an open-source project. Use at your own risk.*
