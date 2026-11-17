from game import Game, rotate, SHAPES, bot_step

def test_four_rotations_preserve_shape():
    for s in SHAPES:
        r=s
        for _ in range(4): r=rotate(r)
        assert sorted(r)==sorted(s)

def test_wall_blocks_movement():
    g=Game()
    for _ in range(20): g.action('left')
    assert g.x==0
    assert g.valid(g.shape,g.x,g.y)

def test_clear_line_and_score():
    g=Game(); g.kind=0; g.shape=SHAPES[0]; g.x=3; g.y=0
    g.board[-1]=[1,1,1,0,0,0,0,1,1,1]
    assert g.action('drop')==1
    assert g.lines==1 and g.score==100
    assert not any(g.board[-1])

def test_same_seed_same_bag():
    a,b=Game(12),Game(12)
    assert [a.draw() for _ in range(50)]==[b.draw() for _ in range(50)]

def test_top_out():
    g=Game(); g.board=[[1]*10 for _ in range(20)]; g.spawn()
    assert g.over

def test_garbage_has_hole():
    g=Game(); g.garbage(2)
    assert g.board[-1].count(0)==1 and g.board[-2].count(8)==9

def test_bot_plays_50_pieces():
    g=Game(42)
    for _ in range(50): bot_step(g)
    assert not g.over and g.lines>0
