"""Matatu: a 14-seater on a Toyota HiAce H200 body (5.38 x 1.88 m, 3.11 m wheelbase).

SACCO livery: white, NTSA yellow band, the route colour below it ("livery",
recoloured per route by the app). Sliding door on the nearside (left).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, arch, box, face_toward, fillet, lathe, rounded_rect, tube  # noqa: E402

k = Kit("matatu", "Matatu (14-seater)")

L, W = 5.38, 1.88
Y0 = -L / 2
ZB = 0.32
WHEEL_R, TIRE_W = 0.345, 0.195
TRACK_HALF = 0.825
AXLE_F, AXLE_R = 1.00, 4.11
ARCH_R = 0.40
BAND_LO, BAND_HI = 0.86, 0.96
BELT, WIN_TOP = 1.20, 1.94
CREASE, ROOF = 1.16, 2.21
TUMBLEHOME, CROWN = 0.06, 0.035


def y_of(s):
    return Y0 + s


def half_width(z):
    if z <= CREASE:
        return W / 2
    return W / 2 * (1 - TUMBLEHOME * min(1.0, (z - CREASE) / (ROOF - CREASE)))


def side_x(side, z, out=0.0):
    return side * (half_width(z) + out)


M = {
    "paint": k.mat("paint", "#EFEFEA", rough=0.24, coat=0.6),
    "livery": k.mat("livery", "#12805C", rough=0.26, coat=0.6),
    "band": k.mat("band_yellow", "#F2C200", rough=0.3, coat=0.4),
    "under": k.mat("underbody", "#141414", rough=0.9),
    "glass": k.mat("glass", "#0A0F15", rough=0.04),
    "rubber": k.mat("rubber", "#131313", rough=0.85),
    "plastic": k.mat("plastic", "#24262A", rough=0.55),
    "chrome": k.mat("chrome", "#DADDE0", rough=0.14, metal=1.0),
    "rim": k.mat("rim", "#B5B9BE", rough=0.3, metal=0.9),
    "hub": k.mat("hubcap", "#C8CCD0", rough=0.22, metal=0.95),
    "head": k.mat("headlight", "#EEF2FA", rough=0.06, emit="#FFF3DA"),
    "reflector": k.mat("reflector", "#9AA3AE", rough=0.12, metal=1.0),
    "tail": k.mat("taillight", "#9E0E17", rough=0.12, emit="#FF1A1A"),
    "ind": k.mat("indicator", "#D47F00", rough=0.12, emit="#FF9500"),
    "plate_w": k.mat("plate_white", "#F5F5F1", rough=0.4),
    "plate_y": k.mat("plate_yellow", "#F5C400", rough=0.4),
    "ink": k.mat("ink", "#111214", rough=0.6),
    "sign": k.mat("route_sign", "#FAFAF7", rough=0.5),
}

# ── Body ─────────────────────────────────────────────────────────────────
outline = [
    ((0.05, 0.34), 0.05), ((0.00, 0.62), 0.10), ((0.06, 1.03), 0.07), ((0.44, 1.13), 0.05),
    ((1.24, 2.11), 0.22), ((1.70, 2.21), 0.60), ((5.31, 2.21), 0.10), ((5.38, 2.10), 0.06),
    ((5.37, 0.38), 0.05), ((5.30, ZB), 0.03),
]
pts, radii = zip(*outline)
profile = fillet(list(pts), list(radii), seg=6)
profile += arch(AXLE_R, WHEEL_R, ARCH_R, ZB)
profile += arch(AXLE_F, WHEEL_R, ARCH_R, ZB)
profile.append((0.10, ZB))

bm = bmesh.new()
left = [bm.verts.new((W / 2, y_of(s), z)) for s, z in profile]
right = [bm.verts.new((-W / 2, y_of(s), z)) for s, z in profile]
bm.faces.new(left)
bm.faces.new(list(reversed(right)))
n = len(profile)
for i in range(n):
    j = (i + 1) % n
    bm.faces.new((left[i], left[j], right[j], right[i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
for z in (BAND_LO, BAND_HI, CREASE):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1))
for x in (-0.66, -0.33, 0.0, 0.33, 0.66):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x, 0, 0), plane_no=(1, 0, 0))
for v in bm.verts:
    z = v.co.z
    if z > CREASE + 1e-4:
        v.co.x *= half_width(z) / (W / 2)
    if z > ROOF - 0.08:
        hw = half_width(ROOF)
        v.co.z += CROWN * max(0.0, 1 - (v.co.x / hw) ** 2) * min(1.0, (z - (ROOF - 0.08)) / 0.08)
bm.normal_update()
for f in bm.faces:
    c = f.calc_center_median()
    nrm = f.normal
    near_arch = min(abs(c.y - y_of(AXLE_F)), abs(c.y - y_of(AXLE_R))) <= ARCH_R + 0.02
    if abs(nrm.x) <= 0.9 and (nrm.z < -0.6 or (near_arch and c.z < WHEEL_R + ARCH_R + 0.01)):
        f.material_index = 3
    elif c.z < BAND_LO:
        f.material_index = 1
    elif c.z < BAND_HI:
        f.material_index = 2
    else:
        f.material_index = 0
body = k.add("shell", bm, [M["paint"], M["livery"], M["band"], M["under"]])
k.bevel(body, 0.055, segments=4)

# ── Glass ────────────────────────────────────────────────────────────────


def a_pillar_s(z, inset):
    return 0.44 + inset + (z - 1.13) * (0.80 / 0.98)


win_front = fillet([(a_pillar_s(BELT, 0.16), BELT), (1.56, BELT), (1.56, WIN_TOP - 0.02),
                    (a_pillar_s(WIN_TOP - 0.02, 0.16), WIN_TOP - 0.02)], [0.04, 0.05, 0.05, 0.08], 5)
windows = [win_front, rounded_rect(1.68, BELT, 2.72, WIN_TOP, 0.06), rounded_rect(2.84, BELT, 3.86, WIN_TOP, 0.06),
           rounded_rect(3.98, BELT, 4.98, WIN_TOP, 0.06), rounded_rect(5.08, BELT, 5.24, WIN_TOP, 0.04)]

bm = bmesh.new()
for side in (1, -1):
    for poly in windows:
        face_toward(bm, [bm.verts.new((side_x(side, z, 0.006), y_of(s), z)) for s, z in poly], (side, 0, 0.06))
ws_dir = Vector((0, 0.80, 0.98)).normalized()
ws_n = Vector((0, -0.98, 0.80)).normalized()
base = Vector((0, y_of(0.44), 1.13))
ws_len = Vector((0, 0.80, 0.98)).length
ws_poly = fillet([(-0.80, 0.10), (0.80, 0.10), (0.74, ws_len - 0.17), (-0.74, ws_len - 0.17)], [0.05, 0.05, 0.10, 0.10], 5)
face_toward(bm, [bm.verts.new(base + Vector((u, 0, 0)) + ws_dir * v + ws_n * 0.006) for u, v in ws_poly], ws_n)
rw = fillet([(-0.72, 1.30), (0.72, 1.30), (0.72, 1.98), (-0.72, 1.98)], [0.06] * 4, 5)
face_toward(bm, [bm.verts.new((u, y_of(5.38) + 0.006, z)) for u, z in rw], (0, 1, 0))
k.add("glass", bm, [M["glass"]], smooth=False, group="glass")

# ── Seals, door gaps, rails, trim (all on the body) ──────────────────────
bm = bmesh.new()
for side in (1, -1):
    for poly in windows:
        cs = sum(p[0] for p in poly) / len(poly)
        cz = sum(p[1] for p in poly) / len(poly)
        big = [(s + (0.018 if s > cs else -0.018), z + (0.018 if z > cz else -0.018)) for s, z in poly]
        face_toward(bm, [bm.verts.new((side_x(side, z, 0.003), y_of(s), z)) for s, z in big], (side, 0, 0.06))


def strip(side, s0, s1, z0, z1, out=0.003, mat=0):
    zs = [z0] + ([CREASE] if z0 < CREASE < z1 else []) + [z1]
    for za, zb in zip(zs, zs[1:]):
        face_toward(bm, [bm.verts.new((side_x(side, z, out), y_of(s), z)) for s, z in ((s0, za), (s1, za), (s1, zb), (s0, zb))],
                    (side, 0, 0), mat)


strip(1, 1.62, 1.636, 0.40, 2.00)            # sliding door
strip(1, 2.78, 2.796, 0.40, 2.00)
strip(1, 1.62, 2.796, 1.995, 2.011)
strip(1, 2.80, 5.05, 1.105, 1.125)           # sliding door rail
strip(-1, 1.60, 1.616, 0.42, 1.98)           # driver's door
strip(-1, 0.62, 0.636, 0.42, 1.10)
strip(1, 0.62, 0.636, 0.42, 1.10)            # passenger front door
seals = k.add("seals", bm, [M["rubber"]], smooth=False)

bm = bmesh.new()
for side in (1, -1):
    # Chrome beltline trim under the windows.
    box(bm, (side_x(side, 1.17, 0.006), y_of(3.2), 1.17), (0.012, 4.1, 0.018), 1)
    # Door handles.
    for s in (1.45, 2.55):
        box(bm, (side * (W / 2 + 0.012), y_of(s), 1.06), (0.018, 0.14, 0.035), 0, bevel=0.006)
    # Side marker lamp, fuel flap (offside only), mirrors.
    box(bm, (side_x(side, 0.70, 0.008), y_of(0.55), 0.70), (0.012, 0.07, 0.035), 4)
    box(bm, (side * 1.00, y_of(0.74), 1.33), (0.14, 0.035, 0.035), 0)
    box(bm, (side * 1.08, y_of(0.74), 1.40), (0.06, 0.15, 0.24), 0, bevel=0.02)
    # Roof gutters.
    box(bm, (side_x(side, ROOF - 0.04, -0.03), y_of(3.4), ROOF - 0.035), (0.03, 3.7, 0.025), 0, bevel=0.008)
    # Mud flaps.
    for s_axle in (AXLE_F, AXLE_R):
        box(bm, (side * TRACK_HALF, y_of(s_axle + 0.47), 0.26), (0.20, 0.012, 0.30), 2)
box(bm, (-(W / 2 + 0.006), y_of(4.55), 1.02), (0.012, 0.16, 0.12), 0, bevel=0.01)
# Front: bumper, grille with slats and chrome bar, plate; rear: bumper, plate.
box(bm, (0, y_of(0.09), 0.43), (1.94, 0.26, 0.24), 0, bevel=0.05)
box(bm, (0, y_of(0.03), 0.71), (0.80, 0.05, 0.17), 0, bevel=0.012)
for z in (0.66, 0.71, 0.76):
    box(bm, (0, y_of(0.0), z), (0.74, 0.02, 0.014), 1)
box(bm, (0, y_of(0.008), 0.815), (0.84, 0.03, 0.028), 1, bevel=0.008)
box(bm, (0, y_of(-0.045), 0.43), (0.52, 0.012, 0.12), 3)
box(bm, (0, y_of(5.36), 0.42), (1.94, 0.20, 0.22), 0, bevel=0.05)
box(bm, (0, y_of(5.38) + 0.01, 0.62), (0.52, 0.012, 0.12), 5)
# Wipers, rear wiper.
for x in (-0.38, 0.30):
    tube(bm, (x - 0.26, y_of(0.52), 1.22), (x + 0.26, y_of(0.60), 1.30), 0.009, 6, 0)
tube(bm, (-0.30, y_of(5.395), 1.36), (0.25, y_of(5.395), 1.40), 0.008, 6, 0)
# Route card stuck on the windshield, top nearside corner.
card = [(0.32, ws_len - 0.42), (0.64, ws_len - 0.42), (0.64, ws_len - 0.25), (0.32, ws_len - 0.25)]
face_toward(bm, [bm.verts.new(base + Vector((u, 0, 0)) + ws_dir * v + ws_n * 0.010) for u, v in card], ws_n, 6)
k.add("trim", bm, [M["plastic"], M["chrome"], M["rubber"], M["plate_w"], M["ind"], M["plate_y"], M["sign"]])

# Plates and the SACCO name (text decals).
k.text("KDN 248V", 0.075, (0, y_of(-0.052), 0.43), (math.radians(90), 0, 0), M["ink"], thicken=0.004)
k.text("KDN 248V", 0.075, (0, y_of(5.38) + 0.017, 0.62), (math.radians(90), 0, math.radians(180)), M["ink"], thicken=0.004)
k.text("NAVIGO SACCO", 0.07, (side_x(1, 0.91, 0.004), y_of(3.35), 0.911), (math.radians(90), 0, math.radians(90)), M["ink"], thicken=0.003)
k.text("NAVIGO SACCO", 0.07, (side_x(-1, 0.91, 0.004), y_of(3.35), 0.911), (math.radians(90), 0, math.radians(-90)), M["ink"], thicken=0.003)
tilt = math.atan2(-ws_n.y, ws_n.z)                  # the windshield's tilt: text faces out of the glass
k.text("46", 0.12, base + Vector((0.48, 0, 0)) + ws_dir * (ws_len - 0.335) + ws_n * 0.012, (tilt, 0, 0), M["ink"], thicken=0.006)

# ── Lights ───────────────────────────────────────────────────────────────
bm = bmesh.new()
for side in (1, -1):
    box(bm, (side * 0.66, y_of(0.035), 0.88), (0.38, 0.05, 0.16), 0, bevel=0.025)       # lens
    box(bm, (side * 0.62, y_of(0.055), 0.88), (0.12, 0.02, 0.11), 3, bevel=0.01)          # reflector
    box(bm, (side * 0.90, y_of(0.06), 0.88), (0.07, 0.05, 0.14), 2, bevel=0.015)
    box(bm, (side * 0.82, y_of(-0.03), 0.47), (0.10, 0.04, 0.05), 2, bevel=0.01)
    box(bm, (side * 0.80, y_of(5.38) + 0.012, 1.06), (0.14, 0.04, 0.42), 1, bevel=0.015)
    box(bm, (side * 0.80, y_of(5.38) + 0.012, 0.78), (0.14, 0.04, 0.12), 2, bevel=0.012)
k.add("lights", bm, [M["head"], M["tail"], M["ind"], M["reflector"]], smooth=False, group="lights")

# ── Wheels: one baked wheel, three instances ─────────────────────────────
tyre = fillet([(-0.092, 0.215), (0.092, 0.215), (0.0975, 0.305), (0.078, WHEEL_R), (-0.078, WHEEL_R), (-0.0975, 0.305)],
              [0.0, 0.0, 0.03, 0.035, 0.035, 0.03], 5)
rim = [(0.080, 0.216), (0.088, 0.205), (0.070, 0.185), (0.058, 0.150), (0.056, 0.095), (0.064, 0.082), (0.080, 0.075),
       (0.084, 0.040), (0.086, 0.0005)]
bm = bmesh.new()
tyre_faces = lathe(bm, tyre, (0, 0, 0), "x", 36, [0] * len(tyre))
bmesh.ops.recalc_face_normals(bm, faces=tyre_faces)
rim_faces = lathe(bm, rim, (0, 0, 0), "x", 36, [1, 1, 1, 1, 1, 1, 2, 2], closed=False)
for f in rim_faces:
    f.normal_update()
    if f.normal.x < 0:
        f.normal_flip()
for a in range(6):                                  # wheel nuts
    ang = 2 * math.pi * a / 6
    c = (0.09, 0.105 * math.cos(ang), 0.105 * math.sin(ang))
    tube(bm, (c[0] - 0.012, c[1], c[2]), (c[0] + 0.012, c[1], c[2]), 0.012, 6, 2)
wheel = k.add("wheel_fl", bm, [M["rubber"], M["rim"], M["hub"]], group="wheel_fl",
              location=(TRACK_HALF, y_of(AXLE_F), WHEEL_R))
k.instance("wheel_rl", wheel, (TRACK_HALF, y_of(AXLE_R), WHEEL_R))
k.instance("wheel_fr", wheel, (-TRACK_HALF, y_of(AXLE_F), WHEEL_R), (0, 0, math.pi))
k.instance("wheel_rr", wheel, (-TRACK_HALF, y_of(AXLE_R), WHEEL_R), (0, 0, math.pi))

k.finish(bake={"body": 1024, "wheel_fl": 512}, dust=(0.0, 1.0, 0.45))
