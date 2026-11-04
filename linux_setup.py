#!/usr/bin/env python3
"""Prepare and validate SkyScan's private native Linux Python environment."""
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SYSTEM_PYTHON = Path("/usr/bin/python3")
PYWEBVIEW_VERSION = "6.2.1"
MARKER = ".mdz-managed.json"
OWNER = "MDZ SkyScan Linux runtime"
SETUP_HINT = "Run bash install.sh to prepare or repair the native Linux app."

# Importing these namespaces does not open a window or require a display.
NATIVE_PROBE = """
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
gi.require_version('Soup', '3.0')
gi.require_foreign('cairo')
from gi.repository import Gtk, WebKit2, Soup
import cairo
"""
SYSTEM_PROBE = NATIVE_PROBE + """
import venv
import ensurepip
ensurepip.version()
"""
ENVIRONMENT_PROBE = """
import sys
from pathlib import Path
assert Path(sys.prefix).resolve() == Path(sys.argv[1]).resolve(), 'Not the managed virtual environment'
assert sys.prefix != sys.base_prefix, 'A virtual environment is required'
assert list(sys.version_info[:2]) == [int(sys.argv[2]), int(sys.argv[3])], 'Python version changed'
assert Path(sys.base_prefix).resolve() == Path(sys.argv[4]).resolve(), 'Not the distro Python'
"""
RUNTIME_PROBE = ENVIRONMENT_PROBE + NATIVE_PROBE + """
from importlib.metadata import version
actual = version('pywebview')
assert actual == sys.argv[5], 'pywebview ' + sys.argv[5] + ' is required; found ' + actual
import webview
"""


class SetupError(RuntimeError):
    """An actionable setup failure, suitable for a terminal message."""


def require_system_python(argv):
    """Ignore active venvs and PATH overrides so distro GI matches Python's ABI."""
    if not sys.platform.startswith("linux"):
        raise SetupError("This installer is for Linux. See README.md for other platforms.")
    if not SYSTEM_PYTHON.is_file():
        raise SetupError("Install your distro's python3 package; /usr/bin/python3 is missing.")
    correct = (Path(sys.executable).resolve() == SYSTEM_PYTHON.resolve()
               and sys.prefix == sys.base_prefix and sys.flags.isolated)
    if not correct:
        os.execv(str(SYSTEM_PYTHON), [str(SYSTEM_PYTHON), "-I", str(Path(__file__).resolve()), *argv])


def managed_environment(root=ROOT):
    """Keep environments from different distro Python ABIs side by side."""
    major, minor = sys.version_info[:2]
    return Path(root) / ".mdz-venv" / f"python{major}.{minor}"


def _expected_marker():
    return {"owner": OWNER, "schema": 1, "python": str(SYSTEM_PYTHON),
            "version": list(sys.version_info[:2])}


