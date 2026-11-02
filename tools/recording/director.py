"""
Scripted demo recorder for Vault Runner 3D.

Plays the REAL game (vault_runner.py) with an autopilot (BFS pathfinding,
smooth turning, aim-and-fire) and records every frame at a fixed 30 fps,
so the footage is smooth even on a software renderer. Clips go to build/raw/.

    python tools/recording/director.py            # all clips
    python tools/recording/director.py boss hud   # selected clips

Needs ffmpeg on PATH. On a headless Linux box, run under a virtual display:
    xvfb-run -a -s "-screen 0 1280x1024x24" python tools/recording/director.py
"""
import sys, os, math, random, subprocess
from collections import deque
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
import vault_runner as g
from OpenGL.GL import *
from OpenGL.GLUT import *

W, H = g.WIN_W, g.WIN_H
DT = 1 / 30
OUT = os.path.join(ROOT, "build", "raw")
os.makedirs(OUT, exist_ok=True)
g.glutSwapBuffers = lambda: None          # we read the back buffer ourselves

# demo safety net: the player never drops below 28 HP so a take never ends early
_orig_hurt = g.hurt_hero
def demo_hurt(amount, reason=""):
    amount = min(amount, max(0.0, g.hero["hp"] - 28))
    _orig_hurt(amount, reason)
g.hurt_hero = demo_hurt


class Rec:
    def start(self, name):
        self.name = name
        self.n = 0
        self.proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", "30", "-i", "-", "-vf", "vflip",
             "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
             f"{OUT}/{name}.mp4"], stdin=subprocess.PIPE)

    def frame(self, update=True):
        g.clock += DT
        if update:
            g.update_game(DT)
        g.showScreen()
        glFinish()
        glReadBuffer(GL_BACK)
        data = glReadPixels(0, 0, W, H, GL_RGB, GL_UNSIGNED_BYTE)
        self.proc.stdin.write(data if isinstance(data, bytes) else data.tobytes())
        self.n += 1

    def hold(self, frames, update=True):
        for _ in range(frames):
            self.frame(update)

    def stop(self):
        self.proc.stdin.close()
        self.proc.wait()
        print(f"  {self.name}: {self.n} frames ({self.n / 30:.1f}s)")


R = Rec()

# ------------------------------------------------------------ autopilot
def norm(a):
    return (a + math.pi) % math.tau - math.pi

def turn_towards(target, rate=3.2):
    d = norm(target - g.hero["yaw"])
    s = rate * DT
    g.hero["yaw"] += max(-s, min(s, d))
    return abs(norm(target - g.hero["yaw"]))

def bfs(start, goal):
    prev = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        if c == goal:
            break
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + dc, c[1] + dr)
            if n not in prev and not g.is_wall_tile(*n):
                prev[n] = c
                q.append(n)
    path, c = [], goal
    while c is not None:
        path.append(c)
        c = prev.get(c)
    return path[::-1]

def walk_to(tile, budget=10_000, during=None, final_dist=12, keys=(b'w',)):
    stage = g.stage_no
    path = bfs(g.tile_at(g.hero["x"], g.hero["y"]), tuple(tile))
    start_n = R.n
    for i, wp in enumerate(path[1:]):
        tx, ty = g.tile_center(*wp)
        last = i == len(path) - 2
        while R.n - start_n < budget:
            d = math.hypot(tx - g.hero["x"], ty - g.hero["y"])
            if d < (final_dist if last else 34):
                break
            err = turn_towards(math.atan2(ty - g.hero["y"], tx - g.hero["x"]))
            g.pressed_keys.clear()
            if err < 0.5:
                g.pressed_keys.update(keys)
            if during:
                during()
            R.frame()
            if g.stage_no != stage:
                g.pressed_keys.clear()
                return
    g.pressed_keys.clear()

def face(yaw, max_frames=60):
    for _ in range(max_frames):
        if turn_towards(yaw) < 0.01:
            break
        R.frame()

