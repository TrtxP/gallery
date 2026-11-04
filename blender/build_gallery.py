"""
build_gallery.py  -  builds the whole 3D art gallery in Blender and exports it for Three.js.

What it does (one run, no manual clicking):
  1. Builds a realistic gallery room (10 x 14 x 4 m): floor, walls, ceiling, a big window with
     mullions, a freestanding partition, skirting boards.
  2. Creates CUSTOM models: a wooden chair and a lathe-turned vase on a pedestal.
  3. Imports EXTERNAL models you downloaded (assets/models/*.glb|gltf) and auto-fits their size
     and polygon count.
  4. Creates 6 artworks + frames (procedural placeholder paintings, or your own images from
     assets/artworks/art_01.jpg ... art_06.jpg).
  5. Lights the scene (sun through the window, sky, ceiling fill, one spotlight per artwork)
     and BAKES the lighting + procedural textures into 3 textures (floor / shell / props),
     so Three.js needs NO lights at all.
  6. Exports build/gallery.glb  and  build/gallery.json  (camera viewpoints + artwork info).

Run:
    blender --background --python build_gallery.py -- [options]

Options:
    --quick           tiny textures + few samples (about a minute) - use it to test the pipeline
    --res-scale F     scale all bake textures, e.g. 0.5 = half size (default 1.0)
    --samples N       bake samples (default 128)
    --exposure X      multiply all light power (default 1.0). Result too dark -> 1.5, too bright -> 0.7
    --gpu             try to bake on the GPU (OptiX / CUDA / HIP / Metal / oneAPI)
    --reuse-bakes     reuse existing <out>/textures/bake_*.png instead of baking again
                      (only when the geometry/lights of that object did not change)
    --preview         also render build/preview_*.png from the baked textures
    --out DIR         output folder (default: ./build next to this script)

Folders next to this script:
    assets/models/     put downloaded models here (see EXTERNAL_MODELS below)
    assets/artworks/   optional own paintings: art_01.jpg ... art_06.jpg (png / webp also fine)

Tested with Blender 5.0 (bpy). Written to also work on Blender 4.2 LTS+.
"""
import argparse
import glob
import json
import math
import os
import re
import sys
import time

import bpy  # must come first (the pip build of bpy registers bmesh/mathutils on import)
import bmesh  # noqa: E402
from mathutils import Matrix, Vector

import numpy as np  # bundled with Blender

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # pragma: no cover
    HERE = os.getcwd()

# =============================================================================================
#  CONFIG  (units: meters, Blender axes: X right, Y forward, Z up)
# =============================================================================================
ROOM_W, ROOM_L, ROOM_H = 10.0, 14.0, 4.0      # a real gallery hall: 4 m ceiling, 1.6 m eye level
HW, HL = ROOM_W / 2, ROOM_L / 2
WALL_T = 0.30                                  # wall thickness (visible in the window reveal)
WIN_HALF_W = 3.0                               # window on the back wall: x from -3 to +3
WIN_Z0, WIN_Z1 = 0.55, 3.55
EYE_H = 1.6                                    # camera height for the visitor
ART_H = 1.55                                   # artwork centre height (museum standard)
PART_Y, PART_W, PART_T, PART_H = -0.5, 4.4, 0.12, 3.2   # freestanding partition

# Texture sizes of the three baked atlases (width, height). Floor ratio = 10:14 -> square texels.
RES_FLOOR = (2560, 3584)
RES_SHELL = (2048, 2048)
RES_PROPS = (2048, 2048)

# External (downloaded) models. Put the files into assets/models/ .
#   file   : name without extension  (armchair -> armchair.glb | armchair.gltf | armchair/*.gltf)
#   xy     : position on the floor (Blender coordinates, meters)
#   rot    : rotation around Z in degrees
#   height : the model is scaled so its height is exactly this many meters
# Where to get them (free, CC0): https://polyhaven.com/models  or  https://sketchfab.com (downloadable)
EXTERNAL_MODELS = [
    dict(file="armchair", xy=(4.2, 3.3), rot=-53, height=0.85),
    dict(file="sculpture", xy=(-4.2, 3.3), rot=53, height=1.25),
]
MAX_TRIS_PER_MODEL = 25000                     # bigger models get decimated automatically

# The artworks. "box" = maximum size in meters; your own image keeps its aspect ratio inside it.
ARTWORKS = [
    dict(id="art_01", where=(0.0, PART_Y - PART_T / 2), normal=(0, -1), box=(1.8, 1.8), kind="rings",
         title="Concentric No. 1", artist="Studio Name", year=2026),
    dict(id="art_02", where=(HW, -4.2), normal=(-1, 0), box=(2.2, 1.4), kind="sunset",
         title="Last Light", artist="Studio Name", year=2026),
    dict(id="art_03", where=(HW, 2.0), normal=(-1, 0), box=(1.4, 1.8), kind="mondrian",
         title="Composition in Red, Blue, Yellow", artist="Studio Name", year=2026),
    dict(id="art_04", where=(0.0, PART_Y + PART_T / 2), normal=(0, 1), box=(2.2, 1.5), kind="waves",
         title="Tidal Study", artist="Studio Name", year=2026),
    dict(id="art_05", where=(-HW, 2.0), normal=(1, 0), box=(1.5, 1.9), kind="blobs",
         title="Cells", artist="Studio Name", year=2026),
    dict(id="art_06", where=(-HW, -4.2), normal=(1, 0), box=(2.0, 1.4), kind="clouds",
         title="Weather Report", artist="Studio Name", year=2026),
]


