import contextlib
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from osskey.app_state import AppState


class InactivityTimer:
    def __init__(self, app_state: "AppState", root, callback):
        self._app_state = app_state
        self._root = root
        self._callback = callback
        self._timer_id: str | None = None
        self._bind_events()

    def _bind_events(self):
        self._root.bind("<ButtonRelease-1>", self._on_activity, add="+")
        self._root.bind("<KeyPress>", self._on_activity, add="+")
        self._root.bind("<MouseWheel>", self._on_activity, add="+")

    def _on_activity(self, event=None):
        # Debounce activity to prevent GUI crashes during high-speed automated typing
        now = time.time()
        if now - self._app_state.last_interaction < 0.1:
            return
        self._app_state.last_interaction = now
        self.reset()

    def reset(self):
        self.cancel()
        if self._app_state.settings.get("auto_lock", True):
            ms = self._app_state.settings.get("timeout_minutes", 5) * 60 * 1000
            self._timer_id = self._root.after(ms, self._on_timeout)

    def cancel(self):
        if self._timer_id is not None:
            with contextlib.suppress(Exception):
                self._root.after_cancel(self._timer_id)
            self._timer_id = None

    def _on_timeout(self):
        self._timer_id = None
        if self._app_state.app == "UNLOCKED":
            self._callback()
