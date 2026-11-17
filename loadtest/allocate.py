"""Reserva N partidas por la API Kubernetes y guarda dos plazas por partida."""
import argparse,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--matches',type=int,default=500)
p.add_argument('--output',default='endpoints.json')
p.add_argument('--ready-timeout',type=float,default=180)
a=p.parse_args()
endpoints=[]
for i in range(a.matches):
    request={'apiVersion':'allocation.agones.dev/v1','kind':'GameServerAllocation','metadata':{'namespace':'default'},
             'spec':{'selectors':[{'matchLabels':{'agones.dev/fleet':'bloques-fleet'}}]}}
    deadline=time.monotonic()+a.ready_timeout
    while True:
        r=subprocess.run(['kubectl','create','-f','-','-o','json'],input=json.dumps(request),text=True,check=True,stdout=subprocess.PIPE,timeout=30)
        status=json.loads(r.stdout)['status']
        if status['state']=='Allocated':
            break
        if status['state']!='UnAllocated' or time.monotonic()>=deadline:
            raise RuntimeError(f'Partida {i+1}: {status["state"]}. Se guardaron {len(endpoints)} asignaciones.')
        time.sleep(2)
    port=next(x['port'] for x in status['ports'] if x['name']=='game')
    endpoints.append(f"ws://{status['address']}:{port}/ws")
    destination=Path(a.output)
    temporary=destination.with_suffix(destination.suffix+'.tmp')
    temporary.write_text(json.dumps(endpoints,indent=2),encoding='utf-8')
    temporary.replace(destination)
print(f'{len(endpoints)} partidas reservadas. Destruir/resetear la flota tras cada escenario.')
