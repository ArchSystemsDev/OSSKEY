import neopixel
import board
import time
import math


def _release_pin(pin):
    """Force-release a pin if it's claimed from a previous run."""
    try:
        import digitalio
        p = digitalio.DigitalInOut(pin)
        p.deinit()
    except Exception:
        pass


class LEDController:
    IDLE       = 0
    CONNECTED  = 1
    VAULT_LOAD = 2
    READY      = 3
    INJECTING  = 4
    ERROR      = 5

    def __init__(self, pin=board.GP16, count=1, brightness=0.3):
        _release_pin(pin)
        self.np = neopixel.NeoPixel(pin, count, brightness=brightness, auto_write=False)
        self.mode = self.IDLE
        self._anim_start = 0.0
        self._breathe_t0 = 0.0
        self._last_phase = 0
        self._blink_on = False

    def set_mode(self, mode):
        now = time.monotonic()
        self.mode = mode
        self._anim_start = now
        self._blink_on = False
        if mode == self.IDLE:
            self._breathe_t0 = now
        elif mode == self.ERROR:
            self._last_phase = 0

    def update(self):
        now = time.monotonic()
        dt = now - self._anim_start

        if self.mode == self.IDLE:
            elapsed = now - self._breathe_t0
            t = elapsed * 2.0 * math.pi / 3.0
            b = (math.sin(t) + 1.0) / 2.0
            v = int(b * 80)
            self.np.fill((0, v, 0))
            self.np.show()

        elif self.mode == self.CONNECTED:
            self.np.fill((0, 0, 128))
            self.np.show()

        elif self.mode == self.VAULT_LOAD:
            if dt < 0.12:
                self.np.fill((0, 100, 100))
            else:
                self.np.fill((0, 0, 0))
            self.np.show()

        elif self.mode == self.READY:
            self.np.fill((0, 128, 0))
            self.np.show()

        elif self.mode == self.INJECTING:
            phase = int(dt / 0.1)
            if phase % 2 == 0:
                self.np.fill((128, 128, 128))
            else:
                self.np.fill((0, 0, 0))
            self.np.show()

        elif self.mode == self.ERROR:
            cycle = 0.6
            total = 3.0 * cycle
            if dt < total:
                phase = dt % cycle
                if phase < 0.3:
                    self.np.fill((128, 0, 0))
                else:
                    self.np.fill((0, 0, 0))
            else:
                self.np.fill((0, 0, 0))
            self.np.show()

    def off(self):
        self.np.fill((0, 0, 0))
        self.np.show()
