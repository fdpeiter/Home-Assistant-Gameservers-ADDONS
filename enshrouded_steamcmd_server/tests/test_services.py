import importlib.util
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("services", ROOT / "services.py")
services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)


class ShutdownTests(unittest.TestCase):
    def test_interrupt_targets_game_not_display_or_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pid, command in [(10, b"Xvfb\0:99\0"), (20, b"/bin/sh\0xvfb-run\0wine\0./enshrouded_server.exe"),
                                 (30, b"Z:\\share\\enshrouded\\server\\enshrouded_server.exe  \0")]:
                (root / str(pid)).mkdir()
                (root / str(pid) / "cmdline").write_bytes(command)
            with patch.object(services.os, "kill") as kill:
                self.assertTrue(services.interrupt_game(root))
            kill.assert_called_once_with(30, signal.SIGINT)

    def test_exit_status_is_preserved(self):
        with patch.object(services, "interrupt_game", return_value=False):
            self.assertEqual(services.supervise([sys.executable, "-c", "raise SystemExit(7)"], grace=0.2), 7)
            self.assertEqual(services.supervise([sys.executable, "-c", "pass"], grace=0.2), 0)


if __name__ == "__main__":
    unittest.main()
