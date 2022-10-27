import asyncio
import errno
import io
import logging
import math
import platform
from typing import AsyncIterable, Literal, Optional, cast, get_args

import av
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

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


def cast_cpp_camera_type(camera_type: CameraType) -> realsense_lib.CameraType:
    match camera_type:
        case "rgb":
            return realsense_lib.CameraType.rgb
        case "depth":
            return realsense_lib.CameraType.depth
    raise KeyError(camera_type)


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

    for frame in realsense_lib.FrameGenerator(cast_cpp_camera_type(camera_type)):
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


async def stream_jpeg_frames(camera_type: CameraType) -> AsyncIterable[bytes]:
    start_bytes = b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n"
    end_bytes = b"\r\n"
    buffer = io.BytesIO()
    async for frame in iter_realsense_frames(camera_type):
        img = frame.to_image()
        img.save(buffer, format="JPEG")
        img_bytes = buffer.getvalue()
        buffer.seek(0)
        yield start_bytes
        yield img_bytes
        yield end_bytes


@r.get("/")
async def get_camera_feed(camera_type: str) -> StreamingResponse:
    return StreamingResponse(
        stream_jpeg_frames(cast_camera_type(camera_type)),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


async def listen_for_message(ws: WebSocket, connection_active: asyncio.Event) -> None:
    while True:
        message = await ws.receive()
        if message["type"] == "websocket.disconnect":
            connection_active.set()
            return


@r.websocket("/{camera}/ws")
async def get_camera_video_feed(ws: WebSocket, camera: str) -> None:
    await ws.accept()

    connection_active = asyncio.Event()
    asyncio.ensure_future(listen_for_message(ws, connection_active))

    buffer = io.BytesIO()

    try:
        async for frame in iter_realsense_frames(cast_camera_type(camera)):
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
