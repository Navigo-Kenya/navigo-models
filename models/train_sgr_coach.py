"""SGR passenger coach (25G class, standard gauge): 25.5 x 3.1 m, glossy white with orange bands."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402

from kit import Kit, box, face_toward, rounded_rect  # noqa: E402
from rail import body, bogie, windows  # noqa: E402

k = Kit("train_sgr_coach", "SGR coach")
L, W = 25.5, 3.10
M = [k.mat("paint", "#F4F4F1", rough=0.2, coat=0.8), k.mat("band_orange", "#F07800", rough=0.25, coat=0.7),
     k.mat("roof", "#5B6066", rough=0.5, metal=0.3), k.mat("underbody", "#1C1D20", rough=0.8)]
body(k, "shell", L, W, 0.98, 3.55, 4.35, [(1.55, 1.82, 1), (2.97, 3.05, 1)], {"under": 3, "roof": 2}, M)

glass = k.mat("glass", "#0B1118", rough=0.04)
dark = k.mat("door", "#2A2D31", rough=0.5)
rubber = k.mat("rubber", "#151515", rough=0.85)
metal = k.mat("metal", "#3B3F44", rough=0.5, metal=0.6)
wheel = k.mat("wheel", "#6F757B", rough=0.35, metal=0.9)

bm = bmesh.new()
windows(bm, W / 2, [-9.65 + i * 1.755 for i in range(12)], 1.98, 2.86, 1.22, 0)
for y in (-11.35, 11.35):
    windows(bm, W / 2, [y], 2.15, 2.75, 0.42, 0, out=0.016)
k.add("glass", bm, [glass], smooth=False, group="glass")

bm = bmesh.new()
for y in (-11.35, 11.35):                       # doors
    for s in (1, -1):
        face_toward(bm, [bm.verts.new((s * (W / 2 + 0.010), y + u, z)) for u, z in rounded_rect(-0.42, 1.15, 0.42, 3.15, 0.06)],
                    (s, 0, 0), 0)
for y in (-L / 2 - 0.22, L / 2 + 0.22):          # gangway bellows, couplers
    box(bm, (0, y, 2.35), (1.25, 0.44, 2.3), 1, bevel=0.05)
    box(bm, (0, y + (0.25 if y > 0 else -0.25), 0.95), (0.35, 0.5, 0.25), 2, bevel=0.03)
for y in (-6.5, 6.5):                           # roof AC units
    box(bm, (0, y, 4.42), (2.0, 3.2, 0.32), 2, bevel=0.08)
for y in (-4.2, -1.4, 1.4, 4.2):                # underframe equipment
    box(bm, (0, y, 0.72), (2.2, 2.2, 0.5), 2, bevel=0.03)
for y in (-8.75, 8.75):
    bogie(bm, y, 0.7175, 0.4575, 2, 2.5, 2, 3)
k.add("trim", bm, [dark, rubber, metal, wheel])
for s in (1, -1):
    k.text("SGR 25G 078", 0.16, (s * (W / 2 + 0.006), 0.0, 1.33), (math.radians(90), 0, math.radians(90 if s > 0 else -90)),
           k.mat("ink", "#2A2D31", rough=0.6), thicken=0.006)

k.finish(bake={"body": 1024}, dust=(0.0, 1.4, 0.35), ao_distance=0.8)
