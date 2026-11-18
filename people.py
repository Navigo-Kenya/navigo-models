"""Riders and passengers for the boda and the bicycle.

A person is built from a pose: a few key points (pelvis, chest, neck, head,
shoulders, hands, hips, ankles, toes); elbows and knees are solved (two-bone
IK) so hands land on the grips and feet on the pegs. Bodies are tapered
capsules and lofted ellipses; clothing is per part (a material each).
At map scale only the outline, the helmet and the clothes' colours read, so
faces aren't modelled: everyone wears a helmet.
"""
import math

import bmesh
from mathutils import Matrix, Vector

from kit import capsule, ellipsoid, two_bone

THIGH, SHIN = 0.43, 0.42
UPPER_ARM, FOREARM = 0.29, 0.26


def _ring(center, lateral, forward, rx, ry, count=14):
    return [center + lateral * (rx * math.cos(2 * math.pi * k / count)) + forward * (ry * math.sin(2 * math.pi * k / count))
            for k in range(count)]


def torso(bm, pelvis, chest, neck, mat, widths=((0.165, 0.105), (0.15, 0.095), (0.18, 0.115), (0.19, 0.11), (0.15, 0.085)),
          grow=0.0):
    """A lofted torso from the pelvis to the neck (lateral axis: X)."""
    pelvis, chest, neck = Vector(pelvis), Vector(chest), Vector(neck)
    pts = [pelvis, pelvis.lerp(chest, 0.5), chest, chest.lerp(neck, 0.55), neck]
    lateral = Vector((1, 0, 0))
    rings = []
    for i, (c, (rx, ry)) in enumerate(zip(pts, widths)):
        up = (pts[min(i + 1, 4)] - pts[max(i - 1, 0)]).normalized()
        forward = up.cross(lateral).normalized()
        rings.append([bm.verts.new(p) for p in _ring(c, lateral, forward, rx + grow, ry + grow)])
    m = len(rings[0])
    for kk in range(len(rings) - 1):
        for i in range(m):
            j = (i + 1) % m
            f = bm.faces.new((rings[kk][i], rings[kk][j], rings[kk + 1][j], rings[kk + 1][i]))
            f.material_index = mat
    for ring, flip in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(list(reversed(ring)) if flip else ring)
        f.material_index = mat


