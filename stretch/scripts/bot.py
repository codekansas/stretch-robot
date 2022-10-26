import asyncio
import os

from stretch.app import serve, set_port
from stretch.utils.logging import configure_logging


async def main() -> None:
    """Main application entrypoint."""

    configure_logging()
    if "STRETCH_PORT" in os.environ:
        set_port(int(os.environ["STRETCH_PORT"]))
    await serve()


if __name__ == "__main__":
    asyncio.run(main())
