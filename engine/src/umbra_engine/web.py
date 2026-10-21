"""The local web app: its browser session routes and its built assets (`ui/`, built into `web/`).

The assets are Umbra's own files, never a Project's: Project content only reaches the page through
the API, which reads it through the Secret Guard.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, params, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import Response
from starlette.types import Scope

from umbra_engine.ui_session import UiSessions

WEB_ROOT = Path(__file__).parent / "web"
NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Umbra</title>
<p>The web app is not built. Run <code>npm ci</code> then <code>npm run build</code> in <code>ui/</code>,
then restart <code>umbra-engine serve</code>.</p>"""


class WebFiles(StaticFiles):
    """The built app. The page itself is checked again on every load, so a new build is never missed;
    its assets have a content hash in their name, so they can be kept for good."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        hashed = Path(path).parts[:1] == ("assets",)  # Starlette hands an OS path: `assets\x.js` on Windows
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if hashed else "no-cache"
        return response


class LoginCode(BaseModel):
    code: str


class Session(BaseModel):
    session: str


def add_web_routes(app: FastAPI, authorized: list[params.Depends], sessions: UiSessions) -> None:
    @app.post("/v1/ui/login-codes", dependencies=authorized)
    def new_login_code() -> LoginCode:
        """For `umbra-engine open`: the CLI holds the token, the browser only gets a one-time code."""
        return LoginCode(code=sessions.new_login_code())

    @app.post("/v1/ui/session")
    def open_session(body: LoginCode) -> Session:
        session = sessions.redeem(body.code)
        if session is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "login link expired or already used")
        return Session(session=session)

    if (WEB_ROOT / "index.html").is_file():
        app.mount("/", WebFiles(directory=WEB_ROOT, html=True), name="web")
    else:

        @app.get("/", include_in_schema=False)
        def not_built() -> HTMLResponse:
            return HTMLResponse(NOT_BUILT, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
