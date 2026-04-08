"""
=============================================================
  CMPT 371 - Assignment 3: Chat GUI Client
=============================================================
  File    : gui_client.py
  Purpose : Premium Tkinter GUI chat client. Connects to the
            TCP server via client.py. Features animated
            message bubbles, live typing indicators, emoji
            picker, gradient animated header, glowing input
            borders, click-to-PM from sidebar, flash
            animations on new messages, and a polished
            cyberpunk-luxe dark theme.
  Usage   : python gui_client.py [--host HOST] [--port PORT]
=============================================================
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox
import argparse
import threading
import datetime
import re
import math

from client import ChatClient


# ─────────────────────────────────────────────────────────────
#  Colour Palette
# ─────────────────────────────────────────────────────────────
P = {
    "bg_root"      : "#070b14",
    "bg_sidebar"   : "#0a0f1e",
    "bg_chat"      : "#070b14",
    "bg_header"    : "#0c1120",
    "bg_input_bar" : "#0c1120",
    "bg_entry"     : "#111827",
    "bg_bubble_me" : "#0d2847",
    "bg_bubble_ot" : "#111827",
    "bg_hover"     : "#151c2e",
    "bg_login"     : "#080c18",
    "fg_main"      : "#e2e8f0",
    "fg_dim"       : "#4b5563",
    "fg_dimmer"    : "#2d3748",
    "fg_accent"    : "#22d3ee",
    "fg_other"     : "#c084fc",
    "fg_system"    : "#fbbf24",
    "fg_private"   : "#34d399",
    "fg_error"     : "#f87171",
    "fg_online"    : "#22c55e",
    "border"       : "#1e293b",
    "glow_me"      : "#0e4f7a",
    "glow_ot"      : "#1e293b",
}

AVATAR_POOL = [
    "#22d3ee", "#c084fc", "#f472b6", "#34d399",
    "#fb923c", "#facc15", "#60a5fa", "#a78bfa",
]

EMOJI_LIST = [
    "😀","😂","😍","🔥","👍","❤️","😭","🙏",
    "💯","🎉","😎","🤔","😅","👀","💀","✨",
    "🚀","😤","🥺","😊","🤣","😢","😡","🎯",
]


def _ts():
    return datetime.datetime.now().strftime("%H:%M")


def _initials(name):
    parts = name.split()
    return (parts[0][0] + parts[1][0]).upper() if len(parts) >= 2 else name[:2].upper()


# ─────────────────────────────────────────────────────────────
#  Animated bouncing dots (typing indicator)
# ─────────────────────────────────────────────────────────────
class TypingDots(tk.Frame):
    """Three animated bouncing dots shown as a typing indicator."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=P["bg_bubble_ot"], **kw)
        self._dots   = []
        self._phases = [0, 4, 8]
        self._running = False
        for i in range(3):
            c = tk.Canvas(self, width=8, height=8,
                          bg=P["bg_bubble_ot"], highlightthickness=0)
            c.pack(side="left", padx=2)
            c.create_oval(0, 0, 8, 8, fill=P["fg_dim"], outline="", tags="dot")
            self._dots.append(c)

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running:
            return
        for i, (c, ph) in enumerate(zip(self._dots, self._phases)):
            brightness = 0.3 + 0.7 * max(0, math.sin(ph * 0.4))
            val = int(brightness * 160)
            color = f"#{val:02x}{min(val+40,255):02x}{min(val+60,255):02x}"
            c.itemconfig("dot", fill=color)
            self._phases[i] += 1
        self.after(80, self._animate)


