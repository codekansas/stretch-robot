import asyncio
import fractions
import logging
import threading
from pathlib import Path
from typing import Iterator, List, Optional

import numpy as np
from aiohttp import web
from aiortc.contrib.media import MediaStreamError, MediaStreamTrack
from av import VideoFrame
from av.frame import Frame
from PIL import Image

from stretch.backend.camera import CameraRTC
from stretch.cpp.realsense.lib import FrameGenerator
from stretch.utils.logging import configure_logging
from stretch.utils.video import write_animation

logger = logging.getLogger(__name__)

TIME_BASE = fractions.Fraction(1, 1_000_000)  # No idea where this number comes from.


def worker(
    loop: asyncio.BaseEventLoop,
    queue: asyncio.Queue[Optional[Frame]],
    quit_event: threading.Event,
) -> None:
    generator = FrameGenerator()
    start_time: Optional[float] = None

    for frame in generator:
        arr = np.array(frame.rgb, copy=False)
        img = Image.fromarray(arr)
        av_frame = VideoFrame.from_image(img)
        if start_time is None:
            start_time, cur_time = frame.timestamp, 0.0
        else:
            cur_time = (frame.timestamp - start_time) / 1000

        av_frame.pts = int(cur_time / TIME_BASE)
        av_frame.time_base = TIME_BASE

        print(
            "av thing",
            av_frame.height,
            av_frame.width,
            av_frame.pts,
            av_frame.time_base,
            av_frame.time,
            "fps:",
            frame.frame_number / max(av_frame.time, 1),
        )

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
        self.__queue: asyncio.Queue[Optional[Frame]] = asyncio.Queue()

    async def recv(self) -> Frame:
        if self.readyState != "live":
            raise MediaStreamError

        if self.__thread is None:
            self.start()
        frame = await self.__queue.get()
        if frame is None:
            self.stop()
            raise MediaStreamError

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

    camera = RealSenseRTC()
    app.on_shutdown.append(camera.on_shutdown)
    app.router.add_post("/offer", camera.offer)


async def test_realsense_recording(total_frames: int = 100) -> None:
    """Records a video using the RealSense camera.

    Usage:
        python -m stretch.backend.realsense

    Args:
        total_frames: The total number of frames to write
    """

    configure_logging()

    quit_event = threading.Event()
    queue: asyncio.Queue[Optional[Frame]] = asyncio.Queue()
    thread = threading.Thread(
        name="media-player",
        target=worker,
        args=(asyncio.get_event_loop(), queue, quit_event),
    )
    thread.start()

    frames: List[Frame] = []
    for i in range(total_frames):
        logger.info("Frame %d / %d", i, total_frames)
        frames.append(await queue.get())
    quit_event.set()
    thread.join()

    def gen_images() -> Iterator[np.ndarray]:
        for frame in frames:
            yield frame.to_ndarray()

    write_animation(gen_images(), Path.home() / "animation.mp4")


if __name__ == "__main__":
    asyncio.run(test_realsense_recording())
