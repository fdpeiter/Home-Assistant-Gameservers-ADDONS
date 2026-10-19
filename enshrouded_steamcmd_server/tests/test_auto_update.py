import importlib.util
from pathlib import Path
import socket
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("auto_update", ROOT / "auto_update.py")
auto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto)


def info(players=0, maximum=8):
    return (b"\xff\xff\xff\xffI\x11Test\0Map\0Enshrouded\0Enshrouded\0" +
            struct.pack("<HBBB", 0, players, maximum, 0) + b"dw\x01\x00version\0")


class PolicyTests(unittest.TestCase):
    def test_same_build_never_restarts_even_when_empty(self):
        policy = auto.UpdatePolicy("100", 300)
        policy.observe_build("100")
        self.assertFalse(policy.observe_players(0, 0))
        self.assertFalse(policy.observe_players(0, 10000))

    def test_update_waits_for_continuous_idle_period(self):
        policy = auto.UpdatePolicy("100", 300)
        policy.observe_build("101")
        self.assertFalse(policy.observe_players(0, 0))
        self.assertFalse(policy.observe_players(0, 299))
        self.assertTrue(policy.observe_players(0, 300))

    def test_players_and_query_failure_reset_idle_period(self):
        for count in (1, None):
            policy = auto.UpdatePolicy("100", 300)
            policy.observe_build("101")
            policy.observe_players(0, 0)
            self.assertFalse(policy.observe_players(count, 299))
            self.assertFalse(policy.observe_players(0, 300))
            self.assertFalse(policy.observe_players(0, 599))
            self.assertTrue(policy.observe_players(0, 600))

    def test_withdrawn_or_changed_update_resets_idle_period(self):
        policy = auto.UpdatePolicy("100", 300)
        policy.observe_build("101")
        policy.observe_players(0, 0)
        policy.observe_build("102")
        self.assertFalse(policy.observe_players(0, 400))
        policy.observe_build("100")
        self.assertFalse(policy.observe_players(0, 10000))


class QueryTests(unittest.TestCase):
    def test_parse_players_and_reject_incomplete_or_invalid_replies(self):
        self.assertEqual(auto.parse_players(info()), 0)
        self.assertEqual(auto.parse_players(info(3)), 3)
        for packet in (b"", info()[:15], info()[:-1], info(9, 8), b"\xff\xff\xff\xfe" + info()[4:]):
            with self.assertRaises(ValueError):
                auto.parse_players(packet)

    def test_udp_challenge_and_populated_response(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
            server.bind(("127.0.0.1", 0))
            server.settimeout(3)
            errors = []

            def respond():
                try:
                    query, peer = server.recvfrom(1024)
                    server.sendto(b"\xff\xff\xff\xffAabcd", peer)
                    query, peer = server.recvfrom(1024)
                    if not query.endswith(b"abcd"):
                        raise AssertionError("Challenge missing")
                    server.sendto(info(2), peer)
                except Exception as error:
                    errors.append(error)

            thread = threading.Thread(target=respond)
            thread.start()
            self.assertEqual(auto.player_count(server.getsockname(), timeout=1), 2)
            thread.join(timeout=4)
            self.assertFalse(errors)
            self.assertFalse(thread.is_alive())

    def test_unavailable_server_is_unknown(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as unavailable:
            unavailable.bind(("127.0.0.1", 0))
            self.assertIsNone(auto.player_count(unavailable.getsockname(), timeout=0.02))


class BuildTests(unittest.TestCase):
    def test_parse_installed_and_remote_public_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "steamapps").mkdir()
            (root / "steamapps/appmanifest_2278520.acf").write_text('"AppState" { "buildid" "100" }')
            self.assertEqual(auto.installed_build(root), "100")
            fake = root / "steamcmd"
            fake.write_text('#!/usr/bin/env python3\nimport sys\n'
                            'assert "+app_update" not in sys.argv\n'
                            'assert "+app_info_update" in sys.argv\n'
                            'print(\'"2278520" { "depots" { "branches" { "beta" { "buildid" "999" } '
                            '"public" { "buildid" "101" } } } }\')\n')
            fake.chmod(0o755)
            self.assertEqual(auto.public_build(threading.Event(), str(fake)), "101")

    def test_missing_or_malformed_metadata_is_not_an_update(self):
        for text in ("Connection failed", '"2278520" {', '"2278520" { "depots" }'):
            with self.assertRaises(ValueError):
                auto.vdf_section(text, "2278520")
        for value in (None, "", "0", "abc"):
            with self.assertRaises(ValueError):
                auto.build_id(value)

    def test_build_check_can_be_cancelled(self):
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "steamcmd"
            fake.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(60)\n')
            fake.chmod(0o755)
            stop = threading.Event()
            stop.set()
            with self.assertRaises(TimeoutError):
                auto.public_build(stop, str(fake))

    def test_final_player_check_defers_when_player_joins(self):
        monitor = auto.AutoUpdater.__new__(auto.AutoUpdater)
        monitor.ready = threading.Event()
        monitor.ready.set()
        monitor.policy = auto.UpdatePolicy("100", 300)
        monitor.policy.observe_build("101")
        with patch.object(auto, "player_count", return_value=1), \
                patch.object(auto.threading, "Thread") as thread:
            self.assertFalse(monitor.should_restart())
            self.assertFalse(monitor.ready.is_set())
            self.assertIsNone(monitor.policy.idle_since)
            thread.return_value.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
