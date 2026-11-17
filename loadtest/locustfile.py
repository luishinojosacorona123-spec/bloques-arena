"""Un proceso Locust por archivo de endpoints; 2 plazas humanas por partida.
Para carga distribuida, particionar endpoints por worker, no compartir el archivo.
"""
import json,os,time,random,itertools
from pathlib import Path
import websocket
from locust import User, HttpUser, task, between, events, LoadTestShape
from gevent.lock import Semaphore
addresses=json.loads(Path(os.getenv('ENDPOINTS','endpoints.json')).read_text()) if Path(os.getenv('ENDPOINTS','endpoints.json')).exists() else ['ws://127.0.0.1:7654/ws']
counter=itertools.count(); lock=Semaphore()

class Player(User):
    wait_time=between(.15,.3)
    def on_start(self):
        with lock: i=next(counter)
        if i>=2*len(addresses): raise RuntimeError('Faltan plazas: generar más endpoints')
        self.ws=websocket.create_connection(addresses[i//2]+'?name=load',timeout=5)
    @task
    def play(self):
        begin=time.perf_counter(); token=time.time_ns(); error=None
        try:
            self.ws.send(json.dumps({'action':random.choice(['left','right','rotate','down'])}))
            self.ws.send(json.dumps({'ping':token}))
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if json.loads(self.ws.recv()).get('pong')==token: break
            else: raise TimeoutError('Sin pong')
        except Exception as e: error=e
        events.request.fire(request_type='WS',name='player_rtt',response_time=(time.perf_counter()-begin)*1000,response_length=0,exception=error)
    def on_stop(self):
        if hasattr(self,'ws'): self.ws.close()

class Spectator(User):
    wait_time=between(0,0)
    def on_start(self): self.ws=websocket.create_connection(addresses[0]+'?watch=1',timeout=5)
    @task
    def receive(self):
        t=time.perf_counter(); error=None; msg=''
        try: msg=self.ws.recv()
        except Exception as e: error=e
        events.request.fire(request_type='WS',name='spectator_state',response_time=(time.perf_counter()-t)*1000,response_length=len(msg),exception=error)
    def on_stop(self):
        if hasattr(self,'ws'): self.ws.close()

class Scores(HttpUser):
    wait_time=between(.5,1)
    # Cloud Run es privado. TOKEN debe ser un ID token con audiencia igual a la URL.
    @task(4)
    def read(self): self.client.get('/top',headers={'Authorization':'Bearer '+os.getenv('TOKEN','')})
    @task(1)
    def write(self):
        self.client.post('/score',json={'match':str(time.time_ns()),'player':'load','score':random.randrange(10000)},headers={'Authorization':'Bearer '+os.getenv('TOKEN','')})

class LaunchShape(LoadTestShape):
    # Activar explícitamente con SCENARIO=ramp|spike|spectators|scores.
    def tick(self):
        scenario=os.getenv('SCENARIO','ramp'); t=self.get_run_time()
        if scenario=='spike': stages=[(60,100,10),(120,1000,50),(420,1000,10)]
        elif scenario in ('spectators','scores'): stages=[(120,100,10),(420,500,10)]
        else: stages=[(120,100,5),(240,300,5),(360,600,5),(600,1000,5)]
        cls={'spectators':Spectator,'scores':Scores}.get(scenario,Player)
        for until,users,rate in stages:
            if t<until:return users,rate,[cls]
        return None
