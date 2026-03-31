"""
PostgreSQL SSH Tunnel — Windows GUI Tool
Opens an SSH tunnel: localhost:15432 -> 31.97.119.57 -> 127.0.0.1:5432
Shows connection status and live upload/download transfer speeds.
"""

import tkinter as tk
import threading
import time
import socket
import paramiko
import sys

# ── SSH / Tunnel Configuration ──────────────────────────────────────────────
SSH_HOST       = "31.97.119.57"
SSH_PORT       = 22
SSH_USER       = "root"
SSH_PASSWORD   = "5jZRCl4How;a9j,L"
LOCAL_PORT     = 15432
REMOTE_HOST    = "127.0.0.1"
REMOTE_PORT    = 5432
# ─────────────────────────────────────────────────────────────────────────────

# Catppuccin Mocha palette
BG        = "#1e1e2e"
SURFACE   = "#181825"
OVERLAY   = "#313244"
TEXT      = "#cdd6f4"
SUBTEXT   = "#6c7086"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"
BLUE      = "#89b4fa"
PEACH     = "#fab387"
BORDER    = "#45475a"


# ── Byte counter (thread-safe) ───────────────────────────────────────────────

class ByteCounter:
    def __init__(self):
        self._lock     = threading.Lock()
        self._sent     = 0
        self._received = 0
        self.stop_event = threading.Event()

    def add_sent(self, n: int):
        with self._lock:
            self._sent += n

    def add_received(self, n: int):
        with self._lock:
            self._received += n

    def drain(self):
        """Return and reset accumulated byte counts since last call."""
        with self._lock:
            s, r = self._sent, self._received
            self._sent = self._received = 0
        return s, r


# ── Low-level forwarding ─────────────────────────────────────────────────────

def _pipe(src, dst, counter, direction: str):
    """Shuttle bytes between src and dst, recording them in counter."""
    try:
        while True:
            data = src.recv(8192)
            if not data:
                break
            dst.sendall(data)
            if direction == "up":
                counter.add_sent(len(data))
            else:
                counter.add_received(len(data))
    except Exception:
        pass
    finally:
        for s in (src, dst):
            try:
                s.close()
            except Exception:
                pass


def _handle(client_sock, transport, remote_host, remote_port, counter):
    """Open a paramiko direct-tcpip channel and start bidirectional piping."""
    try:
        peer = client_sock.getpeername()
        chan = transport.open_channel("direct-tcpip", (remote_host, remote_port), peer)
    except Exception:
        client_sock.close()
        return

    threading.Thread(target=_pipe, args=(client_sock, chan,  counter, "up"),   daemon=True).start()
    threading.Thread(target=_pipe, args=(chan, client_sock,  counter, "down"), daemon=True).start()


