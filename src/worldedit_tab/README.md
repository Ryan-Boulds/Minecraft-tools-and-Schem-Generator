# worldedit_tab rebuild

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

## New: custom / curated texture selection

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
  convert_to_command_blocks/       <- (renamed from command_block_generator) your original tab, bugs fixed
  resource_pack_scanner/           <- scan a texture folder -> dominant (or average) RGB per full-cube block -> palette JSON
    valid_blocks.json              <- bundled list of full-cube vanilla block ids (strict mode)
    all_blocks.json                <- bundled list of every vanilla block id (baseline for custom/curated additions)
    review_window.py               <- post-scan thumbnail review/edit window (select, remove, undo, save/cancel)
  image_to_pixelart/               <- image -> block grid -> direct-block or command-block-wall schem
  gif_placeholder/                 <- stub UI, not implemented
  video_placeholder/                <- stub UI, not implemented
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

**GIF / Video** — placeholders only, per your instructions.

## What I didn't touch

`utils.py` (logging setup) isn't part of `worldedit_tab` and didn't need
changes here.
