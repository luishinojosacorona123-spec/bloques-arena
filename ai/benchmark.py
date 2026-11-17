import sys,time,statistics,json,platform,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from game import Game,choose,bot_step
g=Game(42); samples=[]
for i in range(100):
    t=time.perf_counter(); choose(g); samples.append((time.perf_counter()-t)*1000)
    bot_step(g)
    if g.over:g=Game(42+i)
mean=statistics.mean(samples); rate=1000/mean
result=dict(kind='medición local, bot heurístico; no PPO',python=platform.python_version(),platform=platform.platform(),samples=len(samples),mean_ms=mean,p95_ms=sorted(samples)[94],decisions_per_second=rate,vcpu_2000_bots_10hz_margin30=math.ceil(20000/rate*1.3))
print(json.dumps(result,indent=2,ensure_ascii=False))
