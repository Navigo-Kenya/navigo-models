"""
Navigo vehicle kit: shared helpers for building the navigation models in
headless Blender (4.2). Each script in models/ builds one vehicle:

    blender -b --factory-startup -P models/matatu.py -- --out /app/assets/models --previews /work/out

Conventions (every model):
  - metres; Blender Z up; the vehicle faces -Y (the exported glTF faces +Z, Y up)
  - origin on the ground, centre of the footprint
  - material names the app and the viewer rely on:
      livery  recoloured per route (matatu), paint  recoloured per user (car)
      headlight / taillight / indicator / neon  emissive, brightened at night
  - every body gets a baked "multiplier" texture: ambient occlusion times a
    little Nairobi dust near the ground, multiplied into its base colour, so
    the models look grounded in any renderer (Mapbox has no AO of its own)
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

# ── Arguments ────────────────────────────────────────────────────────────


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"out": "/out", "previews": "/work/out", "render": True, "bake": True}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--out", "--previews"):
            out[a[2:]] = argv[i + 1]
            i += 2
            continue
        if a == "--no-render":
            out["render"] = False
        if a == "--no-bake":
            out["bake"] = False
        i += 1
    return out


# ── Colour ───────────────────────────────────────────────────────────────


def lin(hex_rgb, alpha=1.0):
    h = hex_rgb.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, alpha)


# ── 2D profiles ──────────────────────────────────────────────────────────


def fillet(points, radii, seg=6):
    """Round a closed 2D polygon's corners; radii[i] = 0 keeps corner i sharp."""
    n = len(points)
    out = []
    for i in range(n):
        p = Vector(points[i])
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        a = Vector(points[i - 1])
        b = Vector(points[(i + 1) % n])
        if r <= 0:
            out.append((p.x, p.y))
            continue
        u1 = (a - p).normalized()
        u2 = (b - p).normalized()
        theta = math.acos(max(-1.0, min(1.0, u1.dot(u2))))
        if theta < 1e-3 or abs(theta - math.pi) < 1e-3:
            out.append((p.x, p.y))
            continue
        t = min(r / math.tan(theta / 2), 0.45 * (a - p).length, 0.45 * (b - p).length)
        reff = t * math.tan(theta / 2)
        t1, t2 = p + u1 * t, p + u2 * t
        c = p + (u1 + u2).normalized() * (reff / math.sin(theta / 2))
        a1 = math.atan2(t1.y - c.y, t1.x - c.x)
        a2 = math.atan2(t2.y - c.y, t2.x - c.x)
        d = a2 - a1
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        for k in range(seg + 1):
            ang = a1 + d * k / seg
            out.append((c.x + reff * math.cos(ang), c.y + reff * math.sin(ang)))
    return out


