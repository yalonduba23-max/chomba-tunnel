# screens/home.py — main connect screen

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp

from utils.theme import Theme
from utils.tunnel import TunnelEngine, fmt_bytes
from utils.storage import load_profiles, get_active_index, set_active_index


class Card(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Theme.CARD)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])


class StatBox(BoxLayout):
    def __init__(self, label, value="—", **kw):
        super().__init__(orientation="vertical", spacing=dp(2), **kw)
        self._val_lbl = Label(text=value, color=Theme.GREEN,
                              font_size="16sp", bold=True, halign="center")
        self._val_lbl.bind(size=self._val_lbl.setter("text_size"))
        self.add_widget(Label(text=label, color=Theme.TEXT_DIM,
                              font_size="10sp", halign="center",
                              size_hint_y=None, height=dp(16)))
        self.add_widget(self._val_lbl)

    def set(self, v):
        self._val_lbl.text = v


class HomeScreen(Screen):

    STATUS_COLORS = {
        "disconnected": Theme.TEXT_DIM,
        "connecting":   Theme.YELLOW,
        "connected":    Theme.GREEN,
        "error":        Theme.RED,
    }

    def __init__(self, **kw):
        super().__init__(**kw)
        self._engine = TunnelEngine(
            log_cb    = self._on_log,
            status_cb = self._on_status,
            stats_cb  = self._on_stats,
        )
        self._status   = "disconnected"
        self._log_lines = []
        self._build_ui()
        Clock.schedule_interval(self._tick, 1)

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        with root.canvas.before:
            Color(*Theme.BG)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(self._bg_rect, "pos", root.pos),
                  size=lambda *_: setattr(self._bg_rect, "size", root.size))

        # ── Top bar ──────────────────────────────────────────────────────
        topbar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        self._title = Label(text="CHOMBA TUNNEL", color=Theme.GREEN,
                            font_size="17sp", bold=True, halign="left",
                            size_hint_x=0.6)
        self._title.bind(size=self._title.setter("text_size"))
        topbar.add_widget(self._title)
        for lbl, screen in [("⚙", "config"), ("☰", "profiles"), ("📋", "logs")]:
            b = Button(text=lbl, font_size="18sp", size_hint_x=None, width=dp(40),
                       background_color=(0, 0, 0, 0), color=Theme.TEXT_LABEL)
            b.bind(on_release=lambda _, s=screen: self._goto(s))
            topbar.add_widget(b)
        root.add_widget(topbar)

        # ── Profile selector ──────────────────────────────────────────────
        prof_card = Card(orientation="horizontal", size_hint_y=None, height=dp(52),
                         padding=dp(12), spacing=dp(8))
        self._prof_label = Label(text="No profile selected", color=Theme.TEXT,
                                 font_size="13sp", halign="left")
        self._prof_label.bind(size=self._prof_label.setter("text_size"))
        change_btn = Button(text="Change", size_hint_x=None, width=dp(72),
                            font_size="12sp", background_color=(0, 0, 0, 0),
                            color=Theme.BLUE)
        change_btn.bind(on_release=lambda _: self._goto("profiles"))
        prof_card.add_widget(self._prof_label)
        prof_card.add_widget(change_btn)
        root.add_widget(prof_card)

        # ── Status orb + label ────────────────────────────────────────────
        status_card = Card(orientation="vertical", size_hint_y=None, height=dp(110),
                           padding=dp(14), spacing=dp(6))
        self._status_lbl = Label(text="● DISCONNECTED", color=Theme.TEXT_DIM,
                                 font_size="15sp", bold=True, halign="center")
        self._status_lbl.bind(size=self._status_lbl.setter("text_size"))
        self._uptime_lbl = Label(text="00:00:00", color=Theme.TEXT_DIM,
                                 font_size="12sp", halign="center")
        self._uptime_lbl.bind(size=self._uptime_lbl.setter("text_size"))
        status_card.add_widget(self._status_lbl)
        status_card.add_widget(self._uptime_lbl)
        root.add_widget(status_card)

        # ── Stats row ─────────────────────────────────────────────────────
        stats_card = Card(orientation="horizontal", size_hint_y=None, height=dp(68),
                          padding=dp(12))
        self._stat_up   = StatBox("↑ UPLOAD",   "0 B")
        self._stat_dn   = StatBox("↓ DOWNLOAD", "0 B")
        self._stat_mode = StatBox("MODE",        "—")
        self._stat_ping = StatBox("PING",        "— ms")
        for w in [self._stat_up, self._stat_dn, self._stat_mode, self._stat_ping]:
            stats_card.add_widget(w)
        root.add_widget(stats_card)

        # ── Connect button ────────────────────────────────────────────────
        self._conn_btn = Button(
            text="CONNECT", font_size="16sp", bold=True,
            size_hint_y=None, height=dp(54),
            background_color=(0, 0, 0, 0), color=Theme.BG
        )
        with self._conn_btn.canvas.before:
            self._btn_color = Color(*Theme.GREEN)
            self._btn_rect  = RoundedRectangle(
                pos=self._conn_btn.pos,
                size=self._conn_btn.size,
                radius=[dp(10)]
            )
        self._conn_btn.bind(
            pos=lambda *_: setattr(self._btn_rect, "pos", self._conn_btn.pos),
            size=lambda *_: setattr(self._btn_rect, "size", self._conn_btn.size),
            on_release=self._toggle_connect
        )
        root.add_widget(self._conn_btn)

        # ── Mini log ──────────────────────────────────────────────────────
        log_card = Card(orientation="vertical", padding=dp(10), spacing=dp(4))
        log_card.add_widget(Label(text="RECENT LOGS", color=Theme.TEXT_DIM,
                                  font_size="10sp", halign="left",
                                  size_hint_y=None, height=dp(16)))
        sv = ScrollView()
        self._log_label = Label(
            text="", color=Theme.TEXT_LABEL, font_size="11sp",
            halign="left", valign="top", markup=True,
            size_hint_y=None
        )
        self._log_label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        self._log_label.bind(width=lambda inst, val: setattr(inst, "text_size", (val, None)))
        sv.add_widget(self._log_label)
        log_card.add_widget(sv)
        root.add_widget(log_card)

        self.add_widget(root)
        self._refresh_profile()

    # ── Actions ───────────────────────────────────────────────────────────

    def _goto(self, screen):
        self.manager.current = screen

    def _toggle_connect(self, *_):
        if self._engine.is_connected():
            self._engine.disconnect()
        else:
            profiles = load_profiles()
            idx = get_active_index()
            if not profiles:
                self._on_log("No profiles — tap ☰ to create one", "warn")
                return
            idx = min(idx, len(profiles) - 1)
            self._engine.connect(profiles[idx])

    def _refresh_profile(self):
        profiles = load_profiles()
        idx = get_active_index()
        if profiles:
            idx = min(idx, len(profiles) - 1)
            p = profiles[idx]
            self._prof_label.text = f"[b]{p['name']}[/b]  {p['server']}:{p['port']}"
            self._prof_label.markup = True
            self._stat_mode.set(p.get("mode", "—"))
        else:
            self._prof_label.text = "No profile — tap Change"

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_status(self, status):
        self._status = status
        color = self.STATUS_COLORS.get(status, Theme.TEXT_DIM)
        self._status_lbl.text  = f"● {status.upper()}"
        self._status_lbl.color = color

        if status == "connected":
            self._btn_color.rgba = Theme.RED
            self._conn_btn.text  = "DISCONNECT"
            self._conn_btn.color = (1, 1, 1, 1)
        else:
            self._btn_color.rgba = Theme.GREEN
            self._conn_btn.text  = "CONNECT"
            self._conn_btn.color = Theme.BG

    def _on_stats(self, up, dn):
        self._stat_up.set(fmt_bytes(up))
        self._stat_dn.set(fmt_bytes(dn))

    def _on_log(self, msg, level="info"):
        colors = {"info": "#c0c8d8", "warn": "#ffd040", "error": "#f05050"}
        c = colors.get(level, "#c0c8d8")
        self._log_lines.append(f"[color={c}]{msg}[/color]")
        self._log_lines = self._log_lines[-20:]
        self._log_label.text = "\n".join(reversed(self._log_lines))

        # Also forward to Logs screen
        logs_screen = self.manager.get_screen("logs") if self.manager else None
        if logs_screen:
            logs_screen.append_log(msg, level)

    def _tick(self, dt):
        if self._engine.is_connected():
            self._uptime_lbl.text = self._engine.get_uptime()
        else:
            self._uptime_lbl.text = "00:00:00"

    def on_enter(self):
        self._refresh_profile()
