# worldedit_tab rebuild

## Fix #12 (the big one): GIF/Video command blocks rebuilt from scratch -- shared walls + relay, not per-pixel columns

The earlier design put one independent vertical repeater/quartz column
per PIXEL. That was wrong. Rebuilt around your worked coordinate
example, which is a fundamentally different, better structure:

**Each frame is a full wall** of command blocks (and stone, for pixels
that didn't change), spanning the picture's actual width and height --
not one column per pixel. Consecutive walls are `1 + num_repeaters`
columns apart along whichever axis is "depth" for the chosen facing
(X for east/west, Z for north/south), and **the picture's world
position genuinely advances frame to frame** -- confirmed against your
exact example: frame 0's wall at depth 0, a relay at depth 1, frame 1's
wall at depth 2, matching "if there is only 1 tick between frames, the
next wall would be at 2 ...".

**The relay only needs a repeater on every OTHER row.** A repeater
hard-powers the block it's pointed at; that hard-powered block then
soft-powers its own neighbors (above, below, left, right). So rows 0,
2, 4, ... (counting from the bottom) get a dedicated repeater chain
(each needing its own quartz support directly underneath, since a
repeater can't be placed without solid ground); the in-between rows
(1, 3, 5, ...) pick up soft power from both neighbors for free, no
relay hardware needed. Verified exactly against your numbers: for a
5-row wall, repeaters land at world Y -61/-59/-57 with quartz supports
at Y -62/-60/-58 -- byte-for-byte what you specified. Multi-tick delays
(more than 1 repeater needed between frames) just extend that same
primary-row pattern in a straight line along the depth axis, each
repeater still on its own quartz support, exactly like an ordinary
repeater chain.

Repeater facing matches the direction the depth axis is actually
increasing in (world_depth = corners["depth"] + frame_index × spacing).
This is my best read of the geometry, not something I can verify without
an actual placement -- flagging it explicitly since guessing wrong on
facing has bitten this project before. If the relay doesn't fire when
you test it, flipping the repeater facing front-to-back is the first
thing to try.

**Practical side effect worth knowing:** since frames now advance along
X/Z instead of stacking in Y, there's no meaningful world-height ceiling
for these tabs anymore (Minecraft's X/Z build limits are enormous). The
old "world height" warning is gone, replaced with a much softer
heads-up about total depth-axis extent (mainly about generation/paste
time for very long animations, not a hard Minecraft limit).

Verified end-to-end: reproduced your exact 5-row/101-column example and
confirmed the relay pattern matches your coordinates precisely; tested
north-facing (opposite axis mapping from your east-facing example) to
confirm the width/depth axis swap is correct either way; tested a
10-tick, 3-repeater delay chain to confirm multi-repeater relays thread
through the skip rows correctly; confirmed stone-vs-command-block
substitution and loop_count both still work correctly with the new
layout; and ran the full pipeline through the actual GIF Command Blocks
GUI (palette load, GIF load, size, generate, save, reload).

This is used by both GIF Command Blocks and Video (both call the same
`generate_gif_command_block_schem`), so this one fix applies to both
tabs.

## New dependency: OpenCV (for the Video tab)

`video_command_blocks` uses OpenCV to decode video files:

```
pip install opencv-python-headless --break-system-packages
```

(headless because this integrates into Tkinter, not OpenCV's own GUI --
avoids potential DLL/Qt conflicts on Windows). Every other tab's
dependencies are unchanged (`nbtlib`, `Pillow`).

## Fix #10 (the big one): BlockData is a varint stream, not one byte per voxel

This is what was actually causing `NullPointerException` on
`BlockStateHolder.toBaseBlock()` when loading `pixel-mario`. Confirmed
against the official Sponge Schematic Specification:

> **BlockData: `varint[]`** — "Each integer is bitpacked into a single
> byte with varint encoding... depending on the length, each proceeding
> byte is or'ed and current value bit shifted by the length multiplied
> by 7."

Every writer in this project (and every reader in Conv to cmd blocks)
was treating `BlockData` as one raw byte per voxel instead of a varint
stream. A palette index under 128 fits in exactly one varint byte,
indistinguishable from "just a byte" -- so anything with a small palette
worked fine, right up until a palette passed 128 entries. Your Mario
pixel art has 141. Index 128 needs a 2-byte varint; writing it as one
raw byte misaligns every voxel after it, and the misread eventually
lands on a byte sequence with no matching palette entry -- a null
block, which is exactly the NPE. It could also crash outright before
even producing a file: nbtlib's `ByteArray` refuses values outside
-128..127, so assigning a raw index of 128+ throws `OverflowError`.

Fixed with `build_block_data()` / `read_block_data()` in
`common/schem_io.py` -- proper varint encode/decode, used everywhere
BlockData is written or read now, including the **Conv to cmd blocks**
tab's reader (which parses schematics that could come from anywhere,
not just this app -- a real detailed WorldEdit build routinely has a
palette well past 128 blocks, so that read path had the exact same bug
in reverse).

Verified with a full round trip at Mario's exact scale (141-entry
palette, 100x67 image, all 6,700 voxels checked byte-for-byte after a
real save/load cycle) and with the Conv to cmd blocks tab reading a
synthetic 150-block external-style schematic.

**Re-generate any pixel art with a large palette** -- anything saved
before this fix has scrambled BlockData past whichever voxel first hit
palette index 128.

## Tab structure: Media Creator / Setup Tools

The old flat row of six subtabs is now two top-level tabs, each holding
its own nested Notebook:

- **Media Creator** -- Image to Pixel Art, Image Command Blocks, GIF
  Command Blocks, Video
- **Setup Tools** -- Conv to cmd blocks, Resource Pack Scanner

`worldedit_gui.py`'s `create_worldedit_schematic_gui(frame, gui)` keeps
its exact old signature; only its internals changed (a top-level
`ttk.Notebook` with two tabs, each containing its own nested `ttk.Notebook`
via a small `_nested_notebook()` helper). Every subtab's own file and
content are completely unchanged.

## Three UX fixes

**1. Palette file dialogs now pre-select the exact last-used file**, not
just open in the right folder. `common/recent_paths.py` gained
`remember_file()`/`get_initial_file_args()` alongside the existing
folder-level `remember()`/`get_dir()` -- every "Browse" for a palette
JSON (all three image-based tabs) and the Resource Pack Scanner's Save/
Load Palette buttons use this now. Falls back to the old folder-only
behavior if the exact file's been moved or deleted since. Verified: a
second dialog open correctly shows `initialfile` set to the previously
used file's name.

**2. Resource Pack Scanner: "Locate Textures for Previews..."** -- when
you load a previously-saved palette JSON, there's no way to know which
texture files the colors originally came from, so the Review window
could only show plain color swatches. This new button lets you point at
a resource pack folder; it matches each palette entry's block name
("minecraft:white_wool") to a texture file by filename ("white_wool.png")
if one exists in that folder, filling in real thumbnails for Review /
Edit Palette without touching the palette's actual colors. Works after
either loading a saved palette or scanning fresh (fills in whatever's
still missing).

**3. Text-entry fields no longer stretch.** Every path/file entry across
all six tabs had `fill="x", expand=True`, letting it grow to whatever
space its row happened to have -- removed everywhere, so every entry now
stays at its fixed character width and scrolls internally like a normal
text field (standard Tk Entry behavior once fill/expand isn't fighting
it). Verified an entry's requested width is now identical before and
after typing/pasting a much longer path.

## New: photo preview with rotate, on all three image-based tabs

**Image to Pixel Art**, **Image Command Blocks**, and **GIF Command
Blocks** now show a live preview beside the controls: the loaded
image/first GIF frame, resized (smoothly, no attempt to look blocky or
match the real block palette -- just a quick visual sanity check) to
whatever width:height ratio your current settings imply. Change the
width/height fields, toggle aspect lock, or switch Image/GIF Command
Blocks' stretch-to-fit-two-corners mode, and the preview updates live to
show exactly how squished or stretched the result will be before you
commit to a conversion.

A **Rotate 90°** button cycles the source image/GIF frames a quarter
turn at a time (all frames rotate together for GIF Command Blocks).
This isn't just a display trick -- the rotated image is what actually
gets used for the conversion. Verified this with a real generate: a
90°-rotated 4x2 image (red left column, white elsewhere) correctly
produced a 2x4 output with red on top, not just a relabeled preview.

Shared implementation in `common/image_preview.py`, reused by all three
tabs.

## Fix #11: portrait photos loaded sideways

Portrait photos (especially from phones) are very often stored with the
raw pixel data in landscape orientation, plus an EXIF `Orientation` tag
telling viewers to rotate it on display. PIL's `Image.open()` does NOT
apply that tag automatically -- so a portrait photo's raw data came out
sideways (landscape), and everything built from it followed suit.
Landscape photos usually don't carry a rotate-on-display tag at all,
which is exactly why only portraits were affected.

Fixed in `image_to_pixelart.converter.load_source_image()` with
`PIL.ImageOps.exif_transpose()`, which reads the tag and returns the
image already correctly oriented (a safe no-op for images with no
orientation tag, which is most PNGs/screenshots). This function is
shared by both **Image to Pixel Art** and **Image Command Blocks** (the
latter imports it directly), so the fix covers both. Also applied
defensively per-frame in the GIF loader, though GIFs essentially never
carry EXIF orientation data in practice.

Reproduced the exact bug first (a synthetic landscape-raw-data-plus-
rotate-tag JPEG, confirmed it loaded sideways before the fix) and
verified the fix resolves it, with no change in behavior for ordinary
images that carry no orientation tag.

## Fix history (read this if a schematic still won't load or look right)

**1. Root NBT wrapper — added by mistake, then reverted.** An early pass
wrapped every `.schem` in `{"Schematic": {...}}`. WorldEdit's actual
`SpongeSchematicReader.getBaseTag()` reads the NBT root directly with no
such wrapper — confirmed against its real source. That extra layer caused
`missing a "Version" tag`. Reverted: `save_schematic()` writes straight
to the NBT root, matching your confirmed-working `timeline_exporter`
files.

**2. BlockEntity `Id` casing.** Every block entity needs a *required*
`Id` tag (capital I). The inherited code used lowercase `"id"`, which is
a very plausible cause of the original "fails to load" report. Fixed in
`common/schem_io.py::make_command_block_entity()` — matches your working
reference file's casing.

**3. Resource-pack scan picking up non-block textures.** The scanner
turned every `.png` it found into `"minecraft:<filename>"` with no
validity check, so GUI icons, particles, and achievement frames ended up
in the palette right next to real blocks. Fixed by filtering scan
results.

**4. "Valid block" wasn't a strict enough filter.** Registry membership
isn't the right bar — torches, tripwire, saplings, slabs, stairs, doors,
anvils, and cake are all real blocks but none are full solid cubes, so
none work for a pixel-art wall. `resource_pack_scanner/valid_blocks.json`
is now the set of 430 vanilla blocks whose hitbox is a single, full
`[0,0,0]`–`[1,1,1]` cube in every state, derived from real Minecraft
1.21.3 collision-shape data (PrismarineJS/minecraft-data). Verified
against your exact texture list: 326 of ~1,032 textures pass, 706
correctly rejected.

**5. Average color drifts toward gray on high-contrast textures.** A
texture that's mostly one color plus a thin dark outline or a few
shading-noise pixels (very common — wool, concrete, etc. all do this)
averages toward a muddy gray that doesn't match anything well. Added
`_dominant_rgb()`: buckets pixels into similar-color groups first (so
anti-aliasing/dithering noise doesn't split a color into many near-
duplicates), then reports the true average *within* the most common
bucket. Tested against a synthetic "mostly white + dark outline" texture:
averaging gave `(188,188,188)` gray, dominant correctly gave `(235,235,235)`
white. **This is now the default color-matching mode** in the Resource
Pack Scanner tab, with a radio button to switch back to plain averaging
if you ever want it.

Also swapped the placeholder `DataVersion` (`4550`, not a real published
version) for `3578`, matching your confirmed-working file.

All fixes verified with actual write/read round trips and synthetic
textures reproducing the reported failure modes.

**6. `barrier` (and friends) passed the full-cube shape check but isn't
a real building material.** `barrier`, `light`, `jigsaw`, and the
command-block family all occupy a full 1x1x1 cube, so the shape filter
let them through -- but barrier and light are normally invisible, and
jigsaw/command blocks are structure/redstone utility blocks. Added
`TECHNICAL_BLOCK_BLACKLIST` in `scanner.py`, enforced everywhere,
regardless of mode.

**7. `orange_concrete_powder` (and everything else affected by gravity)
didn't work.** Sand, red sand, gravel, suspicious sand/gravel, and all
16 concrete powder colors are full 1x1x1 cubes, so they passed every
earlier filter -- but they fall as soon as nothing supports them, so a
freshly-pasted pixel-art block just turns into a falling-sand entity and
vanishes. Added `GRAVITY_AFFECTED_BLOCKS` to `scanner.py`, always
enforced everywhere, same as the technical blacklist.

**8. The "require full-cube shape" checkbox is gone -- it's always on
now.** Custom/curated folder and individual-file additions used to be
able to skip the full-cube requirement (so you could deliberately
include a slab or stair). That option's been removed per your request;
`scan_folder()` and `scan_specific_files()` now use the exact same
filter, no exceptions.

**9. File dialogs remember where you last left them.** Persisted to
`~/.worldedit_tab_recent_paths.json` (survives between runs, not just
within one session):
- the Resource Pack Scanner's texture-folder browse (main scan, Add
  Custom Folder, and Add Individual File(s) all share this)
