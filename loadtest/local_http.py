"""Muestras locales de video HLS y API de resultados. Ejecutar desde el repositorio."""
import asyncio
import json
import math
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urljoin

from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector, web
from aiohttp.test_utils import TestServer


def summary(samples):
    durations = sorted(ms for ms, _, _ in samples)
    return {
        "requests": len(samples),
        "errors": sum(not ok for _, ok, _ in samples),
        "p95_ms": round(durations[math.ceil(.95 * len(durations)) - 1], 2),
        "p99_ms": round(durations[math.ceil(.99 * len(durations)) - 1], 2),
        "payload_bytes": sum(size for _, _, size in samples),
    }


async def request(client, method, url, data=None):
    start = time.perf_counter()
    try:
        async with client.request(method, url, json=data) as response:
            body = await response.read()
            return ((time.perf_counter() - start) * 1000, 200 <= response.status < 300, len(body)), body
    except (ClientError, OSError, asyncio.TimeoutError):
        return ((time.perf_counter() - start) * 1000, False, 0), b""


async def scores(client, origin):
    async def user(index):
        samples = []
        for _ in range(4):
            sample, _ = await request(client, "GET", origin + "/top")
            samples.append(sample)
        sample, _ = await request(client, "POST", origin + "/score",
                                  {"match": uuid.uuid4().hex, "player": f"load-{index}", "score": index})
        return samples + [sample]

    users = await asyncio.gather(*(user(index) for index in range(500)))
    return {"scope": "500 clientes concurrentes, 80% GET y 20% POST, Docker con SQLite",
            **summary([sample for user_samples in users for sample in user_samples])}


async def hls(client):
    import imageio_ffmpeg

    with tempfile.TemporaryDirectory() as directory:
        subprocess.run([
            imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-f", "lavfi",
            "-i", "testsrc2=size=640x360:rate=30", "-t", "6", "-c:v", "libx264",
            "-b:v", "1M", "-g", "60", "-sc_threshold", "0", "-hls_time", "2",
            "-hls_playlist_type", "vod", str(Path(directory) / "index.m3u8"),
        ], check=True)
        assets = {path.name: path.read_bytes() for path in Path(directory).iterdir()}
        app = web.Application()

        async def asset(request):
            name = request.match_info["name"]
            if name not in assets:
                raise web.HTTPNotFound()
            kind = "application/vnd.apple.mpegurl" if name.endswith(".m3u8") else "video/mp2t"
            return web.Response(body=assets[name], content_type=kind)

        app.router.add_get("/{name}", asset)
        async with TestServer(app) as server:
            playlist = str(server.make_url("/index.m3u8"))

            async def viewer(index):
                await asyncio.sleep(index / 350)
                first, body = await request(client, "GET", playlist)
                segments = [line for line in body.decode().splitlines() if line and not line.startswith("#")]
                samples = []
                for segment in segments:
                    sample, _ = await request(client, "GET", urljoin(playlist, segment))
                    samples.append(sample)
                    await asyncio.sleep(2)
                return first, samples

            viewers = await asyncio.gather(*(viewer(index) for index in range(500)))
        segment_samples = [sample for _, samples in viewers for sample in samples]
        clip_bytes = sum(path.stat().st_size for path in Path(directory).glob("*.ts"))
        return {
            "scope": "500 clientes HTTP HLS locales, clip sintético de 6 s en memoria, sin reproductor ni CDN",
            "playlists": summary([first for first, _ in viewers]),
            "segments": summary(segment_samples),
            "extrapolated_20000_gb_per_hour_at_measured_clip_rate": round(clip_bytes * 20000 * 600 / 1e9, 2),
            "extrapolated_20000_gb_per_hour_at_6000_kbps": 54000,
        }


async def main():
    async with ClientSession(connector=TCPConnector(limit=100), timeout=ClientTimeout(total=30)) as client:
        result = {"scores": await scores(client, "http://127.0.0.1:17655"), "hls": await hls(client)}
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
