"""SGR diesel locomotive (DF11 class, double cab, Co-Co): 21.25 x 3.3 m, white with orange."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, box, face_toward  # noqa: E402
from rail import body, bogie  # noqa: E402

k = Kit("train_sgr_loco", "SGR locomotive")
L, W = 21.25, 3.30
ZS, ZE, ZR = 1.05, 3.75, 4.55
NOSE = 1.3


def nose(y):
    d = L / 2 - abs(y)
    if d >= NOSE:
        return 1.0, 0.0
    t = 1 - d / NOSE
    return 1 - 0.05 * t ** 2, 1.25 * t ** 1.7


ys = sorted({*(-L / 2 + i * 0.13 for i in range(11)), *(L / 2 - i * 0.13 for i in range(11)),
             *(-L / 2 + NOSE + i * (L - 2 * NOSE) / 12 for i in range(13))})
M = [k.mat("paint", "#F4F4F1", rough=0.2, coat=0.8), k.mat("band_orange", "#F07800", rough=0.25, coat=0.7),
     k.mat("roof", "#4A4F55", rough=0.5, metal=0.3), k.mat("underbody", "#1C1D20", rough=0.8),
     k.mat("band_dark", "#23262B", rough=0.3, coat=0.6)]
body(k, "shell", L, W, ZS, ZE, ZR, [(1.45, 1.95, 1), (3.05, 3.70, 4)], {"under": 3, "roof": 2}, M, nose=nose, y_steps=ys)


def roof_point(x, y):
    """The nose surface above x at y (top centre line drop applied)."""
    sx, drop = nose(y)
    hw = W / 2 * sx
    zr = ZR - drop
    t = min(1.0, abs(x) / hw)
    return Vector((x, y, ZE + (zr - ZE) * math.sqrt(max(0.0, 1 - t ** 2.2)) - drop * 0.0))


glass = k.mat("glass", "#0B1118", rough=0.04)
bm = bmesh.new()
for end in (-1, 1):
    y_out, y_in = end * (L / 2 - 0.10), end * (L / 2 - 0.62)
    for x0, x1 in ((-1.18, -0.08), (0.08, 1.18)):
        quad = [roof_point(x0, y_out), roof_point(x1, y_out), roof_point(x1, y_in), roof_point(x0, y_in)]
        quad = [p + Vector((0, end * 0.02, 0.02)) for p in quad]
        face_toward(bm, [bm.verts.new(p) for p in quad], (0, end, 0.6))
    for s in (1, -1):                       # cab side windows
        face_toward(bm, [bm.verts.new((s * (W / 2 * 0.985 + 0.012), end * (L / 2 - 1.15) + u, z))
                         for u, z in ((-0.35, 3.10), (0.35, 3.10), (0.35, 3.62), (-0.35, 3.62))], (s, 0, 0))
k.add("glass", bm, [glass], smooth=False, group="glass")

dark = k.mat("grille", "#2A2D31", rough=0.5)
metal = k.mat("metal", "#3B3F44", rough=0.5, metal=0.6)
wheel = k.mat("wheel", "#6F757B", rough=0.35, metal=0.9)
bm = bmesh.new()
for s in (1, -1):                            # side louvres
    for y0 in (-6.0, -2.0, 2.0, 6.0):
        box(bm, (s * (W / 2 + 0.01), y0, 2.65), (0.02, 3.2, 0.9), 0, bevel=0.01)
        for z in (2.3, 2.45, 2.6, 2.75, 2.9):
            box(bm, (s * (W / 2 + 0.022), y0, z), (0.012, 3.1, 0.03), 1)
for end in (-1, 1):                          # buffer beam, coupler, snowplough-style pilot
    box(bm, (0, end * (L / 2 + 0.12), 1.15), (W * 0.96, 0.24, 0.42), 1, bevel=0.04)
    box(bm, (0, end * (L / 2 + 0.38), 1.05), (0.35, 0.4, 0.25), 1, bevel=0.03)
    box(bm, (0, end * (L / 2 + 0.06), 0.55), (W * 0.8, 0.12, 0.5), 1, bevel=0.03)
for y in (-3.0, 0.0, 3.0):                   # fuel tank and equipment
    box(bm, (0, y, 0.78), (2.4, 2.8, 0.55), 1, bevel=0.06)
box(bm, (0, 0, ZR + 0.12), (1.2, 6.0, 0.22), 1, bevel=0.06)   # roof fan housings
for y in (-6.6, 6.6):
    bogie(bm, y, 0.7175, 0.525, 3, 1.8, 1, 2)
k.add("trim", bm, [dark, metal, wheel])

lights = [k.mat("headlight", "#EEF2FA", rough=0.06, emit="#FFF3DA"), k.mat("taillight", "#9E0E17", rough=0.12, emit="#FF1A1A")]
bm = bmesh.new()
for end in (-1, 1):
    for x in (-1.05, 1.05):
        box(bm, (x, end * (L / 2 + 0.005), 1.75), (0.32, 0.04, 0.16), 0, bevel=0.03)
        box(bm, (x * 0.8, end * (L / 2 + 0.005), 1.55), (0.12, 0.04, 0.08), 1, bevel=0.015)
    p = roof_point(0, end * (L / 2 - 0.66)) + Vector((0, end * 0.05, 0.08))
    box(bm, p, (0.34, 0.06, 0.12), 0, bevel=0.03)
k.add("lights", bm, lights, smooth=False, group="lights")
for s in (1, -1):
    k.text("DF11 0007", 0.2, (s * (W / 2 + 0.006), 0.0, 1.70), (math.radians(90), 0, math.radians(90 if s > 0 else -90)),
           k.mat("ink_white", "#F7F7F5", rough=0.4), thicken=0.008)

k.finish(bake={"body": 1024}, dust=(0.0, 1.5, 0.4), ao_distance=0.8)
