"""Update Enshrouded and recover stale Steam manifests after app state 0x6."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

APP_ID = "2278520"
STATE_ERROR = re.compile(r"App\s+'2278520'\s+state is 0x6\b", re.IGNORECASE)
SUCCESS = re.compile(r"Success!\s+App\s+'2278520'\s+(?:fully installed|already up to date)", re.IGNORECASE)


def recover_manifests(server_dir, backup_dir):
    """Preserve the two known Steam metadata files before letting Steam rebuild them."""
    for app_id in (APP_ID, "228980"):
        manifest = server_dir / "steamapps" / f"appmanifest_{app_id}.acf"
        if manifest.is_symlink():
            raise RuntimeError(f"Refusing to reset symlinked Steam manifest: {manifest}")
        if not manifest.is_file():
            continue
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"{manifest.name}.{time.time_ns()}.bak"
        # /data and /share may be different filesystems; copy before unlinking.
        shutil.copy2(manifest, backup)
        manifest.unlink()
        print(f"[SteamCMD] Stale manifest backed up to {backup}", flush=True)


def update_server(server_dir, steamcmd, backup_dir, log_path, attempts=3, sleep=time.sleep):
    command = [str(steamcmd), "+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1",
               "+@sSteamCmdForcePlatformType", "windows", "+@sSteamCmdForcePlatformBitness", "64",
               "+force_install_dir", str(server_dir), "+login", "anonymous",
               "+app_update", APP_ID, "validate", "+quit"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    recovered = False
    with log_path.open("w") as log:
        for attempt in range(1, attempts + 1):
            print(f"[Enshrouded] SteamCMD install/update attempt {attempt}/{attempts}", flush=True)
            log.write(f"\n--- Attempt {attempt}/{attempts} ---\n")
            state_error = False
            confirmed = False
            app_error = False
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace") as process:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                    log.flush()
                    state_error |= bool(STATE_ERROR.search(line))
                    confirmed |= bool(SUCCESS.search(line))
                    app_error |= "error!" in line.lower() and APP_ID in line
                code = process.wait()
            if code == 0 and confirmed and not app_error and (server_dir / "enshrouded_server.exe").is_file():
                print("[SteamCMD] Server installation/update verified", flush=True)
                return
            print(f"[SteamCMD] Update not verified (exit {code})", flush=True)
            if attempt < attempts:
                if state_error and not recovered:
                    print("[SteamCMD] App state 0x6: rebuilding stale Steam manifest metadata", flush=True)
                    recover_manifests(server_dir, backup_dir)
                    recovered = True
                sleep(attempt * 5)
    free = shutil.disk_usage(server_dir).free // (1024 * 1024)
    raise RuntimeError(f"SteamCMD update failed after {attempts} attempts. "
                       f"Free server disk space: {free} MiB. Update log: {log_path}. "
                       "World saves and game settings have not been reset.")


if __name__ == "__main__":
    try:
        update_server(Path("/share/enshrouded/server"), Path("/opt/steamcmd/steamcmd.sh"),
                      Path("/data/steamcmd-manifest-backups"), Path("/data/steamcmd-update.log"))
    except (OSError, RuntimeError) as error:
        print(f"[SteamCMD] {error}", file=sys.stderr)
        sys.exit(1)
