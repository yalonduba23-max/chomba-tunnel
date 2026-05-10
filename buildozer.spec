[app]
title = Chomba Tunnel
package.name = chomba_tunnel
package.domain = tech.chomba

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 1.0.0

requirements = python3,kivy==2.3.0,openssl,requests

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE,ACCESS_WIFI_STATE,CHANGE_NETWORK_STATE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 34.0.0
android.archs = arm64-v8a, armeabi-v7a

android.enable_androidx = True

[buildozer]
log_level = 2
warn_on_root = 1
