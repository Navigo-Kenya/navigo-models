"""Bus: a 33-seater "nganya" on an Isuzu NQR-class chassis (8.0 x 2.3 m, 4.18 m wheelbase).

Graffiti livery: a sunset gradient, speed slashes, a sun behind the name and
sparkles above the windows, all procedural and baked into the body texture.
Chrome rims, neon underglow and a roof LED strip ("neon" materials glow at
night), a lit destination sign. Passenger door on the nearside behind the
front wheel, dual rear wheels.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import Kit, arch, box, face_toward, fillet, lathe, lin, rounded_rect, tube  # noqa: E402

k = Kit("bus", "Nganya (33-seater)")

L, W = 8.0, 2.30
Y0 = -L / 2
ZB = 0.55
WHEEL_R = 0.395
AXLE_F, AXLE_R = 1.25, 5.43
ARCH_R = 0.48
BELT, WIN_TOP = 1.45, 2.45
CREASE, ROOF = 1.40, 2.95
TUMBLEHOME, CROWN = 0.03, 0.05


def y_of(s):
    return Y0 + s


def half_width(z):
    if z <= CREASE:
        return W / 2
    return W / 2 * (1 - TUMBLEHOME * min(1.0, (z - CREASE) / (ROOF - CREASE)))


def side_x(side, z, out=0.0):
    return side * (half_width(z) + out)


# ── The graffiti livery (procedural, object space) ───────────────────────
art = k.mat("art", "#FFFFFF", rough=0.26, coat=0.7)
nt = art.node_tree
N, Ln = nt.nodes, nt.links
tc = N.new("ShaderNodeTexCoord")
sep = N.new("ShaderNodeSeparateXYZ")
Ln.new(tc.outputs["Object"], sep.inputs["Vector"])


def math_node(op, a=None, b=None, va=None, vb=None):
    n = N.new("ShaderNodeMath")
    n.operation = op
    if a is not None:
        Ln.new(a, n.inputs[0])
    elif va is not None:
        n.inputs[0].default_value = va
    if b is not None:
        Ln.new(b, n.inputs[1])
    elif vb is not None:
        n.inputs[1].default_value = vb
    return n.outputs[0]


def ramp(fac, stops, constant=False):
    r = N.new("ShaderNodeValToRGB")
    r.color_ramp.interpolation = "CONSTANT" if constant else "LINEAR"
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = lin(col)
    Ln.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]


def mix(a, b, fac):
    m = N.new("ShaderNodeMix")
    m.data_type = "RGBA"
    Ln.new(fac, m.inputs["Factor"])
    Ln.new(a, m.inputs["A"])
    Ln.new(b, m.inputs["B"])
    return m.outputs["Result"]


Y, Z = sep.outputs["Y"], sep.outputs["Z"]
# Sunset, bottom to top of the lower panel; deep blue above the windows.
zf = math_node("MULTIPLY", math_node("SUBTRACT", Z, None, vb=0.55), None, vb=1 / 0.95)
sunset = ramp(zf, [(0.0, "#1A0636"), (0.45, "#9C0F6E"), (0.8, "#FF4F1F"), (1.0, "#FFB21A")])
upper = ramp(math_node("MULTIPLY", math_node("ADD", Y, None, vb=4.0), None, vb=1 / 8.0),
             [(0.0, "#3B0A72"), (1.0, "#0A2A8C")])
base = mix(sunset, upper, math_node("GREATER_THAN", Z, None, vb=1.47))
# A sun behind the name, on both sides.
cy = N.new("ShaderNodeCombineXYZ")
Ln.new(Y, cy.inputs["Y"])
Ln.new(Z, cy.inputs["Z"])
dist = N.new("ShaderNodeVectorMath")
dist.operation = "DISTANCE"
Ln.new(cy.outputs["Vector"], dist.inputs[0])
dist.inputs[1].default_value = (0, 0.4, 1.35)
sun_core = math_node("LESS_THAN", dist.outputs["Value"], None, vb=0.62)
sun_col = ramp(math_node("DIVIDE", dist.outputs["Value"], None, vb=0.62), [(0.0, "#FFE45C"), (1.0, "#FF7A1A")])
base = mix(base, sun_col, math_node("MULTIPLY", sun_core, math_node("LESS_THAN", Z, None, vb=1.47)))
# Speed slashes on the lower panel.
w = math_node("ADD", Y, math_node("MULTIPLY", Z, None, vb=1.7))
frac = math_node("FRACT", math_node("MULTIPLY", w, None, vb=0.85))
slash = math_node("MULTIPLY", math_node("LESS_THAN", frac, None, vb=0.06), math_node("LESS_THAN", Z, None, vb=1.42))
slash = math_node("MULTIPLY", slash, math_node("GREATER_THAN", Z, None, vb=0.62))
base = mix(base, ramp(frac, [(0.0, "#00E5FF"), (1.0, "#00E5FF")]), slash)
# Sparkles above the windows.
vor = N.new("ShaderNodeTexVoronoi")
vor.inputs["Scale"].default_value = 11.0
Ln.new(tc.outputs["Object"], vor.inputs["Vector"])
dots = math_node("MULTIPLY", math_node("LESS_THAN", vor.outputs["Distance"], None, vb=0.07),
                 math_node("GREATER_THAN", Z, None, vb=2.47))
base = mix(base, ramp(dots, [(0.0, "#FFFFFF"), (1.0, "#FFFFFF")]), dots)
# Dark skirt along the bottom.
base = mix(base, ramp(Z, [(0.0, "#141414"), (1.0, "#141414")]), math_node("LESS_THAN", Z, None, vb=0.66))
Ln.new(base, nt.nodes["Principled BSDF"].inputs["Base Color"])

M = {
    "art": art,
    "under": k.mat("underbody", "#121212", rough=0.9),
    "glass": k.mat("glass", "#080C12", rough=0.04),
    "rubber": k.mat("rubber", "#121212", rough=0.85),
    "plastic": k.mat("plastic", "#1F2125", rough=0.5),
    "chrome": k.mat("chrome", "#E2E5E8", rough=0.1, metal=1.0),
    "head": k.mat("headlight", "#EEF2FA", rough=0.06, emit="#FFF3DA"),
    "tail": k.mat("taillight", "#9E0E17", rough=0.12, emit="#FF1A1A"),
    "ind": k.mat("indicator", "#D47F00", rough=0.12, emit="#FF9500"),
    "neon": k.mat("neon", "#FF2BD6", rough=0.3, emit="#FF2BD6", emit_strength=1.0),
    "neon_cyan": k.mat("neon_cyan", "#00E5FF", rough=0.3, emit="#00E5FF", emit_strength=1.0),
    "sign": k.mat("beacon", "#1B1B1B", rough=0.4, emit="#FFB000", emit_strength=1.0),
    "plate_w": k.mat("plate_white", "#F5F5F1", rough=0.4),
    "plate_y": k.mat("plate_yellow", "#F5C400", rough=0.4),
    "ink": k.mat("ink", "#111214", rough=0.6),
    "white_ink": k.mat("ink_white", "#FAFAFA", rough=0.35, coat=0.5),
    "rim": k.mat("rim_chrome", "#E6E9EC", rough=0.08, metal=1.0),
    "hub": k.mat("hubcap", "#C8CCD0", rough=0.2, metal=0.95),
}

# ── Body ─────────────────────────────────────────────────────────────────
outline = [
    ((0.03, 0.56), 0.04), ((0.00, 1.20), 0.06), ((0.08, 2.60), 0.10), ((0.22, 2.95), 0.26),
    ((7.85, 2.95), 0.14), ((8.00, 2.80), 0.07), ((8.00, 0.60), 0.05), ((7.94, ZB), 0.02),
]
pts, radii = zip(*outline)
profile = fillet(list(pts), list(radii), seg=6)
profile += arch(AXLE_R, WHEEL_R, ARCH_R, ZB)
profile += arch(AXLE_F, WHEEL_R, ARCH_R, ZB)
profile.append((0.12, ZB))

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
for z in (0.66, CREASE, 1.47, 2.47):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1))
for x in (-0.8, -0.4, 0.0, 0.4, 0.8):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x, 0, 0), plane_no=(1, 0, 0))
for s in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, y_of(s), 0), plane_no=(0, 1, 0))
for v in bm.verts:
    z = v.co.z
    if z > CREASE + 1e-4:
        v.co.x *= half_width(z) / (W / 2)
    if z > ROOF - 0.1:
        hw = half_width(ROOF)
        v.co.z += CROWN * max(0.0, 1 - (v.co.x / hw) ** 2) * min(1.0, (z - (ROOF - 0.1)) / 0.1)
bm.normal_update()
for f in bm.faces:
    c = f.calc_center_median()
    nrm = f.normal
    near_arch = min(abs(c.y - y_of(AXLE_F)), abs(c.y - y_of(AXLE_R))) <= ARCH_R + 0.02
    if abs(nrm.x) <= 0.9 and (nrm.z < -0.6 or (near_arch and c.z < WHEEL_R + ARCH_R + 0.01)):
        f.material_index = 1
    else:
        f.material_index = 0
shell = k.add("shell", bm, [M["art"], M["under"]])
k.bevel(shell, 0.06, segments=4)

# ── Glass ────────────────────────────────────────────────────────────────


def front_s(z):
    """The front face's s at height z (windshield rake)."""
    return 0.0 + (z - 1.20) * (0.08 / 1.40) if z >= 1.20 else 0.0


