# Runtime design — playing the levels

Status: rev 2, approved for planning
Date: 2026-08-13

Revision history:
- rev 1 — initial draft. Scored 29/45 at the Requirements Rubric gate; blocked
  on absent architectural constraints, no acceptance criteria, and no
  accessibility requirements.
- rev 2 — adds §2 audience, §7 architecture and function-size constraints,
  §8 data model, §11 accessibility, §12 acceptance criteria, §13 edge cases
  and failure modes. Requirements given IDs.

## 1. Why this exists

The editor produces levels that nothing plays. This adds the engine.

## 2. Who it is for, and the governing principle

**The audience is a five-year-old.** This project is built for the author's
child to edit levels and build things with.

**Governing principle: a rule a five-year-old can predict beats a rule that is
authentic.** Where they conflict, legibility wins. Two decisions below depart
from Super Mario Bros. on exactly these grounds, and both are marked.

This applies to the *rules*. It does not apply to the *pacing* — running and
jumping follow Super Mario Bros. closely, via the constants already tuned in
`structure-notes.py`.

A corollary that constrains the whole design: **no punishing mechanics.** No
lives to run out, no timer, no game over. Death costs a moment and nothing
else.

## 3. Constraints inherited from the project

Not up for renegotiation in this work:

- **C-1 Single file.** The runtime lives inside `index.html`. No asset files,
  no CDN fetches, no build step (`CLAUDE.md`).
- **C-2 All artwork procedural.** The runtime reuses sprites generated at
  boot and draws no new art.
- **C-3 No browser storage.**
- **C-4 Items are immutable.** The runtime must never mutate editor items in
  place. It compiles its own state and leaves `track` untouched. This is the
  one invariant the codebase depends on; violating it corrupts undo history
  and any duplicated level sharing an item.

## 4. Physics

Ported as written from `structure-notes.py`, pixels per frame at 60 Hz,
`+y` down.

| Constant | Value |
|---|---|
| `WALK_ACCEL` / `RUN_ACCEL` | 0.10 / 0.16 |
| `MAX_WALK` / `MAX_RUN` | 1.5 / 2.5 |
| `FRICTION` / `SKID_DECEL` | 0.12 / 0.25 |
| `AIR_CONTROL` | 0.08 |
| `GRAVITY` / `GRAVITY_HELD` | 0.45 / 0.22 |
| `JUMP_IMPULSE` / `JUMP_IMPULSE_RUN` | −4.0 / −5.0 |
| `MAX_FALL` | 4.5 |
| `COYOTE_TICKS` / `JUMP_BUFFER_TICKS` | 4 / 6 |

- **R-1** Simulation runs at a fixed 60 Hz via an accumulator, decoupled from
  render rate. Physics tuned in per-frame units are wrong at any other rate,
  and a variable step makes jump height depend on the monitor.
- **R-2** `GRAVITY_HELD` applies while the jump control is held, giving
  variable jump height.
- **R-3** Jump impulse scales with horizontal speed (`JUMP_IMPULSE` walking,
  `JUMP_IMPULSE_RUN` at run speed).
- **R-4** Coyote time and jump buffering apply as specified. These are
  forgiveness features and matter more here than usual, given §2.

## 5. The play view

- **R-5** The play view is **16 columns × 12 rows — 256 × 192 native**, scaled
  up with hard pixel edges, *regardless* of the editor's current View setting.
  The editor's 12–32 column zoom is an authoring convenience; carrying it into
  play would make the game easier at 32 columns because you see more of what
  is coming. 256 px is also the NES screen width assumed throughout
  `structure-notes.py`.
- **R-6** The camera follows the boy in both directions, clamped to
  `[0, COLS*TILE − 256]`.
  *Deviation from SMB, deliberate — confirmed by the author 2026-08-14:* SMB
  never scrolls back. Here backtracking is allowed — the level is a sandbox
  the child built and wants to look at, and trapping them past their own
  castle punishes without teaching. Do not "fix" this toward the genre.
