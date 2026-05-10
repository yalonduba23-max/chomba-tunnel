# screens/logs.py — live connection log screen

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
import datetime

from utils.theme import Theme


class LogsScreen(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._lines = []
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        with root.canvas.before:
            Color(*Theme.BG)
            bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(bg, "pos", root.pos),
                  size=lambda *_: setattr(bg, "size", root.size))

        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        back = Button(text="←", font_size="18sp", size_hint_x=None, width=dp(40),
                      background_color=(0,0,0,0), color=Theme.TEXT)
        back.bind(on_release=lambda _: setattr(self.manager, "current", "home"))
        title = Label(text="LOGS", color=Theme.GREEN, font_size="15sp",
                      bold=True, halign="left")
        title.bind(size=title.setter("text_size"))
        clear_btn = Button(text="CLEAR", font_size="12sp",
                           size_hint_x=None, width=dp(64),
                           background_color=(0,0,0,0), color=Theme.RED)
        clear_btn.bind(on_release=self._clear)
        bar.add_widget(back)
        bar.add_widget(title)
        bar.add_widget(clear_btn)
        root.add_widget(bar)

        self._sv = ScrollView()
        self._log_lbl = Label(
            text="", color=Theme.TEXT_LABEL, font_size="11sp",
            halign="left", valign="top", markup=True,
            size_hint_y=None, font_name="RobotoMono"
        )
        self._log_lbl.bind(texture_size=lambda i, v: setattr(i, "height", v[1]))
        self._log_lbl.bind(width=lambda i, v: setattr(i, "text_size", (v, None)))
        self._sv.add_widget(self._log_lbl)
        root.add_widget(self._sv)
        self.add_widget(root)

    def append_log(self, msg, level="info"):
        colors = {"info": "#c0c8d8", "warn": "#ffd040", "error": "#f05050"}
        c = colors.get(level, "#c0c8d8")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._lines.append(f"[color=#4a5568]{ts}[/color]  [color={c}]{msg}[/color]")
        if len(self._lines) > 200:
            self._lines = self._lines[-200:]
        self._log_lbl.text = "\n".join(self._lines)
        self._sv.scroll_y = 0  # scroll to bottom

    def _clear(self, *_):
        self._lines = []
        self._log_lbl.text = ""
