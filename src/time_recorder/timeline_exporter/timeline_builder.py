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

    def build_reference_layout(self, max_z_per_floor: int = 15, floor_height: int = 2):
        num_items = len(self.physical_items)
        num_floors = math.ceil(num_items / max_z_per_floor)

        OAK_SLAB = "minecraft:oak_slab[type=top,waterlogged=false]"
        STONE_SLAB = "minecraft:stone_slab[type=top,waterlogged=false]"
        QTZ = "minecraft:quartz_block"
        WIRE = "minecraft:redstone_wire[east=none,north=side,power=0,south=side,west=none]"
        CMD = "minecraft:command_block[conditional=false,facing=up]"

        print(f"DEBUG: Building layout with {num_floors} floors and {num_items} items")

        item_idx = 0
        for floor_idx in range(num_floors):
            y_base = floor_idx * floor_height

            # Main timeline
            for pos in range(max_z_per_floor):
                if item_idx >= num_items:
                    break
                z = 2 + pos
                item = self.physical_items[item_idx]

                self._set(0, y_base, z, QTZ)

                if item[0] == 'cmd':
                    self._set(0, y_base + 1, z, CMD)
                    self._add_cmd_entity(0, y_base + 1, z, item[1])
                else:
                    facing = "south" if (floor_idx % 2 == 0) else "north"
                    rep = f"minecraft:repeater[delay={item[1]},facing={facing},locked=false,powered=false]"
                    self._set(0, y_base + 1, z, rep)

                item_idx += 1

            # === STRONG DEBUG TRANSITION ===
            if floor_idx < num_floors - 1:
                next_y = y_base + floor_height
                end_z = 2 + max_z_per_floor

                # Left side (beginning) - BIG oak slab tower so it's obvious
                for dy in range(3):
                    self._set(0, next_y + dy, 0, OAK_SLAB)
                    self._set(0, next_y + dy, 1, OAK_SLAB)

                # Right side (end) - BIG stone slab tower
                for dy in range(4):
                    self._set(0, next_y + dy, end_z + 1, STONE_SLAB)

                self._set(0, next_y + 1, end_z + 2, WIRE)

                # Only one quartz at corner
                self._set(0, next_y, end_z, QTZ)

        print("DEBUG: Transition code executed")

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
        # (standard conversion - unchanged)
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
                "WEOffsetX": Int(min_x),
                "WEOffsetY": Int(min_y),
                "WEOffsetZ": Int(min_z - 18),
            }),
        }