def run_local_server(transport, local_port, remote_host, remote_port, counter):
    """Accept connections on local_port and forward them through the SSH transport."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    srv.bind(("127.0.0.1", local_port))
    srv.listen(20)
    srv.settimeout(1.0)

    try:
        while not counter.stop_event.is_set():
            try:
                client_sock, _ = srv.accept()
                threading.Thread(
                    target=_handle,
                    args=(client_sock, transport, remote_host, remote_port, counter),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except Exception:
                break
    finally:
        srv.close()


# ── GUI ──────────────────────────────────────────────────────────────────────

class TunnelApp:
    # Pulse animation: colours to cycle through when connected
    PULSE_COLORS = [
        "#a6e3a1", "#a0dca0", "#98d49f", "#a6e3a1",
        "#b3eab0", "#a6e3a1", "#98d49f", "#a0dca0",
    ]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SSH Tunnel")
        self.root.geometry("360x440")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # State
        self._client        = None
        self._transport     = None
        self._counter       = ByteCounter()
        self._connected     = False
        self._connect_time  = None
        self._pulse_idx     = 0

        self._build_ui()
        self._tick()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        tk.Label(self.root, text="PostgreSQL SSH Tunnel",
                 bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(pady=(18, 2))
        tk.Label(self.root,
                 text=f"localhost:{LOCAL_PORT}  →  {SSH_HOST}:{REMOTE_PORT}",
                 bg=BG, fg=SUBTEXT, font=("Segoe UI", 9)).pack()

        # Status circle
        self._canvas = tk.Canvas(self.root, width=120, height=120,
                                 bg=BG, highlightthickness=0)
        self._canvas.pack(pady=(18, 4))
        self._outer = self._canvas.create_oval(8,  8,  112, 112, fill=OVERLAY, outline=BORDER, width=3)
        self._inner = self._canvas.create_oval(24, 24, 96,  96,  fill=OVERLAY, outline="")

        # Status / timer labels
        self._status_var = tk.StringVar(value="Disconnected")
        self._status_lbl = tk.Label(self.root, textvariable=self._status_var,
                                    bg=BG, fg=RED, font=("Segoe UI", 12, "bold"))
        self._status_lbl.pack()

        self._timer_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self._timer_var,
                 bg=BG, fg=SUBTEXT, font=("Segoe UI", 9)).pack(pady=(2, 0))

        # Speed panel
        panel = tk.Frame(self.root, bg=SURFACE)
        panel.pack(fill="x", padx=32, pady=(18, 0), ipady=12)

        up_col = tk.Frame(panel, bg=SURFACE)
        up_col.pack(side="left", expand=True)
        tk.Label(up_col, text="↑  Upload",
                 bg=SURFACE, fg=GREEN, font=("Segoe UI", 8, "bold")).pack()
        self._up_var = tk.StringVar(value="—")
        tk.Label(up_col, textvariable=self._up_var,
                 bg=SURFACE, fg=TEXT, font=("Segoe UI", 13, "bold")).pack()

        tk.Frame(panel, bg=BORDER, width=1).pack(side="left", fill="y", padx=12, pady=6)

        dn_col = tk.Frame(panel, bg=SURFACE)
        dn_col.pack(side="left", expand=True)
        tk.Label(dn_col, text="↓  Download",
                 bg=SURFACE, fg=BLUE, font=("Segoe UI", 8, "bold")).pack()
        self._dn_var = tk.StringVar(value="—")
        tk.Label(dn_col, textvariable=self._dn_var,
                 bg=SURFACE, fg=TEXT, font=("Segoe UI", 13, "bold")).pack()

        # Connect button
        self._btn = tk.Button(
            self.root, text="Connect",
            command=self._toggle,
            bg=GREEN, fg=BG,
            font=("Segoe UI", 11, "bold"),
            relief="flat", bd=0, padx=36, pady=9,
            cursor="hand2",
            activebackground="#94e2d5", activeforeground=BG,
        )
        self._btn.pack(pady=(24, 4))

        # Error label
        self._err_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self._err_var,
                 bg=BG, fg=PEACH, font=("Segoe UI", 8),
                 wraplength=320).pack(pady=(0, 10))

    # ── State helpers ────────────────────────────────────────────────────────

    def _set_connected(self, ok: bool):
        self._connected    = ok
        self._connect_time = time.time() if ok else None

        if ok:
            self._canvas.itemconfig(self._outer, fill=GREEN, outline=GREEN)
            self._canvas.itemconfig(self._inner, fill=GREEN)
            self._status_var.set("Connected")
            self._status_lbl.config(fg=GREEN)
            self._btn.config(text="Disconnect", bg=RED,
                             activebackground="#eba0ac", state="normal")
        else:
            self._canvas.itemconfig(self._outer, fill=OVERLAY, outline=BORDER)
            self._canvas.itemconfig(self._inner, fill=OVERLAY)
            self._status_var.set("Disconnected")
            self._status_lbl.config(fg=RED)
            self._btn.config(text="Connect", bg=GREEN,
                             activebackground="#94e2d5", state="normal")
            self._up_var.set("—")
            self._dn_var.set("—")
            self._timer_var.set("")

    # ── Connect / disconnect ─────────────────────────────────────────────────

    def _toggle(self):
        if not self._connected:
            self._btn.config(state="disabled", text="Connecting…", bg=PEACH)
            self._err_var.set("")
            threading.Thread(target=self._do_connect, daemon=True).start()
        else:
            self._btn.config(state="disabled", text="Disconnecting…", bg=PEACH)
            threading.Thread(target=self._do_disconnect, daemon=True).start()

    def _do_connect(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                SSH_HOST, port=SSH_PORT,
                username=SSH_USER, password=SSH_PASSWORD,
                timeout=15, allow_agent=False, look_for_keys=False,
            )
            self._client    = client
            self._transport = client.get_transport()
            self._counter.stop_event.clear()

            threading.Thread(
                target=run_local_server,
                args=(self._transport, LOCAL_PORT, REMOTE_HOST, REMOTE_PORT, self._counter),
                daemon=True,
            ).start()

            self.root.after(0, lambda: self._set_connected(True))

        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda: self._on_error(msg))

    def _do_disconnect(self):
        self._counter.stop_event.set()
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._client    = None
        self._transport = None
        self.root.after(0, lambda: self._set_connected(False))

    def _on_error(self, msg: str):
        self._err_var.set(f"Error: {msg}")
        self._btn.config(state="normal", text="Connect", bg=GREEN)

    # ── Periodic tick (every 1 s) ────────────────────────────────────────────

    def _tick(self):
        if self._connected:
            # Speed readout
            sent, received = self._counter.drain()
            self._up_var.set(_fmt_speed(sent))
            self._dn_var.set(_fmt_speed(received))

            # Elapsed timer
            if self._connect_time:
                e = int(time.time() - self._connect_time)
                self._timer_var.set(
                    f"Connected  {e // 3600:02d}:{(e % 3600) // 60:02d}:{e % 60:02d}"
                )

            # Pulse animation
            self._pulse_idx = (self._pulse_idx + 1) % len(self.PULSE_COLORS)
            c = self.PULSE_COLORS[self._pulse_idx]
            self._canvas.itemconfig(self._inner, fill=c)

            # Watch for unexpected transport drop
            if self._transport and not self._transport.is_active():
                self._do_disconnect()

        self.root.after(1000, self._tick)

    # ── Window close ────────────────────────────────────────────────────────

    def on_close(self):
        if self._connected:
            self._do_disconnect()
        self.root.destroy()


# ── Utilities ────────────────────────────────────────────────────────────────

def _fmt_speed(bps: int) -> str:
    if bps < 1024:
        return f"{bps} B/s"
    elif bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    else:
        return f"{bps / 1024 / 1024:.2f} MB/s"


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = TunnelApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
