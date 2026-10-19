import importlib.util
from pathlib import Path
import signal
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

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

    def test_restart_request_gracefully_stops_game(self):
        requested = threading.Event()
        with patch.object(services, "interrupt_game", return_value=False):
            result = services.supervise([sys.executable, "-c", "import time; time.sleep(60)"],
                                        grace=1, restart_check=lambda: True, restart_requested=requested)
        self.assertEqual(result, 0)
        self.assertTrue(requested.is_set())

    def test_manual_stop_during_final_check_cancels_restart(self):
        import os

        def check():
            os.kill(os.getpid(), signal.SIGTERM)
            return True

        requested = threading.Event()
        with patch.object(services, "interrupt_game", return_value=False):
            result = services.supervise([sys.executable, "-c", "import time; time.sleep(60)"],
                                        grace=1, restart_check=check, restart_requested=requested)
        self.assertEqual(result, 0)
        self.assertFalse(requested.is_set())

    def test_update_happens_between_game_runs(self):
        import json

        with patch.dict(sys.modules):
            sys.modules["auto_update"] = Mock()
            monitor_type = sys.modules["auto_update"].AutoUpdater
            monitor_type.return_value.should_restart.return_value = True
            options = json.dumps({"auto_update": True, "update_on_start": True})
            with patch.object(services.Path, "read_text", return_value=options), \
                    patch.object(services, "supervise") as supervise, \
                    patch.object(services.subprocess, "call", return_value=0) as call:
                events = []

                def game(*args, **kwargs):
                    events.append("game")
                    if len(events) == 1:
                        kwargs["restart_requested"].set()
                    return 0

                def update(command):
                    events.append(command[-1])
                    return 0

                supervise.side_effect = game
                call.side_effect = update
                self.assertEqual(services.main(), 0)
                self.assertEqual(events, ["game", "/update.py", "/configure.py", "game"])
                self.assertEqual(monitor_type.return_value.close.call_count, 2)

    def test_update_failure_does_not_relaunch_game(self):
        import json

        with patch.dict(sys.modules, {"auto_update": Mock()}), \
                patch.object(services.Path, "read_text", return_value=json.dumps(
                    {"auto_update": True, "update_on_start": True})), \
                patch.object(services, "supervise") as supervise, \
                patch.object(services.subprocess, "call", return_value=1):
            def game(*args, **kwargs):
                kwargs["restart_requested"].set()
                return 0
            supervise.side_effect = game
            self.assertEqual(services.main(), 1)
            self.assertEqual(supervise.call_count, 1)


if __name__ == "__main__":
    unittest.main()
