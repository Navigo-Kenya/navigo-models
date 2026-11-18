"""Nairobi commuter DMU car (metre gauge): 19 x 2.8 m, cab at the front, white with
Kenya Railways red and green. The app runs two back to back (the second turned round)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, box, face_toward, rounded_rect  # noqa: E402
from rail import body, bogie, windows  # noqa: E402

k = Kit("train_commuter", "Commuter train car")
L, W = 19.0, 2.80
ZS, ZE, ZR = 0.85, 3.05, 3.70
NOSE = 1.5


def nose(y):
    d = y + L / 2                           # cab at the front (-Y) only
    if d >= NOSE:
        return 1.0, 0.0
    t = 1 - d / NOSE
    return 1 - 0.07 * t ** 2, 1.05 * t ** 1.5


ys = sorted({*(-L / 2 + i * 0.15 for i in range(11)), *(-L / 2 + NOSE + i * (L - NOSE) / 12 for i in range(13))})
M = [k.mat("paint", "#F4F4F1", rough=0.2, coat=0.8), k.mat("band_red", "#C1121F", rough=0.25, coat=0.7),
     k.mat("roof", "#5B6066", rough=0.5, metal=0.3), k.mat("underbody", "#1C1D20", rough=0.8),
     k.mat("band_green", "#0B7A3E", rough=0.25, coat=0.7)]
body(k, "shell", L, W, ZS, ZE, ZR, [(1.18, 1.52, 1), (1.56, 1.64, 4)], {"under": 3, "roof": 2}, M, nose=nose, y_steps=ys)


def roof_point(x, y):
    sx, drop = nose(y)
    hw = W / 2 * sx
    zr = ZR - drop
    t = min(1.0, abs(x) / hw)
    return Vector((x, y, ZE + (zr - ZE) * math.sqrt(max(0.0, 1 - t ** 2.2))))


glass = k.mat("glass", "#0B1118", rough=0.04)
bm = bmesh.new()
windows(bm, W / 2, [-4.6 + i * 1.65 for i in range(8)] + [-7.2], 1.85, 2.65, 1.25, 0)
y_out, y_in = -L / 2 + 0.12, -L / 2 + 0.85
quad = [roof_point(-1.05, y_out), roof_point(1.05, y_out), roof_point(1.0, y_in), roof_point(-1.0, y_in)]
face_toward(bm, [bm.verts.new(p + Vector((0, -0.02, 0.02))) for p in quad], (0, -1, 0.6))
k.add("glass", bm, [glass], smooth=False, group="glass")

dark = k.mat("door", "#2A2D31", rough=0.5)
metal = k.mat("metal", "#3B3F44", rough=0.5, metal=0.6)
wheel = k.mat("wheel", "#6F757B", rough=0.35, metal=0.9)
bm = bmesh.new()
for y in (-5.9, 4.9):                        # sliding doors with windows
    for s in (1, -1):
        face_toward(bm, [bm.verts.new((s * (W / 2 + 0.010), y + u, z)) for u, z in rounded_rect(-0.65, 1.0, 0.65, 2.85, 0.05)],
                    (s, 0, 0), 0)
box(bm, (0, L / 2 + 0.2, 2.1), (1.1, 0.4, 2.1), 0, bevel=0.05)   # rear gangway
box(bm, (0, -L / 2 - 0.10, 0.95), (W * 0.9, 0.2, 0.32), 0, bevel=0.04)
box(bm, (0, -L / 2 - 0.32, 0.88), (0.3, 0.4, 0.22), 1, bevel=0.03)
box(bm, (0, L / 2 + 0.30, 0.88), (0.3, 0.4, 0.22), 1, bevel=0.03)
for y in (-2.0, 1.5):
    box(bm, (0, y, 0.62), (2.0, 2.6, 0.45), 1, bevel=0.03)
box(bm, (0, 2.0, ZR + 0.1), (1.6, 3.0, 0.24), 1, bevel=0.06)
for y in (-6.4, 6.4):
    bogie(bm, y, 0.5, 0.42, 2, 2.1, 1, 2)
k.add("trim", bm, [dark, metal, wheel])

lights = [k.mat("headlight", "#EEF2FA", rough=0.06, emit="#FFF3DA"), k.mat("taillight", "#9E0E17", rough=0.12, emit="#FF1A1A")]
bm = bmesh.new()
for x in (-0.95, 0.95):
    box(bm, (x, -L / 2 - 0.005, 1.45), (0.28, 0.04, 0.14), 0, bevel=0.03)
    box(bm, (x, L / 2 + 0.005, 1.45), (0.18, 0.04, 0.10), 1, bevel=0.02)
k.add("lights", bm, lights, smooth=False, group="lights")
for s in (1, -1):
    k.text("NAIROBI COMMUTER", 0.16, (s * (W / 2 + 0.006), 0.6, 1.35), (math.radians(90), 0, math.radians(90 if s > 0 else -90)),
           k.mat("ink_white", "#F7F7F5", rough=0.4), thicken=0.006)

k.finish(bake={"body": 1024}, dust=(0.0, 1.2, 0.35), ao_distance=0.8)
