import os
import shutil

import customtkinter as ctk

from osskey.config import vault_path
from osskey.crypto import decrypt_vault, derive_key, encrypt_vault, zero_key
from osskey.views.dialogs import message_dialog

BG       = "#020a02"
BG2      = "#040e04"
BORDER   = "#1a3a1a"
GREEN    = "#00ff41"
GREEN_DIM= "#1a5a1a"
TEXT     = "#a0c878"
TEXT_DIM = "#2a5a2a"
RED_DIM  = "#3a1010"

TIMEOUT_OPTIONS = [1, 2, 5, 10, 15, 30]


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self._app = app

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self._scroll.grid_columnconfigure(0, weight=1)

        self._build_sections()

    def _section(self, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(
            self._scroll, fg_color="transparent", corner_radius=0
        )
        frame.pack(fill="x", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text=f"> {title}", font=("Consolas", 15, "bold"),
            text_color=GREEN
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        sep = ctk.CTkFrame(frame, fg_color=BORDER, height=1, corner_radius=0)
        sep.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        sep.grid_propagate(False)

        return frame

    def _build_sections(self):
        self._build_pin_section()
        self._build_timeout_section()
        self._build_export_section()
        self._build_about_section()

    def _build_pin_section(self):
        section = self._section("SECURITY")
        ctk.CTkButton(
            section, text="CHANGE PIN", command=self._on_change_pin,
            font=("Consolas", 11), width=200, height=32,
            corner_radius=0, fg_color="transparent",
            hover_color=BG2, text_color=GREEN,
            border_width=1, border_color=GREEN_DIM
        ).grid(row=2, column=0, sticky="w")

    def _build_timeout_section(self):
        section = self._section("INACTIVITY LOCK")

        self._auto_lock_var = ctk.BooleanVar(
            value=self._app.app_state.settings.get("auto_lock", True)
        )
        self._auto_lock_check = ctk.CTkCheckBox(
            section, text="Auto-lock after inactivity",
            variable=self._auto_lock_var,
            command=self._on_settings_changed,
            font=("Consolas", 11), text_color=TEXT,
            corner_radius=0, fg_color=BG2,
            checkmark_color=GREEN, hover_color="#0a1a0a",
            border_color=BORDER
        )
        self._auto_lock_check.grid(row=2, column=0, sticky="w", pady=(0, 8))

        self._timeout_var = ctk.IntVar(
            value=self._app.app_state.settings.get("timeout_minutes", 5)
        )

        radio_frame = ctk.CTkFrame(section, fg_color="transparent")
        radio_frame.grid(row=3, column=0, sticky="w")

        for i, val in enumerate(TIMEOUT_OPTIONS):
            rb = ctk.CTkRadioButton(
                radio_frame, text=f"{val} min",
                variable=self._timeout_var, value=val,
                command=self._on_settings_changed,
                font=("Consolas", 10), text_color=TEXT_DIM,
                corner_radius=0, fg_color=BG2,
                border_color=BORDER, hover_color="#0a1a0a",
                border_width_unchecked=2, border_width_checked=2
            )
            rb.grid(row=i // 3, column=i % 3, padx=(0, 12), pady=2, sticky="w")

    def _build_export_section(self):
        section = self._section("BACKUP")

        ctk.CTkButton(
            section, text="EXPORT VAULT",
            command=self._on_export,
            font=("Consolas", 11), width=200, height=32,
            corner_radius=0, fg_color="transparent",
            hover_color=BG2, text_color=GREEN,
            border_width=1, border_color=GREEN_DIM
        ).grid(row=2, column=0, sticky="w")

    def _build_about_section(self):
        section = self._section("ABOUT")

        info = (
            "OSSKEY v1.0.0\n"
            "AES-256-GCM encrypted credential vault\n\n"
            "Protected by your master PIN."
        )
        ctk.CTkLabel(
            section, text=info, font=("Consolas", 10),
            text_color=TEXT_DIM, justify="left"
        ).grid(row=2, column=0, sticky="w")

    def _on_change_pin(self):
        dialog = ctk.CTkInputDialog(
            text="Enter CURRENT PIN:",
            title="Change PIN"
        )
        old_pin = dialog.get_input()
        if old_pin is None or not old_pin.strip():
            return

        dialog = ctk.CTkInputDialog(
            text="Enter NEW PIN (4-32 characters):",
            title="Change PIN"
        )
        new_pin = dialog.get_input()
        if new_pin is None or not new_pin.strip():
            return
        if len(new_pin) < 4 or len(new_pin) > 32:
            message_dialog("Error", "PIN must be 4-32 characters.", parent=self)
            return
        if new_pin == old_pin:
            message_dialog("Error", "New PIN must differ from current PIN.", parent=self)
            return

        try:
            full_blob = vault_path().read_bytes()
            kdf_salt = full_blob[:16]
            inner = full_blob[16:]
            old_key = derive_key(old_pin, kdf_salt)
            try:
                plaintext = decrypt_vault(inner, old_key)
            except Exception:
                zero_key(old_key)
                message_dialog("Error", "Wrong current PIN.", parent=self)
                return
            zero_key(old_key)

            new_kdf_salt = os.urandom(16)
            new_key = derive_key(new_pin, new_kdf_salt)
            new_inner = encrypt_vault(plaintext, new_key)
            new_full_blob = new_kdf_salt + new_inner
            vault_path().write_bytes(new_full_blob)

            self._app.app_state.derived_key = new_key
            self._app.app_state.encrypted_blob = new_full_blob
            message_dialog("Success", "PIN changed successfully.", parent=self)
        except Exception as e:
            message_dialog("Error", f"Failed to change PIN:\n{e}", parent=self)

    def _on_settings_changed(self):
        self._app.app_state.settings["auto_lock"] = self._auto_lock_var.get()
        self._app.app_state.settings["timeout_minutes"] = self._timeout_var.get()
        self._app.app_state.timeout_minutes = self._timeout_var.get()
        self._app.inactivity_timer.reset()
        self._app.save_settings()

    def _on_export(self):
        from tkinter import filedialog

        src = vault_path()
        if not src.exists():
            message_dialog("Error", "No vault file to export.", parent=self)
            return

        dest = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".enc",
            filetypes=[("Encrypted vault", "*.enc")],
            initialfile="vault.enc",
            title="Export Encrypted Vault"
        )
        if not dest:
            return

        try:
            shutil.copy2(src, dest)
            message_dialog("Exported", f"Vault exported to:\n{dest}", parent=self)
        except Exception as e:
            message_dialog("Error", f"Export failed:\n{e}", parent=self)
