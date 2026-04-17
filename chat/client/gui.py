import tkinter as tk
from tkinter import scrolledtext
import sys
sys.path.append("..")

import client
from shared.protocol import TYPE_MESSAGE, TYPE_SERVER, TYPE_ERROR, TYPE_PRIVATE


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


     # take the username typed and passes it to the backend
    def _on_join(self, event=None):
        username = self.username_input.get().strip()

        if not username:
            self.login_error.config(text="Username cannot be empty.")
            return

        self.username = username

        try:
            # send client's username to the connect function (client.py)
            self.sock = client.connect(self.username)
        except Exception as e:
            self.login_error.config(text=f"Could not connect: {e}")
            return

        self.login_frame.destroy()
        self._build_chat_screen()
        # start polling only after chat screen widgets exist
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

    # pushs the chat text own to the network layer
    def _on_send(self, event=None):
        text = self.message_input.get().strip()

        if not text or not self.sock:
            return

        if text.startswith("/msg"):
            # ["/msg", "Bob", "hello"]
            parts = text.split(" ", 2)
            if len(parts) < 3:
                self._append_message(
                    "Usage: /msg <username> <message>\n", tag="error"
                )
                self.message_input.delete(0, tk.END)
                return
            to_username = parts[1]
            private_text = parts[2]
            client.send_private(self.sock, to_username, private_text)

        else:
            # for send the message we call the send_message function (client.py)
            client.send_message(self.sock, self.username, text)

            # prints the message on your own screen
            self._append_message(f"[You]: {text}\n", tag="self")

        # clear the inpur box
        self.message_input.delete(0, tk.END)


    # write the messages other clients sent
    def _poll_queue(self):
        while not client.packet_queue.empty():
            packet = client.packet_queue.get()
            packet_type = packet.get("type")

            if packet_type == TYPE_MESSAGE:
                username = packet.get("username", "?")
                text = packet.get("text", "")
                self._append_message(f"{username}: {text}\n", tag="other")

            elif packet_type == TYPE_SERVER:
                text = packet.get("text", "")
                self._append_message(f"[Server]: {text}\n", tag="server")

            elif packet_type == TYPE_ERROR:
                text = packet.get("text", "")
                self._append_message(f"[ERROR]: {text}\n", tag="error")

            elif packet_type == TYPE_PRIVATE:
                # the sender's echo
                if "to" in packet:
                    self._append_message(
                        f"[Private msg from {packet['to']}]: {packet['text']}\n",
                        tag="private"
                    )

                # recipient seeing incoming msg
                else:
                    self._append_message(
                        f"[Private msg from {packet['from']}]: {packet['text']}\n",
                        tag="private"
                    )

        # loops back and checks again after 100ms later
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
