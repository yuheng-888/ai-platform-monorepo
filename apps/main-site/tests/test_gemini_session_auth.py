import unittest

from starlette.requests import Request

from core.auth import SESSION_COOKIE_NAME, build_session_token
from core.db import init_db
from embedded.gemini_business2api.core.session_auth import is_logged_in


def _build_request(*, session=None, state=None, cookies=None) -> Request:
    headers = []
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        headers.append((b"cookie", cookie_header.encode("utf-8")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/gemini/admin/stats",
        "headers": headers,
        "session": session or {},
        "state": state or {},
    }
    return Request(scope)


class GeminiSessionAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_main_site_request_state_bridges_gemini_session(self):
        request = _build_request(state={"auth_username": "admin"})

        self.assertTrue(is_logged_in(request))
        self.assertTrue(request.session.get("authenticated"))
        self.assertEqual(request.session.get("username"), "admin")

    def test_main_site_cookie_bridges_gemini_session(self):
        token = build_session_token("admin")
        request = _build_request(cookies={SESSION_COOKIE_NAME: token})

        self.assertTrue(is_logged_in(request))
        self.assertTrue(request.session.get("authenticated"))
        self.assertEqual(request.session.get("username"), "admin")


if __name__ == "__main__":
    unittest.main()
