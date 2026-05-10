# Chomba Tunnel

HTTP Custom-style Android VPN/tunnel app — built with Python (Kivy) and compiled to APK via Buildozer on GitHub Actions.

## Features
- **WebSocket + TLS** tunneling (VLESS/custom UUID auth)
- **SSH** tunnel mode (with password or private key)
- **HTTP Proxy** mode with payload/header injection
- Save and manage multiple profiles
- Auto-reconnect
- Live logs screen
- Upload/download stats + uptime timer
- No root required

## Project Structure
```
chomba_tunnel/
├── main.py                  ← App entry point
├── buildozer.spec           ← APK build config
├── .github/workflows/
│   └── build.yml            ← GitHub Actions CI
├── screens/
│   ├── home.py              ← Main connect screen
│   ├── config.py            ← Profile editor
│   ├── profiles.py          ← Profile list
│   └── logs.py              ← Live logs
└── utils/
    ├── theme.py             ← Colors & style tokens
    ├── tunnel.py            ← Core tunnel engine
    └── storage.py           ← Profile save/load (JSON)
```

## Build APK on GitHub

1. **Fork / push this repo to GitHub**
2. Go to **Actions** tab
3. Click **Build APK** → **Run workflow**
4. Wait ~15–20 minutes
5. Download the `.apk` from **Artifacts**

The workflow caches the Buildozer environment so subsequent builds are much faster.

## Run locally (desktop testing)

```bash
pip install kivy requests
python main.py
```

## Add SSH support

Uncomment the paramiko line in `buildozer.spec`:
```ini
requirements = python3,kivy==2.3.0,openssl,requests,paramiko,cryptography,bcrypt,cffi
```

## WebSocket Config Example

| Field    | Value                          |
|----------|--------------------------------|
| Mode     | WebSocket                      |
| Host     | web.chomba.tech                |
| Port     | 443                            |
| UUID     | your-vless-uuid-here           |
| WS Path  | /vless                         |
| TLS      | ON                             |
| SNI      | web.chomba.tech (or CDN host)  |

## Payload Injection

For HTTP injection through a proxy, put raw headers in the **Payload** field, e.g.:
```
GET / HTTP/1.1
Host: web.chomba.tech
X-Online-Host: web.chomba.tech
X-Forward-Host: web.chomba.tech
```

## Notes
- Android 5.0+ (API 21+), ARM64 + ARMv7 builds
- Profiles are stored as JSON in the app's private data directory
- The tunnel engine runs in a background thread so the UI stays responsive
