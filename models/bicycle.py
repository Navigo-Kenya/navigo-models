"""Bicycle: a black roadster ("Black Mamba" class, 28-inch wheels) and its rider."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, box, ellipsoid, lathe, tube  # noqa: E402
from people import person, seated_pose  # noqa: E402

k = Kit("bicycle", "Bicycle")

WR = 0.355
YF, YR = -0.57, 0.58
BB = Vector((0, 0.05, 0.30))       # bottom bracket

M = {
    "frame": k.mat("frame", "#0E0F11", rough=0.18, coat=0.9),
    "chrome": k.mat("chrome", "#DDE0E3", rough=0.12, metal=1.0),
    "rubber": k.mat("rubber", "#121212", rough=0.85),
    "saddle": k.mat("saddle", "#3A2418", rough=0.6),
    "head": k.mat("headlight", "#EEF2FA", rough=0.06, emit="#FFF3DA"),
    "tail": k.mat("taillight", "#9E0E17", rough=0.12, emit="#FF1A1A"),
}

# ── Wheel ────────────────────────────────────────────────────────────────
bm = bmesh.new()
tyre = [(-0.019, 0.318), (0.019, 0.318), (0.021, 0.335), (0.0, WR), (-0.021, 0.335)]
bmesh.ops.recalc_face_normals(bm, faces=lathe(bm, tyre, (0, 0, 0), "x", 40, [0] * len(tyre)))
rim = [(-0.014, 0.305), (0.014, 0.305), (0.016, 0.318), (-0.016, 0.318)]
bmesh.ops.recalc_face_normals(bm, faces=lathe(bm, rim, (0, 0, 0), "x", 40, [1] * 4))
tube(bm, (-0.05, 0, 0), (0.05, 0, 0), 0.022, 12, 1)
for i in range(36):
    a = 2 * math.pi * i / 36
    s = 1 if i % 2 else -1
    tube(bm, (s * 0.04, 0.02 * math.cos(a + 0.3), 0.02 * math.sin(a + 0.3)),
         (s * 0.006, 0.306 * math.cos(a), 0.306 * math.sin(a)), 0.0016, 4, 1, caps=False)
front = k.add("wheel_f", bm, [M["rubber"], M["chrome"]], group="wheel_f", location=(0, YF, WR))
k.instance("wheel_r", front, (0, YR, WR))

# ── Frame and parts ──────────────────────────────────────────────────────
bm = bmesh.new()
head_top, head_bot = Vector((0, -0.46, 1.00)), Vector((0, -0.42, 0.84))
seat_top = Vector((0, 0.20, 0.90))
rear_axle, front_axle = Vector((0, YR, WR)), Vector((0, YF, WR))
r = 0.017
tube(bm, head_bot, head_top, 0.02, 10, 0)
tube(bm, head_top + Vector((0, 0.02, -0.04)), seat_top, r, 10, 0)            # top tube
tube(bm, head_top + Vector((0, 0.03, -0.12)), seat_top + Vector((0, 0.0, -0.10)), r, 10, 0)  # second top tube
tube(bm, head_bot, BB, r + 0.003, 10, 0)                                      # down tube
tube(bm, BB, seat_top + Vector((0, 0.01, 0.04)), r, 10, 0)                    # seat tube
for s in (1, -1):
    tube(bm, BB + Vector((s * 0.03, 0, 0)), rear_axle + Vector((s * 0.05, 0, 0)), 0.012, 8, 0)       # chain stays
    tube(bm, seat_top + Vector((s * 0.02, 0, 0)), rear_axle + Vector((s * 0.05, 0, 0)), 0.011, 8, 0)  # seat stays
    tube(bm, head_bot + Vector((s * 0.03, 0, 0)), front_axle + Vector((s * 0.05, 0, 0)), 0.013, 8, 0)  # fork
    tube(bm, rear_axle + Vector((s * 0.08, 0.02, 0.36)), rear_axle + Vector((s * 0.05, 0, 0)), 0.008, 6, 0)  # rack struts
# Upright handlebar sweeping back, grips.
stem_top = Vector((0, -0.44, 1.10))
tube(bm, head_top, stem_top, 0.012, 8, 1)
for s in (1, -1):
    tube(bm, stem_top, Vector((s * 0.20, -0.36, 1.12)), 0.011, 8, 1)
    tube(bm, Vector((s * 0.20, -0.36, 1.12)), Vector((s * 0.29, -0.24, 1.10)), 0.011, 8, 1)
    tube(bm, Vector((s * 0.25, -0.30, 1.11)), Vector((s * 0.31, -0.22, 1.10)), 0.017, 10, 2)
# Mudguards (arcs), rear carrier, chain guard (right side), crank, pedals.
for yc, a0, a1 in ((YF, 0.3, 2.0), (YR, 1.2, 3.0)):
    pts = [Vector((0, yc - math.cos(a0 + (a1 - a0) * i / 14) * (WR + 0.025), WR + math.sin(a0 + (a1 - a0) * i / 14) * (WR + 0.025)))
           for i in range(15)]
    for i in range(14):
        p, q = pts[i], pts[i + 1]
        f = bm.faces.new([bm.verts.new(p + Vector((-0.03, 0, 0))), bm.verts.new(p + Vector((0.03, 0, 0))),
                          bm.verts.new(q + Vector((0.03, 0, 0))), bm.verts.new(q + Vector((-0.03, 0, 0)))])
        f.material_index = 0
box(bm, (0, YR + 0.02, WR + 0.37), (0.16, 0.36, 0.012), 0)
box(bm, (-0.07, 0.32, 0.31), (0.012, 0.58, 0.09), 0, bevel=0.01)
tube(bm, BB + Vector((-0.06, 0, 0)), BB + Vector((0.06, 0, 0)), 0.03, 12, 1)
crank_l = BB + Vector((0.09, -0.15, 0.09))
crank_r = BB + Vector((-0.09, 0.15, -0.09))
tube(bm, BB + Vector((0.07, 0, 0)), crank_l, 0.01, 6, 1)
tube(bm, BB + Vector((-0.07, 0, 0)), crank_r, 0.01, 6, 1)
box(bm, crank_l + Vector((0.05, 0, 0)), (0.09, 0.06, 0.02), 0)
box(bm, crank_r + Vector((-0.05, 0, 0)), (0.09, 0.06, 0.02), 0)
# Saddle on springs.
ellipsoid(bm, seat_top + Vector((0, 0.01, 0.10)), (0.095, 0.13, 0.035), 3, segs=16, rings=8)
for s in (1, -1):
    tube(bm, seat_top + Vector((s * 0.05, 0.06, 0.03)), seat_top + Vector((s * 0.05, 0.06, 0.08)), 0.014, 8, 1)
k.add("frame", bm, [M["frame"], M["chrome"], M["rubber"], M["saddle"]])

bm = bmesh.new()
ellipsoid(bm, (0, -0.52, 0.98), (0.04, 0.035, 0.04), 0, segs=12, rings=6)
box(bm, (0, YR + 0.20, WR + 0.36), (0.06, 0.015, 0.03), 1)
k.add("lights", bm, [M["head"], M["tail"]], smooth=False, group="lights")

# ── Rider, mid pedal stroke ──────────────────────────────────────────────
pose = seated_pose(pelvis=(0, 0.21, 1.03), lean=24, hands=(0.29, -0.25, 1.11),
                   ankles=(crank_l + Vector((0.08, 0.02, 0.06)), crank_r + Vector((-0.08, -0.02, 0.06))),
                   toes=(crank_l + Vector((0.08, -0.11, 0.03)), crank_r + Vector((-0.08, -0.15, 0.03))))
person(k, "rider", pose, {
    "skin": k.mat("skin", "#5E3A22", rough=0.6),
    "helmet": k.mat("helmet", "#F2A900", rough=0.25, coat=0.8),
    "visor": k.mat("helmet_front", "#F2A900", rough=0.25, coat=0.8),   # an open cycling helmet: no dark visor
    "top": k.mat("shirt", "#1D7A55", rough=0.75), "sleeves": k.mat("skin_arms", "#5E3A22", rough=0.6),
    "trousers": k.mat("trousers", "#2F3338", rough=0.8), "shoes": k.mat("shoes", "#EDEDED", rough=0.6),
})

k.finish(bake={"body": 1024, "wheel_f": 512, "rider": 512}, dust=(0.0, 0.4, 0.3), ao_distance=0.2)
