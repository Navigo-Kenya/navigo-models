"""Walking marker: a 3D arrow on a glowing disc, in Navigo orange (replaces the CC-BY arrow)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, lathe  # noqa: E402

k = Kit("puck", "Walking marker")
top = k.mat("paint", "#FFFFFF", rough=0.25, coat=0.8)
edge = k.mat("beacon", "#FF6F00", rough=0.3, emit="#FF6F00", emit_strength=1.0)
disc = k.mat("neon", "#FF8A2A", rough=0.4, emit="#FF6F00", emit_strength=0.6)

# Arrow (chevron), pointing forward (-Y), bevelled, white top with an orange rim.
outline = [(0.0, -0.95), (0.62, 0.55), (0.0, 0.22), (-0.62, 0.55)]
bm = bmesh.new()
bottom = [bm.verts.new((x, y, 0.06)) for x, y in outline]
topv = [bm.verts.new((x, y, 0.30)) for x, y in outline]
bm.faces.new(list(reversed(bottom)))
f = bm.faces.new(topv)
for i in range(4):
    j = (i + 1) % 4
    side = bm.faces.new((bottom[i], bottom[j], topv[j], topv[i]))
    side.material_index = 1
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
arrow = k.add("arrow", bm, [top, edge], smooth=False, group="arrow")
k.bevel(arrow, 0.035, segments=3, angle=20)

# Disc: a flat ring that glows.
bm = bmesh.new()
lathe(bm, [(0.0, 1.05), (0.0, 1.25), (0.025, 1.25), (0.025, 1.05)], (0, 0, 0.0), "z", 48, [0] * 4)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
k.add("disc", bm, [disc], smooth=False, group="lights")

k.finish(bake={"arrow": 256}, dust=(0.0, 0.0, 0.0), ao_distance=0.2,
         shots=[("hero", (2.6, -3.2, 2.4), (0, 0, 0.1), 50), ("rear", (-2.4, 3.0, 2.6), (0, 0, 0.1), 50), ("nav", (0, 5.5, 4.5), (0, -1.2, 0), 35)])
