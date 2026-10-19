"""Run the shared Playit agent without putting its secret in logs or argv."""
import json
import os
from pathlib import Path
import sys


def prepare_secret(options, path):
    secret = options.get("secret_key", "").strip()
    if not secret or len(secret) % 2 or any(c not in "0123456789abcdefABCDEF" for c in secret):
        raise ValueError("Set secret_key to the agent key from Playit.gg before starting this add-on")
    # The daemon supports a plain hex secret file. Replace atomically with mode 600.
    temporary = path.with_suffix(".tmp")
    with open(temporary, "w", opener=lambda p, flags: os.open(p, flags, 0o600)) as stream:
        os.chmod(temporary, 0o600)
        stream.write(secret + "\n")
    os.replace(temporary, path)


def main():
    os.umask(0o077)
    options = json.loads(Path("/data/options.json").read_text())
    prepare_secret(options, Path("/data/playit-secret"))
    print("[Playit] Starting shared agent; manage game tunnels in the Playit dashboard", flush=True)
    # Replace the launcher so HA's init sends shutdown directly to the daemon.
    os.execv("/usr/local/bin/playit", ["playit", "--secret-path", "/data/playit-secret",
                                       "--platform-docker"])


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(f"[Playit] {error}", file=sys.stderr)
        sys.exit(1)
