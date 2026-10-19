import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("configure", ROOT / "configure.py")
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigurationTests(unittest.TestCase):
    def test_reject_empty_password_before_creating_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "server.json"
            with self.assertRaises(ValueError):
                configure.configure({"server_password": " "}, path)
            self.assertFalse(path.exists())

    def test_preserve_custom_settings_and_replace_unprotected_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "server.json"
            path.write_text(json.dumps({"gameSettingsPreset": "Hard", "password": "old",
                                        "userGroups": [{"name": "Guest", "password": ""}]}))
            password = 'quote " and unicode á'
            configure.configure({"server_name": "Friends", "server_password": password, "slots": 8}, path)
            result = json.loads(path.read_text())
            self.assertEqual(result["gameSettingsPreset"], "Hard")
            self.assertNotIn("password", result)
            self.assertEqual(len(result["userGroups"]), 1)
            self.assertEqual(result["userGroups"][0]["password"], password)
            self.assertEqual(result["queryPort"], 15637)
            self.assertEqual(result["saveDirectory"], "Z:/share/enshrouded/savegame")


if __name__ == "__main__":
    unittest.main()
