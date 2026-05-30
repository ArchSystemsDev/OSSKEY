import customtkinter as ctk

BG       = "#020a02"
BG2      = "#040e04"
BORDER   = "#1a3a1a"
GREEN    = "#00ff41"
GREEN_DIM= "#1a5a1a"
TEXT     = "#a0c878"
TEXT_DIM = "#2a5a2a"


def confirm_dialog(title: str, message: str, parent=None) -> bool:
    dialog = ctk.CTkToplevel(parent, fg_color=BG)
    dialog.title(title)
    dialog.geometry("380x160")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.grab_set()

    result: list[bool] = [False]

    ctk.CTkLabel(
        dialog, text=message, wraplength=320,
        font=("Consolas", 12), text_color=TEXT
    ).pack(pady=(24, 16))

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=8)

    ctk.CTkButton(
        btn_frame, text="CANCEL", command=dialog.destroy,
        font=("Consolas", 11), width=110, height=32,
        corner_radius=0, fg_color="transparent",
        hover_color=BG2, text_color=TEXT_DIM,
        border_width=1, border_color=BORDER
    ).pack(side="left", padx=6)

    ctk.CTkButton(
        btn_frame, text="CONFIRM", command=lambda: [result.__setitem__(0, True), dialog.destroy()],
        font=("Consolas", 11, "bold"), width=110, height=32,
        corner_radius=0, fg_color="#331111",
        hover_color="#552222", text_color="#ff4444",
        border_width=1, border_color="#552222"
    ).pack(side="left", padx=6)

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()
    return result[0]


def message_dialog(title: str, message: str, parent=None):
    dialog = ctk.CTkToplevel(parent, fg_color=BG)
    dialog.title(title)
    dialog.geometry("380x140")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.grab_set()

    ctk.CTkLabel(
        dialog, text=message, wraplength=320,
        font=("Consolas", 12), text_color=TEXT
    ).pack(pady=(24, 16))

    ctk.CTkButton(
        dialog, text="OK", command=dialog.destroy,
        font=("Consolas", 11), width=110, height=32,
        corner_radius=0, fg_color=GREEN,
        hover_color="#00cc33", text_color="#000000"
    ).pack(pady=4)

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()
