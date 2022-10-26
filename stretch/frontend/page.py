import logging
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.resolve()


async def index(request: web.Request) -> web.Response:  # pylint: disable=unused-argument
    with open(ROOT / "frontend" / "build" / "index.html", "r", encoding="utf-8") as f:
        content = f.read()
    return web.Response(content_type="text/html", text=content)


def serve_frontend(app: web.Application) -> None:
    """Serves the frontend website.

    Args:
        app: The running application
    """

    app.router.add_get("/", index)
    app.router.add_static("/", ROOT / "frontend" / "build")
