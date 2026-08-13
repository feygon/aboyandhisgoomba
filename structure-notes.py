"""
smb_structure.py — Architectural skeleton of a Super Mario Bros.-style platformer.

SCOPE
    This is *structure*, not a playable game: class hierarchy, ownership,
    update order, and the collision/state contracts that make a 2D platformer
    behave correctly. Bodies are stubbed or minimally implemented where the
    implementation is the interesting part.

NOT INCLUDED (deliberately)
    Nintendo assets, level data, or ROM-derived tables. Physics constants below
    are hand-tuned approximations in pixels/frame, NOT the original's
    fixed-point subpixel values.

RENDERING BACKEND
    Written against pygame's API shape (Surface, Rect, event queue), but the
    backend is isolated behind Renderer / InputMap so it can be swapped.

UPDATE ORDER (per fixed tick) — order matters, changing it changes game feel:
    1. input       -> intent flags
    2. actors      -> apply intent to velocity
    3. physics X   -> move + resolve horizontal tile collisions
    4. physics Y   -> move + resolve vertical tile collisions (sets on_ground)
    5. actor-actor -> stomps, damage, pickups
    6. spawner     -> activate/despawn by camera window
    7. camera      -> follow (after positions are final)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterable, Optional


# =============================================================================
# 1. CONSTANTS
# =============================================================================

TILE = 16
SCREEN_W, SCREEN_H = 256, 240      # NES resolution; scale at blit time
TICK_HZ = 60                       # fixed timestep; decouple from render rate
DT = 1.0 / TICK_HZ


class Physics:
    """Tuned in pixels/frame and pixels/frame^2. Signs: +y is DOWN."""
    WALK_ACCEL = 0.10
    RUN_ACCEL = 0.16
    MAX_WALK = 1.5
    MAX_RUN = 2.5
    FRICTION = 0.12
    SKID_DECEL = 0.25              # decel when input opposes velocity
    AIR_CONTROL = 0.08

    GRAVITY = 0.45
    GRAVITY_HELD = 0.22            # lower gravity while jump button held
    JUMP_IMPULSE = -4.0
    JUMP_IMPULSE_RUN = -5.0        # jump height scales with horizontal speed
    MAX_FALL = 4.5

    COYOTE_TICKS = 4               # grace frames to jump after leaving ledge
    JUMP_BUFFER_TICKS = 6          # grace frames to buffer an early press


# =============================================================================
# 2. CORE VALUE TYPES
# =============================================================================

@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0


@dataclass
class AABB:
    """Axis-aligned box. Position is top-left. Collision primitive for everything."""
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float: return self.x + self.w

    @property
    def bottom(self) -> float: return self.y + self.h

    def intersects(self, other: "AABB") -> bool:
        return (self.x < other.right and self.right > other.x
                and self.y < other.bottom and self.bottom > other.y)


class Facing(Enum):
    LEFT = -1
    RIGHT = 1


# =============================================================================
# 3. INPUT
# =============================================================================

@dataclass
class Intent:
    """Backend-agnostic frame intent. Actors read this, never raw key codes."""
    move_x: int = 0            # -1, 0, 1
    run: bool = False
    jump_pressed: bool = False # edge
    jump_held: bool = False    # level
    crouch: bool = False


class InputMap:
    """Translates backend events into Intent. Swap for AI/replay/netcode."""

    def poll(self) -> Intent:
        raise NotImplementedError


class ReplayInput(InputMap):
    """Deterministic playback — only sound if the sim is fixed-timestep."""

    def __init__(self, frames: list[Intent]) -> None:
        self._frames, self._i = frames, 0

    def poll(self) -> Intent:
        ...


# =============================================================================
# 4. TILEMAP / LEVEL
# =============================================================================

class TileType(Enum):
    EMPTY = auto()
    SOLID = auto()          # ground, bricks
    PLATFORM = auto()       # one-way: solid only from above
    BRICK = auto()          # breakable if player is big
    QUESTION = auto()       # spawns item on head-bump
    USED = auto()           # spent question block
    PIPE = auto()
    FLAGPOLE = auto()
    HAZARD = auto()         # lava / spikes


SOLID_TYPES = {TileType.SOLID, TileType.BRICK, TileType.QUESTION,
               TileType.USED, TileType.PIPE}


@dataclass
class Tile:
    type: TileType
    contents: Optional[str] = None   # "coin", "mushroom", "star", "1up"
    hit_animation: int = 0           # bump offset countdown


class TileMap:
    """Column-major grid. The only source of static-world truth."""

    def __init__(self, width_tiles: int, height_tiles: int) -> None:
        self.w, self.h = width_tiles, height_tiles
        self.grid: list[list[Tile]] = []

    def at_px(self, px: float, py: float) -> Tile:
        """World pixel -> tile. Hot path; keep it arithmetic, not search."""
        ...

    def tiles_overlapping(self, box: AABB) -> Iterable[tuple[int, int, Tile]]:
        """Yield only the tiles in the box's footprint (typically 2x2..3x3)."""
        ...

    def is_solid(self, tile: Tile, moving_down: bool) -> bool:
        if tile.type is TileType.PLATFORM:
            return moving_down          # one-way
        return tile.type in SOLID_TYPES

    def bump(self, tx: int, ty: int, actor: "Actor") -> None:
        """Head-bump from below: break brick, pop question block, kill enemies above."""
        ...


