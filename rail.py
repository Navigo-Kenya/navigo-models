"""Rail cars for the train models: a lofted car body with livery bands, window
rows, doors, gangways, roof units, underframe boxes and bogies.

Origin: top of the rail, centre of the car. The car runs along Y (front -Y).
"""
import math

import bmesh
from mathutils import Vector

from kit import box, face_toward, fillet, lathe, rounded_rect, tube


def section(width, z_skirt, z_eave, z_roof, bands):
    """Cross-section (x, z), counter-clockwise, with extra points at the band heights."""
    hw = width / 2
    pts = fillet([(-hw, z_skirt), (hw, z_skirt), (hw, z_eave), (hw * 0.62, z_roof), (-hw * 0.62, z_roof), (-hw, z_eave)],
                 [0.06, 0.06, 0.42, 0.9, 0.9, 0.42], 6)
    out = []
    for i, p in enumerate(pts):
        out.append(p)
        q = pts[(i + 1) % len(pts)]
        # On the vertical sides, add points at each band height so bands are crisp.
        if abs(p[0] - q[0]) < 1e-6 and abs(abs(p[0]) - hw) < 1e-6:
            lo, hi = sorted((p[1], q[1]))
            zs = [z for z in sorted(bands) if lo + 1e-4 < z < hi - 1e-4]
            if q[1] < p[1]:
                zs = list(reversed(zs))
            out += [(p[0], z) for z in zs]
    return out


def body(k, name, length, width, z_skirt, z_eave, z_roof, bands, band_mats, mats, nose=None, y_steps=None):
    """Loft the section along Y. bands: [(z_from, z_to, material index)] painted on the sides;
    nose(t): optional (width scale, roof drop) for the last metres at the front (t: 0..1)."""
    sec = section(width, z_skirt, z_eave, z_roof, [z for b in bands for z in b[:2]])
    ys = list(y_steps or [])
    if not ys:
        n = max(8, int(length / 1.5))
        ys = [-length / 2 + length * i / n for i in range(n + 1)]
    rings = []
    for y in ys:
        sx, drop = (1.0, 0.0)
        if nose:
            sx, drop = nose(y)
        ring = []
        for x, z in sec:
            zz = z
            if drop and z > z_eave - 0.6:
                zz = z - drop * min(1.0, (z - (z_eave - 0.6)) / (z_roof - z_eave + 0.6))
            ring.append(Vector((x * sx, y, zz)))
        rings.append(ring)
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    m = len(sec)
    for kk in range(len(vr) - 1):
        for i in range(m):
            j = (i + 1) % m
            f = bm.faces.new((vr[kk][i], vr[kk][j], vr[kk + 1][j], vr[kk + 1][i]))
            f.material_index = 0
    bm.faces.new(list(reversed(vr[0])))
    bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for f in bm.faces:
        c = f.calc_center_median()
        if f.normal.z < -0.7:
            f.material_index = band_mats["under"]
        elif c.z > z_eave + 0.25 and abs(f.normal.y) < 0.9:
            f.material_index = band_mats["roof"]
        else:
            for z0, z1, mi in bands:
                if z0 <= c.z <= z1 and abs(f.normal.x) > 0.7:
                    f.material_index = mi
    ob = k.add(name, bm, mats)
    k.smooth_by_angle(ob, 35)
    return ob


def windows(bm, half_w, ys, z0, z1, w, mat, out=0.008, r=0.08):
    for y in ys:
        for s in (1, -1):
            face_toward(bm, [bm.verts.new((s * (half_w + out), y + u, z)) for u, z in rounded_rect(-w / 2, z0, w / 2, z1, r)],
                        (s, 0, 0), mat)


def bogie(bm, y, half_gauge, wheel_r, axles, spacing, frame_mat, wheel_mat, axle_z=None):
    """A bogie: frame, springs, wheels (as discs) on `axles` axles."""
    az = axle_z or wheel_r
    span = spacing * (axles - 1)
    for s in (1, -1):
        box(bm, (s * (half_gauge + 0.16), y, az + 0.1), (0.16, span + 1.0, 0.32), frame_mat, bevel=0.04)
        for i in range(axles):
            ya = y - span / 2 + i * spacing
            prof = [(-0.07, 0.0), (-0.07, wheel_r - 0.03), (-0.03, wheel_r), (0.07, wheel_r), (0.07, 0.0)]
            lathe(bm, prof, (s * half_gauge, ya, az), "x", 24, [wheel_mat] * 5, closed=False, side=s)
            tube(bm, (s * (half_gauge + 0.09), ya, az), (s * (half_gauge + 0.20), ya, az), 0.09, 12, frame_mat)
            tube(bm, (s * (half_gauge + 0.16), ya, az + 0.25), (s * (half_gauge + 0.16), ya, az + 0.45), 0.08, 12, frame_mat)
    for i in range(axles):
        ya = y - span / 2 + i * spacing
        tube(bm, (-half_gauge, ya, az), (half_gauge, ya, az), 0.06, 10, frame_mat)
