"""Render BOSS: the arena's knight versus the PRODUCTION BUG. Blender (bpy, Cycles, OptiX).

The boss is a giant beetle: a glowing core wrapped in a few hundred armour plates (cubes laid on
ellipsoids), six cylinder legs, pink eyes, mandibles. It rears a front leg and slams the floor
where the knight stood (shockwave, camera shake); the knight jumps clear, runs in and lands a
two-handed slice. On the hit every plate becomes a rigid body, the core flashes and the boss comes
apart in slow motion. The knight cheers; the film fades to black and loops.

Timeline (24 fps):  0-16 idle | 16-44 slam + jump | 44-60 run in | 60-86 slice, hit at 74 |
                    74-132 the boss breaks apart, cheer | 132-140 fade

Usage:
    py -3.11 scripts/render_boss.py -- <out_dir>
Env:
    BOSS_W (1000)  BOSS_H (420)  BOSS_SAMPLES (96)  BOSS_ONLY ("0,32,74")  BOSS_STEP (2)  BOSS_END (140)
"""
from __future__ import annotations

import math
import os
import random
import sys

import bpy
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "render_boss")
W = int(os.environ.get("BOSS_W", "1000"))
H = int(os.environ.get("BOSS_H", "420"))
SAMPLES = int(os.environ.get("BOSS_SAMPLES", "96"))
STEP = int(os.environ.get("BOSS_STEP", "2"))
END = int(os.environ.get("BOSS_END", "140"))
ONLY = [int(x) for x in os.environ.get("BOSS_ONLY", "").split(",") if x.strip()]
KNIGHT = os.path.normpath(os.path.join(HERE, "..", "..", "site", "arena", "assets", "kaykit", "Knight.glb"))
os.makedirs(OUT, exist_ok=True)
random.seed(7)

T_JUMP, T_SLAM, T_RUN, T_SLICE, T_HIT, T_CHEER = 16, 32, 44, 60, 74, 92
PINK, ORANGE, YELLOW = (0.925, 0.282, 0.600), (0.976, 0.451, 0.086), (0.980, 0.800, 0.082)
INK = (0.051, 0.066, 0.090)

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start, scene.frame_end = 0, END + 10
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
parts = []          # everything that breaks on the hit: (object, kind)
CARAPACE = mat("carapace", (0.10, 0.06, 0.16), rough=0.32, metal=0.55, spec=0.8)
VENT = mat("vent", ORANGE, rough=0.4, emit=2.2)
VENT_PINK = mat("ventpink", PINK, rough=0.4, emit=2.2)
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


def shell(centre, radii, n, size, vents=0.12, pink=False):
    """cubes laid on an ellipsoid surface, a Fibonacci sphere of them"""
    cx, cy, cz = centre
    rx, ry, rz = radii
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        th = golden * i
        nx, ny, nz = r * math.cos(th), r * math.sin(th), z
        loc = (cx + rx * nx, cy + ry * ny, cz + rz * nz)
        m = CARAPACE
        if random.random() < vents:
            m = VENT_PINK if pink else VENT
        plate(loc, (nx / rx, ny / ry, nz / rz), size, m)


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
    # the mandibles chew, slowly
    for f in range(0, END + 1, 12):
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
        hip = (hx, sy * 0.95, 1.6)
        knee = (hx + 0.15, sy * 2.1, 2.55)
        foot = (hx + 0.35, sy * 3.1, 0.0)
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
        legs[(i, sy)] = (e_hip, e_knee, femur, tibia, kn)
        for o in (femur, tibia, kn):
            parts.append((o, "leg"))

# the slam: the front leg on the camera's side rears up and comes down where the knight stood
e_hip, e_knee = legs[(0, -1)][:2]
for f, (ex, ez, kx) in {T_JUMP: (0, 0, 0), T_JUMP + 9: (-62, -58, 20), T_SLAM - 2: (-45, -52, 5), T_SLAM: (18, -50, -32),
                        T_SLAM + 6: (18, -50, -32), T_SLAM + 20: (0, 0, 0)}.items():
    e_hip.rotation_euler = Euler((math.radians(ex), 0, math.radians(ez)))
    e_hip.keyframe_insert("rotation_euler", frame=f)
    e_knee.rotation_euler = Euler((math.radians(kx), 0, 0))
    e_knee.keyframe_insert("rotation_euler", frame=f)
# the whole boss breathes
boss_parts = [o for o, _ in parts] + [core] + [v[0] for v in legs.values()]
bpy.ops.object.empty_add(location=(0, 0, 0))
root = bpy.context.object
root.name = "BossRoot"
for o in boss_parts:
    if o.parent is None:
        parent_keep(o, root)
for f in range(0, T_HIT + 1, 8):
    root.location.z = 0.06 * math.sin(f / 16 * math.pi)
    root.rotation_euler = Euler((0, math.radians(0.8 * math.sin(f / 24 * math.pi)), 0))
    root.keyframe_insert("location", frame=f)
    root.keyframe_insert("rotation_euler", frame=f)

# rigid bodies: every plate, eye, mandible and leg segment is held until the hit, then let go
for o, kind in parts:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.rigidbody.object_add(type="ACTIVE")
    o.select_set(False)
    rb = o.rigid_body
    rb.mass = {"plate": 0.5, "eye": 0.3, "mand": 0.6, "leg": 1.2}[kind]
    rb.friction = 0.6
    rb.restitution = 0.3
    rb.collision_shape = "BOX" if kind in ("plate",) else "CONVEX_HULL"
    rb.collision_margin = 0.002
    rb.kinematic = True
    rb.keyframe_insert("kinematic", frame=T_HIT)
    rb.kinematic = False
    rb.keyframe_insert("kinematic", frame=T_HIT + 1)
