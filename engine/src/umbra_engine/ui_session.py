"""Browser sessions for the local web app, so the API token never travels in a URL.

`umbra-engine serve` (or `open`) mints a one-time login code and opens `/#login=<code>`: the fragment
never reaches the server or its logs. The page trades the code for an HttpOnly session cookie.
Sessions live in memory: restarting the engine signs every browser out.
"""

import secrets
import threading
import time
from collections.abc import Callable

LOGIN_CODE_TTL = 120.0
SESSION_TTL = 12 * 3600.0
SESSION_COOKIE = "umbra_session"
# Cookie requests must carry this header: a page on another local port is "same-site" for the
# browser, but a custom header forces a CORS preflight that this API never grants.
UI_CLIENT_HEADER = "X-Umbra-Client"


class UiSessions:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._codes: dict[str, float] = {}
        self._sessions: dict[str, float] = {}
        self._lock = threading.Lock()

    def new_login_code(self) -> str:
        code = secrets.token_urlsafe(24)
        with self._lock:
            self._codes[code] = self._clock() + LOGIN_CODE_TTL
        return code

    def redeem(self, code: str) -> str | None:
        """A code opens one session, once, before it expires."""
        now = self._clock()
        with self._lock:
            expires = self._codes.pop(code, None)
            if expires is None or expires < now:
                return None
            session = secrets.token_urlsafe(32)
            self._sessions[session] = now + SESSION_TTL
            return session

    def is_valid(self, session: str) -> bool:
        with self._lock:
            expires = self._sessions.get(session)
            if expires is None:
                return False
            if expires < self._clock():
                del self._sessions[session]
                return False
            return True