- the palette JSON save/open dialogs, shared between the Resource Pack
  Scanner and Image to Pixel Art tabs -- save it from one, and the other
  tab's "load palette" dialog opens right there
- the Image to Pixel Art tab's source-image browse, and its schematic
  save-location dialog (its own separate memory, since you're not
  usually saving schematics next to your source photos)

## New: Review / Edit Palette window

`orange_glazed_terracotta` (and anything else that scans a little oddly)
can now be caught by eye before it ends up in a build. A new **Review /
Edit Palette...** button opens a scrollable window showing every
texture currently in the palette as a big (96x96, upscaled with nearest-
neighbor so pixel art stays crisp) thumbnail, sorted alphabetically:

- Click a texture to select it (highlights blue).
- **Remove Selected** or the **Delete** key drops it from the list.
- **Undo** brings back the most recently removed one.
- **Save Selections** commits your edits back into the palette (and
  refreshes the preview below); **Cancel** closes the window and
  discards whatever you removed.

Only after you click Save Selections does anything change -- closing
the window with Cancel (or the OS close button) leaves the palette
exactly as it was. Saving the edited palette to JSON afterward is still
the same "Save Palette JSON" button as before.

If a palette entry came from a live scan, its real texture is shown; if
it came from a previously-saved palette JSON (no source file on hand),
a plain color swatch is shown instead as a fallback.