def _validate_location(environment, create=False):
    """Only use an empty directory or one that this app explicitly owns."""
    parent = environment.parent
    for path in (parent, environment):
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise SetupError(f"Refusing to change {path}: it is not a regular directory. {SETUP_HINT}")
    marker = environment / MARKER
    if marker.is_symlink():
        raise SetupError(f"Refusing to change the linked ownership marker in {environment}.")
    if marker.exists():
        try:
            owned = json.loads(marker.read_text(encoding="utf-8")) == _expected_marker()
        except (OSError, ValueError):
            owned = False
        if not owned:
            raise SetupError(f"The runtime in {environment} is not a recognized SkyScan environment. "
                             "Its files were preserved. Move it aside before running bash install.sh.")
        for path in (environment / "bin", environment / "pyvenv.cfg"):
            if path.is_symlink():
                raise SetupError(f"Refusing to change linked environment files at {path}; files were preserved.")
        return
    if environment.exists() and any(environment.iterdir()):
        raise SetupError(f"Refusing to replace the unmarked environment at {environment}. "
                         "Its files were preserved. Move it aside before running bash install.sh.")
    if not create:
        raise SetupError(f"The native Linux runtime has not been prepared at {environment}. {SETUP_HINT}")
    environment.mkdir(parents=True, exist_ok=True)
    # The temporary file stays outside the environment so interruption cannot
    # leave an unmarked, nonempty environment that cannot be repaired safely.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                         prefix=".mdz-marker-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(_expected_marker(), stream)
            stream.write("\n")
        temporary.replace(marker)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _probe(python, script, arguments=()):
    """Return a concise failure string, retaining successful probes' silence."""
    try:
        result = subprocess.run([str(python), "-I", "-c", script, *map(str, arguments)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return str(error)
    if result.returncode:
        lines = (result.stderr or result.stdout).strip().splitlines()
        return lines[-1] if lines else f"Python exited with status {result.returncode}"
    return None


def _environment_problem(environment, full=False):
    python = environment / "bin/python"
    config = environment / "pyvenv.cfg"
    if not python.is_file() or not os.access(python, os.X_OK):
        return "The managed Python interpreter is missing or unusable"
    if config.is_symlink() or (environment / "bin").is_symlink():
        return "The managed environment has linked configuration or executable directories"
    try:
        options = dict(line.lower().split("=", 1) for line in config.read_text().splitlines() if "=" in line)
    except (OSError, UnicodeError):
        return "The managed virtual environment configuration is missing"
    options = {key.strip(): value.strip() for key, value in options.items()}
    if options.get("include-system-site-packages") != "true":
        return "The managed environment cannot use the distro PyGObject bindings"
    arguments = (environment, *sys.version_info[:2], sys.base_prefix, PYWEBVIEW_VERSION)
    return _probe(python, RUNTIME_PROBE if full else ENVIRONMENT_PROBE, arguments)


def _run(command, description):
    print(description, file=sys.stderr)
    try:
        subprocess.run(list(map(str, command)), check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SetupError(f"{description} failed: {error}. {SETUP_HINT}") from error


def install_system_packages():
    """Only the explicitly invoked installer asks for system package privileges."""
    if shutil.which("dnf"):
        commands = [["dnf", "install", "-y", "python3", "python3-pip", "python3-gobject", "gtk3", "webkit2gtk4.1"]]
    elif shutil.which("apt-get"):
        commands = [["apt-get", "update"],
                    ["apt-get", "install", "-y", "python3", "python3-venv", "python3-gi", "python3-gi-cairo",
                     "gir1.2-gtk-3.0", "gir1.2-webkit2-4.1"]]
    else:
        raise SetupError("No supported Linux package manager was found. Install Python venv/pip, "
                         "PyGObject, Pycairo, GTK3 and WebKit2GTK 4.1 with your distro's tools, "
                         "then run bash install.sh --skip-system-packages. See README.md.")
    prefix = []
    if os.geteuid() != 0:
        if not shutil.which("sudo"):
            instructions = "; ".join(shlex.join(command) for command in commands)
            raise SetupError("Administrator access is needed for the Linux window packages. "
                             f"Ask an administrator to run: {instructions}\n"
                             "Then run bash install.sh --skip-system-packages as your regular user.")
        prefix = ["sudo"]
    for command in commands:
        _run(prefix + command, "Installing Linux native window prerequisites")


def _create_environment(environment):
    # venv repairs in place: no --clear, directory removal, or foreign .venv.
    for path in (environment / "bin", environment / "pyvenv.cfg"):
        if path.is_symlink():
            raise SetupError(f"Refusing to repair linked environment files at {path}; files were preserved.")
    # venv otherwise leaves dangling interpreter symlinks untouched. Replace
    # only these known aliases inside the already marked, app-owned directory.
    for name in ("python", "python3", f"python{sys.version_info.major}.{sys.version_info.minor}"):
        alias = environment / "bin" / name
        if alias.is_symlink():
            alias.unlink()
    _run([SYSTEM_PYTHON, "-I", "-m", "venv", "--system-site-packages", environment],
         f"Preparing SkyScan's managed Python environment: {environment}")


def check(root=ROOT):
    """Validate the managed runtime without creating files or installing packages."""
    environment = managed_environment(root)
    _validate_location(environment)
    problem = _environment_problem(environment, full=True)
    if problem:
        raise SetupError(f"The native Linux runtime is not ready: {problem}. {SETUP_HINT}")
    return environment / "bin/python"


def setup(root=ROOT, skip_system_packages=False):
    """Install missing distro prerequisites and repair only an app-owned venv."""
    root = Path(root)
    environment = managed_environment(root)
    # Check ownership before asking for privileges or changing system packages.
    _validate_location(environment, create=True)
    installed_system_packages = False
    native_problem = _probe(SYSTEM_PYTHON, SYSTEM_PROBE)
    if native_problem:
        if skip_system_packages:
            raise SetupError(f"Linux GTK/WebKit or Python venv prerequisites are missing: {native_problem}. "
                             "Install the distro packages listed in README.md, then rerun bash install.sh.")
        install_system_packages()
        installed_system_packages = True
        native_problem = _probe(SYSTEM_PYTHON, SYSTEM_PROBE)
        if native_problem:
            raise SetupError(f"Linux GTK/WebKit prerequisites are still unavailable: {native_problem}. "
                             "See README.md for the distro package requirements.")

    def prepare():
        nonlocal installed_system_packages
        try:
            _create_environment(environment)
        except SetupError:
            if skip_system_packages or installed_system_packages:
                raise
            # A distro can have working GTK but lack the venv/ensurepip package.
            install_system_packages()
            installed_system_packages = True
            _create_environment(environment)

    python = environment / "bin/python"
    if _environment_problem(environment) or _probe(python, "import pip"):
        prepare()
    if _environment_problem(environment, full=True):
        requirements = root / "desktop-requirements.txt"
        if not requirements.is_file():
            raise SetupError(f"The app download is incomplete: {requirements} is missing.")
        _run([python, "-I", "-m", "pip", "--isolated", "--require-virtualenv", "install",
              "--disable-pip-version-check", "--no-input", "-r", requirements],
             "Installing SkyScan's desktop Python dependencies in its private environment")
    return check(root)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print-python", action="store_true", help="Validate and print only the managed Python path")
    mode.add_argument("--check", action="store_true", help="Check native dependencies without changing anything")
    parser.add_argument("--skip-system-packages", action="store_true",
                        help="Prepare Python dependencies but leave distro packages to the administrator")
    args = parser.parse_args(argv)
    if args.skip_system_packages and (args.print_python or args.check):
        parser.error("--skip-system-packages is only used when installing")
    try:
        require_system_python(argv)
        python = check() if args.print_python or args.check else setup(skip_system_packages=args.skip_system_packages)
    except (SetupError, OSError) as error:
        print(f"SkyScan Linux setup: {error}", file=sys.stderr)
        return 1
    if args.print_python:
        print(python)
    else:
        print(f"SkyScan's native Linux runtime is ready.\nPython: {python}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
