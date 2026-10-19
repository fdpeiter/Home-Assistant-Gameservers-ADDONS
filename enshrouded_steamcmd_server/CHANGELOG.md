# 1.0.3

- Recover SteamCMD app state `0x6` by backing up and resetting only the Enshrouded
  and Steam redistributables app manifests before retrying the update.
- Explicitly request the Windows 64-bit depot before logging into Steam.
- Require SteamCMD success output and the executable before starting the game.
- Keep update diagnostics and manifest backups in persistent `/data`.

# 1.0.2

- Load Wine environment variables through s6's `with-contenv` at startup.
- Forward shutdown to the game before stopping its virtual display.

# 1.0.1

- Disable Docker init so the base image's s6 init runs as PID 1.

# 1.0.0

- Add the Enshrouded SteamCMD and Wine dedicated server with persistent worlds.
- Add HA configuration for server name, password, player slots and startup updates.