- **R-7** Scrolling is pixel-smooth, not column-quantised. The runtime renders
  the visible column span into a buffer one tile wider than the screen and
  blits at `−(camX mod TILE)`.

## 6. Collision

### Solidity

- **R-8** **Every front-plane shape cell is solid**, whatever its material —
  turf, earth, brick, merlon, leaf, mound, trunk.
  *Deviation from the genre, deliberate:* trees and bushes would normally be
  scenery you run past. The rule chosen instead is **"if you drew it, you can
  stand on it."** A child who draws a tree and cannot stand on it has been
  told the drawing lied. One sentence, no exceptions, no material table to
  memorise. **This is the design rationale of record.**
- **R-9** Landmarks are not shape cells and behave as follows:

| Thing | Behaviour |
|---|---|
| Castle | Solid. It is a building; you can climb it. |
| Flagpole | Trigger, not a wall. Touching it wins. |
| Cloud | Pass-through scenery. |
| Anything on the back plane | Never collides. It is distance. |

### Method

- **R-10** Swept AABB against the tile grid, resolving one axis at a time,
  horizontal then vertical. A single combined resolution produces corner
  snagging.
- **R-11** The boy's collision box is **10 px wide against his 16 px sprite**,
  centred, full sprite height. Forgiving box, generous corners; same
  motivation as R-4.
- **R-12** Solidity is compiled **once at level start** into a flat
  `Uint8Array(COLS * ROWS)`, never queried against the item list per frame.
  The editor's per-item cell maps are the wrong shape for a query running 60
  times a second.

## 7. Architecture

The runtime is one fenced section of `index.html`, organised as the modules
below. These boundaries are binding on implementation.

| Module | Owns | May depend on |
|---|---|---|
| `compileLevel` | Turning editor items into runtime state | Editor read model (read-only) |
| `physics` | Constants, integration, AABB resolution | Nothing |
| `actors` | Wake rules, enemy movement, contact outcomes | `physics`, level grid |
| `runLoop` | Fixed-step accumulator, tick order, run state | `actors`, `physics` |
| `runRender` | Drawing a frame from runtime state | Sprite tables (read-only) |
| `runInput` | Key state → intent flags | Nothing |

- **R-13 Dependency direction.** Dependencies point inward. `physics` and
  `runInput` depend on nothing. Nothing in the runtime depends on
  `runRender`. **No module may write to editor state.** Circular dependencies
  between runtime modules are prohibited.
- **R-14 Business-rule isolation.** Physics integration, wake rules and
  contact outcomes must be pure functions of (state, input) with no canvas,
  DOM or event access, so each is testable without rendering a frame.
- **R-15 Function size.** Target **~100 lines or fewer** per function.
  **Any function exceeding 300 lines is a blocking defect** and must be
  decomposed before the work is considered complete. In particular, the tick
  function must not accumulate physics, actor logic and rendering inline.
- **R-16 Interface stability.** `compileLevel(track) → RunState` and
  `tick(RunState, Intent) → RunState` are the stable contracts. Rendering and
  input may change without touching simulation.
- **R-17 Extension points.** New enemy behaviours must be addable by adding a
  `ledge`/behaviour entry, not by editing a switch inside the tick. Enemy
  behaviour is driven by the `ledge` property already on each `ACTORS` entry
  (`fall` / `turn` / `none`) — the editor already records it, so the runtime
  reads it rather than duplicating a table.

## 8. Runtime data model

```
RunState {
  grid:    Uint8Array(COLS*ROWS)   // 1 = solid
  boy:     Body { x, y, vx, vy, onGround, coyote, buffer, facing }
  actors:  [ RunActor { id, x, y, vx, dir, awake, alive, tiles, ledge } ]
  spawn:   { x, y }                // for respawn
  camX:    number                  // pixels
  phase:   'playing'|'dying'|'won'
  timer:   number                  // frames remaining in phase
}
```

