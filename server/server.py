import asyncio, json, os, time, uuid, logging
from pathlib import Path
from aiohttp import web, ClientSession, WSMsgType
from prometheus_client import CollectorRegistry, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from game import Game, bot_step

log=logging.getLogger('bloques')
class Arena:
    def __init__(self):
        self.players={}; self.viewers=set(); self.started=False; self.done=False
        self.seed=int(time.time()); self.bot=None; self.last_bot=0; self.last_gravity=0
        self.match=uuid.uuid4().hex; self.results=None; self.submitted=False; self.last_submit=0
        self.registry=CollectorRegistry()
        self.ccu=Gauge('bloques_players_connected','Jugadores humanos',registry=self.registry)
        self.ccv=Gauge('bloques_viewers_connected','Espectadores',registry=self.registry)
        self.tick=Histogram('bloques_tick_seconds','Trabajo del tick',buckets=(.001,.005,.01,.025,.05,.1),registry=self.registry)
        self.lag=Histogram('bloques_loop_lag_seconds','Retraso del bucle',registry=self.registry)

    async def sdk(self,path):
        if os.getenv('AGONES_ENABLED')!='1': return
        async with ClientSession() as s:
            async with s.post('http://localhost:'+os.getenv('AGONES_SDK_HTTP_PORT','9358')+path,json={},timeout=2) as r:
                r.raise_for_status()

    def states(self):
        data={p['id']:dict(name=p['name'],**p['game'].snapshot()) for p in self.players.values()}
        if self.bot: data['bot']=dict(name='Bot CPU',**self.bot.snapshot())
        return data

    async def ws(self,request):
        spectator=request.query.get('watch')=='1'
        if not spectator and (self.done or len(self.players)+(1 if self.bot else 0)>=2):
            raise web.HTTPConflict(text='Partida llena o terminada')
        if spectator and len(self.viewers)>=int(os.getenv('MAX_VIEWERS','500')):
            raise web.HTTPServiceUnavailable(text='Límite de espectadores')
        ws=web.WebSocketResponse(heartbeat=20,max_msg_size=1024)
        await ws.prepare(request)
        ident=uuid.uuid4().hex[:8]
        if spectator: self.viewers.add(ws)
        else:
            # Para producción, conectar solo al endpoint devuelto por GameServerAllocation.
            self.players[ws]=dict(id=ident,name=request.query.get('name','Jugador')[:20],game=Game(self.seed),last=0)
            self.started=True
            if request.query.get('bot')=='1' and len(self.players)==1: self.bot=Game(self.seed)
        self.ccu.set(len(self.players)); self.ccv.set(len(self.viewers))
        await ws.send_json(dict(type='hello',id=ident,watch=spectator))
        try:
            async for msg in ws:
                if msg.type!=WSMsgType.TEXT: continue
                try:
                    d=json.loads(msg.data)
                    if not isinstance(d,dict): continue
                    if 'ping' in d: await ws.send_json(dict(pong=d['ping'])); continue
                    if spectator or self.done: continue
                    p=self.players[ws]; now=time.monotonic()
                    if now-p['last']<.04: continue
                    p['last']=now
                    cleared=p['game'].action(d.get('action'))
                    self.attack(p['game'],cleared)
                except (ValueError,TypeError):
                    await ws.send_json(dict(error='Mensaje inválido'))
        finally:
            self.players.pop(ws,None); self.viewers.discard(ws)
            self.ccu.set(len(self.players)); self.ccv.set(len(self.viewers))
        return ws

    def attack(self,source,cleared):
        if cleared<2: return
        for p in self.players.values():
            if p['game'] is not source: p['game'].garbage(cleared-1)
        if self.bot and source is not self.bot: self.bot.garbage(cleared-1)

    async def submit(self):
        url=os.getenv('LEADERBOARD_URL')
        if not url or not self.results or self.submitted: return
        async with ClientSession() as s:
            headers={}
            if os.getenv('AGONES_ENABLED')=='1':
                async with s.get('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity',
                    params={'audience':url},headers={'Metadata-Flavor':'Google'},timeout=2) as r:
                    r.raise_for_status(); headers['Authorization']='Bearer '+await r.text()
            for result in self.results:
                async with s.post(url+'/score',json=result,headers=headers,timeout=3) as r: r.raise_for_status()
            self.submitted=True

    async def loop(self):
        await self.sdk('/ready'); last_health=0; empty_since=None
        while True:
            start=time.perf_counter(); now=time.monotonic()
            if now-last_health>2:
                await self.sdk('/health'); last_health=now
            if not self.done:
                if self.bot and now-self.last_bot>1.5:
                    n=bot_step(self.bot); self.attack(self.bot,n); self.last_bot=now
                if now-self.last_gravity>.6:
                    for p in self.players.values():
                        n=p['game'].action('down'); self.attack(p['game'],n)
                    self.last_gravity=now
                self.done=any(p['game'].over for p in self.players.values()) or bool(self.bot and self.bot.over)
                if self.done:
                    self.results=[dict(match=self.match,player=p['id'],score=p['game'].score) for p in self.players.values()]
            if self.done and now-self.last_submit>5:
                self.last_submit=now
                try: await self.submit()
                except Exception: log.exception('No se pudo guardar resultado; se reintentará')
            payload=json.dumps(dict(type='state',players=self.states(),done=self.done))
            clients=list(self.players)+list(self.viewers)
            async def send(ws):
                try: await asyncio.wait_for(ws.send_str(payload),.1)
                except Exception: await ws.close()
            if clients: await asyncio.gather(*(send(ws) for ws in clients))
            if self.started and not self.players:
                empty_since=empty_since or now
                if now-empty_since>3:
                    if os.getenv('AGONES_ENABLED')=='1':
                        await self.sdk('/shutdown'); return
                    self.bot=None; self.done=False; self.started=False; self.seed+=1
                    self.match=uuid.uuid4().hex; self.results=None; self.submitted=False
            else: empty_since=None
            work=time.perf_counter()-start; self.tick.observe(work)
            await asyncio.sleep(max(0,.05-work))
            self.lag.observe(max(0,time.perf_counter()-start-.05))

def make_app():
    arena=Arena(); app=web.Application(); app['arena']=arena
    app.router.add_get('/ws',arena.ws)
    async def index(r): return web.FileResponse(Path(__file__).parent/'static'/'index.html')
    async def health(r): return web.json_response({'ok':True})
    async def metrics(r): return web.Response(body=generate_latest(arena.registry),headers={'Content-Type':CONTENT_TYPE_LATEST})
    app.router.add_get('/',index); app.router.add_get('/health',health); app.router.add_get('/metrics',metrics)
    async def start(a): a['task']=asyncio.create_task(arena.loop())
    async def stop(a):
        a['task'].cancel()
        try: await a['task']
        except asyncio.CancelledError: pass
    app.on_startup.append(start); app.on_cleanup.append(stop)
    return app
if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    web.run_app(make_app(),port=int(os.getenv('PORT','7654')))