near = [rounded_rect(1.86, 0.95, 2.22, 2.40, 0.04), rounded_rect(2.27, 0.95, 2.63, 2.40, 0.04)]   # folding door
win_n = [rounded_rect(2.78 + i * 0.83, BELT, 2.78 + i * 0.83 + 0.76, WIN_TOP, 0.06) for i in range(6)]
driver = fillet([(0.30, BELT), (1.12, BELT), (1.12, WIN_TOP), (0.36, WIN_TOP)], [0.04, 0.05, 0.05, 0.06], 5)
win_o = [rounded_rect(1.22 + i * 0.82, BELT, 1.22 + i * 0.82 + 0.75, WIN_TOP, 0.06) for i in range(8)]

bm = bmesh.new()
for poly in near + win_n:
    face_toward(bm, [bm.verts.new((side_x(1, z, 0.006), y_of(s), z)) for s, z in poly], (1, 0, 0.03))
for poly in [driver] + win_o:
    face_toward(bm, [bm.verts.new((side_x(-1, z, 0.006), y_of(s), z)) for s, z in poly], (-1, 0, 0.03))
ws = rounded_rect(-1.02, 1.30, 1.02, 2.52, 0.08)
face_toward(bm, [bm.verts.new((x, y_of(front_s(z)) - 0.012, z)) for x, z in ws], (0, -1, 0.06))
rw = rounded_rect(-0.95, 1.70, 0.95, 2.58, 0.07)
face_toward(bm, [bm.verts.new((x, y_of(8.0) + 0.006, z)) for x, z in rw], (0, 1, 0))
k.add("glass", bm, [M["glass"]], smooth=False, group="glass")

