#!/usr/bin/env python3
"""Install on a test emulator/device, CLEAR app data, and verify UI and bridge."""
import re
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
    adb("shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2))


def main():
    adb("install", "-r", str(ROOT / "dist/MDZ-SkyScan-android.apk"))
    adb("shell", "pm", "clear", "dev.mdz.skyscan")
    adb("shell", "am", "start", "-W", "-n", "dev.mdz.skyscan/.MainActivity")
    for _ in range(15):
        tree = screen()
        texts = " ".join(n.attrib.get("text", "") for n in tree.iter())
        if "TRACKER LOCATION" in texts and "MDZ SKYSCAN" in texts:
            break
        time.sleep(1)
    else:
        raise AssertionError("Android UI or native configuration bridge did not load")
    # Empty coordinates exercise persistence without a live API dependency.
    tap(next(n for n in tree.iter() if n.attrib.get("text") == "SAVE"))
    for _ in range(10):
        tree = screen()
        texts = " ".join(n.attrib.get("text", "") for n in tree.iter())
        if "TRACKER LOCATION" not in texts:
            break
        time.sleep(1)
    else:
        raise AssertionError("Android settings save did not complete")
    tap(next(n for n in tree.iter() if n.attrib.get("text") == "MODE: NEAREST"))
    tree = screen()
    assert any(n.attrib.get("text") == "MODE: RADAR" for n in tree.iter()), "Radar switch failed"
    print("PASS: APK installs, opens UI, reads/saves native settings, and switches to radar")


if __name__ == "__main__":
    main()