def fight(t, max_frames=240, strafe=None, pace=None):
    for i in range(max_frames):
        if not t["alive"]:
            break
        err = turn_towards(g.angle_to(g.hero["x"], g.hero["y"], t["x"], t["y"]), 3.6)
        g.pressed_keys.clear()
        if strafe:
            k = strafe(i)
            if k:
                g.pressed_keys.add(k)
        ok_pace = pace(i) if pace else True
        if ok_pace and err < 0.05 and g.can_see(g.hero["x"], g.hero["y"], t["x"], t["y"]):
            g.shoot()
        R.frame()
    g.pressed_keys.clear()

def put(col, row, yaw=0.0):
    g.hero["x"], g.hero["y"] = g.tile_center(col, row)
    g.hero["yaw"] = yaw

def clear_world(items=False):
    g.guards.clear(); g.hunters.clear(); g.aliens.clear()
    g.foe_shots.clear(); g.my_shots.clear(); g.particles.clear()
    if items:
        g.medkits.clear(); g.ammo_boxes.clear()

def add_guard(c, r, yaw=0.0):
    x, y = g.tile_center(c, r)
    g.guards.append({"x": x, "y": y, "hp": 70, "max_hp": 70, "yaw": yaw,
                     "shot_cd": 0.6, "turn_dir": 1, "alive": True})
    return g.guards[-1]

def add_alien(c, r, yaw=0.0):
    x, y = g.tile_center(c, r)
    g.aliens.append({"x": x, "y": y, "hp": 60, "max_hp": 60, "yaw": yaw,
                     "shot_cd": 0.8, "turn_dir": -1, "alive": True})
    return g.aliens[-1]

def add_hunter(c, r):
    g.hunters.append(g.new_hunter(*g.tile_center(c, r)))
    return g.hunters[-1]

def add_item(kind, c, r):
    x, y = g.tile_center(c, r)
    if kind == "med":
        g.medkits.append({"x": x, "y": y, "heal": 25, "spin": 0.0})
    else:
        g.ammo_boxes.append({"x": x, "y": y, "bullets": 18, "spin": 0.0})

def fresh(stage, seed):
    random.seed(seed)
    g.score = 0; g.game_over = False; g.victory = False
    g.cheat_mode = False; g.third_person = False
    g.pressed_keys.clear()
    g.build_stage(stage, keep_items=False)

# ------------------------------------------------------------ clips
def clip_minimap():
    fresh(1, 11); clear_world()
    g.key_tile = (7, 3)
    R.start("01_minimap")
    R.hold(20)
    walk_to((7, 3))                          # keycard: yellow dot disappears
    R.hold(10)
    walk_to((13, 9), budget=330)             # head for the gate
    R.hold(10)
    R.stop()

def clip_hud():
    fresh(1, 12); clear_world(items=True)
    g.banner_timer = 0
    put(1, 9, 0.0)
    gd = add_guard(8, 9, math.pi)
    R.start("02_hud")
    R.hold(25)
    walk_to((3, 9))                          # step into the guard's sight
    R.hold(55)                               # get hit: health text + bar + shake
    fight(gd, 240, pace=lambda i: i > 10)    # ammo counts down, score goes up
    R.hold(40)
    R.stop()

def clip_pickups():
    fresh(1, 13); clear_world(items=True)
    put(1, 9, 0.0)
    g.hero["hp"] = 45.0; g.hero["ammo"] = 6
    add_item("med", 4, 9); add_item("ammo", 7, 9); add_item("med", 10, 9)
    g.banner_timer = 0
    R.start("03a_pickups")
    R.hold(20)
    walk_to((11, 9))
    R.hold(25)
    R.stop()

    fresh(4, 14); clear_world(items=True)
    g.warden = None
    g.third_person = True
    put(1, 3, 0.0); g.banner_timer = 0
    R.start("03b_acid")
    R.hold(15)
    walk_to((3, 3))
    walk_to((4, 3), final_dist=40)
    walk_to((5, 4), final_dist=40)           # standing in acid -> health drains
    for _ in range(45):
        turn_towards(0.0)
        R.frame()
    walk_to((8, 4))
    R.hold(25)
    R.stop()

