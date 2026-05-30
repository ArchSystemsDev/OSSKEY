import customtkinter as ctk

from osskey import vault_ops
from osskey.autotype import autotype
from osskey.views.dialogs import confirm_dialog

BG       = "#020a02"
BG2      = "#040e04"
BORDER   = "#1a3a1a"
GREEN    = "#00ff41"
GREEN_DIM= "#1a5a1a"
TEXT     = "#a0c878"
TEXT_DIM = "#2a5a2a"


class VaultView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self._app = app
        self._rows: list[ctk.CTkFrame] = []
        self._clipboard_timer: str | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        top.grid_columnconfigure(0, weight=1)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._rebuild_list())
        self._search_entry = ctk.CTkEntry(
            top, textvariable=self._search_var,
            placeholder_text="grep credentials...",
            font=("Consolas", 13), corner_radius=0,
            border_color=BORDER, fg_color=BG2, text_color=TEXT
        )
        self._search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._add_btn = ctk.CTkButton(
            top, text="+ NEW", command=self._on_add,
            font=("Consolas", 11), width=90, height=32,
            corner_radius=0, fg_color="transparent",
            hover_color=BG2, text_color=GREEN,
            border_width=1, border_color=GREEN_DIM
        )
        self._add_btn.grid(row=0, column=1)

        header = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=30)
        header.grid(row=1, column=0, sticky="ew", padx=12)
        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=2)
        header.grid_columnconfigure(2, weight=0)
        header.grid_columnconfigure(3, weight=0)
        header.grid_propagate(False)

        for col, txt in enumerate(["LABEL", "USERNAME", "ACTIONS"]):
            ctk.CTkLabel(
                header, text=txt, font=("Consolas", 9),
                text_color=TEXT_DIM
            ).grid(row=0, column=col, padx=6, pady=4, sticky="w")

        self._count_label = ctk.CTkLabel(
            header, text="", font=("Consolas", 9),
            text_color=TEXT_DIM
        )
        self._count_label.grid(row=0, column=3, padx=(0, 6), pady=4, sticky="e")

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._scroll.grid_columnconfigure(0, weight=1)

        self._rebuild_list()

    def _credential_list(self) -> list:
        vm = self._app.app_state.vault_manager
        query = self._search_var.get().strip().lower()
        if query:
            return sorted(vm.search(query), key=lambda c: c.label.lower())
        return sorted(vm.credentials, key=lambda c: c.label.lower())

    def _rebuild_list(self):
        for row in self._rows:
            row.destroy()
        self._rows.clear()

        total = len(self._app.app_state.vault_manager)
        creds = self._credential_list()
        query = self._search_var.get().strip()
        if query:
            self._count_label.configure(text=f"{len(creds)} / {total}")
        else:
            self._count_label.configure(text=f"{total} CREDS")
        if not creds:
            lbl = ctk.CTkLabel(
                self._scroll, text="no credentials found",
                font=("Consolas", 11), text_color=TEXT_DIM
            )
            lbl.pack(pady=30)
            self._rows.append(lbl)
            return

        for cred in creds:
            row = ctk.CTkFrame(
                self._scroll, fg_color=BG2, corner_radius=0, height=36
            )
            row.pack(fill="x", pady=1)
            row.grid_columnconfigure(0, weight=2)
            row.grid_columnconfigure(1, weight=2)
            row.grid_columnconfigure(2, weight=0)
            row.pack_propagate(False)

            ctk.CTkLabel(
                row, text=cred.label,
                font=("Consolas", 12), text_color=TEXT
            ).grid(row=0, column=0, padx=6, pady=2, sticky="w")

            ctk.CTkLabel(
                row, text=cred.username,
                font=("Consolas", 11), text_color=TEXT_DIM
            ).grid(row=0, column=1, padx=6, pady=2, sticky="w")

            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.grid(row=0, column=2, padx=4, pady=2, sticky="e")

            auto_btn = ctk.CTkButton(
                btn_frame, text="AUTOTYPE",
                font=("Consolas", 9, "bold"), width=56, height=22,
                corner_radius=0, fg_color="transparent",
                hover_color="#0a1a0a", text_color=GREEN
            )
            auto_btn.configure(
                command=lambda u=cred.username, p=cred.password: self._on_autotype(u, p)
            )
            auto_btn.pack(side="left", padx=1)

            user_btn = ctk.CTkButton(
                btn_frame, text="USER",
                font=("Consolas", 9), width=40, height=22,
                corner_radius=0, fg_color="transparent",
                hover_color="#0a1a0a", text_color=TEXT_DIM
            )
            user_btn.configure(
                command=lambda b=user_btn, t=cred.username: self._copy_to_clipboard(b, t),
            )
            user_btn.pack(side="left", padx=1)

            pass_btn = ctk.CTkButton(
                btn_frame, text="PASS",
                font=("Consolas", 9), width=40, height=22,
                corner_radius=0, fg_color="transparent",
                hover_color="#0a1a0a", text_color=TEXT_DIM
            )
            pass_btn.configure(
                command=lambda b=pass_btn, t=cred.password: self._copy_to_clipboard(b, t),
            )
            pass_btn.pack(side="left", padx=1)

            edit_btn = ctk.CTkButton(
                btn_frame, text="EDIT",
                font=("Consolas", 9), width=40, height=22,
                corner_radius=0, fg_color="transparent",
                hover_color="#0a1a0a", text_color=TEXT_DIM
            )
            edit_btn.configure(command=lambda c=cred.id: self._on_edit(c))
            edit_btn.pack(side="left", padx=1)

            del_btn = ctk.CTkButton(
                btn_frame, text="DEL",
                font=("Consolas", 9), width=40, height=22,
                corner_radius=0, fg_color="transparent",
                hover_color="#1a0a0a", text_color="#553333"
            )
            del_btn.configure(command=lambda c=cred.id: self._on_delete(c))
            del_btn.pack(side="left", padx=1)

            self._rows.append(row)

    def _on_autotype(self, username: str, password: str):
        serial = getattr(self._app, "_serial", None)
        if serial is not None and serial.connected:
            key = self._app.app_state.derived_key
            if key is not None:
                try:
                    serial.inject_encrypted(username, password, key)
                    return
                except Exception:
                    pass
        autotype(
            root=self._app.root,
            username=username,
            password=password,
            mode="both",
            delay_ms=400,
            press_enter=False,
        )

    def _on_add(self):
        self._app.show_view("edit_credential")

    def _on_edit(self, cred_id: str):
        self._app.show_view("edit_credential", cred_id=cred_id)

    def _on_delete(self, cred_id: str):
        cred = self._app.app_state.vault_manager.get(cred_id)
        label = cred.label if cred else "untitled"
        confirmed = confirm_dialog(
            "Delete Credential",
            f"Delete '{label}'?\nThis cannot be undone.",
            parent=self
        )
        if not confirmed:
            return

        self._app.app_state.vault_manager.delete(cred_id)
        self._save_vault()
        self._rebuild_list()

    def _copy_to_clipboard(self, btn: ctk.CTkButton, text: str):
        if not text:
            return
        if self._clipboard_timer:
            self._app.root.after_cancel(self._clipboard_timer)
        self._app.root.clipboard_clear()
        self._app.root.clipboard_append(text)
        orig_text = btn.cget("text")
        btn.configure(text="OK", fg_color="#0a1a0a")
        self._app.root.after(1200, lambda b=btn, t=orig_text: b.configure(text=t, fg_color="transparent"))
        self._clipboard_timer = self._app.root.after(30000, self._app.root.clipboard_clear)

    def _save_vault(self):
        vault_ops.save_vault(self._app.app_state)
