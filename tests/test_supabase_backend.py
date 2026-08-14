import unittest
from unittest.mock import Mock, patch

import requests

from supabase_backend import SupabaseBackend, SupabaseError


class SupabaseBackendTest(unittest.TestCase):
    def setUp(self):
        self.backend = SupabaseBackend("https://example.supabase.co/", "sb_publishable_test")

    @patch("supabase_backend.requests.post")
    def test_sign_in_returns_session(self, post):
        post.return_value = Mock(
            ok=True,
            content=b"{}",
            headers={"Content-Type": "application/json"},
            status_code=200,
            json=lambda: {"access_token": "token", "user": {"id": "user-1"}},
        )
        result = self.backend.sign_in("user@example.com", "password123")
        self.assertEqual(result["access_token"], "token")
        self.assertIn("grant_type=password", post.call_args.args[0])

    @patch("supabase_backend.requests.post")
    def test_sign_in_exposes_safe_error(self, post):
        post.return_value = Mock(
            ok=False,
            content=b"{}",
            headers={"Content-Type": "application/json"},
            status_code=400,
            json=lambda: {"message": "Invalid login credentials"},
        )
        with self.assertRaisesRegex(SupabaseError, "Invalid login credentials"):
            self.backend.sign_in("user@example.com", "wrong-password")

    @patch("supabase_backend.requests.post")
    def test_non_json_auth_response_does_not_crash(self, post):
        post.return_value = Mock(
            ok=False,
            content=b"<html>upstream error</html>",
            headers={"Content-Type": "text/html"},
            status_code=502,
        )
        with self.assertRaisesRegex(SupabaseError, "HTTP 502"):
            self.backend.sign_up("user@example.com", "password123")

    @patch("supabase_backend.requests.post")
    def test_empty_success_response_has_configuration_hint(self, post):
        post.return_value = Mock(
            ok=True,
            content=b"",
            headers={"Content-Type": "text/plain"},
            status_code=200,
        )
        with self.assertRaisesRegex(SupabaseError, "SUPABASE_URL"):
            self.backend.sign_up("user@example.com", "password123")

    @patch("supabase_backend.requests.request")
    def test_loads_user_state_with_bearer_token(self, request):
        request.return_value = Mock(
            ok=True,
            json=lambda: [{"state": {"completed": ["reading"]}}],
        )
        state = self.backend.load_state("user-1", "access-token")
        self.assertEqual(state, {"completed": ["reading"]})
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer access-token")

    @patch("supabase_backend.requests.request")
    def test_saves_state_with_upsert(self, request):
        request.return_value = Mock(ok=True)
        self.backend.save_state("user-1", "access-token", {"tone": "따뜻한 친구"})
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["json"]["user_id"], "user-1")
        self.assertEqual(kwargs["headers"]["Prefer"], "resolution=merge-duplicates,return=minimal")

    @patch("supabase_backend.requests.request", side_effect=requests.Timeout)
    def test_network_failure_has_user_friendly_message(self, _request):
        with self.assertRaisesRegex(SupabaseError, "기록 서버에 연결할 수 없습니다"):
            self.backend.load_state("user-1", "access-token")


if __name__ == "__main__":
    unittest.main()
