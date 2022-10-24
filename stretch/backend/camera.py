import asyncio
import json
import logging
import platform
from typing import Set

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRelay, MediaStreamTrack

from stretch.utils.colors import colorize

logger = logging.getLogger(__name__)


def get_camera_media_player() -> MediaPlayer:
    system = platform.system()
    options = {"framerate": "30", "video_size": "640x480"}

    if system == "Darwin":
        return MediaPlayer("default:none", format="avfoundation", options=options)

    if system == "Linux":
        return MediaPlayer("/dev/video4", format="v4l2", options=options)

    raise NotImplementedError(f"Webcam not supported for {system=}")


def colorize_connection_state(state: str) -> str:
    if state == "failed":
        return colorize(state, "red")
    if state == "connecting":
        return colorize(state, "yellow")
    return colorize(state, "blue")


class CameraRTC:
    def __init__(self) -> None:
        self.pcs: Set[RTCPeerConnection] = set()

    def log_peer_count(self) -> None:
        logger.info("Number of peers: %s", colorize(str(len(self.pcs)), "green"))

    def get_media_stream_track(self) -> MediaStreamTrack:
        return get_camera_media_player().video

    async def offer(self, request: web.Request) -> web.Response:
        params = await request.json()
        desc = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        self.pcs.add(pc)
        self.log_peer_count()

        @pc.on("connectionstatechange")
        async def on_state_change() -> None:
            logger.info("Connection state changed to %s", colorize_connection_state(pc.connectionState))
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)
                self.log_peer_count()

        relay = MediaRelay()
        camera = self.get_media_stream_track()
        track = relay.subscribe(camera)
        pc.addTrack(track)
        await pc.setRemoteDescription(desc)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type,
                },
            ),
        )

    async def on_shutdown(self, app: web.Application) -> None:  # pylint: disable=unused-argument
        await asyncio.gather(*[pc.close() for pc in self.pcs])
        self.pcs.clear()
        self.log_peer_count()


def serve_camera(app: web.Application) -> None:
    """Serves the webcam over RTC.

    Args:
        app: The running application
    """

    # Don't long random aio stuff.
    logging.getLogger("aioice").setLevel(logging.WARNING)

    camera = CameraRTC()
    app.on_shutdown.append(camera.on_shutdown)
    app.router.add_post("/camera/offer", camera.offer)