# =============================================================================================
#  small helpers
# =============================================================================================
def log(msg):
    print(f"[gallery] {msg}", flush=True)


def op(fn, **kw):
    """Call a bpy operator; silently drop keyword args this Blender version does not know."""
    kw = dict(kw)
    while True:
        try:
            return fn(**kw)
        except TypeError as e:
            m = re.search(r'keyword "(\w+)" unrecognized', str(e))
            if m and m.group(1) in kw:
                log(f"note: option '{m.group(1)}' not supported by this Blender, skipped")
                del kw[m.group(1)]
                continue
            raise


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description="Build the 3D art gallery")
    ap.add_argument("--out", default=os.path.join(HERE, "build"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--res-scale", type=float, default=None, help="scale all bake textures (e.g. 0.5)")
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--exposure", type=float, default=1.0)
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--reuse-bakes", action="store_true", help="skip bakes whose PNG already exists in <out>/textures")
    ap.add_argument("--preview", action="store_true")
    return ap.parse_args(argv)


def select_only(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def to_three(v):
    """Blender (Z up) -> Three.js / glTF (Y up) coordinates."""
    return [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]


# =============================================================================================
#  materials  (all procedural, so the repo needs no texture files; they get baked anyway)
# =============================================================================================
def _set(nt, sock, v):
    if isinstance(v, bpy.types.NodeSocket):
        nt.links.new(v, sock)
    else:
        sock.default_value = v


def mix_color(nt, a, b, fac=1.0, blend="MIX"):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    _set(nt, m.inputs[0], fac)
    _set(nt, m.inputs[6], a)
    _set(nt, m.inputs[7], b)
    return m.outputs[2]


def color_ramp(nt, fac_socket, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(1.0)
    for e, (pos, col) in zip(els, stops):
        e.position = pos
        e.color = col
    nt.links.new(fac_socket, r.inputs["Fac"])
    return r.outputs["Color"]


def new_mat(name, base=(0.8, 0.8, 0.8, 1.0), rough=0.9):
    m = bpy.data.materials.new(name)
    if m.node_tree is None:          # Blender < 5 needs this; 5.0 creates the node tree itself
        m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Roughness"].default_value = rough
    return m, nt, bsdf


def mat_plaster(name, tint=(0.93, 0.92, 0.89)):
    m, nt, bsdf = new_mat(name, rough=0.95)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 55.0
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    t = tint
    col = color_ramp(nt, noise.outputs["Fac"], [
        (0.35, (t[0] * 0.93, t[1] * 0.93, t[2] * 0.93, 1)), (0.65, (t[0], t[1], t[2], 1))])
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m


def mat_wood(name, dark, light, planks=False):
    """Oak. With planks=True it becomes a floor: 1.6 m x 0.18 m boards with different tints."""
    m, nt, bsdf = new_mat(name, rough=0.5)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (5.0, 85.0, 5.0)        # stretched along X = wood grain
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.0
    noise.inputs["Detail"].default_value = 5.0
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])
    if planks:
        streak = color_ramp(nt, noise.outputs["Fac"], [
            (0.30, (0.74, 0.74, 0.74, 1)), (0.70, (1.0, 1.0, 1.0, 1))])
        brick = nt.nodes.new("ShaderNodeTexBrick")
        brick.offset = 0.5
        brick.offset_frequency = 2
        brick.inputs["Color1"].default_value = dark
        brick.inputs["Color2"].default_value = light
        brick.inputs["Mortar"].default_value = (0.05, 0.03, 0.02, 1)
        brick.inputs["Scale"].default_value = 1.0
        brick.inputs["Mortar Size"].default_value = 0.004
        brick.inputs["Bias"].default_value = 0.0
        brick.inputs["Brick Width"].default_value = 1.6
        brick.inputs["Row Height"].default_value = 0.18
        nt.links.new(tc.outputs["Object"], brick.inputs["Vector"])
        col = mix_color(nt, brick.outputs["Color"], streak, 1.0, "MULTIPLY")
    else:
        col = color_ramp(nt, noise.outputs["Fac"], [(0.3, dark), (0.7, light)])
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m


def mat_ceramic(name):
    m, nt, bsdf = new_mat(name, rough=0.15)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    col = color_ramp(nt, noise.outputs["Fac"], [
        (0.35, (0.01, 0.12, 0.17, 1)), (0.65, (0.03, 0.34, 0.33, 1))])
    nt.links.new(col, bsdf.inputs["Base Color"])
    return m


def mat_image(name, image, rough=1.0):
    """Principled material with one image in Base Color (used for baked atlases and artworks)."""
    m, nt, bsdf = new_mat(name, rough=rough)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return m


# =============================================================================================
#  geometry helpers (everything is built directly in WORLD coordinates, objects stay at origin)
# =============================================================================================
def mesh_object(name, bm, mats, smooth=False):
    if smooth:
        for f in bm.faces:
            f.smooth = True
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _tag(verts, mat):
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat


def bm_quad(bm, pts, normal, mat=0):
    f = bm.faces.new([bm.verts.new(p) for p in pts])
    f.normal_update()
    if f.normal.dot(Vector(normal)) < 0:
        f.normal_flip()
    f.material_index = mat
    return f


def bm_box(bm, center, size, rot_z=0.0, mat=0):
    M = Matrix.Translation(center) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Diagonal((*size, 1.0))
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    _tag(res["verts"], mat)


def bm_obox(bm, center, n, r, u, size, mat=0):
    """Box with local axes n (size[0]), r (size[1]), u (size[2]). (n, r, u) must be right-handed."""
    B = Matrix(((n.x, r.x, u.x, 0), (n.y, r.y, u.y, 0), (n.z, r.z, u.z, 0), (0, 0, 0, 1)))
    M = Matrix.Translation(center) @ B @ Matrix.Diagonal((*size, 1.0))
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
    _tag(res["verts"], mat)


def bm_beam(bm, p0, p1, r0, r1, segs=14, mat=0):
    """Tapered round beam from p0 (radius r0) to p1 (radius r1)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    M = Matrix.Translation((p0 + p1) / 2) @ rot
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs,
                                radius1=r0, radius2=r1, depth=d.length, matrix=M)
    _tag(res["verts"], mat)


# =============================================================================================
#  room
# =============================================================================================
def build_shell(m_wall, m_ceil, m_dark):
    """Walls, ceiling, window reveal, mullions, partition, skirting. Single-sided surfaces only
    (no invisible outer faces), so the baked atlas is not wasted on things nobody sees."""
    bm = bmesh.new()
    H = ROOM_H
    wx, z0, z1 = WIN_HALF_W, WIN_Z0, WIN_Z1
    # ceiling
    bm_quad(bm, [(-HW, -HL, H), (HW, -HL, H), (HW, HL, H), (-HW, HL, H)], (0, 0, -1), 1)
    # west / east / front walls
    bm_quad(bm, [(-HW, -HL, 0), (-HW, HL, 0), (-HW, HL, H), (-HW, -HL, H)], (1, 0, 0))
    bm_quad(bm, [(HW, -HL, 0), (HW, HL, 0), (HW, HL, H), (HW, -HL, H)], (-1, 0, 0))
    bm_quad(bm, [(-HW, -HL, 0), (HW, -HL, 0), (HW, -HL, H), (-HW, -HL, H)], (0, 1, 0))
    # back wall (y = +HL) with the window opening: 4 pieces around the hole
    for (xa, xb, za, zb) in [(-HW, -wx, 0, H), (wx, HW, 0, H), (-wx, wx, 0, z0), (-wx, wx, z1, H)]:
        bm_quad(bm, [(xa, HL, za), (xb, HL, za), (xb, HL, zb), (xa, HL, zb)], (0, -1, 0))
    # window reveal (wall thickness): sill, head, left and right jamb
    t = WALL_T
    bm_quad(bm, [(-wx, HL, z0), (wx, HL, z0), (wx, HL + t, z0), (-wx, HL + t, z0)], (0, 0, 1))
    bm_quad(bm, [(-wx, HL, z1), (wx, HL, z1), (wx, HL + t, z1), (-wx, HL + t, z1)], (0, 0, -1))
    bm_quad(bm, [(-wx, HL, z0), (-wx, HL + t, z0), (-wx, HL + t, z1), (-wx, HL, z1)], (1, 0, 0))
    bm_quad(bm, [(wx, HL, z0), (wx, HL + t, z0), (wx, HL + t, z1), (wx, HL, z1)], (-1, 0, 0))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)

    # window mullions (dark metal): 4 verticals + 1 transom
    yc = HL + t / 2
    for i in range(1, 5):
        x = -wx + i * (2 * wx / 5)
        bm_box(bm, (x, yc, (z0 + z1) / 2), (0.07, 0.10, z1 - z0), mat=2)
    bm_box(bm, (0, yc, z0 + (z1 - z0) * 0.72), (2 * wx, 0.10, 0.07), mat=2)
    # skirting boards
    s_h, s_t = 0.12, 0.025
    bm_box(bm, (-HW + s_t / 2, 0, s_h / 2), (s_t, ROOM_L, s_h))
    bm_box(bm, (HW - s_t / 2, 0, s_h / 2), (s_t, ROOM_L, s_h))
    bm_box(bm, (0, -HL + s_t / 2, s_h / 2), (ROOM_W, s_t, s_h))
    bm_box(bm, (0, HL - s_t / 2, s_h / 2), (ROOM_W, s_t, s_h))
    # freestanding partition wall
    bm_box(bm, (0, PART_Y, PART_H / 2), (PART_W, PART_T, PART_H))
    return mesh_object("Shell", bm, [m_wall, m_ceil, m_dark])


def build_floor(mat):
    bm = bmesh.new()
    bm_quad(bm, [(-HW, -HL, 0), (HW, -HL, 0), (HW, HL, 0), (-HW, HL, 0)], (0, 0, 1))
    return mesh_object("Floor", bm, [mat])


# =============================================================================================
#  custom models
# =============================================================================================
def build_chair(xy, rot_deg, m_wood):
    """A wooden dining/gallery chair: splayed tapered legs, slatted tilted back, stretchers.
    Local frame: the chair looks along +X."""
    bm = bmesh.new()
    sx = sy = 0.20                                  # half-spacing of the legs
    seat_z = 0.46
    # seat (slightly thick, two layers for a soft edge)
    bm_box(bm, (0, 0, seat_z), (0.46, 0.46, 0.035))
    bm_box(bm, (0, 0, seat_z - 0.03), (0.40, 0.40, 0.03))
    # front legs: tapered + splayed
    for sgn in (-1, 1):
        bm_beam(bm, (sx * 1.12, sgn * sy * 1.12, 0.0), (sx, sgn * sy, seat_z - 0.02), 0.014, 0.024)
    # back legs continue up as the backrest posts, leaning back
    for sgn in (-1, 1):
        bm_beam(bm, (-sx * 1.12, sgn * sy * 1.12, 0.0), (-sx, sgn * sy, seat_z), 0.014, 0.024)
        bm_beam(bm, (-sx, sgn * sy, seat_z), (-sx - 0.07, sgn * sy * 0.95, 0.93), 0.024, 0.018)
    # back slats
    for z in (0.60, 0.72, 0.84):
        k = (z - seat_z) / (0.93 - seat_z)
        x = -sx - 0.07 * k
        bm_box(bm, (x - 0.004, 0, z), (0.014, 0.37, 0.075))
    # stretchers
    for sgn in (-1, 1):
        bm_beam(bm, (-sx * 1.06, sgn * sy * 1.06, 0.20), (sx * 1.06, sgn * sy * 1.06, 0.20), 0.012, 0.012, 10)
    bm_beam(bm, (-sx * 1.06, -sy * 1.06, 0.14), (-sx * 1.06, sy * 1.06, 0.14), 0.012, 0.012, 10)
    for f in bm.faces:
        f.material_index = 0
    M = Matrix.Translation((xy[0], xy[1], 0)) @ Matrix.Rotation(math.radians(rot_deg), 4, "Z")
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_object("Chair", bm, [m_wood])


def build_vase_on_pedestal(xy, m_ceramic, m_pedestal):
    """A lathe-turned vase (profile revolved around Z) standing on a white pedestal."""
    ped_h = 1.0
    # pedestal
    bm = bmesh.new()
    bm_box(bm, (xy[0], xy[1], ped_h / 2), (0.46, 0.46, ped_h))
    bm_box(bm, (xy[0], xy[1], 0.03), (0.54, 0.54, 0.06))              # plinth
    bm_box(bm, (xy[0], xy[1], ped_h + 0.012), (0.52, 0.52, 0.024))    # cap
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ped = mesh_object("Pedestal", bm, [m_pedestal])

    profile = [(0.0, 0.0), (0.085, 0.0), (0.11, 0.012), (0.17, 0.07), (0.205, 0.17), (0.19, 0.27),
               (0.12, 0.36), (0.075, 0.43), (0.07, 0.49), (0.09, 0.545), (0.105, 0.58),
               (0.088, 0.585), (0.06, 0.52), (0.05, 0.40), (0.0, 0.39)]
    bm = bmesh.new()
    vs = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + es, cent=(0, 0, 0), axis=(0, 0, 1), dvec=(0, 0, 0),
                   angle=2 * math.pi, space=Matrix.Identity(4), steps=48, use_merge=True,
                   use_normal_flip=False, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.transform(bm, matrix=Matrix.Translation((xy[0], xy[1], ped_h + 0.024)), verts=bm.verts)
    vase = mesh_object("Vase", bm, [m_ceramic], smooth=True)
    return [ped, vase]


# =============================================================================================
#  artworks
# =============================================================================================
def _pal(t, a, b, c, d):
    t = np.asarray(t, dtype=np.float32)[..., None]
    return np.asarray(a) + np.asarray(b) * np.cos(2 * np.pi * (np.asarray(c) * t + np.asarray(d)))


def _noise(w, h, cells, rng):
    g = rng.random((cells + 2, cells + 2)).astype(np.float32)
    ys = np.linspace(0, cells, h, dtype=np.float32)
    xs = np.linspace(0, cells, w, dtype=np.float32)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    fy, fx = ys - y0, xs - x0
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    top, bot = a + (b - a) * fx[None, :], c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def gen_art(kind, w, h, seed):
    """Procedural abstract paintings (placeholders, so the gallery works out of the box).
    Returns float32 (h, w, 3), row 0 = BOTTOM of the picture (Blender image order)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x, y = xx / (w - 1), yy / (h - 1)
    asp = w / h
    if kind == "rings":
        d = np.hypot((x - 0.5) * asp, y - 0.5)
        img = _pal(d * 7.0 + 0.12 * np.sin(d * 34), (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (1, 1, 1), (0.0, 0.1, 0.2))
        img = np.where((d < 0.07)[..., None], np.array([0.04, 0.04, 0.06]), img)
    elif kind == "sunset":
        hor = 0.40
        u = np.clip((y - hor) / (1 - hor), 0, 1)[..., None] ** 0.7
        sky = (1 - u) * np.array([1.0, 0.62, 0.25]) + u * np.array([0.14, 0.10, 0.35])
        d = np.hypot((x - 0.5) * asp, y - 0.52)
        sun = np.clip((0.13 - d) / 0.01, 0, 1)[..., None]
        sky = sky * (1 - sun) + np.array([1.0, 0.92, 0.65]) * sun
        glow = np.exp(-(((x - 0.5) * asp) ** 2) / 0.02) * (0.55 + 0.45 * np.sin(y * 260 + x * 9))
        sea = (1 - glow[..., None]) * np.array([0.04, 0.11, 0.20]) + glow[..., None] * np.array([0.95, 0.55, 0.30])
        img = np.where((y < hor)[..., None], sea, sky)
    elif kind == "mondrian":
        img = np.ones((h, w, 3), np.float32) * np.array([0.95, 0.94, 0.90])
        img[(x < 0.30) & (y > 0.78)] = (0.80, 0.08, 0.07)
        img[(x > 0.72) & (y > 0.78)] = (0.97, 0.80, 0.10)
        img[(x > 0.30) & (x < 0.72) & (y < 0.35)] = (0.10, 0.25, 0.66)
        line = 0.011
        for lx in (0.30, 0.72):
            img[np.abs(x - lx) < line] = 0.04
        for ly in (0.35, 0.78):
            img[np.abs(y - ly) < line * asp] = 0.04
    elif kind == "waves":
        t = y * 3 + 0.35 * np.sin(x * asp * 9 + y * 5) + 0.2 * np.sin(x * asp * 21)
        img = _pal(np.floor(t * 7) / 7, (0.5, 0.45, 0.5), (0.5, 0.5, 0.5), (1, 1, 0.5), (0.8, 0.9, 0.3))
    elif kind == "blobs":
        n = 26
        pts = rng.random((n, 2)).astype(np.float32) * np.array([asp, 1.0], np.float32)
        img = np.zeros((h, w, 3), np.float32)
        for r0 in range(0, h, 32):
            px = np.stack([x[r0:r0 + 32] * asp, y[r0:r0 + 32]], -1).reshape(-1, 2)
            dist = np.hypot(px[:, None, 0] - pts[None, :, 0], px[:, None, 1] - pts[None, :, 1])
            idx = dist.argmin(1)
            two = np.partition(dist, 1, axis=1)[:, :2]
            col = _pal(idx / n * 0.9 + 0.05, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (1, 1, 1), (0.0, 0.33, 0.67))
            col[(two[:, 1] - two[:, 0]) < 0.006] = 0.05
            img[r0:r0 + 32] = col.reshape(-1, w, 3)[: img[r0:r0 + 32].shape[0]]
    else:  # clouds
        nz = 0.55 * _noise(w, h, 5, rng) + 0.28 * _noise(w, h, 11, rng) + 0.17 * _noise(w, h, 23, rng)
        img = _pal(nz * 1.2 + 0.3, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (1, 0.7, 0.4), (0.0, 0.15, 0.2))
    img = img + rng.normal(0, 0.008, img.shape)               # a little film grain
    return np.clip(img, 0, 1).astype(np.float32)


def artwork_image(spec, tex_dir, idx):
    """Your own file from assets/artworks/<id>.* if it exists, else a generated placeholder."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = os.path.join(HERE, "assets", "artworks", f"{spec['id']}.{ext}")
        if os.path.exists(p):
            img = bpy.data.images.load(p)
            img.colorspace_settings.name = "sRGB"
            img.pack()
            log(f"{spec['id']}: using your image {os.path.basename(p)}")
            return img
    px_per_m = 480
    w, h = int(spec["box"][0] * px_per_m), int(spec["box"][1] * px_per_m)
    arr = gen_art(spec["kind"], w, h, seed=100 + idx)
    img = bpy.data.images.new(spec["id"], w, h, alpha=False)
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :3] = arr
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(tex_dir, f"{spec['id']}.png")
    img.file_format = "PNG"
    img.save()
    img.colorspace_settings.name = "sRGB"
    return img


def build_artwork(spec, idx, tex_dir, m_frame):
    """Returns (picture_object, frame_bmesh, light_target, viewpoint_dict_part)."""
    n = Vector((spec["normal"][0], spec["normal"][1], 0)).normalized()
    up = Vector((0, 0, 1))
    r = up.cross(n)                                    # viewer's right when looking at the picture
    base = Vector((spec["where"][0], spec["where"][1], ART_H))
    img = artwork_image(spec, tex_dir, idx)
    aspect = img.size[0] / img.size[1]
    bw, bh = spec["box"]
    w, h = (bh * aspect, bh) if aspect <= bw / bh else (bw, bw / aspect)
    c = base + n * 0.012
    # picture plane (own object, own image, not baked)
    bm = bmesh.new()
    pts = [c - r * w / 2 - up * h / 2, c + r * w / 2 - up * h / 2,
           c + r * w / 2 + up * h / 2, c - r * w / 2 + up * h / 2]
    f = bm.faces.new([bm.verts.new(p) for p in pts])
    uv = bm.loops.layers.uv.new("UVMap")
    for loop, (u_, v_) in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        loop[uv].uv = (u_, v_)
    mat = mat_image(f"M_{spec['id']}", img, rough=0.6)
    pic = mesh_object(f"Art_{idx + 1:02d}", bm, [mat])
    return pic, n, r, up, base, w, h


def add_frame(bm, base, n, r, up, w, h, fw=0.05, depth=0.05):
    for center, size in [
        (base + up * (h / 2 + fw / 2), (depth, w + 2 * fw, fw)),
        (base - up * (h / 2 + fw / 2), (depth, w + 2 * fw, fw)),
        (base - r * (w / 2 + fw / 2), (depth, fw, h)),
        (base + r * (w / 2 + fw / 2), (depth, fw, h)),
    ]:
        bm_obox(bm, center + n * depth / 2, n, r, up, size, mat=0)


# =============================================================================================
#  external models
# =============================================================================================
def find_model(stem):
    d = os.path.join(HERE, "assets", "models")
    cands = [os.path.join(d, f"{stem}.glb"), os.path.join(d, f"{stem}.gltf")]
    cands += sorted(glob.glob(os.path.join(d, stem, "*.gltf")) + glob.glob(os.path.join(d, stem, "*.glb")))
    return next((c for c in cands if os.path.exists(c)), None)


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def import_external(spec):
    path = find_model(spec["file"])
    if not path:
        log(f"external model '{spec['file']}' not found in assets/models/ - skipped")
        return []
    before = set(bpy.data.objects)
    op(bpy.ops.import_scene.gltf, filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    for o in new:
        if o.type != "MESH":
            continue
        mw = o.matrix_world.copy()
        o.parent = None
        o.data = o.data.copy()
        o.modifiers.clear()
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    for o in new:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    if not meshes:
        log(f"'{spec['file']}' has no meshes - skipped")
        return []
    # fit: bottom-centre to the given floor spot, uniform scale to the requested height, rotate
    pts = [v.co for o in meshes for v in o.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = spec["height"] / max(mx.z - mn.z, 1e-6)
    M = (Matrix.Translation((spec["xy"][0], spec["xy"][1], 0)) @ Matrix.Rotation(math.radians(spec["rot"]), 4, "Z")
         @ Matrix.Scale(s, 4) @ Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    for o in meshes:
        o.data.transform(M)
    # polygon budget
    total = sum(tri_count(o) for o in meshes)
    if total > MAX_TRIS_PER_MODEL:
        ratio = MAX_TRIS_PER_MODEL / total
        for o in meshes:
            mod = o.modifiers.new("dec", "DECIMATE")
            mod.ratio = max(ratio, 0.02)
            select_only([o])
            bpy.ops.object.modifier_apply(modifier=mod.name)
        log(f"{spec['file']}: {total} -> {sum(tri_count(o) for o in meshes)} triangles")
    else:
        log(f"{spec['file']}: {total} triangles (ok), scaled x{s:.3f}")
    return meshes


# =============================================================================================
#  lights
# =============================================================================================
def add_light(name, kind, loc, energy, color=(1, 1, 1), direction=None, **props):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    for k, v in props.items():
        setattr(ld, k, v)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    if direction is not None:
        ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return ob


def build_lights(art_info, exposure):
    sc = bpy.context.scene
    # sky (what lights the room through the window besides the sun)
    w = bpy.data.worlds.new("Sky")
    if w.node_tree is None:
        w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.70, 1.0, 1.0)
    bg.inputs[1].default_value = 0.9 * exposure
    sc.world = w
    # sun coming through the big window: travels towards -Y, slightly +X, downwards
    add_light("Sun", "SUN", (0, HL + 10, 10), 3.6 * exposure, color=(1.0, 0.94, 0.85),
              direction=(0.35, -0.75, -0.55), angle=math.radians(1.6))
    # soft ceiling fill (two long area strips)
    for i, x in enumerate((-2.5, 2.5)):
        add_light(f"Fill_{i}", "AREA", (x, 0, ROOM_H - 0.03), 90 * exposure, color=(1.0, 0.93, 0.82),
                  direction=(0, 0, -1), shape="RECTANGLE", size=1.0, size_y=9.0)
    # one gallery spotlight per artwork (wall-wash + the typical "scallop" on the wall)
    for a in art_info:
        loc = Vector(a["base"]) + a["n"] * 1.7
        loc.z = ROOM_H - 0.2
        add_light(f"Spot_{a['id']}", "SPOT", loc, 260 * exposure, color=(1.0, 0.90, 0.76),
                  direction=Vector(a["base"]) - loc, spot_size=math.radians(62), spot_blend=0.65,
                  shadow_soft_size=0.12)


# =============================================================================================
#  UV + baking
# =============================================================================================
def real_uvs(me):
    """UV layers without Blender's hidden helper layers (names starting with '.', seen in 5.x)."""
    return [l for l in me.uv_layers if not l.name.startswith(".")]


def ensure_single_uv(obj):
    me = obj.data
    layers = real_uvs(me)
    if not layers:
        me.uv_layers.new(name="UVMap")
        return
    names = [l.name for l in layers]
    for n in names[1:]:
        me.uv_layers.remove(me.uv_layers[n])     # by name: layer pointers go stale after a removal
    me.uv_layers[names[0]].name = "UVMap"


def join_objects(objs, name):
    for o in objs:
        ensure_single_uv(o)
    if len(objs) > 1:
        select_only(objs, active=objs[0])
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active if len(objs) > 1 else objs[0]
    ob.name = name
    ob.data.name = name
    return ob


def add_bake_uv_smart(obj, island_margin):
    me = obj.data
    uv = me.uv_layers.new(name="BakeUV")
    layers = real_uvs(me)
    for l in layers:
        l.active_render = (l.name != "BakeUV") if len(layers) > 1 else True
    me.uv_layers.active = uv
    select_only([obj])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    op(bpy.ops.uv.smart_project, angle_limit=math.radians(66), island_margin=island_margin,
       area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def add_bake_uv_floor(obj):
    me = obj.data
    uv = me.uv_layers.new(name="BakeUV")
    uv.active_render = True
    me.uv_layers.active = uv
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.x + HW) / ROOM_W, (co.y + HL) / ROOM_L)


def bake_object(obj, name, size, margin, tex_dir, reuse=False):
    existing = os.path.join(tex_dir, f"bake_{name}.png")
    if reuse and os.path.exists(existing):
        img = bpy.data.images.load(existing)
        img.name = f"bake_{name}"
        img.colorspace_settings.name = "sRGB"
        img.pack()
        log(f"reusing existing bake '{name}' ({img.size[0]}x{img.size[1]})")
        return img
    img = bpy.data.images.new(f"bake_{name}", size[0], size[1], alpha=False)
    img.colorspace_settings.name = "sRGB"
    me = obj.data
    me.uv_layers.active = me.uv_layers["BakeUV"]
    select_only([obj])
    temp = []
    for slot in obj.material_slots:
        if slot.material:
            nt = slot.material.node_tree
            node = nt.nodes.new("ShaderNodeTexImage")
            node.image = img
            node.select = True
            nt.nodes.active = node
            temp.append((nt, node))
    t0 = time.time()
    log(f"baking '{name}'  {size[0]}x{size[1]} ...")
    op(bpy.ops.object.bake, type="COMBINED", pass_filter={"DIRECT", "INDIRECT", "DIFFUSE", "EMIT"},
       margin=margin, margin_type="EXTEND", use_clear=True)
    log(f"  done in {time.time() - t0:.0f}s")
    for nt, node in temp:
        nt.nodes.remove(node)
    img.filepath_raw = os.path.join(tex_dir, f"bake_{name}.png")
    img.file_format = "PNG"
    img.save()
    return img


def finalize_baked(obj, img, name):
    """Drop the procedural materials and the old UV: the object now only knows its baked texture."""
    me = obj.data
    for n in [l.name for l in real_uvs(me) if l.name != "BakeUV"]:
        me.uv_layers.remove(me.uv_layers[n])
    me.materials.clear()
    mat = mat_image(f"M_baked_{name}", img, rough=1.0)
    me.materials.append(mat)
    for p in me.polygons:
        p.material_index = 0
    return mat


def setup_gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for t in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                prefs.compute_device_type = t
            except TypeError:
                continue
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == t]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == t
                bpy.context.scene.cycles.device = "GPU"
                log(f"GPU baking enabled ({t}: {', '.join(d.name for d in devs)})")
                return
        log("no usable GPU found - baking on CPU")
    except Exception as e:  # noqa
        log(f"GPU setup failed ({e}) - baking on CPU")


# =============================================================================================
#  preview render (optional): shows the baked result exactly as Three.js will show it (unlit)
# =============================================================================================
def render_previews(out_dir, views, extra_mats):
    sc = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.hide_render = True
    for m in extra_mats:
        nt = m.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
        if not (bsdf and tex):
            continue
        for lk in list(nt.links):
            if lk.to_socket == bsdf.inputs["Base Color"]:
                nt.links.remove(lk)
        bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
        for name in ("Specular IOR Level", "Specular"):
            if name in bsdf.inputs:
                bsdf.inputs[name].default_value = 0.0
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.cycles.samples = 12
    sc.cycles.use_adaptive_sampling = False
    sc.view_settings.view_transform = "Standard"
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.angle = math.radians(80)
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    for name, pos, target in views:
        cam.location = pos
        cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = os.path.join(out_dir, f"preview_{name}.png")
        log(f"rendering preview_{name}.png")
        bpy.ops.render.render(write_still=True)


# =============================================================================================
#  main
# =============================================================================================
def main():
    args = parse_args()
    out_dir = os.path.abspath(args.out)
    tex_dir = os.path.join(out_dir, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    for sub in ("models", "artworks"):
        os.makedirs(os.path.join(HERE, "assets", sub), exist_ok=True)
    t_start = time.time()

    # ---- scene + render settings
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.samples = args.samples or (16 if args.quick else 128)
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.01
    cy.max_bounces, cy.diffuse_bounces, cy.glossy_bounces = 8, 6, 2
    cy.sample_clamp_indirect = 6.0
    cy.device = "CPU"
    try:
        cy.use_denoising = True
    except Exception:  # noqa
        pass
    sc.view_settings.view_transform = "Standard"
    if args.gpu:
        setup_gpu()
    k = args.res_scale or (1 / 8 if args.quick else 1.0)
    scale = lambda wh: (max(64, int(wh[0] * k)), max(64, int(wh[1] * k)))  # noqa: E731
    res_floor, res_shell, res_props = scale(RES_FLOOR), scale(RES_SHELL), scale(RES_PROPS)

    # ---- materials
    m_floor = mat_wood("M_FloorOak", (0.20, 0.11, 0.05, 1), (0.34, 0.20, 0.10, 1), planks=True)
    m_wall = mat_plaster("M_Plaster")
    m_ceil = mat_plaster("M_Ceiling", (0.97, 0.97, 0.96))
    m_dark = new_mat("M_DarkMetal", (0.02, 0.02, 0.022, 1), 0.4)[0]
    m_frame = new_mat("M_FrameBlack", (0.015, 0.015, 0.017, 1), 0.45)[0]
    m_wood = mat_wood("M_ChairOak", (0.20, 0.10, 0.045, 1), (0.42, 0.25, 0.12, 1))
    m_ceramic = mat_ceramic("M_Ceramic")
    m_pedestal = mat_plaster("M_Pedestal", (0.88, 0.88, 0.86))

    # ---- geometry
    floor = build_floor(m_floor)
    shell = build_shell(m_wall, m_ceil, m_dark)
    props = [build_chair((-4.2, -1.1), 0, m_wood)]
    props += build_vase_on_pedestal((4.1, -1.1), m_ceramic, m_pedestal)
    ext_loaded = 0
    for spec in EXTERNAL_MODELS:
        got = import_external(spec)
        ext_loaded += 1 if got else 0
        props += got
    if ext_loaded == 0:
        log("WARNING: no external model loaded. The assignment needs at least one - download a "
            "model (e.g. polyhaven.com/models) and put it into assets/models/ (see EXTERNAL_MODELS).")

    # ---- artworks + frames
    art_objs, art_info, frame_bm = [], [], bmesh.new()
    for i, spec in enumerate(ARTWORKS):
        pic, n, r, up, base, w, h = build_artwork(spec, i, tex_dir, m_frame)
        add_frame(frame_bm, base, n, r, up, w, h)
        art_objs.append(pic)
        art_info.append(dict(id=spec["id"], spec=spec, node=pic.name, n=n, base=base, w=w, h=h))
    bmesh.ops.recalc_face_normals(frame_bm, faces=frame_bm.faces[:])
    props.append(mesh_object("Frames", frame_bm, [m_frame]))

    # ---- lights
    build_lights(art_info, args.exposure)

    # ---- bake: Floor, Shell, Props (each its own atlas)
    props_obj = join_objects(props, "Props")
    margin = lambda res: max(2, max(res) // 256)  # noqa: E731
    add_bake_uv_floor(floor)
    add_bake_uv_smart(shell, island_margin=2.0 * margin(res_shell) / res_shell[0])
    add_bake_uv_smart(props_obj, island_margin=2.0 * margin(res_props) / res_props[0])
    baked = {}
    for name, obj, res in (("floor", floor, res_floor), ("shell", shell, res_shell), ("props", props_obj, res_props)):
        baked[name] = (obj, bake_object(obj, name, res, margin(res), tex_dir, args.reuse_bakes))
    baked_mats = [finalize_baked(obj, img, name) for name, (obj, img) in baked.items()]
    log(f"triangles: floor {tri_count(floor)}, shell {tri_count(shell)}, props {tri_count(props_obj)}")

    # ---- viewpoints (empties) + json
    vps = [dict(id="overview", title="Overview", position=Vector((0, -HL + 0.9, EYE_H)),
                target=Vector((0, 2.0, 1.7)), artwork=None)]
    for a in art_info:
        dist = min(max(1.35 * max(a["w"], a["h"]) + 0.9, 2.6), 3.8)
        pos = Vector((a["base"].x, a["base"].y, EYE_H)) + a["n"] * dist
        s = a["spec"]
        vps.append(dict(id=s["id"], title=s["title"], artist=s["artist"], year=s["year"],
                        position=pos, target=Vector(a["base"]),
                        artwork=dict(node=a["node"], width=round(a["w"], 3), height=round(a["h"], 3))))
    empties = []
    for i, v in enumerate(vps):
        e = bpy.data.objects.new(f"Viewpoint_{i:02d}", None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 0.3
        e.location = v["position"]
        e.rotation_euler = (v["target"] - v["position"]).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(e)
        empties.append(e)
    meta = dict(
        coordinateSystem="Three.js / glTF (Y up). Converted from Blender (Z up): x, z, -y",
        room=dict(width=ROOM_W, length=ROOM_L, height=ROOM_H),
        # boxes the web camera must walk around (centre / size in the X-Z plane, Three.js coordinates)
        obstacles=[dict(id="partition", center=[0, round(-PART_Y, 3)], size=[PART_W, PART_T])],
        eyeHeight=EYE_H, suggestedFov=55,
        viewpoints=[dict(
            id=v["id"], title=v["title"], artist=v.get("artist", ""), year=v.get("year"),
            description="", position=to_three(v["position"]), target=to_three(v["target"]),
            artwork=v["artwork"]) for v in vps])
    json_path = os.path.join(out_dir, "gallery.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # ---- export GLB
    export_objs = [floor, shell, props_obj] + art_objs + empties
    select_only(export_objs)
    glb_path = os.path.join(out_dir, "gallery.glb")
    op(bpy.ops.export_scene.gltf, filepath=glb_path, export_format="GLB", use_selection=True,
       export_apply=True, export_yup=True, export_image_format="JPEG", export_jpeg_quality=88,
       export_materials="EXPORT", export_cameras=False, export_lights=False, export_extras=False)
    log(f"exported {glb_path}  ({os.path.getsize(glb_path) / 1e6:.1f} MB)")
    op(bpy.ops.wm.save_as_mainfile, filepath=os.path.join(out_dir, "gallery.blend"), compress=True)

    # ---- optional preview renders
    if args.preview:
        art_mats = [o.data.materials[0] for o in art_objs]
        views = [("overview", tuple(vps[0]["position"]), tuple(vps[0]["target"])),
                 ("art_01", tuple(vps[1]["position"]), tuple(vps[1]["target"])),
                 ("art_03", tuple(vps[3]["position"]), tuple(vps[3]["target"])),
                 ("window", (-0.5, 1.0, EYE_H), (0.3, HL, 1.9))]
        render_previews(out_dir, views, baked_mats + art_mats)

    log(f"ALL DONE in {(time.time() - t_start) / 60:.1f} min  ->  {out_dir}")


if __name__ == "__main__":
    main()
