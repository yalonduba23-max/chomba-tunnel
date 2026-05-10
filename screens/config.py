# screens/config.py — profile editor screen

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp
from kivy.clock import Clock

from utils.theme import Theme
from utils.storage import (
    load_profiles, save_profiles, add_profile,
    update_profile, get_active_index, DEFAULT_PROFILE
)
import copy


def _labeled_input(label_text, hint="", password=False, multiline=False):
    box = BoxLayout(orientation="vertical", spacing=dp(2),
                    size_hint_y=None, height=dp(62) if not multiline else dp(90))
    lbl = Label(text=label_text, color=Theme.TEXT_LABEL, font_size="11sp",
                halign="left", size_hint_y=None, height=dp(16))
    lbl.bind(size=lbl.setter("text_size"))
    ti = TextInput(
        hint_text=hint, multiline=multiline, password=password,
        background_color=Theme.CARD2,
        foreground_color=Theme.TEXT,
        hint_text_color=Theme.TEXT_DIM,
        font_size="13sp",
        padding=[dp(8), dp(6)],
        size_hint_y=None,
        height=dp(38) if not multiline else dp(68),
        cursor_color=Theme.GREEN,
    )
    box.add_widget(lbl)
    box.add_widget(ti)
    return box, ti


def _section_label(text):
    lbl = Label(text=f"── {text}", color=Theme.BLUE, font_size="11sp",
                halign="left", size_hint_y=None, height=dp(24))
    lbl.bind(size=lbl.setter("text_size"))
    return lbl


