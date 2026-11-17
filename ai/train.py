"""Práctica 3.1: PPO sobre colocación de piezas, no CartPole.
Dependencias opcionales grandes. No son necesarias para jugar.
"""
import argparse,sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from stable_baselines3 import PPO
from game import Game,rotate,features

class BlocksEnv(gym.Env):
    def __init__(self):
        self.action_space=spaces.Discrete(40)
        self.observation_space=spaces.Box(0,8,(202,),dtype=np.float32)
        self.game=Game()
    def obs(self):
        return np.array([v for row in self.game.board for v in row]+[self.game.kind,self.game.next],dtype=np.float32)
    def reset(self,seed=None,options=None):
        super().reset(seed=seed)
        self.game=Game(int(self.np_random.integers(2**31)))
        return self.obs(),{}
    def step(self,action):
        rotation,x=divmod(int(action),10); g=self.game; shape=g.shape
        for _ in range(rotation):shape=rotate(shape)
        if not g.valid(shape,x,0):return self.obs(),-2.,False,False,{}
        g.shape=shape; g.x=x; g.y=0
        n=g.action('drop'); height,holes,bump=features(g.board)
        reward=10*n-.02*height-.1*holes-.01*bump-(10 if g.over else 0)
        return self.obs(),float(reward),g.over,False,{}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--device',choices=['cpu','cuda'],default='cpu');p.add_argument('--steps',type=int,default=100000);a=p.parse_args()
    env=gym.wrappers.TimeLimit(BlocksEnv(),max_episode_steps=1000)
    model=PPO('MlpPolicy',env,device=a.device,verbose=0,seed=42)
    t=time.perf_counter();model.learn(total_timesteps=a.steps);elapsed=time.perf_counter()-t
    model.save('bot_bloques_'+a.device)
    model.policy.to('cpu');model.device='cpu';obs,_=env.reset(seed=43);times=[]
    for _ in range(1000):
        t=time.perf_counter();action,_=model.predict(obs,deterministic=True);times.append(time.perf_counter()-t)
        obs,_,done,truncated,_=env.step(action)
        if done or truncated:obs,_=env.reset()
    ms=float(np.mean(times)*1000); rate=1000/ms
    print(json.dumps(dict(device=a.device,training_s=elapsed,inference_mean_ms=ms,decisions_s=rate,vcpu_2000_10hz=int(np.ceil(20000/rate*1.3))),indent=2))
