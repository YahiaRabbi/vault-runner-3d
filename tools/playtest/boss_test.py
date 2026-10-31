"""
Bug reproduction: can the Warden's bullet fan actually hit the player?

Stands the player still in front of the boss for 10 seconds (ground slam
disabled, so only the bullet fan can do damage) and checks that HP dropped.

    python tools/playtest/boss_test.py
"""
import os, sys, random, importlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MOD = sys.argv[1] if len(sys.argv) > 1 else "vault_runner"
g = importlib.import_module(MOD)
random.seed(3)

g.build_stage(4, keep_items=False)
g.aliens.clear()
w = g.warden
w["slam_cd"] = 1e9                                # only the bullet fan
g.hero["x"], g.hero["y"] = w["x"] - 400, w["y"]   # stand still in front of the boss
for _ in range(60 * 10):
    g.update_game(1 / 60)

hp = g.hero["hp"]
ok = hp < 100
print(f"{'PASS' if ok else 'FAIL'}  HP after 10 s in the bullet fan: {hp:.0f}"
      + ("" if ok else "  (boss bullets never hit the player)"))
sys.exit(0 if ok else 1)