class ConfigScreen(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._profile_index = None   # None = new profile
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
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
        self._screen_title = Label(text="NEW PROFILE", color=Theme.GREEN,
                                   font_size="15sp", bold=True, halign="left")
        self._screen_title.bind(size=self._screen_title.setter("text_size"))
        save_btn = Button(text="SAVE", font_size="13sp", bold=True,
                          size_hint_x=None, width=dp(64),
                          background_color=(0,0,0,0), color=Theme.GREEN)
        save_btn.bind(on_release=self._save)
        bar.add_widget(back)
        bar.add_widget(self._screen_title)
        bar.add_widget(save_btn)
        root.add_widget(bar)

        # Scrollable form
        sv = ScrollView()
        form = BoxLayout(orientation="vertical", spacing=dp(8),
                         padding=[0, dp(4)], size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        # Profile name
        form.add_widget(_section_label("PROFILE"))
        name_box, self._f_name     = _labeled_input("Profile Name", "My Profile")
        form.add_widget(name_box)

        # Mode selector
        mode_box = BoxLayout(orientation="vertical", spacing=dp(2),
                             size_hint_y=None, height=dp(62))
        mode_lbl = Label(text="Tunnel Mode", color=Theme.TEXT_LABEL, font_size="11sp",
                         halign="left", size_hint_y=None, height=dp(16))
        mode_lbl.bind(size=mode_lbl.setter("text_size"))
        self._f_mode = Spinner(
            text="WebSocket",
            values=["WebSocket", "SSH", "HTTP Proxy"],
            size_hint_y=None, height=dp(38),
            background_color=Theme.CARD2,
            color=Theme.TEXT, font_size="13sp",
        )
        self._f_mode.bind(text=self._on_mode_change)
        mode_box.add_widget(mode_lbl)
        mode_box.add_widget(self._f_mode)
        form.add_widget(mode_box)

        # Server
        form.add_widget(_section_label("SERVER"))
        srv_box, self._f_server  = _labeled_input("Host / IP", "example.com")
        port_box, self._f_port   = _labeled_input("Port", "443")
        form.add_widget(srv_box)
        form.add_widget(port_box)

        # WebSocket options
        self._ws_section = BoxLayout(orientation="vertical", spacing=dp(8),
                                     size_hint_y=None)
        self._ws_section.bind(minimum_height=self._ws_section.setter("height"))
        self._ws_section.add_widget(_section_label("WEBSOCKET / TLS"))
        uuid_box,  self._f_uuid  = _labeled_input("UUID / Token", "xxxxxxxx-xxxx-...")
        path_box,  self._f_path  = _labeled_input("WS Path", "/")
        sni_box,   self._f_sni   = _labeled_input("SNI Override", "(leave blank = host)")
        dns_box,   self._f_dns   = _labeled_input("DNS", "1.1.1.1")
        tls_row = BoxLayout(size_hint_y=None, height=dp(40))
        tls_lbl = Label(text="Enable TLS", color=Theme.TEXT_LABEL, font_size="12sp",
                        halign="left")
        tls_lbl.bind(size=tls_lbl.setter("text_size"))
        self._f_tls = Switch(active=True, size_hint_x=None, width=dp(68))
        tls_row.add_widget(tls_lbl)
        tls_row.add_widget(self._f_tls)
        for w in [uuid_box, path_box, sni_box, dns_box, tls_row]:
            self._ws_section.add_widget(w)
        form.add_widget(self._ws_section)

        # SSH options
        self._ssh_section = BoxLayout(orientation="vertical", spacing=dp(8),
                                      size_hint_y=None, opacity=0)
        self._ssh_section.bind(minimum_height=self._ssh_section.setter("height"))
        self._ssh_section.add_widget(_section_label("SSH"))
        su_box,  self._f_ssh_user = _labeled_input("SSH Username", "root")
        sp_box,  self._f_ssh_pass = _labeled_input("SSH Password", "", password=True)
        sk_box,  self._f_ssh_key  = _labeled_input("Private Key Path", "/sdcard/id_rsa")
        for w in [su_box, sp_box, sk_box]:
            self._ssh_section.add_widget(w)
        form.add_widget(self._ssh_section)

        # HTTP Proxy options
        self._proxy_section = BoxLayout(orientation="vertical", spacing=dp(8),
                                        size_hint_y=None, opacity=0)
        self._proxy_section.bind(minimum_height=self._proxy_section.setter("height"))
        self._proxy_section.add_widget(_section_label("HTTP PROXY"))
        ph_box,  self._f_proxy_host = _labeled_input("Proxy Host", "")
        pp_box,  self._f_proxy_port = _labeled_input("Proxy Port", "8080")
        for w in [ph_box, pp_box]:
            self._proxy_section.add_widget(w)
        form.add_widget(self._proxy_section)

        # Payload injection
        form.add_widget(_section_label("PAYLOAD INJECTION"))
        pl_box, self._f_payload = _labeled_input(
            "Custom HTTP Headers / Payload",
            "X-Custom-Header: value\nUser-Agent: custom",
            multiline=True
        )
        form.add_widget(pl_box)

        # Advanced
        form.add_widget(_section_label("ADVANCED"))
        mtu_box, self._f_mtu = _labeled_input("MTU", "1400")
        rec_row = BoxLayout(size_hint_y=None, height=dp(40))
        rec_lbl = Label(text="Auto Reconnect", color=Theme.TEXT_LABEL,
                        font_size="12sp", halign="left")
        rec_lbl.bind(size=rec_lbl.setter("text_size"))
        self._f_reconnect = Switch(active=True, size_hint_x=None, width=dp(68))
        rec_row.add_widget(rec_lbl)
        rec_row.add_widget(self._f_reconnect)
        notes_box, self._f_notes = _labeled_input("Notes", "", multiline=True)
        for w in [mtu_box, rec_row, notes_box]:
            form.add_widget(w)

        form.add_widget(BoxLayout(size_hint_y=None, height=dp(20)))  # spacer

        sv.add_widget(form)
        root.add_widget(sv)
        self.add_widget(root)

    # ── Mode switching ────────────────────────────────────────────────────

    def _on_mode_change(self, spinner, mode):
        self._ws_section.opacity    = 1 if mode == "WebSocket" else 0
        self._ws_section.height     = None if mode == "WebSocket" else 0
        self._ssh_section.opacity   = 1 if mode == "SSH" else 0
        self._ssh_section.height    = None if mode == "SSH" else 0
        self._proxy_section.opacity = 1 if mode == "HTTP Proxy" else 0
        self._proxy_section.height  = None if mode == "HTTP Proxy" else 0

    # ── Save ──────────────────────────────────────────────────────────────

    def _save(self, *_):
        p = dict(DEFAULT_PROFILE)
        p["name"]       = self._f_name.text.strip() or "Profile"
        p["mode"]       = self._f_mode.text
        p["server"]     = self._f_server.text.strip()
        p["port"]       = self._f_port.text.strip() or "443"
        p["uuid"]       = self._f_uuid.text.strip()
        p["ws_path"]    = self._f_path.text.strip() or "/"
        p["sni"]        = self._f_sni.text.strip()
        p["dns"]        = self._f_dns.text.strip() or "1.1.1.1"
        p["tls"]        = self._f_tls.active
        p["ssh_user"]   = self._f_ssh_user.text.strip()
        p["ssh_pass"]   = self._f_ssh_pass.text
        p["ssh_key"]    = self._f_ssh_key.text.strip()
        p["proxy_host"] = self._f_proxy_host.text.strip()
        p["proxy_port"] = self._f_proxy_port.text.strip() or "8080"
        p["payload"]    = self._f_payload.text.strip()
        p["mtu"]        = self._f_mtu.text.strip() or "1400"
        p["reconnect"]  = self._f_reconnect.active
        p["notes"]      = self._f_notes.text.strip()

        if self._profile_index is None:
            add_profile(p)
        else:
            update_profile(self._profile_index, p)

        self.manager.current = "profiles"

    # ── Load existing profile into form ───────────────────────────────────

    def load_profile(self, index):
        from utils.storage import get_profile
        self._profile_index = index
        p = get_profile(index)
        self._screen_title.text = "EDIT PROFILE"
        self._f_name.text      = p.get("name", "")
        self._f_mode.text      = p.get("mode", "WebSocket")
        self._f_server.text    = p.get("server", "")
        self._f_port.text      = p.get("port", "443")
        self._f_uuid.text      = p.get("uuid", "")
        self._f_path.text      = p.get("ws_path", "/")
        self._f_sni.text       = p.get("sni", "")
        self._f_dns.text       = p.get("dns", "1.1.1.1")
        self._f_tls.active     = p.get("tls", True)
        self._f_ssh_user.text  = p.get("ssh_user", "root")
        self._f_ssh_pass.text  = p.get("ssh_pass", "")
        self._f_ssh_key.text   = p.get("ssh_key", "")
        self._f_proxy_host.text= p.get("proxy_host", "")
        self._f_proxy_port.text= p.get("proxy_port", "8080")
        self._f_payload.text   = p.get("payload", "")
        self._f_mtu.text       = p.get("mtu", "1400")
        self._f_reconnect.active = p.get("reconnect", True)
        self._f_notes.text     = p.get("notes", "")
        self._on_mode_change(None, p.get("mode", "WebSocket"))

    def new_profile(self):
        self._profile_index = None
        self._screen_title.text = "NEW PROFILE"
        for ti in [self._f_name, self._f_server, self._f_port, self._f_uuid,
                   self._f_path, self._f_sni, self._f_dns, self._f_ssh_user,
                   self._f_ssh_pass, self._f_ssh_key, self._f_proxy_host,
                   self._f_proxy_port, self._f_payload, self._f_mtu, self._f_notes]:
            ti.text = ""
        self._f_mode.text = "WebSocket"
        self._f_tls.active = True
        self._f_reconnect.active = True
