"""Merge HA options into the persistent server config without losing custom settings."""
import json
import math
import os
from pathlib import Path


def configure(options, path):
    password = options["server_password"]
    if not password.strip():
        raise ValueError("Set a non-empty server_password in the add-on configuration first")
    config = json.loads(path.read_text()) if path.exists() else {}
    if options.get("custom_game_settings", False):
        settings = config.setdefault("gameSettings", {})
        for option, field, minimum in (
            ("resource_drop_multiplier", "resourceDropStackAmountFactor", 0.25),
            ("combat_xp_multiplier", "experienceCombatFactor", 0.25),
            ("mining_xp_multiplier", "experienceMiningFactor", 0),
            ("exploration_quest_xp_multiplier", "experienceExplorationQuestsFactor", 0.25),
        ):
            value = options.get(option, 1.0)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not minimum <= value <= 2):
                raise ValueError(f"{option} must be a number between {minimum} and 2")
            settings[field] = value
        config["gameSettingsPreset"] = "Custom"
    config.update(
        name=options["server_name"], slotCount=options["slots"],
        ip="0.0.0.0", queryPort=15637,
        saveDirectory="Z:/share/enshrouded/savegame",
        logDirectory="Z:/share/enshrouded/logs",
    )
    # This wrapper manages one password-protected Friend role. No open guest role.
    config.pop("password", None)
    config["userGroups"] = [{
        "name": "Friend", "password": password, "canKickBan": False,
        "canAccessInventories": True, "canEditBase": True,
        "canExtendBase": True, "reservedSlots": 0,
    }]
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.chmod(0o600)
    os.replace(temporary, path)


if __name__ == "__main__":
    configure(json.loads(Path("/data/options.json").read_text()),
              Path("/share/enshrouded/server/enshrouded_server.json"))
