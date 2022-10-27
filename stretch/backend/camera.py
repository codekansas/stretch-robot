import asyncio
import errno
import io
import logging
import math
import platform
from typing import Any, AsyncIterable, Dict, Literal, Optional, Set, cast, get_args

import av
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from stretch.utils.logging import configure_logging

try:
    from stretch.cpp.realsense import lib as realsense_lib
except (ImportError, ModuleNotFoundError):
    realsense_lib = None  # type: ignore

logger = logging.getLogger(__name__)

router = r = APIRouter()

CameraType = Literal["depth", "rgb"]


def cast_camera_type(raw_camera_type: str) -> CameraType:
    args = get_args(CameraType)
    assert raw_camera_type in args, f"Invalid camera type: {raw_camera_type}"
    return cast(CameraType, raw_camera_type)


async def iter_webcam_frames(
    *,
    framerate: int = 30,
    width: int = 640,
    height: int = 480,
    pixel_format: str = "yuyv422",
) -> AsyncIterable[av.video.frame.VideoFrame]:
    system = platform.system()
    assert system == "Darwin", f"Unsupported {system=}"

    if system == "Darwin":
        av_fmt, av_file = "avfoundation", "default:none"
    else:
        raise RuntimeError(f"Unsupported {system=}")

    options = {
        "framerate": str(framerate),
        "video_size": f"{width}x{height}",
        "pixel_format": pixel_format,
    }

    try:
        container = av.open(file=av_file, format=av_fmt, mode="r", options=options, timeout=None)
        stream = next(s for s in container.streams if s.type == "video")  # pylint: disable=stop-iteration-return
        video_first_pts: Optional[float] = None

        while True:
            try:
                frame = next(container.decode(stream))  # pylint: disable=stop-iteration-return
            except av.FFmpegError as exc:
                if exc.errno == errno.EAGAIN:
                    await asyncio.sleep(0.01)
                    continue
                raise

            if video_first_pts is None:
                video_first_pts = frame.pts
            frame.pts -= video_first_pts
            yield frame

    except Exception:
        logger.exception("Caught exception while iterating webcam frames")

    finally:
        container.close()


def get_cpp_camera_type(camera_type: CameraType) -> Any:
    match camera_type:
        case "rgb":
            return realsense_lib.CameraType.rgb
        case "depth":
            return realsense_lib.CameraType.depth
    raise KeyError(camera_type)


def get_camera_format(camera_type: CameraType) -> str:
    match camera_type:
        case "rgb":
            return "yuyv422"
        case "depth":
            # After remapping colors.
            # return "rgb24"
            # Without remapping colors.
            return "gray"
    raise KeyError(camera_type)


async def iter_realsense_frames(camera_type: CameraType) -> AsyncIterable[av.video.frame.VideoFrame]:
    if realsense_lib is None:
        webcam_iter = iter_webcam_frames()
        async for frame in webcam_iter:
            yield frame
        return

    for frame in realsense_lib.FrameGenerator(get_cpp_camera_type(camera_type)):
        arr = np.array(frame, copy=False)

        # Can use `matplotlib.cm` to remap depths to RGB. Need to change camera format above.
        # if camera_type == "depth":
        #     arr = arr[..., 1].astype(np.float64) * 255.0 + arr[..., 0].astype(np.float64)
        #     arr = (cm.jet(arr)[..., :3] * 255.0).astype(np.uint8)

        if camera_type == "depth":
            arr = arr[..., 1].astype(np.float64) * 255.0 + arr[..., 0].astype(np.float64)
            # Normal scaling.
            # arr = (arr / 256).astype(np.uint8)
            # Inverse depth scaling.
            arr = (255 * 1024 / (arr + 1024)).astype(np.uint8)

        av_frame = av.video.frame.VideoFrame.from_ndarray(arr, format=get_camera_format(camera_type))
        yield av_frame


class ConnectionManager:
    def __init__(self) -> None:
        self.web_sockets: Dict[CameraType, Set[WebSocket]] = {}
        self.started = asyncio.Event()
        self.task = asyncio.create_task(run_connection_manager(self))

    async def connect(self, camera_type: CameraType, websocket: WebSocket) -> None:
        await websocket.accept()
        if camera_type in self.web_sockets:
            self.web_sockets[camera_type].add(websocket)
        else:
            self.web_sockets[camera_type] = {websocket}
        if not self.started.is_set():
            logger.info("Starting camera stream")
            self.started.set()

    def disconnect(self, camera_type: CameraType, websocket: WebSocket) -> None:
        self.web_sockets[camera_type].remove(websocket)
        if not self.web_sockets[camera_type]:
            self.web_sockets.pop(camera_type)
        if not self.web_sockets:
            logger.info("Stopping camera stream")
            self.started.clear()


async def run_connection_manager(manager: ConnectionManager) -> None:
    buffer = io.BytesIO()

    while True:
        await manager.started.wait()

        async for frame in iter_realsense_frames("rgb"):
            img = frame.to_image()
            img.save(buffer, format="JPEG")
            img_bytes = buffer.getvalue()
            buffer.seek(0)
            if not manager.started.is_set():
                break
            await asyncio.gather(
                *(
                    ws.send_bytes(img_bytes)
                    for wss in manager.web_sockets.values()
                    for ws in wss
                )
            )
            await asyncio.sleep(0.01)


connections = ConnectionManager()


@r.websocket("/{camera}/ws")
async def get_camera_video_feed(ws: WebSocket, camera: str) -> None:
    camera_type = cast_camera_type(camera)

    try:
        await connections.connect(camera_type, ws)

        # Receive until the websocket is closed by the client.
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        logger.exception("Web socket is disconnected")

    finally:
        connections.disconnect(camera_type, ws)


async def test_iter_frames(total_seconds: float = 3.0) -> None:
    """Tests getting an input video stream using PyAV.

    Usage:
        python -m stretch.backend.camera

    Args:
        total_seconds: The total number of seconds of video to record
    """

    configure_logging()

    framerate = 30  # Default value
    total_frames = int(math.ceil(total_seconds * framerate))

    output = av.open("output.mp4", mode="w")
    ovstream = output.add_stream("mpeg4", framerate)
    ovstream.pix_fmt = "yuv420p"
    ovstream.width = 640
    ovstream.height = 480

    i = 0

    async for frame in iter_realsense_frames("depth"):
        i += 1
        if i > total_frames:
            break
        logger.info("Captured frame %d / %d with shape (%d, %d)", i, total_frames, frame.height, frame.width)
        for p in ovstream.encode(frame):
            output.mux(p)

    for p in ovstream.encode():
        output.mux(p)

    output.close()


if __name__ == "__main__":
    asyncio.run(test_iter_frames())
