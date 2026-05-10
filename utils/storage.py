# utils/storage.py — save/load profiles and settings using JSON

import json
import os
from kivy.app import App

DEFAULT_PROFILE = {
    "name": "My Profile",
    "mode": "WebSocket",          # WebSocket | SSH | HTTP Proxy
    "server": "",
    "port": "443",
    "uuid": "",
    "ws_path": "/",
    "tls": True,
    "sni": "",
    "payload": "",                # raw HTTP payload for header injection
    "proxy_host": "",
    "proxy_port": "8080",
    "ssh_user": "root",
    "ssh_pass": "",
    "ssh_key": "",
    "dns": "1.1.1.1",
    "mtu": "1400",
    "reconnect": True,
    "notes": "",
}


def _data_dir():
    try:
        return App.get_running_app().user_data_dir
    except Exception:
        return os.path.expanduser("~")


def _profiles_path():
    return os.path.join(_data_dir(), "profiles.json")


def _settings_path():
    return os.path.join(_data_dir(), "settings.json")


# ── Profiles ────────────────────────────────────────────────────────────────

def load_profiles():
    path = _profiles_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_profiles(profiles: list):
    with open(_profiles_path(), "w") as f:
        json.dump(profiles, f, indent=2)


def add_profile(profile: dict):
    profiles = load_profiles()
    profiles.append(profile)
    save_profiles(profiles)
    return profiles


def delete_profile(index: int):
    profiles = load_profiles()
    if 0 <= index < len(profiles):
        profiles.pop(index)
        save_profiles(profiles)
    return profiles


def update_profile(index: int, profile: dict):
    profiles = load_profiles()
    if 0 <= index < len(profiles):
        profiles[index] = profile
        save_profiles(profiles)
    return profiles


def get_profile(index: int):
    profiles = load_profiles()
    if 0 <= index < len(profiles):
        return profiles[index]
    return dict(DEFAULT_PROFILE)


# ── Active / last-used profile index ────────────────────────────────────────

def load_settings():
    path = _settings_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {"active_profile": 0}


def save_settings(settings: dict):
    with open(_settings_path(), "w") as f:
        json.dump(settings, f, indent=2)


def get_active_index():
    return load_settings().get("active_profile", 0)


def set_active_index(idx: int):
    s = load_settings()
    s["active_profile"] = idx
    save_settings(s)
