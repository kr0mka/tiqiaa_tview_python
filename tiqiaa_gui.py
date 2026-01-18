#!/usr/bin/env python3
"""
Tiqiaa TView USB IR - Graphical User Interface

A simple Tkinter GUI for sending and learning IR codes.

Features:
    - Click: sends tap code (quick single press)
    - Hold: sends codes repeatedly (like holding a remote button)
    - Learn new IR codes interactively
    - Auto-refresh device connection

Based on protocol work from: https://gitlab.com/XenRE/tiqiaa-usb-ir
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time

from tiqiaa import (
    TiqiaaIR,
    list_ir_codes,
    load_smart_code,
    save_ir_code,
    delete_ir_code,
    __version__,
)


class IRRemoteGUI:
    """Main GUI application for the Tiqiaa IR transceiver."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Tiqiaa IR Remote v{__version__}")
        self.root.resizable(True, True)
        self.root.minsize(400, 300)

        self.ir = None
        self.sending = False
        self.send_thread = None
        self.current_code = None
        self.send_lock = threading.Lock()

        self._setup_ui()
        self._connect_device()

    def _setup_ui(self):
        """Set up the user interface."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Status bar
        self.status_var = tk.StringVar(value="Connecting...")
        self.status_label = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            font=('Arial', 10)
        )
        self.status_label.grid(row=0, column=0, columnspan=3, pady=(0, 5), sticky="w")

        # Hint text
        hint_label = ttk.Label(
            main_frame,
            text="Click: single send | Hold: repeat send",
            font=('Arial', 8),
            foreground='gray'
        )
        hint_label.grid(row=1, column=0, columnspan=3, pady=(0, 10), sticky="w")

        # IR codes buttons frame
        self.buttons_frame = ttk.LabelFrame(main_frame, text="IR Codes", padding="5")
        self.buttons_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))

        self._load_buttons()

        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, sticky="ew")

        ttk.Button(
            control_frame,
            text="Learn New",
            command=self._learn_code
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            control_frame,
            text="Refresh",
            command=self._refresh
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            control_frame,
            text="Delete...",
            command=self._delete_code
        ).pack(side=tk.LEFT)

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

    def _load_buttons(self):
        """Load IR code buttons into the grid."""
        # Clear existing buttons
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()

        codes = list_ir_codes()

        if not codes:
            ttk.Label(
                self.buttons_frame,
                text="No IR codes found.\nUse 'Learn New' to add codes.",
                justify=tk.CENTER
            ).grid(padx=20, pady=20)
            return

        # Create button grid
        cols = 3
        for i, name in enumerate(codes):
            row = i // cols
            col = i % cols

            btn = tk.Button(
                self.buttons_frame,
                text=name,
                width=15,
                height=2,
                font=('Arial', 10, 'bold'),
                bg='#e0e0e0',
                activebackground='#c0c0c0'
            )
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # Bind mouse events for click/hold behavior
            btn.bind('<ButtonPress-1>', lambda e, n=name: self._on_press(n))
            btn.bind('<ButtonRelease-1>', lambda e: self._on_release())

        # Configure column weights
        for c in range(cols):
            self.buttons_frame.columnconfigure(c, weight=1)

    def _connect_device(self):
        """Connect to the IR device in background thread."""
        def connect():
            self.ir = TiqiaaIR()
            if self.ir.open(verbose=False):
                self.status_var.set("Connected - Ready to send")
            else:
                self.status_var.set("Device not found - Click Refresh")
                self.ir = None

        threading.Thread(target=connect, daemon=True).start()

    def _on_press(self, code_name: str):
        """Handle button press - start sending."""
        if not self.ir:
            self.status_var.set("Device not connected! Click Refresh")
            return

        # Stop any previous send
        self.sending = False
        if self.send_thread and self.send_thread.is_alive():
            self.send_thread.join(timeout=0.05)

        self.sending = True
        self.current_code = code_name
        self.status_var.set(f"Sending: {code_name}")

        # Start send loop in background
        self.send_thread = threading.Thread(
            target=self._send_loop,
            args=(code_name,),
            daemon=True
        )
        self.send_thread.start()

    def _on_release(self):
        """Handle button release - stop sending."""
        self.sending = False
        if self.current_code:
            self.status_var.set(f"Sent: {self.current_code}")
        self.current_code = None

    def _send_loop(self, code_name: str):
        """Background thread for sending IR codes."""
        codes = load_smart_code(code_name)
        if codes is None:
            self.status_var.set(f"Error loading: {code_name}")
            return

        freq = codes['freq']
        tap_code = codes['tap']
        full_code = codes['full']

        # Send tap code immediately
        with self.send_lock:
            if not self.sending:
                return
            try:
                if self.ir:
                    self.ir.send_ir(tap_code, freq)
            except Exception as e:
                self.status_var.set(f"Error: {e}")
                self.ir = None
                return

        # Small delay to detect hold
        time.sleep(0.15)

        # If still holding, send full code repeatedly
        while self.sending:
            with self.send_lock:
                if not self.sending:
                    break
                try:
                    if self.ir:
                        self.ir.send_ir(full_code, freq)
                except Exception as e:
                    self.status_var.set(f"Error: {e}")
                    self.ir = None
                    break
            time.sleep(0.08)  # ~12 codes per second

    def _learn_code(self):
        """Open dialog to learn a new IR code."""
        # Get code name
        name = simpledialog.askstring(
            "Learn IR Code",
            "Enter a name for this IR code:",
            parent=self.root
        )

        if not name:
            return

        # Sanitize name
        name = name.strip().replace(' ', '_')
        if not name:
            return

        if not self.ir:
            messagebox.showerror(
                "Error",
                "Device not connected. Click Refresh first."
            )
            return

        # Show learning dialog
        self.status_var.set(f"Learning '{name}' - Press remote button...")

        def learn():
            try:
                ir_data = self.ir.receive_ir(timeout_sec=15, verbose=False)
                if ir_data:
                    save_ir_code(name, ir_data)
                    self.status_var.set(f"Learned and saved: {name}")
                    # Refresh buttons on main thread
                    self.root.after(0, self._load_buttons)
                else:
                    self.status_var.set("Learning failed - timeout")
            except Exception as e:
                self.status_var.set(f"Learning error: {e}")

        threading.Thread(target=learn, daemon=True).start()

    def _delete_code(self):
        """Open dialog to delete an IR code."""
        codes = list_ir_codes()
        if not codes:
            messagebox.showinfo("Delete Code", "No codes to delete.")
            return

        # Simple dialog to select code
        name = simpledialog.askstring(
            "Delete IR Code",
            f"Enter name to delete:\n\nAvailable: {', '.join(codes)}",
            parent=self.root
        )

        if not name:
            return

        name = name.strip()
        if name not in codes:
            messagebox.showerror("Error", f"Code '{name}' not found.")
            return

        # Confirm deletion
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete IR code '{name}'?"
        ):
            if delete_ir_code(name):
                self.status_var.set(f"Deleted: {name}")
                self._load_buttons()
            else:
                messagebox.showerror("Error", f"Failed to delete '{name}'")

    def _refresh(self):
        """Refresh buttons and reconnect device."""
        self._load_buttons()

        # Stop any ongoing sends
        self.sending = False
        if self.send_thread and self.send_thread.is_alive():
            self.send_thread.join(timeout=0.2)

        # Reconnect device
        with self.send_lock:
            if self.ir:
                try:
                    self.ir.close()
                except:
                    pass
                self.ir = None

        self.status_var.set("Reconnecting...")
        self._connect_device()

    def run(self):
        """Run the application."""
        def on_close():
            self.sending = False
            if self.send_thread and self.send_thread.is_alive():
                self.send_thread.join(timeout=0.2)
            with self.send_lock:
                if self.ir:
                    self.ir.close()
            self.root.destroy()

        self.root.protocol("WM_DELETE_WINDOW", on_close)
        self.root.mainloop()


def main():
    """Entry point for the GUI application."""
    app = IRRemoteGUI()
    app.run()


if __name__ == "__main__":
    main()
