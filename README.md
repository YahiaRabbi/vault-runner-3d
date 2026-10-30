# Vault Runner 3D

A first-person 3D maze shooter built from raw OpenGL. No game engine.

Written in **Python + PyOpenGL + GLUT** as the final project for **CSE423 · Computer Graphics**. Every wall, enemy, camera and HUD element is drawn with OpenGL calls and matrix transforms.

## Gameplay

Fight through 4 stages. In stages 1–3 you find the **keycard**, which unlocks the **exit gate**. Stage 4 is the **Warden Arena**: beat the two-phase boss to win.

## Features

1. Real-time tactical minimap
2. Screen-space HUD (health, ammo, score, stage, crosshair)
3. Pickups and acid hazard
4. Maze collision with wall sliding
5. Dual camera (first / third person)
6. Keycard, locked gate and 4-stage progression
7. Guard and alien AI (scan, line of sight, timed fire)
8. Hunter AI (chase, roam, respawn)
9. Two-phase boss fight and projectile system

## Controls

| Key | Action |
|---|---|
| `W` / `S` | Move forward / back |
| `A` / `D` | Strafe left / right |
| `Q` / `E` or `←` / `→` | Turn |
| `↑` / `↓` | Look up / down |
| `Space` or left click | Shoot |
| `C` or right click | Switch first / third person |
| `G` | Cheat mode |
| `R` | Restart |

## Run it

```bash
pip install -r requirements.txt
python vault_runner.py
```

GLUT has to be installed too. On Linux run `sudo apt install freeglut3-dev`.

## Team

Built by **Yahia Rabbi**, **Aloke Ankur** and **ASM Najmus Sakib Khan**.