scene.rigidbody_world.substeps_per_frame = 10
scene.rigidbody_world.solver_iterations = 20
scene.rigidbody_world.point_cache.frame_start = 0
scene.rigidbody_world.point_cache.frame_end = END + 10
scene.rigidbody_world.time_scale = 0.45

bpy.ops.object.effector_add(type="FORCE", location=CORE)
blast = bpy.context.object
ff = blast.field
ff.shape = "POINT"
ff.falloff_power = 0.8
ff.use_max_distance = True
ff.distance_max = 12.0
for f, st in ((T_HIT, 0.0), (T_HIT + 1, 2800.0), (T_HIT + 3, 2800.0), (T_HIT + 4, 0.0)):
    ff.strength = st
    ff.keyframe_insert("strength", frame=f)
for fc in blast.animation_data.action.fcurves:
    for k in fc.keyframe_points:
        k.interpolation = "CONSTANT"
bpy.ops.object.effector_add(type="TURBULENCE", location=CORE)
turb = bpy.context.object
turb.field.size = 2.0
for f, st in ((T_HIT, 0.0), (T_HIT + 1, 25.0)):
    turb.field.strength = st
    turb.field.keyframe_insert("strength", frame=f)

# the core: flash, swell, and go out
for f, (sc, em) in {T_HIT: (1.0, 5.0), T_HIT + 3: (1.5, 40.0), T_HIT + 8: (1.9, 14.0), T_HIT + 18: (0.05, 0.0)}.items():
    core.scale = (sc,) * 3
    core.keyframe_insert("scale", frame=f)
    emission_key(core_mat, f, em)
# the eyes go dark
for f, em in ((T_HIT, 7.0), (T_HIT + 6, 0.0)):
    emission_key(EYE, f, em)

# the shockwave ring at the slam
foot_world = (-1.45, -1.0, 0.03)
bpy.ops.mesh.primitive_torus_add(location=foot_world, major_radius=0.3, minor_radius=0.05, major_segments=64, minor_segments=8)
ring = bpy.context.object
ring_mat = mat("ring", ORANGE, rough=0.5, emit=10.0)
ring.data.materials.append(ring_mat)
ring.scale = (0.01,) * 3
ring.keyframe_insert("scale", frame=T_SLAM - 1)
ring.scale = (1.0, 1.0, 1.0)
ring.keyframe_insert("scale", frame=T_SLAM)
ring.scale = (9.0, 9.0, 1.0)
ring.keyframe_insert("scale", frame=T_SLAM + 10)
ring.scale = (0.01,) * 3
ring.keyframe_insert("scale", frame=T_SLAM + 11)
emission_key(ring_mat, T_SLAM, 10.0)
emission_key(ring_mat, T_SLAM + 10, 0.0)

# ---------------------------------------------------------------- the knight
bpy.ops.import_scene.gltf(filepath=KNIGHT)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
rig.name = "Knight"
keep = {"Knight_Body", "Knight_Head", "Knight_Helmet", "Knight_Cape", "Knight_ArmLeft", "Knight_ArmRight",
        "Knight_LegLeft", "Knight_LegRight", "2H_Sword"}
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.parent == rig and o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
rig.scale = (1.95 / rig.dimensions.z,) * 3
rig.rotation_euler = (0, 0, math.radians(90))
for o in bpy.data.objects:
    if o.type == "MESH" and o.parent == rig:
        for slot in o.material_slots:
            p = slot.material.node_tree.nodes.get("Principled BSDF")
            if p:
                p.inputs["Roughness"].default_value = 0.55
rig.animation_data_create()
track = rig.animation_data.nla_tracks.new()
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
strip("slice", T_SLICE, "2H_Melee_Attack_Slice")
strip("cheer", T_CHEER, "Cheer")
# where the knight is: standing close, thrown back by the jump, running in, planted for the slice
for f, (x, z) in {0: (-1.7, 0), T_JUMP: (-1.7, 0), T_JUMP + 10: (-2.4, 0.95), T_JUMP + 20: (-3.0, 0.0),
                  T_RUN: (-3.0, 0), T_SLICE: (-1.05, 0), END + 10: (-1.05, 0)}.items():
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
cam.data.dof.focus_distance = 12.5
cam.data.clip_end = 200


def look_at(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def shake(f, at, amp, length=7):
    if at <= f < at + length:
        k = 1 - (f - at) / length
        return Vector((random.uniform(-1, 1), random.uniform(-1, 1) * 0.3, random.uniform(-1, 1))) * amp * k
    return Vector((0, 0, 0))


for f in range(0, END + 11):
    t = min(f / T_HIT, 1.0)
    e = t * t * (3 - 2 * t)
    loc = Vector((-0.6 + 0.9 * e, -13.2 + 1.4 * e, 3.1 - 0.2 * e))
    if f > T_HIT:                                       # a slow drift while the boss comes apart
        loc += Vector((0.35, 0.0, 0.25)) * min((f - T_HIT) / 50, 1.0)
    loc += shake(f, T_SLAM, 0.09) + shake(f, T_HIT, 0.13)
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
glare.mix = -0.3
glare.size = 8
comp = nt.nodes.new("CompositorNodeComposite")
nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
nt.links.new(glare.outputs["Image"], comp.inputs["Image"])

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
