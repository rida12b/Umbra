"""The MCP server Claude Code starts (`umbra-engine mcp`, stdio; registered by the plugin's `.mcp.json`).
One tool, `show` (seen by Claude as `mcp__…umbra__show`, « umbra.show » in ADR-0007): Claude answers a repo
question in ≤ 3 lines and calls it; the open map tab lights the parts within a second."""

from typing import Annotated, Any, Protocol

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from umbra_engine.engine_link import EngineError, EngineLink

TOOL = "show"
INSTRUCTIONS = (
    "Umbra draws the project map of the repository in a browser tab. When the user asks where or how "
    "something happens in this repo, answer in at most 3 lines, then call `show` to light the answer on "
    "the map. Umbra never runs a model itself."
)
DESCRIPTION = """Light the answer to a repo question on the Umbra map open in the browser.

- caption: the user's question (or the action), one line, as asked,
  e.g. « où j'ajoute un champ prix à Item ? ».
- path: the places to look or change, in order, at most 6, numbered on the map. Each one is a repo path
  (file, or folder ending with /; a new file is fine if its folder exists) or a box of the map. Give each a
  `note` of 2-4 French words (« ajouter le champ », « nouvelle migration », « vérifier ») and a one-sentence
  French `why` shown on hover.
- parts: boxes to light without a number (e.g. the database the change reaches). Boxes holding a path step
  light up by themselves.
A box is named by its id, its title (« Serveur ») or its folder. An unknown name is refused with the list of
valid boxes: correct it and call again. The user's « copier pour Claude » button copies the path's files."""


class Step(BaseModel):
    part: str = Field(description="repo path (file, or folder ending with /) or a box of the map")
    note: str = Field("", description="2-4 French words beside it: « ajouter le champ »")
    why: str = Field("", description="one French sentence on hover: why this place")


class Engine(Protocol):
    def show(self, caption: str, parts: list[str], path: list[Any]) -> dict[str, Any]: ...


def build_server(engine: Engine) -> FastMCP:
    server = FastMCP("umbra", instructions=INSTRUCTIONS, log_level="WARNING")

    @server.tool(name=TOOL, description=DESCRIPTION)
    def show(
        caption: Annotated[str, Field(description="the question or action, one line")],
        path: Annotated[list[Step | str] | None, Field(description="≤ 6 ordered places")] = None,
        parts: Annotated[list[str] | None, Field(description="boxes to light, unnumbered")] = None,
    ) -> str:
        steps = [s.model_dump() if isinstance(s, Step) else s for s in path or []]
        try:
            lit = engine.show(caption, parts or [], steps)
        except EngineError as error:
            raise ToolError(str(error)) from error
        return _said(lit)

    return server


def _said(lit: dict[str, Any]) -> str:
    rows = [
        f"{s['n']} {s['label']}" + (f" ({s['note']})" if s.get("note") else "") for s in lit.get("steps", [])
    ]
    lit_boxes = len(lit.get("boxes", []))
    shown = "; ".join(rows) if rows else "no numbered step"
    return f"Shown on the map: {shown}; {lit_boxes} boxes lit, the rest dimmed. Do not repeat the list."


def serve() -> None:
    build_server(EngineLink.from_env()).run("stdio")


if __name__ == "__main__":
    serve()
