# MDZ SkyScan ✈

A pixel-style live aircraft tracker for **Linux (including Switchroot Fedora on
Nintendo Switch V1), Windows, and Android**.

**Nearest** mode shows the closest aircraft, including its model (for example
B747), callsign, registration, altitude, speed, heading, distance and bearing.
**Radar** shows nearby contacts and a scrolling list. Use **MODE** to switch views.
Models appear when supplied by the data source; missing models display UNKNOWN.

Nearest mode also shows a cyan aircraft silhouette beneath the flight data. It
uses a matching aircraft family (jet, turboprop, light plane, or helicopter) when
recognized and turns with the reported heading. Other models use a generic
silhouette; these are family outlines, not exact model drawings. No aircraft in
range clears the silhouette.

The interface uses the bundled **Silkscreen** pixel font, so the same typography
works offline on Windows, Linux, and Android. Its SIL Open Font License and
copyright notice are included in `web/OFL-Silkscreen.txt`.

## Downloads

Open **[Releases](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases)**
and expand **Assets** on a completed release:

| Platform | Download | Requirements |
| --- | --- | --- |
| Linux / Switchroot Fedora | [MDZ-SkyScan-linux.tar.gz](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-linux.tar.gz) | Python 3.10+, GTK/WebKit2GTK and pywebview; ARM64 and x86-64 supported |
| Windows app | [MDZ-SkyScan-windows.exe](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-windows.exe) | Windows 10/11, x86-64; Edge WebView2 Runtime |
| Windows ZIP (app + runtime installer) | [MDZ-SkyScan-windows.zip](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-windows.zip) | Windows 10/11, x86-64; Edge WebView2 Runtime; no separate Python installation |
| Windows source alternative | [MDZ-SkyScan-windows-portable.zip](https://github.com/MDZ-code-dev/MDZ-flight-tracker/releases/latest/download/MDZ-SkyScan-windows-portable.zip) | Python 3.11+ and desktop-requirements.txt installed separately |
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
2. Install the native window prerequisites. On Fedora / Switchroot Fedora:

   ```bash
   sudo dnf install python3 python3-pip python3-gobject gtk3 webkit2gtk4.1
   ```

   On Debian / Ubuntu:

   ```bash
   sudo apt install python3-venv python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
   ```

3. Open a terminal in the extracted `MDZ-SkyScan` folder and prepare its Python environment:

   ```bash
   python3 -m venv --system-site-packages .venv
   .venv/bin/python -m pip install -r desktop-requirements.txt
   chmod +x MDZ-SkyScan.sh
   ./MDZ-SkyScan.sh
   ```

SkyScan opens in its own desktop window using GTK/WebKit. Closing the window stops
its private background server. The virtual environment must use the distro's
Python so it can access the distro PyGObject bindings. ARM64 Switchroot does not
need Qt or architecture-specific Python WebView wheels.

### Original Switchroot desktop launcher

The Fedora desktop shortcut and idle/sleep inhibitor are available from a Git
checkout. Install the Linux dependencies and `.venv` above, then:

```bash
git clone https://github.com/MDZ-code-dev/MDZ-flight-tracker.git
cd MDZ-flight-tracker
bash install.sh
```

Search the application launcher for **MDZ SkyScan**, or run `bash start.sh`.
This uses `systemd-inhibit` to keep the Switch awake while its native app window
is open. Closing the window stops the server and releases the sleep inhibitor.
Use the portable launcher on systems without systemd or when sleep inhibition
is unnecessary.

## Windows

1. Download **MDZ-SkyScan-windows.exe** and run it directly. No Python installation
   or `_internal` folder is needed.
2. Alternatively, download `MDZ-SkyScan-windows.zip`, **Extract All**, and run
   **MDZ-SkyScan.exe** inside its `MDZ-SkyScan` folder. The ZIP also includes the
   optional Microsoft runtime installer.
3. SkyScan opens as its own desktop application, without browser tabs or an address
   bar. Closing the app window also stops its private background server.

The app uses Microsoft's **Edge WebView2 Runtime** inside its window, not the Edge
browser. It is normally present on Windows 10/11. If the app reports that it is
missing, run the included `MicrosoftEdgeWebview2Setup.exe` installer, then reopen
SkyScan. The installer downloads the runtime from Microsoft and needs Internet
access. There is no automatic browser fallback.

The standalone executable unpacks its bundled libraries into a private temporary
folder when it runs. First launch can take a few seconds. This also avoids loading
.NET DLLs directly from an Internet-marked extracted download folder. Windows continues to check the downloaded executable normally.

When updating, run the new executable or extract the new ZIP to a fresh folder.
Check the version in the app footer. Each app window owns a fresh private local
server, so an older SkyScan cannot supply an outdated interface. You can close
old console-based releases after upgrading. Saved location settings are shared
across updates.

The executable is unsigned, so Windows may show a publisher warning. Download
from this repository's releases and check the supplied checksum.

For the source alternative, install [Python 3.11+](https://www.python.org/downloads/windows/)
with the Python launcher/PATH option enabled, extract
`MDZ-SkyScan-windows-portable.zip`, and double-click **MDZ-SkyScan.cmd**.
Install the desktop dependencies first with `py -3 -m pip install -r desktop-requirements.txt`.

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
`MDZ_TRACKER_PORT` selects the HTTP port (default 8765). An explicitly selected
port must be free; app windows never reuse another process. The desktop server binds
only to `127.0.0.1`. Existing `start.sh` users keep their original settings;
switching to a portable launcher uses a separate settings location.

## Develop and build

### Run from source

```bash
git clone https://github.com/MDZ-code-dev/MDZ-flight-tracker.git
cd MDZ-flight-tracker
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r desktop-requirements.txt
.venv/bin/python desktop.py
```

On Windows use Python 3.11+ with `py -3 -m pip install -r desktop-requirements.txt` and
`py -3 desktop.py`. The native GUI loop runs on the main thread and owns its
backend's lifecycle. Linux also needs the GTK dependencies listed above.
For explicit browser-based development only, use `python3 app.py` and open its
printed local address yourself. This server-only option needs Python 3.10+ and
no third-party packages; the app launcher never opens a browser. Run the checks with:

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
py -3 -m pip install pyinstaller==6.16.0 -r desktop-requirements.txt
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name MDZ-SkyScan --collect-all webview --collect-all pythonnet --collect-all clr_loader --add-data "web;web" desktop.py
```

The app is `dist/MDZ-SkyScan.exe`. GitHub Actions tests a downloaded-file scenario:
Internet-marked DLLs reproduce the older loader failure, then the new Internet-marked
standalone executable must open its real app window, render the silhouette and pixel
font, and shut down cleanly. The ZIP contains this same app and the official
runtime installer; a direct executable download is also published.

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
- **Address already in use:** unset `MDZ_TRACKER_PORT` to let each desktop app
  select its own free port. Only explicitly pinned ports can collide.
- **“Failed to resolve Python.Runtime.Loader.Initialize”:** replace older folder-based
  Windows builds with the latest standalone executable. This is a bundled .NET
  library load failure. If the current executable still fails, share `desktop.log`
  from `%LOCALAPPDATA%\mdz-skyscan`; the error dialog shows the exact log path.
- **Android “App not installed”:** check Android 8.0+, free space, and whether an
  installed version has a different signing key.
- **Fedora launcher fails on another distro:** use `MDZ-SkyScan.sh` instead of the
  optional systemd desktop launcher.
- **Update a source checkout:** run `git pull`, close and reopen the app.
  For packages, download and extract the new version.

Desktop startup errors are written to `desktop.log` beside the desktop settings
file. Windows also shows a native error dialog; Linux prints setup guidance in
the launching terminal.