@dataclass
class Level:
    tilemap: TileMap
    spawn_points: list["SpawnPoint"] = field(default_factory=list)
    player_start: Vec2 = field(default_factory=Vec2)
    time_limit: int = 400
    theme: str = "overworld"

    @classmethod
    def load(cls, path: str) -> "Level":
        """Parse level definition (JSON/Tiled). Keep authoring data out of code."""
        ...


@dataclass
class SpawnPoint:
    """Enemies exist as data until the camera window reaches them."""
    x: float
    y: float
    kind: str
    spawned: bool = False


# =============================================================================
# 5. ACTORS
# =============================================================================

class Actor(ABC):
    """Anything with a box, a velocity, and a stake in collisions."""

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        self.box = AABB(x, y, w, h)
        self.vel = Vec2()
        self.facing = Facing.RIGHT
        self.on_ground = False
        self.alive = True
        self.solid_to_world = True     # False for e.g. death-falling enemies

    @abstractmethod
    def update(self, intent: Intent, world: "World") -> None:
        ...

    def on_collide_actor(self, other: "Actor", world: "World") -> None:
        """Default: no interaction. Dispatch lives in CollisionSystem."""
        return


# ---- Player ----------------------------------------------------------------

class PowerState(Enum):
    SMALL = auto()
    BIG = auto()
    FIRE = auto()

    @property
    def height(self) -> int:
        return TILE if self is PowerState.SMALL else TILE * 2


class MotionState(Enum):
    IDLE = auto()
    WALK = auto()
    RUN = auto()
    SKID = auto()
    JUMP = auto()
    FALL = auto()
    CROUCH = auto()
    CLIMB = auto()
    DEAD = auto()


class Player(Actor):
    """Two orthogonal state machines: power (what I am) and motion (what I'm doing)."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, w=12, h=TILE)
        self.power = PowerState.SMALL
        self.motion = MotionState.IDLE
        self.invuln_ticks = 0
        self.coyote = 0
        self.jump_buffer = 0
        self.star_ticks = 0

    # -- intent -> velocity --------------------------------------------------
    def update(self, intent: Intent, world: "World") -> None:
        self._apply_horizontal(intent)
        self._apply_jump(intent)
        self._apply_gravity(intent)
        self._resolve_motion_state(intent)
        self._tick_timers()

    def _apply_horizontal(self, intent: Intent) -> None:
        """Accel toward target speed; skid decel if input opposes velocity."""
        ...

    def _apply_jump(self, intent: Intent) -> None:
        """Consume jump_buffer if coyote > 0. Impulse scales with |vel.x|."""
        ...

    def _apply_gravity(self, intent: Intent) -> None:
        """Variable jump height: GRAVITY_HELD while rising and button held."""
        ...

    def _resolve_motion_state(self, intent: Intent) -> None:
        """Derived, not authoritative — motion state is for animation + sfx."""
        ...

    def _tick_timers(self) -> None:
        ...

    # -- power transitions ---------------------------------------------------
    def grow(self, to: PowerState) -> None:
        """Resize box upward (feet stay planted) or the player clips into ground."""
        ...

    def take_damage(self, world: "World") -> None:
        """FIRE/BIG -> shrink + i-frames. SMALL -> die. No-op if invuln or star."""
        ...

    def die(self, world: "World") -> None:
        ...


# ---- Enemies ---------------------------------------------------------------

class Enemy(Actor):
    """Shared contract: stompable?, what happens on side contact."""
    stompable = True
    points = 100

    def on_stomped(self, player: Player, world: "World") -> None:
        self.alive = False

    def on_side_contact(self, player: Player, world: "World") -> None:
        player.take_damage(world)

    def on_shell_hit(self, shell: "KoopaShell", world: "World") -> None:
        self.alive = False


class Goomba(Enemy):
    """Walks, reverses at walls and (optionally) ledges. Squash-then-despawn."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, TILE, TILE)
        self.vel.x = -0.5
        self.squash_ticks = 0

    def update(self, intent: Intent, world: "World") -> None:
        ...


