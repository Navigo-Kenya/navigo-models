"""Ferry: a double-ended Likoni-class ro-ro ferry (72 x 18 m) with cars aboard.
Origin at the waterline (nothing below it: the map has no water surface)."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402

from kit import Kit, box, face_toward, fillet, tube  # noqa: E402

k = Kit("ferry", "Ferry (Likoni)")
L, W = 72.0, 18.0
DECK = 1.6

M = {
    "hull": k.mat("hull", "#173A6B", rough=0.4, coat=0.4),
    "white": k.mat("paint", "#F2F3F1", rough=0.3, coat=0.4),
    "deck": k.mat("deck", "#4A4E52", rough=0.85),
    "line": k.mat("deck_line", "#E8D27A", rough=0.7),
    "rail": k.mat("rail", "#DADDE0", rough=0.3, metal=0.8),
    "orange": k.mat("raft", "#F26B1D", rough=0.5),
    "ramp": k.mat("ramp", "#3A3D41", rough=0.6, metal=0.4),
    "red": k.mat("boot_top", "#9E1B1B", rough=0.5),
}

# Hull: a flat-bottomed box with raked ends (double-ended), red boot top at the waterline.
half_l, rake = L / 2, 4.0
outline = [(-half_l + rake, 0.0), (half_l - rake, 0.0), (half_l, DECK), (-half_l, DECK)]
prof = fillet(outline, [0.4, 0.4, 0.2, 0.2], 4)
bm = bmesh.new()
left = [bm.verts.new((W / 2, y, z)) for y, z in prof]
right = [bm.verts.new((-W / 2, y, z)) for y, z in prof]
bm.faces.new(left)
bm.faces.new(list(reversed(right)))
for i in range(len(prof)):
    j = (i + 1) % len(prof)
    bm.faces.new((left[i], left[j], right[j], right[i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0.35), plane_no=(0, 0, 1))
bm.normal_update()
for f in bm.faces:
    c = f.calc_center_median()
    f.material_index = 2 if f.normal.z > 0.9 else (1 if c.z < 0.35 else 0)
hull = k.add("hull", bm, [M["hull"], M["red"], M["deck"]])
k.bevel(hull, 0.15, segments=3)

bm = bmesh.new()
# Lane lines on the car deck.
for x in (-4.5, -1.5, 1.5, 4.5):
    box(bm, (x, 0, DECK + 0.01), (0.15, L - 14, 0.02), 1)
# Side superstructure (two decks of cabins) along both sides, white with windows.
for s in (1, -1):
    box(bm, (s * (W / 2 - 1.6), 0, DECK + 2.4), (3.2, 46, 4.8), 0, bevel=0.15)
    box(bm, (s * (W / 2 - 1.4), 0, DECK + 6.2), (2.8, 40, 2.8), 0, bevel=0.15)
    for deck_z, length in ((DECK + 3.0, 44), (DECK + 6.4, 38)):
        tube(bm, (s * (W / 2 + 0.02), -length / 2, deck_z + 1.15), (s * (W / 2 + 0.02), length / 2, deck_z + 1.15), 0.05, 6, 2)
    for i in range(10):                                        # life rafts
        tube(bm, (s * (W / 2 - 0.6), -18 + i * 4, DECK + 8.0), (s * (W / 2 - 0.6), -16.8 + i * 4, DECK + 8.0), 0.35, 12, 3)
# Bridge across the car deck, wheelhouse on top, mast.
box(bm, (0, 0, DECK + 8.6), (W - 2, 6.0, 1.2), 0, bevel=0.15)
box(bm, (0, 0, DECK + 10.2), (8.0, 5.0, 2.2), 0, bevel=0.2)
tube(bm, (0, 0, DECK + 11.3), (0, 0, DECK + 16.0), 0.12, 8, 2)
box(bm, (0, 0, DECK + 15.0), (2.4, 0.15, 0.15), 2)
# Ramps (raised) at both ends.
for e in (-1, 1):
    box(bm, (0, e * (half_l - 0.3), DECK + 1.6), (11.0, 0.5, 3.4), 4, bevel=0.08)
k.add("decks", bm, [M["white"], M["line"], M["rail"], M["orange"], M["ramp"]])

# Cars aboard: simple low boxes in everyday colours.
random.seed(7)
colours = ["#F2F2EE", "#C9CDD2", "#2B2E33", "#9E1B1B", "#1F4E8C", "#F2F2EE", "#7A7F86"]
bm = bmesh.new()
mats = []
for i, x in enumerate((-3.0, 0.0, 3.0)):
    for j in range(6):
        y = -14 + j * 5.6 + random.uniform(-0.6, 0.6)
        mi = (i * 6 + j) % len(colours)
        box(bm, (x, y, DECK + 0.55), (1.75, 4.3, 0.75), mi, bevel=0.12)
        box(bm, (x, y + 0.3, DECK + 1.2), (1.55, 2.4, 0.6), len(colours), bevel=0.12)
cars = k.add("cars", bm, [k.mat(f"car_{n}", c, rough=0.3, coat=0.5) for n, c in enumerate(colours)] + [k.mat("car_glass", "#141A21", rough=0.1)])

glass = k.mat("glass", "#10161D", rough=0.05)
bm = bmesh.new()
for s in (1, -1):
    for deck_z, length, count in ((DECK + 3.0, 44, 20), (DECK + 6.4, 38, 17)):
        for i in range(count):
            y = -length / 2 + 1.2 + i * (length - 2.4) / (count - 1)
            face_toward(bm, [bm.verts.new((s * (W / 2 + 0.02), y + u, deck_z + v)) for u, v in ((-0.6, 0), (0.6, 0), (0.6, 0.9), (-0.6, 0.9))],
                        (s, 0, 0))
for e in (-1, 1):
    face_toward(bm, [bm.verts.new((u, e * 2.52, DECK + 10.4 + v)) for u, v in ((-3.6, 0), (3.6, 0), (3.6, 0.9), (-3.6, 0.9))], (0, e, 0))
k.add("glass", bm, [glass], smooth=False, group="glass")

bm = bmesh.new()
for e in (-1, 1):
    box(bm, (0, e * 2.55, DECK + 11.45), (0.4, 0.1, 0.3), 0)
    box(bm, (0, e * (half_l - 0.05), DECK + 3.4), (0.3, 0.1, 0.3), 1)
k.add("lights", bm, [k.mat("headlight", "#EEF2FA", emit="#FFF3DA"), k.mat("taillight", "#9E0E17", emit="#FF1A1A")],
      smooth=False, group="lights")
for s in (1, -1):
    k.text("MV UMOJA", 1.1, (s * (W / 2 + 0.03), 0, 0.9), (math.radians(90), 0, math.radians(90 if s > 0 else -90)),
           k.mat("ink_white", "#F7F7F5", rough=0.4), thicken=0.03)

k.finish(bake={"body": 1024}, dust=(0.0, 0.0, 0.0), ao_distance=2.0,
         shots=[("hero", (55, -70, 38), (0, -4, 4), 50), ("rear", (-55, 72, 40), (0, 4, 4), 50), ("nav", (0, 110, 70), (0, -30, 2), 35)])
