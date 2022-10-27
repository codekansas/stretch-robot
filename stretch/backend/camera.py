import asyncio
import errno
import functools
import io
import logging
import math
import platform
from dataclasses import dataclass
from typing import AsyncIterable, Dict, Iterable, Literal, Optional, Set, cast, get_args

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

SensorType = Literal["depth", "rgb"]


@dataclass(frozen=True)
class Frame:
    rgb: av.video.frame.VideoFrame
    depth: av.video.frame.VideoFrame


def cast_sensor_type(raw_sensor_type: str) -> SensorType:
    args = get_args(SensorType)
    assert raw_sensor_type in args, f"Invalid sensor type: {raw_sensor_type}"
    return cast(SensorType, raw_sensor_type)


async def iter_webcam_frames(
    *,
    framerate: int = 30,
    width: int = 640,
    height: int = 480,
    pixel_format: str = "yuyv422",
) -> AsyncIterable[Frame]:
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

            yield Frame(rgb=frame, depth=frame)

    except Exception:
        logger.exception("Caught exception while iterating webcam frames")

    finally:
        container.close()


async def iter_realsense_frames() -> AsyncIterable[Frame]:
    assert realsense_lib is not None

    for frame in realsense_lib.FrameGenerator():
        rgb_arr = np.array(frame.rgb, copy=False)
        depth_arr = np.array(frame.depth, copy=False)

        depth_arr = depth_arr[..., 1].astype(np.float64) * 256.0 + depth_arr[..., 0].astype(np.float64)
        # Normal scaling.
        # depth_arr = (depth_arr / 256).astype(np.uint8)
        # Inverse depth scaling.
        depth_arr = (255 * 1024 / (depth_arr + 1024)).astype(np.uint8)

        rgb_frame = av.video.frame.VideoFrame.from_ndarray(rgb_arr, format="yuyv422")
        depth_frame = av.video.frame.VideoFrame.from_ndarray(depth_arr, format="gray")

        yield Frame(
            rgb=rgb_frame,
            depth=depth_frame,
        )

        await asyncio.sleep(0.01)


async def iter_frames() -> AsyncIterable[Frame]:
    if realsense_lib is None:
        webcam_iter = iter_webcam_frames()
        async for frame in webcam_iter:
            yield frame

    else:
        realsense_iter = iter_realsense_frames()
        async for frame in realsense_iter:
            yield frame


class ConnectionManager:
    def __init__(self) -> None:
        self.web_sockets: Dict[SensorType, Set[WebSocket]] = {}
        self.started = asyncio.Event()
        self.lock = asyncio.Lock()
        self.task = asyncio.create_task(run_connection_manager(self))

    async def connect(self, sensor_type: SensorType, websocket: WebSocket) -> None:
        await websocket.accept()
        await self.lock.acquire()
        if sensor_type in self.web_sockets:
            self.web_sockets[sensor_type].add(websocket)
        else:
            self.web_sockets[sensor_type] = {websocket}
        self.lock.release()
        if not self.started.is_set():
            logger.info("Starting camera stream")
            self.started.set()

    async def disconnect(self, sensor_type: SensorType, websocket: WebSocket) -> None:
        await self.lock.acquire()
        self.web_sockets[sensor_type].remove(websocket)
        if not self.web_sockets[sensor_type]:
            self.web_sockets.pop(sensor_type)
        self.lock.release()
        if not self.web_sockets:
            logger.info("Stopping camera stream")
            self.started.clear()

    @classmethod
    @functools.lru_cache
    def get(cls) -> "ConnectionManager":
        return cls()  # Returns a singleton to use for all connections.


async def safe_send(ws: WebSocket, img_bytes: bytes) -> None:
    try:
        await asyncio.wait_for(ws.send_bytes(img_bytes), 1.0)
    except Exception:
        logger.exception("Exception while sending websocket bytes")


async def safe_send_many(wss: Iterable[WebSocket], img_bytes: bytes) -> None:
    await asyncio.gather(*(safe_send(ws, img_bytes) for ws in wss), return_exceptions=True)


async def run_connection_manager(manager: ConnectionManager) -> None:
    rgb_buffer = io.BytesIO()
    depth_buffer = io.BytesIO()

    while True:
        await manager.started.wait()

        async for frame in iter_frames():
            rgb_img = frame.rgb.to_image()
            depth_img = frame.depth.to_image()

            rgb_img.save(rgb_buffer, format="JPEG")
            rgb_img_bytes = rgb_buffer.getvalue()
            rgb_buffer.seek(0)

            depth_img.save(depth_buffer, format="JPEG")
            depth_img_bytes = depth_buffer.getvalue()
            depth_buffer.seek(0)

            if not manager.started.is_set():
                break

            await manager.lock.acquire()
            await asyncio.gather(
                safe_send_many(manager.web_sockets.get("rgb", {}), rgb_img_bytes),
                safe_send_many(manager.web_sockets.get("depth", {}), depth_img_bytes),
                return_exceptions=True,
            )
            manager.lock.release()
            await asyncio.sleep(0.01)


@r.websocket("/{sensor}/ws")
async def get_sensor_feed(ws: WebSocket, sensor: str) -> None:
    sensor_type = cast_sensor_type(sensor)

    try:
        await ConnectionManager.get().connect(sensor_type, ws)

        # Receive until the websocket is closed by the client.
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        logger.exception("Web socket is disconnected")

    finally:
        await ConnectionManager.get().disconnect(sensor_type, ws)


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

    async for frame in iter_frames():
        depth = frame.depth
        i += 1
        if i > total_frames:
            break
        logger.info("Captured frame %d / %d with shape (%d, %d)", i, total_frames, depth.height, depth.width)
        for p in ovstream.encode(depth):
            output.mux(p)

    for p in ovstream.encode():
        output.mux(p)

    output.close()


if __name__ == "__main__":
    asyncio.run(test_iter_frames())
