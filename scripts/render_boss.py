"""Render BOSS: the arena's knight versus the PRODUCTION BUG. Blender (bpy, Cycles, OptiX).

The boss is a giant beetle: a glowing core wrapped in a few hundred armour plates (cubes laid on
ellipsoids), six cylinder legs, pink eyes, mandibles. It rears a front leg and slams the floor
where the knight stood (shockwave, camera shake); the knight jumps clear, runs in and lands a
three-hit combo - slice, chop, spin - facing the boss. The blade leaves a glowing ribbon behind it;
every hit throws sparks (rigid bodies), flashes the boss's vents and shakes the camera. On the last
hit every plate becomes a rigid body, the core flashes and the boss comes apart in slow motion.
The knight cheers; the film fades to black and loops.

Hit frames are not guessed: the script evaluates the blade tip every frame and takes, in each
swing, the frame where the tip reaches furthest into the boss. They are written to boss_hits.json
for assemble_boss.py, together with their screen positions for the damage numbers.

Usage:
    py -3.11 scripts/render_boss.py -- <out_dir>
Env:
    BOSS_W (1000)  BOSS_H (420)  BOSS_SAMPLES (96)  BOSS_ONLY ("0,32,74")  BOSS_STEP (2)
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "render_boss")
W = int(os.environ.get("BOSS_W", "1000"))
H = int(os.environ.get("BOSS_H", "420"))
SAMPLES = int(os.environ.get("BOSS_SAMPLES", "96"))
STEP = int(os.environ.get("BOSS_STEP", "2"))
ONLY = [int(x) for x in os.environ.get("BOSS_ONLY", "").split(",") if x.strip()]
KNIGHT = os.path.normpath(os.path.join(HERE, "..", "..", "site", "arena", "assets", "kaykit", "Knight.glb"))
os.makedirs(OUT, exist_ok=True)
random.seed(7)

T_JUMP, T_SLAM, T_RUN, T_SLICE, T_CHOP, T_SPIN = 12, 26, 40, 52, 78, 117
SWINGS = [("slice", T_SLICE, T_CHOP), ("chop", T_CHOP, T_SPIN), ("spin", T_SPIN, T_SPIN + 40)]
PINK, ORANGE, YELLOW = (0.925, 0.282, 0.600), (0.976, 0.451, 0.086), (0.980, 0.800, 0.082)
INK = (0.051, 0.066, 0.090)
LAST = 260

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start, scene.frame_end = 0, LAST
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPTIX"
scene.cycles.use_adaptive_sampling = True
scene.cycles.device = "GPU"
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 1.0
scene.view_settings.view_transform = "Filmic" if "Filmic" in [i.name for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "AgX"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type != "CPU"

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (*INK, 1.0)
bg.inputs[1].default_value = 0.6


def mat(name, color, rough=0.35, metal=0.0, emit=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1.0)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if "Specular IOR Level" in p.inputs:
        p.inputs["Specular IOR Level"].default_value = spec
    if emit:
        p.inputs["Emission Color"].default_value = (*color, 1.0)
        p.inputs["Emission Strength"].default_value = emit
    return m


def emission_key(m, frame, strength):
    p = m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    p.default_value = strength
    p.keyframe_insert("default_value", frame=frame)


def hide_key(o, frame, hidden):
    o.hide_render = hidden
    o.hide_viewport = hidden
    o.keyframe_insert("hide_render", frame=frame)
    o.keyframe_insert("hide_viewport", frame=frame)


def constant(o):
    if o.animation_data and o.animation_data.action:
        for fc in o.animation_data.action.fcurves:
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"


bpy.ops.mesh.primitive_plane_add(size=90, location=(0, 0, 0))
floor = bpy.context.object
floor.name = "Floor"
floor.data.materials.append(mat("floor", (0.02, 0.022, 0.03), rough=0.18, metal=0.15, spec=0.7))
bpy.ops.rigidbody.object_add(type="PASSIVE")
floor.rigid_body.friction = 0.8
floor.rigid_body.restitution = 0.15
floor.rigid_body.collision_shape = "BOX"
grid = mat("grid", (0.35, 0.25, 0.45), rough=0.6, emit=0.6)
for i in range(-14, 15):
    for axis in (0, 1):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(i * 2 if axis == 0 else 0, 0 if axis == 0 else i * 2, 0.002))
        o = bpy.context.object
        o.scale = (0.006, 46, 1) if axis == 0 else (46, 0.006, 1)
        o.data.materials.append(grid)
        o.visible_shadow = False

# ---------------------------------------------------------------- the boss
parts = []          # everything that breaks on the last hit: (object, kind)
CARAPACE = mat("carapace", (0.10, 0.06, 0.16), rough=0.32, metal=0.55, spec=0.8)
VENT = mat("vent", ORANGE, rough=0.4, emit=2.2)
LEG = mat("leg", (0.12, 0.08, 0.18), rough=0.3, metal=0.7)


def plate(loc, normal, size, m):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
    o = bpy.context.object
    o.rotation_euler = Vector(normal).to_track_quat("Z", "Y").to_euler()
    o.scale = (1, 1, 0.55)
    o.data.materials.append(m)
    bpy.ops.object.modifier_add(type="BEVEL")
    o.modifiers[-1].width = 0.02
    o.modifiers[-1].segments = 2
    parts.append((o, "plate"))
    return o


def shell(centre, radii, n, size, vents=0.12):
    """cubes laid on an ellipsoid surface, a Fibonacci sphere of them"""
    cx, cy, cz = centre
    rx, ry, rz = radii
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        th = golden * i
        nx, ny, nz = r * math.cos(th), r * math.sin(th), z
        plate((cx + rx * nx, cy + ry * ny, cz + rz * nz), (nx / rx, ny / ry, nz / rz), size,
              VENT if random.random() < vents else CARAPACE)


CORE = (2.9, 0.0, 1.95)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.35, location=CORE, segments=48, ring_count=24)
core = bpy.context.object
core.name = "Core"
core_mat = mat("core", ORANGE, rough=0.5, emit=5.0)
core.data.materials.append(core_mat)
bpy.ops.object.shade_smooth()
shell((3.7, 0.0, 1.95), (2.0, 1.55, 1.4), 240, 0.34)                   # abdomen
shell((1.9, 0.0, 1.95), (1.05, 1.05, 1.0), 110, 0.30)                   # thorax
shell((0.85, 0.0, 1.75), (0.78, 0.72, 0.72), 80, 0.26, vents=0.06)      # head
EYE = mat("eye", PINK, rough=0.3, emit=7.0)
for sy in (-1, 1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.17, location=(0.2, sy * 0.32, 1.95), segments=24, ring_count=12)
    e = bpy.context.object
    e.data.materials.append(EYE)
    bpy.ops.object.shade_smooth()
    parts.append((e, "eye"))
    bpy.ops.mesh.primitive_cone_add(radius1=0.13, radius2=0.02, depth=0.95, location=(-0.25, sy * 0.42, 1.55))
    mand = bpy.context.object
    mand.data.materials.append(LEG)
    mand.rotation_euler = Euler((0, math.radians(-100), sy * math.radians(-25)))
    for f in range(0, LAST + 1, 12):                                     # the mandibles chew, slowly
        mand.rotation_euler.z = sy * math.radians(-25 + 12 * math.sin(f / 12 * math.pi))
        mand.keyframe_insert("rotation_euler", frame=f)
    parts.append((mand, "mand"))


def cyl(a, b, r, m):
    a, b = Vector(a), Vector(b)
    d = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d.length, location=(a + b) / 2, vertices=14)
    o = bpy.context.object
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(m)
    bpy.ops.object.shade_smooth()
    return o


def empty(loc, name):
    bpy.ops.object.empty_add(location=loc)
    o = bpy.context.object
    o.name = name
    return o


def parent_keep(child, parent):
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


legs = {}
for i, hx in enumerate((1.5, 2.6, 3.7)):
    for sy in (-1, 1):
        hip, knee, foot = (hx, sy * 0.95, 1.6), (hx + 0.15, sy * 2.1, 2.55), (hx + 0.35, sy * 3.1, 0.0)
        e_hip = empty(hip, f"hip{i}{sy}")
        femur = cyl(hip, knee, 0.12, LEG)
        parent_keep(femur, e_hip)
        e_knee = empty(knee, f"knee{i}{sy}")
        parent_keep(e_knee, e_hip)
        tibia = cyl(knee, foot, 0.085, LEG)
        parent_keep(tibia, e_knee)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=knee, segments=16, ring_count=8)
        kn = bpy.context.object
        kn.data.materials.append(LEG)
        parent_keep(kn, e_hip)
        legs[(i, sy)] = (e_hip, e_knee)
        for o in (femur, tibia, kn):
            parts.append((o, "leg"))

# the slam: the front leg on the camera's side rears up and comes down where the knight stood
e_hip, e_knee = legs[(0, -1)]
for f, (ex, ez, kx) in {T_JUMP - 4: (0, 0, 0), T_JUMP + 6: (-62, -58, 20), T_SLAM - 2: (-45, -52, 5), T_SLAM: (18, -50, -32),
                        T_SLAM + 6: (18, -50, -32), T_SLAM + 18: (0, 0, 0)}.items():
    e_hip.rotation_euler = Euler((math.radians(ex), 0, math.radians(ez)))
    e_hip.keyframe_insert("rotation_euler", frame=f)
    e_knee.rotation_euler = Euler((math.radians(kx), 0, 0))
    e_knee.keyframe_insert("rotation_euler", frame=f)
bpy.ops.object.empty_add(location=(0, 0, 0))
root = bpy.context.object
root.name = "BossRoot"
for o in [o for o, _ in parts] + [core] + [v[0] for v in legs.values()]:
    if o.parent is None:
        parent_keep(o, root)

# ---------------------------------------------------------------- the knight
bpy.ops.import_scene.gltf(filepath=KNIGHT)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
rig.name = "Knight"
keep = {"Knight_Body", "Knight_Head", "Knight_Helmet", "Knight_Cape", "Knight_ArmLeft", "Knight_ArmRight",
        "Knight_LegLeft", "Knight_LegRight", "2H_Sword"}
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.parent == rig and o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
sword = bpy.data.objects["2H_Sword"]
rig.scale = (1.95 / rig.dimensions.z,) * 3
rig.rotation_euler = (0, 0, math.radians(180))            # the rig faces -X at rest; the boss is at +X
for o in bpy.data.objects:
    if o.type == "MESH" and o.parent == rig:
        for slot in o.material_slots:
            p = slot.material.node_tree.nodes.get("Principled BSDF")
            if p:
                p.inputs["Roughness"].default_value = 0.55
# the blade burns while the combo is on
sword_mat = sword.material_slots[0].material.copy()
sword.material_slots[0].material = sword_mat
sp = sword_mat.node_tree.nodes["Principled BSDF"]
sp.inputs["Emission Color"].default_value = (1.0, 0.85, 0.45, 1.0)
for f, em in ((T_RUN, 0.0), (T_SLICE, 2.2), (T_SPIN + 44, 2.2), (T_SPIN + 56, 0.0)):
    emission_key(sword_mat, f, em)

# the importer leaves every clip as an NLA track and one as the active action, which would play over
# anything we add: clear all of it and choreograph on one fresh track
rig.animation_data_create()
rig.animation_data.action = None
for t in list(rig.animation_data.nla_tracks):
    rig.animation_data.nla_tracks.remove(t)
track = rig.animation_data.nla_tracks.new()
track.name = "film"
acts = bpy.data.actions


def strip(name, start, action_name, end=None, repeat=1.0):
    a = acts[action_name]
    s = track.strips.new(name, start, a)
    s.action_frame_start, s.action_frame_end = a.frame_range[0], a.frame_range[1]
    if repeat != 1.0:
        s.repeat = repeat
    if end is not None:
        s.frame_end = end
    s.blend_type = "REPLACE"
    s.extrapolation = "HOLD_FORWARD"
    return s


strip("idle", 0, "Idle", end=T_JUMP)
strip("jump", T_JUMP, "Jump_Full_Short", end=T_RUN)
strip("run", T_RUN, "Running_A", end=T_SLICE, repeat=(T_SLICE - T_RUN) / 19)
strip("slice", T_SLICE, "2H_Melee_Attack_Slice", end=T_CHOP)
strip("chop", T_CHOP, "2H_Melee_Attack_Chop", end=T_SPIN)
spin_strip = strip("spin", T_SPIN, "2H_Melee_Attack_Spin")
for f, (x, z) in {0: (-1.7, 0), T_JUMP: (-1.7, 0), T_JUMP + 10: (-2.4, 0.95), T_JUMP + 20: (-3.0, 0.0),
                  T_RUN: (-3.0, 0), T_SLICE: (-0.75, 0), LAST: (-0.75, 0)}.items():
    rig.location = (x, 0.1, z)
    rig.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- lights and camera
def light(name, kind, loc, color, energy, size=2.0, aim=(0.8, 0, 1.4)):
    bpy.ops.object.light_add(type=kind, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.color = color
    o.data.energy = energy
    if kind == "AREA":
        o.data.size = size
    d = Vector(aim) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if hasattr(o, "visible_glossy"):
        o.visible_glossy = False
    return o


light("Key", "AREA", (-5.0, -7.0, 7.0), (1.0, 0.93, 0.85), 1100, size=3.5)
light("RimPink", "AREA", (6.5, 5.0, 4.0), PINK, 900, size=3.0)
light("RimOrange", "AREA", (-6.0, 5.0, 3.5), ORANGE, 600, size=3.0)
light("Fill", "AREA", (2.0, -8.0, 2.5), (0.6, 0.55, 0.8), 160, size=5.0)

bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.lens = 36
cam.data.sensor_width = 36
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 2.8
cam.data.dof.focus_distance = 12.0
cam.data.clip_end = 200


def look_at(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- where the blade goes, frame by frame
bpy.context.view_layer.update()
hand_bone = rig.pose.bones["handslot.r"] if "handslot.r" in rig.pose.bones else None
blade = {}                                  # frame -> (hand, tip) in world space
depsgraph = bpy.context.evaluated_depsgraph_get()
for f in range(T_RUN, SWINGS[-1][2] + 1):
    scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ev = sword.evaluated_get(depsgraph)
    me = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    hand = (rig.matrix_world @ hand_bone.head) if hand_bone else min(pts, key=lambda p: (p - rig.matrix_world.translation).length)
    tip = max(pts, key=lambda p: (p - hand).length)
    blade[f] = (hand.copy(), tip.copy())
hits = []
for name, a, b in SWINGS:
    f_best = max(range(a + 2, b - 1), key=lambda f: blade[f][1].x)
    hits.append((name, f_best, blade[f_best][1].copy()))
    print(f"{name}: blade tip reaches x={blade[f_best][1].x:.2f} at frame {f_best}")
T_HIT = hits[-1][1]
T_CHEER = T_HIT + 30
END = T_HIT + 84
spin_strip.frame_end = T_CHEER
strip("cheer", T_CHEER, "Cheer")

# the slash ribbons: one thin quad per frame between consecutive blade positions, alive for six frames
TRAIL = []
for name, a, b in SWINGS:
    for f in range(a + 1, b):
        h0, t0 = blade[f - 1]
        h1, t1 = blade[f]
        me = bpy.data.meshes.new(f"trail_{f}")
        me.from_pydata([h0, t0, t1, h1], [], [(0, 1, 2, 3)])
        o = bpy.data.objects.new(f"trail_{f}", me)
        scene.collection.objects.link(o)
        m = mat(f"trail_{f}", YELLOW, rough=1.0, emit=0.0)
        m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (1.0, 0.72 + 0.28 * random.random(), 0.25, 1.0)
        m.blend_method = "BLEND"
        m.show_transparent_back = False
        o.data.materials.append(m)
        o.visible_shadow = False
        hide_key(o, 0, True)
        hide_key(o, f, False)
        hide_key(o, f + 7, True)
        alpha = m.node_tree.nodes["Principled BSDF"].inputs["Alpha"]
        for ff, (em, al) in ((f, (10.0, 0.75)), (f + 6, (0.0, 0.0))):      # a ribbon that thins and cools
            emission_key(m, ff, em)
            alpha.default_value = al
            alpha.keyframe_insert("default_value", frame=ff)
        constant(o)
        TRAIL.append(o)

# the hits: a flash, a spray of sparks, the vents blaze, the boss and the camera shake
SPARK = mat("spark", (1.0, 0.8, 0.3), rough=0.6, emit=16.0)
FLASH = mat("flash", (1.0, 0.95, 0.8), rough=1.0, emit=0.0)
sparks = []
for name, f, p in hits:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=p, segments=24, ring_count=12)
    fl = bpy.context.object
    fl.data.materials.append(FLASH.copy())
    bpy.ops.object.shade_smooth()
    fm = fl.material_slots[0].material
    hide_key(fl, 0, True)
    hide_key(fl, f, False)
    hide_key(fl, f + 5, True)
    for ff, (sc, em) in {f: (0.12, 60.0), f + 2: (0.9, 30.0), f + 4: (1.6, 0.0)}.items():
        fl.scale = (sc,) * 3
        fl.keyframe_insert("scale", frame=ff)
        emission_key(fm, ff, em)
    for i in range(34):
        d = Vector((random.uniform(0.2, 1.0), random.uniform(-1, 1), random.uniform(-0.2, 1.2))).normalized() * random.uniform(0.18, 0.42)
        bpy.ops.mesh.primitive_cube_add(size=random.uniform(0.05, 0.1), location=p - d)
        s = bpy.context.object
        s.data.materials.append(SPARK)
        s.rotation_euler = Euler((random.random() * 3, random.random() * 3, random.random() * 3))
        s.keyframe_insert("location", frame=0)
        s.keyframe_insert("location", frame=f - 1)
        s.location = p
        s.keyframe_insert("location", frame=f)
        for ff, hidden in ((0, True), (f - 1, False), (f + 26, True)):      # render visibility only: a
            s.hide_render = hidden                                           # viewport-hidden body would be
            s.keyframe_insert("hide_render", frame=ff)                       # dropped from the simulation
        sparks.append((s, f))
    emission_key(VENT, f - 1, 2.2)
    emission_key(VENT, f, 16.0)
    emission_key(VENT, f + 4, 2.2)
    for ff in range(f, f + 5):
        root.location = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))) * 0.06 * (1 - (ff - f) / 5)
        root.keyframe_insert("location", frame=ff)
    root.location = (0, 0, 0)
    root.keyframe_insert("location", frame=f + 5)
for f in range(0, T_HIT + 1, 8):                                          # and it breathes
    if not any(h - 2 <= f <= h + 6 for _, h, _ in hits):
        root.location = (0, 0, 0.06 * math.sin(f / 16 * math.pi))
        root.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- rigid bodies
for o, kind in parts:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.rigidbody.object_add(type="ACTIVE")
    o.select_set(False)
    rb = o.rigid_body
    rb.mass = {"plate": 0.5, "eye": 0.3, "mand": 0.6, "leg": 1.2}[kind]
    rb.friction = 0.6
    rb.restitution = 0.3
    rb.collision_shape = "BOX" if kind == "plate" else "CONVEX_HULL"
    rb.collision_margin = 0.002
    rb.kinematic = True
    rb.keyframe_insert("kinematic", frame=T_HIT)
    rb.kinematic = False
    rb.keyframe_insert("kinematic", frame=T_HIT + 1)
for s, f in sparks:
    bpy.context.view_layer.objects.active = s
    s.select_set(True)
    bpy.ops.rigidbody.object_add(type="ACTIVE")
    s.select_set(False)
    rb = s.rigid_body
    rb.mass = 0.05
    rb.restitution = 0.5
    rb.collision_shape = "BOX"
    rb.kinematic = True
    rb.keyframe_insert("kinematic", frame=f)
    rb.kinematic = False
    rb.keyframe_insert("kinematic", frame=f + 1)          # keeps the velocity of the two animated frames
scene.rigidbody_world.substeps_per_frame = 10
scene.rigidbody_world.solver_iterations = 20
scene.rigidbody_world.point_cache.frame_start = 0
scene.rigidbody_world.point_cache.frame_end = LAST
scene.rigidbody_world.time_scale = 0.5

bpy.ops.object.effector_add(type="FORCE", location=CORE)
blast = bpy.context.object
ff_ = blast.field
ff_.shape = "POINT"
ff_.falloff_power = 0.8
ff_.use_max_distance = True
ff_.distance_max = 12.0
for f, st in ((T_HIT, 0.0), (T_HIT + 1, 2800.0), (T_HIT + 3, 2800.0), (T_HIT + 4, 0.0)):
    ff_.strength = st
    ff_.keyframe_insert("strength", frame=f)
constant(blast)
bpy.ops.object.effector_add(type="TURBULENCE", location=CORE)
turb = bpy.context.object
turb.field.size = 2.0
for f, st in ((T_HIT, 0.0), (T_HIT + 1, 25.0)):
    turb.field.strength = st
    turb.field.keyframe_insert("strength", frame=f)

for f, (sc, em) in {T_HIT: (1.0, 5.0), T_HIT + 3: (1.5, 40.0), T_HIT + 8: (1.9, 14.0), T_HIT + 18: (0.05, 0.0)}.items():
    core.scale = (sc,) * 3
    core.keyframe_insert("scale", frame=f)
    emission_key(core_mat, f, em)
for f, em in ((T_HIT, 7.0), (T_HIT + 6, 0.0)):
    emission_key(EYE, f, em)

# the shockwave ring at the slam
bpy.ops.mesh.primitive_torus_add(location=(-1.45, -1.0, 0.03), major_radius=0.3, minor_radius=0.05, major_segments=64, minor_segments=8)
ring = bpy.context.object
ring_mat = mat("ring", ORANGE, rough=0.5, emit=10.0)
ring.data.materials.append(ring_mat)
for f, sc in ((T_SLAM - 1, 0.01), (T_SLAM, 1.0), (T_SLAM + 10, 9.0), (T_SLAM + 11, 0.01)):
    ring.scale = (sc, sc, 1.0 if sc > 0.5 else sc)
    ring.keyframe_insert("scale", frame=f)
emission_key(ring_mat, T_SLAM, 10.0)
emission_key(ring_mat, T_SLAM + 10, 0.0)

# the camera: a slow push in, shaken by the slam and every hit, drifting while the boss comes apart
def shake(f, at, amp, length=6):
    if at <= f < at + length:
        k = 1 - (f - at) / length
        return Vector((random.uniform(-1, 1), random.uniform(-1, 1) * 0.3, random.uniform(-1, 1))) * amp * k
    return Vector((0, 0, 0))


for f in range(0, LAST + 1):
    t = min(f / T_HIT, 1.0)
    e = t * t * (3 - 2 * t)
    loc = Vector((-0.6 + 0.9 * e, -13.2 + 1.6 * e, 3.1 - 0.2 * e))
    if f > T_HIT:
        loc += Vector((0.35, 0.0, 0.25)) * min((f - T_HIT) / 50, 1.0)
    loc += shake(f, T_SLAM, 0.09)
    for _, h, _ in hits:
        loc += shake(f, h, 0.07 if h != T_HIT else 0.14)
    cam.location = loc
    look_at(cam, (1.0 + 0.4 * e, 0.0, 1.7))
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)

scene.use_nodes = True
nt = scene.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
rl = nt.nodes.new("CompositorNodeRLayers")
glare = nt.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.threshold = 1.05
glare.mix = -0.25
glare.size = 8
comp = nt.nodes.new("CompositorNodeComposite")
nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
nt.links.new(glare.outputs["Image"], comp.inputs["Image"])

# where the hits land on screen, for the HUD
hud = {"hits": [], "t_hit": T_HIT, "end": END, "t_slam": T_SLAM}
for name, f, p in hits:
    scene.frame_set(f)
    v = world_to_camera_view(scene, cam, p)
    hud["hits"].append({"name": name, "frame": f, "x": round(v.x * W), "y": round((1 - v.y) * H)})
with open(os.path.join(OUT, "boss_hits.json"), "w") as fh:
    json.dump(hud, fh)
print("hits:", hud)

# ---------------------------------------------------------------- bake and render
bpy.context.view_layer.update()
bpy.ops.ptcache.bake_all(bake=True)
frames = ONLY or list(range(0, END + 1, STEP))
for f in frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, f"F_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered {f}", flush=True)
print("done", frames[0], frames[-1])
