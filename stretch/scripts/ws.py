import asyncio

import websockets


async def hello(websocket) -> None:
    name = await websocket.recv()
    print(f"<<< {name}")

    greeting = f"Hello {name}!"

    await websocket.send(greeting)
    print(f">>> {greeting}")


async def ws_main() -> None:
    async with websockets.serve(hello, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever


def main() -> None:
    """Run the websockets app.

    Usage:
        python -m stretch.scripts.ws
    """

    asyncio.run(ws_main())


if __name__ == "__main__":
    main()