# ── Trim on the body ─────────────────────────────────────────────────────
bm = bmesh.new()
for side, polys in ((1, near + win_n), (-1, [driver] + win_o)):
    for poly in polys:
        cs = sum(p[0] for p in poly) / len(poly)
        cz = sum(p[1] for p in poly) / len(poly)
        big = [(s + (0.025 if s > cs else -0.025), z + (0.025 if z > cz else -0.025)) for s, z in poly]
        face_toward(bm, [bm.verts.new((side_x(side, z, 0.003), y_of(s), z)) for s, z in big], (side, 0, 0.03), 2)
face_toward(bm, [bm.verts.new((x * 1.04, y_of(front_s(z)) - 0.006, z)) for x, z in rounded_rect(-1.06, 1.26, 1.06, 2.56, 0.1)],
            (0, -1, 0.06), 2)
# Destination sign box above the windshield, mirrors on arms, wipers.
box(bm, (0, y_of(0.07) - 0.03, 2.73), (1.80, 0.06, 0.22), 1, bevel=0.02)
for side in (1, -1):
    tube(bm, (side * 1.08, y_of(0.25), 2.35), (side * 1.32, y_of(-0.18), 2.30), 0.016, 8, 1)
    box(bm, (side * 1.34, y_of(-0.20), 2.05), (0.08, 0.10, 0.44), 1, bevel=0.03)
    tube(bm, (side * 0.85, y_of(0.03) - 0.02, 1.33), (side * 0.15, y_of(0.03) - 0.03, 1.80), 0.011, 6, 1)
