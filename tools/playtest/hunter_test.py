"""
Bug reproduction: can a hunter be shot once it reaches the player?

Lets a hunter charge all the way in (player kept alive), then aims straight
at it and fires for 6 seconds. The hunter should die.

    python tools/playtest/hunter_test.py
"""
import os, sys, math, random, importlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MOD = sys.argv[1] if len(sys.argv) > 1 else "vault_runner"
g = importlib.import_module(MOD)
random.seed(5)

g.build_stage(2, keep_items=False)
g.hunters.clear(); g.guards.clear(); g.aliens.clear()
g.hero["x"], g.hero["y"] = g.tile_center(14, 5)
g.hero["yaw"] = math.pi
g.hero["hp"] = 1e6                                # keep the player alive for the test
h = g.new_hunter(*g.tile_center(11, 5))
g.hunters.append(h)

for _ in range(400):                              # let it charge all the way in
    g.update_game(1 / 60)
d = math.dist((h["x"], h["y"]), (g.hero["x"], g.hero["y"]))

for _ in range(60 * 6):                           # aim at it and fire for 6 s
    g.hero["yaw"] = g.angle_to(g.hero["x"], g.hero["y"], h["x"], h["y"])
    g.shoot()
    g.update_game(1 / 60)

ok = not h["alive"]
print(f"{'PASS' if ok else 'FAIL'}  hunter stopped at distance {d:.0f}; "
      f"after 6 s of point-blank fire it is {'dead' if ok else 'still alive (unkillable)'}")
sys.exit(0 if ok else 1)
