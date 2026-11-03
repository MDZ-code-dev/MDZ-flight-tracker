#!/usr/bin/env python3
"""Install on a test emulator/device, CLEAR app data, and verify UI and bridge."""
import re
import os
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def adb(*args):
    return subprocess.check_output(["adb", *args], text=True)


def screen():
    adb("shell", "uiautomator", "dump", "/sdcard/mdz-ui.xml")
    return ET.fromstring(adb("shell", "cat", "/sdcard/mdz-ui.xml"))


def tap(node):
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.attrib["bounds"]))
    assert x2 > x1 and y2 > y1, "Control is outside viewport: " + repr(node.attrib)
    adb("shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2))


def main():
    adb("install", "-r", str(ROOT / "dist/MDZ-SkyScan-android.apk"))
    adb("shell", "pm", "clear", "dev.mdz.skyscan")
    adb("shell", "am", "start", "-W", "-n", "dev.mdz.skyscan/.MainActivity")
    for _ in range(15):
        tree = screen()
        texts = " ".join(n.attrib.get("text", "") for n in tree.iter())
        if "TRACKER LOCATION" in texts:
            break
        time.sleep(1)
    else:
        raise AssertionError("Android settings UI did not load: " + texts)
    # Empty coordinates exercise persistence without a live API dependency.
    tap(next(n for n in tree.iter() if n.attrib.get("text") == "SAVE"))
    for _ in range(10):
        tree = screen()
        texts = " ".join(n.attrib.get("text", "") for n in tree.iter())
        if "TRACKER LOCATION" not in texts:
            break
        time.sleep(1)
    else:
        raise AssertionError("Android settings save did not complete: " + texts)
    tap(next(n for n in tree.iter() if n.attrib.get("text") == "MODE: NEAREST"))
    tree = screen()
    assert any(n.attrib.get("text") == "MODE: RADAR" for n in tree.iter()), "Radar switch failed"
    print("PASS: APK installs, opens UI, reads/saves native settings, and switches to radar")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("::error::Android smoke test: " + str(error).replace("\n", " "))
        diagnostics = "Android smoke test failed: " + repr(error) + "\n"
        try:
            tree = screen()
            diagnostics += "\nUI text and bounds:\n" + "\n".join(
                repr(n.attrib) for n in tree.iter() if n.attrib.get("text") or n.attrib.get("clickable") == "true")
            diagnostics += "\n\nRuntime errors:\n" + adb("logcat", "-d", "-t", "300", "AndroidRuntime:E", "chromium:E", "*:S")
        except Exception as diagnostic_error:
            diagnostics += "\nDiagnostics unavailable: " + repr(diagnostic_error)
        print(diagnostics)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
                summary.write("### Android smoke diagnostics\n\n```text\n" + diagnostics + "\n```\n")
        raise
