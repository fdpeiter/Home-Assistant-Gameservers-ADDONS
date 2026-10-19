import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("update", ROOT / "update.py")
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.server = self.root / "server"
        self.steamapps = self.server / "steamapps"
        self.steamapps.mkdir(parents=True)
        self.backups = self.root / "backups"
        self.log = self.root / "update.log"
        self.fake = self.root / "steamcmd"

    def executable(self, body):
        self.fake.write_text("#!/usr/bin/env python3\nimport sys,json\nfrom pathlib import Path\n" + body)
        self.fake.chmod(0o755)

    def run_update(self, attempts=3):
        update.update_server(self.server, self.fake, self.backups, self.log,
                             attempts=attempts, sleep=lambda _: None)

    def test_exact_state_error_recovers_then_updates_without_touching_game_data(self):
        originals = {}
        for app in ("2278520", "228980"):
            path = self.steamapps / f"appmanifest_{app}.acf"
            originals[path.name] = f"stale metadata {app}"
            path.write_text(originals[path.name])
        preserved = [self.root / "savegame" / "world", self.server / "enshrouded_server.json",
                     self.steamapps / "appmanifest_999.acf", self.steamapps / "downloading" / "chunk"]
        for path in preserved:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("must survive")
        self.executable(
            f"server=Path({str(self.server)!r})\n"
            f"Path({str(self.root / 'args.json')!r}).write_text(json.dumps(sys.argv))\n"
            "if (server/'steamapps/appmanifest_2278520.acf').exists():\n"
            " print(\"Error! App '2278520' state is 0x6 after update job.\");sys.exit(1)\n"
            "(server/'enshrouded_server.exe').write_text('new executable')\n"
            "print(\"Success! App '2278520' fully installed.\")\n")
        self.run_update()
        for path in preserved:
            self.assertEqual(path.read_text(), "must survive")
        backups = list(self.backups.glob("*.bak"))
        self.assertEqual(len(backups), 2)
        self.assertEqual({p.read_text() for p in backups}, set(originals.values()))
        args = json.loads((self.root / "args.json").read_text())
        self.assertLess(args.index("+@sSteamCmdForcePlatformType"), args.index("+login"))
        self.assertLess(args.index("+@sSteamCmdForcePlatformBitness"), args.index("+login"))
        self.assertEqual(args[args.index("+@sSteamCmdForcePlatformBitness") + 1], "64")
        self.assertIn("0x6", self.log.read_text())
        self.assertIn("Success!", self.log.read_text())

    def test_unrelated_failure_does_not_reset_manifests(self):
        manifest = self.steamapps / "appmanifest_2278520.acf"
        manifest.write_text("keep me")
        self.executable("print('Connection failed');sys.exit(1)\n")
        with self.assertRaises(RuntimeError):
            self.run_update(attempts=2)
        self.assertEqual(manifest.read_text(), "keep me")
        self.assertFalse(self.backups.exists())

    def test_zero_exit_without_success_is_not_accepted(self):
        (self.server / "enshrouded_server.exe").write_text("old executable")
        self.executable("print(\"Error! App '2278520' state is 0x6 after update job.\")\n")
        with self.assertRaises(RuntimeError):
            self.run_update(attempts=1)

    def test_success_without_executable_is_not_accepted(self):
        self.executable("print(\"Success! App '2278520' fully installed.\")\n")
        with self.assertRaises(RuntimeError):
            self.run_update(attempts=1)

    def test_up_to_date_installation_is_accepted(self):
        (self.server / "enshrouded_server.exe").write_text("existing executable")
        self.executable("print(\"Success! App '2278520' already up to date.\")\n")
        self.run_update()
        self.assertFalse(self.backups.exists())

    def test_persistent_failure_has_bounded_recovery(self):
        manifest = self.steamapps / "appmanifest_2278520.acf"
        manifest.write_text("original")
        self.executable("print(\"Error! App '2278520' state is 0x6 after update job.\");sys.exit(1)\n")
        with self.assertRaisesRegex(RuntimeError, "after 3 attempts"):
            self.run_update()
        self.assertEqual(len(list(self.backups.glob("*.bak"))), 1)
        self.assertEqual(self.log.read_text().count("--- Attempt"), 3)


if __name__ == "__main__":
    unittest.main()
