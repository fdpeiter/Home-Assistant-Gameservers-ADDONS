import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("playit_run", ROOT / "run.py")
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


class AgentTests(unittest.TestCase):
    def test_missing_or_invalid_key_does_not_write_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            for key in ("", "abc", "not-hex", "ab 12"):
                with self.assertRaises(ValueError):
                    run.prepare_secret({"secret_key": key}, path)
                self.assertFalse(path.exists())

    def test_key_is_private_and_can_be_rotated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            run.prepare_secret({"secret_key": " ab12cd34 "}, path)
            self.assertEqual(path.read_text(), "ab12cd34\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.chmod(0o644)
            run.prepare_secret({"secret_key": "ef567890"}, path)
            self.assertEqual(path.read_text(), "ef567890\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertFalse(path.with_suffix(".tmp").exists())

    def test_execs_agent_with_secret_path_and_no_game_dependency(self):
        with patch.object(run.Path, "read_text", return_value=json.dumps({"secret_key": "ab12"})), \
                patch.object(run, "prepare_secret") as prepare, \
                patch.object(run.os, "umask"), patch.object(run.os, "execv") as execute:
            run.main()
        prepare.assert_called_once_with({"secret_key": "ab12"}, Path("/data/playit-secret"))
        execute.assert_called_once_with("/usr/local/bin/playit",
                                        ["playit", "--secret-path", "/data/playit-secret", "--platform-docker"])


if __name__ == "__main__":
    unittest.main()
