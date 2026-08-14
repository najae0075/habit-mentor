"""Public deployment availability check using only the Python standard library."""

from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


APP_URL = "https://habit-mentor-najae0075.streamlit.app/"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def main() -> None:
    request = Request(
        APP_URL,
        headers={"User-Agent": "Mozilla/5.0 daily-pace-health-check/1.0"},
    )
    opener = build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            if status == 200 and "text/html" not in content_type:
                raise SystemExit(f"Unexpected content type: {content_type}")
    except HTTPError as error:
        status = error.code

    if status not in {200, 301, 302, 303, 307, 308}:
        raise SystemExit(f"Deployment check failed with HTTP {status}")
    print(f"Deployment is reachable: {APP_URL} (HTTP {status})")


if __name__ == "__main__":
    main()
