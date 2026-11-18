"""Boda: a 150 cc commuter motorbike (Bajaj Boxer class, 1.28 m wheelbase) with
its rider (helmet, reflective vest) and the passenger (the app's user).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, box, ellipsoid, lathe, tube  # noqa: E402
from people import person, seated_pose  # noqa: E402

k = Kit("boda", "Boda boda")

WR = 0.30                    # wheel radius (2.75-17)
YF, YR = -0.66, 0.62         # axles

M = {
    "paint": k.mat("paint", "#B3121C", rough=0.22, coat=0.8),
    "black": k.mat("frame", "#17181A", rough=0.45, metal=0.3),
    "seat": k.mat("seat", "#141414", rough=0.7),
    "chrome": k.mat("chrome", "#DDE0E3", rough=0.12, metal=1.0),
    "engine": k.mat("engine", "#8C9196", rough=0.45, metal=0.8),
    "rubber": k.mat("rubber", "#121212", rough=0.85),
    "plate_y": k.mat("plate_yellow", "#F5C400", rough=0.4),
    "ink": k.mat("ink", "#111214", rough=0.6),
    "head": k.mat("headlight", "#EEF2FA", rough=0.06, emit="#FFF3DA"),
    "tail": k.mat("taillight", "#9E0E17", rough=0.12, emit="#FF1A1A"),
    "ind": k.mat("indicator", "#D47F00", rough=0.12, emit="#FF9500"),
    "glass": k.mat("glass_mirror", "#C9D3DC", rough=0.05, metal=1.0),
}

# ── Wheel (spoked), used front and rear ──────────────────────────────────
bm = bmesh.new()
tyre = [(-0.040, 0.218), (0.040, 0.218), (0.046, 0.25), (0.036, 0.29), (0.0, WR), (-0.036, 0.29), (-0.046, 0.25)]
tf = lathe(bm, tyre, (0, 0, 0), "x", 36, [0] * len(tyre))
bmesh.ops.recalc_face_normals(bm, faces=tf)
rim = [(-0.030, 0.205), (0.030, 0.205), (0.034, 0.22), (-0.034, 0.22)]
rf = lathe(bm, rim, (0, 0, 0), "x", 36, [1] * 4)
bmesh.ops.recalc_face_normals(bm, faces=rf)
hub = [(-0.055, 0.0), (-0.055, 0.055), (0.055, 0.055), (0.055, 0.0)]
hf = lathe(bm, hub, (0, 0, 0), "x", 18, [2] * 4)
for f in hf:
    f.normal_update()
for i in range(36):
    a = 2 * math.pi * i / 36
    side = 1 if i % 2 else -1
    p0 = Vector((side * 0.045, 0.05 * math.cos(a + 0.2), 0.05 * math.sin(a + 0.2)))
    p1 = Vector((side * 0.012, 0.207 * math.cos(a), 0.207 * math.sin(a)))
    tube(bm, p0, p1, 0.0022, 4, 1, caps=False)
front_wheel = k.add("wheel_f", bm, [M["rubber"], M["chrome"], M["engine"]], group="wheel_f", location=(0, YF, WR))
k.instance("wheel_r", front_wheel, (0, YR, WR))

# ── Frame, tank, seat, engine, forks, exhaust, racks ─────────────────────
bm = bmesh.new()
# Paint: tank, side covers, mudguards.
ellipsoid(bm, (0, -0.22, 0.93), (0.15, 0.25, 0.11), 0, segs=20, rings=12)
for s in (1, -1):
    box(bm, (s * 0.12, 0.22, 0.66), (0.03, 0.28, 0.17), 0, bevel=0.03)
for yc, z0, a0, a1 in ((YF, WR, 0.35, 1.75), (YR, WR, 1.35, 2.9)):
    # Mudguard: an arc strip over the wheel (angles in the YZ plane, 0 = forward).
    pts = []
    for i in range(13):
        t = a0 + (a1 - a0) * i / 12
        pts.append(Vector((0, yc - math.cos(t) * (WR + 0.035), z0 + math.sin(t) * (WR + 0.035))))
    for i in range(12):
        p, q = pts[i], pts[i + 1]
        quad = [bm.verts.new(p + Vector((-0.05, 0, 0))), bm.verts.new(p + Vector((0.05, 0, 0))),
                bm.verts.new(q + Vector((0.05, 0, 0))), bm.verts.new(q + Vector((-0.05, 0, 0)))]
        f = bm.faces.new(quad)
        f.material_index = 0
# Black: frame, seat base, forks' lower legs, chain guard, swingarm, rack.
tube(bm, (0, -0.47, 0.98), (0, -0.30, 0.60), 0.028, 10, 1)
tube(bm, (0, -0.47, 0.98), (0, 0.10, 0.80), 0.024, 10, 1)
tube(bm, (0, 0.10, 0.80), (0, 0.80, 0.80), 0.018, 8, 1)
for s in (1, -1):
    tube(bm, (s * 0.07, YF, WR), (s * 0.07, -0.53, 0.66), 0.028, 10, 1)          # fork legs
    tube(bm, (s * 0.07, -0.53, 0.66), (s * 0.07, -0.47, 0.96), 0.022, 10, 3)     # chrome stanchions
    tube(bm, (s * 0.10, 0.02, 0.38), (s * 0.10, YR, WR), 0.022, 8, 1)            # swingarm
    tube(bm, (s * 0.115, YR - 0.02, WR + 0.02), (s * 0.125, 0.36, 0.78), 0.02, 8, 3)  # shocks
    # Crash bars (leg guards).
    tube(bm, (s * 0.06, -0.42, 0.76), (s * 0.27, -0.40, 0.62), 0.016, 8, 3)
    tube(bm, (s * 0.27, -0.40, 0.62), (s * 0.24, -0.28, 0.30), 0.016, 8, 3)
    tube(bm, (s * 0.24, -0.28, 0.30), (s * 0.08, -0.22, 0.25), 0.016, 8, 3)
    # Footpegs: rider, passenger.
    tube(bm, (s * 0.07, -0.06, 0.32), (s * 0.20, -0.06, 0.32), 0.014, 8, 2)
    tube(bm, (s * 0.10, 0.30, 0.42), (s * 0.24, 0.30, 0.42), 0.012, 8, 2)
    # Rear carrier rack.
    tube(bm, (s * 0.13, 0.62, 0.84), (s * 0.13, 0.98, 0.84), 0.012, 8, 1)
box(bm, (0, 0.80, 0.84), (0.28, 0.02, 0.02), 1)
box(bm, (0, 0.98, 0.84), (0.28, 0.02, 0.02), 1)
box(bm, (0.12, 0.30, 0.36), (0.02, 0.62, 0.08), 1, bevel=0.01)                  # chain guard (left)
# Seat: long, for two.
ellipsoid(bm, (0, 0.30, 0.82), (0.135, 0.42, 0.055), 4, segs=20, rings=10)
# Engine: crankcase, cylinder with fins, side cover.
box(bm, (0, -0.10, 0.40), (0.26, 0.34, 0.24), 2, bevel=0.05)
for i in range(6):
    box(bm, (0, -0.30, 0.50 + i * 0.035), (0.20, 0.13, 0.012), 2)
ellipsoid(bm, (0.13, -0.08, 0.40), (0.02, 0.11, 0.10), 2, segs=14, rings=8)
# Exhaust down the right side, chrome.
tube(bm, (-0.05, -0.33, 0.48), (-0.10, -0.30, 0.28), 0.022, 10, 3)
tube(bm, (-0.10, -0.30, 0.28), (-0.15, 0.20, 0.28), 0.022, 10, 3)
tube(bm, (-0.15, 0.20, 0.28), (-0.17, 0.70, 0.40), 0.045, 14, 3, r1=0.04)
# Handlebar with grips and mirrors, headlight shell, speedo.
tube(bm, (-0.34, -0.46, 1.08), (0.34, -0.46, 1.08), 0.012, 8, 3)
for s in (1, -1):
    tube(bm, (s * 0.24, -0.46, 1.08), (s * 0.36, -0.46, 1.08), 0.018, 10, 5)
    tube(bm, (s * 0.22, -0.46, 1.09), (s * 0.29, -0.44, 1.30), 0.006, 6, 3)
    ellipsoid(bm, (s * 0.30, -0.44, 1.33), (0.055, 0.015, 0.04), 7, segs=12, rings=6)
ellipsoid(bm, (0, -0.55, 1.00), (0.10, 0.10, 0.09), 0, segs=16, rings=10)
tube(bm, (0, -0.47, 1.10), (0, -0.44, 1.16), 0.045, 14, 1)
# Plate (Kenyan motorcycle plates are yellow at the rear).
box(bm, (0, 0.99, 0.62), (0.22, 0.01, 0.13), 6)
k.add("bike", bm, [M["paint"], M["black"], M["engine"], M["chrome"], M["seat"], M["rubber"], M["plate_y"], M["glass"]])
k.text("KMEB", 0.045, (0, 1.0, 0.65), (math.radians(90), 0, math.radians(180)), M["ink"], thicken=0.003)
k.text("342Y", 0.045, (0, 1.0, 0.595), (math.radians(90), 0, math.radians(180)), M["ink"], thicken=0.003)

bm = bmesh.new()
box(bm, (0, -0.64, 1.00), (0.15, 0.02, 0.12), 0, bevel=0.03)
box(bm, (0, 1.0, 0.74), (0.12, 0.04, 0.06), 1, bevel=0.01)
for s in (1, -1):
    box(bm, (s * 0.14, -0.58, 0.98), (0.04, 0.05, 0.03), 2, bevel=0.008)
    box(bm, (s * 0.12, 0.98, 0.76), (0.04, 0.05, 0.03), 2, bevel=0.008)
k.add("lights", bm, [M["head"], M["tail"], M["ind"]], smooth=False, group="lights")

# ── Rider and passenger ──────────────────────────────────────────────────
skin1 = k.mat("skin_rider", "#5A3820", rough=0.6)
skin2 = k.mat("skin_passenger", "#6E4528", rough=0.6)
rider = seated_pose(pelvis=(0, 0.04, 0.92), lean=16, hands=(0.31, -0.46, 1.08),
                    ankles=((0.17, -0.07, 0.36), (-0.17, -0.07, 0.36)), toes=((0.17, -0.21, 0.33), (-0.17, -0.21, 0.33)))
person(k, "rider", rider, {
    "skin": skin1, "helmet": k.mat("helmet_rider", "#16181B", rough=0.2, coat=0.8), "visor": k.mat("visor", "#0B0E12", rough=0.04),
    "top": k.mat("jacket", "#1F2A44", rough=0.7), "sleeves": k.mat("sleeves", "#1F2A44", rough=0.7),
    "trousers": k.mat("trousers", "#2E3136", rough=0.75), "shoes": k.mat("shoes", "#141414", rough=0.6),
    "vest": k.mat("vest", "#C6F23A", rough=0.5, emit="#C6F23A", emit_strength=0.08), "stripe": k.mat("reflective", "#C9CDD2", rough=0.25, metal=0.6),
}, vest=True)
passenger = seated_pose(pelvis=(0, 0.44, 0.95), lean=4, hands=(0.15, 0.24, 0.98),
                        ankles=((0.20, 0.31, 0.45), (-0.20, 0.31, 0.45)), toes=((0.20, 0.18, 0.43), (-0.20, 0.18, 0.43)))
person(k, "passenger", passenger, {
    "skin": skin2, "helmet": k.mat("helmet_passenger", "#E9EDF1", rough=0.25, coat=0.8), "visor": k.mat("visor", "#0B0E12"),
    "top": k.mat("shirt", "#E2671B", rough=0.75), "sleeves": k.mat("shirt", "#E2671B"),
    "trousers": k.mat("jeans", "#2E4A7A", rough=0.8), "shoes": k.mat("shoes", "#141414"),
})

k.finish(bake={"body": 1024, "wheel_f": 512, "rider": 512, "passenger": 512}, dust=(0.0, 0.5, 0.35), ao_distance=0.25)
