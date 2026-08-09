# worldedit_tab/gif_command_blocks/converter.py
"""
Turns a GIF into an animated command-block wall: each frame is a FULL
WALL of command blocks (and stone, for pixels that didn't change), and
consecutive walls are connected by a repeater relay -- not a per-pixel
column (an earlier version of this did that; it was wrong, rebuilt from
scratch around your worked coordinate example).

Concretely, for a picture with rows at world Y = -61..-57 (5 rows) and
facing such that the picture's "depth" axis is world X:

    X=0:  the whole wall for frame 0 (every row, every column)
    X=1:  repeater relay (see below)
    X=2:  the whole wall for frame 1
    X=3:  repeater relay (if only 1 tick of delay is needed; more ticks
          means more relay columns, e.g. X=1..3 for 3 repeaters, and the
          next wall starts at X=4)
    X=4:  the whole wall for frame 2
    ... and so on -- each wall is frame_spacing = 1 + num_repeaters
    columns after the previous one.

THE RELAY DOESN'T NEED A REPEATER ON EVERY ROW. A repeater hard-powers
the block it's pointed at; that hard-powered block then SOFT-powers its
own neighbors (above, below, left, right) too. So only every OTHER row
(0, 2, 4, ... counting from the bottom) gets its own dedicated repeater
chain -- each repeater needs a solid block directly beneath it (quartz)
to be placed at all, so each one gets its own quartz support one Y level
down. The skipped rows in between (1, 3, 5, ...) get triggered for free:
they're vertically sandwiched between two hard-powered rows, so they
pick up soft power from both neighbors without needing any relay
hardware of their own. This roughly halves the repeater count. This
happens once, right where the relay reaches the next wall -- the skipped
rows don't carry a relay chain forward themselves; every wall's skipped
rows are freshly soft-powered from that same wall's own primary rows
every time.

Repeaters in a straight multi-tick chain (delay1, delay2, ... along the
depth axis, same row) work exactly like any ordinary repeater chain --
each one's hard-powered output directly feeds the next repeater behind
it, no special handling needed beyond "each one needs its own quartz
support directly underneath."

STORAGE vs DISPLAY -- these are two different things, and it's worth
being explicit about which is which after getting this backward once
already. The command blocks and repeaters described above (X=0, X=1,
X=2, ...) are the STORAGE structure -- where the redstone circuitry and
the frame data physically live. The DISPLAY target -- the actual world
position the picture appears at -- is a SEPARATE, FIXED location
(corners["depth"], the same for every frame). Every frame's command
blocks setblock to that one fixed spot, overwriting whatever the
previous frame put there; only the storage position (which command
block fires when) advances with the frame index. A pixel that had a
real block in the previous frame and is transparent in the current one
gets an explicit `setblock <target> minecraft:air` (clearing it), not
silently skipped -- and the very first frame always emits an explicit
command for every non-transparent pixel (and air for transparent ones),
regardless of whatever happened to already be at that world position
before the schematic was ever placed.

Repeater facing: my first guess here (facing = the compass direction
the depth axis increases in) was backward -- confirmed by you testing
it and getting the animation playing last-frame-to-first, meaning the
relay was firing correctly, just in reverse. Flipped to the opposite
compass direction (north/west instead of south/east) below. Worth
noting this is the SECOND time a facing guess needed this exact flip
(the earlier per-pixel-column design had the same issue), which is a
good sign it's a consistent, fixable pattern rather than a coincidence
-- but still empirically-derived rather than something I can rederive
from first principles with full confidence.

Unlike a per-pixel vertical stack, there's no meaningful world-height
ceiling here regardless of the storage-vs-display distinction above:
long animations grow the STORAGE structure along X/Z (Minecraft's build
limits there are enormous) rather than Y (capped at ~384 blocks), which
is why this design scales so much better for GIFs and especially for
video.
"""

from PIL import Image, ImageSequence, ImageOps
from nbtlib.tag import Compound, Int, Short, IntArray, List

from ..common.schem_io import command_block_state, make_command_block_entity, build_block_data

AIR_BLOCK = "minecraft:air"
STONE_BLOCK = "minecraft:stone"
QUARTZ_BLOCK = "minecraft:quartz_block"


def load_gif_frames(path: str):
    """Returns (frames: list[Image RGBA], native_fps: float). native_fps
    is derived from the GIF's own per-frame duration metadata (averaged,
    since GIFs can vary frame to frame)."""
    im = Image.open(path)
    frames = []
    durations = []
    for frame in ImageSequence.Iterator(im):
        normalized = ImageOps.exif_transpose(frame)
        frames.append(normalized.convert("RGBA"))
        durations.append(frame.info.get("duration", 100) or 100)  # ms; GIFs sometimes store 0

    if not frames:
        raise ValueError("No frames found in that file.")

    avg_duration_ms = sum(durations) / len(durations)
    native_fps = 1000.0 / avg_duration_ms if avg_duration_ms > 0 else 10.0
    return frames, native_fps


