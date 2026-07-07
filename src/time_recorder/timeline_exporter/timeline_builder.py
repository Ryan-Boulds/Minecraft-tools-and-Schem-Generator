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

                item_idx += 1

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