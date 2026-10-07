# NEON RAIN source contract (grey-box slice)

Modules live on `window.NR`, load in the order of `dev.html`, and talk through `NR.bus`.

| File | Owns |
|---|---|
| config.js | `NR.cfg` tuning, asset paths, `NR.bus`, `NR.rng`, `NR.clamp` |
| core.js | renderer, post pass (half-res light shafts, grade, B&W + red, grain, vignette, hurt edges, scan, focus, fade), view-model pass, loop, `core.state` |
| world.js | level builder (merged boxes, AABB colliders, cover points, rays) and the office, alley and club |
| fx.js | revolver and hat models, smoke, rain, blood (spray, wall and floor decals, wounds; milky for artificial), tracers, muzzle light |
| actors.js | painted billboard characters (8 angles + idle) and enemies with cover AI |
| player.js | movement, look, revolver, aim assist, health, lives, cigarettes, scan state, view models |
| controls.js | portrait twin-stick touch layout, WASD + mouse; `NR.controls.state` once per frame |
| audio.js | placeholder music and synthesized sfx |
| story.js | all lines, clues and interrogation data |
| ui.js | gate, title, settings, HUD, dialogue, cards, interrogation, case file, end card |
| game.js | the director: beats, scan, interact, fights, respawn, pause, case file |

States: `TITLE`, `CUTSCENE`, `PLAY`, `INTERRO`, `CASE`, `PAUSE`, `DOWN`, `END`.

Bus events: `state`, `shot`, `reload`, `reloaded`, `dryFire`, `hitEnemy`, `enemyDown`, `enemyShot`, `playerHit`, `playerHurt`, `playerDown`, `smoke`, `focus`, `focusEnd`, `clue`, `asked`, `offer`, `resize`.

Dev: `src/dev.html?beat=alley` or `?beat=club` jumps to a beat. `python src/build.py` writes `../index.html`. `python tools/prep_assets.py` rebuilds `assets/sprites/` from `art/sprites/`.
Tests: `python tests/slice_test.py [--built] [--throttle 4]`.
