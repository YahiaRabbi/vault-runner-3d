# Tools

Everything here works on the **real game file** (`vault_runner.py`). Nothing is mocked.

| Folder | What it does | Run |
|---|---|---|
| [`playtest/`](playtest) | Plays the game headless and checks that it behaves correctly (32 checks + 2 bug reproductions) | `python tools/playtest/logic_test.py` |
| [`recording/`](recording) | An autopilot plays each feature while every frame is captured, then the clips get captions, title cards and GIFs | `python tools/recording/director.py` then `python tools/recording/finish.py` |
| [`soundtrack/`](soundtrack) | Generates the original synthwave music for the videos, entirely in code | `python tools/soundtrack/music.py` |

## Playtest

```bash
python tools/playtest/logic_test.py    # 32 gameplay checks, exits 1 on any failure
python tools/playtest/boss_test.py     # can the boss's bullets hit the player?
python tools/playtest/hunter_test.py   # can a hunter be shot at point blank?
```

These tests found the four bugs fixed in [#5](https://github.com/YahiaRabbi/vault-runner-3d/pull/5).

## Recording pipeline

```
director.py  ->  build/raw/*.mp4          (one clip per feature, fixed 30 fps)
finish.py    ->  build/out/*.mp4, *.gif   (captions, minimap zoom, title cards, cuts)
music.py     ->  music_*.wav              (soundtrack, synced to the cuts)
```

The autopilot finds paths with BFS over the maze grid, turns smoothly toward each waypoint, and aims before firing. Because time is stepped at exactly 1/30 s per frame, the videos are smooth even when rendering is slow.

On a headless Linux machine, give it a virtual display:

```bash
xvfb-run -a -s "-screen 0 1280x1024x24" python tools/recording/director.py
```

## Soundtrack

`music.py` synthesizes every sound with NumPy (no samples): band-limited sawtooth pads, bass, arpeggios and lead, drums made of sine sweeps and filtered noise, convolution reverb, and kick sidechain ducking. The tempo is solved per video so a bar line lands on the end of the intro and the drop hits on the first frame of the boss fight.

## Requirements

```bash
pip install -r tools/requirements.txt
```

You also need `ffmpeg` (with `drawtext`) and the Inter font family for `finish.py`.
