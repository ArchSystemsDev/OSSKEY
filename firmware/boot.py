import storage
import usb_cdc

# DEV MODE (default): console=True, USB drive hidden (allows vault writes)
# PRODUCTION MODE: set DEV_MODE = False — disables REPL + USB drive
DEV_MODE = False

if DEV_MODE:
    storage.disable_usb_drive()
    usb_cdc.enable(console=True, data=False)
else:
    storage.disable_usb_drive()
    usb_cdc.enable(console=False, data=True)
