"""Plane: a generic narrow-body jet (A320 class, 37.6 m long, 34 m span), no airline branding.
Window rows are procedural art baked into the fuselage texture. Origin under the engines."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, lathe, lin, loft  # noqa: E402

k = Kit("plane", "Plane")
R = 1.98                      # fuselage radius
ZC = 3.0                      # fuselage centre height above the origin

# ── Fuselage: white with grey belly and window rows (procedural, baked) ──
fus = k.mat("fuselage", "#FFFFFF", rough=0.25, coat=0.6)
nt = fus.node_tree
N, Ln = nt.nodes, nt.links
tc = N.new("ShaderNodeTexCoord")
sep = N.new("ShaderNodeSeparateXYZ")
Ln.new(tc.outputs["Object"], sep.inputs["Vector"])


def mnode(op, a, b=None, vb=None):
    n = N.new("ShaderNodeMath")
    n.operation = op
    Ln.new(a, n.inputs[0])
    if b is not None:
        Ln.new(b, n.inputs[1])
    elif vb is not None:
        n.inputs[1].default_value = vb
    return n.outputs[0]


def colour(hex_rgb):
    rgb = N.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = lin(hex_rgb)
    return rgb.outputs[0]


def mixc(a, b, fac):
    m = N.new("ShaderNodeMix")
    m.data_type = "RGBA"
    Ln.new(fac, m.inputs["Factor"])
    Ln.new(a, m.inputs["A"])
    Ln.new(b, m.inputs["B"])
    return m.outputs["Result"]


X, Y, Z = sep.outputs["X"], sep.outputs["Y"], sep.outputs["Z"]
col = mixc(colour("#F7F8F9"), colour("#B9BEC4"), mnode("LESS_THAN", Z, vb=ZC - 1.05))           # grey belly
cheat = mnode("MULTIPLY", mnode("GREATER_THAN", Z, vb=ZC - 0.62), mnode("LESS_THAN", Z, vb=ZC - 0.48))
col = mixc(col, colour("#123A73"), cheat)                                                      # cheatline
win_band = mnode("MULTIPLY", mnode("GREATER_THAN", Z, vb=ZC + 0.18), mnode("LESS_THAN", Z, vb=ZC + 0.52))
pitch = mnode("LESS_THAN", mnode("FRACT", mnode("MULTIPLY", Y, vb=1 / 0.53)), vb=0.42)
in_cabin = mnode("MULTIPLY", mnode("GREATER_THAN", Y, vb=-13.0), mnode("LESS_THAN", Y, vb=12.0))
wins = mnode("MULTIPLY", mnode("MULTIPLY", win_band, pitch), in_cabin)
col = mixc(col, colour("#1A2128"), wins)
cockpit = mnode("MULTIPLY", mnode("LESS_THAN", Y, vb=-16.1), mnode("MULTIPLY", mnode("GREATER_THAN", Z, vb=ZC + 0.25),
                                                                       mnode("LESS_THAN", Z, vb=ZC + 0.75)))
col = mixc(col, colour("#141A21"), cockpit)
Ln.new(col, nt.nodes["Principled BSDF"].inputs["Base Color"])

bm = bmesh.new()
stations = [(-18.8, 0.05, -0.35), (-18.5, 0.45, -0.25), (-17.8, 0.95, -0.12), (-16.8, 1.45, -0.05), (-15.4, 1.82, 0.0),
            (-13.5, R, 0.0), (10.0, R, 0.0), (12.5, 1.85, 0.15), (15.0, 1.45, 0.45), (17.0, 0.95, 0.85), (18.6, 0.35, 1.2),
            (18.8, 0.08, 1.3)]
sections = []
for y, r, dz in stations:
    sections.append([Vector((r * math.cos(2 * math.pi * i / 32), y, ZC + dz + r * math.sin(2 * math.pi * i / 32) * (1.0 if r > 0.1 else 1)))
                     for i in range(32)])
loft(bm, sections, 0)
k.add("fuselage", bm, [fus], group="fuselage")

# ── Wings, tail, engines (painted grey/white, tail blue with an orange band) ──
paint = k.mat("paint", "#E9ECEF", rough=0.3, coat=0.4)
tailc = k.mat("tail", "#123A73", rough=0.25, coat=0.6)
orange = k.mat("tail_band", "#F07800", rough=0.25, coat=0.6)
nacelle = k.mat("nacelle", "#D5D9DD", rough=0.3, metal=0.4)
inlet = k.mat("inlet", "#2A2E33", rough=0.5, metal=0.6)


def airfoil_ring(lead, chord, z, thick, twist_y=0.0):
    """A thin airfoil section (in the XY plane at height z); lead = leading-edge point (x, y)."""
    x, y = lead
    pts = []
    for t, h in ((0.0, 0.0), (0.06, 0.55), (0.25, 1.0), (0.6, 0.7), (1.0, 0.0)):
        pts.append((x, y + t * chord, z + h * thick))
    for t, h in ((0.6, -0.35), (0.25, -0.5), (0.06, -0.3)):
        pts.append((x, y + t * chord, z + h * thick))
    return [Vector(p) for p in pts]


bm = bmesh.new()
for s in (1, -1):                                # wings: root at the fuselage, swept, dihedral
    root = airfoil_ring((s * 1.6, -4.6), 6.2, ZC - 1.2, 0.42)
    mid = airfoil_ring((s * 8.0, -1.6), 3.4, ZC - 0.65, 0.26)
    tip = airfoil_ring((s * 17.0, 2.3), 1.6, ZC - 0.1, 0.14)
    winglet = airfoil_ring((s * 17.25, 2.9), 1.0, ZC + 1.4, 0.08)
    loft(bm, [root, mid, tip, winglet] if s > 0 else [winglet, tip, mid, root], 0)
    hroot = airfoil_ring((s * 0.8, 14.6), 3.0, ZC + 0.6, 0.18)
    htip = airfoil_ring((s * 6.2, 17.6), 1.3, ZC + 0.9, 0.08)
    loft(bm, [hroot, htip] if s > 0 else [htip, hroot], 0)
fin = []
for lead, chord, z in (((0, 12.6), 5.6, ZC + 1.2), ((0, 14.9), 3.6, ZC + 4.0), ((0, 16.6), 2.0, ZC + 6.6)):
    ring = []
    for t, h in ((0.0, 0.0), (0.06, 0.5), (0.3, 1.0), (0.7, 0.6), (1.0, 0.0), (0.7, -0.6), (0.3, -1.0), (0.06, -0.5)):
        ring.append(Vector((h * 0.22, lead[1] + t * chord, z)))
    fin.append(ring)
first = len(bm.faces)
loft(bm, fin, 1)
for f in bm.faces[first:] if hasattr(bm.faces, "__getitem__") else []:
    pass
bm.faces.ensure_lookup_table()
for f in bm.faces[first:]:
    c = f.calc_center_median()
    if ZC + 2.6 < c.z < ZC + 3.4:
        f.material_index = 2
for s in (1, -1):                                # engines
    prof = [(-2.0, 0.0), (-2.0, 0.78), (-1.85, 0.98), (-1.2, 1.05), (0.6, 0.98), (1.6, 0.72), (2.1, 0.45), (2.4, 0.0)]
    lathe(bm, prof, (s * 5.75, -6.0, ZC - 2.05), "y", 28, [4, 3, 3, 3, 3, 3, 3], closed=False)
k.add("wings", bm, [paint, tailc, orange, nacelle, inlet], group="wings")

bm = bmesh.new()
for s in (1, -1):
    from kit import box
    box(bm, (s * 17.1, 2.6, ZC - 0.05), (0.15, 0.3, 0.12), 0 if s > 0 else 1)   # nav lights
box(bm, (0, 18.75, ZC + 1.32), (0.12, 0.12, 0.12), 2)
k.add("lights", bm, [k.mat("indicator", "#1B9E3E", emit="#2BFF5A"), k.mat("taillight", "#9E0E17", emit="#FF1A1A"),
                     k.mat("headlight", "#EEF2FA", emit="#FFFFFF")], smooth=False, group="lights")

k.finish(bake={"fuselage": 2048, "wings": 1024}, dust=(0.0, 0.0, 0.0), ao_distance=1.5,
         shots=[("hero", (30, -38, 16), (0, -2, 3), 50), ("rear", (-30, 40, 18), (0, 2, 3), 50), ("nav", (0, 60, 36), (0, -14, 2), 35)])
