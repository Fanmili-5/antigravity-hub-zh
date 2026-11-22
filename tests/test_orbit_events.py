import hashlib
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools import orbit_events


def expected_tag(path, name):
    return {"group": hashlib.sha256(path.encode()).hexdigest()[:20], "label": name}


class WorkspacePathTests(unittest.TestCase):
    def test_equivalent_path_spellings_share_a_group(self):
        path = "/Projects/峡湾"
        self.assertEqual(orbit_events.workspace_label({"workspacePaths": ["/Projects//./峡湾/"]}),
                         expected_tag(path, "峡湾"))

    def test_oversized_hook_payload_is_ignored(self):
        payload = b'{"conversationId":"fixture"}'
        payload = payload.ljust(orbit_events.MAX_EVENT_BYTES + 1, b" ")
        standard_input = SimpleNamespace(buffer=io.BytesIO(payload))
        with patch.object(orbit_events.sys, "stdin", standard_input):
            with patch.object(orbit_events, "send") as send, patch("sys.stdout", io.StringIO()) as stdout:
                orbit_events.hook("stop")
                self.assertEqual(json.loads(stdout.getvalue()), {"decision": ""})
        send.assert_not_called()

    def test_non_utf8_path_does_not_hide_later_valid_workspace(self):
        valid = "/Projects/极地实验"
        malformed = "/Projects/" + chr(0xD800)
        self.assertEqual(orbit_events.workspace_label({"workspacePaths": [malformed, valid]}),
                         expected_tag(valid, "极地实验"))

    def test_embedded_nul_is_skipped(self):
        valid = "/Projects/fjord"
        malformed = "/Projects/" + chr(0) + "broken"
        self.assertEqual(orbit_events.workspace_label({"workspacePaths": [malformed, valid]}),
                         expected_tag(valid, "fjord"))

    def test_hook_forwards_session_when_all_workspace_paths_are_invalid(self):
        session = "conversation-one"
        malformed = "/Projects/" + chr(0xD800)
        payload = json.dumps({"conversationId": session, "workspacePaths": [malformed]}).encode()
        standard_input = SimpleNamespace(buffer=io.BytesIO(payload))
        with patch.object(orbit_events.sys, "stdin", standard_input):
            with patch.object(orbit_events, "send") as send, patch("sys.stdout", io.StringIO()) as stdout:
                orbit_events.hook("think")
                self.assertEqual(json.loads(stdout.getvalue()), {})
        session_id = hashlib.sha256(session.encode()).hexdigest()[:20]
        send.assert_called_once_with("thinking", session_id, None)

    def test_valid_chinese_workspace_keeps_label_and_group(self):
        valid = "/Projects/峡湾"
        self.assertEqual(orbit_events.workspace_label({"workspacePaths": [valid]}),
                         expected_tag(valid, "峡湾"))
