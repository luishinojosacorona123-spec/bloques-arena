"""Reglas autoritativas de un juego de bloques. Sin dependencias externas."""
import random
from copy import deepcopy

W, H = 10, 20
SHAPES = [((0,0),(1,0),(2,0),(3,0)), ((0,0),(1,0),(0,1),(1,1)),
          ((1,0),(0,1),(1,1),(2,1)), ((1,0),(2,0),(0,1),(1,1)),
          ((0,0),(1,0),(1,1),(2,1)), ((0,0),(0,1),(1,1),(2,1)),
          ((2,0),(0,1),(1,1),(2,1))]

def rotate(shape):
    cells = [(-y,x) for x,y in shape]
    mx, my = min(x for x,y in cells), min(y for x,y in cells)
    return tuple(sorted((x-mx,y-my) for x,y in cells))

class Game:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.board = [[0]*W for _ in range(H)]
        self.bag = []
        self.score = self.lines = 0
        self.over = False
        self.next = self.draw()
        self.spawn()

    def draw(self):
        if not self.bag:
            self.bag = list(range(7)); self.rng.shuffle(self.bag)
        return self.bag.pop()

    def spawn(self):
        self.kind = self.next
        self.next = self.draw()
        self.shape = SHAPES[self.kind]
        self.x, self.y = 3, 0
        if not self.valid(self.shape,self.x,self.y): self.over = True

    def valid(self,shape,x,y):
        return all(0 <= x+dx < W and 0 <= y+dy < H and not self.board[y+dy][x+dx]
                   for dx,dy in shape)

    def lock(self):
        for dx,dy in self.shape: self.board[self.y+dy][self.x+dx] = self.kind+1
        remaining = [row for row in self.board if not all(row)]
        n = H-len(remaining)
        self.board = [[0]*W for _ in range(n)] + remaining
        self.lines += n
        self.score += (0,100,300,500,800)[n] * (1+self.lines//10)
        self.spawn()
        return n

    def action(self, action):
        if self.over: return 0
        if action in ('left','right'):
            nx = self.x + (1 if action=='right' else -1)
            if self.valid(self.shape,nx,self.y): self.x=nx
        elif action=='rotate':
            shape=rotate(self.shape)
            for kick in (0,-1,1,-2,2):
                if self.valid(shape,self.x+kick,self.y):
                    self.x+=kick; self.shape=shape; break
        elif action=='down':
            if self.valid(self.shape,self.x,self.y+1): self.y+=1
            else: return self.lock()
        elif action=='drop':
            while self.valid(self.shape,self.x,self.y+1): self.y+=1
            return self.lock()
        return 0

    def garbage(self,n):
        for _ in range(n):
            if any(self.board[0]): self.over=True
            hole=self.rng.randrange(W)
            self.board.pop(0); self.board.append([0 if x==hole else 8 for x in range(W)])
        if not self.valid(self.shape,self.x,self.y): self.over=True

    def snapshot(self):
        return dict(board=self.board, shape=self.shape,x=self.x,y=self.y,
                    kind=self.kind+1,next=self.next+1,score=self.score,lines=self.lines,over=self.over)

def features(board):
    heights=[]; holes=0
    for x in range(W):
        col=[board[y][x] for y in range(H)]
        first=next((i for i,v in enumerate(col) if v),H)
        heights.append(H-first); holes+=sum(v==0 for v in col[first:])
    return sum(heights),holes,sum(abs(a-b) for a,b in zip(heights,heights[1:]))

def choose(game):
    """Bot heurístico: busca colocaciones, penaliza huecos y altura."""
    best=(-float('inf'),0,3); shape=game.shape
    for rotation in range(4):
        for x in range(W):
            if not game.valid(shape,x,0): continue
            y=0
            while game.valid(shape,x,y+1): y+=1
            board=deepcopy(game.board)
            for dx,dy in shape: board[y+dy][x+dx]=1
            cleared=sum(all(row) for row in board)
            board=[[0]*W for _ in range(cleared)]+[r for r in board if not all(r)]
            height,holes,bump=features(board)
            score=8*cleared-.5*height-3*holes-.3*bump
            if score>best[0]: best=(score,rotation,x)
        shape=rotate(shape)
    return best[1:]

def bot_step(game):
    rotation,x=choose(game)
    for _ in range(rotation): game.action('rotate')
    for _ in range(W):
        if game.x==x: break
        game.action('right' if game.x<x else 'left')
    return game.action('drop')
