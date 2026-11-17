"""Muestra local real: 2 jugadores + rampas de espectadores de estado WebSocket.
No mide video HLS, 1000 jugadores ni escalado de nodos.
"""
import asyncio,json,sys,time,statistics,platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from aiohttp import ClientSession,TCPConnector
from aiohttp.test_utils import TestServer
from server import make_app

async def probe():
    result={'environment':platform.platform(),'python':platform.python_version(),'scope':'Local, un proceso de servidor y generador en la misma máquina; RTT de eco, no latencia de video','rows':[]}
    async with TestServer(make_app()) as srv,ClientSession(connector=TCPConnector(limit=0)) as client:
        base=str(srv.make_url('/ws')); players=[await client.ws_connect(base) for _ in range(2)]
        await players[0].receive_json();await players[1].receive_json()
        for count in (0,10,100,500):
            viewers=await asyncio.gather(*(client.ws_connect(base+'?watch=1') for _ in range(count)))
            async def drain(ws):
                async for _ in ws:pass
            drains=[asyncio.create_task(drain(ws)) for ws in viewers]
            other=asyncio.create_task(drain(players[1]));samples=[]
            for i in range(30):
                t=time.perf_counter(); await players[0].send_json({'ping':i})
                while (await players[0].receive_json()).get('pong')!=i:pass
                samples.append((time.perf_counter()-t)*1000);await asyncio.sleep(.05)
            result['rows'].append(dict(players=2,viewers=count,samples=len(samples),rtt_p50_ms=statistics.median(samples),rtt_p95_ms=sorted(samples)[int(.95*(len(samples)-1))],rtt_p99_ms=sorted(samples)[-1]))
            for ws in viewers:await ws.close()
            for task in drains:task.cancel()
            other.cancel()
        for ws in players:await ws.close()
    return result
if __name__=='__main__':print(json.dumps(asyncio.run(probe()),indent=2,ensure_ascii=False))
