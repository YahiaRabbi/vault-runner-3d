from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

#  SHARED SETUP   --   agreed by all three members
#  All the settings, the game variables, the 4 stage maps and the
#  few tiny helper functions that every part needs


# --- SETTINGS, GAME STATE AND STAGE DATA

WIN_W = 1000
WIN_H = 800

TILE = 120
WALL_HEIGHT = 115
BODY_R = 24

WALK_SPEED = 210.0
SIDE_SPEED = 185.0
SPIN_SPEED = 2.6

MY_SHOT_SPEED = 700.0
FOE_SHOT_SPEED = 250.0

MAX_HP = 100
START_AMMO = 40

ITEM_R = 30
GATE_R = 48
KEY_R = 24

MAP_SIZE = 155

fovY = 90
camera_pos = (0, 500, 500)


# 2. GLOBAL GAME STATE

pressed_keys = set()
prev_time = 0.0
clock = 0.0

stage_no = 1
score = 0
game_over = False
victory = False
third_person = False
shake_timer = 0.0
cheat_mode = False        # G toggles unlimited health + ammo

banner = ""
banner_timer = 0.0

# the player
hero = {
    "x": 0.0, "y": 0.0, "z": 42.0,
    "yaw": 0.0,           #left/right facing angle
    "pitch": 0.0,         # up/down looking angle
    "hp": float(MAX_HP),
    "ammo": START_AMMO,
    "has_key": False,
    "shot_cd": 0.0,       #cooldown so we cannot spam bullets
    "hurt_cd": 0.0,
}

# the current stage grid
grid = []
grid_w = 0
grid_h = 0
origin_x = 0.0
origin_y = 0.0
free_tiles = []
gate_tile = None
key_tile = (1, 1)

#every object
guards = []
hunters = []
aliens = []       # green alien shooters
warden = None     #the final boss
my_shots = []
foe_shots = []
medkits = []
ammo_boxes = []
particles = []



# 3. STAGE DATA
#     '#' = wall     '.' = floor     'S' = start
#     'G' = exit gate    'A' = acid pool (damages the player)

STAGES = {
    1: {
        "title": "Stage 1 : Guard Post",
        "guards": 7,
        "hunters": 0,
        "aliens": 2,
        "medkits": 4,
        "ammo": 4,
        "gate": (13, 9),
        "map": [
            "###############",
            "#S..#.....#...#",
            "###...###...#.#",
            "#.#...#...#.#.#",
            "#.##.##.#####.#",
            "#.....#.......#",
            "####..#.#.###.#",
            "#.....#.....#.#",
            "#.#########.#.#",
            "#............G#",
            "###############",
        ],
    },
    2: {
        "title": "Stage 2 : Hunter Halls",
        "guards": 0,
        "hunters": 8,
        "aliens": 3,
        "medkits": 5,
        "ammo": 5,
        "gate": (15, 11),
        "map": [
            "#################",
            "#S#.......#.....#",
            "#.#.#####.####..#",
            "#.....#.#.......#",
            "#.#.....##.####.#",
            "#.#.#.#.........#",
            "#.###.#.#.#####.#",
            "#.......#.......#",
            "#######.#########",
            "#.#.....#.....#.#",
            "#.#..######.#.#.#",
            "#...........#..G#",
            "#################",
        ],
    },
    3: {
        "title": "Stage 3 : Crossfire Grid",
        "guards": 8,
        "hunters": 8,
        "aliens": 4,
        "medkits": 6,
        "ammo": 7,
        "gate": (19, 13),
        "map": [
            "#####################",
            "#S................#.#",
            "#.#.#####...#####.#.#",
            "#.#.#...#.#...#.#...#",
            "#.#.#...#.###.#.#.#.#",
            "#.#.#.#.#...#.#...#.#",
            "#.#.#.#.###.#.#.###.#",
            "#.#...#.......#...#.#",
            "#...#######.#.###.#.#",
            "#.#.....#.........#.#",
            "#.#####.#.#.#.###.#.#",
            "#.....#.#.#.#...#.#.#",
            "#.###.#.#.#.#.#.#.#.#",
            "#.......#.#...#....G#",
            "#####################",
        ],
    },
    4: {
        "title": "Stage 4 : Warden Arena",
        "guards": 0,
        "hunters": 0,
        "aliens": 3,
        "medkits": 7,
        "ammo": 8,
        "gate": None,                 # no gate, you must kill the boss
        "map": [
            "###################",
            "#S................#",
            "#.................#",
            "#...AA.......AA...#",
            "#...AA.......AA...#",
            "#.................#",
            "#..A...........A..#",
            "#..A...........A..#",
            "#.................#",
            "#...AA.......AA...#",
            "#...AA.......AA...#",
            "#.................#",
            "#.................#",
            "###################",
        ],
    },
}

# wall colours are different for every stage
WALL_COLOR = {
    1: (0.16, 0.30, 0.40),    # deep steel blue
    2: (0.31, 0.18, 0.38),    # dark purple
    3: (0.14, 0.33, 0.25),    # forest green
    4: (0.37, 0.20, 0.15),    # rusty brown
}

# thin glowing strip drawn on top of every wall
WALL_TRIM = {
    1: (0.20, 0.75, 0.95),
    2: (0.85, 0.45, 1.00),
    3: (0.35, 0.95, 0.55),
    4: (1.00, 0.55, 0.25),
}


# --- TINY MATH / GRID / DRAWING HELPERS --------------------------


def clamp(value, low, high):
    """Keep a number inside a range."""
    return max(low, min(high, value))


def dist2(ax, ay, bx, by):
    """Squared distance. We avoid sqrt because it is slower."""
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def angle_to(ax, ay, bx, by):
    """Angle from point A to point B."""
    return math.atan2(by - ay, bx - ax)


def tile_center(col, row):
    """Convert a grid cell into the world position of its center."""
    return (origin_x + col * TILE + TILE * 0.5,
            origin_y + row * TILE + TILE * 0.5)


