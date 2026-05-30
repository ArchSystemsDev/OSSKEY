"""
autotype.py — Windows autotype for OSSKEY
Minimizes the app, waits for the target window to regain focus,
then types credentials using pynput.
"""

import threading
import time

from pynput.keyboard import Controller, Key


def _type_string(keyboard: Controller, text: str, inter_char_delay: float = 0.012) -> None:
    """Type a string character by character, handling all unicode safely."""
    for char in text:
        keyboard.type(char)
        time.sleep(inter_char_delay)  # small inter-character delay, feels natural


def _execute_safe_autotype(
    keyboard: Controller,
    username: str,
    password: str,
    mode: str,
    press_enter: bool,
) -> None:
    """Helper function that executes the pynput typing sequence safely."""
    try:
        # More robust Alt+Tab sequence with internal spacing to ensure OS registers focus shift
        with keyboard.pressed(Key.alt):
            time.sleep(0.05)
            keyboard.press(Key.tab)
            time.sleep(0.05)
            keyboard.release(Key.tab)
            time.sleep(0.05)

        time.sleep(0.5)  # Focus hand-off buffer to ensure the target window is active

        if mode == "username":
            _type_string(keyboard, username)
        elif mode == "password":
            _type_string(keyboard, password)
        elif mode == "both":
            _type_string(keyboard, username)
            time.sleep(0.12)  # Give the OS time to catch up
            keyboard.press(Key.tab)
            keyboard.release(Key.tab)
            time.sleep(0.12)  # Give the target window time to change inputs
            _type_string(keyboard, password)
            if press_enter:
                time.sleep(0.12)
                keyboard.press(Key.enter)
                keyboard.release(Key.enter)
    except Exception:
        pass  # never crash the app from a background thread



def autotype(
    root,
    username: str = "",
    password: str = "",
    mode: str = "both",
    delay_ms: int = 400,
    press_enter: bool = False,
) -> None:
    """
    Executes the autotype sequence in a background thread to prevent
    blocking the GUI main loop.
    """
    def worker_wrapper():
        try:
            # Initialize controller inside the thread for better OS hook stability
            keyboard = Controller()
            time.sleep(delay_ms / 1000.0)
            _execute_safe_autotype(keyboard, username, password, mode, press_enter)
        except Exception:
            pass

    t = threading.Thread(target=worker_wrapper, daemon=True)
    t.start()
