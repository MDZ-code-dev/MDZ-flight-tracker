# MDZ SkyScan ✈

A pixel-style live aircraft tracker for **Linux (including Switchroot Fedora on
Nintendo Switch V1), Windows, and Android**.

**Nearest** mode shows the closest aircraft, including its model (for example
B747), callsign, registration, altitude, speed, heading, distance and bearing.
**Radar** shows nearby contacts and a scrolling list. Use **MODE** to switch views.
Models appear when supplied by the data source; missing models display UNKNOWN.

## Downloads

Open **[Releases](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases)**
and expand **Assets** on a completed release:

| Platform | Download | Requirements |
| --- | --- | --- |
| Linux / Switchroot Fedora | [MDZ-SkyScan-linux.tar.gz](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-linux.tar.gz) | Python 3.10+ and a browser; ARM64 and x86-64 supported |
| Windows | [MDZ-SkyScan-windows.zip](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-windows.zip) | Windows 10/11, x86-64; no separate Python installation |
| Windows source alternative | [MDZ-SkyScan-windows-portable.zip](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-windows-portable.zip) | Python 3.10+ installed separately |
| Android | [MDZ-SkyScan-android.apk](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-android.apk) | Android 8.0+; universal ARM/x86 APK |

The **Build downloads** workflow produces these files. A `v*` tag publishes them
only after every build and smoke-test job passes. If no release has completed,
there is no release download yet: check
**[Actions](https://github.com/MDZ-code-dev/MDZ-flight-tracker/actions/workflows/packages.yml)**.
Successful branch builds also have artifacts at the bottom of the run page
(GitHub sign-in required; artifacts expire). Releases include `SHA256SUMS.txt`.
GitHub's automatic “Source code” archives are not the packaged app.

## Linux / Switchroot Fedora

1. Download and extract `MDZ-SkyScan-linux.tar.gz`.
2. Install Python and a browser if needed. Fedora: `sudo dnf install python3 firefox`.
3. Open a terminal in the extracted `MDZ-SkyScan` folder and run:

   ```bash
   chmod +x MDZ-SkyScan.sh
   ./MDZ-SkyScan.sh
   ```

Your browser opens the tracker. Keep the terminal open; press Ctrl+C to stop.
No pip packages are required. This package works with ARM64 and x86-64 Python.

### Original Switchroot desktop launcher

The original full-screen Fedora launcher and idle/sleep inhibitor remain available
from a Git checkout:

```bash
git clone https://github.com/MDZ-code-dev/MDZ-flight-tracker.git
cd MDZ-flight-tracker
bash install.sh
```

Search the application launcher for **MDZ SkyScan**, or run `bash start.sh`.
This uses `systemd-inhibit` to keep the Switch awake while the server runs. It
tries Chromium, Chromium Browser, Chrome, Firefox, then the default browser.
Use the portable launcher on systems without systemd or when sleep inhibition
is unnecessary. Closing the browser alone does not stop `start.sh`'s server.

## Windows

1. Download `MDZ-SkyScan-windows.zip` and **Extract All**.
2. Open its `MDZ-SkyScan` folder and run **MDZ-SkyScan.exe**. Keep the other files
   beside it; do not run from inside the ZIP.
3. The tracker opens in your default browser. Keep the console open; closing it
   stops the server.

The executable is unsigned, so Windows may show a publisher warning. Download
from this repository's releases and check the supplied checksum.

For the source alternative, install [Python 3.10+](https://www.python.org/downloads/windows/)
with the Python launcher/PATH option enabled, extract
`MDZ-SkyScan-windows-portable.zip`, and double-click **MDZ-SkyScan.cmd**.
No pip installation is needed.

## Android APK

1. Download `MDZ-SkyScan-android.apk` onto your Android device.
2. Open it and, if prompted, allow your browser/file manager to install this app.
3. Install and open **MDZ SkyScan**.
4. Enter latitude and longitude in **SETTINGS**, then press **SAVE**.

Android runs the tracker inside the app: no Python, second computer, server,
or root access required. Internet access is needed for live data. This version
uses manual coordinates and does not request GPS permission. Settings stay in
private app storage. Keep Android System WebView updated. The APK supports
Switchroot Android; it is not a stock Nintendo Switch/Horizon `.nro` application.

**Signing:** builds use a development signature unless the maintainer supplies a
release key. Local builds reuse a key outside the repository. GitHub runners
create a fresh development key, so updates between those builds may require
uninstalling the previous app (clearing settings). Configure a stable signing
key below for seamless updates. These are sideload APKs, not Google Play releases.

## First use

- Set your location once. Switch has no built-in GPS available to this app;
  desktop browser location may work, otherwise enter coordinates manually.
- Choose a radius of **1–250 nautical miles** and a refresh interval of
  **3–60 seconds**, then press **SAVE**.
- Toggle **MODE: NEAREST / RADAR** to switch views.
- Zero contacts can mean no aircraft are in range. Missing aircraft metadata
  depends on the source and cannot always be filled in.

Data comes from the public [adsb.lol API](https://api.adsb.lol/docs), licensed
**ODbL**. No API key is needed. The app sends your selected coordinates and radius
to `api.adsb.lol` over HTTPS to find nearby aircraft.

### Saved settings

| Launcher | Settings location |
| --- | --- |
| Linux portable | `$XDG_CONFIG_HOME/mdz-skyscan/config.json`, or `~/.config/mdz-skyscan/config.json` |
| Windows executable / portable | `%LOCALAPPDATA%\mdz-skyscan\config.json` |
| Original `app.py` / `start.sh` | `config.json` in the checkout |
| Android | Private app preferences; cleared when uninstalling |

Desktop overrides: `MDZ_TRACKER_CONFIG` selects a settings file;
`MDZ_TRACKER_PORT` selects the HTTP port (default 8765). The desktop server binds
only to `127.0.0.1`. Existing `start.sh` users keep their original settings;
switching to a portable launcher uses a separate settings location.

## Develop and build

### Run from source

```bash
git clone https://github.com/MDZ-code-dev/MDZ-flight-tracker.git
cd MDZ-flight-tracker
python3 desktop.py
```

On Windows use `py -3 desktop.py`. For server-only development use `python3 app.py`.
Python 3.10+ is sufficient. Run the checks with:

```bash
python3 -m unittest discover -s tests -v
node tests/test_web.cjs
```

Node.js is needed only for JavaScript checks. The Python suite exercises the real
local HTTP server, settings persistence and fixture aircraft processing. It does
not claim live API or physical Switch validation.

### Desktop packages

```bash
python3 scripts/package_desktop.py
```

Linux and Windows source packages appear in `dist/`. To build the standalone
Windows executable, run **on Windows**:

```powershell
py -3 -m pip install pyinstaller==6.16.0
py -3 -m PyInstaller --noconfirm --clean --onedir --name MDZ-SkyScan --add-data "web;web" desktop.py
```

Distribute the entire `dist/MDZ-SkyScan` folder. GitHub Actions builds, starts,
checks, and ZIPs this executable automatically.

### Android APK

Install JDK 17+ and the official Android SDK. Set `JAVA_HOME` and `ANDROID_HOME`,
then install the SDK packages and build **on Linux**:

```bash
sdkmanager "platforms;android-35" "build-tools;35.0.0"
python3 scripts/build_android.py
```

This uses `aapt2`, `javac`, `d8`, `zipalign`, and `apksigner` directly. Gradle and
Python-for-Android are unnecessary. It packages `web/`, compiles the Java backend,
signs the APK, and verifies its signature. Output: `dist/MDZ-SkyScan-android.apk`.

Without a release key it generates/reuses
`~/.android/mdz-skyscan-development.keystore`. Set
`MDZ_ANDROID_DEVELOPMENT_KEYSTORE` to use another writable path. Never commit
private signing keys. For your own signing identity, securely set:

- `MDZ_ANDROID_KEYSTORE`: path to an existing keystore.
- `MDZ_ANDROID_KEY_ALIAS`: signing alias (default `mdz-skyscan`).
- `MDZ_ANDROID_STORE_PASSWORD`: keystore password.
- `MDZ_ANDROID_KEY_PASSWORD`: key password (defaults to the store password).

For GitHub builds use repository Actions secrets `ANDROID_KEYSTORE_BASE64`,
`ANDROID_KEY_ALIAS`, `ANDROID_STORE_PASSWORD`, and `ANDROID_KEY_PASSWORD`. The
workflow decodes the key only in runner temporary storage. Back up your key;
keep the same identity and increment `android:versionCode`/`android:versionName`
in the manifest for Android updates.

To test the APK on a connected test emulator/device with ADB:

```bash
python3 scripts/smoke_android.py
```

This **clears this app's data on that test device**, then checks startup, native
settings, and radar switching. GitHub Actions runs it on an emulator.

### Publish downloads

Push to `main` for CI artifacts. For a release, create a new version tag:

```bash
git tag v1.0.3
git push origin v1.0.3
```

When all three platform jobs pass, the workflow publishes a GitHub Release with
packages and SHA-256 checksums. Failed jobs publish no release. GitHub Actions
must be enabled and allow the release job's `contents: write` permission. Windows
native tests and Android emulator tests run in CI; source archives alone do not
prove those platforms have been tested.

## Troubleshooting

- **No planes:** check coordinates, radius, and Internet access to `api.adsb.lol`.
- **Address already in use:** stop the existing tracker, or set another
  `MDZ_TRACKER_PORT` when using `desktop.py` / `app.py`.
- **Android “App not installed”:** check Android 8.0+, free space, and whether an
  installed version has a different signing key.
- **Fedora launcher fails on another distro:** use `MDZ-SkyScan.sh` instead of the
  optional systemd desktop launcher.
- **Update a source checkout:** run `git pull`, restart the server, and refresh
  the browser. For packages, download and extract the new version.