# ─────────────────────────────────────────────────────────────
#  Emoji Picker popup
# ─────────────────────────────────────────────────────────────
class EmojiPicker(tk.Toplevel):
    """Floating emoji grid that inserts into the message input."""
    def __init__(self, parent, input_var, anchor_widget):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=P["bg_header"])
        self._input_var = input_var
        x = anchor_widget.winfo_rootx()
        y = anchor_widget.winfo_rooty() - 160
        self.geometry(f"280x140+{x}+{y}")
        frame = tk.Frame(self, bg=P["bg_header"], padx=6, pady=6)
        frame.pack(fill="both", expand=True)
        for i, em in enumerate(EMOJI_LIST):
            btn = tk.Button(
                frame, text=em, font=("Segoe UI Emoji", 14),
                bg=P["bg_header"], fg=P["fg_main"],
                activebackground=P["bg_hover"],
                relief="flat", cursor="hand2", width=2,
                command=lambda e=em: self._insert(e),
            )
            btn.grid(row=i // 8, column=i % 8, padx=1, pady=1)
        self.bind("<FocusOut>", lambda e: self.destroy())
        self.focus_set()

    def _insert(self, emoji):
        self._input_var.set(self._input_var.get() + emoji)
        self.destroy()


# ─────────────────────────────────────────────────────────────
#  Animated gradient title canvas
# ─────────────────────────────────────────────────────────────
class GradientTitle(tk.Canvas):
    """
    Draws app title with a slowly shifting cyan->violet gradient
    by interpolating colour per character each frame.
    """
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=P["bg_header"],
                         highlightthickness=0, height=38, **kw)
        self._phase = 0
        self._animate()

    def _lerp(self, c1, c2, t):
        r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        r = int(r1 + (r2-r1)*t)
        g = int(g1 + (g2-g1)*t)
        b = int(b1 + (b2-b1)*t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _animate(self):
        self.delete("all")
        self._phase += 0.025
        text   = "  NEXUS CHAT  "
        colors = ["#22d3ee", "#818cf8", "#c084fc", "#22d3ee"]
        x = 12
        for i, ch in enumerate(text):
            t   = (math.sin(self._phase + i * 0.35) + 1) / 2
            seg = t * (len(colors) - 1)
            idx = int(seg)
            frac = seg - idx
            c1  = colors[min(idx,   len(colors)-1)]
            c2  = colors[min(idx+1, len(colors)-1)]
            col = self._lerp(c1, c2, frac)
            self.create_text(x, 19, text=ch, fill=col,
                             font=("Courier New", 16, "bold"), anchor="w")
            x += 13
        self.after(45, self._animate)


# ─────────────────────────────────────────────────────────────
#  Shimmer separator canvas
# ─────────────────────────────────────────────────────────────
class ShimmerLine(tk.Canvas):
    """A 2px line that shimmers with a travelling cyan glow."""
    def __init__(self, parent, **kw):
        super().__init__(parent, height=2, bg=P["bg_login"],
                         highlightthickness=0, **kw)
        self._phase = 0
        self._animate()

    def _animate(self):
        self._phase += 0.08
        w = self.winfo_width() or 380
        self.delete("all")
        for x in range(0, w, 2):
            t = (math.sin(self._phase + x * 0.03) + 1) / 2
            val = int(20 + t * 180)
            color = f"#{0:02x}{val:02x}{min(val+60,255):02x}"
            self.create_line(x, 0, x+2, 0, fill=color, width=2)
        self.after(35, self._animate)


# ─────────────────────────────────────────────────────────────
#  Login Screen
# ─────────────────────────────────────────────────────────────
class LoginScreen(tk.Toplevel):
    """Animated login dialog — collects host, port, username."""

    def __init__(self, master, on_connect_cb):
        super().__init__(master)
        self.on_connect_cb = on_connect_cb
        self.title("Nexus Chat — Connect")
        self.resizable(False, False)
        self.configure(bg=P["bg_login"])
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", master.destroy)
        self._build()
        self._centre()

    def _centre(self):
        self.update_idletasks()
        w, h = 440, 580
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        # Animated title
        GradientTitle(self, width=440).pack(fill="x")

        tk.Label(self, text="TCP Chat Application  •  CMPT 371",
                 bg=P["bg_login"], fg=P["fg_dim"],
                 font=("Courier New", 9)).pack(pady=(0, 4))

        ShimmerLine(self).pack(fill="x", padx=30, pady=(0, 4))

        form = tk.Frame(self, bg=P["bg_login"], padx=40, pady=16)
        form.pack(fill="both", expand=True)

        def field(label, default=""):
            tk.Label(form, text=label, bg=P["bg_login"], fg=P["fg_dim"],
                     font=("Courier New", 8), anchor="w").pack(fill="x", pady=(12, 3))
            wrap = tk.Frame(form, bg=P["border"], pady=1, padx=1)
            wrap.pack(fill="x")
            var = tk.StringVar(value=default)
            e = tk.Entry(wrap, textvariable=var, bg=P["bg_entry"],
                         fg=P["fg_main"], insertbackground=P["fg_accent"],
                         relief="flat", font=("Courier New", 12),
                         highlightthickness=0)
            e.pack(fill="x", ipady=9, padx=1)
            def fi(_): wrap.config(bg=P["fg_accent"])
            def fo(_): wrap.config(bg=P["border"])
            e.bind("<FocusIn>",  fi)
            e.bind("<FocusOut>", fo)
            return var, e

        self.host_var, _          = field("⬡  SERVER HOST", "127.0.0.1")
        self.port_var, _          = field("⬡  PORT",        "9090")
        self.user_var, user_entry = field("⬡  YOUR CALLSIGN")

        self.status_var = tk.StringVar()
        tk.Label(form, textvariable=self.status_var,
                 bg=P["bg_login"], fg=P["fg_error"],
                 font=("Courier New", 9), wraplength=340).pack(pady=(10, 0))

        btn_wrap = tk.Frame(self, bg=P["bg_login"], padx=40, pady=14)
        btn_wrap.pack(fill="x")

        self.btn = tk.Button(
            btn_wrap, text="⟶  CONNECT",
            bg=P["fg_accent"], fg=P["bg_root"],
            activebackground="#06b6d4", activeforeground=P["bg_root"],
            font=("Courier New", 13, "bold"),
            relief="flat", cursor="hand2",
            command=self._attempt, pady=11,
        )
        self.btn.pack(fill="x")
        self.btn.bind("<Enter>", lambda e: self.btn.config(bg="#38bdf8"))
        self.btn.bind("<Leave>", lambda e: self.btn.config(bg=P["fg_accent"]))

        tk.Label(self, text="Messages travel over TCP • socket programming",
                 bg=P["bg_login"], fg=P["fg_dimmer"],
                 font=("Courier New", 8)).pack(pady=(0, 10))

        self.bind("<Return>", lambda e: self._attempt())
        user_entry.focus_set()

    def _attempt(self):
        host     = self.host_var.get().strip()
        port_str = self.port_var.get().strip()
        username = self.user_var.get().strip()

        if not host:
            self.status_var.set("⚠  Host cannot be empty.")
            return
        if not port_str.isdigit():
            self.status_var.set("⚠  Port must be a number.")
            return
        port = int(port_str)
        if not (1 <= port <= 65535):
            self.status_var.set("⚠  Port out of range (1-65535).")
            return
        if not username:
            self.status_var.set("⚠  Callsign cannot be empty.")
            return
        if len(username) > 24:
            self.status_var.set("⚠  Callsign too long (max 24).")
            return

        self.btn.config(text="Connecting...", state="disabled", bg=P["fg_dim"])
        self.status_var.set("")
        self.update()
        threading.Thread(target=self.on_connect_cb,
                         args=(host, port, username, self),
                         daemon=True).start()

    def show_error(self, msg):
        self.btn.config(text="⟶  CONNECT", state="normal", bg=P["fg_accent"])
        self.status_var.set(f"✖  {msg}")


# ─────────────────────────────────────────────────────────────
#  Main Chat Window
# ─────────────────────────────────────────────────────────────
class ChatWindow(tk.Tk):
    """
    Primary application window.
    Layout:
      Header (animated gradient title + status)
      ├─ Sidebar (online users + commands + stats)
      └─ Chat area (scrollable bubbles)
           └─ Input bar (emoji + text entry + send)
    """

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("Nexus Chat")
        self.configure(bg=P["bg_root"])
        self.geometry("1100x720")
        self.minsize(800, 520)

        self._client        = None
        self._username      = ""
        self._avatar_map    = {}
        self._colour_idx    = 0
        self._online_users  = []
        self._typing_widget = None
        self._msg_count     = 0

        self._build_fonts()
        self._build_ui()
        self.after(60, self._show_login)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_fonts(self):
        self.fn         = tkfont.Font(family="Courier New", size=11)
        self.fn_bold    = tkfont.Font(family="Courier New", size=11, weight="bold")
        self.fn_sm      = tkfont.Font(family="Courier New", size=9)
        self.fn_sm_bold = tkfont.Font(family="Courier New", size=9,  weight="bold")
        self.fn_input   = tkfont.Font(family="Courier New", size=12)

    # ── Layout ────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        body = tk.Frame(self, bg=P["bg_root"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self._build_sidebar(body)
        self._build_chat_panel(body)

    def _build_header(self):
        hdr = tk.Frame(self, bg=P["bg_header"], height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        GradientTitle(hdr, width=340).pack(side="left", padx=10)

        right = tk.Frame(hdr, bg=P["bg_header"])
        right.pack(side="right", padx=16)

        self._conn_dot = tk.Label(right, text="●", bg=P["bg_header"],
                                  fg=P["fg_dim"], font=self.fn)
        self._conn_dot.pack(side="right", padx=(4, 0))

        self._conn_lbl = tk.Label(right, text="offline",
                                  bg=P["bg_header"], fg=P["fg_dim"],
                                  font=self.fn_sm)
        self._conn_lbl.pack(side="right")

        # Neon cyan accent line under header
        tk.Frame(self, bg=P["fg_accent"], height=1).pack(fill="x")

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=P["bg_sidebar"], width=240)
        sb.grid(row=0, column=0, sticky="ns")
        sb.grid_propagate(False)

        tk.Label(sb, text="ONLINE", bg=P["bg_sidebar"], fg=P["fg_accent"],
                 font=self.fn_sm_bold, anchor="w").pack(fill="x", padx=16, pady=(20, 6))

        self._users_frame = tk.Frame(sb, bg=P["bg_sidebar"])
        self._users_frame.pack(fill="x")

        tk.Frame(sb, bg=P["border"], height=1).pack(fill="x", padx=14, pady=12)

        tk.Label(sb, text="COMMANDS", bg=P["bg_sidebar"], fg=P["fg_accent"],
                 font=self.fn_sm_bold, anchor="w").pack(fill="x", padx=16, pady=(0, 8))

        for cmd, desc in [("/list",           "show who's online"),
                          ("/msg <user> <m>", "private message"),
                          ("/quit",           "disconnect & exit")]:
            row = tk.Frame(sb, bg=P["bg_sidebar"])
            row.pack(fill="x", padx=14, pady=2)
            tk.Label(row, text=cmd,  bg=P["bg_sidebar"], fg=P["fg_accent"],
                     font=self.fn_sm, anchor="w").pack(fill="x")
            tk.Label(row, text=desc, bg=P["bg_sidebar"], fg=P["fg_dim"],
                     font=self.fn_sm, anchor="w").pack(fill="x")

        tk.Frame(sb, bg=P["border"], height=1).pack(fill="x", padx=14, pady=12)

        self._stats_var = tk.StringVar(value="Messages: 0")
        tk.Label(sb, textvariable=self._stats_var,
                 bg=P["bg_sidebar"], fg=P["fg_dim"],
                 font=self.fn_sm, anchor="w").pack(fill="x", padx=16)

        tk.Frame(sb, bg=P["border"], height=1).pack(fill="x", padx=14, pady=12)

        tk.Label(sb, text="💡 Click a username\n    to private message",
                 bg=P["bg_sidebar"], fg=P["fg_dim"],
                 font=self.fn_sm, justify="left").pack(fill="x", padx=16, pady=(0, 8))

        tk.Frame(sb, bg=P["border"], height=1).pack(fill="x", padx=14, pady=4)

        disc = tk.Button(sb, text="⏻  DISCONNECT",
                         bg="#1a0a0a", fg=P["fg_error"],
                         activebackground="#2a1010", activeforeground=P["fg_error"],
                         font=self.fn_sm, relief="flat", cursor="hand2",
                         command=self._on_close)
        disc.pack(fill="x", padx=14, pady=8, ipady=6)

        # Right border
        tk.Frame(parent, bg=P["border"], width=1).grid(row=0, column=0, sticky="nse")

    def _build_chat_panel(self, parent):
        panel = tk.Frame(parent, bg=P["bg_chat"])
        panel.grid(row=0, column=1, sticky="nsew")
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)

        # Scrollable canvas
        outer = tk.Frame(panel, bg=P["bg_chat"])
        outer.grid(row=0, column=0, sticky="nsew")

        self._canvas = tk.Canvas(outer, bg=P["bg_chat"],
                                 highlightthickness=0, bd=0)
        self._canvas.pack(side="left", fill="both", expand=True)

        vsb = tk.Scrollbar(outer, orient="vertical",
                           command=self._canvas.yview,
                           bg=P["bg_sidebar"], troughcolor=P["bg_root"],
                           width=7, relief="flat", bd=0)
        vsb.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._msgs = tk.Frame(self._canvas, bg=P["bg_chat"])
        self._cwin = self._canvas.create_window((0, 0), window=self._msgs, anchor="nw")

        self._msgs.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
            lambda e: self._canvas.itemconfig(self._cwin, width=e.width))

        self._canvas.bind_all("<MouseWheel>", self._wheel)
        self._canvas.bind_all("<Button-4>",   self._wheel)
        self._canvas.bind_all("<Button-5>",   self._wheel)

        self._build_input_bar(panel)

    def _build_input_bar(self, parent):
        # Accent top border
        tk.Frame(parent, bg=P["fg_accent"], height=1).grid(row=1, column=0, sticky="ew")

        bar = tk.Frame(parent, bg=P["bg_input_bar"], pady=10, padx=12)
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        # Emoji button
        emoji_btn = tk.Button(
            bar, text="😊",
            bg=P["bg_input_bar"], fg=P["fg_main"],
            activebackground=P["bg_hover"],
            font=("Segoe UI Emoji", 14),
            relief="flat", cursor="hand2", width=2,
            command=self._open_emoji,
        )
        emoji_btn.grid(row=0, column=0, padx=(0, 8))
        self._emoji_anchor = emoji_btn

        # Entry with glowing border
        self._entry_wrap = tk.Frame(bar, bg=P["border"], pady=1, padx=1)
        self._entry_wrap.grid(row=0, column=1, sticky="ew")

        self._input_var   = tk.StringVar()
        self._input_entry = tk.Entry(
            self._entry_wrap, textvariable=self._input_var,
            bg=P["bg_entry"], fg=P["fg_main"],
            insertbackground=P["fg_accent"],
            relief="flat", font=self.fn_input,
            highlightthickness=0, state="disabled",
        )
        self._input_entry.pack(fill="x", ipady=9, padx=1)
        self._input_entry.bind("<FocusIn>",  lambda e: self._entry_wrap.config(bg=P["fg_accent"]))
        self._input_entry.bind("<FocusOut>", lambda e: self._entry_wrap.config(bg=P["border"]))
        self._input_entry.bind("<Return>", lambda e: self._send())

        # Send button
        self._send_btn = tk.Button(
            bar, text="SEND  ⟶",
            bg=P["fg_accent"], fg=P["bg_root"],
            activebackground="#06b6d4", activeforeground=P["bg_root"],
            font=self.fn_bold, relief="flat", cursor="hand2",
            command=self._send, padx=16, pady=8,
        )
        self._send_btn.grid(row=0, column=2, padx=(8, 0))
        self._send_btn.bind("<Enter>", lambda e: self._send_btn.config(bg="#38bdf8"))
        self._send_btn.bind("<Leave>", lambda e: self._send_btn.config(bg=P["fg_accent"]))

        # Character counter
        self._char_var = tk.StringVar(value="")
        tk.Label(bar, textvariable=self._char_var,
                 bg=P["bg_input_bar"], fg=P["fg_dim"],
                 font=self.fn_sm).grid(row=1, column=1, sticky="e", pady=(2, 0))
        self._input_var.trace_add("write", self._update_char)

    def _update_char(self, *_):
        n = len(self._input_var.get())
        self._char_var.set(f"{n}/500" if n > 0 else "")

    # ── Emoji ─────────────────────────────────────────────────
    def _open_emoji(self):
        EmojiPicker(self, self._input_var, self._emoji_anchor)

    # ── Scroll ────────────────────────────────────────────────
    def _wheel(self, event):
        if event.num == 4 or event.delta > 0:
            self._canvas.yview_scroll(-2, "units")
        else:
            self._canvas.yview_scroll(2, "units")

    def _scroll_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── Avatar colour ─────────────────────────────────────────
    def _av_color(self, name):
        if name not in self._avatar_map:
            self._avatar_map[name] = AVATAR_POOL[self._colour_idx % len(AVATAR_POOL)]
            self._colour_idx += 1
        return self._avatar_map[name]

    # ── Message bubbles ───────────────────────────────────────
    def _add_bubble(self, sender, text, ts,
                    is_me=False, is_system=False,
                    is_private=False, is_private_sent=False,
                    avatar_name=None):
        """Render a styled message row into the chat canvas."""
        self._remove_typing()

        row = tk.Frame(self._msgs, bg=P["bg_chat"])
        row.pack(fill="x", padx=16, pady=4)

        # System messages: centred amber line
        if is_system:
            inner = tk.Frame(row, bg=P["bg_chat"])
            inner.pack()
            for widget_text, col in [
                ("──", P["fg_dimmer"]),
                (f"  {text}  ", P["fg_system"]),
                (f"[{ts}]", P["fg_dimmer"]),
                ("──", P["fg_dimmer"]),
            ]:
                tk.Label(inner, text=widget_text, bg=P["bg_chat"],
                         fg=col, font=self.fn_sm).pack(side="left")
            self._scroll_bottom()
            return

        # Avatar circle
        avatar_name = avatar_name or sender
        color = self._av_color(avatar_name)
        av = tk.Canvas(row, width=38, height=38,
                       bg=P["bg_chat"], highlightthickness=0)
        av.create_oval(1, 1, 37, 37, fill=color, outline=color)
        av.create_text(19, 19, text=_initials(avatar_name),
                       fill="#000000", font=self.fn_sm_bold)

        # Bubble style
        if is_me:
            bg_bub, name_col, border_col = P["bg_bubble_me"], P["fg_accent"], P["glow_me"]
        elif is_private or is_private_sent:
            bg_bub, name_col, border_col = "#081f18", P["fg_private"], "#1a5c3a"
        else:
            bg_bub, name_col, border_col = P["bg_bubble_ot"], P["fg_other"], P["glow_ot"]

        # Thin glowing border around bubble
        bf = tk.Frame(row, bg=border_col, padx=1, pady=1)
        bubble = tk.Frame(bf, bg=bg_bub, padx=14, pady=10)
        bubble.pack(fill="x")

        # Name row
        top = tk.Frame(bubble, bg=bg_bub)
        top.pack(fill="x")
        if is_private:
            tk.Label(top, text="🔒 PM from ", bg=bg_bub, fg=P["fg_private"],
                     font=self.fn_sm).pack(side="left")
        elif is_private_sent:
            tk.Label(top, text="🔒 PM to ", bg=bg_bub, fg=P["fg_private"],
                     font=self.fn_sm).pack(side="left")
        tk.Label(top, text=sender, bg=bg_bub, fg=name_col,
                 font=self.fn_bold).pack(side="left")
        tk.Label(top, text=f"   {ts}", bg=bg_bub, fg=P["fg_dim"],
                 font=self.fn_sm).pack(side="left")

        # Message text
        tk.Label(bubble, text=text, bg=bg_bub, fg=P["fg_main"],
                 font=self.fn, wraplength=640,
                 justify="left", anchor="w").pack(fill="x", pady=(6, 0))

        av.pack(side="left", anchor="n", pady=4)
        bf.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Brief flash on new message row
        self._flash(row, border_col)
        self._scroll_bottom()

    def _flash(self, row, color, step=0):
        """Flash row background briefly to signal new message."""
        seq = [color, P["bg_chat"], color, P["bg_chat"]]
        if step < len(seq):
            try:
                row.config(bg=seq[step])
            except Exception:
                return
            self.after(90, lambda: self._flash(row, color, step + 1))

    def _add_system(self, text, ts=""):
        self._add_bubble("", text, ts or _ts(), is_system=True)

    # ── Typing indicator ──────────────────────────────────────
    def _show_typing(self, username):
        self._remove_typing()
        row = tk.Frame(self._msgs, bg=P["bg_chat"])
        row.pack(fill="x", padx=16, pady=2)
        color = self._av_color(username)
        av = tk.Canvas(row, width=38, height=38,
                       bg=P["bg_chat"], highlightthickness=0)
        av.create_oval(1, 1, 37, 37, fill=color, outline=color)
        av.create_text(19, 19, text=_initials(username),
                       fill="#000000", font=self.fn_sm_bold)
        av.pack(side="left", anchor="n", pady=4)
        bubble = tk.Frame(row, bg=P["bg_bubble_ot"], padx=14, pady=12)
        bubble.pack(side="left", padx=(10, 0))
        dots = TypingDots(bubble)
        dots.pack()
        dots.start()
        self._typing_widget = row
        self._scroll_bottom()

    def _remove_typing(self):
        if self._typing_widget:
            try:
                self._typing_widget.destroy()
            except Exception:
                pass
            self._typing_widget = None

    # ── Sidebar user list ─────────────────────────────────────
    def _rebuild_users(self):
        for w in self._users_frame.winfo_children():
            w.destroy()

        for uname in self._online_users:
            color = self._av_color(uname)
            is_me = (uname == self._username)

            row = tk.Frame(self._users_frame, bg=P["bg_sidebar"],
                           pady=7, padx=12, cursor="hand2")
            row.pack(fill="x", padx=8, pady=1)

            def _enter(e, r=row): r.config(bg=P["bg_hover"])
            def _leave(e, r=row): r.config(bg=P["bg_sidebar"])
            row.bind("<Enter>", _enter)
            row.bind("<Leave>", _leave)

            # Coloured dot
            dot = tk.Label(row, text="●", bg=P["bg_sidebar"],
                           fg=P["fg_online"], font=self.fn_sm)
            dot.pack(side="left", padx=(0, 6))
            dot.bind("<Enter>", _enter)
            dot.bind("<Leave>", _leave)

            # Username
            lbl = tk.Label(row,
                           text=f"{uname}  (you)" if is_me else uname,
                           bg=P["bg_sidebar"], fg=color,
                           font=self.fn_sm_bold if is_me else self.fn_sm,
                           anchor="w")
            lbl.pack(side="left", fill="x")
            lbl.bind("<Enter>", _enter)
            lbl.bind("<Leave>", _leave)

            # Click to auto-fill /msg in input box
            def _pm(e, u=uname):
                if u != self._username:
                    self._input_var.set(f"/msg {u} ")
                    self._input_entry.focus_set()
                    self._input_entry.icursor(tk.END)

            for w in (row, dot, lbl):
                w.bind("<Button-1>", _pm)

        self._stats_var.set(
            f"Messages: {self._msg_count}  |  Online: {len(self._online_users)}"
        )

    # ── Incoming message parsing ──────────────────────────────
    def _on_message(self, raw):
        """
        Called from background recv thread.
        Parses pipe-delimited server protocol and schedules
        all UI updates on the main thread via after().

        Protocol:
          USERLIST|username|ts
          MSG|sender|text|ts
          SYSTEM|text|ts
          PRIVATE|from|text|ts
          PRIVATE_SENT|to|text|ts
        """
        parts = raw.split("|", 3)
        kind  = parts[0] if parts else ""

        if kind == "USERLIST" and len(parts) >= 2:
            uname = parts[1]
            if uname not in self._online_users:
                self._online_users.append(uname)
                self.after(0, self._rebuild_users)

        elif kind == "MSG" and len(parts) == 4:
            _, sender, text, ts = parts
            is_me = (sender == self._username)
            self._msg_count += 1
            if sender not in self._online_users:
                self._online_users.append(sender)
                self.after(0, self._rebuild_users)
            self.after(0, lambda s=sender, t=text, time=ts, me=is_me:
                       self._add_bubble(s, t, time, is_me=me))
            self.after(0, lambda: self._stats_var.set(
                f"Messages: {self._msg_count}  |  Online: {len(self._online_users)}"))

        elif kind == "SYSTEM" and len(parts) >= 2:
            text = parts[1]
            ts   = parts[2] if len(parts) > 2 else _ts()
            join  = re.match(r"^(.+) joined the chat\.$", text)
            leave = re.match(r"^(.+) left the chat\.$",  text)
            if join:
                u = join.group(1)
                if u not in self._online_users:
                    self._online_users.append(u)
                    self.after(0, self._rebuild_users)
            elif leave:
                u = leave.group(1)
                if u in self._online_users:
                    self._online_users.remove(u)
                    self.after(0, self._rebuild_users)
            self.after(0, lambda t=text, time=ts: self._add_system(t, time))

        elif kind == "PRIVATE" and len(parts) == 4:
            _, sender, text, ts = parts
            self._msg_count += 1
            self.after(0, lambda s=sender, t=text, time=ts:
                       self._add_bubble(s, t, time, is_private=True))

        elif kind == "PRIVATE_SENT" and len(parts) == 4:
            _, target, text, ts = parts
            self.after(0, lambda tg=target, t=text, time=ts:
                       self._add_bubble(
                           tg, t, time,
                           is_private_sent=True,
                           avatar_name=self._username
                       ))
        else:
            self.after(0, lambda r=raw: self._add_system(r))

    def _on_disconnect(self):
        self.after(0, self._disc_ui)

    def _disc_ui(self):
        self._conn_dot.config(fg=P["fg_dim"])
        self._conn_lbl.config(text="offline", fg=P["fg_dim"])
        self._input_entry.config(state="disabled")
        self._add_system("Disconnected from server.")
        self._online_users.clear()
        self._rebuild_users()

    # ── Login ─────────────────────────────────────────────────
    def _show_login(self):
        LoginScreen(self, on_connect_cb=self._attempt_connect)

    def _attempt_connect(self, host, port, username, login_win):
        """Runs in background thread spawned by LoginScreen."""
        c = ChatClient(on_message=self._on_message,
                       on_disconnect=self._on_disconnect)
        ok, err = c.connect(host, port, username)
        if not ok:
            self.after(0, lambda: login_win.show_error(err))
            return
        self._client       = c
        self._username     = username
        self._online_users = [username]
        self.after(0, lambda: self._open_chat(login_win))

    def _open_chat(self, login_win):
        login_win.destroy()
        self.deiconify()
        self.lift()
        
        self._conn_dot.config(fg=P["fg_online"])
        self._conn_lbl.config(text=f"online  ·  {self._username}", fg=P["fg_main"])
        self._input_entry.config(state="normal")
        self._input_entry.focus_set()
        self._rebuild_users()
        self._add_system(
            f"Connected as {self._username}  "
            f"·  type to chat  ·  click a name on the left to PM"
        )

    # ── Send ──────────────────────────────────────────────────
    def _send(self):
        text = self._input_var.get().strip()
        if not text:
            return
        if not (self._client and self._client.connected):
            messagebox.showwarning("Nexus", "Not connected.")
            return
        if text == "/quit":
            self._on_close()
            return
        self._client.send_message(text)
        self._input_var.set("")

    # ── Close ─────────────────────────────────────────────────
    def _on_close(self):
        if self._client and self._client.connected:
            self._client.disconnect()
        self.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nexus Chat GUI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    args = parser.parse_args()
    ChatWindow().mainloop()
