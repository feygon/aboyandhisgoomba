# CLAUDE.md

Context for Claude Code sessions in this repository.

## What this is

`ABoyAndHisGoomba` — a single-file browser level editor. The whole
application is `index.html`. There is no build step, no package manager, no
dependency tree, and no server. Open the file and it runs.

`versions/v1.html` through `v6.html` are the build history. `index.html` is a
copy of `v6.html`. If you change the editor, change `index.html`; leave
`versions/` alone as a record.

`structure-notes.py` is a design document written as Python — the class
hierarchy and collision contracts for a runtime that could eventually play
these levels. It is not wired to anything and does not execute as a game.

## Immediate task

This repo was created in a sandbox with no GitHub credentials, so it was
committed but never pushed. There is one commit on `main` and no remote.

If asked to publish it:

```bash
gh repo create ABoyAndHisGoomba --private --source=. --remote=origin
git push -u origin main
```

Confirm the copyright holder in `LICENSE` before pushing. It currently reads
"Feygon Nickerson"; the operating entity may be Richard Nickerson Consulting,
LLC instead.

## Who this is for — read before making design tradeoffs

**A five-year-old.** This editor is built for the author's child to edit
levels and build things with.

**A rule a five-year-old can predict beats a rule that is authentic.** Where
the two conflict, legibility wins. Two runtime decisions already turn on this
and should not be "corrected" toward the genre by a later session:

- **Every front-plane cell is solid, whatever its material.** Trees and
  bushes would normally be scenery you run past. The rule is instead *"if you
  drew it, you can stand on it."* A child who draws a tree and cannot stand on
  it has been told the drawing lied.
- **Enemies never despawn.** Super Mario Bros. removes enemies that leave the
  screen. Here nothing the child placed disappears. *"Everything you made
  stays there"* is a rule a five-year-old can hold.

This governs the *rules*, not the *pacing* — running and jumping still follow
Super Mario Bros., via the tuned constants in `structure-notes.py`.

Corollary: **no punishing mechanics** — no lives running out, no timer, no
game over — without asking first.

Full reasoning in `docs/superpowers/specs/2026-08-13-runtime-design.md`.

## Architecture, briefly

Read `README.md` first — it is thorough and current.

The parts most likely to bite you:

**Items are immutable.** Undo works by structural sharing: a snapshot is
three shallow array copies, and every edit clones the single item it touches
via `mutable(list, i)` before modifying it. Any new code path that mutates an
item in place will silently corrupt both the undo history and any duplicated
level sharing that item. This is the one invariant the codebase depends on.

**Shapes are cell sets, not sprites.** A shape is `Map<"dx,dy", material>`
anchored at a centre column and base row. Tile appearance is chosen per cell
from a 4-bit neighbour mask (N=1 E=2 S=4 W=8) against the same material in
the same shape. All 16 variants per material are generated at boot.

**Trees cascade.** After a cell is deleted from a shape whose family has
`cascade: true`, every cell that lost its 4-connected path to the shape's
lowest row is removed too. Only `TREE` sets this flag.

**All artwork is procedural.** No image files exist. Sprites are drawn with
`fillRect` into off-screen canvases at startup, then depth-tinted copies are
generated for the back plane. Do not introduce asset files or CDN fetches;
the single-file, offline property is deliberate.

**No browser storage.** Save is an explicit JSON export. Do not add
`localStorage` — it breaks portability and is unavailable in some hosts.

## Known gaps

Listed in `README.md` section 15. The two worth acting on first:

1. No runtime. The editor produces levels nothing plays yet.
2. `rebuildFlair()` rescans the entire foreground on every edit. Fine at
   current scale, first bottleneck if `COLS` grows.

## Style

The author prefers direct, literal explanation. State what changed and why.
No filler apologies. Corrections are data, not failures. Flag fragile
assumptions explicitly rather than burying them.