def rounded_rect(x0, y0, x1, y1, r, seg=5):
    return fillet([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [r] * 4, seg)


def arch(s_c, zc, radius, z_floor, steps=14):
    """A wheel arch cut into a body's floor line, from its rear end to its front end."""
    dz = z_floor - zc
    dx = math.sqrt(max(radius ** 2 - dz ** 2, 1e-6))
    a0 = math.atan2(dz, dx)
    a1 = math.pi - a0
    return [(s_c + radius * math.cos(a0 + (a1 - a0) * k / steps),
             zc + radius * math.sin(a0 + (a1 - a0) * k / steps)) for k in range(steps + 1)]


# ── Geometry into a bmesh ────────────────────────────────────────────────


def face_toward(bm, verts, direction, mat=0):
    f = bm.faces.new(verts)
    f.normal_update()
    if f.normal.dot(Vector(direction)) < 0:
        f.normal_flip()
    f.material_index = mat
    return f


def box(bm, center, size, mat=0, bevel=0.0, segments=3):
    cx, cy, cz = center
    sx, sy, sz = (v / 2 for v in size)
    geom = bmesh.ops.create_cube(bm, size=1.0)
    vs = geom["verts"]
    for v in vs:
        v.co = Vector((cx + v.co.x * 2 * sx, cy + v.co.y * 2 * sy, cz + v.co.z * 2 * sz))
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mat
    if bevel > 0:
        edges = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segments, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    return vs


def rings_to_faces(bm, rings, mat=0, closed_rings=True, cap_start=False, cap_end=False):
    """Join rings of verts (each ring the same length) into a surface."""
    m = len(rings[0])
    count = m if closed_rings else m - 1
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        for i in range(count):
            j = (i + 1) % m
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mat
    if cap_start:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = mat
    if cap_end:
        f = bm.faces.new(rings[-1])
        f.material_index = mat


def lathe(bm, profile, axis_origin, axis="x", segments=32, mats=None, closed=True, side=1):
    """Revolve (axial, radius) points around an axis through axis_origin."""
    ox, oy, oz = axis_origin
    rings = []
    for k in range(segments):
        a = 2 * math.pi * k / segments
        ring = []
        for ax, r in profile:
            ax *= side
            if axis == "x":
                co = (ox + ax, oy + r * math.cos(a), oz + r * math.sin(a))
            elif axis == "y":
                co = (ox + r * math.cos(a), oy + ax, oz + r * math.sin(a))
            else:
                co = (ox + r * math.cos(a), oy + r * math.sin(a), oz + ax)
            ring.append(bm.verts.new(co))
        rings.append(ring)
    m = len(profile)
    count = m if closed else m - 1
    faces = []
    for k in range(segments):
        r0, r1 = rings[k], rings[(k + 1) % segments]
        for i in range(count):
            j = (i + 1) % m
            f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
            f.material_index = mats[i] if mats else 0
            faces.append(f)
    return faces


def _frame(direction):
    """Two unit vectors perpendicular to direction."""
    d = Vector(direction).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(up).normalized()
    v = d.cross(u).normalized()
    return d, u, v


def tube(bm, p0, p1, r, segs=10, mat=0, caps=True, r1=None):
    """A cylinder (or cone, with r1) between two points."""
    p0, p1 = Vector(p0), Vector(p1)
    d, u, v = _frame(p1 - p0)
    r1 = r if r1 is None else r1
    rings = []
    for p, rr in ((p0, r), (p1, r1)):
        rings.append([bm.verts.new(p + (u * math.cos(2 * math.pi * k / segs) + v * math.sin(2 * math.pi * k / segs)) * rr)
                      for k in range(segs)])
    rings_to_faces(bm, rings, mat, cap_start=caps, cap_end=caps)


def ellipsoid(bm, center, radii, mat=0, segs=16, rings=10, rotation=None):
    c = Vector(center)
    rx, ry, rz = radii
    rot = rotation or Matrix.Identity(3)
    verts_rings = []
    top = bm.verts.new(c + rot @ Vector((0, 0, rz)))
    bottom = bm.verts.new(c + rot @ Vector((0, 0, -rz)))
    for i in range(1, rings):
        phi = math.pi * i / rings
        ring = []
        for k in range(segs):
            th = 2 * math.pi * k / segs
            p = Vector((rx * math.sin(phi) * math.cos(th), ry * math.sin(phi) * math.sin(th), rz * math.cos(phi)))
            ring.append(bm.verts.new(c + rot @ p))
        verts_rings.append(ring)
    for k in range(segs):
        j = (k + 1) % segs
        f = bm.faces.new((top, verts_rings[0][k], verts_rings[0][j]))
        f.material_index = mat
        f = bm.faces.new((bottom, verts_rings[-1][j], verts_rings[-1][k]))
        f.material_index = mat
    rings_to_faces(bm, verts_rings, mat)


def capsule(bm, p0, p1, r0, r1, mat=0, segs=12, cap_rings=4):
    """A tapered capsule (a limb) from p0 (radius r0) to p1 (radius r1)."""
    p0, p1 = Vector(p0), Vector(p1)
    d, u, v = _frame(p1 - p0)
    rings = []
    for i in range(cap_rings, 0, -1):          # cap at p0
        a = math.pi / 2 * i / cap_rings
        rings.append((p0 - d * r0 * math.sin(a), r0 * math.cos(a)))
    rings.append((p0, r0))
    rings.append((p1, r1))
    for i in range(1, cap_rings + 1):          # cap at p1
        a = math.pi / 2 * i / cap_rings
        rings.append((p1 + d * r1 * math.sin(a), r1 * math.cos(a)))
    vr = []
    for c, rr in rings:
        rr = max(rr, 1e-4)
        vr.append([bm.verts.new(c + (u * math.cos(2 * math.pi * k / segs) + v * math.sin(2 * math.pi * k / segs)) * rr)
                   for k in range(segs)])
    rings_to_faces(bm, vr, mat, cap_start=True, cap_end=True)


def loft(bm, sections, mat=0, cap_start=True, cap_end=True, mats_by_ring=None):
    """sections: list of rings, each a list of 3D points (same count)."""
    rings = [[bm.verts.new(p) for p in ring] for ring in sections]
    m = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(m):
            j = (i + 1) % m
            f = bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
            f.material_index = mats_by_ring[k] if mats_by_ring else mat
    if cap_start:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = mat
    if cap_end:
        f = bm.faces.new(rings[-1])
        f.material_index = mat
    return rings


def superellipse(cx, cz, rx, rz, n=2.6, count=24, x_shift=0.0):
    """Points of a superellipse in the XZ plane (a rounded-box cross-section)."""
    pts = []
    for k in range(count):
        t = 2 * math.pi * k / count
        c, s = math.cos(t), math.sin(t)
        x = rx * math.copysign(abs(c) ** (2 / n), c)
        z = rz * math.copysign(abs(s) ** (2 / n), s)
        pts.append((cx + x + x_shift, cz + z))
    return pts


def two_bone(a, c, l1, l2, pole):
    """Middle joint of a two-bone chain from a to c, bending toward pole."""
    a, c = Vector(a), Vector(c)
    d = (c - a)
    dist = min(d.length, l1 + l2 - 1e-4)
    dirn = d.normalized()
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    sin_a = math.sqrt(max(0.0, 1 - cos_a * cos_a))
    p = Vector(pole)
    n = (p - dirn * p.dot(dirn)).normalized()
    return a + dirn * (l1 * cos_a) + n * (l1 * sin_a)


# ── The kit ──────────────────────────────────────────────────────────────


class Kit:
    def __init__(self, name, title=None):
        self.name = name
        self.title = title or name
        self.opts = args()
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.root = bpy.data.objects.new(name, None)
        self.scene.collection.objects.link(self.root)
        self.parts = []
        self.bake_specs = {}
        self.materials = {}
        self.meta = {"name": name, "title": self.title}

    # ── Materials ──
    def mat(self, name, color, rough=0.5, metal=0.0, coat=0.0, emit=None, emit_strength=1.0, alpha=None):
        if name in self.materials:
            return self.materials[name]
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        p = m.node_tree.nodes["Principled BSDF"]
        p.inputs["Base Color"].default_value = lin(color)
        p.inputs["Roughness"].default_value = rough
        p.inputs["Metallic"].default_value = metal
        if coat:
            p.inputs["Coat Weight"].default_value = coat
            p.inputs["Coat Roughness"].default_value = 0.06
        if emit:
            p.inputs["Emission Color"].default_value = lin(emit)
            p.inputs["Emission Strength"].default_value = emit_strength
        if alpha is not None:
            p.inputs["Alpha"].default_value = alpha
            m.blend_method = "BLEND"
        self.materials[name] = m
        return m

    # ── Objects ──
    def add(self, name, bm, mats, smooth=True, group="body", location=(0, 0, 0)):
        """Add a bmesh as an object. Objects of one group are merged into one
        mesh at the end (one texture); "glass" and "lights" aren't baked."""
        me = bpy.data.meshes.new(name)
        if smooth:
            for f in bm.faces:
                f.smooth = True
        bm.normal_update()
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        self.scene.collection.objects.link(ob)
        ob.parent = self.root
        ob.location = location
        ob["group"] = group
        self.parts.append(ob)
        return ob

    def instance(self, name, source, location, rotation=(0, 0, 0)):
        """A copy sharing source's mesh (wheels): exported once, baked once."""
        ob = bpy.data.objects.new(name, source.data)
        self.scene.collection.objects.link(ob)
        ob.parent = self.root
        ob.location = location
        ob.rotation_euler = rotation
        ob["group"] = f"instance:{source.name}"
        self.parts.append(ob)
        return ob

    def bevel(self, ob, width, segments=3, angle=30, harden=True):
        b = ob.modifiers.new("bevel", "BEVEL")
        b.width = width
        b.segments = segments
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(angle)
        b.harden_normals = harden
        return b

    def smooth_by_angle(self, ob, angle=40):
        """Flat-shade edges sharper than angle (custom split normals), smooth the rest."""
        me = ob.data
        me.shade_smooth()
        bm = bmesh.new()
        bm.from_mesh(me)
        for e in bm.edges:
            if e.is_manifold and e.calc_face_angle(0) > math.radians(angle):
                e.smooth = False
        bm.to_mesh(me)
        bm.free()

    def text(self, body, size, location, rotation, mat, align="CENTER", thicken=0.0, extrude=0.0, group="body"):
        """Text as a mesh decal (plates, names). Returns the object (not parented yet)."""
        cu = bpy.data.curves.new(type="FONT", name=f"txt_{body}")
        cu.body = body
        cu.size = size
        cu.align_x = align
        cu.align_y = "CENTER"
        cu.extrude = extrude
        cu.offset = thicken
        cu.resolution_u = 4
        tmp = bpy.data.objects.new("tmp_text", cu)
        self.scene.collection.objects.link(tmp)
        deps = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(tmp.evaluated_get(deps))
        bpy.data.objects.remove(tmp)
        me.materials.clear()
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"text_{body.lower().replace(' ', '_')}", me)
        self.scene.collection.objects.link(ob)
        ob.location = location
        ob.rotation_euler = rotation
        ob.parent = self.root
        ob["group"] = group
        self.parts.append(ob)
        return ob

    # ── Finish: apply, merge, bake, export, preview ──
    def _apply_all(self):
        deps = bpy.context.evaluated_depsgraph_get()
        done = set()
        for ob in self.parts:
            if ob.type != "MESH" or not ob.modifiers or ob.data.name in done:
                continue
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
            for other in self.parts:                     # instances follow their source
                if other is not ob and other.type == "MESH" and other.data == ob.data:
                    other.data = me
            ob.modifiers.clear()
            ob.data = me
            done.add(me.name)

    def _merge_groups(self):
        """One object per group (instances and unbaked groups stay as they are)."""
        groups = {}
        for ob in self.parts:
            g = ob.get("group", "body")
            if g.startswith("instance:"):
                continue
            groups.setdefault(g, []).append(ob)
        merged = []
        for g, obs in groups.items():
            if len(obs) == 1:
                # One part: it takes the group's name too, so bake={"body": …} finds it.
                if obs[0].name != g and g not in bpy.data.objects:
                    obs[0].name = g
                merged.append(obs[0])
                continue
            target = obs[0]
            with bpy.context.temp_override(active_object=target, object=target,
                                           selected_objects=obs, selected_editable_objects=obs):
                bpy.ops.object.join()
            target.name = g
            self.parts = [p for p in self.parts if p is target or p not in obs]
            merged.append(target)
        return merged

    def _ground(self):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60)
        me = bpy.data.meshes.new("ground")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(self.mat("_asphalt", "#3B3E42", rough=0.92))
        g = bpy.data.objects.new("_ground", me)
        self.scene.collection.objects.link(g)
        return g

    EMISSIVE = ("headlight", "taillight", "indicator", "neon", "beacon")

    def _skip(self, m):
        return (m is None or m.name.startswith(("glass", "_", "neon")) or m.name in self.EMISSIVE)

    def _bake(self, sizes, dust=(0.0, 0.9, 0.42), ao_distance=0.6):
        """Bake AO x dust into one texture per object named in sizes, and
        multiply it into the object's base colours. A material belongs to the
        first object that bakes it; anything else using it gets a clean copy."""
        sc = self.scene
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = 24
        bake_dir = "/tmp/bake"
        os.makedirs(bake_dir, exist_ok=True)
        z0, z1, strength = dust
        if z1 <= z0:                     # no dust: a non-empty range, zero strength
            z1, strength = z0 + 1.0, 0.0

        meshes = [ob for ob in self.parts if ob.type == "MESH"]
        pristine = {}
        for ob in meshes:
            for slot in ob.material_slots:
                m = slot.material
                if not self._skip(m) and m.name not in pristine:
                    c = m.copy()
                    c.name = f"_plain_{m.name}"
                    pristine[m.name] = c
        owner = {}
        baked_meshes = set()
        dummy = bpy.data.images.new("_bake_dummy", 4, 4, alpha=False)

        order = [ob for name in sizes for ob in meshes if ob.name == name]
        for name in sizes:
            if not any(ob.name == name for ob in meshes):
                print(f"[{self.name}] WARNING: nothing named {name!r} to bake; objects: {[ob.name for ob in meshes]}")
        for ob in order:
            size = sizes[ob.name]
            if ob.data.name in baked_meshes:
                continue
            baked_meshes.add(ob.data.name)
            for slot in ob.material_slots:
                m = slot.material
                if self._skip(m):
                    continue
                if m.name in owner and owner[m.name] != ob.data.name:
                    c = pristine[m.name].copy()
                    c.name = f"{m.name}_{ob.name}"
                    slot.material = c
                owner.setdefault(slot.material.name, ob.data.name)

            for o in sc.objects:
                o.select_set(False)
            bpy.context.view_layer.objects.active = ob
            ob.select_set(True)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.006)
            bpy.ops.object.mode_set(mode="OBJECT")

            img = bpy.data.images.new(f"{ob.name}_ao", size, size, alpha=False)
            temp = []
            seen = set()
            for slot in ob.material_slots:
                m = slot.material
                if m is None or m.name in seen:
                    continue
                seen.add(m.name)
                nt = m.node_tree
                N, L = nt.nodes, nt.links
                if self._skip(m):
                    t = N.new("ShaderNodeTexImage")
                    t.image = dummy
                    N.active = t
                    temp.append((m, [t], None, None, None))
                    continue
                out = N["Material Output"]
                bsdf = N["Principled BSDF"]
                # Procedural art on the base colour (nganya livery): baked into the texture too.
                art = bsdf.inputs["Base Color"].links[0].from_socket if bsdf.inputs["Base Color"].is_linked else None
                ao = N.new("ShaderNodeAmbientOcclusion")
                ao.samples = 16
                ao.inputs["Distance"].default_value = ao_distance
                geo = N.new("ShaderNodeNewGeometry")
                sep = N.new("ShaderNodeSeparateXYZ")
                rng = N.new("ShaderNodeMapRange")
                rng.inputs["From Min"].default_value = z0
                rng.inputs["From Max"].default_value = z1
                rng.inputs["To Min"].default_value = strength
                rng.inputs["To Max"].default_value = 0.0
                noise = N.new("ShaderNodeTexNoise")
                noise.inputs["Scale"].default_value = 3.5
                nmul = N.new("ShaderNodeMath")
                nmul.operation = "MULTIPLY"
                dirt = N.new("ShaderNodeMix")
                dirt.data_type = "RGBA"
                dirt.inputs["A"].default_value = (1, 1, 1, 1)
                dirt.inputs["B"].default_value = lin("#B89A78")
                mult = N.new("ShaderNodeMix")
                mult.data_type = "RGBA"
                mult.blend_type = "MULTIPLY"
                mult.inputs["Factor"].default_value = 1.0
                aocol = N.new("ShaderNodeCombineColor")
                emit = N.new("ShaderNodeEmission")
                tex = N.new("ShaderNodeTexImage")
                tex.image = img
                L.new(geo.outputs["Position"], sep.inputs["Vector"])
                L.new(sep.outputs["Z"], rng.inputs["Value"])
                L.new(rng.outputs["Result"], nmul.inputs[0])
                L.new(noise.outputs["Fac"], nmul.inputs[1])
                L.new(nmul.outputs["Value"], dirt.inputs["Factor"])
                L.new(dirt.outputs["Result"], mult.inputs["A"])
                for ch in ("Red", "Green", "Blue"):
                    L.new(ao.outputs["AO"], aocol.inputs[ch])
                L.new(aocol.outputs["Color"], mult.inputs["B"])
                extra = []
                if art is not None:
                    withart = N.new("ShaderNodeMix")
                    withart.data_type = "RGBA"
                    withart.blend_type = "MULTIPLY"
                    withart.inputs["Factor"].default_value = 1.0
                    L.new(art, withart.inputs["A"])
                    L.new(mult.outputs["Result"], withart.inputs["B"])
                    L.new(withart.outputs["Result"], emit.inputs["Color"])
                    extra.append(withart)
                    m["_art"] = True
                else:
                    L.new(mult.outputs["Result"], emit.inputs["Color"])
                L.new(emit.outputs["Emission"], out.inputs["Surface"])
                N.active = tex
                temp.append((m, [ao, geo, sep, rng, noise, nmul, dirt, mult, aocol, emit] + extra, tex, bsdf, out))

            bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
            # Soften the bake noise (3x3 box blur), then save for the exporter.
            px = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)
            pad = np.pad(px[:, :, :3], ((1, 1), (1, 1), (0, 0)), mode="edge")
            px[:, :, :3] = sum(pad[i:i + size, j:j + size] for i in range(3) for j in range(3)) / 9.0
            img.pixels.foreach_set(px.ravel())
            img.filepath_raw = f"{bake_dir}/{self.name}_{ob.name}_ao.png"
            img.file_format = "PNG"
            img.save()
            for m, nodes, tex, bsdf, out in temp:
                nt = m.node_tree
                for n in nodes:
                    nt.nodes.remove(n)
                if tex is None:
                    continue
                nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
                base = (1.0, 1.0, 1.0, 1.0) if m.get("_art") else tuple(bsdf.inputs["Base Color"].default_value)
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                mix.blend_type = "MULTIPLY"
                mix.inputs["Factor"].default_value = 1.0
                mix.inputs["B"].default_value = base
                nt.links.new(tex.outputs["Color"], mix.inputs["A"])
                nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])

        # Objects that weren't baked but use a baked material get a clean copy.
        for ob in meshes:
            if ob.data.name in baked_meshes:
                continue
            for slot in ob.material_slots:
                m = slot.material
                if m is not None and m.name in owner and m.name in pristine:
                    c = pristine[m.name].copy()
                    c.name = f"{m.name}_{ob.name}"
                    slot.material = c
        for c in pristine.values():
            if c.users == 0:
                bpy.data.materials.remove(c)

    def finish(self, bake=None, dust=(0.0, 0.9, 0.42), ao_distance=0.6, shots=None):
        """bake: {object name after merging: texture size}, e.g. {"body": 1024, "wheel_fl": 512}."""
        o = self.opts
        self._apply_all()
        self._merge_groups()
        if o["bake"]:
            ground = self._ground()
            self._bake(bake or {"body": 1024}, dust=dust, ao_distance=ao_distance)
            bpy.data.objects.remove(ground)

        deps = bpy.context.evaluated_depsgraph_get()
        tris = 0
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        for ob in self.parts:
            if ob.type != "MESH":
                continue
            ev = ob.evaluated_get(deps)
            me = ev.to_mesh()
            me.calc_loop_triangles()
            tris += len(me.loop_triangles)
            mw = ob.matrix_world
            co = np.array([(mw @ v.co)[:] for v in me.vertices]) if len(me.vertices) else np.zeros((1, 3))
            lo = Vector(np.minimum(np.array(lo[:]), co.min(axis=0)))
            hi = Vector(np.maximum(np.array(hi[:]), co.max(axis=0)))
            ev.to_mesh_clear()

        os.makedirs(o["out"], exist_ok=True)
        for ob in self.scene.objects:
            ob.select_set(False)
        self.root.select_set(True)
        for ob in self.parts:
            ob.select_set(True)
        glb = os.path.join(o["out"], f"{self.name}.glb")
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", use_selection=True,
                                  export_apply=True, export_yup=True,
                                  export_image_format="JPEG", export_jpeg_quality=80)
        size = os.path.getsize(glb)
        self.meta.update({
            "triangles": tris,
            "bytes": size,
            "length_m": round(hi.y - lo.y, 2),
            "width_m": round(hi.x - lo.x, 2),
            "height_m": round(hi.z - lo.z, 2),
            "materials": sorted({s.material.name for ob in self.parts if ob.type == "MESH"
                                 for s in ob.material_slots if s.material}),
        })
        os.makedirs(o["previews"], exist_ok=True)
        with open(os.path.join(o["previews"], f"{self.name}.json"), "w") as fh:
            json.dump(self.meta, fh, indent=2)
        print(f"[{self.name}] {tris} triangles, {size / 1024:.0f} KB, "
              f"{self.meta['length_m']} x {self.meta['width_m']} x {self.meta['height_m']} m -> {glb}")
        if o["render"]:
            self.render(shots)

    # ── Previews ──
    def render(self, shots=None, size=(560, 380)):
        sc = self.scene
        o = self.opts
        g = self._ground()
        sun_data = bpy.data.lights.new("sun", type="SUN")
        sun_data.energy = 4.0
        sun_data.angle = math.radians(3)
        sun = bpy.data.objects.new("sun", sun_data)
        sun.rotation_euler = (math.radians(42), 0, math.radians(35))
        sc.collection.objects.link(sun)
        world = bpy.data.worlds.new("world")
        sc.world = world
        world.use_nodes = True
        nt = world.node_tree
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.sky_type = "NISHITA"
        sky.sun_disc = False
        sky.sun_elevation = math.radians(40)
        nt.links.new(sky.outputs["Color"], nt.nodes["Background"].inputs["Color"])
        nt.nodes["Background"].inputs["Strength"].default_value = 0.25
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = 40
        sc.cycles.use_denoising = True
        sc.render.resolution_x, sc.render.resolution_y = size
        sc.view_settings.view_transform = "AgX"
        L = max(self.meta.get("length_m", 5), 1.0)
        H = max(self.meta.get("height_m", 2), 0.5)
        shots = shots or [
            ("hero", (0.95 * L + 1.2, -1.15 * L - 1.6, 0.42 * L + 0.6 * H), (0, -0.05 * L, 0.45 * H), 50),
            ("rear", (-0.9 * L - 1.2, 1.25 * L + 1.6, 0.5 * L + 0.6 * H), (0, 0.05 * L, 0.45 * H), 50),
            ("nav", (0, 1.7 * L + 2.5, 0.8 * L + 2.5), (0, -0.5 * L, 0.3 * H), 35),
        ]
        paths = []
        for name, loc, target, lens in shots:
            cam_data = bpy.data.cameras.new(name)
            cam_data.lens = lens
            cam = bpy.data.objects.new(f"cam_{name}", cam_data)
            cam.location = loc
            cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
            sc.collection.objects.link(cam)
            sc.camera = cam
            path = f"/tmp/{self.name}_{name}.png"
            sc.render.filepath = path
            bpy.ops.render.render(write_still=True)
            paths.append(path)
        # One contact sheet per model (side by side).
        imgs = [bpy.data.images.load(p) for p in paths]
        w, h = size
        sheet = np.zeros((h, w * len(imgs), 4), dtype=np.float32)
        for i, im in enumerate(imgs):
            sheet[:, i * w:(i + 1) * w] = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
        out = bpy.data.images.new(f"{self.name}_sheet", w * len(imgs), h, alpha=False)
        out.pixels.foreach_set(sheet.ravel())
        out.filepath_raw = os.path.join(o["previews"], f"{self.name}.png")
        out.file_format = "PNG"
        out.save()
        # The hero shot alone, as a JPEG for the viewer.
        hero = imgs[0]
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 82
        hero.save_render(os.path.join(o["previews"], f"{self.name}_hero.jpg"), scene=sc)
        print(f"[{self.name}] previews -> {out.filepath_raw}")
        bpy.data.objects.remove(g)