def tile_at(x, y):
    """Convert a world position into a grid cell."""
    col = int((x - origin_x) // TILE)
    row = int((y - origin_y) // TILE)
    return col, row


def is_wall_tile(col, row):
    """True if this cell is a wall or outside the map."""
    if col < 0 or row < 0 or col >= grid_w or row >= grid_h:
        return True
    return grid[row][col] == "#"


def is_acid_tile(col, row):
    """True if this cell is an acid pool."""
    if col < 0 or row < 0 or col >= grid_w or row >= grid_h:
        return False
    return grid[row][col] == "A"


def pick_free_tile(keep_away_from=None):
    """Pick a random empty cell that is not too close to the given cells."""
    avoid = [c for c in (keep_away_from or []) if c is not None]
    options = []
    for cell in free_tiles:
        ok = True
        for other in avoid:
            if abs(cell[0] - other[0]) + abs(cell[1] - other[1]) < 4:
                ok = False
                break
        if ok:
            options.append(cell)
    if not options:
        options = free_tiles[:]
    return random.choice(options)


def make_particles(x, y, z, color, count=8):
    """Spawn a small burst of glowing points."""
    for _ in range(count):
        particles.append({
            "x": x, "y": y, "z": z,
            "vx": random.uniform(-80, 80),
            "vy": random.uniform(-80, 80),
            "vz": random.uniform(20, 140),
            "life": random.uniform(0.25, 0.55),
            "color": color,
        })


def blood_splash(x, y, z, count=10):
    """Extra red blood particles thrown out right where a hit landed."""
    make_particles(x, y, z, (0.75, 0.02, 0.02), count)


def box(x, y, z, sx, sy, sz, color):
    """Draw one coloured box. Every object is built from these."""
    glPushMatrix()
    glColor3f(*color)
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glutSolidCube(1)
    glPopMatrix()


def tube(length, radius, color):
    """Draw a cylinder along the current Z axis (arms, legs, gun barrel)."""
    glColor3f(*color)
    gluCylinder(gluNewQuadric(), radius, radius * 0.85, length, 10, 2)


def draw_hp_bar(z, hp, max_hp, width):
    """Small floating health bar drawn above an enemy."""
    part = clamp(hp / float(max_hp), 0.0, 1.0)
    glPushMatrix()
    glTranslatef(0, 0, z)
    box(0, 0, 0, width, 5, 5, (0.20, 0.02, 0.02))                 # red back
    box(-(width * (1 - part)) * 0.5, 0, 3,
        width * part, 7, 7, (0.15, 0.90, 0.30))                   # green front
    glPopMatrix()





#  PART 1 of 3   --   YAHIA
#  Feature 1 : Minimap
#  Feature 2 : HUD (score, health, ammo, stage, crosshair)
#  Feature 3 : Pickup system + acid hazard



# FEATURE 1 : MINIMAP


def draw_minimap():
    """
    Top RIGHT minimap.
    We draw the whole grid small, then put coloured dots for the
    player, the gate and the keycard.
    """
    ox = WIN_W - MAP_SIZE - 18          # 18 pixels away from the right edge
    oy = WIN_H - MAP_SIZE - 18          # 18 pixels down from the top
    cw = MAP_SIZE / float(grid_w)
    ch = MAP_SIZE / float(grid_h)

    begin_2d()

    # background frame
    flat_rect(ox - 3, oy - 3, MAP_SIZE + 6, MAP_SIZE + 6, WALL_TRIM[stage_no])
    flat_rect(ox - 1, oy - 1, MAP_SIZE + 2, MAP_SIZE + 2, (0.03, 0.04, 0.05))

    # the grid itself
    glBegin(GL_QUADS)
    for row in range(grid_h):
        for col in range(grid_w):
            x0 = ox + col * cw
            y0 = oy + (grid_h - row - 1) * ch     # flip Y so it matches the world
            cell = grid[row][col]
            if cell == "#":
                glColor3f(*WALL_COLOR[stage_no])
            elif cell == "A":
                glColor3f(0.10, 0.75, 0.25)
            else:
                glColor3f(0.06, 0.08, 0.10)
            glVertex3f(x0, y0, 0)
            glVertex3f(x0 + cw - 1, y0, 0)
            glVertex3f(x0 + cw - 1, y0 + ch - 1, 0)
            glVertex3f(x0, y0 + ch - 1, 0)
    glEnd()

    # dots
    pc, pr = tile_at(hero["x"], hero["y"])
    map_dot(ox + pc * cw + cw * 0.5, oy + (grid_h - pr - 1) * ch + ch * 0.5,
            5, (0.15, 1.00, 0.30))                       # player = green
    if gate_tile:
        map_dot(ox + gate_tile[0] * cw + cw * 0.5,
                oy + (grid_h - gate_tile[1] - 1) * ch + ch * 0.5,
                4, (0.15, 0.80, 1.00))                   # gate = blue
        if not hero["has_key"]:
            map_dot(ox + key_tile[0] * cw + cw * 0.5,
                    oy + (grid_h - key_tile[1] - 1) * ch + ch * 0.5,
                    4, (1.00, 0.90, 0.10))               # keycard = yellow

    end_2d()


def map_dot(x, y, r, color):
    """One small square marker on the minimap."""
    flat_rect(x - r, y - r, r * 2, r * 2, color)



#FEATURE 2 : HUD


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    """Draw 2D text on the screen (taken from the lab template)."""
    glColor3f(1, 1, 1)
    glDisable(GL_DEPTH_TEST)                # text must always stay on top
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)          # screen coordinates

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)


def begin_2d():
    """
    Switch to 2D screen coordinates for HUD drawing.
    Depth test is turned OFF here, otherwise the HUD parts would hide
    each other because they are all drawn at the same depth (z = 0).
    """
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_W, 0, WIN_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()


def end_2d():
    """Go back to the normal 3D matrices and turn depth test on again."""
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)


def flat_rect(x, y, w, h, color):
    """Draw a filled 2D rectangle (used by the HUD and minimap)."""
    glColor3f(*color)
    glBegin(GL_QUADS)
    glVertex3f(x, y, 0)
    glVertex3f(x + w, y, 0)
    glVertex3f(x + w, y + h, 0)
    glVertex3f(x, y + h, 0)
    glEnd()


def draw_hud():
    """
    All the text is drawn at the BOTTOM LEFT so it never covers the
    minimap, which sits at the top right corner.
    """
    key_text = "YES" if (hero["has_key"] or gate_tile is None) else "NO"

    draw_text(14, 96, "Score : " + str(score))
    draw_text(14, 72, "Health: " + str(int(hero["hp"])) + " / " + str(MAX_HP))
    draw_text(14, 48, "Ammo  : " + ("UNLIMITED" if cheat_mode else str(hero["ammo"])))
    draw_text(14, 24, "Stage : " + str(stage_no) + "    Keycard : " + key_text)

    if cheat_mode:
        draw_text(14, 144, "CHEAT MODE ON (G)")

    if warden and warden["alive"]:
        draw_text(700, 24, "Warden HP : " + str(max(0, int(warden["hp"]))))

    if banner_timer > 0 and banner:
        draw_text(300, 748, banner)

    if game_over:
        draw_text(410, 430, "GAME OVER")
        draw_text(300, 400, "Press R to restart from Stage 1")
    if victory:
        draw_text(380, 430, "MISSION COMPLETE")
        draw_text(300, 400, "Final Score: " + str(score) + "    Press R to play again")

    draw_health_strip()
    draw_crosshair()


def draw_health_strip():
    """A green health bar under the HUD text."""
    begin_2d()
    part = clamp(hero["hp"] / float(MAX_HP), 0.0, 1.0)
    flat_rect(14, 118, 220, 12, (0.15, 0.05, 0.05))
    flat_rect(14, 118, 220 * part, 12, (0.20, 0.85, 0.35))
    end_2d()


