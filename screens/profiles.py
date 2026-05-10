# screens/profiles.py — profile list screen

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp

from utils.theme import Theme
from utils.storage import (
    load_profiles, delete_profile,
    get_active_index, set_active_index
)


class ProfileRow(BoxLayout):
    def __init__(self, profile, index, is_active, on_select, on_edit, on_delete, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None,
                         height=dp(66), padding=dp(10), spacing=dp(6), **kw)
        with self.canvas.before:
            Color(*(Theme.CARD2 if is_active else Theme.CARD))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda *_: setattr(self._bg, "pos", self.pos),
                  size=lambda *_: setattr(self._bg, "size", self.size))

        # Active indicator bar
        with self.canvas.before:
            if is_active:
                Color(*Theme.GREEN)
                RoundedRectangle(pos=(self.x, self.y), size=(dp(3), self.height),
                                 radius=[dp(2)])

        # Info
        info = BoxLayout(orientation="vertical", spacing=dp(2))
        name_lbl = Label(
            text=f"[b]{profile['name']}[/b]", markup=True,
            color=Theme.GREEN if is_active else Theme.TEXT,
            font_size="13sp", halign="left"
        )
        name_lbl.bind(size=name_lbl.setter("text_size"))
        detail_lbl = Label(
            text=f"{profile.get('mode','?')}  {profile.get('server','')}:{profile.get('port','')}",
            color=Theme.TEXT_DIM, font_size="11sp", halign="left"
        )
        detail_lbl.bind(size=detail_lbl.setter("text_size"))
        info.add_widget(name_lbl)
        info.add_widget(detail_lbl)
        self.add_widget(info)

        # Buttons
        for txt, cb, col in [
            ("✓", lambda _, i=index: on_select(i), Theme.GREEN),
            ("✎", lambda _, i=index: on_edit(i),   Theme.BLUE),
            ("✕", lambda _, i=index: on_delete(i),  Theme.RED),
        ]:
            btn = Button(text=txt, font_size="15sp", size_hint_x=None, width=dp(36),
                         background_color=(0,0,0,0), color=col)
            btn.bind(on_release=cb)
            self.add_widget(btn)


class ProfilesScreen(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        with root.canvas.before:
            Color(*Theme.BG)
            bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda *_: setattr(bg, "pos", root.pos),
                  size=lambda *_: setattr(bg, "size", root.size))

        # Top bar
        bar = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        back = Button(text="←", font_size="18sp", size_hint_x=None, width=dp(40),
                      background_color=(0,0,0,0), color=Theme.TEXT)
        back.bind(on_release=lambda _: setattr(self.manager, "current", "home"))
        title = Label(text="PROFILES", color=Theme.GREEN, font_size="15sp",
                      bold=True, halign="left")
        title.bind(size=title.setter("text_size"))
        add_btn = Button(text="+ NEW", font_size="12sp", bold=True,
                         size_hint_x=None, width=dp(70),
                         background_color=(0,0,0,0), color=Theme.GREEN)
        add_btn.bind(on_release=self._new_profile)
        bar.add_widget(back)
        bar.add_widget(title)
        bar.add_widget(add_btn)
        root.add_widget(bar)

        # Profile list
        sv = ScrollView()
        self._list = BoxLayout(orientation="vertical", spacing=dp(8),
                               size_hint_y=None, padding=[0, dp(4)])
        self._list.bind(minimum_height=self._list.setter("height"))
        sv.add_widget(self._list)
        root.add_widget(sv)

        # Empty state
        self._empty_lbl = Label(
            text="No profiles yet.\nTap [b]+ NEW[/b] to create one.",
            markup=True, color=Theme.TEXT_DIM, font_size="13sp",
            halign="center", valign="middle"
        )
        self._empty_lbl.bind(size=self._empty_lbl.setter("text_size"))

        self.add_widget(root)

    def on_enter(self):
        self._refresh()

    def _refresh(self):
        self._list.clear_widgets()
        profiles = load_profiles()
        active = get_active_index()

        if not profiles:
            self._list.add_widget(self._empty_lbl)
            return

        for i, p in enumerate(profiles):
            row = ProfileRow(
                profile=p, index=i, is_active=(i == active),
                on_select=self._select,
                on_edit=self._edit,
                on_delete=self._delete,
            )
            self._list.add_widget(row)

    def _select(self, index):
        set_active_index(index)
        self._refresh()
        self.manager.current = "home"

    def _edit(self, index):
        config_screen = self.manager.get_screen("config")
        config_screen.load_profile(index)
        self.manager.current = "config"

    def _delete(self, index):
        delete_profile(index)
        active = get_active_index()
        profiles = load_profiles()
        if active >= len(profiles) and profiles:
            set_active_index(len(profiles) - 1)
        self._refresh()

    def _new_profile(self, *_):
        config_screen = self.manager.get_screen("config")
        config_screen.new_profile()
        self.manager.current = "config"
