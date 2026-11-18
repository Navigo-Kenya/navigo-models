"""Car: a compact 5-door wagon in the Toyota Probox class (4.25 x 1.69 m, 2.55 m wheelbase).

Paint is the "paint" material (white; recoloured to the user's car colour).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, arch, box, face_toward, fillet, lathe, rounded_rect, tube  # noqa: E402

k = Kit("car", "Car (compact wagon)")

L, W = 4.25, 1.69
Y0 = -L / 2
ZB = 0.24
WHEEL_R = 0.292
TRACK_HALF = 0.735
AXLE_F, AXLE_R = 0.80, 3.35
ARCH_R = 0.335
BELT, WIN_TOP = 0.98, 1.37
CREASE, ROOF = 0.93, 1.52
TUMBLEHOME, CROWN = 0.13, 0.03


def y_of(s):
    return Y0 + s


def plan(s):
    """Plan-view taper: the nose and tail are narrower (rounded corners)."""
    if s < 0.55:
        return 1 - 0.09 * ((0.55 - s) / 0.55) ** 1.6
    if s > 3.95:
        return 1 - 0.05 * ((s - 3.95) / 0.3) ** 1.6
    return 1.0


def half_width(z, s=2.0):
    hw = W / 2 * plan(s)
    if z <= CREASE:
        return hw
    return hw * (1 - TUMBLEHOME * min(1.0, (z - CREASE) / (ROOF - CREASE)))


def side_x(side, z, s, out=0.0):
    return side * (half_width(z, s) + out)


M = {
    "paint": k.mat("paint", "#F2F2EE", rough=0.22, coat=0.8),
    "under": k.mat("underbody", "#141414", rough=0.9),
    "glass": k.mat("glass", "#0B1118", rough=0.03),
    "rubber": k.mat("rubber", "#131313", rough=0.85),
    "plastic": k.mat("plastic", "#2A2C30", rough=0.6),
    "chrome": k.mat("chrome", "#DADDE0", rough=0.14, metal=1.0),
    "head": k.mat("headlight", "#EEF2FA", rough=0.06, emit="#FFF3DA"),
    "reflector": k.mat("reflector", "#9AA3AE", rough=0.12, metal=1.0),
    "tail": k.mat("taillight", "#9E0E17", rough=0.12, emit="#FF1A1A"),
    "ind": k.mat("indicator", "#D47F00", rough=0.12, emit="#FF9500"),
    "plate_w": k.mat("plate_white", "#F5F5F1", rough=0.4),
    "plate_y": k.mat("plate_yellow", "#F5C400", rough=0.4),
    "ink": k.mat("ink", "#111214", rough=0.6),
    "rim": k.mat("rim", "#3A3D41", rough=0.4, metal=0.7),
    "hub": k.mat("hubcap", "#C3C7CB", rough=0.25, metal=0.9),
}

outline = [
    ((0.06, 0.25), 0.05), ((0.00, 0.48), 0.09), ((0.05, 0.74), 0.07), ((0.95, 0.88), 0.06),
    ((1.70, 1.45), 0.20), ((2.20, 1.52), 0.5), ((4.12, 1.50), 0.09), ((4.25, 1.40), 0.07),
    ((4.22, 0.30), 0.07), ((4.15, ZB), 0.02),
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
for z in (CREASE, 0.55):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1))
for x in (-0.6, -0.3, 0.0, 0.3, 0.6):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x, 0, 0), plane_no=(1, 0, 0))
for s in (0.15, 0.3, 0.45, 3.95, 4.1):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y_of(s), 0), plane_no=(0, 1, 0))
for v in bm.verts:
    s = v.co.y - Y0
    z = v.co.z
    v.co.x *= half_width(z, s) / (W / 2)
    if z > ROOF - 0.07:
        hw = half_width(ROOF, s)
        v.co.z += CROWN * max(0.0, 1 - (v.co.x / hw) ** 2) * min(1.0, (z - (ROOF - 0.07)) / 0.07)
bm.normal_update()
for f in bm.faces:
    c = f.calc_center_median()
    nrm = f.normal
    near_arch = min(abs(c.y - y_of(AXLE_F)), abs(c.y - y_of(AXLE_R))) <= ARCH_R + 0.02
    f.material_index = 1 if abs(nrm.x) <= 0.9 and (nrm.z < -0.6 or (near_arch and c.z < WHEEL_R + ARCH_R + 0.01)) else 0
shell = k.add("shell", bm, [M["paint"], M["under"]])
k.bevel(shell, 0.04, segments=4)


def a_s(z, inset):
    """The A-pillar line (windshield edge) moved back by inset."""
    return 0.95 + inset + (z - 0.88) * (0.75 / 0.57)


win1 = fillet([(a_s(BELT, 0.13), BELT), (2.12, BELT), (2.12, WIN_TOP), (a_s(WIN_TOP, 0.13), WIN_TOP)], [0.03, 0.03, 0.04, 0.06], 5)
win2 = rounded_rect(2.22, BELT, 3.08, WIN_TOP, 0.03)
win3 = fillet([(3.18, BELT), (3.98, BELT), (3.96, WIN_TOP - 0.02), (3.18, WIN_TOP)], [0.03, 0.06, 0.06, 0.03], 5)
bm = bmesh.new()
for side in (1, -1):
    for poly in (win1, win2, win3):
        face_toward(bm, [bm.verts.new((side_x(side, z, s, 0.006), y_of(s), z)) for s, z in poly], (side, 0, 0.12))
# Windshield on its plane, inside the A-pillars (the glass narrows with the tumblehome).
wb, wt = Vector((0, y_of(0.95), 0.88)), Vector((0, y_of(1.70), 1.45))
wdir = (wt - wb).normalized()
wn = Vector((0, -(wt - wb).z, (wt - wb).y)).normalized()
wl = (wt - wb).length
ws = []
for u, v in fillet([(-0.70, 0.06), (0.70, 0.06), (0.58, wl - 0.10), (-0.58, wl - 0.10)], [0.04, 0.04, 0.08, 0.08], 5):
    ws.append(bm.verts.new(wb + Vector((u, 0, 0)) + wdir * v + wn * 0.006))
face_toward(bm, ws, wn)
rear = fillet([(-0.60, 0.98), (0.60, 0.98), (0.54, 1.36), (-0.54, 1.36)], [0.04, 0.04, 0.06, 0.06], 5)
# Just outside the tailgate, which leans back 3 cm over its height.
face_toward(bm, [bm.verts.new((x, y_of(4.25) + 0.008 - (1.40 - z) * 0.027, z)) for x, z in rear], (0, 1, 0.03))
k.add("glass", bm, [M["glass"]], smooth=False, group="glass")

bm = bmesh.new()
for side in (1, -1):
    for poly in (win1, win2, win3):
        cs = sum(p[0] for p in poly) / len(poly)
        cz = sum(p[1] for p in poly) / len(poly)
        big = [(s + (0.016 if s > cs else -0.016), z + (0.016 if z > cz else -0.016)) for s, z in poly]
        face_toward(bm, [bm.verts.new((side_x(side, z, s, 0.003), y_of(s), z)) for s, z in big], (side, 0, 0.12), 2)
    for s0 in (1.16, 2.17, 3.13):                                         # door gaps
        for za, zb in ((0.30, CREASE), (CREASE, 1.40)):
            face_toward(bm, [bm.verts.new((side_x(side, z, s, 0.003), y_of(s), z))
                             for s, z in ((s0, za), (s0 + 0.012, za), (s0 + 0.012, zb), (s0, zb))], (side, 0, 0), 2)
    for s in (1.95, 2.95):                                                # door handles
        box(bm, (side_x(side, 0.88, s, 0.012), y_of(s), 0.88), (0.02, 0.13, 0.03), 0, bevel=0.006)
    box(bm, (side * 0.95, y_of(1.20), 1.02), (0.12, 0.10, 0.11), 0, bevel=0.025)   # mirrors
    box(bm, (side_x(side, 0.40, 2.0, 0.01), y_of(2.1), 0.36), (0.02, 2.2, 0.05), 0, bevel=0.01)   # sill trim
    for s_axle in (AXLE_F, AXLE_R):
        box(bm, (side * TRACK_HALF, y_of(s_axle + 0.38), 0.20), (0.18, 0.012, 0.18), 2)
# Bumpers, grille, plates, wipers.
box(bm, (0, y_of(0.07), 0.38), (1.62, 0.20, 0.22), 0, bevel=0.06)
box(bm, (0, y_of(0.03), 0.60), (0.90, 0.05, 0.12), 0, bevel=0.015)
box(bm, (0, y_of(0.005), 0.64), (0.90, 0.03, 0.02), 1, bevel=0.005)
box(bm, (0, y_of(4.18), 0.40), (1.62, 0.18, 0.20), 0, bevel=0.06)
box(bm, (0, y_of(-0.035), 0.38), (0.48, 0.012, 0.11), 3)
box(bm, (0, y_of(4.25) + 0.012, 0.66), (0.48, 0.012, 0.11), 4)
for x in (-0.30, 0.25):
    tube(bm, (x - 0.24, y_of(0.98), 0.90), (x + 0.24, y_of(1.04), 0.94), 0.008, 6, 0)
tube(bm, (-0.25, y_of(4.27), 1.0), (0.22, y_of(4.27), 1.04), 0.007, 6, 0)
tube(bm, (-0.55, y_of(3.6), 1.53), (-0.55, y_of(3.75), 1.95), 0.004, 6, 0)          # roof antenna
k.add("trim", bm, [M["plastic"], M["chrome"], M["rubber"], M["plate_w"], M["plate_y"]])
k.text("KDN 512C", 0.07, (0, y_of(-0.042), 0.38), (math.radians(90), 0, 0), M["ink"], thicken=0.004)
k.text("KDN 512C", 0.07, (0, y_of(4.25) + 0.019, 0.66), (math.radians(90), 0, math.radians(180)), M["ink"], thicken=0.004)

bm = bmesh.new()
for side in (1, -1):
    box(bm, (side * 0.58, y_of(0.06), 0.64), (0.30, 0.06, 0.12), 0, bevel=0.02)
    box(bm, (side * 0.54, y_of(0.085), 0.64), (0.10, 0.02, 0.08), 3, bevel=0.008)
    box(bm, (side * 0.76, y_of(0.13), 0.63), (0.06, 0.08, 0.10), 2, bevel=0.012)
    box(bm, (side * 0.74, y_of(4.25) + 0.0, 1.05), (0.10, 0.05, 0.38), 1, bevel=0.015)
k.add("lights", bm, [M["head"], M["tail"], M["ind"], M["reflector"]], smooth=False, group="lights")

tyre = fillet([(-0.082, 0.18), (0.082, 0.18), (0.0875, 0.255), (0.07, WHEEL_R), (-0.07, WHEEL_R), (-0.0875, 0.255)],
              [0, 0, 0.025, 0.03, 0.03, 0.025], 5)
rim = [(0.072, 0.181), (0.079, 0.172), (0.062, 0.150), (0.05, 0.12), (0.05, 0.06), (0.068, 0.05), (0.076, 0.0005)]
bm = bmesh.new()
tf = lathe(bm, tyre, (0, 0, 0), "x", 32, [0] * len(tyre))
bmesh.ops.recalc_face_normals(bm, faces=tf)
for f in lathe(bm, rim, (0, 0, 0), "x", 32, [1, 1, 1, 2, 2, 2], closed=False):
    f.normal_update()
    if f.normal.x < 0:
        f.normal_flip()
wheel = k.add("wheel_fl", bm, [M["rubber"], M["rim"], M["hub"]], group="wheel_fl", location=(TRACK_HALF, y_of(AXLE_F), WHEEL_R))
k.instance("wheel_rl", wheel, (TRACK_HALF, y_of(AXLE_R), WHEEL_R))
k.instance("wheel_fr", wheel, (-TRACK_HALF, y_of(AXLE_F), WHEEL_R), (0, 0, math.pi))
k.instance("wheel_rr", wheel, (-TRACK_HALF, y_of(AXLE_R), WHEEL_R), (0, 0, math.pi))

k.finish(bake={"body": 1024, "wheel_fl": 512}, dust=(0.0, 0.7, 0.4))