def draw_crosshair():
    """A simple + shaped aiming mark in the middle of the screen."""
    begin_2d()
    cx = WIN_W // 2
    cy = WIN_H // 2
    color = (0.90, 0.95, 1.0)
    flat_rect(cx - 14, cy - 1, 9, 2, color)      # left
    flat_rect(cx + 5, cy - 1, 9, 2, color)       # right
    flat_rect(cx - 1, cy - 14, 2, 9, color)      # bottom
    flat_rect(cx - 1, cy + 5, 2, 9, color)       # top
    end_2d()


def say(text, seconds=2.2):
    """Show a short message on the screen for a few seconds."""
    global banner, banner_timer
    banner = text
    banner_timer = seconds


# --- FEATURE 3 : PICKUPS AND ACID HAZARD -------------------------


def spawn_items(medkit_count, ammo_count, busy):
    """Drop health packs and ammo boxes on random empty cells."""
    used = busy[:]
    for _ in range(medkit_count):
        cell = pick_free_tile(used)
        while is_acid_tile(*cell):
            cell = pick_free_tile(used)
        used.append(cell)
        x, y = tile_center(*cell)
        medkits.append({"x": x, "y": y, "heal": 25, "spin": random.random() * 360})

    for _ in range(ammo_count):
        cell = pick_free_tile(used)
        while is_acid_tile(*cell):
            cell = pick_free_tile(used)
        used.append(cell)
        x, y = tile_center(*cell)
        ammo_boxes.append({"x": x, "y": y, "bullets": 18, "spin": random.random() * 360})


def draw_items():
    """Draw the spinning health packs and ammo boxes."""
    for item in medkits:
        glPushMatrix()
        glTranslatef(item["x"], item["y"], 34)
        glRotatef(item["spin"], 0, 0, 1)
        # a plus sign made of two boxes
        box(0, 0, 0, 40, 12, 12, (0.10, 0.90, 0.20))
        box(0, 0, 0, 12, 40, 12, (0.10, 0.90, 0.20))
        glPopMatrix()

    for item in ammo_boxes:
        glPushMatrix()
        glTranslatef(item["x"], item["y"], 26)
        glRotatef(item["spin"], 0, 0, 1)
        box(0, 0, 0, 36, 24, 22, (0.10, 0.35, 0.85))
        box(0, 0, 16, 22, 14, 12, (0.95, 0.85, 0.20))
        glPopMatrix()


def update_pickups(dt):
    """
    Spin the health packs and ammo boxes, and collect them when the
    player walks close enough. Distance is compared in squared form
    so that we do not need a slow square root.
    """
    for item in medkits:
        item["spin"] += 90 * dt              # slow spin so they look alive
    for item in ammo_boxes:
        item["spin"] += 120 * dt

    # health packs
    for item in medkits[:]:
        if dist2(hero["x"], hero["y"], item["x"], item["y"]) < (ITEM_R + BODY_R) ** 2:
            hero["hp"] = min(float(MAX_HP), hero["hp"] + item["heal"])
            medkits.remove(item)
            say("Health restored", 1.1)
            make_particles(item["x"], item["y"], 45, (0.2, 1.0, 0.35))

    # ammo boxes
    for item in ammo_boxes[:]:
        if dist2(hero["x"], hero["y"], item["x"], item["y"]) < (ITEM_R + BODY_R) ** 2:
            hero["ammo"] += item["bullets"]
            ammo_boxes.remove(item)
            say("Ammo collected", 1.1)
            make_particles(item["x"], item["y"], 45, (0.35, 0.65, 1.0))


def check_acid(dt):
    """
    Acid hazard.
    If the player is standing on an 'A' cell we take damage every
    frame. We multiply by dt so the burn rate is the same on a fast
    and on a slow computer (about 22 health per second).
    """
    col, row = tile_at(hero["x"], hero["y"])
    if is_acid_tile(col, row):
        hurt_hero(22.0 * dt, "Acid burn")


#  PART 2 of 3   --   PEOPLE 1
#  Feature 4 : Maze system, collision and wall sliding
#  Feature 5 : Dual camera (first / third person) and input
#  Feature 6 : Keycard, locked gate and 4 stage progression




# --- FEATURE 4 : MAZE, COLLISION AND MOVEMENT --------------------


def can_stand(x, y, radius=BODY_R):
    """
    Collision check.
    We test the center plus 8 points around the body, so a corner
    of a wall cannot slip inside the player.
    """
    d = radius * 0.7
    points = [(x, y),
              (x + radius, y), (x - radius, y),
              (x, y + radius), (x, y - radius),
              (x + d, y + d), (x - d, y - d),
              (x + d, y - d), (x - d, y + d)]
    for px, py in points:
        col, row = tile_at(px, py)
        if is_wall_tile(col, row):
            return False
    return True


def move_hero(dt):
    """Read the held keys and move the player with wall sliding."""
    if game_over or victory:
        return

    forward = 0.0
    side = 0.0
    if b'w' in pressed_keys:
        forward += 1.0
    if b's' in pressed_keys:
        forward -= 1.0
    if b'a' in pressed_keys:
        side -= 1.0
    if b'd' in pressed_keys:
        side += 1.0
    if b'q' in pressed_keys:
        hero["yaw"] += SPIN_SPEED * dt
    if b'e' in pressed_keys:
        hero["yaw"] -= SPIN_SPEED * dt

    yaw = hero["yaw"]
    dx = math.cos(yaw) * forward * WALK_SPEED * dt
    dy = math.sin(yaw) * forward * WALK_SPEED * dt
    dx += math.cos(yaw - math.pi / 2) * side * SIDE_SPEED * dt
    dy += math.sin(yaw - math.pi / 2) * side * SIDE_SPEED * dt

    #X and Y are checked separately so we slide along a wall
    # instead of getting stuck on it
    if dx != 0.0 and can_stand(hero["x"] + dx, hero["y"]):
        hero["x"] += dx
    if dy != 0.0 and can_stand(hero["x"], hero["y"] + dy):
        hero["y"] += dy

    # the acid hazard is handled in its own function (Part 1)
    check_acid(dt)


def draw_floor():
    """Draw the floor as one quad per grid cell (checker pattern)."""
    glBegin(GL_QUADS)
    for row in range(grid_h):
        for col in range(grid_w):
            x0 = origin_x + col * TILE
            y0 = origin_y + row * TILE
            x1 = x0 + TILE
            y1 = y0 + TILE

            if is_acid_tile(col, row):
                # acid glows up and down using a sine wave
                glow = 0.18 + 0.12 * math.sin(clock * 5.0 + col)
                glColor3f(0.10, 0.55 + glow, 0.18)
            else:
                shade = 0.15 if (row + col) % 2 == 0 else 0.20
                tint = WALL_COLOR[stage_no]
                glColor3f(shade + tint[0] * 0.18,
                          shade + tint[1] * 0.18,
                          shade + tint[2] * 0.18)

            glVertex3f(x0, y0, 0)
            glVertex3f(x1, y0, 0)
            glVertex3f(x1, y1, 0)
            glVertex3f(x0, y1, 0)
    glEnd()


