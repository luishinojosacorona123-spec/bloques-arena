"""Rampa y pico de 1000 WebSockets locales, 500 partidas lógicas en un proceso."""
import asyncio
import json
import math
import sys
import time
from pathlib import Path

from aiohttp import ClientSession, TCPConnector, web
from aiohttp.test_utils import TestServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from server import Arena


async def run_scenario(name, levels):
    arenas = [Arena() for _ in range(500)]
    app = web.Application()

    async def connect(request):
        return await arenas[int(request.match_info["room"])].ws(request)

    app.router.add_get("/{room}/ws", connect)
    loops = [asyncio.create_task(arena.loop()) for arena in arenas]
    sockets = []
    rows = []
    handshakes = asyncio.Semaphore(48)
    async with TestServer(app) as server, ClientSession(connector=TCPConnector(limit=0)) as client:
        async def join(index):
            async with handshakes, asyncio.timeout(15):
                socket = await client.ws_connect(server.make_url(f"/{index // 2}/ws"))
                try:
                    await socket.receive_json(timeout=10)
                except BaseException:
                    await socket.close()
                    raise
                return socket

        async def measure(index, socket):
            start = time.perf_counter()
            await socket.send_json({"action": "left" if index % 2 else "right"})
            await socket.send_json({"ping": index})
            async with asyncio.timeout(10):
                while True:
                    if (await socket.receive_json()).get("pong") == index:
                        return (time.perf_counter() - start) * 1000

        try:
            for target, batch in levels:
                start = time.perf_counter()
                for first in range(len(sockets), target, batch):
                    joined = await asyncio.gather(
                        *(join(index) for index in range(first, min(first + batch, target))),
                        return_exceptions=True,
                    )
                    sockets.extend(joined)
                    await asyncio.sleep(.15)
                connect_seconds = time.perf_counter() - start
                samples = []
                failed = 0
                for _ in range(4):
                    results = await asyncio.gather(
                        *(measure(index, socket) for index, socket in enumerate(sockets)
                          if not isinstance(socket, Exception)), return_exceptions=True
                    )
                    samples.extend(value for value in results if isinstance(value, float))
                    failed += sum(isinstance(value, Exception) for value in results)
                    await asyncio.sleep(.25)
                samples.sort()
                rows.append(dict(target=target, ccu=sum(len(arena.players) for arena in arenas),
                                 connect_seconds=round(connect_seconds, 3), samples=len(samples),
                                 failures=failed, failed_connections=sum(isinstance(s, Exception) for s in sockets),
                                 rtt_p95_ms=round(samples[math.ceil(.95 * len(samples)) - 1], 2) if samples else None))
                print(f"{name} {target}: {rows[-1]}", file=sys.stderr, flush=True)
        finally:
            await asyncio.gather(*(socket.close() for socket in sockets if not isinstance(socket, Exception)),
                                 return_exceptions=True)
            for loop in loops:
                loop.cancel()
            await asyncio.gather(*loops, return_exceptions=True)
    return {"scenario": name, "levels": rows}


async def main():
    result = {
        "scope": "Un proceso, mismo equipo, 500 salas lógicas. Sin escalado de nodos.",
        "scenarios": [
            await run_scenario("rampa", [(100, 50), (300, 50), (600, 50), (1000, 50)]),
            await run_scenario("pico", [(100, 100), (1000, 900)]),
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
