import json

import customtkinter as ctk

from osskey.app_state import AppState
from osskey.config import settings_path
from osskey.inactivity import InactivityTimer
from osskey.views.edit_credential_view import EditCredentialView
from osskey.views.settings_view import SettingsView
from osskey.views.unlock_view import UnlockView
from osskey.views.vault_view import VaultView

# ── palette ────────────────────────────────────────────────────────────────
BG       = "#020a02"
BG2      = "#040e04"
BORDER   = "#1a3a1a"
GREEN    = "#00ff41"
GREEN_DIM= "#2a6a2a"
GREEN_MID= "#4a9a4a"
TEXT     = "#a0c878"
TEXT_DIM = "#2a5a2a"
RED_DIM  = "#3a1010"


class App:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.app_state = AppState()
        self.current_view: ctk.CTkFrame | None = None

        self._load_settings()
        self._build_ui()
        self.inactivity_timer = InactivityTimer(
            self.app_state, root, self._on_inactivity_timeout
        )
        self.inactivity_timer.reset()
        self.show_view("unlock")

    def _build_ui(self):
        self.root.configure(fg_color=BG)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # ── top bar ────────────────────────────────────────────────────────
        self.top_bar = ctk.CTkFrame(
            self.root, fg_color=BG, corner_radius=0, height=36,
            border_width=0
        )
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.grid_columnconfigure(1, weight=1)
        self.top_bar.grid_propagate(False)

        # border line under top bar
        self._top_border = ctk.CTkFrame(
            self.root, fg_color=BORDER, corner_radius=0, height=1
        )
        self._top_border.grid(row=0, column=0, sticky="sew")
        self._top_border.grid_propagate(False)

        ctk.CTkLabel(
            self.top_bar, text="OSSKEY",
            font=("Consolas", 14, "bold"), text_color=GREEN
        ).grid(row=0, column=0, padx=(14, 8), pady=0, sticky="w")

        ctk.CTkLabel(
            self.top_bar, text="//",
            font=("Consolas", 11), text_color=BORDER
        ).grid(row=0, column=1, padx=0, pady=0, sticky="w")

        ctk.CTkLabel(
            self.top_bar, text="v1.0.0 · AES-256-GCM",
            font=("Consolas", 10), text_color=TEXT_DIM
        ).grid(row=0, column=2, padx=(4, 0), pady=0, sticky="w")

        # spacer
        ctk.CTkFrame(self.top_bar, fg_color="transparent").grid(
            row=0, column=3, sticky="ew"
        )
        self.top_bar.grid_columnconfigure(3, weight=1)

        self._status_label = ctk.CTkLabel(
            self.top_bar, text="[ LOCKED ]",
            font=("Consolas", 10), text_color="#ff3333"
        )
        self._status_label.grid(row=0, column=4, padx=(0, 12), pady=0, sticky="e")

        self._settings_btn = ctk.CTkButton(
            self.top_bar, text="settings",
            command=lambda: self.show_view("settings"),
            font=("Consolas", 10), width=60, height=22,
            corner_radius=0, fg_color="transparent",
            hover_color=BG2, text_color=TEXT_DIM,
            border_width=0
        )
        self._settings_btn.grid(row=0, column=5, padx=(0, 4), pady=0)

        self._lock_btn = ctk.CTkButton(
            self.top_bar, text="lock",
            command=self._on_lock,
            font=("Consolas", 10), width=44, height=22,
            corner_radius=0, fg_color="transparent",
            hover_color=BG2, text_color=RED_DIM,
            border_width=0
        )
        self._lock_btn.grid(row=0, column=6, padx=(0, 10), pady=0)

        # start disabled (vault starts locked)
        self._settings_btn.configure(state="disabled", text_color="#1a3a1a")
        self._lock_btn.configure(state="disabled", text_color="#1a0a0a")

        # ── content area ───────────────────────────────────────────────────
        self.content = ctk.CTkFrame(
            self.root, fg_color=BG, corner_radius=0
        )
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def set_status(self, locked: bool):
        if locked:
            self._status_label.configure(text="[ LOCKED ]", text_color="#ff3333")
            self._settings_btn.configure(state="disabled", text_color="#1a3a1a")
            self._lock_btn.configure(state="disabled", text_color="#1a0a0a")
        else:
            self._status_label.configure(text="[ UNLOCKED ]", text_color=GREEN)
            self._settings_btn.configure(state="normal", text_color=TEXT_DIM)
            self._lock_btn.configure(state="normal", text_color=RED_DIM)

    def show_view(self, name: str, **kwargs):
        if name != "unlock" and self.app_state.app == "LOCKED":
            return

        if self.current_view:
            self.current_view.destroy()
            self.current_view = None

        view_class = {
            "unlock": UnlockView,
            "vault": VaultView,
            "edit_credential": EditCredentialView,
            "settings": SettingsView,
        }.get(name)

        if view_class is None:
            return

        view = view_class(self.content, self, **kwargs)
        view.grid(row=0, column=0, sticky="nsew")
        self.current_view = view
        self.inactivity_timer.reset()

    def _on_lock(self):
        self.app_state.lock()
        self.set_status(locked=True)
        self.show_view("unlock")

    def _on_inactivity_timeout(self):
        self.app_state.lock()
        self.set_status(locked=True)
        self.show_view("unlock")

    def _load_settings(self):
        sp = settings_path()
        if sp.exists():
            try:
                data = json.loads(sp.read_text(encoding="utf-8"))
                self.app_state.settings.update(data)
            except Exception:
                pass
        self.app_state.timeout_minutes = self.app_state.settings.get(
            "timeout_minutes", 5
        )

    def save_settings(self):
        sp = settings_path()
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(
            json.dumps(self.app_state.settings, indent=2),
            encoding="utf-8"
        )

    def on_close(self):
        self.app_state.zero_sensitive()
        try:
            # Prevent rare crashes if the clipboard is locked by another process on exit
            self.root.clipboard_clear()
        except Exception:
            pass
