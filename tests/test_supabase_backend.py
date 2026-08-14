import unittest
from unittest.mock import Mock, patch

import requests

from services.supabase import SupabaseBackend, SupabaseError


class SupabaseBackendTest(unittest.TestCase):
    def setUp(self):
        self.backend = SupabaseBackend("https://example.supabase.co/", "sb_publishable_test")

    def test_normalizes_rest_endpoint_to_project_url(self):
        backend = SupabaseBackend(
            "https://example.supabase.co/rest/v1",
            "sb_publishable_test",
        )
        self.assertEqual(backend.url, "https://example.supabase.co")

    def test_normalizes_quoted_project_url(self):
        backend = SupabaseBackend(
            '"https://example.supabase.co/"',
            "sb_publishable_test",
        )
        self.assertEqual(backend.url, "https://example.supabase.co")

    @patch("services.supabase.requests.post")
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

    @patch("services.supabase.requests.post")
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

    @patch("services.supabase.requests.post")
    def test_sign_up_includes_production_redirect(self, post):
        post.return_value = Mock(
            ok=True,
            content=b"{}",
            headers={"Content-Type": "application/json"},
            status_code=200,
            json=lambda: {"user": {"id": "user-1"}},
        )
        self.backend.sign_up(
            "user@example.com",
            "password123",
            redirect_to="https://habit-mentor-najae0075.streamlit.app/",
        )
        requested_url = post.call_args.args[0]
        self.assertIn("redirect_to=https%3A%2F%2Fhabit-mentor-najae0075.streamlit.app%2F", requested_url)

    @patch("services.supabase.requests.post")
    def test_non_json_auth_response_does_not_crash(self, post):
        post.return_value = Mock(
            ok=False,
            content=b"<html>upstream error</html>",
            headers={"Content-Type": "text/html"},
            status_code=502,
        )
        with self.assertRaisesRegex(SupabaseError, "HTTP 502"):
            self.backend.sign_up("user@example.com", "password123")

    @patch("services.supabase.requests.post")
    def test_empty_success_response_has_configuration_hint(self, post):
        post.return_value = Mock(
            ok=True,
            content=b"",
            headers={"Content-Type": "text/plain"},
            status_code=200,
        )
        with self.assertRaisesRegex(SupabaseError, "SUPABASE_URL"):
            self.backend.sign_up("user@example.com", "password123")

    @patch("services.supabase.requests.post")
    def test_not_found_response_explains_project_url_format(self, post):
        post.return_value = Mock(
            ok=False,
            content=b"not found",
            headers={"Content-Type": "text/plain"},
            status_code=404,
        )
        with self.assertRaisesRegex(SupabaseError, "프로젝트참조.supabase.co"):
            self.backend.sign_up("user@example.com", "password123")

    @patch("services.supabase.requests.request")
    def test_loads_user_state_with_bearer_token(self, request):
        request.return_value = Mock(
            ok=True,
            json=lambda: [{"state": {"completed": ["reading"]}}],
        )
        state = self.backend.load_state("user-1", "access-token")
        self.assertEqual(state, {"completed": ["reading"]})
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer access-token")

    @patch("services.supabase.requests.request")
    def test_saves_state_with_upsert(self, request):
        request.return_value = Mock(ok=True)
        self.backend.save_state("user-1", "access-token", {"tone": "따뜻한 친구"})
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["json"]["user_id"], "user-1")
        self.assertEqual(kwargs["headers"]["Prefer"], "resolution=merge-duplicates,return=minimal")

    @patch("services.supabase.requests.request")
    def test_tracks_event_with_deduplication_key(self, request):
        request.return_value = Mock(ok=True)
        self.backend.track_event(
            "user-1",
            "access-token",
            "checkin_completed",
            {"condition": "좋음"},
            "checkin_completed:2026-08-14",
        )

        kwargs = request.call_args.kwargs
        self.assertIn("on_conflict=user_id,event_key", request.call_args.args[1])
        self.assertEqual(kwargs["json"]["event_name"], "checkin_completed")
        self.assertEqual(kwargs["json"]["metadata"], {"condition": "좋음"})
        self.assertEqual(kwargs["headers"]["Prefer"], "resolution=ignore-duplicates,return=minimal")
        self.assertEqual(kwargs["timeout"], 3)

    @patch("services.supabase.requests.request")
    def test_loads_aggregated_admin_metrics_from_secure_rpc(self, request):
        request.return_value = Mock(
            ok=True,
            json=lambda: {"registered_users": 12, "checkin_rate": 75.0},
        )

        metrics = self.backend.load_admin_metrics("admin-token", 30)

        self.assertEqual(metrics["registered_users"], 12)
        self.assertIn("/rest/v1/rpc/admin_analytics_dashboard", request.call_args.args[1])
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer admin-token")
        self.assertEqual(request.call_args.kwargs["json"], {"p_days": 30})

    def test_rejects_invalid_admin_metrics_period(self):
        with self.assertRaisesRegex(ValueError, "1일, 7일 또는 30일"):
            self.backend.load_admin_metrics("admin-token", 14)

    @patch("services.supabase.requests.request")
    def test_falls_back_to_legacy_admin_rpc_when_schema_cache_is_stale(self, request):
        request.side_effect = [
            Mock(
                ok=False,
                status_code=404,
                json=lambda: {
                    "message": "Could not find the function public.admin_analytics_dashboard(p_days) in the schema cache"
                },
            ),
            Mock(ok=True, json=lambda: {"registered_users": 3}),
        ]

        metrics = self.backend.load_admin_metrics("admin-token", 7)

        self.assertTrue(metrics["_legacy_rpc"])
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args.kwargs["json"], {})

    @patch("services.supabase.requests.request", side_effect=requests.Timeout)
    def test_network_failure_has_user_friendly_message(self, _request):
        with self.assertRaisesRegex(SupabaseError, "기록 서버에 연결할 수 없습니다"):
            self.backend.load_state("user-1", "access-token")


if __name__ == "__main__":
    unittest.main()
