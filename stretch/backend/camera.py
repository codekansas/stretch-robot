import asyncio
import errno
import io
import logging
import math
import platform
from typing import AsyncIterable, Optional

import av
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from stretch.utils.logging import configure_logging

logger = logging.getLogger(__name__)

router = r = APIRouter()


async def iter_frames(
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


async def stream_jpeg_frames() -> AsyncIterable[bytes]:
    start_bytes = b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n"
    end_bytes = b"\r\n"
    buffer = io.BytesIO()
    async for frame in iter_frames():
        img = frame.to_image()
        img.save(buffer, format="JPEG")
        img_bytes = buffer.getvalue()
        buffer.seek(0)
        yield start_bytes
        yield img_bytes
        yield end_bytes


@r.get("/")
async def get_camera_feed() -> StreamingResponse:
    return StreamingResponse(stream_jpeg_frames(), media_type="multipart/x-mixed-replace; boundary=frame")


async def listen_for_message(ws: WebSocket, connection_active: asyncio.Event) -> None:
    while True:
        message = await ws.receive()
        if message["type"] == "websocket.disconnect":
            connection_active.set()
            return


@r.websocket("/ws")
async def get_camera_video_feed(ws: WebSocket) -> None:
    await ws.accept()

    connection_active = asyncio.Event()
    asyncio.ensure_future(listen_for_message(ws, connection_active))

    buffer = io.BytesIO()

    try:
        async for frame in iter_frames():
            img = frame.to_image()
            img.save(buffer, format="JPEG")
            img_bytes = buffer.getvalue()
            buffer.seek(0)
            if connection_active.is_set():
                break
            await ws.send_bytes(img_bytes)
            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        logger.exception("Web socket is disconnected")


async def test_iter_frames(total_seconds: float = 3.0, framerate: int = 30) -> None:
    """Tests getting an input video stream using PyAV.

    Usage:
        python -m stretch.backend.camera

    Args:
        total_seconds: The total number of seconds of video to record
        framerate: The framerate for recording the video
    """

    configure_logging()

    total_frames = int(math.ceil(total_seconds * framerate))

    output = av.open("output.mp4", mode="w")
    ovstream = output.add_stream("mpeg4", framerate)
    ovstream.pix_fmt = "yuv420p"
    ovstream.width = 640
    ovstream.height = 480

    i = 0

    async for frame in iter_frames(framerate=framerate):
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
