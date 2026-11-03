#!/usr/bin/env python3
"""Build and sign a universal APK using the official Android SDK and a JDK."""
import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/MDZ-SkyScan-android.apk")
    args = parser.parse_args()
    sdk_path = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk_path:
        parser.error('Set ANDROID_HOME to an SDK with "platforms;android-35" and "build-tools;35.0.0" installed.')
    sdk = Path(sdk_path)
    tools = sdk / "build-tools/35.0.0"
    android_jar = sdk / "platforms/android-35/android.jar"
    if not android_jar.is_file():
        parser.error("Android platform 35 is not installed.")
    java_bin = Path(os.environ["JAVA_HOME"]) / "bin" if os.environ.get("JAVA_HOME") else None

    def java_tool(name):
        return java_bin / name if java_bin else name

    # This local development key is retained outside the repository. For a stable
    # published identity supply your own keystore through the documented variables.
    custom = os.environ.get("MDZ_ANDROID_KEYSTORE")
    if custom:
        keystore = Path(custom).resolve()
        alias = os.environ.get("MDZ_ANDROID_KEY_ALIAS") or "mdz-skyscan"
        if not os.environ.get("MDZ_ANDROID_STORE_PASSWORD"):
            parser.error("MDZ_ANDROID_STORE_PASSWORD is required for a custom keystore.")
        if not os.environ.get("MDZ_ANDROID_KEY_PASSWORD"):
            os.environ["MDZ_ANDROID_KEY_PASSWORD"] = os.environ["MDZ_ANDROID_STORE_PASSWORD"]
    else:
        keystore = Path(os.environ.get("MDZ_ANDROID_DEVELOPMENT_KEYSTORE",
            str(Path.home() / ".android/mdz-skyscan-development.keystore")))
        alias = "androiddebugkey"
        os.environ["MDZ_ANDROID_STORE_PASSWORD"] = "android"
        os.environ["MDZ_ANDROID_KEY_PASSWORD"] = "android"
        if not keystore.exists():
            keystore.parent.mkdir(parents=True, exist_ok=True)
            run(java_tool("keytool"), "-genkeypair", "-noprompt", "-keystore", keystore,
                "-storepass:env", "MDZ_ANDROID_STORE_PASSWORD", "-keypass:env", "MDZ_ANDROID_KEY_PASSWORD",
                "-alias", alias, "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
                "-dname", "CN=MDZ SkyScan Development", "-storetype", "JKS")
        print("Using a DEVELOPMENT signature. Keep the same key for updates; see README.")
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mdz-apk-") as tmp:
        build = Path(tmp)
        source = ROOT / "android/app/src/main"
        assets = build / "assets"
        shutil.copytree(ROOT / "web", assets / "web")
        compiled = build / "resources.zip"
        unsigned = build / "unsigned.apk"
        classes = build / "classes"
        classes.mkdir()
        dex = build / "dex"
        dex.mkdir()
        run(tools / "aapt2", "compile", "--dir", source / "res", "-o", compiled)
        run(tools / "aapt2", "link", "-o", unsigned, "-I", android_jar,
            "--manifest", source / "AndroidManifest.xml", "-A", assets, compiled)
        run(java_tool("javac"), "--release", "8", "-encoding", "UTF-8", "-classpath", android_jar,
            "-d", classes, *sorted(source.glob("java/**/*.java")))
        run(tools / "d8", "--lib", android_jar, "--min-api", "26", "--output", dex,
            *sorted(classes.rglob("*.class")))
        with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
            for path in dex.glob("*.dex"):
                archive.write(path, path.name)
        aligned = build / "aligned.apk"
        run(tools / "zipalign", "-f", "-p", "4", unsigned, aligned)
        run(tools / "apksigner", "sign", "--ks", keystore, "--ks-key-alias", alias,
            "--ks-pass", "env:MDZ_ANDROID_STORE_PASSWORD", "--key-pass", "env:MDZ_ANDROID_KEY_PASSWORD",
            "--out", args.output, aligned)
        run(tools / "apksigner", "verify", "--verbose", args.output)
        run(tools / "zipalign", "-c", "4", args.output)
    print(f"APK built and signature verified: {args.output}")


if __name__ == "__main__":
    main()
