import secrets
import string

import customtkinter as ctk

from osskey import vault_ops

BG       = "#020a02"
BG2      = "#040e04"
BORDER   = "#1a3a1a"
GREEN    = "#00ff41"
GREEN_DIM= "#1a5a1a"
TEXT     = "#a0c878"
TEXT_DIM = "#2a5a2a"


def _generate_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _strength_info(password: str) -> tuple[int, str, str]:
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1

    if score <= 2:
        return 0, "WEAK", "#ff4444"
    if score <= 3:
        return 1, "FAIR", "#ff8844"
    if score <= 4:
        return 2, "GOOD", "#ffcc00"
    if score <= 5:
        return 3, "STRONG", "#88cc00"
    return 4, "VERY STRONG", "#00cc66"


class EditCredentialView(ctk.CTkFrame):
    def __init__(self, master, app, cred_id: str | None = None, **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self._app = app
        self._cred_id = cred_id
        self._password_visible = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=0)
        center.grid_columnconfigure(1, weight=1)

        is_edit = cred_id is not None
        existing = app.app_state.vault_manager.get(cred_id) if cred_id else None

        title_text = "EDIT CREDENTIAL" if is_edit else "NEW CREDENTIAL"
        ctk.CTkLabel(
            center, text=title_text,
            font=("Consolas", 18, "bold"), text_color=GREEN
        ).grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="w")

        row = 1
        ctk.CTkLabel(
            center, text="> LABEL", font=("Consolas", 11),
            text_color=TEXT_DIM
        ).grid(row=row, column=0, padx=(0, 8), pady=4, sticky="w")
        self._label_entry = ctk.CTkEntry(
            center, font=("Consolas", 14), width=320, height=36,
            corner_radius=0, border_color=BORDER,
            fg_color=BG2, text_color=TEXT
        )
        self._label_entry.grid(row=row, column=1, columnspan=2, pady=4, sticky="ew")
        if existing:
            self._label_entry.insert(0, existing.label)

        row += 1
        ctk.CTkLabel(
            center, text="> USERNAME", font=("Consolas", 11),
            text_color=TEXT_DIM
        ).grid(row=row, column=0, padx=(0, 8), pady=4, sticky="w")
        self._username_entry = ctk.CTkEntry(
            center, font=("Consolas", 14), width=320, height=36,
            corner_radius=0, border_color=BORDER,
            fg_color=BG2, text_color=TEXT
        )
        self._username_entry.grid(row=row, column=1, columnspan=2, pady=4, sticky="ew")
        if existing:
            self._username_entry.insert(0, existing.username)

        row += 1
        ctk.CTkLabel(
            center, text="> PASSWORD", font=("Consolas", 11),
            text_color=TEXT_DIM
        ).grid(row=row, column=0, padx=(0, 8), pady=4, sticky="w")
        self._password_entry = ctk.CTkEntry(
            center, font=("Consolas", 14), width=240, height=36,
            corner_radius=0, border_color=BORDER,
            fg_color=BG2, text_color=TEXT,
            show="\u25cf"
        )
        self._password_entry.grid(row=row, column=1, pady=4, sticky="ew")
        if existing:
            self._password_entry.insert(0, existing.password)
        self._password_entry.bind("<KeyRelease>", lambda e: self._update_strength())

        self._toggle_btn = ctk.CTkButton(
            center, text="\u25c9", command=self._toggle_visibility,
            font=("Consolas", 14), width=34, height=34,
            corner_radius=0, fg_color=BG2,
            hover_color="#0a2a0a", text_color=TEXT_DIM
        )
        self._toggle_btn.grid(row=row, column=2, padx=(4, 0), pady=4)

        row += 1
        self._strength_bar = ctk.CTkProgressBar(
            center, width=320, height=4, corner_radius=0,
            progress_color="#ff4444", fg_color="#0a180a"
        )
        self._strength_bar.grid(row=row, column=0, columnspan=3, pady=(6, 0), sticky="ew")
        self._strength_bar.set(0)

        self._strength_label = ctk.CTkLabel(
            center, text="", font=("Consolas", 10), text_color=TEXT_DIM
        )
        self._strength_label.grid(row=row + 1, column=0, columnspan=3, pady=(0, 4), sticky="w")

        row += 2
        self._generate_btn = ctk.CTkButton(
            center, text="GENERATE PASSWORD", command=self._on_generate,
            font=("Consolas", 11), width=320, height=32,
            corner_radius=0, fg_color="transparent",
            hover_color=BG2, text_color=GREEN,
            border_width=1, border_color=GREEN_DIM
        )
        self._generate_btn.grid(row=row, column=0, columnspan=3, pady=(8, 4))

        row += 1
        btn_frame = ctk.CTkFrame(center, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(16, 0))

        ctk.CTkButton(
            btn_frame, text="CANCEL", command=self._on_cancel,
            font=("Consolas", 11), width=120, height=34,
            corner_radius=0, fg_color="transparent",
            hover_color=BG2, text_color=TEXT_DIM,
            border_width=1, border_color=BORDER
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame, text="SAVE", command=self._on_save,
            font=("Consolas", 11, "bold"), width=120, height=34,
            corner_radius=0, fg_color=GREEN,
            hover_color="#00cc33", text_color="#000000"
        ).pack(side="left", padx=6)

        self._error_label = ctk.CTkLabel(
            center, text="", font=("Consolas", 10),
            text_color="#ff4444", wraplength=320
        )
        self._error_label.grid(row=row + 1, column=0, columnspan=3, pady=6)

        self._update_strength()

    def _toggle_visibility(self):
        self._password_visible = not self._password_visible
        self._password_entry.configure(
            show="" if self._password_visible else "\u25cf"
        )
        self._toggle_btn.configure(
            text="\u25c6" if self._password_visible else "\u25c9"
        )

    def _update_strength(self):
        pw = self._password_entry.get()
        if not pw:
            self._strength_bar.set(0)
            self._strength_bar.configure(progress_color="#ff4444")
            self._strength_label.configure(text="")
            return
        level, label, color = _strength_info(pw)
        self._strength_bar.set((level + 1) / 5.0)
        self._strength_bar.configure(progress_color=color)
        self._strength_label.configure(text=label, text_color=color)

    def _on_generate(self):
        pw = _generate_password()
        self._password_entry.delete(0, "end")
        self._password_entry.insert(0, pw)
        self._update_strength()

    def _on_cancel(self):
        self._app.show_view("vault")

    def _on_save(self):
        label = self._label_entry.get().strip()
        username = self._username_entry.get().strip()
        password = self._password_entry.get()

        if not label:
            self._error_label.configure(text="[ERR] Label is required")
            return
        if not username:
            self._error_label.configure(text="[ERR] Username is required")
            return
        if not password:
            self._error_label.configure(text="[ERR] Password is required")
            return

        self._error_label.configure(text="")

        vm = self._app.app_state.vault_manager
        if self._cred_id and vm.get(self._cred_id):
            vm.edit(self._cred_id, label=label, username=username, password=password)
        else:
            vm.add(label, username, password)

        self._save_vault()
        self._app.show_view("vault")

    def _save_vault(self):
        vault_ops.save_vault(self._app.app_state)
