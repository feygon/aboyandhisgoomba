# A Boy And His Goomba

A one-lane level editor for the browser.

It borrows its shape from the Design mode in *Excitebike* — a numbered piece
palette, a cursor that travels a fixed-length track, a stamp action, and a
whole-track overview strip.

It drops the lanes. It replaces the track pieces with 16-pixel tiles.

**One file. No build step. No dependencies. No network.**
Open `index.html` in Chrome and it runs.

---

## Contents

1. [Quick start](#1-quick-start)
2. [What it does](#2-what-it-does)
3. [The three planes](#3-the-three-planes)
4. [Shapes that snap together](#4-shapes-that-snap-together)
5. [Construct slots](#5-construct-slots)
6. [Actors](#6-actors)
7. [Landmarks](#7-landmarks)
8. [Background flair](#8-background-flair)
9. [Levels and playlists](#9-levels-and-playlists)
10. [Undo](#10-undo)
11. [Sound](#11-sound)
12. [Keyboard reference](#12-keyboard-reference)
13. [Saving your work](#13-saving-your-work)
14. [File layout](#14-file-layout)
15. [Known gaps](#15-known-gaps)
16. [Artwork and licensing](#16-artwork-and-licensing)

---

## 1. Quick start

Open `index.html` in a browser. That's it.

Try this first:

1. Pick **Brick** from the palette.
2. Click and drag to draw a wide, tall wall.
3. Watch a crenellated building appear behind it.
4. Press `Tab` to switch planes and see the two depths separate.

To save, press **Export project**. To come back later, press **Import
project** and pick the file you saved.

---

## 2. What it does

> **In short:** you paint a side-scrolling level onto a 256-column grid,
> across three depth planes, using shapes that grow one tile at a time. You
> can save your favourite shapes, organise levels into playlists, and export
> everything as one JSON file.

The track is **256 columns wide** and **12 rows tall**. Every tile is
16 × 16 pixels — the same size as a brick in a mid-1980s platformer.

You never scroll off the end. The track length is fixed, like an Excitebike
course. The strip under the canvas shows the whole thing at once, one pixel
per column, with a bracket marking where you are.

The canvas renders at native resolution and scales up with hard pixel edges.
You can widen the view from 12 to 32 columns using the buttons above it.

---

## 3. The three planes

> **In short:** Back, Front, and Actors. `Tab` cycles between them. The back
> plane is tinted blue to look distant.

**Back** holds scenery — hills, clouds, distant buildings.

**Front** holds the terrain you'd actually stand on.

**Actors** holds enemies. Only actors go here.

Everything on the back plane is drawn from a **second, pre-tinted copy** of
its artwork. It is blended 42% toward the sky colour and flattened slightly
in contrast.

That is atmospheric perspective, and it is baked into the artwork rather than
applied as a screen effect. So a background brick wall still looks distant in
an exported PNG, not just while you are editing.

The plane you are *not* editing is dimmed a little on top of that. The dim is
a focus cue. The tint is the depth.

---

## 4. Shapes that snap together

> **In short:** a shape is a set of tiles, not a fixed sprite. Drop a 1×1 bit
> next to a matching shape and it joins, and the seam re-tiles itself.

There are five growable families:

| Family | Made of | Notes |
|---|---|---|
| Ground | Turf, Earth | Turf grows grass on any exposed top |
| Brick | Brick, Merlon | Merlons are the crenellation caps |
| Bush | Leaf | |
| Tree | Leaf, Trunk | Cascades — see below |
| Hill | Mound | |

Each family stamps a default shape. After that you grow it by hand with the
**1×1 bits** at the bottom of the palette.

### How the edges work

Every tile picks its own appearance from a **4-bit neighbour mask** — is
there a matching tile north, east, south, west? That's 16 variants per
material, all generated at startup from one corner-carving routine.

The practical result: grow a bush sideways and the seam closes. Grow it
upward and a fresh rounded top appears where the old one was. You never
place edge pieces manually.

### Trees are different

Trees **cascade**. When you erase a tile, the shape checks which tiles still
have a path to its lowest row. Anything that lost its footing falls away too.

- Cut a **leaf** → just that leaf goes.
- Cut a **branch** → the branch and every leaf on it go.
- Cut the **trunk** → the whole crown above the cut goes.

No parent-child bookkeeping is involved. Structure is read from connectivity,
so it works on lopsided trees you built by hand, not just the default one.

### Trunk height

Press `]` over a tree to raise the trunk, `[` to lower it.

Raising **lifts the canopy** and inserts a trunk tile at the top of the
column. It does not push the trunk into the ground.

### Digging pits

Plain erase peels one ground tile. Drag to carve a pit of any shape.

`Alt` + erase on ground digs out the **entire column**, top to bottom.

On any other shape, `Alt` + erase removes the whole shape.

---

## 5. Construct slots

> **In short:** build one lopsided tree, save it, stamp it forever. Eight
> slots per family.

Build something. Hover it. Press `S`.

That shape is now saved to a slot for its family. Selecting the slot makes
the stamp tool place that exact thing.

**Naming is optional.** Leave the name box blank and you get `Tree 1`,
`Hill 3`, and so on — family name plus slot number.

Slots store tile lists, not references. Placing from a slot builds a fresh
shape, so editing a stamped copy never changes the slot it came from.

`Shift` + `1`–`8` switches slots from the keyboard. Slot `✱` is always the
built-in default.

---

## 6. Actors

> **In short:** the boy, plus four enemy types. The two koopas differ only in
> what they do at a ledge.

| Actor | At a ledge | Height |
|---|---|---|
| The boy | n/a | 2 tiles |
| Goomba | Walks off | 1 tile |
| Green koopa | Walks off | 2 tiles |
| Red koopa | Turns around | 2 tiles |
| Blaster | n/a | 1–6 tiles |

**The boy** is the player's start point, and a level has exactly one. Drop a
castle into a level that has no boy and he appears at its gate facing into
the track. After that he is an ordinary actor: place him anywhere with `P`,
and clicking the cell he already stands on turns him round. Placing him
somewhere new *moves* him rather than making a second one.

The green and red koopas share one drawing routine with a swapped shell
palette. The only real difference is the `ledge` flag — exactly as it is in
the source material.

Red koopas show **amber chevrons at their feet** in the editor so you can
tell them apart at a glance. The chevrons are an editor overlay and do not
appear in exported images.

The behaviour flag is exported with every actor, so a runtime built on top of
this can read it directly.

**Blasters** have adjustable barrel height on `[` and `]` — the same keys as
tree trunks.

Re-placing any actor on its own tile **flips which way it faces**.

---

## 7. Landmarks

A **castle** marks the start. A **flagpole** marks the end.

Both are unique. Placing a second one moves the first rather than creating a
duplicate.

A new level starts with the castle near column 3 and the flagpole near column
248. Move them wherever you like.

---

## 8. Background flair

> **In short:** wide, tall brick walls in front automatically grow a
> crenellated building behind them.

Any front-plane brick shape at least **4 columns wide and 3 rows tall** (both
adjustable) generates a matching building on the back plane.

The building is one column wider on each side, two rows taller, and topped
with merlons on alternating columns. The gaps between merlons are the
embrasures — no second tile type needed.

Generated shapes are tagged internally. Rebuilding only touches those, so
**hand-placed background work is never overwritten**.

Toggle it off with the **Auto** button and the generated buildings disappear.
Toggle it back on and they return.

---

## 9. Levels and playlists

> **In short:** a project holds many named levels. A playlist is a named,
> ordered list of them.

Levels get names you can edit. New, Duplicate and Delete all work from the
Levels panel.

Playlists reference levels **by id, not by position**. Delete a level and it
removes itself cleanly from every playlist instead of silently repointing at
whatever moved into its slot.

In a playlist you can reorder with the arrows, jump to a level with **Open**,
or remove it from the list with **✕** — which does not delete the level
itself.

One export covers everything: levels, playlists, and all forty construct
slots.

---

## 10. Undo

`Ctrl` + `Z` undoes. `Ctrl` + `Shift` + `Z` redoes. Eighty steps deep.

**A drag is one step,** not thirty. Snapshots are taken once per gesture.

### How it works

Items are treated as immutable. A snapshot is three shallow array copies —
pointers only, no tile data.

Every edit replaces the one item it touches with a clone and leaves every
other item shared with every snapshot that already holds it.

The cost of a snapshot is therefore the *number of objects* in the level, not
the number of tiles. The 512-tile ground shape gets copied once per stroke
that touches it, rather than once per undo step.

**This invariant is load-bearing.** Any new code path that edits an item
without going through `mutable()` will silently corrupt both the undo history
and any duplicated level that shares that item.

---

## 11. Sound

Every sound is generated at runtime with the **Web Audio API**. Nothing is
fetched or bundled.

Web Audio is not MIDI. MIDI is a control protocol — it carries no sound, and
something downstream has to interpret it. Web Audio computes the samples
directly, so the output is identical everywhere.

The voice set is deliberate: square, triangle and sawtooth oscillators plus
one filtered noise buffer. That is the same set of channels an NES had, so
the audio sits in the same world as the pixels.

Mute with the button in the header.

---

## 12. Keyboard reference

### Choosing what to place

| Key | Does |
|---|---|
| `1`–`5` | Ground, Brick, Bush, Tree, Hill |
| `6` | Cloud |
| `C` | Castle |
| `F` | Flagpole |
| `7`–`9` | Goomba, Green koopa, Red koopa |
| `B` | Blaster |
| `P` | The boy (start point) |
| `Q` `W` `E` `R` `U` `T` `Y` | Leaf, Mound, Trunk, Brick, Merlon, Turf, Earth bits |
| `0` | Eraser |
| `Shift` + `1`–`8` | Pick a construct slot |

### Moving and editing

| Key | Does |
|---|---|
| `←` `→` | Move the cursor |
| `Shift` + `←` `→` | Move eight columns |
| `↑` `↓` | Move up and down |
| `Home` / `End` | Jump to the start or end |
| `Tab` | Next plane |
| `Space` | Place |
| `X` | Erase |
| `Alt` + erase | Whole shape, or a full column of ground |
| `[` `]` | Trunk or barrel height |
| `S` | Save the shape under the cursor to a slot |
| `Ctrl` + `Z` | Undo |
| `Ctrl` + `Shift` + `Z` | Redo |

### Mouse

- **Click** places. **Drag** paints, but only with 1×1 bits — dragging a
  whole construct would carpet the track.
- **Right-click** erases. **Right-drag** erases continuously.
- **Click the ruler** to jump to that column, or **hold and drag along it**
  to scrub the whole track.
- **Middle-drag** on the canvas pans. You grab the track and slide it, the
  way a hand tool works.
- **Wheel** zooms through the same four view widths as the View buttons —
  12, 16, 24, 32 columns. It zooms around the column under the pointer, so
  the tile you are pointing at stays put.

---

## 13. Saving your work

There is **no autosave**. Nothing is written to browser storage.

Use **Export project** to download a JSON file. Use **Import project** to
load it back.

Three buttons write files, and they all write the same format, so anything
saved here loads back through **Import project**:

| Button | Writes |
|---|---|
| **Export project** | Everything — all levels, all playlists, all constructs |
| **Save level** (yellow diskette) | Just the level you are looking at |
| **Save playlist** (blue diskette) | The current playlist and the levels in it |

**The Constructs panel's `S` button is a different kind of save.** It stores
the shape under the cursor in one of eight reusable slots, in memory. It
writes nothing to disk. It is labelled **To slot** to keep the two apart —
until you export, a captured construct is as unsaved as everything else.

**Level PNG** exports the current level as a single 4096 × 192 image.

Older save files from v1 through v5 still import. Piece sizes changed between
versions, so an old file converts to something close rather than identical.
Re-save anything you care about.

---

## 14. File layout

```
index.html          The editor. Everything is in here.
LICENSE             MIT.
README.md           This file.
versions/           Every earlier build, oldest to newest.
structure-notes.py  Architectural sketch of a platformer runtime.
                    Not wired to the editor — reference only.
```

`structure-notes.py` is the class hierarchy, update order and collision
contracts for a runtime that could eventually play these levels. It is a
design document written as code, not a working game.

---

## 15. Known gaps

Honest list of what is missing or fragile:

- **No runtime.** This edits levels. Nothing plays them yet.
- **No autosave.** Close the tab without exporting and the work is gone.
- **Flair rebuild is not incremental.** It rescans the whole foreground on
  every edit. Fine at a few hundred objects; the first thing to fix if the
  track gets much longer.
- **The palette is at capacity.** Nineteen tools in a 232-pixel column. One
  more content type and it needs collapsible sections.
- **Snapping picks the topmost match.** Dropping a bit into a pile of
  overlapping shapes joins whichever is visually on top, which is not always
  the one you meant.
- **Mobile is untested.** Pointer events should work, but the layout is built
  for a desktop window.

---

## 16. Artwork and licensing

**All artwork is generated procedurally at startup.** There are no image
files anywhere in this repository. Every tile and sprite is drawn with
rectangle fills into an off-screen canvas when the page loads.

The designs are **original**. The goomba is a dome with angry brows and two
feet because that is what the brief asked for, not because it is anyone
else's sprite data. The same goes for the koopas, the blaster, the castle and
the flagpole.

No ROM data, level data, or ripped assets are included.

The code is MIT licensed — see `LICENSE`.

The *ideas* being referenced — Excitebike's design mode, a side-scrolling
platformer's visual vocabulary — belong to Nintendo. This is a tool built in
that idiom, which is a different thing from a copy of it, but worth being
clear-eyed about if you ever publish anything made with it.
