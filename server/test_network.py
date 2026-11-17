import asyncio,json
from aiohttp import ClientSession
from aiohttp.test_utils import TestServer
from server import make_app

def test_two_players_spectator_and_server_validation():
    async def scenario():
        async with TestServer(make_app()) as srv, ClientSession() as client:
            base=str(srv.make_url('/ws'))
            a=await client.ws_connect(base); b=await client.ws_connect(base)
            try:
                await client.ws_connect(base)
                assert False,'Se aceptó un tercer jugador'
            except Exception as exc:
                assert getattr(exc,'status',None)==409
            viewer=await client.ws_connect(base+'?watch=1')
            await a.send_json({'ping':'test'})
            for _ in range(10):
                if (await a.receive_json()) .get('pong')=='test':break
            else:assert False,'No hubo pong'
            await a.send_json({'score':999999999,'board':[]})
            await viewer.send_json({'action':'drop'})
            await asyncio.sleep(.12)
            state=srv.app['arena'].states()
            assert len(state)==2 and all(p['score']==0 for p in state.values())
            async with client.get(srv.make_url('/metrics')) as r:
                text=await r.text()
                assert 'bloques_players_connected 2.0' in text
                assert 'bloques_viewers_connected 1.0' in text
            await a.close();await b.close();await viewer.close()
    asyncio.run(scenario())
