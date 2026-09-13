import json
import unittest
from unittest.mock import patch

from reference_client import AuroraAdapterError, AuroraLensClient


class _Resp:
    def __init__(self, obj):
        self.payload = json.dumps(obj).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class ClientTests(unittest.TestCase):
    def test_pass_preserved(self):
        body = {
            "choices": [{"message": {"content": "ok"}}],
            "aurora": {"governance": "PASS", "turn": 2, "session_id": "s1", "audit_id": "a1"},
        }
        with patch("urllib.request.urlopen", return_value=_Resp(body)):
            r = AuroraLensClient("http://aurora").assess(messages=[{"role": "user", "content": "x"}])
        self.assertEqual(r.governance, "PASS")
        self.assertTrue(r.admitted)
        self.assertFalse(r.non_admit)
        self.assertEqual(r.response_text, "ok")

    def test_hard_stop_preserved(self):
        body = {
            "choices": [{"message": {"content": "blocked"}}],
            "aurora": {"governance": "HARD_STOP"},
        }
        with patch("urllib.request.urlopen", return_value=_Resp(body)):
            r = AuroraLensClient("http://aurora").assess(messages=[{"role": "user", "content": "x"}])
        self.assertEqual(r.governance, "HARD_STOP")
        self.assertTrue(r.non_admit)

    def test_missing_governance_fails_closed(self):
        body = {"choices": [{"message": {"content": "unsafe release"}}]}
        with patch("urllib.request.urlopen", return_value=_Resp(body)):
            with self.assertRaises(AuroraAdapterError):
                AuroraLensClient("http://aurora").assess(messages=[{"role": "user", "content": "x"}])

    def test_unknown_outcome_fails_closed(self):
        body = {"choices": [], "aurora": {"governance": "ALLOW_ANYWAY"}}
        with patch("urllib.request.urlopen", return_value=_Resp(body)):
            with self.assertRaises(AuroraAdapterError):
                AuroraLensClient("http://aurora").assess(messages=[{"role": "user", "content": "x"}])


if __name__ == "__main__":
    unittest.main()
