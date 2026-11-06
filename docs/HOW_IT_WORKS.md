# How Vault Runner 3D works

A plain-language tour of the game, written for anyone who is curious, with no coding background needed. Every picture below is a real description of what the code in [`vault_runner.py`](../vault_runner.py) does.

## 1. The game is a loop

A video game is really a very fast flipbook. About 60 times every second, the game runs the same four steps, then shows you the new picture.

![The game loop](sketches/game-loop.svg)

1. **Read the keys.** Which keys are held down right now? Was the mouse clicked?
2. **Move everything.** The player, every enemy, every bullet and every spark takes one small step.
3. **Check what touched what.** Did a bullet hit someone? Did the player walk into a wall, onto a health pack, or into acid?
4. **Draw the picture.** Paint the 3D world, then paint the health bar, ammo and minimap on top.

**Why the game feels the same on every computer:** a fast computer runs the loop more often than a slow one. If everything moved "5 steps per lap", the game would run faster on a fast PC. Instead, every movement is multiplied by **how much time passed since the last lap** (called `dt`, "delta time"). Faster laps means smaller steps, so the speed in real seconds is always the same. The acid, for example, always burns exactly 22 health per second.

## 2. Every frame is two layers

![Two layers](sketches/screen-layers.svg)

The picture you see is painted in two passes:

- **The 3D world** is painted first, through a *perspective camera*: things far away look smaller, just like in real life. The graphics card keeps a "depth" number for every pixel so that a wall in front correctly hides an enemy behind it.
- **The HUD** (health, ammo, score, crosshair, minimap) is painted last, as a flat 2D layer, like stickers on a window. Depth is switched off for this pass so nothing in the world can ever cover it.

Switching between these two "modes" is done with OpenGL's *projection matrix*: a perspective one for the world (`gluPerspective`), and a flat one that maps straight to screen pixels for the HUD (`gluOrtho2D`).

## 3. The minimap: shrinking the world

![Minimap math](sketches/minimap-math.svg)

The maze is stored as a grid of letters (`#` is a wall, `.` is floor). The minimap redraws that grid, very small, in the corner of the screen, and puts dots on it:

1. **World → grid:** divide the player's position by the size of one tile (120 units). 1,020 units from the left edge is column 8.5.
2. **Grid → pixels:** multiply by the size of one minimap cell (about 10 pixels) and add the minimap's corner position.
3. **Which way you face:** a short line from your dot, pointing along your turning angle. Its direction is `(cos a, sin a)`, the standard way to turn an angle into a direction.

The minimap first drew row 0 at the top, so it matched how the maze looks in the code. But in the 3D world, row 0 is at the *bottom* when you look down from above, so the map was secretly a mirror image. The robot tester caught that, and it was fixed in [issue #3](https://github.com/YahiaRabbi/vault-runner-3d/issues/3).

## 4. Walls you can't walk through

![Collision](sketches/collision.svg)

- The player's body is a circle. Before every step, the game checks **9 points** on and inside that circle (the centre plus 8 around the edge). If any point would land inside a wall tile, that step is not allowed.
- Sideways and forward movement are checked **separately**. If you walk diagonally into a wall, the part of the move that goes into the wall is blocked, but the part that runs along the wall still happens, so you *slide* instead of getting stuck.