- **R-18** `RunState` is created by `compileLevel` and owned solely by the run
  loop. Editor state (`track`, `project`, `ed`) is **read once at compile
  time and never written**. This is C-4 applied.
- **R-19** Actor spawn positions are snapshotted at compile time so respawn
  restores them exactly.

## 9. Actors

### Activation

- **R-20** Every non-player actor starts **dormant**: it renders, so the child
  can see what is ahead, but does not move and cannot kill.
- **R-21** An actor **wakes when it enters the play view** — its column falls
  within the camera window plus a one-tile margin, so nothing visibly pops
  into motion at the screen edge.
- **R-22** **Once awake it stays awake for the rest of the run and is never
  removed**, with the single exception in R-23.
  *Deviation from SMB, deliberate:* SMB despawns enemies that leave the
  screen. Here nothing the child placed disappears. "Everything you made stays
  there" is a rule a five-year-old can hold; "some of them go away when you
  are not looking" is not.
- **R-23** The one exception: an actor that falls below the bottom row is
  marked not-alive and stops being simulated. Accepted consequence of R-22 —
  a goomba that walks into a pit would otherwise fall forever.

### Behaviour

- **R-24** Awake actor behaviour, walk speed 0.5 px/frame:

| Actor | Behaviour |
|---|---|
| Goomba | Walks in facing direction. Turns at a wall. Walks off ledges. |
| Green koopa | As goomba, 2 tiles tall. |
| Red koopa | As goomba, but turns at a ledge instead of walking off. |
| Blaster | Stationary. |

### Contact

- **R-25** One rule, no per-enemy special cases:
  - **From above** — boy is falling (`vy > 0`) and his feet are above the
    enemy's midline: the enemy is defeated and the boy bounces (`vy = −3.0`).
  - **Any other contact** — the boy dies.

  This includes the Blaster. A single rule the child can state outranks
  per-enemy nuance.

## 10. Run loop and states

- **R-26 Start.** Play validates the level (§13), compiles `RunState`, and
  enters `playing`. Editor state is not touched.
- **R-27 Tick order**, fixed per tick: input → boy physics → boy/tile
  collision → actor wake checks → actor movement and collision → contact
  resolution → camera → phase transitions.
- **R-28 Death.** Contact per R-25, or falling below the bottom row. Enters
  `dying` for **45 frames (0.75 s)**, then respawns the boy at `spawn` and
  restores every actor to its snapshotted position and dormant state.
- **R-29 No lives, no timer, no score, no game over.** Per §2. There is no
  failure state to reach, only a level to keep trying.
- **R-30 Win.** Overlapping the flagpole's column enters `won`, shows a
  completion message for **120 frames (2 s)**, then returns to the editor.
- **R-31 Exit.** `Esc` or a Stop button at any time returns to the editor with
  the level unchanged. Exiting mid-run is always safe.

### Input

- **R-32**

| Control | Does |
|---|---|
| `←` `→` | Move |
| `Space` / `↑` / `Z` | Jump |
| `Shift` | Run |
| `Esc` | Stop and return to the editor |

## 11. Accessibility

The editor announces state through a `role="status"` live region via `say()`
and labels every control. The runtime must not regress that.

- **R-33** Entering and leaving play, death, and winning are announced through
  the existing live region.
- **R-34** The Play and Stop controls are real focusable buttons with
  accessible names, reachable by keyboard.
- **R-35** Gameplay is fully keyboard-operable (R-32 is keyboard-only by
  construction). No pointer input is required to play.
- **R-36** The runtime canvas carries an `aria-label` describing the controls,
  as the editor canvas does.
- **R-37** No flashing above 3 Hz in the death or win feedback.

## 12. Acceptance criteria

Verifiable at the console or by observation. The repo has no test framework
(no `package.json`, no build step), so these are stated as checks a human or
a browser-driving agent can run.