# Front bumper with an LED bar, grille, headlights housing; rear bumper; ladder.
box(bm, (0, y_of(0.06), 0.66), (2.36, 0.24, 0.30), 1, bevel=0.06)
box(bm, (0, y_of(0.02), 1.03), (1.30, 0.04, 0.26), 1, bevel=0.02)
for z in (0.95, 1.01, 1.07, 1.13):
    box(bm, (0, y_of(-0.002), z), (1.24, 0.02, 0.018), 0)
box(bm, (0, y_of(7.98), 0.66), (2.36, 0.22, 0.28), 1, bevel=0.06)
for x in (0.55, 0.85):
    tube(bm, (x, y_of(8.03), 0.85), (x, y_of(8.03), 2.85), 0.016, 8, 0)
for z in (1.1, 1.35, 1.6, 1.85, 2.1, 2.35, 2.6):
    tube(bm, (0.55, y_of(8.03), z), (0.85, y_of(8.03), z), 0.012, 6, 0)
# Roof rack.
for x in (-0.95, 0.95):
    tube(bm, (x, y_of(1.0), 3.12), (x, y_of(7.2), 3.12), 0.022, 8, 0)
for s in (1.0, 2.5, 4.0, 5.5, 7.2):
    tube(bm, (-0.95, y_of(s), 3.12), (0.95, y_of(s), 3.12), 0.018, 8, 0)
    for x in (-0.95, 0.95):
        tube(bm, (x, y_of(s), 2.98), (x, y_of(s), 3.12), 0.016, 6, 0)
# Plates.
box(bm, (0, y_of(-0.07), 0.66), (0.52, 0.012, 0.12), 3)
box(bm, (0, y_of(8.0) + 0.012, 0.95), (0.52, 0.012, 0.12), 4)
k.add("trim", bm, [M["chrome"], M["plastic"], M["rubber"], M["plate_w"], M["plate_y"]])

# Lettering: the name on both sides, the plates, the windshield banner.
for side in (1, -1):
    rot = (math.radians(90), 0, math.radians(90 if side > 0 else -90))
    k.text("BARAKA", 0.62, (side_x(side, 1.0, 0.012), y_of(4.6), 1.02), rot, M["ink"], thicken=0.05)
    k.text("BARAKA", 0.62, (side_x(side, 1.0, 0.020), y_of(4.6), 1.02), rot, M["white_ink"], thicken=0.012)
    k.text("NAVIGO", 0.14, (side_x(side, 2.7, 0.012), y_of(6.9), 2.70), rot, M["white_ink"], thicken=0.008)
k.text("KDN 777X", 0.075, (0, y_of(-0.077), 0.66), (math.radians(90), 0, 0), M["ink"], thicken=0.004)
k.text("KDN 777X", 0.075, (0, y_of(8.0) + 0.019, 0.95), (math.radians(90), 0, math.radians(180)), M["ink"], thicken=0.004)
k.text("NGANYA STYLE", 0.12, (0, y_of(front_s(2.45)) - 0.02, 2.45), (math.radians(90), 0, 0), M["white_ink"], thicken=0.008)