def draw_walls():
    """
    Draw a wall block for every '#' cell.
    Each wall is 3 parts: the main block, a bright trim strip,
    and a dark cap on the very top.
    """
    base = WALL_COLOR[stage_no]
    trim = WALL_TRIM[stage_no]

    for row in range(grid_h):
        for col in range(grid_w):
            if grid[row][col] != "#":
                continue
            x, y = tile_center(col, row)

            # checker pattern makes the wall look less flat
            step = 0.05 if (row + col) % 2 == 0 else 0.0
            body = (base[0] + step, base[1] + step, base[2] + step)

            box(x, y, WALL_HEIGHT * 0.45, TILE, TILE, WALL_HEIGHT * 0.9, body)
            box(x, y, WALL_HEIGHT * 0.94, TILE * 1.01, TILE * 1.01, 10, trim)
            box(x, y, WALL_HEIGHT + 6, TILE * 0.94, TILE * 0.94, 8, (0.06, 0.07, 0.09))


# --- FEATURE 5 : DUAL CAMERA AND INPUT ---------------------------


def setupCamera():
    """
    Set the projection and then place the camera.
    Two modes:
      first person  -> the eye is inside the player head
      third person  -> the eye is behind and above the player
    """
    global camera_pos

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 3000)      # 1.25 = 1000/800 window ratio
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if third_person:
        cx = hero["x"] - math.cos(hero["yaw"]) * 320
        cy = hero["y"] - math.sin(hero["yaw"]) * 320
        cz = 270
        # if the camera would be inside a wall, lift it higher instead
        if not can_stand(cx, cy, 20):
            cx = hero["x"] - math.cos(hero["yaw"]) * 120
            cy = hero["y"] - math.sin(hero["yaw"]) * 120
            cz = 430
        camera_pos = (cx, cy, cz)
        gluLookAt(cx, cy, cz,
                  hero["x"], hero["y"], 65,
                  0, 0, 1)
        return

    eye_x = hero["x"]
    eye_y = hero["y"]
    eye_z = hero["z"] + 28
    if shake_timer > 0:                        # small shake after taking damage
        eye_x += random.uniform(-3, 3)
        eye_y += random.uniform(-3, 3)
        eye_z += random.uniform(-2, 2)

    look_x = eye_x + math.cos(hero["yaw"]) * math.cos(hero["pitch"]) * 180
    look_y = eye_y + math.sin(hero["yaw"]) * math.cos(hero["pitch"]) * 180
    look_z = eye_z + math.sin(hero["pitch"]) * 180

    camera_pos = (eye_x, eye_y, eye_z)
    gluLookAt(eye_x, eye_y, eye_z, look_x, look_y, look_z, 0, 0, 1)


def draw_hero_model():
    """
    The player body. Only drawn in third person camera mode,
    because in first person the camera is inside the head.
    """
    walking = bool(pressed_keys & {b'w', b'a', b's', b'd'})
    swing = math.sin(clock * 12.0) * (18 if walking else 4)
    flash = 0.25 if hero["hurt_cd"] > 0 else 0.0

    glPushMatrix()
    glTranslatef(hero["x"], hero["y"], 0)
    glRotatef(math.degrees(hero["yaw"]), 0, 0, 1)

    # feet and legs (the legs swing while walking)
    box(0, 11, 8, 18, 12, 16, (0.04, 0.05, 0.06))
    box(0, -11, 8, 18, 12, 16, (0.04, 0.05, 0.06))
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(0, side * 12, 18)
        glRotatef(side * swing, 0, 1, 0)
        tube(32, 7, (0.12, 0.20, 0.26))
        glPopMatrix()

    # body and back pack
    box(0, 0, 54, 34, 42, 50, (0.10 + flash, 0.26, 0.32))
    box(-16, 0, 58, 16, 34, 42, (0.05, 0.08, 0.10))
    box(5, 0, 73, 24, 34, 13, (0.18 + flash, 0.50, 0.58))

    # head with a visor and antenna
    glPushMatrix()
    glTranslatef(0, 0, 93)
    box(0, 0, 0, 32, 32, 32, (0.16 + flash, 0.19, 0.21))
    box(14, 0, 2, 7, 28, 8, (0.10, 0.95, 1.00))
    glPushMatrix()
    glTranslatef(-8, 0, 16)
    tube(18, 2, (0.03, 0.04, 0.05))
    glPopMatrix()
    glPopMatrix()

    # both arms holding the gun in front
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(8, side * 25, 70)
        glRotatef(82 + side * swing * 0.4, 0, 1, 0)
        tube(36, 6, (0.11, 0.18, 0.22))
        glPopMatrix()

    box(33, 0, 67, 48, 9, 9, (0.05, 0.05, 0.06))     # gun
    box(56, 0, 67, 18, 5, 5, (0.00, 0.00, 0.00))     # barrel tip

    glPopMatrix()


def draw_gun_view():
    """
    The gun held in front of the camera (first person view model).
    We reset the matrices so it is drawn in front of everything and
    does not move with the world.
    """
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glTranslatef(0.18, -0.34, -0.72)

    # hands
    box(-0.13, -0.08, 0.02, 0.16, 0.07, 0.12, (0.68, 0.48, 0.34))
    box(0.10, -0.08, 0.02, 0.16, 0.07, 0.12, (0.68, 0.48, 0.34))
    # arms
    box(-0.18, -0.18, 0.06, 0.20, 0.08, 0.18, (0.09, 0.19, 0.24))
    box(0.04, -0.18, 0.06, 0.20, 0.08, 0.18, (0.09, 0.19, 0.24))
    # gun body and magazine
    box(0.02, 0.00, -0.08, 0.16, 0.10, 0.38, (0.13, 0.14, 0.16))
    box(0.02, -0.06, 0.08, 0.08, 0.06, 0.16, (0.20, 0.17, 0.12))

    glPushMatrix()
    glTranslatef(0.02, 0, -0.28)
    glRotatef(180, 1, 0, 0)
    tube(0.25, 0.025, (0.04, 0.04, 0.05))            # barrel
    glPopMatrix()

    # muzzle flash right after firing
    if hero["shot_cd"] > 0.12:
        box(0.02, 0, -0.56, 0.09, 0.09, 0.09, (1.0, 0.75, 0.10))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def keyboardListener(key, x, y):
    """A key was pressed. Movement keys go into a set."""
    global third_person, cheat_mode
    k = key.lower()
    pressed_keys.add(k)

    if k == b'r':                       # restart
        start_new_game()
    elif k == b' ':                     # shoot
        shoot()
    elif k == b'c':                     # change camera mode
        third_person = not third_person
    elif k == b'g':                     # toggle cheat mode
        cheat_mode = not cheat_mode
        hero["hp"] = float(MAX_HP)
        say("CHEAT MODE ON - unlimited health & ammo" if cheat_mode
            else "Cheat mode off", 1.6)


def keyboardUpListener(key, x, y):
    """A key was released, so remove it from the set."""
    pressed_keys.discard(key.lower())


