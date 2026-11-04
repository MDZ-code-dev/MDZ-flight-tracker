import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import linux_setup


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux runtime setup")
class LinuxSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "SkyScan app"
        self.root.mkdir()
        (self.root / "desktop-requirements.txt").write_text("pywebview==6.2.1\n")
        self.environment = linux_setup.managed_environment(self.root)

    def claim(self):
        linux_setup._validate_location(self.environment, create=True)

    def make_environment(self):
        self.claim()
        (self.environment / "bin").mkdir(exist_ok=True)
        python = self.environment / "bin/python"
        python.write_text("managed Python fixture\n")
        python.chmod(0o755)
        (self.environment / "pyvenv.cfg").write_text("include-system-site-packages = true\n")

    def simulate_installer(self, *, runtime_ready=False, pip_ready=True):
        state = {"runtime": runtime_ready, "pip": pip_ready}

        def probe(python, script, arguments=()):
            if script == linux_setup.RUNTIME_PROBE:
                return None if state["runtime"] else "pywebview 6.2.1 is required; found 6.1"
            if script == "import pip":
                return None if state["pip"] else "ModuleNotFoundError: No module named 'pip'"
            return None

        def run(command, description):
            words = list(map(str, command))
            if "venv" in words:
                self.make_environment()
                state["pip"] = True
            elif "pip" in words:
                state["runtime"] = True
            else:
                self.fail(f"Unexpected mutation: {words}")

        return patch.object(linux_setup, "_probe", side_effect=probe), patch.object(linux_setup, "_run", side_effect=run)

    def test_selects_versioned_private_environment_without_touching_foreign_venv(self):
        foreign = self.root / ".venv"
        foreign.mkdir()
        (foreign / "user-data").write_text("preserve me")
        older = self.root / ".mdz-venv/python3.0"
        older.mkdir(parents=True)
        (older / "older-runtime").write_text("also preserve me")
        config = self.root / "config.json"
        config.write_text('{"lat": 45}')
        probe, run = self.simulate_installer()
        with probe, run as commands, patch.object(linux_setup, "install_system_packages") as packages:
            selected = linux_setup.setup(self.root)
        self.assertEqual(selected, self.environment / "bin/python")
        self.assertEqual(self.environment.name, f"python{sys.version_info.major}.{sys.version_info.minor}")
        self.assertEqual((foreign / "user-data").read_text(), "preserve me")
        self.assertEqual((older / "older-runtime").read_text(), "also preserve me")
        self.assertEqual(config.read_text(), '{"lat": 45}')
        marker = json.loads((self.environment / linux_setup.MARKER).read_text())
        self.assertEqual(marker["version"], list(sys.version_info[:2]))
        self.assertEqual(marker["python"], "/usr/bin/python3")
        packages.assert_not_called()
        pip = next(call.args[0] for call in commands.call_args_list if "pip" in call.args[0])
        self.assertEqual(pip[0], selected)
        self.assertIn("--require-virtualenv", pip)
        self.assertIn("--isolated", pip)
        self.assertIn("--no-input", pip)
        self.assertNotIn("sudo", pip)

    def test_unmarked_environment_is_preserved_before_any_package_mutation(self):
        self.environment.mkdir(parents=True)
        precious = self.environment / "user-data"
        precious.write_text("unrelated environment")
        with patch.object(linux_setup, "_probe") as probe, \
             patch.object(linux_setup, "install_system_packages") as packages:
            with self.assertRaisesRegex(linux_setup.SetupError, "unmarked.*environment"):
                linux_setup.setup(self.root)
        self.assertEqual(precious.read_text(), "unrelated environment")
        self.assertFalse((self.environment / linux_setup.MARKER).exists())
        packages.assert_not_called()
        probe.assert_not_called()

    def test_foreign_or_corrupt_markers_are_preserved(self):
        self.environment.mkdir(parents=True)
        marker = self.environment / linux_setup.MARKER
        for contents in ('{"owner":"someone else"}', "interrupted foreign JSON"):
            with self.subTest(contents=contents):
                marker.write_text(contents)
                with self.assertRaisesRegex(linux_setup.SetupError, "not a recognized"):
                    linux_setup.setup(self.root)
                self.assertEqual(marker.read_text(), contents)

    def test_linked_environment_is_never_claimed(self):
        foreign = self.root / "foreign"
        foreign.mkdir()
        self.environment.parent.mkdir()
        self.environment.symlink_to(foreign, target_is_directory=True)
        with self.assertRaisesRegex(linux_setup.SetupError, "not a regular directory"):
            linux_setup.setup(self.root)
        self.assertEqual(list(foreign.iterdir()), [])

    def test_linked_managed_configuration_is_preserved_before_requesting_privileges(self):
        self.claim()
        foreign = self.root / "foreign-config"
        foreign.write_text("unrelated configuration")
        (self.environment / "pyvenv.cfg").symlink_to(foreign)
        with patch.object(linux_setup, "install_system_packages") as packages, \
             patch.object(linux_setup, "_probe") as probe:
            with self.assertRaisesRegex(linux_setup.SetupError, "linked environment files"):
                linux_setup.setup(self.root)
        self.assertEqual(foreign.read_text(), "unrelated configuration")
        packages.assert_not_called()
        probe.assert_not_called()

    def test_partial_managed_environment_and_dangling_python_are_repaired_in_place(self):
        self.claim()
        (self.environment / "bin").mkdir()
        for name in ("python", "python3"):
            (self.environment / "bin" / name).symlink_to("/missing-old-python")
        retained = self.environment / "keep-this-file"
        retained.write_text("keep")
        probe, run = self.simulate_installer()
        with probe, run as commands:
            selected = linux_setup.setup(self.root, skip_system_packages=True)
        self.assertTrue(selected.is_file())
        self.assertEqual(retained.read_text(), "keep")
        creation = commands.call_args_list[0].args[0]
        self.assertEqual(creation[0], Path("/usr/bin/python3"))
        self.assertIn("--system-site-packages", creation)
        self.assertNotIn("--clear", creation)

    def test_missing_pip_is_reseeded_by_distro_venv_not_global_pip(self):
        self.make_environment()
        probe, run = self.simulate_installer(runtime_ready=True, pip_ready=False)
        with probe, run as commands, patch.object(linux_setup, "install_system_packages") as packages:
            linux_setup.setup(self.root)
        self.assertEqual(len(commands.call_args_list), 1)
        self.assertIn("venv", commands.call_args.args[0])
        packages.assert_not_called()

    def test_wrong_webview_version_is_repaired_in_the_existing_managed_environment(self):
        self.make_environment()
        probe, run = self.simulate_installer()
        with probe, run as commands:
            linux_setup.setup(self.root)
        self.assertEqual(len(commands.call_args_list), 1)
        command = commands.call_args.args[0]
        self.assertEqual(command[0], self.environment / "bin/python")
        self.assertIn("pip", command)
        self.assertIn(self.root / "desktop-requirements.txt", command)

    def test_skip_system_packages_fails_clearly_when_gi_is_missing(self):
        with patch.object(linux_setup, "_probe", return_value="No module named gi"), \
             patch.object(linux_setup, "install_system_packages") as packages, \
             patch.object(linux_setup, "_run") as commands:
            with self.assertRaisesRegex(linux_setup.SetupError, "GTK/WebKit.*missing"):
                linux_setup.setup(self.root, skip_system_packages=True)
        packages.assert_not_called()
        commands.assert_not_called()

    def test_missing_ensurepip_installs_system_prerequisites_before_venv(self):
        probe_patch, run_patch = self.simulate_installer()
        with probe_patch as probes, run_patch, \
             patch.object(linux_setup, "install_system_packages") as packages:
            ordinary_probe = probes.side_effect
            first = True

            def probe(python, script, arguments=()):
                nonlocal first
                if script == linux_setup.SYSTEM_PROBE and first:
                    first = False
                    return "ModuleNotFoundError: No module named ensurepip"
                return ordinary_probe(python, script, arguments)

            probes.side_effect = probe
            linux_setup.setup(self.root)
        packages.assert_called_once_with()
        self.assertIn("import ensurepip", linux_setup.SYSTEM_PROBE)
        self.assertIn("ensurepip.version()", linux_setup.SYSTEM_PROBE)

    def test_venv_bootstrap_failure_retries_after_installing_distro_packages(self):
        self.claim()
        attempts = []

        def create(environment):
            attempts.append(environment)
            if len(attempts) == 1:
                raise linux_setup.SetupError("ensurepip unavailable")
            self.make_environment()

        with patch.object(linux_setup, "_probe", return_value=None), \
             patch.object(linux_setup, "_create_environment", side_effect=create), \
             patch.object(linux_setup, "install_system_packages") as packages:
            linux_setup.setup(self.root)
        self.assertEqual(attempts, [self.environment, self.environment])
        packages.assert_called_once_with()

    def test_fedora_packages_use_sudo_only_for_dnf(self):
        with patch.object(linux_setup.shutil, "which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), \
             patch.object(linux_setup.os, "geteuid", return_value=1000), \
             patch.object(linux_setup, "_run") as commands:
            linux_setup.install_system_packages()
        self.assertEqual(commands.call_args.args[0], ["sudo", "dnf", "install", "-y", "python3",
                                                     "python3-pip", "python3-gobject", "gtk3", "webkit2gtk4.1"])

    def test_ubuntu_packages_work_as_root_without_sudo(self):
        with patch.object(linux_setup.shutil, "which", side_effect=lambda cmd: "/usr/bin/apt-get" if cmd == "apt-get" else None), \
             patch.object(linux_setup.os, "geteuid", return_value=0), \
             patch.object(linux_setup, "_run") as commands:
            linux_setup.install_system_packages()
        self.assertEqual(commands.call_args_list[0].args[0], ["apt-get", "update"])
        install = commands.call_args_list[1].args[0]
        self.assertIn("python3-venv", install)
        self.assertIn("python3-gi-cairo", install)
        self.assertIn("gir1.2-webkit2-4.1", install)
        self.assertNotIn("sudo", install)

    def test_no_administrator_access_provides_manual_command_and_does_not_run_it(self):
        with patch.object(linux_setup.shutil, "which", side_effect=lambda cmd: "/usr/bin/dnf" if cmd == "dnf" else None), \
             patch.object(linux_setup.os, "geteuid", return_value=1000), \
             patch.object(linux_setup, "_run") as commands:
            with self.assertRaisesRegex(linux_setup.SetupError, "administrator.*dnf install"):
                linux_setup.install_system_packages()
        commands.assert_not_called()

    def test_check_missing_environment_never_creates_it(self):
        with self.assertRaisesRegex(linux_setup.SetupError, "bash install.sh"):
            linux_setup.check(self.root)
        self.assertFalse(self.environment.parent.exists())

    def test_print_python_is_read_only_and_prints_only_the_validated_path(self):
        self.make_environment()
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        stdout, stderr = io.StringIO(), io.StringIO()
        real_check = linux_setup.check
        with patch.object(linux_setup, "require_system_python"), \
             patch.object(linux_setup, "check", side_effect=lambda: real_check(self.root)), \
             patch.object(linux_setup, "_probe", return_value=None) as probes, \
             patch.object(linux_setup, "_run") as commands, \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = linux_setup.main(["--print-python"])
        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), f"{self.environment / 'bin/python'}\n")
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(before, sorted(path.relative_to(self.root) for path in self.root.rglob("*")))
        self.assertEqual(probes.call_args.args[0], self.environment / "bin/python")
        self.assertEqual(probes.call_args.args[1], linux_setup.RUNTIME_PROBE)
        commands.assert_not_called()

    def test_print_python_failure_has_no_stdout_and_explains_repair(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        real_check = linux_setup.check
        with patch.object(linux_setup, "require_system_python"), \
             patch.object(linux_setup, "check", side_effect=lambda: real_check(self.root)), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = linux_setup.main(["--print-python"])
        self.assertEqual(result, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("bash install.sh", stderr.getvalue())

    def test_active_or_path_python_is_reexecuted_with_isolated_distro_python(self):
        with patch.object(linux_setup.sys, "executable", "/unexpected/python"), \
             patch.object(linux_setup.os, "execv") as execute:
            linux_setup.require_system_python(["--print-python"])
        self.assertEqual(execute.call_args.args[0], "/usr/bin/python3")
        self.assertEqual(execute.call_args.args[1][:2], ["/usr/bin/python3", "-I"])
        self.assertEqual(execute.call_args.args[1][-1], "--print-python")

    def test_native_probe_uses_isolated_python_and_surfaces_import_failure(self):
        failed = subprocess.CompletedProcess([], 1, "", "Traceback...\nValueError: WebKit2 4.1 unavailable\n")
        with patch.object(linux_setup.subprocess, "run", return_value=failed) as run:
            problem = linux_setup._probe(linux_setup.SYSTEM_PYTHON, linux_setup.SYSTEM_PROBE)
        self.assertEqual(problem, "ValueError: WebKit2 4.1 unavailable")
        self.assertEqual(run.call_args.args[0][:3], ["/usr/bin/python3", "-I", "-c"])
        self.assertIn("gi.require_foreign('cairo')", linux_setup.SYSTEM_PROBE)


if __name__ == "__main__":
    unittest.main()
