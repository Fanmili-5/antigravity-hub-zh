import hashlib
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools import orbit_events


class StopStateTests(unittest.TestCase):
    def classify(self, termination_reason, *, idle=True, error=""):
        session = "alpha5-regression-session"
        payload = {
            "conversationId": session,
            "fullyIdle": idle,
            "terminationReason": termination_reason,
            "error": error,
            "workspacePaths": ["/Projects/峡湾"],
        }
        expected_session = hashlib.sha256(session.encode()).hexdigest()[:20]
        expected_group = hashlib.sha256("/Projects/峡湾".encode()).hexdigest()[:20]
        with patch.object(orbit_events.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))):
            with patch.object(orbit_events, "send") as send, patch("sys.stdout", io.StringIO()) as stdout:
                orbit_events.hook("stop")
                self.assertEqual(json.loads(stdout.getvalue()), {"decision": ""})
                send.assert_called_once()
                state, session_id, tag = send.call_args.args
        self.assertEqual(session_id, expected_session)
        self.assertEqual(tag, {"group": expected_group, "label": "峡湾"})
        return state

    def test_step_limit_when_idle_is_marked_for_review(self):
        self.assertEqual(self.classify("max_steps_exceeded"), "error")

    def test_step_limit_while_background_work_continues_is_thinking(self):
        self.assertEqual(self.classify("max_steps_exceeded", idle=False), "thinking")

    def test_normal_model_stop_is_done(self):
        self.assertEqual(self.classify("model_stop"), "done")

    def test_system_errors_remain_marked_for_review(self):
        self.assertEqual(self.classify("error"), "error")
        self.assertEqual(self.classify("model_stop", error="synthetic runner failure"), "error")
