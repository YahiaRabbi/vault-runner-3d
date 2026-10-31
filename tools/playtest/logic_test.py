"""
Automated gameplay tests for Vault Runner 3D.

Runs the real game module headless (no window is opened) and checks maze
reachability, keycard/gate logic, pickups, frame-rate independent acid damage,
shooting, the boss fight, game over/restart, wall collision, and a 3-minute
random-play soak test on every stage.

    python tools/playtest/logic_test.py
"""
import sys, importlib, random, math
from collections import deque
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
g = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else "vault_runner")
random.seed(1)
dt = 1 / 60
results = []

def check(name, ok, info=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + ("  -> " + str(info) if info else ""))

def step(n=1):
    for _ in range(n):
        g.clock += dt
        g.update_game(dt)

def put(col, row):
    g.hero["x"], g.hero["y"] = g.tile_center(col, row)

def clear_enemies():
    g.guards.clear(); g.hunters.clear(); g.aliens.clear(); g.foe_shots.clear()

# 1. every free tile reachable from start, in every stage
for s in (1, 2, 3, 4):
    g.build_stage(s)
    m = g.grid
    start = [(c, r) for r in range(g.grid_h) for c in range(g.grid_w) if m[r][c] == "S"][0]
    seen = {start}; q = deque([start])
    while q:
        c, r = q.popleft()
        for dc, dr in ((1,0),(-1,0),(0,1),(0,-1)):
            n = (c+dc, r+dr)
            if n not in seen and not g.is_wall_tile(*n):
                seen.add(n); q.append(n)
    unreachable = [t for t in g.free_tiles if t not in seen]
    check(f"stage {s}: all floor reachable", not unreachable, unreachable)
    if g.STAGES[s]["gate"]:
        gc, gr = g.STAGES[s]["gate"]
        check(f"stage {s}: gate tile is 'G'", m[gr][gc] == "G", m[gr][gc])
    # starting direction: is the tile in front of the player a wall?
    yaw = g.hero["yaw"]
    front = g.tile_at(g.hero["x"] + 120 * math.cos(yaw), g.hero["y"] + 120 * math.sin(yaw))
    check(f"stage {s}: player starts facing an open tile", not g.is_wall_tile(*front))

# 2. locked gate, keycard, stage advance
g.start_new_game(); clear_enemies()
put(*g.gate_tile); step()
check("gate locked without key", g.stage_no == 1 and "locked" in g.banner, g.banner)
put(*g.key_tile); step()
check("keycard pickup", g.hero["has_key"])
put(*g.gate_tile); step()
check("gate -> stage 2 with +150 bonus", g.stage_no == 2 and g.score == 150, (g.stage_no, g.score))
check("has_key reset on new stage", not g.hero["has_key"])

# 3. pickups
g.start_new_game(); clear_enemies()
g.hero["hp"] = 50; mk = g.medkits[0]
g.hero["x"], g.hero["y"] = mk["x"], mk["y"]; step()
check("medkit heals 25", g.hero["hp"] == 75, g.hero["hp"])
g.hero["hp"] = 100; mk = g.medkits[0]
g.hero["x"], g.hero["y"] = mk["x"], mk["y"]; step()
check("medkit NOT wasted at full health", mk in g.medkits, "consumed at 100/100")
a0 = g.hero["ammo"]; ab = g.ammo_boxes[0]
g.hero["x"], g.hero["y"] = ab["x"], ab["y"]; step()
check("ammo box +18", g.hero["ammo"] == a0 + 18, g.hero["ammo"])

# 4. acid ~22 hp/sec, frame-rate independent
for fps in (30, 144):
    g.build_stage(4, keep_items=False); clear_enemies(); g.warden["shot_cd"] = 1e9; g.warden["slam_cd"] = 1e9
    acid = [(c, r) for (c, r) in g.free_tiles if g.is_acid_tile(c, r)][0]
    put(*acid); g.hero["hp"] = 100.0
    for _ in range(fps):
        g.update_game(1 / fps)
    check(f"acid burn at {fps} fps ~22/s", abs((100 - g.hero["hp"]) - 22) < 0.5, round(100 - g.hero["hp"], 2))

# 5. shooting + ammo
g.start_new_game(); clear_enemies()
a0 = g.hero["ammo"]; g.shoot(); g.shoot()
check("shot cooldown blocks spam", g.hero["ammo"] == a0 - 1, g.hero["ammo"])
g.hero["ammo"] = 0; step(30); g.shoot()
check("empty ammo message", "No ammo" in g.banner)

# 6. guard killed by bullets
g.start_new_game(); clear_enemies(); g.aliens.clear()
put(1, 1); gx, gy = g.tile_center(3, 1)
g.guards.append({"x": gx, "y": gy, "hp": 70, "max_hp": 70, "yaw": 0, "shot_cd": 99, "turn_dir": 1, "alive": True})
g.hero["yaw"] = 0
for _ in range(3):
    g.shoot(); step(20)
check("guard dies after 3 shots (+70)", not g.guards[0]["alive"] and g.score == 70, (g.guards[0]["hp"], g.score))

# 7. boss phases + victory
g.build_stage(4, keep_items=False); clear_enemies()
w = g.warden; w["hp"] = 200; step()
check("warden phase 2 below 55%", w["phase"] == 2)
g.hero["x"], g.hero["y"] = w["x"] - 400, w["y"]; g.hero["yaw"] = 0; g.cheat_mode = True
for _ in range(10):
    g.shoot(); step(30)
g.cheat_mode = False
check("killing warden -> victory", g.victory, (w["hp"], g.victory))

# 8. game over + restart
g.start_new_game(); clear_enemies()
g.hurt_hero(200)
check("game over at 0 hp", g.game_over)
g.keyboardListener(b'r', 0, 0)
check("R restarts at stage 1 full hp", not g.game_over and g.stage_no == 1 and g.hero["hp"] == 100)
g.pressed_keys.clear()

# 9. collision: walking into a wall never puts body inside a wall
g.start_new_game(); clear_enemies()
g.pressed_keys.add(b'w'); bad = 0
for i in range(600):
    g.hero["yaw"] += 0.03
    step()
    if not g.can_stand(g.hero["x"], g.hero["y"]): bad += 1
g.pressed_keys.clear()
check("never inside a wall over 600 frames", bad == 0, bad)

# 10. hunter respawn only stage 2/3
g.build_stage(2); n = len(g.hunters); random.seed(0); resp = 0
for h in list(g.hunters):
    before = len(g.hunters); g.kill_enemy(h, "hunter"); resp += len(g.hunters) - before
print(f"   stage 2: {n} hunters killed, {resp} respawned")

# 11. full-session soak: random play for 3 minutes per stage, look for crashes
for s in (1, 2, 3, 4):
    g.build_stage(s, keep_items=False); g.cheat_mode = True
    keys = [b'w', b'a', b's', b'd']
    try:
        for i in range(60 * 180):
            if i % 40 == 0:
                g.pressed_keys.clear(); g.pressed_keys.add(random.choice(keys))
                g.hero["yaw"] += random.uniform(-1, 1)
            if i % 7 == 0: g.shoot()
            step()
            if g.stage_no != s or g.victory: break
        check(f"stage {s}: 3 min soak, no crash", True, f"particles={len(g.particles)} foe_shots={len(g.foe_shots)}")
    except Exception as e:
        check(f"stage {s}: soak", False, repr(e))
    g.cheat_mode = False; g.pressed_keys.clear()

passed = sum(ok for _, ok in results)
print("\n%d/%d passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
