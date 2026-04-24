import tkinter as tk
from tkinter import scrolledtext, filedialog, simpledialog
import sys
sys.path.append("..")
import os

import client
from shared.protocol import *


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.sock = None
        self.username = None

        self._progress_widgets = {}

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

        tk.Label(self.login_frame, text="Python Chat", bg="#1e1e2e",
                 fg="#cdd6f4", font=("TkDefaultFont", 22, "bold")).pack(pady=(0, 6))

        tk.Label(self.login_frame, text="Enter a username to join", bg="#1e1e2e",
                 fg="#6c7086", font=("TkDefaultFont", 11)).pack(pady=(0, 24))

        self.username_input = tk.Entry(
            self.login_frame, bg="#313244", fg="#cdd6f4",
            font=("TkDefaultFont", 13), relief=tk.FLAT,
            insertbackground="#cdd6f4", justify=tk.CENTER, width=22
        )
        self.username_input.pack(ipady=8)
        self.username_input.focus()
        self.username_input.bind("<Return>", self._on_join)

        tk.Button(
            self.login_frame, text="Join Chat", command=self._on_join,
            bg="#89b4fa", fg="#1e1e2e", font=("TkDefaultFont", 12, "bold"),
            relief=tk.FLAT, padx=20, pady=8, cursor="hand2",
            activebackground="#b4befe", activeforeground="#1e1e2e"
        ).pack(pady=16)

        self.login_error = tk.Label(
            self.login_frame, text="", bg="#1e1e2e",
            fg="#f38ba8", font=("TkDefaultFont", 10)
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

        title_frame = tk.Frame(self.root, bg="#181825", pady=10)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text="Python Chat", bg="#181825",
                 fg="#cdd6f4", font=("TkDefaultFont", 15, "bold")).pack()

        main_frame = tk.Frame(self.root, bg="#1e1e2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self.chat_display = scrolledtext.ScrolledText(
            main_frame, state=tk.DISABLED, wrap=tk.WORD,
            bg="#181825", fg="#cdd6f4", font=("TkDefaultFont", 11),
            relief=tk.FLAT, padx=10, pady=10,
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        self.chat_display.tag_config("server",  foreground="#a6e3a1")  # green
        self.chat_display.tag_config("self",    foreground="#89b4fa")  # blue
        self.chat_display.tag_config("other",   foreground="#cdd6f4")  # white
        self.chat_display.tag_config("error",   foreground="#f38ba8")  # red
        self.chat_display.tag_config("private", foreground="#f9e2af")  # yellow
        self.chat_display.tag_config("warning", foreground="#fab387")  # orange
        self.chat_display.tag_config("file",    foreground="#cba6f7")  # purple

        # progress area — file transfers show bars here
        self.progress_frame = tk.Frame(self.root, bg="#1e1e2e")
        self.progress_frame.pack(fill=tk.X, padx=10)
        tk.Label(
            self.root,
            text="Tip: /msg <username> <text>  for private messages",
            bg="#1e1e2e", fg="#585b70", font=("TkDefaultFont", 8)
        ).pack(pady=(6, 0))

        input_frame = tk.Frame(self.root, bg="#1e1e2e", pady=10)
        input_frame.pack(fill=tk.X, padx=10)

        # file button
        tk.Button(
            input_frame, text="[+]", command=self._on_file_button,
            bg="#313244", fg="#cdd6f4", font=("TkDefaultFont", 11, "bold"),
            relief=tk.FLAT, padx=10, pady=6, cursor="hand2",
            activebackground="#45475a", activeforeground="#cdd6f4"
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.message_input = tk.Entry(
            input_frame, bg="#313244", fg="#cdd6f4",
            font=("TkDefaultFont", 12), relief=tk.FLAT,
            insertbackground="#cdd6f4",
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.message_input.bind("<Return>", self._on_send)
        self.message_input.focus()

        tk.Button(
            input_frame, text="Send", command=self._on_send,
            bg="#89b4fa", fg="#1e1e2e", font=("TkDefaultFont", 11, "bold"),
            relief=tk.FLAT, padx=16, pady=6, cursor="hand2",
            activebackground="#b4befe", activeforeground="#1e1e2e"
        ).pack(side=tk.RIGHT)

        # dynamic status bar — we keep a reference to update it later
        self.status_var = tk.StringVar(value=f"Connected as {self.username}")
        tk.Label(
            self.root, textvariable=self.status_var,
            bg="#181825", fg="#6c7086", font=("TkDefaultFont", 9),
            anchor=tk.W, padx=10, pady=4
        ).pack(fill=tk.X, side=tk.BOTTOM)

    # -------------------------------------------------------------------------
    # File Button
    # -------------------------------------------------------------------------
    def _on_file_button(self):
        filepath = filedialog.askopenfilename(title="Choose a file to send")
        if not filepath:
            return

        to_username = simpledialog.askstring(
            "Send File",
            f"Send '{os.path.basename(filepath)}' to which user?",
            parent=self.root
        )
        if not to_username or not to_username.strip():
            return

        to_username = to_username.strip()

        filename = os.path.basename(filepath)
        client._pending_files[filename] = filepath

        client.send_file_offer(to_username, filepath)


    # -------------------------------------------------------------------------
    # File Accept/Reject Dialog
    # -------------------------------------------------------------------------
    def _show_file_offer_dialog(self, from_username, filename, filesize):
        size_str = self._format_size(filesize)
        answer = tk.messagebox.askyesno(
            "Incoming File",
            f"{from_username} wants to send you:\n\n"
            f" {filename}  ({size_str})\n\n"
            f"Accept?",
            parent=self.root
        )

        if answer:
            client.accept_file(from_username, filename, filesize)
            self._append_message(
                f"[File] Receiving '{filename}' from {from_username}\n",
                tag="file"
            )
        else:
            client.reject_file(from_username, filename)
            self._append_message(
                f"[File] You rejected '{filename}' from {from_username}.\n",
                tag="warning"
            )


    # -------------------------------------------------------------------------
    # Progress Bar Helpers
    # -------------------------------------------------------------------------

    def _show_progress(self, key, label_text):
        """Create a progress bar row in the progress frame."""
        if key in self._progress_widgets:
            return   # already showing

        frame = tk.Frame(self.progress_frame, bg="#313244", pady=4, padx=6)
        frame.pack(fill=tk.X, pady=2)

        lbl = tk.Label(frame, text=label_text, bg="#313244",
                       fg="#cdd6f4", font=("TkDefaultFont", 9), anchor=tk.W)
        lbl.pack(fill=tk.X)

        bar_bg = tk.Frame(frame, bg="#1e1e2e", height=6)
        bar_bg.pack(fill=tk.X, pady=(2, 0))

        bar_fill = tk.Frame(bar_bg, bg="#89b4fa", height=6, width=0)
        bar_fill.place(x=0, y=0, relheight=1.0, relwidth=0.0)

        self._progress_widgets[key] = (frame, bar_fill, lbl, bar_bg)

    def _update_progress(self, key, percent):
        """Update a progress bar to a given percentage."""
        if key not in self._progress_widgets:
            return
        frame, bar_fill, lbl, bar_bg = self._progress_widgets[key]
        bar_fill.place(relwidth=percent / 100)
        lbl.config(text=f"{lbl.cget('text').split('—')[0].strip()} — {percent}%")

    def _remove_progress(self, key):
        """Remove a progress bar once transfer is complete."""
        if key not in self._progress_widgets:
            return
        frame, bar_fill, lbl, bar_bg = self._progress_widgets[key]
        frame.destroy()
        del self._progress_widgets[key]

    @staticmethod
    def _format_size(size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / 1024 ** 2:.1f} MB"


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

        elif text.startswith("/file "):
            # /file <username>  — alternative to the [+] button
            parts = text.split(" ", 1)
            if len(parts) < 2:
                self._append_message("Usage: /file <username>\n", tag="error")
                self.message_input.delete(0, tk.END)
                return
            to_username = parts[1].strip()
            filepath = filedialog.askopenfilename(title="Choose a file to send")
            if filepath:
                filename = os.path.basename(filepath)
                client._pending_files[filename] = filepath
                client.send_file_offer(to_username, filepath)

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
            # ── file events ───────────────────────────────────────────────────
            elif packet_type == TYPE_FILE_OFFER:
                # incoming file offer — show accept/reject dialog
                self._show_file_offer_dialog(
                    packet.get("from"),
                    packet.get("filename"),
                    packet.get("filesize")
                )

            elif packet_type == TYPE_FILE_REJECT:
                filename = packet.get("filename")
                frm      = packet.get("from", "")
                self._append_message(f"[File] {frm} rejected '{filename}'.\n", tag="file")
                self._remove_progress(filename)

            elif packet_type == TYPE_FILE_DONE:
                filename = packet.get("filename")
                self._append_message(
                    f"[File] '{filename}' transfer complete.\n", tag="file"
                )
                self._remove_progress(filename)

            elif packet_type == "file_waiting":
                filename = packet.get("filename")
                to       = packet.get("to")
                self._append_message(
                    f"[File] Waiting for {to} to accept '{filename}'...\n", tag="file"
                )

            elif packet_type == "file_progress":
                filename = packet.get("filename")
                percent  = packet.get("percent", 0)
                frm      = packet.get("from", packet.get("to", ""))
                label    = f"{'Sending' if 'to' in packet else 'Receiving'} '{filename}' {'to' if 'to' in packet else 'from'} {frm}"

                if filename not in self._progress_widgets:
                    self._show_progress(filename, label)
                self._update_progress(filename, percent)

            elif packet_type == "file_sent":
                filename = packet.get("filename")
                to       = packet.get("to")
                self._append_message(f"[File] '{filename}' sent to {to}.\n", tag="file")
                self._remove_progress(filename)

            elif packet_type == "file_received":
                filename = packet.get("filename")
                filepath = packet.get("filepath")
                frm      = packet.get("from")
                self._append_message(
                    f"[File] '{filename}' from {frm} saved to downloads/\n",
                    tag="file"
                )
                self._remove_progress(filename)

            # ── connection ────────────────────────────────────────────────────
            elif packet_type == TYPE_DISCONNECTED:
                text = packet.get("text", "Disconnected")
                self._append_message(f"\n[!] {text}\n", tag="warning")
                self.status_var.set("Disconnected - reconnecting...")
                # disable input -< user can't send while disconnected
                self.message_input.config(state=tk.DISABLED)

                if packet.get("fatal"):
                    self.status_var.set("Connection lost. Please restart")

            elif packet_type == "reconnecting":
                attempt = packet.get("attempt")
                max = packet.get("max")
                wait = packet.get("wait")
                self.status_var.set(f"Reconnecting... attemt {attempt}/{max} (wait {wait}s)")
                self._append_message(
                    f"[!] Reconnecting... attempt {attempt} / {max}\n", tag="warning"
                )
                self.message_input.config(state=tk.DISABLED)

            elif packet_type == TYPE_RECONNECTED:
                self._append_message(f"\n[+] {packet.get('text', 'Reconnected!')}", tag="server")
                self.status_var.set(f"Connected as {self.username}")

                # reunable input
                self.message_input.config(state=tk.NORMAL)
                self.message_input.focus()

        # loops back and checks again after 100ms later
        self.root.after(100, self._poll_queue)

    def _append_message(self, message, tag="other"):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, message, tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    from tkinter import messagebox
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