def person(k, name, pose, outfit, vest=False, group=None):
    """pose: dict of points; outfit: dict of materials (skin, helmet, visor, top, sleeves, trousers, shoes,
    and vest, stripe when vest=True). Adds one object; returns it."""
    mats = ["skin", "helmet", "visor", "top", "sleeves", "trousers", "shoes"] + (["vest", "stripe"] if vest else [])
    idx = {m: i for i, m in enumerate(mats)}
    bm = bmesh.new()
    P = {key: Vector(v) for key, v in pose.items()}

    # Torso, neck, head with a full-face helmet.
    torso(bm, P["pelvis"], P["chest"], P["neck"], idx["top"])
    if vest:
        torso(bm, P["pelvis"] + (P["chest"] - P["pelvis"]) * 0.12, P["chest"], P["chest"].lerp(P["neck"], 0.4),
              idx["vest"], widths=((0.155, 0.10), (0.158, 0.10), (0.188, 0.122), (0.196, 0.118), (0.17, 0.10)), grow=0.008)
        for t in (0.42, 0.72):
            c = P["pelvis"].lerp(P["chest"], t)
            up = (P["chest"] - P["pelvis"]).normalized()
            fwd = up.cross(Vector((1, 0, 0))).normalized()
            rx, ry = (0.168, 0.108) if t < 0.6 else (0.182, 0.118)
            lower = [bm.verts.new(p) for p in _ring(c - up * 0.022, Vector((1, 0, 0)), fwd, rx + 0.016, ry + 0.016)]
            upper = [bm.verts.new(p) for p in _ring(c + up * 0.022, Vector((1, 0, 0)), fwd, rx + 0.016, ry + 0.016)]
            m = len(lower)
            for i in range(m):
                j = (i + 1) % m
                f = bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
                f.material_index = idx["stripe"]
    capsule(bm, P["neck"], P["neck"] + (P["head"] - P["neck"]) * 0.45, 0.05, 0.048, idx["skin"], segs=10)
    head_dir = (P["head"] - P["neck"]).normalized()
    look = Vector(pose.get("look", (0, -1, 0)))
    look = (look - head_dir * look.dot(head_dir)).normalized()      # gaze, square to the neck
    side = look.cross(head_dir).normalized()
    rot = Matrix((side, look, head_dir)).transposed()               # local x: side, y: gaze, z: up
    ellipsoid(bm, P["head"] + head_dir * 0.01, (0.138, 0.15, 0.152), idx["helmet"], segs=18, rings=12, rotation=rot)
    ellipsoid(bm, P["head"] + look * 0.105 + head_dir * 0.012, (0.11, 0.055, 0.07), idx["visor"], segs=14, rings=8, rotation=rot)

    # Arms (elbows solved, bending out and down).
    for s, sh, hand in ((1, "l_shoulder", "l_hand"), (-1, "r_shoulder", "r_hand")):
        elbow = two_bone(P[sh], P[hand], UPPER_ARM, FOREARM, Vector((s * 1.0, 0.3, -0.8)))
        capsule(bm, P[sh], elbow, 0.058, 0.047, idx["sleeves"], segs=10)
        capsule(bm, elbow, P[hand], 0.046, 0.036, idx["sleeves"], segs=10)
        ellipsoid(bm, P[hand], (0.042, 0.05, 0.035), idx["skin"], segs=10, rings=6)
    # Legs (knees solved, bending forward and a little out).
    for s, hip, ankle, toe in ((1, "l_hip", "l_ankle", "l_toe"), (-1, "r_hip", "r_ankle", "r_toe")):
        knee = two_bone(P[hip], P[ankle], THIGH, SHIN, Vector((s * 0.25, -1.0, 0.35)))
        capsule(bm, P[hip], knee, 0.085, 0.062, idx["trousers"], segs=12)
        capsule(bm, knee, P[ankle], 0.058, 0.043, idx["trousers"], segs=12)
        capsule(bm, P[ankle] + Vector((0, 0.02, -0.02)), P[toe], 0.045, 0.04, idx["shoes"], segs=10)

    return k.add(name, bm, [outfit[m] for m in mats], group=group or name)


def mirror_x(p):
    return (-p[0], p[1], p[2])


def seated_pose(pelvis, lean, hands, ankles, toes, look=(0, -1, 0), shoulder_w=0.19, hip_w=0.095):
    """A seated rider: spine from the pelvis, leaning forward by `lean` degrees."""
    pelvis = Vector(pelvis)
    a = math.radians(lean)
    up = Vector((0, -math.sin(a), math.cos(a)))
    chest = pelvis + up * 0.32
    neck = pelvis + up * 0.52
    head = neck + Vector((0, -math.sin(a) * 0.5, 1)).normalized() * 0.17
    shoulder = neck - up * 0.05
    return {
        "pelvis": pelvis, "chest": chest, "neck": neck, "head": head, "look": look,
        "l_shoulder": shoulder + Vector((shoulder_w, 0, 0)), "r_shoulder": shoulder + Vector((-shoulder_w, 0, 0)),
        "l_hand": Vector(hands), "r_hand": Vector(mirror_x(hands)),
        "l_hip": pelvis + Vector((hip_w, 0, -0.02)), "r_hip": pelvis + Vector((-hip_w, 0, -0.02)),
        "l_ankle": Vector(ankles[0]), "r_ankle": Vector(ankles[1]),
        "l_toe": Vector(toes[0]), "r_toe": Vector(toes[1]),
    }