# ── Lights, sign, neon ───────────────────────────────────────────────────
bm = bmesh.new()
for side in (1, -1):
    box(bm, (side * 0.86, y_of(0.0), 1.03), (0.36, 0.05, 0.20), 0, bevel=0.025)
    box(bm, (side * 1.10, y_of(0.02), 1.03), (0.07, 0.05, 0.16), 2, bevel=0.015)
    box(bm, (side * 0.98, y_of(8.0) + 0.012, 1.25), (0.16, 0.04, 0.50), 1, bevel=0.015)
    box(bm, (side * 0.98, y_of(8.0) + 0.012, 0.92), (0.16, 0.04, 0.14), 2, bevel=0.012)
    # Underglow along the sills, LED dots under the roof line.
    box(bm, (side * (W / 2 - 0.05), y_of(4.6), 0.54), (0.04, 2.6, 0.03), 4)
    box(bm, (side * (W / 2 - 0.05), y_of(0.6), 0.54), (0.04, 0.45, 0.03), 4)
    for i in range(18):
        box(bm, (side_x(side, 2.55, 0.008), y_of(0.6 + i * 0.4), 2.55), (0.012, 0.05, 0.05), 3, bevel=0.01)
box(bm, (0, y_of(0.06) - 0.12, 0.66), (1.6, 0.02, 0.05), 4)                 # LED bar on the bumper
for x in (-0.95, 0.95):
    box(bm, (x, y_of(4.1), 3.16), (0.03, 6.2, 0.02), 3)                      # roof LED strips
box(bm, (0, y_of(0.07) - 0.062, 2.73), (1.66, 0.01, 0.16), 5)               # destination sign face
k.add("lights", bm, [M["head"], M["tail"], M["ind"], M["neon"], M["neon_cyan"], M["sign"]], smooth=False, group="lights")
k.text("RONGAI - TOWN", 0.11, (0, y_of(0.07) - 0.07, 2.73), (math.radians(90), 0, 0), M["ink"], thicken=0.006, group="lights")

# ── Wheels: chrome, dual at the rear ─────────────────────────────────────
tyre = fillet([(-0.10, 0.25), (0.10, 0.25), (0.108, 0.35), (0.088, WHEEL_R), (-0.088, WHEEL_R), (-0.108, 0.35)],
              [0, 0, 0.03, 0.04, 0.04, 0.03], 5)
rim = [(0.09, 0.252), (0.098, 0.24), (0.075, 0.215), (0.06, 0.15), (0.058, 0.10), (0.07, 0.085), (0.088, 0.075),
       (0.092, 0.04), (0.094, 0.0005)]
bm = bmesh.new()
tf = lathe(bm, tyre, (0, 0, 0), "x", 36, [0] * len(tyre))
bmesh.ops.recalc_face_normals(bm, faces=tf)
for f in lathe(bm, rim, (0, 0, 0), "x", 36, [1, 1, 1, 1, 1, 1, 2, 2], closed=False):
    f.normal_update()
    if f.normal.x < 0:
        f.normal_flip()
for a in range(8):
    ang = 2 * math.pi * a / 8
    c = (0.098, 0.115 * math.cos(ang), 0.115 * math.sin(ang))
    tube(bm, (c[0] - 0.012, c[1], c[2]), (c[0] + 0.012, c[1], c[2]), 0.013, 6, 2)
wheel = k.add("wheel_fl", bm, [M["rubber"], M["rim"], M["hub"]], group="wheel_fl", location=(0.97, y_of(AXLE_F), WHEEL_R))
k.instance("wheel_fr", wheel, (-0.97, y_of(AXLE_F), WHEEL_R), (0, 0, math.pi))
for name, x, rot in (("wheel_rl", 0.99, 0), ("wheel_rl2", 0.765, 0), ("wheel_rr", -0.99, math.pi), ("wheel_rr2", -0.765, math.pi)):
    k.instance(name, wheel, (x, y_of(AXLE_R), WHEEL_R), (0, 0, rot))

k.finish(bake={"body": 2048, "wheel_fl": 512}, dust=(0.0, 1.1, 0.4))
