"""
Chomba Tunnel - HTTP Custom-style Android VPN/Tunnel App
Built with Kivy + Buildozer
"""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock

from screens.home import HomeScreen
from screens.config import ConfigScreen
from screens.profiles import ProfilesScreen
from screens.logs import LogsScreen
from utils.theme import Theme

# Android-specific imports
if platform == "android":
    from android.permissions import request_permissions, Permission  # type: ignore
    from android import mActivity  # type: ignore


class TunnelApp(App):
    title = "Chomba Tunnel"

    def build(self):
        # Dark background
        Window.clearcolor = Theme.BG

        # Request Android permissions
        if platform == "android":
            request_permissions([
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.FOREGROUND_SERVICE,
            ])

        sm = ScreenManager(transition=FadeTransition(duration=0.15))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(ConfigScreen(name="config"))
        sm.add_widget(ProfilesScreen(name="profiles"))
        sm.add_widget(LogsScreen(name="logs"))
        return sm

    def on_pause(self):
        return True  # keep running in background

    def on_resume(self):
        pass


if __name__ == "__main__":
    TunnelApp().run()