| # | Criterion |
|---|---|
| A-1 | Boy stands on a drawn leaf tile and on a trunk tile without falling through (R-8) |
| A-2 | Nothing on the back plane blocks movement (R-9) |
| A-3 | An actor two screens to the right has `awake === false` at run start, and `awake === true` after the camera reaches it (R-20, R-21) |
| A-4 | That actor remains `awake === true` after the camera leaves it again (R-22) |
| A-5 | Play view is 256×192 regardless of whether the editor was on 12, 16, 24 or 32 columns (R-5) |
| A-6 | Camera clamps at both level ends; boy cannot leave the level (R-6) |
| A-7 | A jump held to its peak is measurably higher than a tapped jump (R-2) |
| A-8 | A jump at run speed is measurably higher than at walk speed (R-3) |
| A-9 | Leaving a ledge and pressing jump within 4 frames still jumps (R-4) |
| A-10 | Landing on an enemy from above defeats it and bounces the boy; touching it from the side kills the boy (R-25) |
| A-11 | After death, boy and every actor are back at their start positions and dormant (R-28) |
| A-12 | Touching the flagpole ends the run (R-30) |
| A-13 | After Play → Esc, a deep-equality check of the serialised level matches the pre-play serialisation exactly (C-4, R-18) |
| A-14 | Undo history depth is unchanged by a play session (C-4) |
| A-15 | No function in the runtime exceeds 300 lines (R-15) |
| A-16 | Announcements fire on entering play, dying, winning and exiting (R-33) |

## 13. Edge cases and failure modes

| Case | Required behaviour |
|---|---|
| **E-1** No boy in the level | Play refuses to start, says so. Already implemented. |
| **E-2** No flagpole | Play refuses to start, says so. Already implemented. |
| **E-3** Boy placed inside solid geometry | Push him up to the nearest free space above; if none, refuse to start and say why. Never start with him embedded. |
| **E-4** Boy placed in mid-air | Legal. He falls. |
| **E-5** Level has no ground at all | Legal. He falls, dies, respawns — an infinite but non-crashing loop the child can Esc out of. |
| **E-6** Flagpole unreachable | Not detected. Out of scope; the level is simply unwinnable. |
| **E-7** Actor placed inside solid geometry | Wakes normally, walks out if it can; if fully enclosed it stays put. Never crashes. |
| **E-8** Actor placed in mid-air | Falls to the first solid tile below. |
| **E-9** Two actors overlapping | Both simulate independently. They do not collide with each other. |
| **E-10** Boy spawns overlapping a dormant actor | Actor cannot kill while dormant (R-20), so no instant death at the castle. |
| **E-11** Window loses focus mid-run | All input released, accumulator reset to avoid a large catch-up step. |
| **E-12** Tab throttled / very long frame | Accumulator clamped to a maximum of 5 ticks per frame; simulation slows rather than tunnelling through walls. |
| **E-13** Browser tab resized during play | Canvas rescales; native resolution unchanged. |

## 14. Explicitly out of scope

Named so nobody has to guess whether they were forgotten:

- Power-ups, coins, score, lives, timer, game over
- The `PowerState` small/big mechanic sketched in `structure-notes.py`
- Blaster projectiles
- Shell mechanics for koopas (kick, slide, ricochet)
- Playlist playthrough — Play runs the current level only
- Sound during play; the editor's `sfx` set is authoring feedback
- Touch and gamepad input
- Detecting unwinnable levels (E-6)

## 15. Risks

- **`index.html` size.** Already ~1900 lines; the runtime is substantial. C-1
  stands, but this is the change that makes the file genuinely large. §7's
  module boundaries and R-15's size limit exist to keep it navigable.
- **The physics constants have never been run.** They are a written design.
  Expect a tuning pass once playable — by feel, with the child, not by
  argument.
- **R-8 versus background flair.** Flair generates shapes on the *back* plane,
  which never collides (R-9), so it should be unaffected. A-2 checks this.
- **C-4 is easy to violate by accident.** R-18 and A-13/A-14 exist to catch it.
