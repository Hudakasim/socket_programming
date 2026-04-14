import tkinter as tk
from tkinter import scrolledtext
import sys
sys.path.append("..")

import client


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.sock = None
        self.username = None

        self._configure_window()
        self._show_login_screen()

    # -------------------------------------------------------------------------
    # Window Setup
    # -------------------------------------------------------------------------

    def _configure_window(self):
        self.root.title("Python Chat")
        self.root.geometry("520x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

    # -------------------------------------------------------------------------
    # Login Screen
    # -------------------------------------------------------------------------

    def _show_login_screen(self):
        self.login_frame = tk.Frame(self.root, bg="#1e1e2e")
        self.login_frame.pack(expand=True)

        tk.Label(
            self.login_frame,
            text="Python Chat",
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("TkDefaultFont", 22, "bold")
        ).pack(pady=(0, 6))

        tk.Label(
            self.login_frame,
            text="Enter a username to join",
            bg="#1e1e2e",
            fg="#6c7086",
            font=("TkDefaultFont", 11)
        ).pack(pady=(0, 24))

        self.username_input = tk.Entry(
            self.login_frame,
            bg="#313244",
            fg="#cdd6f4",
            font=("TkDefaultFont", 13),
            relief=tk.FLAT,
            insertbackground="#cdd6f4",
            justify=tk.CENTER,
            width=22
        )
        self.username_input.pack(ipady=8)
        self.username_input.focus()
        self.username_input.bind("<Return>", self._on_join)

        tk.Button(
            self.login_frame,
            text="Join Chat",
            command=self._on_join,
            bg="#89b4fa",
            fg="#1e1e2e",
            font=("TkDefaultFont", 12, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2",
            activebackground="#b4befe",
            activeforeground="#1e1e2e"
        ).pack(pady=16)

        self.login_error = tk.Label(
            self.login_frame,
            text="",
            bg="#1e1e2e",
            fg="#f38ba8",
            font=("TkDefaultFont", 10)
        )
        self.login_error.pack()

    def _on_join(self, event=None):
        username = self.username_input.get().strip()

        if not username:
            self.login_error.config(text="Username cannot be empty.")
            return

        self.username = username

        try:
            self.sock = client.connect(self.username)
        except Exception as e:
            self.login_error.config(text=f"Could not connect: {e}")
            return

        self.login_frame.destroy()
        self._build_chat_screen()
        self._append_message(f"Connected as {self.username}\n", tag="server")
        self.root.after(100, self._poll_queue)

    # -------------------------------------------------------------------------
    # Chat Screen
    # -------------------------------------------------------------------------

    def _build_chat_screen(self):
        self.root.title(f"Python Chat  —  {self.username}")

        # title bar
        title_frame = tk.Frame(self.root, bg="#181825", pady=10)
        title_frame.pack(fill=tk.X)

        tk.Label(
            title_frame,
            text="Python Chat",
            bg="#181825",
            fg="#cdd6f4",
            font=("TkDefaultFont", 15, "bold")
        ).pack()

        # chat display
        main_frame = tk.Frame(self.root, bg="#1e1e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self.chat_display = scrolledtext.ScrolledText(
            main_frame,
            state=tk.DISABLED,
            wrap=tk.WORD,
            bg="#181825",
            fg="#cdd6f4",
            font=("TkDefaultFont", 11),
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        self.chat_display.tag_config("server", foreground="#a6e3a1")  # green
        self.chat_display.tag_config("self",   foreground="#89b4fa")  # blue
        self.chat_display.tag_config("other",  foreground="#cdd6f4")  # white
        self.chat_display.tag_config("error",  foreground="#f38ba8")  # red

        # input row
        input_frame = tk.Frame(self.root, bg="#1e1e2e", pady=10)
        input_frame.pack(fill=tk.X, padx=10)

        self.message_input = tk.Entry(
            input_frame,
            bg="#313244",
            fg="#cdd6f4",
            font=("TkDefaultFont", 12),
            relief=tk.FLAT,
            insertbackground="#cdd6f4",
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.message_input.bind("<Return>", self._on_send)
        self.message_input.focus()

        tk.Button(
            input_frame,
            text="Send",
            command=self._on_send,
            bg="#89b4fa",
            fg="#1e1e2e",
            font=("TkDefaultFont", 11, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2",
            activebackground="#b4befe",
            activeforeground="#1e1e2e"
        ).pack(side=tk.RIGHT)

        # status bar
        tk.Label(
            self.root,
            text=f"Connected as {self.username}",
            bg="#181825",
            fg="#6c7086",
            font=("TkDefaultFont", 9),
            anchor=tk.W,
            padx=10,
            pady=4
        ).pack(fill=tk.X, side=tk.BOTTOM)

    # -------------------------------------------------------------------------
    # Send & Receive
    # -------------------------------------------------------------------------

    def _on_send(self, event=None):
        message = self.message_input.get().strip()
        if not message or not self.sock:
            return
        client.send_message(self.sock, message)
        self._append_message(f"[You]: {message}\n", tag="self")
        self.message_input.delete(0, tk.END)

    def _poll_queue(self):
        while not client.message_queue.empty():
            message = client.message_queue.get()
            if message.startswith("[Server]:"):
                self._append_message(message + "\n", tag="server")
            else:
                self._append_message(message + "\n", tag="other")
        self.root.after(100, self._poll_queue)

    def _append_message(self, message, tag="other"):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message, tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
