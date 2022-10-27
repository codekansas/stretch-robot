from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from stretch.backend.camera import router as camera_router
from stretch.backend.ping import router as ping_router
from stretch.utils.logging import configure_logging

logger = logging.getLogger(__name__)

FRONTEND_ROOT = Path(__file__).parent / "frontend" / "build"

if not FRONTEND_ROOT.exists():
    raise RuntimeError("Frontend directory not found; change to `frontend` and run `npm run watch`")

app = FastAPI()
app.include_router(camera_router, prefix="/camera", tags=["camera"])
app.include_router(ping_router, prefix="/ping", tags=["ping"])


app.add_middleware(
    CORSMiddleware,
    # allow_origins=[f"{o.host}:{o.port}" for o in cfg.origins],
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)


@app.get("/")
async def read_index() -> FileResponse:
    return FileResponse(FRONTEND_ROOT / "index.html")


# Mounts frontend static files.
app.mount("/", StaticFiles(directory=FRONTEND_ROOT), name="static")

# Finally configure logging.
configure_logging()
