from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import requests


class SupabaseError(RuntimeError):
    pass


class SupabaseBackend:
    def __init__(self, url: str, key: str) -> None:
        self.url = self._normalize_project_url(url)
        self.key = key

    @staticmethod
    def _normalize_project_url(url: str) -> str:
        cleaned = url.strip().strip('"').strip("'").rstrip("/")
        parsed = urlsplit(cleaned)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            # Users often copy the REST/Auth endpoint instead of the Project URL.
            if parsed.path.rstrip("/") in {"/rest/v1", "/auth/v1"}:
                return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        return cleaned

    @property
    def public_headers(self) -> dict[str, str]:
        return {"apikey": self.key, "Content-Type": "application/json"}

    def sign_in(self, email: str, password: str) -> dict[str, Any]:
        return self._auth_request(
            "/auth/v1/token?grant_type=password",
            {"email": email, "password": password},
        )

    def sign_up(
        self,
        email: str,
        password: str,
        redirect_to: str | None = None,
    ) -> dict[str, Any]:
        path = "/auth/v1/signup"
        if redirect_to:
            path = f"{path}?redirect_to={quote(redirect_to, safe='')}"
        return self._auth_request(
            path,
            {"email": email, "password": password},
        )

    def _auth_request(self, path: str, payload: dict[str, str]) -> dict[str, Any]:
        try:
            response = requests.post(
                f"{self.url}{path}",
                headers=self.public_headers,
                json=payload,
                timeout=20,
            )
        except requests.RequestException as error:
            raise SupabaseError("인증 서버에 연결할 수 없습니다.") from error
        data = self._safe_json(response)
        if not response.ok:
            message = data.get("msg") or data.get("message") or data.get("error_description")
            if response.status_code == 404:
                raise SupabaseError(
                    "Supabase 프로젝트 주소를 찾지 못했습니다. Streamlit Secrets의 "
                    "SUPABASE_URL에는 https://프로젝트참조.supabase.co 형식의 "
                    "Project URL만 입력해주세요."
                )
            raise SupabaseError(message or f"인증 요청을 처리하지 못했습니다. (HTTP {response.status_code})")
        if not data:
            raise SupabaseError(
                "Supabase 인증 서버가 예상과 다른 응답을 보냈습니다. "
                f"SUPABASE_URL과 Publishable key를 확인해주세요. (HTTP {response.status_code})"
            )
        return data

    @staticmethod
    def _safe_json(response: requests.Response) -> dict[str, Any]:
        if not response.content:
            return {}
        content_type = response.headers.get("Content-Type", "")
        if "json" not in content_type.lower():
            return {}
        try:
            data = response.json()
        except (requests.exceptions.JSONDecodeError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def load_state(self, user_id: str, access_token: str) -> dict[str, Any] | None:
        response = self._data_request(
            "GET",
            f"/rest/v1/user_state?select=state&user_id=eq.{user_id}&limit=1",
            access_token,
        )
        rows = response.json()
        return rows[0]["state"] if rows else None

    def save_state(self, user_id: str, access_token: str, state: dict[str, Any]) -> None:
        self._data_request(
            "POST",
            "/rest/v1/user_state?on_conflict=user_id",
            access_token,
            payload={
                "user_id": user_id,
                "state": state,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    def track_event(
        self,
        user_id: str,
        access_token: str,
        event_name: str,
        metadata: dict[str, Any] | None = None,
        event_key: str | None = None,
    ) -> None:
        payload = {
            "user_id": user_id,
            "event_name": event_name,
            "metadata": metadata or {},
        }
        if event_key:
            payload["event_key"] = event_key
        self._data_request(
            "POST",
            "/rest/v1/analytics_events?on_conflict=user_id,event_key",
            access_token,
            payload=payload,
            extra_headers={"Prefer": "resolution=ignore-duplicates,return=minimal"},
            timeout_seconds=3,
        )

    def load_admin_metrics(self, access_token: str) -> dict[str, Any]:
        response = self._data_request(
            "POST",
            "/rest/v1/rpc/admin_analytics_dashboard",
            access_token,
            payload={},
        )
        data = response.json()
        if not isinstance(data, dict):
            raise SupabaseError("운영 지표 응답 형식이 올바르지 않습니다.")
        return data

    def _data_request(
        self,
        method: str,
        path: str,
        access_token: str,
        payload: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout_seconds: int = 20,
    ) -> requests.Response:
        headers = {**self.public_headers, "Authorization": f"Bearer {access_token}"}
        if extra_headers:
            headers.update(extra_headers)
        try:
            response = requests.request(
                method,
                f"{self.url}{path}",
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
        except requests.RequestException as error:
            raise SupabaseError("기록 서버에 연결할 수 없습니다.") from error
        if not response.ok:
            try:
                message = response.json().get("message")
            except ValueError:
                message = None
            raise SupabaseError(message or f"기록 요청이 실패했습니다. ({response.status_code})")
        return response