def specialKeyListener(key, x, y):
    """Arrow keys turn the camera left/right and look up/down."""
    if key == GLUT_KEY_LEFT:
        hero["yaw"] += 0.08
    elif key == GLUT_KEY_RIGHT:
        hero["yaw"] -= 0.08
    elif key == GLUT_KEY_UP:
        hero["pitch"] = clamp(hero["pitch"] + 0.04, -0.55, 0.45)
    elif key == GLUT_KEY_DOWN:
        hero["pitch"] = clamp(hero["pitch"] - 0.04, -0.55, 0.45)


def mouseListener(button, state, x, y):
    """Left click shoots, right click changes the camera mode."""
    global third_person
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        shoot()
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        third_person = not third_person


# --- FEATURE 6 : KEYCARD, GATE AND STAGE PROGRESSION -------------


def build_stage(number, keep_items=True):
    """Read the stage map, place the player, and spawn everything."""
    global stage_no, grid, grid_w, grid_h, origin_x, origin_y
    global free_tiles, gate_tile, key_tile
    global guards, hunters, aliens, warden, my_shots, foe_shots
    global medkits, ammo_boxes, particles

    stage_no = number
    data = STAGES[stage_no]
    grid = data["map"]
    grid_h = len(grid)
    grid_w = len(grid[0])

    # place the grid so that the middle of the maze sits at (0, 0)
    origin_x = -grid_w * TILE * 0.5
    origin_y = -grid_h * TILE * 0.5

    # scan the map once and remember every empty cell
    free_tiles = []
    start_tile = (1, 1)
    for row in range(grid_h):
        for col in range(grid_w):
            ch = grid[row][col]
            if ch != "#":
                free_tiles.append((col, row))
            if ch == "S":
                start_tile = (col, row)

    # reset the player for this stage
    sx, sy = tile_center(*start_tile)
    hero["x"] = sx
    hero["y"] = sy
    hero["z"] = 42.0
    hero["yaw"] = 0.0
    hero["pitch"] = 0.0
    hero["has_key"] = False
    hero["shot_cd"] = 0.0
    hero["hurt_cd"] = 0.0
    if not keep_items:                 # only on a fresh game
        hero["hp"] = float(MAX_HP)
        hero["ammo"] = START_AMMO

    # clear all old objects
    guards = []
    hunters = []
    aliens = []
    warden = None
    my_shots = []
    foe_shots = []
    medkits = []
    ammo_boxes = []
    particles = []

    # the exit gate and the keycard
    gate_tile = data["gate"]
    key_tile = pick_free_tile([start_tile, gate_tile])
    while key_tile == start_tile or key_tile == gate_tile or is_acid_tile(*key_tile):
        key_tile = pick_free_tile([start_tile, gate_tile])

    busy = [c for c in [start_tile, gate_tile, key_tile] if c is not None]
    spawn_items(data["medkits"], data["ammo"], busy)
    spawn_enemies(data["guards"], data["hunters"], busy)
    spawn_aliens(data.get("aliens", 0), busy)

    # the boss only exists on the last stage
    if stage_no == 4:
        make_warden()

    say(data["title"], 2.6)


def update_key_and_gate(dt):
    """
    Pick up the keycard, and move to the next stage when the player
    reaches the gate WITH the keycard. Without it the gate stays shut.
    """
    # the keycard
    if gate_tile and not hero["has_key"]:
        kx, ky = tile_center(*key_tile)
        if dist2(hero["x"], hero["y"], kx, ky) < (KEY_R + BODY_R) ** 2:
            hero["has_key"] = True
            say("Keycard found - the gate is open", 2.0)
            make_particles(kx, ky, 70, (1.0, 0.9, 0.2), 12)

    # the exit gate
    if gate_tile:
        gx, gy = tile_center(*gate_tile)
        if dist2(hero["x"], hero["y"], gx, gy) < (GATE_R + BODY_R) ** 2:
            if hero["has_key"]:
                go_next_stage()
            else:
                say("Gate is locked. Find the keycard.", 1.4)


def draw_key_and_gate():
    """Draw the floating keycard and the exit gate ring."""
    # keycard: a spinning diamond that floats up and down
    if gate_tile and not hero["has_key"]:
        x, y = tile_center(*key_tile)
        glPushMatrix()
        glTranslatef(x, y, 52 + 9 * math.sin(clock * 2.5))
        glRotatef(clock * 90.0, 0, 0, 1)
        glRotatef(45, 1, 0, 0)
        box(0, 0, 0, 30, 30, 30, (1.00, 0.84, 0.10))
        glPopMatrix()

    # gate: a ring of small blocks, red when locked and cyan when open
    if gate_tile:
        x, y = tile_center(*gate_tile)
        open_now = hero["has_key"]
        color = (0.15, 0.95, 1.00) if open_now else (0.85, 0.15, 0.25)

        glPushMatrix()
        glTranslatef(x, y, 62)
        glRotatef(clock * 60.0, 0, 0, 1)
        for i in range(12):                       # 12 blocks around a circle
            ang = i * (math.tau / 12)
            bx = math.cos(ang) * 52
            by = math.sin(ang) * 52
            box(bx, by, 0, 16, 16, 26, color)
        box(0, 0, 0, 14, 14, 96, color)           # centre pillar
        glPopMatrix()


def start_new_game():
    """Reset the score and start again from stage 1."""
    global score, game_over, victory
    score = 0
    game_over = False
    victory = False
    build_stage(1, keep_items=False)


def go_next_stage():
    """Move to the next stage, or finish the game after stage 4."""
    global victory, score
    if stage_no < 4:
        score += 150                       # bonus for clearing a stage
        build_stage(stage_no + 1, keep_items=True)
    else:
        victory = True
        say("VICTORY - the Warden is down. Press R to play again.", 999)


# PART 3 of 3   --   PEOPLE 2
# Feature 7 : Guard AI  (scan, line of sight, timed firing)
# Feature 8 : Hunter AI (chase, roam, respawn)
# Feature 9 : Two phase boss fight + projectile system


# --- FEATURE 7 : GUARD AI ----------------------------------------


def can_see(ax, ay, bx, by):
    """
    Line of sight check.
    We walk in small steps from A to B, and if any step lands on a
    wall then the view is blocked.
    """
    steps = int(max(6, math.sqrt(dist2(ax, ay, bx, by)) / 35))
    for i in range(1, steps):
        t = i / float(steps)
        col, row = tile_at(ax + (bx - ax) * t, ay + (by - ay) * t)
        if is_wall_tile(col, row):
            return False
    return True


def spawn_enemies(guard_count, hunter_count, busy):
    """Place the two normal enemy types on random empty cells."""
    used = busy[:]

    for _ in range(guard_count):
        cell = pick_free_tile(used)
        while is_acid_tile(*cell):
            cell = pick_free_tile(used)
        used.append(cell)
        x, y = tile_center(*cell)
        guards.append({
            "x": x, "y": y,
            "hp": 70, "max_hp": 70,
            "yaw": random.random() * math.tau,
            "shot_cd": random.uniform(0.3, 1.6),
            "turn_dir": random.choice([-1, 1]),   # scanning direction
            "alive": True,
        })

    for _ in range(hunter_count):
        cell = pick_free_tile(used)
        while is_acid_tile(*cell):
            cell = pick_free_tile(used)
        used.append(cell)
        x, y = tile_center(*cell)
        hunters.append(new_hunter(x, y))


