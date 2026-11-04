#!/usr/bin/env python3
"""Launch SkyScan in an embedded desktop window; closing it stops its backend."""
import ctypes
import importlib
import json
import os
import platform
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path


WINDOW_TITLE = "MDZ SkyScan"


def bundle_directory():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def require_windows_runtime():
    # pywebview otherwise silently falls back to legacy MSHTML, which cannot
    # run this interface. Detect the supported renderer before creating a GUI.
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full") as key:
            framework = int(winreg.QueryValueEx(key, "Release")[0])
        if framework < 394802:
            raise ValueError("Unsupported .NET Framework version")
    except (OSError, ValueError) as error:
        raise RuntimeError("Microsoft .NET Framework 4.6.2 or newer is required. "
                           "Install .NET Framework 4.8 and reopen SkyScan.") from error
    roots = (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)
    runtime = r"\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    for root in roots:
        for prefix in ("SOFTWARE", r"SOFTWARE\WOW6432Node"):
            try:
                with winreg.OpenKey(root, prefix + runtime) as key:
                    version = str(winreg.QueryValueEx(key, "pv")[0])
                    if int(version.split(".")[0]) >= 86:
                        return
            except (OSError, ValueError):
                pass
    raise RuntimeError(
        "Microsoft Edge WebView2 Runtime is required. Run the included "
        "MicrosoftEdgeWebview2Setup.exe, then reopen SkyScan."
    )


def load_webview():
    try:
        return importlib.import_module("webview")
    except ImportError as error:
        if sys.platform.startswith("linux"):
            raise RuntimeError(
                "Linux app setup is incomplete. Open a terminal in the app folder "
                "and run: bash install.sh\nThen start SkyScan from its application shortcut "
                "or run: bash start.sh"
            ) from error
        raise RuntimeError(
            "The desktop window dependency is missing. Install desktop-requirements.txt "
            "with the Python environment used to launch SkyScan. On Linux, also install "
            "GTK, PyGObject, and WebKit2GTK 4.1 as described in README.md."
        ) from error


def configure_settings():
    if "MDZ_TRACKER_CONFIG" not in os.environ:
        base = (Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
                if sys.platform == "win32" else
                Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")))
        os.environ["MDZ_TRACKER_CONFIG"] = str(base / "mdz-skyscan" / "config.json")


def configure_native_test(view):
    # The frozen-app CI test connects to the embedded renderer, not a separate
    # browser. Normal launches never open a debugging port or developer tools.
    value = os.environ.get("MDZ_NATIVE_TEST_PORT")
    enabled = os.environ.get("CI") == "true" and os.environ.get("MDZ_DESKTOP_STATE_FILE") and value
    if not enabled:
        return False
    port = int(value)
    if not 1 <= port <= 65535:
        raise ValueError("Invalid native CI test port")
    view.settings["REMOTE_DEBUGGING_PORT"] = port
    view.settings["OPEN_DEVTOOLS_IN_DEBUG"] = False
    return True


def write_runtime_info(app, url, renderer):
    # Optional diagnostics for the frozen-app smoke test; never enable debugging
    # or expose an application control API in normal operation.
    target = os.environ.get("MDZ_DESKTOP_STATE_FILE")
    if target:
        destination = Path(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = dict(app.health_payload(), pid=os.getpid(), url=url,
                    renderer=renderer, window_title=WINDOW_TITLE,
                    bundle_dir=str(bundle_directory()), frozen=bool(getattr(sys, "frozen", False)))
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_text(json.dumps(data), encoding="utf-8")
        temporary.replace(destination)


def main():
    configure_settings()
    view = load_webview()
    if sys.platform == "win32":
        require_windows_runtime()
    native_test = configure_native_test(view)
    import app

    # Each window owns a backend. An old release can neither supply this UI nor
    # keep this window's server alive after it closes. Honor explicit port pins.
    port = app.PORT if "MDZ_TRACKER_PORT" in os.environ else 0
    try:
        server = app.TrackerHTTPServer((app.HOST, port), app.Handler)
    except OSError as error:
        raise RuntimeError(
            f"Could not start SkyScan on port {port}. Close the app using that port "
            "or unset MDZ_TRACKER_PORT to choose a free port automatically."
        ) from error
    url = f"http://{app.HOST}:{server.server_port}"
    renderer = "edgechromium" if sys.platform == "win32" else "gtk"
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="SkyScan backend")
    thread.start()
    try:
        view.create_window(WINDOW_TITLE, url, width=1180, height=680,
                           min_size=(360, 480), background_color="#070e16",
                           text_select=False)
        write_runtime_info(app, url, renderer)
        # pywebview requires its GUI event loop on the main thread. No default
        # browser is opened, including when dependencies or the renderer fail.
        view.start(gui=renderer, debug=native_test)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def startup_message(error, log_file):
    details = str(error)
    if "Python.Runtime" in details or "pythonnet" in details.lower():
        help_text = ("A bundled .NET library could not be loaded. Use the latest "
                     "standalone SkyScan Windows executable from the project's releases. "
                     "If it still fails, share the startup log below.")
    elif sys.platform == "win32":
        # Specific runtime checks already name the installer that is needed.
        help_text = "See the startup log below for details."
    else:
        help_text = "Open a terminal in the app folder and run: bash install.sh"
    return (f"SkyScan could not open its app window.\n\n{details}\n\n"
            f"{help_text}\n\nStartup log: {log_file}")


def report_error(error):
    target = os.environ.get("MDZ_DESKTOP_STATE_FILE")
    if target:
        try:
            destination = Path(target)
            destination.parent.mkdir(parents=True, exist_ok=True)
            previous = json.loads(destination.read_text()) if destination.exists() else {}
            if not isinstance(previous, dict):
                previous = {}
            previous.update(error=str(error), pid=os.getpid(), bundle_dir=str(bundle_directory()))
            destination.write_text(json.dumps(previous), encoding="utf-8")
        except (OSError, ValueError):
            pass
    config = Path(os.environ.get("MDZ_TRACKER_CONFIG", Path.home() / ".config/mdz-skyscan/config.json"))
    log_file = config.parent / "desktop.log"
    try:
        config.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as stream:
            stream.write(f"\n{datetime.now(timezone.utc).isoformat()} Desktop startup failed\n")
            stream.write(f"Platform: {platform.platform()}\nPython: {sys.version}\n")
            stream.write(f"Bundle: {bundle_directory()}\n")
            traceback.print_exception(type(error), error, error.__traceback__, file=stream)
    except OSError:
        pass
    message = startup_message(error, log_file)
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, message, WINDOW_TITLE, 0x10)
    elif sys.stderr:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        report_error(error)
        sys.exit(1)