def clip_maze():
    fresh(3, 15); clear_world()
    g.third_person = True
    put(1, 1, -0.38)                         # pushed diagonally into the wall
    g.banner_timer = 0
    R.start("04_maze_collision")
    R.hold(10)
    g.pressed_keys.add(b'w')
    R.hold(95)                               # slides along the wall, never through it
    g.pressed_keys.clear()
    walk_to((11, 2))
    walk_to((11, 7), budget=140)
    R.hold(10)
    R.stop()

def clip_camera():
    fresh(2, 16); clear_world()
    g.banner_timer = 0
    R.start("05_dual_camera")
    R.hold(10)
    marks = [70, 140, 210, 280]
    def toggle():
        if R.n in marks:
            g.third_person = not g.third_person
    walk_to((7, 5), during=toggle, budget=320)
    R.hold(15)
    R.stop()

def clip_gate():
    fresh(1, 17); clear_world()
    g.third_person = True
    g.key_tile = (4, 9)
    put(8, 9, 0.0); g.banner_timer = 0
    R.start("06_keycard_gate")
    R.hold(15)
    walk_to((13, 9), final_dist=55)          # red ring, "Gate is locked"
    R.hold(40)
    walk_to((4, 9))                          # keycard found, ring turns cyan
    R.hold(20)
    walk_to((13, 9))                         # through the gate -> Stage 2
    R.hold(70)
    R.stop()

def clip_guards():
    fresh(1, 18); clear_world()
    put(1, 9, 0.0); g.banner_timer = 0
    gd = add_guard(7, 9, 1.0)
    al = add_alien(11, 9, -1.0)
    R.start("07_guard_alien_ai")
    R.hold(45)                               # guard head scanning, out of range
    walk_to((2, 9))                          # in range: it snaps to us and fires
    R.hold(30)
    fight(gd, 200)
    R.hold(15)
    walk_to((5, 9))
    R.hold(20)
    fight(al, 200)
    R.hold(35)
    R.stop()

def clip_hunters():
    fresh(2, 19); clear_world(items=True)
    put(14, 5, math.pi); g.banner_timer = 0
    add_hunter(10, 5); add_hunter(8, 5); add_hunter(7, 7)
    R.start("08_hunter_ai")
    g.third_person = True
    R.hold(50)                               # one spots us and charges, others roam
    g.third_person = False
    kills = 0
    for _ in range(40):
        seen = [h for h in g.hunters if h["alive"] and
                g.can_see(g.hero["x"], g.hero["y"], h["x"], h["y"])]
        if seen:
            tgt = min(seen, key=lambda h: g.dist2(h["x"], h["y"], g.hero["x"], g.hero["y"]))
            fight(tgt, 120)
            kills += not tgt["alive"]
            R.hold(8)
        else:                                # nobody in sight: push west
            col, row = g.tile_at(g.hero["x"], g.hero["y"])
            walk_to((max(7, col - 1), 5), budget=25)
        if kills >= 3 or R.n > 750:
            break
    R.hold(40)
    R.stop()

def clip_boss():
    fresh(4, 20); clear_world()
    g.third_person = True
    put(9, 2, 0.0)
    w = g.warden
    g.hero["yaw"] = g.angle_to(g.hero["x"], g.hero["y"], w["x"], w["y"])
    R.start("09_boss_fight")
    R.hold(75)                               # phase 1 fan of 8 bullets
    g.third_person = False
    dodge = lambda i: (b'a' if (i // 40) % 2 == 0 else b'd')
    fight(w, 210, strafe=dodge, pace=lambda i: (i // 25) % 2 == 0)
    g.third_person = True
    fight(w, 90, strafe=dodge, pace=lambda i: False)       # watch phase 2 (12 bullets)
    g.third_person = False
    fight(w, 400, strafe=dodge, pace=lambda i: (i // 20) % 3 != 2)
    R.hold(110)                              # MISSION COMPLETE
    R.stop()

CLIPS = {"minimap": clip_minimap, "hud": clip_hud, "pickups": clip_pickups,
         "maze": clip_maze, "camera": clip_camera, "gate": clip_gate,
         "guards": clip_guards, "hunters": clip_hunters, "boss": clip_boss}

if __name__ == "__main__":
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(W, H)
    glutCreateWindow(b"Vault Runner 3D")
    g.init_gl()
    for name in (sys.argv[1:] or CLIPS):
        CLIPS[name]()