## Image to Pixel Art: simplified to direct-blocks-only

Removed the "Convert to blocks" checkbox and the player-position fields
-- this tab now always produces a direct-block schematic, nothing else.
The command-block-wall mode it used to have is superseded by the Image
Command Blocks tab's much better placed-by-corner-coordinates model.

## New tab: Video (Media Creator)

Turns a video into an animated command-block wall -- the same circuit
generator as GIF Command Blocks (`generate_gif_command_block_schem`,
imported directly from `gif_command_blocks.converter`, so a fix to the
redstone design fixes both tabs at once), fed by video frames instead
of GIF frames.

**Two steps, kept deliberately separate, because of scale.** A 60fps,
60-second video is 3600 frames -- holding that many full-resolution
frames in memory at once would be tens of gigabytes.

1. **Extract Frames** -- decodes the video with OpenCV
   (`opencv-python-headless`, needs `pip install`) and writes each frame
   straight to disk as a numbered PNG, one at a time, never holding more
   than a single frame in memory. Writes a small JSON sidecar recording
   the source fps so step 2 can read the original timing back
   automatically. An "extract every Nth frame" field controls disk usage
   independent of the timing-driven skipping step 2 does later.

2. **Generate From Frame Folder** -- also doesn't load image data up
   front: it lists file paths and reads the fps sidecar (or takes a
   manual fps if the folder wasn't made by this tool), and *streams*
   frames one at a time during generation -- each one loaded, resized
   down to the tiny target block grid, and discarded before the next
   loads. Peak memory stays around a single full-resolution frame
   regardless of whether the video is 10 frames or 10,000.

Verified this isn't just a theoretical claim: extracted and streamed a
real 300-frame, 800x600 test video through the actual pipeline and
measured **zero** memory growth during streaming, versus the ~550MB it
would take to hold all 300 frames at once. Also ran the full path
through the real GUI end-to-end (extract → load → generate → save →
reload), confirming frame counts, timing math, and the resulting
schematic's command blocks/coordinates all check out.

Same placement UI (corner-coordinate model), palette loading, preview +
rotate, and timing controls (target fps, tick rate, loop count, "show
all frames") as GIF Command Blocks -- see Fix #12 at the top for the
current wall+relay architecture and what the depth-extent callout below
the timing plan means.

## Fix: threading + Tkinter don't mix the way it looks like they should

Building the Video tab's background extraction/generation surfaced a
real bug, not just a testing artifact: **Tkinter widgets and Variables
aren't safe to touch from any thread other than the one running the
event loop.** Two forms of this were present:

1. Calling `.after()` *from* a background thread to schedule a UI
   update -- worked most of the time by luck, but could raise
   `RuntimeError: main thread is not in main loop`, especially for very
   fast operations where the callback fires before the main thread's
   event loop has "settled." Fixed everywhere by switching to the
   standard safe pattern: the worker thread only ever pushes plain data
   into a `queue.Queue`; a self-rescheduling `frame.after(100, poll)`
   loop -- itself only ever invoked from the main thread -- drains the
   queue and does the actual widget updates.

2. Reading a `tk.StringVar`'s `.get()` value *inside* a worker thread
   (found in the Video tab's `facing_var.get()` and the Resource Pack
   Scanner's `color_mode_var.get()`, both called from inside their
   `worker()` functions). This one doesn't always raise -- it can just
   silently hang, which is exactly what happened in testing: extraction
   worked, but generation froze indefinitely with no error. Fixed by
   reading these values on the main thread *before* starting the
   worker, and passing the plain string in.

Both fixes applied to every background-threaded operation in the
project (Resource Pack Scanner's Scan Folder / Add Custom Folder / Add
Individual Files, and Video's Extract Frames / Generate). GIF and Image
Command Blocks don't use background threads for generation currently
(synchronous), so they weren't at risk of this specific bug, but the
same pattern should be used if threading gets added there later.

## New tab: GIF Command Blocks (corrected redstone architecture)

## New tab: GIF Command Blocks

Turns a GIF into an animated command-block wall -- **see Fix #12 at the
top of this file for the current architecture** (shared walls + relay,
not per-pixel columns; that description below is what an earlier,
now-replaced version did, kept only as history).

**Timing preserves the GIF's actual frame rate**, not just "1 repeater =
1 gap." Enter your server's tick rate and a target playback fps
(defaults to the GIF's own native fps when you load it, so "24fps stays
24fps" regardless of tick rate -- override it for custom speed). The
tool works out exactly how many redstone ticks that requires and
decomposes it into as many repeaters as it takes (1-4 ticks each,
greedy) -- so a high tick rate genuinely means more repeaters, not a
fixed count. Source frames are only skipped if the target fps is faster
than even a single 1-tick repeater can keep up with at your tick rate;
"Show all frames" forces every frame to be kept regardless, for
deliberate slow motion.

**Loop count**: repeat the whole frame sequence end-to-end as many
times as you want, baked directly into the structure (not a rewire-back-
to-the-start auto-loop -- each repetition physically exists in the
schematic).

## New tab: Image Command Blocks

A separate tab from Image to Pixel Art (which is untouched -- still does
exactly what it did before, for the direct-block "paste and it's just
there" case). This one is specifically for the recreate-on-power command
block wall, placed by explicit world coordinates instead of a single
player position:

**Coordinate convention:** the source image's left edge maps to the
lowest value of the wall's horizontal axis, its top edge to the highest
Y. Which world axis counts as "horizontal" depends on facing:
North/South → X, East/West → Z (thickness/depth is the other one, a
single coordinate). This is documented in the tab itself too.

**Fixed size mode (default)** — set Width/Height in blocks (aspect-lock
checkbox, same as Image to Pixel Art), pick which corner you're placing
(Bottom-Left/Bottom-Right/Top-Left/Top-Right), and give that corner's
X/Y/Z. The other three corners are fully determined by the fixed
dimensions -- scale is locked, so you're positioning the whole rectangle,
not stretching it. All four corners are shown live, recalculating on
every keystroke.

**Stretch mode** — give any two diagonally-opposite corners' X/Y/Z
instead, and the image is resized to exactly fill that span. Still flat
(2D) -- only the horizontal and vertical extents come from the two
points; the depth is taken from the first point (a warning shows if the
two points disagree on depth). Optional "Lock aspect ratio, based on
Horizontal/Vertical" preserves the source image's proportions by
recomputing the other axis's span from whichever one you pick;
unchecked, both spans are used exactly as given, which will distort the
image if they don't already match its aspect ratio.

Verified end-to-end (not just the geometry math, the actual GUI click
path): loading a palette and image through the real Browse buttons,
generating in both modes, and confirming the resulting `.schem`'s
`setblock` coordinates and computed width/height land exactly where the
math predicts.

## Resource Pack Scanner: custom / curated texture selection

Two new buttons on the Resource Pack Scanner tab, both **merge into**
the current palette instead of replacing it:

- **Add Custom Folder...** — point it at a small folder of hand-picked
  textures (e.g. your own 20-texture set) and every one of them gets
  scanned, not just full-cube blocks.
- **Add Individual File(s)...** — a multi-select file dialog to pick
  specific `.png` files from anywhere, one at a time or in a batch.

Both default to a looser check than the main "Scan Folder" button: the
texture name still has to be a **real** vanilla block id (checked
against the full ~1,084-block registry, not just the 430 full-cube
ones) so it's guaranteed placeable — but it no longer has to be a full
cube, so you can deliberately include a slab, stair, etc. if you want
one for a specific look. `TECHNICAL_BLOCK_BLACKLIST` (barrier, light,
command blocks) is still always blocked no matter what. A checkbox
("Also require full-cube shape") lets you re-apply the strict filter to
these additions too, if you want.

## Custom / curated texture selection: two workflows

**Broad, all-vanilla-blocks palette:** "Scan Folder" against a whole
resource pack (or its `textures/block` folder). Filtered to real,
full-cube blocks automatically.

**Limited palette (e.g. "just the colored concretes"):** point "Add
Custom Folder..." at a small folder you've curated yourself -- retexture
it however you like, the palette only uses what's in that folder. "Add
Individual File(s)..." does the same for a hand-picked multi-select of
specific `.png` files instead of a whole folder. Both **merge into** the
current palette rather than replacing it, so you can combine a broad
scan with your own additions, or skip the broad scan entirely and use
only your curated set.

Custom/individual additions still have to be a real, full-cube vanilla
block id, exactly like the main scan -- there's no looser mode anymore.

**Emissive/glow textures are always skipped, in every mode** -- if your
custom retexture set ships glow-map variants alongside the normal
textures (filenames ending `_e`, `_emissive`, `_glow`, `_emission`, or
sitting in an `emissive` subfolder), those never get scanned as their
own block color. Only the real texture is used.

## New package layout

```
worldedit_tab/
  worldedit_gui.py                 <- create_worldedit_schematic_gui(frame, gui), same signature as before
  common/
    schem_io.py                    <- save_schematic / load_schematic / build_block_data / read_block_data / command-block helpers, used by every tab
    recent_paths.py                <- remembers the last folder used per file-dialog kind, across runs
    image_preview.py               <- shared live photo preview + rotate widget, used by all three image tabs
  convert_to_command_blocks/       <- (renamed from command_block_generator) your original tab, bugs fixed
  resource_pack_scanner/           <- scan a texture folder -> dominant (or average) RGB per full-cube block -> palette JSON
    valid_blocks.json              <- bundled list of full-cube vanilla block ids (strict mode)
    all_blocks.json                <- bundled list of every vanilla block id (baseline for custom/curated additions)
    review_window.py               <- post-scan thumbnail review/edit window (select, remove, undo, save/cancel)
  image_to_pixelart/               <- image -> block grid -> direct-block or command-block-wall schem (via a single player position)
  image_command_blocks/            <- image -> command-block wall placed by explicit corner coordinates (fixed size or stretch-to-fit)
  gif_command_blocks/               <- GIF -> animated command-block wall (fixed target position, per-pixel repeater/stone timing chain)
  video_command_blocks/              <- video -> extracted frames -> animated command-block wall (streamed, memory-safe)
```

`create_worldedit_schematic_gui(frame, gui)` keeps its exact old
signature, so `main.py` shouldn't need any changes beyond however it
already imports `worldedit_tab`.

## Tab-by-tab notes

**Conv to cmd blocks** — your original Schem → Command Blocks converter,
re-homed, bugs fixed.

**Resource Pack Scanner** — pick a folder of `.png` textures, walks it
recursively, picks the dominant (or, if selected, average) color of each
texture's opaque pixels (only the first frame is sampled for animated
strip textures), filters out anything that isn't a full-cube block, and
saves/loads a `{"minecraft:name": [r,g,b]}` JSON palette. The status
line reports how many textures were kept vs. filtered as "not a
full-cube block" vs. skipped as unreadable/transparent.

**Image to Pixel Art** — load a palette JSON, load a photo, set
width/height (aspect-ratio-lock checkbox), pick a facing
(north/south spans the image across X, east/west spans it across Z), and
generate either a direct-block schematic (**Convert to blocks** checked)
or a command-block wall (unchecked) whose `setblock` commands target the
X/Y/Z you record as "player position when scanned."

**GIF Command Blocks** — see the dedicated section above.

**Video** — see the dedicated section above.

## What I didn't touch

`utils.py` (logging setup) isn't part of `worldedit_tab` and didn't need
changes here.