class KoopaShellState(Enum):
    WALKING = auto()
    SHELL_IDLE = auto()
    SHELL_SLIDING = auto()
    RECOVERING = auto()


class Koopa(Enemy):
    """Three-phase enemy — the classic case for per-actor sub-state."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, TILE, TILE + 8)
        self.state = KoopaShellState.WALKING

    def on_stomped(self, player: Player, world: "World") -> None:
        """WALKING -> SHELL_IDLE; SHELL_IDLE -> SLIDING away from player."""
        ...


class KoopaShell(Actor):
    """Sliding shell is a projectile that damages enemies AND the player."""
    ...


# ---- Items -----------------------------------------------------------------

class Item(Actor):
    def on_pickup(self, player: Player, world: "World") -> None:
        raise NotImplementedError


class Mushroom(Item):
    """Emerges from a block (scripted rise), then behaves like a walker."""
    ...


class FireFlower(Item):
    ...


class Coin(Item):
    ...


class Fireball(Actor):
    """Player projectile: bounces off floors, dies on wall/enemy contact, max 2 live."""
    ...


# =============================================================================
# 6. SYSTEMS
# =============================================================================

class PhysicsSystem:
    """Move-and-resolve, one axis at a time. Combining axes causes corner snags."""

    def step(self, actor: Actor, tilemap: TileMap) -> None:
        self._move_x(actor, tilemap)
        self._move_y(actor, tilemap)

    def _move_x(self, actor: Actor, tilemap: TileMap) -> None:
        """Translate on X, then push out of any solid tile along X only."""
        ...

    def _move_y(self, actor: Actor, tilemap: TileMap) -> None:
        """Translate on Y, push out, set on_ground, trigger tilemap.bump() on head hit."""
        ...


class CollisionSystem:
    """Actor-vs-actor. Broad phase then pairwise dispatch."""

    def resolve(self, actors: list[Actor], world: "World") -> None:
        for a, b in self._candidate_pairs(actors):
            if a.box.intersects(b.box):
                self._dispatch(a, b, world)

    def _candidate_pairs(self, actors: list[Actor]):
        """Spatial hash or sweep-and-prune. Naive O(n^2) is fine at NES entity counts."""
        ...

    def _dispatch(self, a: Actor, b: Actor, world: "World") -> None:
        """
        Player vs Enemy is the one rule that must be exactly right:
        stomp iff player.vel.y > 0 AND player.box.bottom is above enemy's midline
        at the START of the tick. Testing only overlap gives false stomps on
        side contact.
        """
        ...


class Camera:
    """Follows player; clamps to level bounds. Classic SMB: x is monotonic (never scrolls back)."""

    def __init__(self, level_width_px: int) -> None:
        self.x = 0.0
        self.y = 0.0
        self.level_width = level_width_px

    def follow(self, player: Player) -> None:
        ...

    def to_screen(self, box: AABB) -> tuple[int, int]:
        return int(box.x - self.x), int(box.y - self.y)

    @property
    def window(self) -> AABB:
        return AABB(self.x, self.y, SCREEN_W, SCREEN_H)


class Spawner:
    """Activates SpawnPoints entering the camera window; culls actors far behind it."""

    ACTIVATE_MARGIN = TILE * 2
    DESPAWN_MARGIN = TILE * 4

    def update(self, world: "World") -> None:
        ...

    def _make(self, kind: str, x: float, y: float) -> Actor:
        """Factory. Registry dict beats an if/elif chain once you have >5 kinds."""
        ...


class Renderer:
    """Draw order: background -> tiles -> items -> enemies -> player -> effects -> HUD."""

    def draw(self, world: "World", camera: Camera) -> None:
        ...

    def draw_hud(self, score: int, coins: int, world_name: str, time_left: int) -> None:
        ...


class AudioSystem:
    def play_sfx(self, name: str) -> None: ...
    def play_music(self, track: str, loop: bool = True) -> None: ...
    def set_tempo(self, multiplier: float) -> None:
        """Speeds up when time_left < 100."""
        ...


# =============================================================================
# 7. WORLD — owns level + actors; the object systems mutate
# =============================================================================

class World:
    def __init__(self, level: Level) -> None:
        self.level = level
        self.tilemap = level.tilemap
        self.player = Player(level.player_start.x, level.player_start.y)
        self.actors: list[Actor] = [self.player]
        self.camera = Camera(level.tilemap.w * TILE)

        self.physics = PhysicsSystem()
        self.collisions = CollisionSystem()
        self.spawner = Spawner()

        self.score = 0
        self.coins = 0
        self.lives = 3
        self.time_left = level.time_limit
        self.tick_count = 0

    def update(self, intent: Intent) -> None:
        for actor in self.actors:
            actor.update(intent if actor is self.player else Intent(), self)

        for actor in self.actors:
            self.physics.step(actor, self.tilemap)

        self.collisions.resolve(self.actors, self)
        self.spawner.update(self)
        self.camera.follow(self.player)

        self.actors = [a for a in self.actors if a.alive]
        self.tick_count += 1
        if self.tick_count % TICK_HZ == 0:
            self.time_left -= 1

    def spawn(self, actor: Actor) -> None:
        self.actors.append(actor)

    def add_score(self, points: int) -> None:
        self.score += points


# =============================================================================
# 8. GAME STATES (screen-level state machine)
# =============================================================================

class GameState(ABC):
    @abstractmethod
    def update(self, intent: Intent) -> Optional["GameState"]:
        """Return the next state, or None to stay."""

    @abstractmethod
    def draw(self, renderer: Renderer) -> None:
        ...


class TitleState(GameState): ...
class LevelIntroState(GameState): ...       # "WORLD 1-1" card


class PlayState(GameState):
    def __init__(self, world: World) -> None:
        self.world = world

    def update(self, intent: Intent) -> Optional[GameState]:
        self.world.update(intent)
        if self.world.time_left <= 0 or not self.world.player.alive:
            return DeathState(self.world)
        return None

    def draw(self, renderer: Renderer) -> None:
        renderer.draw(self.world, self.world.camera)


class DeathState(GameState): ...
class LevelCompleteState(GameState): ...    # flagpole slide, time->points
class GameOverState(GameState): ...


# =============================================================================
# 9. ENTRY POINT — fixed-timestep loop with render interpolation
# =============================================================================

class Game:
    def __init__(self, input_map: InputMap, renderer: Renderer) -> None:
        self.input = input_map
        self.renderer = renderer
        self.state: GameState = TitleState()
        self.running = True

    def run(self) -> None:
        """
        Accumulator loop: simulate in fixed DT chunks so physics is
        frame-rate independent and replays stay deterministic.
        """
        accumulator = 0.0
        previous = self._now()

        while self.running:
            current = self._now()
            accumulator += min(current - previous, 0.25)   # clamp spiral-of-death
            previous = current

            while accumulator >= DT:
                intent = self.input.poll()
                nxt = self.state.update(intent)
                if nxt is not None:
                    self.state = nxt
                accumulator -= DT

            self.state.draw(self.renderer)

    @staticmethod
    def _now() -> float:
        import time
        return time.perf_counter()


if __name__ == "__main__":
    ...
