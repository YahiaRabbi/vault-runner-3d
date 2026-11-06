# Contributing

Thanks for taking a look at Vault Runner 3D! Bug reports, fixes and ideas are welcome.

## Run the game

```bash
pip install -r requirements.txt
python vault_runner.py
```

GLUT must be installed (`sudo apt install freeglut3-dev` on Linux).

## Before you open a pull request

Every change is checked by the playtest robot in CI, so please run it locally first:

```bash
python tools/playtest/logic_test.py    # must print 33/33 passed
python tools/playtest/boss_test.py
python tools/playtest/hunter_test.py
```

The tests run headless (no window), so they work over SSH and in CI.

## How we work

1. **Open an issue first** for bugs: what happened, why you think it happens, and how to reproduce it. A failing playtest is the best reproduction.
2. **One fix per commit**, on a branch (for example `fix/short-name`).
3. **Add or extend a playtest** that fails before your fix and passes after it.
4. **Open a pull request** that links the issue (`Closes #N`) and shows the before/after test results.
5. Mark changed lines with a short `# FIX:` or `# POLISH:` comment explaining *why*, like the existing ones.

## Code style

- Plain Python and PyOpenGL, no game engine. Keep it that way.
- Multiply every movement, timer and damage by `dt` so the game runs the same on every computer.
- Every `glPushMatrix()` needs a matching `glPopMatrix()`.
