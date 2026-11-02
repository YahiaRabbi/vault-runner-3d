"""
Post-production for the recorded clips in build/raw/:
caption bands, an enlarged minimap inset, title cards, the full showcase,
the LinkedIn cut, and README GIFs. Results go to build/out/.

    python tools/recording/finish.py

Needs ffmpeg (with drawtext) and the Inter font family installed.
"""
import os, subprocess

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "build"))
RAW, TXT, CAP, OUT = f"{BASE}/raw", f"{BASE}/txt", f"{BASE}/captioned", f"{BASE}/out"
for d in (TXT, CAP, OUT, f"{CAP}/li"):
    os.makedirs(d, exist_ok=True)

F = "/usr/share/fonts/opentype/inter/"
BOLD, SEMI, MED, REG = F + "Inter-Bold.otf", F + "Inter-SemiBold.otf", F + "Inter-Medium.otf", F + "Inter-Regular.otf"
DISP = F + "InterDisplay-ExtraBold.otf"
BG = "0x0b0f14"
MINE, TEAM = "0x22d3ee", "0xf59e0b"      # cyan = Yahia's part, amber = team

def run(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args, check=True)

def txt(name, s):
    p = f"{TXT}/{name}.txt"
    open(p, "w").write(s)
    return p

def dt(name, s, font, size, color, x, y):
    return (f"drawtext=fontfile={font}:textfile={txt(name, s)}:fontsize={size}"
            f":fontcolor={color}:x={x}:y={y}:expansion=none")

FEATURES = [
    # file(s)                         title                                   subtitle                                                              mine
    (["01_minimap"],                  "Real-Time Tactical Minimap",            "World -> grid -> screen mapping  ·  smooth position + heading line", True),
    (["02_hud"],                      "Screen-Space HUD",                      "Orthographic 2D overlay  ·  health bar, ammo, score, alerts, crosshair", True),
    (["03a_pickups", "03b_acid"],     "Pickups & Acid Hazard",                 "Squared-distance pickups  ·  frame-rate independent acid (22 HP/s)", True),
    (["04_maze_collision"],           "Maze Collision & Wall Sliding",         "9-point body test  ·  X and Y resolved separately to slide along walls", False),
    (["05_dual_camera"],              "Dual Camera",                           "First person <-> third person  ·  camera lifts when a wall is behind", False),
    (["06_keycard_gate"],             "Keycard, Locked Gate & Stages",         "Find the keycard to open the gate  ·  4-stage progression", False),
    (["07_guard_alien_ai"],           "Guard & Alien AI",                      "Scanning turrets  ·  line-of-sight raycast  ·  timed return fire", False),
    (["08_hunter_ai"],                "Hunter AI",                             "Chase on sight, roam otherwise  ·  35% respawn on stages 2-3", False),
    (["09_boss_fight"],               "Two-Phase Boss Fight",                  "Bullet fans  ·  ground slam  ·  phase 2 below 55% HP", False),
]

def caption(src, dst, idx, title, sub, mine, tag=None, trim=None, zoom=False):
    accent = MINE if mine else TEAM
    tag = tag or f"FEATURE {idx:02d}"
    key = os.path.basename(dst)[:-4]
    chain = []
    pre = ""
    if zoom:   # enlarge the minimap in place so it reads on a phone
        pre = ("[0:v]split[a][b];[b]crop=171:171:819:10,scale=342:342:flags=neighbor[z];"
               "[a][z]overlay=650:8,drawbox=x=650:y=8:w=342:h=342:color=white@0.85:t=2[v0];[v0]")
    else:
        pre = "[0:v]"
    chain += [f"pad=1000:900:0:0:color={BG}",
              f"drawbox=x=0:y=800:w=1000:h=3:color={accent}:t=fill",
              dt(key + "_tag", tag, SEMI, 15, accent, 28, 818),
              dt(key + "_t", title, BOLD, 28, "white", 28, 840),
              dt(key + "_s", sub, REG, 17, "0x9fb3c8", 28, 876),
              dt(key + "_r1", "CSE423  ·  COMPUTER GRAPHICS", MED, 13, "0x6b7f95", "w-tw-28", 820),
              dt(key + "_r2", "Vault Runner 3D", BOLD, 17, "0xc7d2de", "w-tw-28", 840)]
    dur = trim or float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]))
    chain += [f"fade=t=in:st=0:d=0.3", f"fade=t=out:st={dur - 0.3:.2f}:d=0.3"]
    args = ["-i", src]
    if trim:
        args = ["-t", str(trim)] + args
    run(args + ["-filter_complex", pre + ",".join(chain),
                "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-r", "30", dst])

def card(dst, lines, dur, bg_src, bg_t):
    """Title card over a blurred, darkened gameplay frame."""
    key = os.path.basename(dst)[:-4]
    draws = []
    for i, (s, font, size, color, y) in enumerate(lines):
        draws.append(dt(f"{key}_{i}", s, font, size, color, "(w-tw)/2", y))
    fc = (f"[0:v]scale=1000:900:force_original_aspect_ratio=increase,crop=1000:900,"
          f"boxblur=18:2,eq=brightness=-0.32:saturation=0.8,"
          f"drawbox=x=(iw-120)/2:y=520:w=120:h=3:color={MINE}:t=fill,"
          + ",".join(draws) +
          f",fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.4}:d=0.4")
    run(["-ss", str(bg_t), "-i", bg_src, "-filter_complex", fc, "-t", str(dur), "-r", "30",
         "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", dst])

