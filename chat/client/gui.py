import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox,
                             QFileDialog, QInputDialog, QVBoxLayout,
                             QWidget, QLabel, QProgressBar)
from PyQt6.QtCore import QTimer
from PyQt6 import uic

import client
from shared.protocol import *

class ChatAppQt(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. LOAD THE UI DESIGN
        uic.loadUi("chat_gui.ui", self)

        # Initialize variables
        self.sock = None
        self.username = None
        self._progress_widgets = {}

        # Layout for the Progress Frame (where progress bars will be added dynamically)
        self.prog_layout = QVBoxLayout(self.progress_frame)
        self.prog_layout.setContentsMargins(0, 0, 0, 0)

        # Show the login page (index 0) initially
        self.stackedWidget.setCurrentIndex(0)

        # 2. CONNECT BUTTONS AND EVENTS (Signals and Slots)
        # Connect the join button and the Enter key on the username input to the join function
        self.join_button.clicked.connect(self._on_join)
        self.username_input.returnPressed.connect(self._on_join)

        # Connect the send button and the Enter key on the message input to the send function
        self.send_btn.clicked.connect(self._on_send)
        self.msg_input.returnPressed.connect(self._on_send)

        # Connect the file button to the file selection function
        self.file_btn.clicked.connect(self._on_file_button)

        # 3. SET UP THE TIMER FOR THE MESSAGE QUEUE
        # Replaces the 'after()' method from Tkinter. Checks the queue every 100ms.
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll_queue)

    # -------------------------------------------------------------------------
    # Login Screen Logic
    # -------------------------------------------------------------------------
    def _on_join(self):
        username = self.username_input.text().strip()
        if not username:
            self.login_error.setText("Username cannot be empty.")
            return

        try:
            # Attempt to connect to the server via the client module
            self.sock = client.connect(username)
            self.username = username
        except Exception as e:
            self.login_error.setText(f"Could not connect: {e}")
            return

        # If successful, switch to the chat page (index 1)
        self.stackedWidget.setCurrentIndex(1)
        self.setWindowTitle(f"Python Chat — {self.username}")
        self.statusbar.showMessage(f"Connected as {self.username}")

        # Start polling the background queue for incoming messages
        self.timer.start(100)

    # -------------------------------------------------------------------------
    # Messaging & Commands Logic
    # -------------------------------------------------------------------------
    def _on_send(self):
        text = self.msg_input.text().strip()
        if not text or not self.sock:
            return

        # Handle private messages (/msg user text)
        if text.startswith("/msg"):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                self._append_message("Usage: /msg <username> <message>", tag="error")
                self.msg_input.clear()
                return
            to_username, private_text = parts[1], parts[2]
            client.send_private(self.sock, to_username, private_text)

        # Handle file transfer command (/file user)
        elif text.startswith("/file "):
            parts = text.split(" ", 1)
            if len(parts) < 2:
                self._append_message("Usage: /file <username>", tag="error")
                self.msg_input.clear()
                return
            to_username = parts[1].strip()
            # Open a file dialog to select the file to send
            filepath, _ = QFileDialog.getOpenFileName(self, "Choose a file to send")
            if filepath:
                self._process_file_offer(filepath, to_username)

        # Handle standard public messages
        else:
            client.send_message(self.sock, self.username, text)
            self._append_message(f"[You]: {text}", tag="self")

        # Clear the input box after sending
        self.msg_input.clear()

    def _append_message(self, message, tag="other"):
        # Define HTML color codes based on the message tag
        colors = {
            "server": "#a6e3a1",
            "self": "#89b4fa",
            "other": "#cdd6f4",
            "error": "#f38ba8",
            "private": "#f9e2af",
            "warning": "#fab387",
            "file": "#cba6f7"
        }
        color = colors.get(tag, "#cdd6f4")
        # Format the message using HTML for the QTextBrowser
        html_msg = f'<div style="color: {color}; margin-bottom: 4px; font-family: sans-serif;">{message}</div>'
        self.chat_display.append(html_msg)

    # -------------------------------------------------------------------------
    # File Transfer Logic
    # -------------------------------------------------------------------------
    def _on_file_button(self):
        # Open file dialog
        filepath, _ = QFileDialog.getOpenFileName(self, "Choose a file to send")
        if not filepath:
            return

        # Open an input dialog to ask who to send the file to
        to_username, ok = QInputDialog.getText(self, "Send File", f"Send '{os.path.basename(filepath)}' to which user?")
        if ok and to_username.strip():
            self._process_file_offer(filepath, to_username.strip())

    def _process_file_offer(self, filepath, to_username):
        filename = os.path.basename(filepath)
        # Store the file path in the client's pending files dictionary
        client._pending_files[filename] = filepath
        # Send the file offer packet to the server
        client.send_file_offer(to_username, filepath)

    def _show_file_offer_dialog(self, from_username, filename, filesize):
        size_str = self._format_size(filesize)
        # Display a Yes/No message box using PyQt6
        reply = QMessageBox.question(
            self, "Incoming File",
            f"{from_username} wants to send you:\n\n{filename} ({size_str})\n\nAccept?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            client.accept_file(from_username, filename, filesize)
            self._append_message(f"[File] Receiving '{filename}' from {from_username}", tag="file")
        else:
            client.reject_file(from_username, filename)
            self._append_message(f"[File] You rejected '{filename}' from {from_username}.", tag="warning")

    # -------------------------------------------------------------------------
    # Progress Bar Logic
    # -------------------------------------------------------------------------
    def _show_progress(self, key, label_text):
        if key in self._progress_widgets:
            return

        # Create a container widget and a vertical layout for the label and progress bar
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 5, 0, 5)

        # Create the label
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #cdd6f4;")

        # Create PyQt6's built-in QProgressBar
        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setValue(0)
        pbar.setTextVisible(True)
        # Apply custom CSS styling to match the dark theme
        pbar.setStyleSheet("QProgressBar { background-color: #1e1e2e; color: white; border: 1px solid #313244; }"
                           "QProgressBar::chunk { background-color: #89b4fa; }")

        # Add widgets to the container's layout
        layout.addWidget(lbl)
        layout.addWidget(pbar)

        # Add the container to the main progress frame layout on the UI
        self.prog_layout.addWidget(container)
        # Store references so we can update or delete them later
        self._progress_widgets[key] = (container, pbar, lbl)

    def _update_progress(self, key, percent):
        if key in self._progress_widgets:
            container, pbar, lbl = self._progress_widgets[key]
            pbar.setValue(percent)

    def _remove_progress(self, key):
        if key in self._progress_widgets:
            container, pbar, lbl = self._progress_widgets[key]
            # Safely delete the widget from the UI
            container.deleteLater()
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
    # Background Queue Listener
    # -------------------------------------------------------------------------
    def _poll_queue(self):
        # Check if there are any packets from the background network thread
        while not client.packet_queue.empty():
            packet = client.packet_queue.get()
            packet_type = packet.get("type")

            if packet_type == TYPE_MESSAGE:
                self._append_message(f"{packet.get('username')}: {packet.get('text')}", tag="other")

            elif packet_type == TYPE_SERVER:
                self._append_message(f"[Server]: {packet.get('text')}", tag="server")

            elif packet_type == TYPE_ERROR:
                self._append_message(f"[ERROR]: {packet.get('text')}", tag="error")

            elif packet_type == TYPE_PRIVATE:
                if packet.get("from") == "You":
                    self._append_message(f"[Private to {packet['to']}]: {packet['text']}", tag="private")

                else:
                    sender = packet.get("from") or packet.get("to", "Unknown")
                    self._append_message(f"[Private from {sender}]: {packet['text']}", tag="private")

            elif packet_type == TYPE_FILE_OFFER:
                self._show_file_offer_dialog(packet.get("from"), packet.get("filename"), packet.get("filesize"))

            elif packet_type == TYPE_FILE_REJECT:
                filename = packet.get("filename")
                self._append_message(f"[File] {packet.get('from', '')} rejected '{filename}'.", tag="file")
                self._remove_progress(filename)

            elif packet_type == TYPE_FILE_DONE:
                filename = packet.get("filename")
                self._append_message(f"[File] '{filename}' transfer complete.", tag="file")
                self._remove_progress(filename)

            elif packet_type == "file_waiting":
                self._append_message(f"[File] Waiting for {packet.get('to')} to accept '{packet.get('filename')}'...", tag="file")

            elif packet_type == "file_progress":
                filename = packet.get("filename")
                percent = packet.get("percent", 0)
                frm = packet.get("from", packet.get("to", ""))

                label = f"{'Sending' if 'to' in packet else 'Receiving'} '{filename}' {'to' if 'to' in packet else 'from'} {frm}"
                if filename not in self._progress_widgets:
                    self._show_progress(filename, label)
                self._update_progress(filename, percent)

            elif packet_type == "file_sent":
                filename = packet.get("filename")
                self._append_message(f"[File] '{filename}' sent to {packet.get('to')}.", tag="file")
                self._remove_progress(filename)

            elif packet_type == "file_received":
                filename = packet.get("filename")
                self._append_message(f"[File] '{filename}' from {packet.get('from')} saved to downloads/", tag="file")
                self._remove_progress(filename)

            elif packet_type == TYPE_DISCONNECTED:
                self._append_message(f"[!] {packet.get('text')}", tag="warning")
                self.statusbar.showMessage("Disconnected - reconnecting...")
                # Lock the input field when disconnected
                self.msg_input.setEnabled(False)

            elif packet_type == "reconnecting":
                self.statusbar.showMessage(f"Reconnecting... attempt {packet.get('attempt')}/{packet.get('max')}")
                self.msg_input.setEnabled(False)

            elif packet_type == TYPE_RECONNECTED:
                self._append_message(f"[+] {packet.get('text', 'Reconnected!')}", tag="server")
                self.statusbar.showMessage(f"Connected as {self.username}")
                # Unlock and refocus the input field when reconnected
                self.msg_input.setEnabled(True)
                self.msg_input.setFocus()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatAppQt()
    window.show()
    sys.exit(app.exec())
