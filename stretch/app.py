from __future__ import annotations

import logging
import os
import socket
import ssl
from typing import Tuple

from aiohttp import web

from stretch.backend.camera import serve_camera
from stretch.backend.realsense import serve_realsense_camera
from stretch.frontend.page import serve_frontend
from stretch.utils.colors import colorize

logger = logging.getLogger(__name__)


def set_port(port: int) -> None:
    port_str = str(port)
    logger.info("Setting port to %s", colorize(port_str, "blue"))
    os.environ["PORT"] = port_str


def get_addr_and_port() -> Tuple[str, int]:
    socket_ptr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_ptr.bind(("", int(os.environ.get("PORT", "0"))))
    addr, port = socket_ptr.getsockname()
    socket_ptr.close()
    logger.info("Got free port at http://%s:%s", colorize(addr, "green"), colorize(str(port), "green"))
    return addr, port


def get_ssl_context() -> ssl.SSLContext | None:
    cert_file = os.environ.get("SSL_CERT_FILE")
    key_file = os.environ.get("SSL_KEY_FILE")

    if cert_file is None:
        logger.warning("SSL cert file not found")
    if key_file is None:
        logger.warning("SSL key file not found")
    if cert_file is None or key_file is None:
        return None

    ssl_context = ssl.SSLContext()
    logger.debug("Loading SSL cert file from %s and key file from %s", cert_file, key_file)
    ssl_context.load_cert_chain(cert_file, key_file)
    return ssl_context


async def app_factory() -> web.Application:
    app = web.Application()
    serve_realsense_camera(app)
    serve_camera(app)
    serve_frontend(app)
    return app


async def serve() -> None:
    """Serves the frontend website."""

    host, port = get_addr_and_port()

    web.run_app(
        await app_factory(),
        host=host,
        port=port,
        ssl_context=get_ssl_context(),
    )