def concat(parts, dst):
    lst = f"{TXT}/{os.path.basename(dst)}.list"
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    run(["-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-crf", "20", "-preset", "slow",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst])

# ---------------- per-feature captioned clips (GitHub)
feature_files = []
for i, (files, title, sub, mine) in enumerate(FEATURES, 1):
    parts = []
    for f in files:
        dst = f"{CAP}/{f}.mp4"
        caption(f"{RAW}/{f}.mp4", dst, i, title, sub, mine, zoom=(f == "01_minimap"))
        parts.append(dst)
    if len(parts) > 1:
        merged = f"{CAP}/{files[0][:2]}_merged.mp4"
        concat(parts, merged)
        parts = [merged]
    feature_files.append(parts[0])
    # standalone per-feature video for the repo
    slug = files[0][:2] + "_" + title.lower().replace("&", "and").replace(",", "").replace(" ", "_").replace("-", "_")
    run(["-i", parts[0], "-c", "copy", "-movflags", "+faststart", f"{OUT}/{slug}.mp4"])

intro_lines = [("VAULT RUNNER 3D", DISP, 76, "white", 380),
               ("A 3D first-person maze shooter built from scratch in Python + OpenGL", MED, 21, "0xc7d2de", 478),
               ("CSE423  ·  COMPUTER GRAPHICS  ·  FINAL PROJECT", SEMI, 16, MINE, 552)]
card(f"{CAP}/00_intro.mp4", intro_lines, 4.0, f"{RAW}/09_boss_fight.mp4", 4.5)
outro_lines = [("9 features  ·  4 stages  ·  0 game engines", BOLD, 40, "white", 410),
               ("Python  ·  PyOpenGL  ·  GLUT  ·  raw matrix transforms", MED, 20, "0xc7d2de", 470),
               ("CSE423  ·  COMPUTER GRAPHICS", SEMI, 16, MINE, 552)]
card(f"{CAP}/99_outro.mp4", outro_lines, 3.5, f"{RAW}/06_keycard_gate.mp4", 2.0)

concat([f"{CAP}/00_intro.mp4"] + feature_files + [f"{CAP}/99_outro.mp4"],
       f"{OUT}/vault_runner_3d_full_showcase.mp4")

# ---------------- LinkedIn cut: my three features + boss highlight, ~45 s
li = []
caption(f"{RAW}/01_minimap.mp4", f"{CAP}/li/a.mp4", 1, FEATURES[0][1], FEATURES[0][2], True, tag="MY PART  ·  01", trim=11, zoom=True)
caption(f"{RAW}/02_hud.mp4", f"{CAP}/li/b.mp4", 2, FEATURES[1][1], FEATURES[1][2], True, tag="MY PART  ·  02")
caption(f"{RAW}/03a_pickups.mp4", f"{CAP}/li/c.mp4", 3, FEATURES[2][1], FEATURES[2][2], True, tag="MY PART  ·  03")
caption(f"{RAW}/03b_acid.mp4", f"{CAP}/li/d.mp4", 3, FEATURES[2][1], FEATURES[2][2], True, tag="MY PART  ·  03")
caption(f"{RAW}/09_boss_fight.mp4", f"{CAP}/li/e.mp4", 9, FEATURES[8][1], FEATURES[8][2], False, tag="TEAM  ·  BOSS FIGHT")
li_intro = [("VAULT RUNNER 3D", DISP, 76, "white", 380),
            ("My part: minimap, HUD, pickups & acid hazard", MED, 22, "0xc7d2de", 478),
            ("CSE423  ·  COMPUTER GRAPHICS  ·  FINAL PROJECT", SEMI, 16, MINE, 552)]
card(f"{CAP}/li/0.mp4", li_intro, 3.0, f"{RAW}/09_boss_fight.mp4", 4.5)
concat([f"{CAP}/li/{p}.mp4" for p in ("0", "a", "b", "c", "d", "e")] + [f"{CAP}/99_outro.mp4"],
       f"{OUT}/vault_runner_3d_linkedin.mp4")

# ---------------- README GIFs (small, loop)
def gif(src, dst, start, dur, width=520):
    pal = f"{TXT}/pal.png"
    vf = f"fps=15,scale={width}:-1:flags=lanczos"
    run(["-ss", str(start), "-t", str(dur), "-i", src, "-vf", vf + ",palettegen=stats_mode=diff", pal])
    run(["-ss", str(start), "-t", str(dur), "-i", src, "-i", pal, "-lavfi",
         vf + "[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", dst])

os.makedirs(f"{OUT}/gifs", exist_ok=True)
gif(f"{CAP}/01_minimap.mp4", f"{OUT}/gifs/minimap.gif", 6, 5)
gif(f"{CAP}/02_hud.mp4", f"{OUT}/gifs/hud.gif", 1.5, 5)
gif(f"{CAP}/03b_acid.mp4", f"{OUT}/gifs/acid.gif", 1.5, 5)
gif(f"{CAP}/09_boss_fight.mp4", f"{OUT}/gifs/boss.gif", 3.5, 5)
print("done")