def update_guards(dt):
    """Standing enemies: keep scanning, shoot when they can see us."""
    for g in guards:
        if not g["alive"]:
            continue
        g["yaw"] += g["turn_dir"] * 0.65 * dt      # slow scanning turn
        g["shot_cd"] -= dt

        d = math.sqrt(dist2(g["x"], g["y"], hero["x"], hero["y"]))
        if d < 620 and can_see(g["x"], g["y"], hero["x"], hero["y"]):
            g["yaw"] = angle_to(g["x"], g["y"], hero["x"], hero["y"])   # aim
            if g["shot_cd"] <= 0:
                enemy_shoot(g["x"], g["y"], 82, FOE_SHOT_SPEED, 8)
                g["shot_cd"] = random.uniform(0.85, 1.35)


def draw_guard(g):
    """Draw one standing enemy: base, rotating head, gun barrel."""
    if not g["alive"]:
        return
    glPushMatrix()
    glTranslatef(g["x"], g["y"], 0)

    box(0, 0, 14, 58, 58, 28, (0.20, 0.24, 0.28))      # base
    glTranslatef(0, 0, 44)
    glRotatef(math.degrees(g["yaw"]), 0, 0, 1)         # the head turns
    box(0, 0, 0, 46, 38, 30, (0.40, 0.46, 0.52))       # head
    box(0, 0, 16, 14, 14, 8, (1.0, 0.35, 0.25))        # red eye light

    glPushMatrix()
    glTranslatef(34, 0, 5)
    glRotatef(90, 0, 1, 0)
    tube(58, 8, (0.08, 0.10, 0.12))                    # barrel
    glPopMatrix()

    draw_hp_bar(54, g["hp"], g["max_hp"], 48)
    glPopMatrix()


def enemy_shoot(ex, ey, ez, speed=FOE_SHOT_SPEED, damage=8):
    """An enemy fires one bullet straight at the player."""
    ang = angle_to(ex, ey, hero["x"], hero["y"])
    foe_shots.append({
        "x": ex, "y": ey, "z": ez,
        "vx": math.cos(ang) * speed,
        "vy": math.sin(ang) * speed,
        "vz": random.uniform(-10, 20),
        "life": 3.2,
        "damage": damage,
    })


# --- FEATURE 8 : HUNTER AI ---------------------------------------


def new_hunter(x, y):
    """Create one chasing enemy. Used at spawn time and on respawn."""
    return {
        "x": x, "y": y,
        "hp": 55, "max_hp": 55,
        "speed": random.uniform(95, 125),
        "hurt_cd": 0.0,
        "roam": random.random() * math.tau,   # random walking direction
        "alive": True,
    }


def update_hunters(dt):
    """Moving enemies: chase if they see us, otherwise walk around."""
    for h in hunters:
        if not h["alive"]:
            continue
        h["hurt_cd"] = max(0.0, h["hurt_cd"] - dt)

        d = math.sqrt(dist2(h["x"], h["y"], hero["x"], hero["y"]))
        chasing = d < 620 and can_see(h["x"], h["y"], hero["x"], hero["y"])

        if chasing:
            ang = angle_to(h["x"], h["y"], hero["x"], hero["y"])
        else:
            h["roam"] += random.uniform(-1.4, 1.4) * dt
            ang = h["roam"]

        speed = h["speed"] * (1.2 if chasing else 0.45)
        # FIX: stop at arm's length. Before, a hunter walked right into the
        # player's body, where bullets (spawned 42 units ahead) could never
        # hit it. At 46 it still touches us (d < 52) but can be shot.
        if chasing and d < 46:
            speed = 0.0
        nx = h["x"] + math.cos(ang) * speed * dt
        ny = h["y"] + math.sin(ang) * speed * dt

        # if a wall blocks one axis, turn a bit and keep the other axis
        if can_stand(nx, h["y"], 22):
            h["x"] = nx
        else:
            h["roam"] += 1.7
        if can_stand(h["x"], ny, 22):
            h["y"] = ny
        else:
            h["roam"] -= 1.1

        # touching the player hurts
        if d < BODY_R + 28 and hero["hurt_cd"] <= 0:
            hurt_hero(7 + stage_no, "Hunter hit you")


def draw_hunter(h):
    """Draw one chasing enemy. It always faces the player."""
    if not h["alive"]:
        return
    flash = 0.25 if h["hurt_cd"] > 0 else 0.0          # flashes when shot

    glPushMatrix()
    glTranslatef(h["x"], h["y"], 0)
    glRotatef(math.degrees(angle_to(h["x"], h["y"], hero["x"], hero["y"])), 0, 0, 1)

    box(0, 0, 30, 40, 34, 58, (0.70 + flash, 0.16, 0.32))    # body
    box(18, 12, 68, 10, 10, 10, (1.0, 0.90, 0.30))           # eyes
    box(18, -12, 68, 10, 10, 10, (1.0, 0.90, 0.30))
    box(-12, 0, 12, 50, 20, 18, (0.26, 0.05, 0.12))          # tail
    for side in (-1, 1):                                     # two legs
        box(0, side * 16, 6, 14, 12, 14, (0.15, 0.03, 0.08))

    draw_hp_bar(88, h["hp"], h["max_hp"], 45)
    glPopMatrix()


def kill_enemy(enemy, kind):
    """Mark an enemy dead, add score, and sometimes respawn a hunter."""
    global score
    enemy["alive"] = False

    if kind == "guard":
        score += 70
        make_particles(enemy["x"], enemy["y"], 80, (0.8, 0.9, 1.0))

    elif kind == "hunter":
        score += 55
        make_particles(enemy["x"], enemy["y"], 50, (1.0, 0.35, 0.25))
        blood_splash(enemy["x"], enemy["y"], 50, 14)
        # on stage 2 and 3 a dead hunter has a chance to come back
        if stage_no in (2, 3) and random.random() < 0.35:
            cell = pick_free_tile([tile_at(hero["x"], hero["y"])])
            x, y = tile_center(*cell)
            hunters.append(new_hunter(x, y))

    elif kind == "alien":
        score += 60
        make_particles(enemy["x"], enemy["y"], 55, (0.3, 1.0, 0.25))
        blood_splash(enemy["x"], enemy["y"], 55, 14)


# --- EXTRA ENEMY : ALIEN SHOOTER (green animal-type) -------------


def spawn_aliens(count, busy):
    """Place the green alien shooters on random empty cells."""
    used = busy[:]
    for _ in range(count):
        cell = pick_free_tile(used)
        while is_acid_tile(*cell):
            cell = pick_free_tile(used)
        used.append(cell)
        x, y = tile_center(*cell)
        aliens.append({
            "x": x, "y": y,
            "hp": 60, "max_hp": 60,
            "yaw": random.random() * math.tau,
            "shot_cd": random.uniform(0.3, 1.6),
            "turn_dir": random.choice([-1, 1]),   # scanning direction
            "alive": True,
        })


