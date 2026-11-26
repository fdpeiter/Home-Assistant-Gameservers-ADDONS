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
    def apply_settings(self, directory, options, existing=None):
        path = Path(directory) / "server.json"
        if existing is not None:
            path.write_text(json.dumps(existing))
        configure.configure(dict(server_name="Friends", server_password="secret", slots=8,
                                 **options), path)
        return json.loads(path.read_text())

    def test_double_rates_preserve_other_gameplay_fields_and_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            options = dict(custom_game_settings=True, resource_drop_multiplier=2,
                           combat_xp_multiplier=2, mining_xp_multiplier=2,
                           exploration_quest_xp_multiplier=2)
            result = self.apply_settings(directory, options, {
                "gameSettingsPreset": "Hard", "enableTextChat": True,
                "gameSettings": {"enemyHealthFactor": 3, "experienceCombatFactor": 0.5}})
            self.assertEqual(result["gameSettingsPreset"], "Custom")
            self.assertTrue(result["enableTextChat"])
            self.assertEqual(result["gameSettings"], {
                "enemyHealthFactor": 3, "resourceDropStackAmountFactor": 2,
                "experienceCombatFactor": 2, "experienceMiningFactor": 2,
                "experienceExplorationQuestsFactor": 2})
            self.assertEqual(self.apply_settings(directory, options), result)
            self.assertEqual(self.apply_settings(directory, {"custom_game_settings": False}), result)

    def test_disabled_controls_preserve_existing_gameplay(self):
        for options in ({}, {"custom_game_settings": False, "combat_xp_multiplier": 2}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                result = self.apply_settings(directory, options, {
                    "gameSettingsPreset": "Hard", "gameSettings": {"experienceCombatFactor": 0.5}})
                self.assertEqual(result["gameSettingsPreset"], "Hard")
                self.assertEqual(result["gameSettings"], {"experienceCombatFactor": 0.5})

    def test_new_config_defaults_and_fractional_rates(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.apply_settings(directory, {"custom_game_settings": True,
                "mining_xp_multiplier": 0, "resource_drop_multiplier": 1.5})
            self.assertEqual(result["gameSettingsPreset"], "Custom")
            self.assertEqual(result["gameSettings"], {
                "resourceDropStackAmountFactor": 1.5, "experienceMiningFactor": 0,
                "experienceCombatFactor": 1, "experienceExplorationQuestsFactor": 1})

    def test_invalid_rates_do_not_modify_config(self):
        for option in ("resource_drop_multiplier", "combat_xp_multiplier",
                       "mining_xp_multiplier", "exploration_quest_xp_multiplier"):
            for value in (-1, 2.01, True, "2", None, float("nan"), float("inf")):
                with self.subTest(option=option, value=value), tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "server.json"
                    original = '{"gameSettingsPreset": "Hard"}\n'
                    path.write_text(original)
                    with self.assertRaises(ValueError):
                        self.apply_settings(directory, {"custom_game_settings": True, option: value})
                    self.assertEqual(path.read_text(), original)

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