def decompose_ticks(total_ticks: int):
    """Break a total tick delay into a sequence of 1-4-tick repeater
    delays (greedy, maximizing each repeater's delay to minimize how
    many repeaters are needed in the chain)."""
    total_ticks = max(1, int(total_ticks))
    delays = []
    remaining = total_ticks
    while remaining > 0:
        d = min(4, remaining)
        delays.append(d)
        remaining -= d
    return delays


def compute_frame_plan(native_fps: float, tick_rate: float, target_fps: float,
                        show_all_frames: bool) -> dict:
    """Works out how many redstone ticks belong between frames to hit
    `target_fps` (defaults to the GIF's own native_fps to preserve its
    original timing, but you can set it to anything) at your server's
    `tick_rate` (ticks/second -- 20 = vanilla; 1 redstone tick = 2 of
    these, so redstone-ticks/second = tick_rate / 2).

    Source frames are skipped ONLY if target_fps can't be represented
    with at least a 1-tick gap at this tick_rate (i.e. you're asking for
    faster playback than the circuit can physically achieve) -- in every
    other case every frame gets its own segment, using however many
    repeaters it takes to hit the requested timing exactly. show_all_
    frames=True forces every frame to be kept regardless (deliberate
    slow motion if the requested fps is unreachably high for this tick
    rate).
    """
    if tick_rate <= 0:
        raise ValueError("tick_rate must be positive")
    if target_fps <= 0:
        raise ValueError("target_fps must be positive")

    redstone_ticks_per_second = tick_rate / 2.0
    ticks_per_gap_ideal = redstone_ticks_per_second / target_fps

    if show_all_frames:
        keep_every_n = 1
    elif ticks_per_gap_ideal < 1:
        keep_every_n = max(1, round(1.0 / ticks_per_gap_ideal))
    else:
        keep_every_n = 1

    ticks_per_gap = max(1, round(ticks_per_gap_ideal * keep_every_n))
    achieved_fps = redstone_ticks_per_second / ticks_per_gap
    num_repeaters = len(decompose_ticks(ticks_per_gap))

    return {
        "keep_every_n": keep_every_n,
        "ticks_per_gap": ticks_per_gap,
        "achieved_fps": achieved_fps,
        "native_fps": native_fps,
        "redstone_ticks_per_second": redstone_ticks_per_second,
        "num_repeaters_per_gap": num_repeaters,
        "segment_length": 1 + num_repeaters,  # depth-axis columns per frame step
    }


def select_kept_frames(frames, keep_every_n: int):
    return frames[::max(1, keep_every_n)]


