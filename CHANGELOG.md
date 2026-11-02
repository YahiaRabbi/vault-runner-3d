# Changelog

All notable changes to Vault Runner 3D are listed here.

## [Unreleased]

### Added
- Automated playtest suite in `tools/playtest/`: 32 headless gameplay checks (`logic_test.py`) plus two bug-reproduction scripts (`boss_test.py`, `hunter_test.py`).
- A 33rd check for held arrow keys ([#8](https://github.com/YahiaRabbi/vault-runner-3d/pull/8)).
- Continuous integration: GitHub Actions runs every playtest on each push and pull request.
- Tools to record the feature showcase (`tools/recording/`) and generate its soundtrack in code (`tools/soundtrack/`).
- Feature GIFs, per-feature clips and a 2-minute showcase video in `media/`.

### Fixed
- Boss bullet fan could never hit the player: it spawned above the player hit zone ([#1](https://github.com/YahiaRabbi/vault-runner-3d/issues/1)).
- Hunters became unkillable once they reached the player ([#2](https://github.com/YahiaRabbi/vault-runner-3d/issues/2)).
- Minimap was a mirror image of the world. It is now a true top-down view, with a smooth player dot and a heading line ([#3](https://github.com/YahiaRabbi/vault-runner-3d/issues/3)).
- Health packs were wasted at full HP, and Stage 2 started facing a wall ([#4](https://github.com/YahiaRabbi/vault-runner-3d/issues/4)).
- GLU quadric memory leak: about 50,000 objects leaked per minute of play ([#6](https://github.com/YahiaRabbi/vault-runner-3d/issues/6)).
- Holding an arrow key turned only one small step ([#7](https://github.com/YahiaRabbi/vault-runner-3d/issues/7)).

Fixes landed in [#5](https://github.com/YahiaRabbi/vault-runner-3d/pull/5) and [#8](https://github.com/YahiaRabbi/vault-runner-3d/pull/8). Playtest result: 30/32 → 33/33.

## [0.1.0] - 2026-10-30

### Added
- Vault Runner 3D: a first-person 3D maze shooter in Python + PyOpenGL/GLUT, built for CSE423 Computer Graphics.
- 4 stages, 9 features: minimap, HUD, pickups and acid hazard, maze collision with wall sliding, dual camera, keycard/gate progression, guard and alien AI, hunter AI and a two-phase boss.
