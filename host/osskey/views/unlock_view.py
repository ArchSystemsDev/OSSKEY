import contextlib
import os
import random
from tkinter import Canvas

import customtkinter as ctk

from osskey.config import vault_path
from osskey.crypto import WrongPINError, decrypt_vault, derive_key, encrypt_vault, zero_key
from osskey.vault import VaultManager

MATRIX_CHARS = list("ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜｦﾝ0123456789#$%&")

BG     = "#020a02"
GREEN  = "#00ff41"
TEXT   = "#a0c878"
DIM    = "#2a5a2a"
BORDER = "#1a3a1a"

# How tall the top bar in app.py is (px). Widgets are placed in the canvas
# which sits *below* the top bar, but canvas coords start at 0 inside the
# canvas – so no extra offset is needed here.  The old code subtracted a
# fixed value from h//2 which pushed everything too high when the window
# was short.  We now centre relative to the canvas's own height.
_TOP_BAR_H = 37   # matches height=36 + 1-px border in app.py


class UnlockView(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=BG, corner_radius=0, **kwargs)
        self._app = app
        self._is_first_run = not vault_path().exists()
        self._drops = []
        self._matrix_after_id = None
        self._widgets_created = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._canvas = Canvas(self, bg=BG, highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        # FIX 3 – wait for a real Configure event (canvas has actual size)
        # instead of polling with after(10/50) and getting width=1.
        self._canvas.bind("<Configure>", self._on_resize)

    def _on_resize(self, event=None):
        # FIX 2 – re-lift the window and restore focus whenever the canvas
        # is resized (which also fires on first map).  This prevents the
        # window from being pushed behind other windows when the user clicks
        # into the PIN entry widget embedded in the canvas.
        try:
            self._app.root.lift()
            self._app.root.focus_force()
        except Exception:
            pass

        if self._matrix_after_id:
            self.after_cancel(self._matrix_after_id)
            self._matrix_after_id = None
        for d in self._drops:
            for item_id in d["items"]:
                self._canvas.delete(item_id)
        self._drops.clear()

        # Only rebuild widgets once; after that just restart the rain.
        if not self._widgets_created:
            self._do_create_widgets(event)
        else:
            self._reposition_widgets()

        self._init_matrix()
        self._animate_matrix()

    # ------------------------------------------------------------------
    # Widget creation  (called once after the canvas has a real size)
    # ------------------------------------------------------------------

    def _do_create_widgets(self, event=None):
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 10 or h < 10:
            self.after(30, lambda: self._do_create_widgets())
            return

        self._widgets_created = True
        cx = w // 2

        # FIX 1 – centre the block in the canvas (not the whole window).
        # Estimated total block height so we can vertically centre it.
        block_h = 48 + 18 + 24 + 20 + 52 + 50 + 28 + 24   # ≈ 264 px
        top_y = max((h - block_h) // 2, 16)
        y = top_y

        # ── title ──────────────────────────────────────────────────────
        title = ctk.CTkLabel(
            self._canvas, text="OSSKEY",
            font=("Consolas", 42, "bold"), text_color=GREEN,
            fg_color="transparent"
        )
        self._title_win = self._canvas.create_window(cx, y, window=title)
        y += 48

        subtitle = ctk.CTkLabel(
            self._canvas,
            text="ENCRYPTED CREDENTIAL VAULT  //  AES-256-GCM",
            font=("Consolas", 10), text_color=DIM,
            fg_color="transparent"
        )
        self._subtitle_win = self._canvas.create_window(cx, y, window=subtitle)
        y += 28

        # ── divider ────────────────────────────────────────────────────
        div = ctk.CTkFrame(self._canvas, fg_color=BORDER, height=1, width=300, corner_radius=0)
        self._div_win = self._canvas.create_window(cx, y, window=div)
        y += 24

        # ── prompt label ───────────────────────────────────────────────
        prompt = ctk.CTkLabel(
            self._canvas,
            text="ENTER MASTER PIN" if not self._is_first_run else "CREATE MASTER PIN",
            font=("Consolas", 9), text_color=DIM,
            fg_color="transparent"
        )
        self._prompt_win = self._canvas.create_window(cx, y, window=prompt)
        y += 22

        # ── PIN entry ──────────────────────────────────────────────────
        entry_frame = ctk.CTkFrame(
            self._canvas, fg_color="#050f05",
            border_width=1, border_color=BORDER,
            corner_radius=0, width=300, height=42
        )
        self._entry_frame_win = self._canvas.create_window(cx, y, window=entry_frame)

        self._pin_entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="··················",
            show="\u25cf",
            font=("Consolas", 18), width=260, height=36,
            corner_radius=0, border_width=0,
            fg_color="transparent", text_color=GREEN,
            placeholder_text_color=DIM
        )
        self._pin_entry.place(relx=0.5, rely=0.5, anchor="center")
        self._pin_entry.bind("<Return>", lambda e: self._do_action())

        # FIX 2 – clicking the entry must NOT minimize the window.
        # Force the root window to stay raised whenever the entry gains focus.
        self._pin_entry.bind("<FocusIn>", self._on_entry_focus)
        self._pin_entry.bind("<Button-1>", self._on_entry_click)

        y += 52

        # ── action button ──────────────────────────────────────────────
        self._action_btn = ctk.CTkButton(
            self._canvas,
            text="[ CREATE VAULT ]" if self._is_first_run else "[ UNLOCK ]",
            command=self._do_action,
            font=("Consolas", 13, "bold"), width=300, height=40,
            corner_radius=0,
            fg_color=GREEN, hover_color="#00cc33",
            text_color="#000000"
        )
        self._action_win = self._canvas.create_window(cx, y, window=self._action_btn)
        y += 50

        # ── hint / spacer ──────────────────────────────────────────────
        if self._is_first_run:
            hint = ctk.CTkLabel(
                self._canvas,
                text="no vault detected — enter a pin (4-32 chars) to initialise",
                font=("Consolas", 10), text_color=DIM,
                fg_color="transparent"
            )
            self._hint_win = self._canvas.create_window(cx, y, window=hint)
        else:
            self._hint_win = None
        y += 28

        # ── feedback labels ────────────────────────────────────────────
        self._error_label = ctk.CTkLabel(
            self._canvas, text="",
            font=("Consolas", 11), text_color="#ff4444",
            fg_color="transparent", wraplength=300
        )
        self._error_win = self._canvas.create_window(cx, y, window=self._error_label)
        y += 24

        self._success_label = ctk.CTkLabel(
            self._canvas, text="",
            font=("Consolas", 11), text_color=GREEN,
            fg_color="transparent", wraplength=300
        )
        self._success_win = self._canvas.create_window(cx, y, window=self._success_label)

        # Store layout anchors for repositioning on resize
        self._layout_cx = cx
        self._layout_top_y = top_y

        self._pin_entry.focus()

    def _reposition_widgets(self):
        """Recentre all canvas windows after a resize without recreating them."""
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 10 or h < 10:
            return
        cx = w // 2
        block_h = 48 + 18 + 24 + 20 + 52 + 50 + 28 + 24
        top_y = max((h - block_h) // 2, 16)
        y = top_y

        offsets = [
            self._title_win,      # +48
            self._subtitle_win,   # +28
            self._div_win,        # +24
            self._prompt_win,     # +22
            self._entry_frame_win,# +52
            self._action_win,     # +50
        ]
        steps = [48, 28, 24, 22, 52, 50]
        for win_id, step in zip(offsets, steps, strict=True):
            self._canvas.coords(win_id, cx, y)
            y += step

        if self._hint_win:
            self._canvas.coords(self._hint_win, cx, y)
        y += 28
        self._canvas.coords(self._error_win, cx, y)
        y += 24
        self._canvas.coords(self._success_win, cx, y)

    # ------------------------------------------------------------------
    # Focus helpers  (FIX 2)
    # ------------------------------------------------------------------

    def _on_entry_focus(self, event=None):
        try:
            self._app.root.lift()
        except Exception:
            pass

    def _on_entry_click(self, event=None):
        try:
            self._app.root.lift()
            self._app.root.focus_force()
        except Exception:
            pass
        # Let the click reach the entry normally
        return None

    # ── matrix rain ────────────────────────────────────────────────────────

    def _init_matrix(self):
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 10 or h < 10:
            self.after(100, self._init_matrix)
            return

        char_w, char_h = 18, 16
        cols = w // char_w

        for c in range(cols + 1):
            x = c * char_w + char_w // 2
            y_start = random.randint(-h, 0)
            speed = random.uniform(1.2, 3.0)
            length = random.randint(10, 22)
            items = []
            for r in range(length):
                ch = random.choice(MATRIX_CHARS)
                # FIX 1 – use a visible dark-green instead of near-black #041404
                # so the rain is actually visible against the BG.
                item_id = self._canvas.create_text(
                    x, y_start - r * char_h,
                    text=ch, font=("Consolas", char_h - 4),
                    fill="#0a2a0a", anchor="n"
                )
                items.append(item_id)
            self._drops.append({
                "x": x, "y": y_start, "speed": speed,
                "length": length, "items": items, "char_h": char_h,
            })

    def _animate_matrix(self):
        if not self.winfo_exists():
            return
        h = self._canvas.winfo_height()
        colors = [
            "#0a2a0a", "#0d3a0d", "#1a5a1a", "#2a7a2a",
            "#1a5a1a", "#2a7a2a", "#00cc33", "#00ff41"
        ]

        for d in self._drops:
            d["y"] += d["speed"]
            max_y = h + d["length"] * d["char_h"] * 2
            if d["y"] > max_y:
                d["y"] = -d["length"] * d["char_h"] * 2
                d["speed"] = random.uniform(1.2, 3.0)

            for r, item_id in enumerate(d["items"]):
                y_pos = d["y"] - r * d["char_h"]
                self._canvas.coords(item_id, d["x"], y_pos)
                if r == 0:
                    c = colors[7]
                elif r == 1:
                    c = colors[6]
                elif r < 4:
                    c = colors[5]
                elif r < 8:
                    c = colors[4]
                elif r < 12:
                    c = colors[2]
                else:
                    c = colors[0]
                self._canvas.itemconfig(item_id, fill=c)
                if random.random() < 0.02:
                    self._canvas.itemconfig(item_id, text=random.choice(MATRIX_CHARS))

        self._matrix_after_id = self.after(80, self._animate_matrix)

    def destroy(self):
        if self._matrix_after_id:
            self.after_cancel(self._matrix_after_id)
            self._matrix_after_id = None
        super().destroy()

    # ── feedback ───────────────────────────────────────────────────────────

    def _clear_feedback(self):
        self._error_label.configure(text="")
        self._success_label.configure(text="")

    def _show_error(self, msg):
        self._error_label.configure(text=f"[ERR] {msg}")
        self._success_label.configure(text="")
        self._pin_entry.delete(0, "end")

    def _show_success(self, msg):
        self._success_label.configure(text=f"[OK]  {msg}")
        self._error_label.configure(text="")

    # ── validation ─────────────────────────────────────────────────────────

    def _validate_pin(self, pin: str) -> str | None:
        if not pin:
            return "PIN cannot be empty"
        if len(pin) < 4:
            return "PIN must be at least 4 characters"
        if len(pin) > 32:
            return "PIN must be at most 32 characters"
        return None

    # ── actions ────────────────────────────────────────────────────────────

    def _do_action(self):
        self._clear_feedback()
        pin = self._pin_entry.get()
        err = self._validate_pin(pin)
        if err:
            self._show_error(err)
            return
        if self._is_first_run:
            self._do_create_vault(pin)
        else:
            self._do_unlock(pin)

    def _do_create_vault(self, pin: str):
        try:
            vault_path().parent.mkdir(parents=True, exist_ok=True)
            kdf_salt = os.urandom(16)
            key = derive_key(pin, kdf_salt)
            vm = VaultManager()
            plaintext = vm.serialize()
            inner = encrypt_vault(plaintext, key)
            full_blob = kdf_salt + inner
            vault_path().write_bytes(full_blob)

            self._app.app_state.vault_manager = vm
            self._app.app_state.derived_key = key
            self._app.app_state.encrypted_blob = full_blob
            self._app.app_state.unlock()
            self._app.set_status(locked=False)
            self._is_first_run = False
            self._app.show_view("vault")
        except Exception as e:
            self._show_error(f"Failed to create vault: {e}")

    def _do_unlock(self, pin: str):
        try:
            full_blob = vault_path().read_bytes()
            if len(full_blob) < 16:
                self._show_error("Vault file corrupted")
                return
            kdf_salt = full_blob[:16]
            inner = full_blob[16:]
            key = derive_key(pin, kdf_salt)
            try:
                plaintext = decrypt_vault(inner, key)
            except WrongPINError:
                zero_key(key)
                self._show_error("Wrong PIN")
                return

            vm = VaultManager()
            vm.deserialize(plaintext)
            self._app.app_state.vault_manager = vm
            self._app.app_state.derived_key = key
            self._app.app_state.encrypted_blob = full_blob
            self._app.app_state.unlock()
            self._app.set_status(locked=False)
            self._app.show_view("vault")
        except FileNotFoundError:
            self._show_error("Vault file not found")
        except WrongPINError:
            self._show_error("Wrong PIN")
        except Exception as e:
            self._show_error(f"Error: {e}")