def generate_gif_command_block_schem(frame_block_grids, facing: str, corners: dict,
                                      ticks_per_gap: int, loop_count: int = 1,
                                      data_version: int = 3578) -> Compound:
    """frame_block_grids: list of block_grid (row-major list of block-id-
    or-None, row 0 = top of the picture), one per KEPT frame, all the
    same width/height.

    corners: from image_command_blocks.converter's compute_corners_
    fixed_size() / compute_corners_stretch(). corners["depth"] is frame
    0's position along the depth axis; each subsequent frame's wall sits
    `segment_length` columns further along that same axis (the picture's
    world position genuinely advances -- see the module docstring).

    ticks_per_gap: redstone ticks of delay between consecutive frames
    (from compute_frame_plan()) -- decomposed into a repeater chain per
    relay row.

    loop_count: repeats the whole frame sequence this many times, end to
    end (no re-trigger wiring back to the start -- each loop is
    physically baked in).
    """
    if not frame_block_grids:
        raise ValueError("Need at least one frame.")
    if loop_count < 1:
        raise ValueError("loop_count must be at least 1")

    target_h = len(frame_block_grids[0])
    target_w = len(frame_block_grids[0][0]) if target_h else 0
    is_ns = corners["is_ns"]
    minH = corners["minH"]
    minY = corners["minY"]
    depth0 = corners["depth"]

    num_source_frames = len(frame_block_grids)
    total_frame_steps = num_source_frames * loop_count

    repeater_delays = decompose_ticks(ticks_per_gap)
    num_repeaters = len(repeater_delays)
    segment_length = 1 + num_repeaters
    total_depth = (total_frame_steps - 1) * segment_length + 1

    # local axes: "H" = the picture's horizontal axis (matches world X for
    # north/south facing, world Z for east/west), "D" = the depth/advance
    # axis (the other one). Y is real Y throughout -- no local offset is
    # needed there except the one extra row reserved below the picture for
    # bottom-row repeater supports (see ly_offset).
    if is_ns:
        w, l = target_w, total_depth
    else:
        w, l = total_depth, target_w
    ly_offset = 1  # local Y = hy + ly_offset; local Y 0 is the reserved support row below the bottom picture row
    height = target_h + ly_offset

    # Best-effort: a repeater has to face the direction it's actually
    # relaying power in, which is the direction world_depth increases.
    # Matches an unrotated paste (local axes = world axes). Flip this if
    # the relay doesn't fire in testing -- see the module docstring.
    circuit_facing = "north" if is_ns else "west"

    cb_state = command_block_state(facing)
    palette = Compound({AIR_BLOCK: Int(0), STONE_BLOCK: Int(1), cb_state: Int(2), QUARTZ_BLOCK: Int(3)})
    repeater_index = {}
    next_index = [4]

    def get_repeater_index(delay):
        if delay not in repeater_index:
            state = f"minecraft:repeater[delay={delay},facing={circuit_facing},locked=false,powered=false]"
            palette[state] = Int(next_index[0])
            repeater_index[delay] = next_index[0]
            next_index[0] += 1
        return repeater_index[delay]

    index_layers = [[[0] * w for _ in range(l)] for _ in range(height)]  # [y][z][x], local
    block_entities = List[Compound]()

    # Rows that get a dedicated repeater relay -- every other one, counting
    # from the bottom (hy=0). The rows in between get soft-powered by these
    # for free (see module docstring).
    primary_rows = set(range(0, target_h, 2))

    _UNSET = object()  # sentinel: "no previous frame" -- distinct from None
                        # (None means "transparent this frame", a real value
                        # worth diffing against on later frames)

    prev_grid = None
    for f in range(total_frame_steps):
        actual_frame_idx = f % num_source_frames
        block_grid = frame_block_grids[actual_frame_idx]
        frame_depth_local = f * segment_length

        for row_i, row in enumerate(block_grid):
            hy = target_h - 1 - row_i  # image row 0 (top) -> top of the wall
            ly = hy + ly_offset
            for col_i, block in enumerate(row):
                prev_block = prev_grid[row_i][col_i] if prev_grid is not None else _UNSET
                changed = (prev_block is _UNSET) or (block != prev_block)

                if is_ns:
                    hx, hz = col_i, frame_depth_local
                else:
                    hx, hz = frame_depth_local, col_i

                if changed:
                    # The command's TARGET is always the same fixed world
                    # position, frame after frame -- only the physical
                    # STORAGE position (hx, ly, hz) advances with the
                    # frame. This is what makes the picture repaint in
                    # place instead of marching across the world. A pixel
                    # that went from a real block to transparent gets an
                    # explicit air command (clearing it), not silently
                    # skipped.
                    index_layers[ly][hz][hx] = 2  # command block
                    world_h = minH + col_i
                    world_y = minY + hy
                    if is_ns:
                        abs_x, abs_y, abs_z = world_h, world_y, depth0
                    else:
                        abs_x, abs_y, abs_z = depth0, world_y, world_h
                    target_block = block if block is not None else AIR_BLOCK
                    cmd = f"setblock {abs_x} {abs_y} {abs_z} {target_block}"
                    block_entities.append(make_command_block_entity((hx, ly, hz), cmd))
                else:
                    index_layers[ly][hz][hx] = 1  # stone filler -- nothing changed, no command needed

                if f < total_frame_steps - 1 and hy in primary_rows:
                    for r, delay in enumerate(repeater_delays):
                        rd = frame_depth_local + 1 + r
                        if is_ns:
                            rhx, rhz = col_i, rd
                        else:
                            rhx, rhz = rd, col_i
                        index_layers[ly][rhz][rhx] = get_repeater_index(delay)
                        index_layers[ly - 1][rhz][rhx] = 3  # quartz support, directly beneath

        prev_grid = block_grid

    block_data = build_block_data(w, height, l, lambda x, y, z: index_layers[y][z][x])

    return Compound({
        "Version": Int(2),
        "DataVersion": Int(data_version),
        "Width": Short(w),
        "Height": Short(height),
        "Length": Short(l),
        "PaletteMax": Int(len(palette)),
        "Palette": palette,
        "BlockData": block_data,
        "BlockEntities": block_entities,
        "Offset": IntArray([0, 0, 0]),
        "Metadata": Compound({}),
    })