def update_aliens(dt):
    """Alien shooters: scan like a guard, then aim and fire when they see us."""
    for a in aliens:
        if not a["alive"]:
            continue
        a["yaw"] += a["turn_dir"] * 0.55 * dt      # slow scanning turn
        a["shot_cd"] -= dt

        d = math.sqrt(dist2(a["x"], a["y"], hero["x"], hero["y"]))
        if d < 600 and can_see(a["x"], a["y"], hero["x"], hero["y"]):
            a["yaw"] = angle_to(a["x"], a["y"], hero["x"], hero["y"])   # aim
            if a["shot_cd"] <= 0:
                enemy_shoot(a["x"], a["y"], 78, FOE_SHOT_SPEED, 9)
                a["shot_cd"] = random.uniform(0.8, 1.3)


def draw_alien(a):
    """Draw one alien shooter: green animal-style body, big eye, antennae."""
    if not a["alive"]:
        return
    glPushMatrix()
    glTranslatef(a["x"], a["y"], 0)

    box(0, 0, 16, 46, 42, 32, (0.12, 0.50, 0.16))      # green haunch / base
    glTranslatef(0, 0, 42)
    glRotatef(math.degrees(a["yaw"]), 0, 0, 1)         # the head turns
    box(0, 0, 0, 34, 30, 26, (0.18, 0.65, 0.22))       # head
    box(14, 0, 6, 14, 14, 10, (0.80, 1.00, 0.30))      # single big alien eye

    for side in (-1, 1):                               # two curled antennae
        glPushMatrix()
        glTranslatef(-6, side * 11, 14)
        glRotatef(side * 30, 1, 0, 0)
        tube(22, 3, (0.10, 0.40, 0.14))
        glPopMatrix()

    glPushMatrix()
    glTranslatef(30, 0, 2)
    glRotatef(90, 0, 1, 0)
    tube(52, 7, (0.07, 0.28, 0.10))                    # forelimb / barrel
    glPopMatrix()

    draw_hp_bar(52, a["hp"], a["max_hp"], 46)
    glPopMatrix()


# --- FEATURE 9 : BOSS FIGHT AND PROJECTILE SYSTEM ----------------


