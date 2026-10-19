"""Supervise the Wine game process and forward add-on shutdown signals."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


def interrupt_game(proc_root=Path("/proc")):
    """Interrupt the Windows game, keeping Xvfb alive while it saves and exits."""
    found = False
    for path in proc_root.glob("[0-9]*/cmdline"):
        try:
            executable = path.read_bytes().split(b"\0")[0].decode(errors="replace").strip()
            executable = executable.replace("\\", "/").rsplit("/", 1)[-1]
            if executable.lower() == "enshrouded_server.exe":
                os.kill(int(path.parent.name), signal.SIGINT)
                found = True
        except (OSError, ValueError):
            continue
    return found


def supervise(game_command, grace=90, restart_check=None, restart_requested=None):
    children = []
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True
        if restart_requested is not None:
            restart_requested.clear()

    previous = {s: signal.signal(s, stop) for s in (signal.SIGTERM, signal.SIGINT)}
    result = 0
    try:
        children.append((subprocess.Popen(game_command, start_new_session=True), signal.SIGINT))
        while not stopping:
            for process, _ in children:
                code = process.poll()
                if code is not None:
                    print(f"[Services] A service exited (code {code}); stopping the add-on", flush=True)
                    result = code if code >= 0 else 1
                    stopping = True
                    break
            if not stopping:
                if restart_check and restart_check() and not stopping:
                    print("[Auto-update] Server empty; stopping for update", flush=True)
                    if restart_requested is not None:
                        restart_requested.set()
                    stopping = True
                    continue
                time.sleep(0.2)
    finally:
        # Interrupt the Windows process, not the group containing its X server.
        interrupted = interrupt_game()
        if stopping:
            print("[Services] Waiting for the game to shut down", flush=True)
        for process, stop_signal in reversed(children):
            try:
                if not interrupted:
                    os.killpg(process.pid, stop_signal)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + grace
        for process, _ in children:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                print("[Services] Game shutdown timed out; forcing cleanup", flush=True)
                result = 1
        for process, _ in children:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return result


def main():
    from auto_update import AutoUpdater

    options = json.loads(Path("/data/options.json").read_text())
    command = ["xvfb-run", "--auto-servernum", "wine", "./enshrouded_server.exe"]
    enabled = options.get("auto_update", False)
    if enabled and not options.get("update_on_start", True):
        raise ValueError("auto_update requires update_on_start: true")
    while True:
        monitor = None
        if enabled:
            try:
                monitor = AutoUpdater(options)
                monitor.start()
            except (OSError, ValueError, KeyError) as error:
                print(f"[Auto-update] Cannot read installed build; monitoring disabled: {error}", flush=True)
        requested = threading.Event()
        try:
            result = supervise(command, restart_check=monitor.should_restart if monitor else None,
                               restart_requested=requested)
        finally:
            if monitor:
                monitor.close()
        if result != 0 or not requested.is_set():
            return result
        # The game has exited gracefully; only now is it safe to replace its files.
        result = subprocess.call([sys.executable, "/update.py"])
        if result:
            return result
        result = subprocess.call([sys.executable, "/configure.py"])
        if result:
            return result
        print("[Auto-update] Update complete; starting the server", flush=True)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as error:
        print(f"[Services] {error}", file=sys.stderr)
        sys.exit(1)
