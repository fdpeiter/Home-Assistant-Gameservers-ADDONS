"""Detect Steam build changes and defer updates until confirmed player inactivity."""
from pathlib import Path
import os
import re
import signal
import socket
import subprocess
import tempfile
import threading
import time

APP_ID = "2278520"
SERVER_DIR = Path("/share/enshrouded/server")


def vdf_section(text, name):
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    match = re.search(r'"' + re.escape(name) + r'"\s*\{', text)
    if not match:
        raise ValueError(f"Missing Steam metadata section {name}")
    tokens = iter(re.findall(r'"((?:\\.|[^"\\])*)"|([{}])', text[match.end():]))

    def block():
        values = {}
        for key, brace in tokens:
            if brace == "}":
                return values
            if brace:
                raise ValueError("Malformed Steam metadata")
            value, brace = next(tokens)
            if brace == "}":
                raise ValueError("Missing Steam metadata value")
            values[key] = block() if brace == "{" else value
        raise ValueError("Incomplete Steam metadata")

    try:
        return block()
    except StopIteration as error:
        raise ValueError("Incomplete Steam metadata") from error


def build_id(value):
    if not isinstance(value, str) or not value.isdecimal() or int(value) <= 0:
        raise ValueError("Invalid Steam build ID")
    return value


def installed_build(server_dir=SERVER_DIR):
    text = (server_dir / "steamapps" / f"appmanifest_{APP_ID}.acf").read_text()
    return build_id(vdf_section(text, "AppState")["buildid"])


def public_build(stop, steamcmd="/opt/steamcmd/steamcmd.sh", timeout=120):
    # Metadata only: never run app_update against a running game.
    command = [steamcmd, "+@ShutdownOnFailedCommand", "1", "+@NoPromptForPassword", "1",
               "+@sSteamCmdForcePlatformType", "windows", "+@sSteamCmdForcePlatformBitness", "64",
               "+login", "anonymous", "+app_info_update", "1", "+app_info_print", APP_ID, "+quit"]
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if stop.wait(0.2) or time.monotonic() >= deadline:
                    raise TimeoutError("Steam build check interrupted or timed out")
            if process.returncode:
                raise RuntimeError(f"Steam metadata check exited {process.returncode}")
            output.seek(0)
            data = vdf_section(output.read(4 * 1024 * 1024).decode(errors="replace"), APP_ID)
            return build_id(data["depots"]["branches"]["public"]["buildid"])
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                except ProcessLookupError:
                    process.wait()


def parse_players(data):
    if data[:5] != b"\xff\xff\xff\xffI" or len(data) < 6 or data[5] < 17:
        raise ValueError("Unsupported Steam query response")
    offset = 6
    for _ in range(4):  # Server name, map, folder and game description.
        offset = data.index(b"\0", offset) + 1
    if len(data) < offset + 10:
        raise ValueError("Truncated Steam query response")
    count, maximum = data[offset + 2:offset + 4]
    if maximum == 0 or count > maximum or b"\0" not in data[offset + 9:]:
        raise ValueError("Invalid Steam query player information")
    return count


def player_count(address=("127.0.0.1", 15637), timeout=3):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.settimeout(timeout)
            client.connect(address)
            query = b"\xff\xff\xff\xffTSource Engine Query\0"
            for _ in range(3):
                client.send(query)
                data = client.recv(65535)
                if data[:5] == b"\xff\xff\xff\xffA" and len(data) == 9:
                    query = b"\xff\xff\xff\xffTSource Engine Query\0" + data[5:]
                    continue
                return parse_players(data)
    except (OSError, ValueError, IndexError):
        pass
    # An unavailable or malformed response is UNKNOWN, never an empty server.
    return None


class UpdatePolicy:
    def __init__(self, installed, idle_seconds):
        self.installed = installed
        self.idle_seconds = idle_seconds
        self.pending = None
        self.idle_since = None

    def observe_build(self, remote):
        pending = remote if remote != self.installed else None
        if pending != self.pending:
            self.idle_since = None
        self.pending = pending

    def observe_players(self, count, now):
        if not self.pending or count != 0:
            self.idle_since = None
            return False
        if self.idle_since is None:
            self.idle_since = now
        return now - self.idle_since >= self.idle_seconds


class AutoUpdater:
    def __init__(self, options):
        self.interval = options.get("update_check_minutes", 30) * 60
        self.policy = UpdatePolicy(installed_build(), options.get("update_idle_minutes", 5) * 60)
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self.run, name="steam-update-monitor", daemon=True)

    def start(self):
        print(f"[Auto-update] Monitoring Steam every {self.interval // 60} minutes; "
              f"installed build {self.policy.installed}", flush=True)
        self.thread.start()

    def run(self):
        next_check = time.monotonic() + self.interval
        while not self.stop.wait(30):
            now = time.monotonic()
            if now >= next_check:
                next_check = now + self.interval
                try:
                    remote = public_build(self.stop)
                    previous = self.policy.pending
                    self.policy.observe_build(remote)
                    if self.policy.pending and remote != previous:
                        print(f"[Auto-update] New Steam build {remote}; waiting for an empty server", flush=True)
                except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
                    print(f"[Auto-update] Build check failed; leaving the game running: {error}", flush=True)
                    self.policy.idle_since = None
                    self.ready.clear()
                    continue
            if self.policy.pending:
                if self.policy.observe_players(player_count(), time.monotonic()):
                    self.ready.set()
                    return

    def should_restart(self):
        if not self.ready.is_set():
            return False
        # Check again immediately before shutdown; no cached zero-player result.
        if player_count() == 0:
            return True
        print("[Auto-update] Server occupied or query unavailable; deferring restart", flush=True)
        self.ready.clear()
        self.policy.idle_since = None
        self.thread = threading.Thread(target=self.run, name="steam-update-monitor", daemon=True)
        self.thread.start()
        return False

    def close(self):
        self.stop.set()
        self.thread.join(timeout=10)
