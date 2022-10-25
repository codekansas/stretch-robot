import asyncio
import fractions
import logging
import threading
from pathlib import Path
from typing import Optional

import av
import numpy as np
from aiohttp import web
from aiortc.contrib.media import MediaStreamError, MediaStreamTrack
from av.frame import Frame

from stretch.backend.camera import CameraRTC
from stretch.cpp.realsense.lib import ColorFrameGenerator
from stretch.utils.logging import configure_logging

logger = logging.getLogger(__name__)

TIME_BASE = fractions.Fraction(1, 1_000_000)  # No idea where this number comes from.


def worker(
    loop: asyncio.BaseEventLoop,
    queue: asyncio.Queue[Frame],
    quit_event: threading.Event,
) -> None:
    start_time: Optional[float] = None

    for frame in ColorFrameGenerator():
        arr = np.array(frame, copy=False)
        av_frame = av.VideoFrame.from_ndarray(arr, format="yuyv422")

        if start_time is None:
            start_time, cur_time = frame.frame_timestamp, 0.0
        else:
            cur_time = (frame.frame_timestamp - start_time) / 999

        av_frame.pts = int(cur_time / TIME_BASE)
        av_frame.time_base = TIME_BASE

        logger.debug("frame: %d, pts: %d, time: %f", frame.frame_number, av_frame.pts, av_frame.time)

        asyncio.run_coroutine_threadsafe(queue.put(av_frame), loop)

        # Exit loop if the quit event is set.
        if quit_event.is_set():
            break


class RealSenseStreamTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self) -> None:
        super().__init__()

        self.__thread: Optional[threading.Thread] = None
        self.__quit_event = threading.Event()
        self.__queue: asyncio.Queue[Frame] = asyncio.Queue()

    async def recv(self) -> Frame:
        if self.readyState != "live":
            raise MediaStreamError

        if self.__thread is None:
            self.start()
        frame = await self.__queue.get()

        return frame

    def start(self) -> None:
        self.__thread = threading.Thread(
            name="media-player",
            target=worker,
            args=(
                asyncio.get_event_loop(),
                self.__queue,
                self.__quit_event,
            ),
        )
        self.__thread.start()

    def stop(self) -> None:
        super().stop()

        if self.__thread is not None:
            self.__quit_event.set()
            self.__thread.join()
            self.__thread = None


class RealSenseRTC(CameraRTC):
    def get_media_stream_track(self) -> MediaStreamTrack:
        return RealSenseStreamTrack()


def serve_realsense_camera(app: web.Application) -> None:
    """Serves the RealSeense over RTC.

    Args:
        app: The running application
    """

    # Don't long random aio stuff.
    logging.getLogger("aioice").setLevel(logging.WARNING)

    # camera = RealSenseRTC(force_codec="video/H264")
    camera = RealSenseRTC(force_codec="video/VP8")
    app.on_shutdown.append(camera.on_shutdown)
    app.router.add_post("/realsense/offer", camera.offer)


async def test_realsense_recording(total_frames: int = 250) -> None:
    """Records a video using the RealSense camera.

    Usage:
        python -m stretch.backend.realsense

    Args:
        total_frames: The total number of frames to write
    """

    configure_logging(log_level=logging.DEBUG)

    quit_event = threading.Event()
    queue: asyncio.Queue[Optional[Frame]] = asyncio.Queue()
    thread = threading.Thread(
        name="media-player",
        target=worker,
        args=(asyncio.get_event_loop(), queue, quit_event),
    )
    thread.start()

    # Open container and stream.
    out_path = Path.home() / "animation.mp4"
    container = av.open(str(out_path), mode="w")
    stream = container.add_stream("mpeg4", rate=30)
    stream.width = 640
    stream.height = 480

    for i in range(total_frames):
        logger.info("Writing %d / %d", i, total_frames)
        frame = await queue.get()
        for packet in stream.encode(frame):
            container.mux(packet)

    quit_event.set()
    thread.join()

    # Fluxh and close container.
    for packet in stream.encode():
        container.mux(packet)
    container.close()


if __name__ == "__main__":
    asyncio.run(test_realsense_recording())
