import customtkinter as ctk

from osskey.app import App


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)

    root = ctk.CTk()
    root.title("OSSKEY")
    root.geometry("650x450")
    root.minsize(600, 400)

    app = App(root)

    def on_close():
        app.on_close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # ─── MOVE THIS RIGHT BEFORE MAINLOOP ───
    # This allows Tkinter to finish initializing the app instance safely
    root.attributes("-topmost", True)

    root.mainloop()


if __name__ == "__main__":
    main()
