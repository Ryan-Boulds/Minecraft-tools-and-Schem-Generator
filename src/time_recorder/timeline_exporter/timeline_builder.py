# time_recorder/timeline_exporter/timeline_builder.py
import math
from collections import defaultdict
from nbtlib.tag import Compound, List, Byte, Int, Short, ByteArray, String, IntArray


class TimelineSchematicBuilder:
    def __init__(self, tick_rate: float = 20.0):
        self.tick_rate = tick_rate
        self.physical_items = []
        self.grid = defaultdict(lambda: ("minecraft:air", None))

    def add_events(self, events):
        prev_ticks = 0
        for i, item in enumerate(events):
            if len(item) >= 2:
                ts, cmd = item[0], item[1]
            else:
                continue
            curr_ticks = round(ts * self.tick_rate)
            delta = curr_ticks - prev_ticks if i > 0 else 0

            if i > 0 and delta > 0:
                rep_ticks = math.ceil(max(1, delta) / 2.0)
                while rep_ticks > 0:
                    d = min(4, rep_ticks)
                    self.physical_items.append(('rep', d))
                    rep_ticks -= d

            self.physical_items.append(('cmd', str(cmd).strip()))
            prev_ticks = curr_ticks

    def build_reference_layout(self, max_z_per_floor: int = 50, floor_height: int = 2, max_height: int = 50):
        num_items = len(self.physical_items)
        num_floors = math.ceil(num_items / max_z_per_floor)

        floors_per_column = max(1, max_height // floor_height)

        QTZ = "minecraft:quartz_block"
        CMD = "minecraft:command_block[conditional=false,facing=up]"

        print(f"DEBUG: Building layout with {num_floors} total segments...")

        self.grid = defaultdict(lambda: ("minecraft:air", None))

        item_idx = 0
        for floor_idx in range(num_floors):
            column_idx = floor_idx // floors_per_column
            floor_in_column = floor_idx % floors_per_column

            x = column_idx * 2

            if column_idx % 2 == 0:
                y_base = floor_in_column * floor_height
            else:
                y_base = (floors_per_column - 1 - floor_in_column) * floor_height

            # Direction of travel along z for this floor, matching the
            # pos -> z relationship below: even floors run high-z -> low-z
            # (-z), odd floors run low-z -> high-z (+z).
            dz = -1 if floor_idx % 2 == 0 else 1

            last_component_pos = None

            for pos in range(max_z_per_floor):
                if item_idx >= num_items:
                    break
                
                if floor_idx % 2 == 0:
                    z = 2 + (max_z_per_floor - 1 - pos)
                    facing = "south"
                else:
                    z = 2 + pos
                    facing = "north"
                    
                item = self.physical_items[item_idx]

                # ONLY place quartz DIRECTLY under the redstone component
                y_support = y_base
                y_component = y_base + 1

                self._set(x, y_support, z, QTZ)   # Support block only here

                if item[0] == 'cmd':
                    self._set(x, y_component, z, CMD)
                    self._add_cmd_entity(x, y_component, z, item[1])
                else:
                    rep = f"minecraft:repeater[delay={item[1]},facing={facing},locked=false,powered=false]"
                    self._set(x, y_component, z, rep)

                last_component_pos = (x, y_component, z)
                item_idx += 1

            # If this floor's run actually finished (as opposed to cutting
            # off mid-run because we ran out of items) and there's a next
            # floor to connect to, bridge the gap so the whole thing stays
            # one continuous circuit.
            next_floor_idx = floor_idx + 1
            if last_component_pos is not None and item_idx < num_items and next_floor_idx < num_floors:
                cx, cy, cz = last_component_pos
                next_column_idx = next_floor_idx // floors_per_column

                if next_column_idx == column_idx:
                    # Next floor stacks directly above/below in the same
                    # column: even columns climb (rising connector), odd
                    # columns descend (hairpin drop).
                    if column_idx % 2 == 0:
                        self._add_vertical_connector(cx, cy, cz, dz)
                    else:
                        self._add_descending_connector(cx, cy, cz, dz)
                else:
                    # Column boundary: next floor is in the next column
                    # over, at the same height (top-to-top or
                    # bottom-to-bottom) - bridge across horizontally.
                    self._add_column_bridge(cx, cy, cz, dz)

    def _add_vertical_connector(self, x, y, z, dz):
        """
        Bridges the vertical gap between the end of one floor's run and the
        start of the next floor stacked directly above it, so the run of
        repeaters/command blocks stays one continuous powered circuit.

        (x, y, z) is the position of the LAST component placed on the
        floor (the end of the run, at component height). dz is +1 or -1,
        the direction the signal was travelling in z on that floor - the
        connector keeps extending outward in that same direction.

        Six-point pattern (confirmed against in-game coordinates):
          1. support block, one step out, one below component height
             (dust goes flat on top of this - handles a command block
             sitting right at the end, since you can't chain a repeater
             directly off one)
          2. dust on top of that support block, at component height
          3. block, two steps out, still at component height
          4. dust on top of that block (component height + 1)
          5. quartz top slab, one step back in (toward the run), level
             with that dust
          6. dust on top of the slab - this lands exactly on the next
             floor's component height (a net rise of +2, i.e. floor_height)
        """
        QTZ = "minecraft:quartz_block"
        SLAB = "minecraft:quartz_slab[type=top]"
        DUST = "minecraft:redstone_wire"

        near_z = z + dz
        far_z = z + 2 * dz

        # 1-2: flat extension, one step out
        self._set(x, y - 1, near_z, QTZ)
        self._set(x, y, near_z, DUST)

        # 3-4: another step out, rising by one
        self._set(x, y, far_z, QTZ)
        self._set(x, y + 1, far_z, DUST)

        # 5-6: step back in on a slab, rising by one more - lands on the
        # next floor's component height
        self._set(x, y + 1, near_z, SLAB)
        self._set(x, y + 2, near_z, DUST)

    def _add_descending_connector(self, x, y, z, dz):
        """
        Same purpose as _add_vertical_connector, but for floors in a
        descending column (odd column_idx) where the next floor is 2
        BELOW instead of above. Redstone dust can't just mirror the
        rising staircase to flow downward, so this uses a 9-block hairpin
        instead: extend forward 3 flat, drop 1 while jogging out to x-1,
        turn back, drop 1 more while returning to x, and continue back
        toward the run - a net drop of 2 (floor_height) by the end.

        (x, y, z) is the last component placed on the floor (component
        height). dz is +1 or -1, the direction of travel on that floor -
        the hairpin's forward leg extends in that same direction, then
        doubles back.

        Confirmed point-for-point against in-game coordinates on both
        ends (only the z-direction mirrors between ends; the x-notch is
        always toward x-1, not mirrored).
        """
        QTZ = "minecraft:quartz_block"
        DUST = "minecraft:redstone_wire"

        x0, y0, z0 = x, y - 1, z  # support level, at the start of the hairpin

        # (delta_x, delta_y, delta_z_steps) - delta_z_steps gets multiplied
        # by dz to mirror direction; delta_x is NOT mirrored, it's always
        # toward x0 - 1.
        offsets = [
            (0, 0, 1),
            (0, 0, 2),
            (0, 0, 3),
            (0, -1, 4),
            (-1, -2, 4),
            (-1, -2, 3),
            (0, -2, 3),
            (0, -2, 2),
            (0, -2, 1),
        ]

        for ddx, ddy, ddz in offsets:
            sx = x0 + ddx
            sy = y0 + ddy
            sz = z0 + dz * ddz
            self._set(sx, sy, sz, QTZ)
            self._set(sx, sy + 1, sz, DUST)

    def _add_column_bridge(self, x, y, z, dz):
        """
        Bridges the END of one column's last floor to the START of the
        next column's first floor, at column boundaries. Both floors sit
        at the same height (top-to-top for an ascending column handing
        off to a descending one, or bottom-to-bottom for the reverse), so
        this is a purely horizontal loop - no vertical rise/drop, just a
        jog over to the next column's x.

        (x, y, z) is the last component placed in the outgoing column
        (component height). dz is +1 or -1, the direction of travel on
        that floor - the bridge's z motion mirrors that direction, while
        x always increases by 2 toward the next column (columns always
        increase in x regardless of ascending/descending).

        Confirmed point-for-point against in-game coordinates on both a
        top (dz=-1) and bottom (dz=+1) bridge.
        """
        QTZ = "minecraft:quartz_block"
        DUST = "minecraft:redstone_wire"

        y_support = y - 1

        # (delta_x, delta_z_steps) - delta_z_steps gets multiplied by dz
        # to mirror direction; delta_x always increases toward x + 2,
        # the next column over.
        offsets = [
            (0, 1),
            (0, 2),
            (1, 2),
            (2, 2),
            (2, 1),
        ]

        for ddx, ddz in offsets:
            sx = x + ddx
            sz = z + dz * ddz
            self._set(sx, y_support, sz, QTZ)
            self._set(sx, y, sz, DUST)

    def _set(self, x, y, z, block):
        self.grid[(x, y, z)] = (block, None)

    def _add_cmd_entity(self, x, y, z, command):
        entity = {
            "Id": "minecraft:command_block",
            "Pos": [x, y, z],
            "Command": command,
            "auto": 0, "conditionMet": 0, "powered": 0,
            "TrackOutput": 1, "SuccessCount": 0, "UpdateLastExecution": 1,
            "CustomName": '{"text":"@"}'
        }
        self.grid[(x, y, z)] = (self.grid[(x, y, z)][0], entity)

    def to_schematic_data(self):
        if not self.grid:
            raise ValueError("Empty grid")

        min_x = min(p[0] for p in self.grid)
        min_y = min(p[1] for p in self.grid)
        min_z = min(p[2] for p in self.grid)

        w = max(p[0] for p in self.grid) - min_x + 1
        h = max(p[1] for p in self.grid) - min_y + 1
        l = max(p[2] for p in self.grid) - min_z + 1

        block_data = bytearray([0] * (w * h * l))
        block_entities = List[Compound]()

        palette = []
        pal_map = {}

        def pid(name):
            if name not in pal_map:
                pal_map[name] = len(palette)
                palette.append(name)
            return pal_map[name]

        # Reserve palette index 0 for air. block_data is a zero-initialized
        # bytearray, so any voxel we never explicitly _set() (i.e. every gap
        # in the bounding box, including the gap between the up-run and
        # down-run) is already byte value 0. If air isn't guaranteed to be
        # palette index 0, those unset voxels get interpreted as whatever
        # block happened to be registered first in the palette (quartz),
        # which is exactly why the gaps were rendering as quartz.
        pid("minecraft:air")

        for (gx, gy, gz), (bname, ent) in self.grid.items():
            lx = gx - min_x
            ly = gy - min_y
            lz = gz - min_z
            idx = (ly * l + lz) * w + lx
            block_data[idx] = pid(bname)

            if ent:
                be = Compound({
                    "Id": String(ent["Id"]),
                    "Pos": IntArray([Int(lx), Int(ly), Int(lz)]),
                    "Command": String(ent.get("Command", "")),
                    "auto": Byte(0),
                    "conditionMet": Byte(0),
                    "powered": Byte(0),
                    "TrackOutput": Byte(1),
                    "SuccessCount": Int(0),
                    "UpdateLastExecution": Byte(1),
                    "CustomName": String('{"text":"@"}'),
                })
                block_entities.append(be)

        return {
            "PaletteMax": Int(len(palette)),
            "Palette": Compound({n: Int(i) for i, n in enumerate(palette)}),
            "Version": Int(2),
            "Width": Short(w),
            "Height": Short(h),
            "Length": Short(l),
            "DataVersion": Int(3578),
            "BlockData": ByteArray(block_data),
            "BlockEntities": block_entities,
            "Metadata": Compound({
                "WEOffsetX": Int(0),
                "WEOffsetY": Int(0),
                "WEOffsetZ": Int(0),
            }),
        }


def create_schematic_data(events, tick_rate=20.0):
    builder = TimelineSchematicBuilder(tick_rate)
    builder.add_events(events)
    builder.build_reference_layout()
    return builder.to_schematic_data()