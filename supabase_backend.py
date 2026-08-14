from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests


class SupabaseError(RuntimeError):
    pass


class SupabaseBackend:
    def __init__(self, url: str, key: str) -> None:
        self.url = url.rstrip("/")
        self.key = key

    @property
    def public_headers(self) -> dict[str, str]:
        return {"apikey": self.key, "Content-Type": "application/json"}

    def sign_in(self, email: str, password: str) -> dict[str, Any]:
        return self._auth_request(
            "/auth/v1/token?grant_type=password",
            {"email": email, "password": password},
        )

    def sign_up(self, email: str, password: str) -> dict[str, Any]:
        return self._auth_request(
            "/auth/v1/signup",
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

    def _data_request(
        self,
        method: str,
        path: str,
        access_token: str,
        payload: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
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
                timeout=20,
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

