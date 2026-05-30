import sys
import unittest.mock

for mod_name in ["usb_cdc", "board", "neopixel", "usb_hid",
                  "adafruit_hid", "adafruit_hid.keyboard",
                  "adafruit_hid.keycode"]:
    sys.modules[mod_name] = unittest.mock.MagicMock()