def make_warden():
    """Create the boss in the middle of the arena."""
    global warden
    bx, by = tile_center(grid_w // 2, grid_h // 2)
    warden = {
        "x": bx, "y": by,
        "hp": 420, "max_hp": 420,
        "phase": 1,
        "shot_cd": 1.0,
        "slam_cd": 3.0,
        "alive": True,
    }


def update_warden(dt):
    """
    Boss logic.
    Phase 1 = slower fan of bullets.
    Phase 2 = starts below 55% health, faster and wider fan.
    """
    if not warden or not warden["alive"]:
        return

    d = math.sqrt(dist2(warden["x"], warden["y"], hero["x"], hero["y"]))
    warden["phase"] = 2 if warden["hp"] < warden["max_hp"] * 0.55 else 1
    warden["shot_cd"] -= dt
    warden["slam_cd"] -= dt

    # attack 1: a fan of bullets aimed at the player
    if warden["shot_cd"] <= 0:
        count = 8 if warden["phase"] == 1 else 12
        base = angle_to(warden["x"], warden["y"], hero["x"], hero["y"])
        for i in range(count):
            ang = base + (i - count // 2) * 0.12
            foe_shots.append({
                # FIX: was z = 120, above the player hit zone (0 < z < 105),
                # so the bullet fan could never hit. 75 = chest height.
                "x": warden["x"], "y": warden["y"], "z": 75,
                "vx": math.cos(ang) * (240 + warden["phase"] * 35),
                "vy": math.sin(ang) * (240 + warden["phase"] * 35),
                "vz": 0.0,
                "life": 4.0,
                "damage": 10,
            })
        warden["shot_cd"] = 1.2 if warden["phase"] == 1 else 0.85

    # attack 2: ground slam that only hits if we are close and visible
    if warden["slam_cd"] <= 0:
        make_particles(warden["x"], warden["y"], 30, (1.0, 0.25, 0.1), 14)
        if d < 260 and can_see(warden["x"], warden["y"], hero["x"], hero["y"]):
            hurt_hero(15, "Warden shockwave")
        warden["slam_cd"] = 3.1 if warden["phase"] == 1 else 2.2

    # attack 3: standing inside the boss hurts
    if d < 95 and hero["hurt_cd"] <= 0:
        hurt_hero(18, "Warden crushed you")


def draw_warden():
    """Draw the boss: big body, head, and 4 spinning arms."""
    if not warden or not warden["alive"]:
        return
    pulse = 0.08 * math.sin(clock * 6.0)               # slow breathing effect

    glPushMatrix()
    glTranslatef(warden["x"], warden["y"], 0)
    glRotatef(clock * 18.0, 0, 0, 1)                   # the whole boss spins

    box(0, 0, 70, 130, 130, 140, (0.42 + pulse, 0.10, 0.06))
    box(0, 0, 164, 84, 84, 54, (0.26, 0.04, 0.03))
    box(0, 0, 196, 30, 30, 22, (1.0, 0.60, 0.10))      # glowing core on top

    for ang in (0, 90, 180, 270):
        glPushMatrix()
        glRotatef(ang, 0, 0, 1)
        box(96, 0, 84, 86, 28, 34, (0.20, 0.02, 0.02))
        glPopMatrix()

    draw_hp_bar(220, warden["hp"], warden["max_hp"], 150)
    glPopMatrix()


def shoot():
    """Fire one bullet in the direction the player is looking."""
    if game_over or victory:
        return
    if hero["shot_cd"] > 0:                # still cooling down
        return
    if hero["ammo"] <= 0 and not cheat_mode:
        say("No ammo left. Find an ammo box.", 1.4)
        hero["shot_cd"] = 0.2
        return

    if not cheat_mode:
        hero["ammo"] -= 1
    hero["shot_cd"] = 0.22

    # direction vector built from yaw (left/right) and pitch (up/down)
    yaw, pitch = hero["yaw"], hero["pitch"]
    fx = math.cos(yaw) * math.cos(pitch)
    fy = math.sin(yaw) * math.cos(pitch)
    fz = math.sin(pitch)

    bx = hero["x"] + fx * 42
    by = hero["y"] + fy * 42
    bz = hero["z"] + 22 + fz * 10

    my_shots.append({
        "x": bx, "y": by, "z": bz,
        "vx": fx * MY_SHOT_SPEED,
        "vy": fy * MY_SHOT_SPEED,
        "vz": fz * MY_SHOT_SPEED,
        "life": 1.4,
        "damage": 34,
    })
    make_particles(bx, by, bz, (1.0, 0.88, 0.28), 5)


def update_shots(dt):
    """Move every bullet and check what it hits."""
    global score

    # ---- player bullets ----
    for b in my_shots[:]:
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["z"] += b["vz"] * dt
        b["life"] -= dt

        col, row = tile_at(b["x"], b["y"])
        if is_wall_tile(col, row) or b["z"] < 5 or b["z"] > 210 or b["life"] <= 0:
            make_particles(b["x"], b["y"], max(10, b["z"]), (0.9, 0.8, 0.2), 4)
            my_shots.remove(b)
            continue

        hit = False

        for g in guards:
            if g["alive"] and b["z"] < 135 and \
               dist2(b["x"], b["y"], g["x"], g["y"]) < 42 ** 2:
                g["hp"] -= b["damage"]
                hit = True
                make_particles(b["x"], b["y"], b["z"], (0.5, 0.9, 1.0), 5)
                blood_splash(b["x"], b["y"], b["z"], 8)
                if g["hp"] <= 0:
                    kill_enemy(g, "guard")
                break

        if not hit:
            for h in hunters:
                if h["alive"] and b["z"] < 105 and \
                   dist2(b["x"], b["y"], h["x"], h["y"]) < 36 ** 2:
                    h["hp"] -= b["damage"]
                    h["hurt_cd"] = 0.25
                    hit = True
                    make_particles(b["x"], b["y"], b["z"], (1.0, 0.35, 0.22), 5)
                    blood_splash(b["x"], b["y"], b["z"], 8)
                    if h["hp"] <= 0:
                        kill_enemy(h, "hunter")
                    break

        if not hit:
            for a in aliens:
                if a["alive"] and b["z"] < 110 and \
                   dist2(b["x"], b["y"], a["x"], a["y"]) < 38 ** 2:
                    a["hp"] -= b["damage"]
                    hit = True
                    make_particles(b["x"], b["y"], b["z"], (0.4, 1.0, 0.3), 5)
                    blood_splash(b["x"], b["y"], b["z"], 8)
                    if a["hp"] <= 0:
                        kill_enemy(a, "alien")
                    break

        if not hit and warden and warden["alive"]:
            if 20 < b["z"] < 190 and \
               dist2(b["x"], b["y"], warden["x"], warden["y"]) < 95 ** 2:
                warden["hp"] -= b["damage"]
                hit = True
                score += 8
                make_particles(b["x"], b["y"], b["z"], (1.0, 0.15, 0.1), 5)
                blood_splash(b["x"], b["y"], b["z"], 6)
                if warden["hp"] <= 0:
                    warden["alive"] = False
                    score += 500
                    make_particles(warden["x"], warden["y"], 120, (1.0, 0.6, 0.1), 30)
                    go_next_stage()

        if hit and b in my_shots:
            my_shots.remove(b)

    # ---- enemy bullets ----
    for b in foe_shots[:]:
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["z"] += b["vz"] * dt
        b["life"] -= dt

        col, row = tile_at(b["x"], b["y"])
        if is_wall_tile(col, row) or b["life"] <= 0:
            foe_shots.remove(b)
            continue

        if 0 < b["z"] < 105 and \
           dist2(b["x"], b["y"], hero["x"], hero["y"]) < (BODY_R + 12) ** 2:
            hurt_hero(b["damage"], "Hit by enemy fire")
            if b in foe_shots:
                foe_shots.remove(b)


def draw_shots():
    """Draw both kinds of bullets as small cubes."""
    for b in my_shots:
        box(b["x"], b["y"], b["z"], 12, 12, 12, (1.00, 0.90, 0.15))
    for b in foe_shots:
        box(b["x"], b["y"], b["z"], 16, 16, 16, (1.00, 0.25, 0.10))


def hurt_hero(amount, reason=""):
    """Reduce player health and check for game over."""
    global game_over, shake_timer
    if game_over or victory:
        return
    if cheat_mode:                         # G cheat mode: no damage taken
        return
    hero["hp"] = max(0.0, hero["hp"] - amount)
    hero["hurt_cd"] = 0.35
    shake_timer = 0.22                     # shake the camera a little
    blood_splash(hero["x"], hero["y"], hero["z"] + 40, 10)
    if reason:
        say(reason, 1.0)
    if hero["hp"] <= 0:
        game_over = True
        say("GAME OVER - press R to restart", 999)


def update_particles(dt):
    """Move the spark points and pull them down with gravity."""
    for p in particles[:]:
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["z"] += p["vz"] * dt
        p["vz"] -= 260 * dt                 # gravity
        p["life"] -= dt
        if p["life"] <= 0:
            particles.remove(p)


def draw_particles():
    """Draw the sparks as GL points."""
    glPointSize(4)
    glBegin(GL_POINTS)
    for p in particles:
        glColor3f(*p["color"])
        glVertex3f(p["x"], p["y"], p["z"])
    glEnd()


#  MAIN LOOP -- glues all three parts together
#  update_game() calls every part once per frame,
#  showScreen() draws one frame, main() starts GLUT.


def update_game(dt):
    """One full game step. Called from idle()."""
    global banner_timer, shake_timer

    banner_timer = max(0.0, banner_timer - dt)
    shake_timer = max(0.0, shake_timer - dt)
    hero["shot_cd"] = max(0.0, hero["shot_cd"] - dt)
    hero["hurt_cd"] = max(0.0, hero["hurt_cd"] - dt)

    move_hero(dt)
    update_pickups(dt)
    update_key_and_gate(dt)
    update_guards(dt)
    update_hunters(dt)
    update_aliens(dt)
    update_warden(dt)
    update_shots(dt)
    update_particles(dt)


def idle():
    """
    Runs all the time.
    We measure how much real time passed (delta time) so the game
    runs at the same speed on a fast and a slow computer.
    """
    global prev_time, clock
    now = time.time()
    if prev_time == 0.0:
        prev_time = now
    dt = now - prev_time
    prev_time = now

    clock += dt
    dt = min(dt, 0.05)          # safety cap if the window freezes for a moment

    update_game(dt)
    glutPostRedisplay()


def showScreen():
    """Draw one frame: world first, then the player, then the HUD."""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WIN_W, WIN_H)

    setupCamera()

    draw_floor()
    draw_walls()
    draw_key_and_gate()
    draw_items()

    for g in guards:
        draw_guard(g)
    for h in hunters:
        draw_hunter(h)
    for a in aliens:
        draw_alien(a)
    draw_warden()

    if third_person:
        draw_hero_model()       # show the body only in third person

    draw_shots()
    draw_particles()

    if not third_person:
        draw_gun_view()         # show the held gun only in first person

    draw_hud()
    draw_minimap()

    glutSwapBuffers()


def init_gl():
    """Turn on depth testing so near objects hide far objects."""
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.02, 0.03, 0.05, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_W, WIN_H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"Vault Runner 3D - Keycard, Gate and Warden")

    init_gl()
    start_new_game()

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)     # needed for smooth movement
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    glutIgnoreKeyRepeat(1)     # one press event, one release event
    glutMainLoop()



if __name__ == "__main__":
    main()
