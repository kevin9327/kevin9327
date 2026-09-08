"""Render THE FIX: the arena's knight cuts a block-letter BUG in half, the letters explode as real
rigid bodies in slow motion, and the debris rewinds itself into FIX. Blender (bpy, Cycles, OptiX).

Three render sets share one scene, one camera path and one knight timeline; assemble_smash.py
sequences them (A forward, cross-fade, B in reverse, hold, then a fast rewind of everything):
    A  WORD=BUG  frames 0..58 (even)   idle, the slice, the blast, the debris
    B  WORD=FIX  frames 23..83 (odd)   a gentler blast on FIX; played backwards it re-assembles the word
    H  WORD=FIX  frames 106..146 (even) FIX intact, the knight cheering

Usage:
    py -3.11 scripts/render_smash.py -- <out_dir>
Env:
    SMASH_MODE (A|B|H)  SMASH_W (1000)  SMASH_H (420)  SMASH_SAMPLES (96)  SMASH_ONLY ("0,30,44")  SMASH_STEP (2)
"""
from __future__ import annotations

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pixelfont import rows_of  # noqa: E402

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "render_smash")
MODE = os.environ.get("SMASH_MODE", "A").upper()
W = int(os.environ.get("SMASH_W", "1000"))
H = int(os.environ.get("SMASH_H", "420"))
SAMPLES = int(os.environ.get("SMASH_SAMPLES", "96"))
STEP = int(os.environ.get("SMASH_STEP", "2"))
ONLY = [int(x) for x in os.environ.get("SMASH_ONLY", "").split(",") if x.strip()]
KNIGHT = os.path.normpath(os.path.join(HERE, "..", "..", "site", "arena", "assets", "kaykit", "Knight.glb"))
os.makedirs(OUT, exist_ok=True)

WORD = {"A": "BUG", "B": "FIX", "H": "FIX"}[MODE]
FRAMES = {"A": (0, 58), "B": (23, 83), "H": (106, 146)}[MODE]
T_ATTACK, T_HIT, T_CAM_STOP, T_CHEER = 16, 27, 48, 106

PINK, ORANGE, YELLOW = (0.925, 0.282, 0.600), (0.976, 0.451, 0.086), (0.980, 0.800, 0.082)
INK = (0.051, 0.066, 0.090)
CUBE, PITCH = 0.28, 0.30

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start, scene.frame_end = 0, 200
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPTIX"
scene.cycles.use_adaptive_sampling = True
scene.cycles.device = "GPU"
scene.render.use_motion_blur = True
scene.render.motion_blur_shutter = 1.1
scene.view_settings.view_transform = "Filmic" if "Filmic" in [i.name for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "AgX"
scene.view_settings.look = "None"
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
bg.inputs[1].default_value = 0.65


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


# floor: dark, glossy, so the letters reflect
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
floor = bpy.context.object
floor.name = "Floor"
floor.data.materials.append(mat("floor", (0.02, 0.022, 0.03), rough=0.18, metal=0.15, spec=0.7))
bpy.ops.rigidbody.object_add(type="PASSIVE")
floor.rigid_body.friction = 0.8
floor.rigid_body.restitution = 0.15
floor.rigid_body.collision_shape = "BOX"

# a faint grid on the floor, like the arena's, from thin emissive strips
grid = mat("grid", (0.35, 0.25, 0.45), rough=0.6, emit=0.6)
for i in range(-12, 13):
    for axis in (0, 1):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(i * 2 if axis == 0 else 0, 0 if axis == 0 else i * 2, 0.002))
        o = bpy.context.object
        o.scale = (0.006, 40, 1) if axis == 0 else (40, 0.006, 1)
        o.data.materials.append(grid)
        o.cycles.is_shadow_catcher = False
        o.visible_shadow = False

# ---------------------------------------------------------------- the word, as rigid-body cubes
letter_colors = [PINK, ORANGE, YELLOW]
cols = len(WORD) * 6 - 1
x0 = 1.15 - cols * PITCH / 2
cubes = []
mats = [mat(f"letter{i}", c, rough=0.28, emit=1.6) for i, c in enumerate(letter_colors)]
for li, ch in enumerate(WORD):
    rows = rows_of(ch)
    for r, row in enumerate(rows):
        for c, bit in enumerate(row):
            if bit != "#":
                continue
            x = x0 + (li * 6 + c) * PITCH
            z = (6 - r) * PITCH + CUBE / 2 + 0.01
            bpy.ops.mesh.primitive_cube_add(size=CUBE, location=(x, 0.0, z))
            o = bpy.context.object
            o.name = f"cube_{li}_{r}_{c}"
            o.data.materials.append(mats[li])
            bpy.ops.object.modifier_add(type="BEVEL")
            o.modifiers[-1].width = 0.02
            o.modifiers[-1].segments = 2
            bpy.ops.rigidbody.object_add(type="ACTIVE")
            rb = o.rigid_body
            rb.mass = 0.4
            rb.friction = 0.6
            rb.restitution = 0.25
            rb.collision_shape = "BOX"
            rb.collision_margin = 0.002
            # hold the letter shape until the sword lands, then let it go
            rb.kinematic = True
            rb.keyframe_insert("kinematic", frame=T_HIT - 1)
            if MODE != "H":
                rb.kinematic = False
                rb.keyframe_insert("kinematic", frame=T_HIT)
            cubes.append(o)

scene.rigidbody_world.substeps_per_frame = 12
scene.rigidbody_world.solver_iterations = 24
scene.rigidbody_world.point_cache.frame_start = 0
scene.rigidbody_world.point_cache.frame_end = 200
# slow motion: the cubes are held in place until the sword lands, so only the blast is slowed
scene.rigidbody_world.time_scale = 0.5

# the blast: a radial force from where the blade lands, for two frames
bpy.ops.object.effector_add(type="FORCE", location=(-0.7, -0.1, 0.55))
blast = bpy.context.object
blast.name = "Blast"
ff = blast.field
ff.shape = "POINT"
ff.falloff_power = 0.9
ff.use_max_distance = True
ff.distance_max = 9.0
ff.strength = 0.0
ff.keyframe_insert("strength", frame=T_HIT - 1)
ff.strength = {"A": 3400.0, "B": 1800.0, "H": 0.0}[MODE]   # FIX keeps its debris in frame, so the rewind has something to gather
ff.keyframe_insert("strength", frame=T_HIT)
ff.keyframe_insert("strength", frame=T_HIT + 2)
ff.strength = 0.0
ff.keyframe_insert("strength", frame=T_HIT + 3)
for fc in blast.animation_data.action.fcurves:
    for k in fc.keyframe_points:
        k.interpolation = "CONSTANT"
bpy.ops.object.effector_add(type="TURBULENCE", location=(1.2, 0, 1.2))
turb = bpy.context.object
turb.field.strength = 0.0
turb.field.keyframe_insert("strength", frame=T_HIT)
turb.field.strength = 20.0 if MODE != "H" else 0.0
turb.field.keyframe_insert("strength", frame=T_HIT + 1)
turb.field.size = 1.6

# ---------------------------------------------------------------- the knight
bpy.ops.import_scene.gltf(filepath=KNIGHT)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
rig.name = "Knight"
keep = {"Knight_Body", "Knight_Head", "Knight_Helmet", "Knight_Cape", "Knight_ArmLeft", "Knight_ArmRight",
        "Knight_LegLeft", "Knight_LegRight", "2H_Sword"}
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.parent == rig and o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
h0 = rig.dimensions.z
rig.scale = (1.95 / h0,) * 3
rig.location = (-2.7, 0.15, 0.0)
rig.rotation_euler = (0, 0, math.radians(90))          # face +X, towards the word
# the sword and the knight's plates catch the rim lights a little more
for o in bpy.data.objects:
    if o.type == "MESH" and o.parent == rig:
        for slot in o.material_slots:
            p = slot.material.node_tree.nodes.get("Principled BSDF")
            if p:
                p.inputs["Roughness"].default_value = 0.55

# timeline on an NLA track: idle, the slice (held in its last pose), and the cheer
rig.animation_data_create()
rig.animation_data.action = None
track = rig.animation_data.nla_tracks.new()
track.name = "film"
acts = bpy.data.actions


def strip(name, start, action_name, end=None):
    a = acts[action_name]
    s = track.strips.new(name, start, a)
    s.action_frame_start, s.action_frame_end = a.frame_range[0], a.frame_range[1]
    if end is not None:
        s.frame_end = end
    s.blend_type = "REPLACE"
    s.extrapolation = "HOLD_FORWARD"
    return s


if MODE == "A":
    strip("idle", 0, "Idle", end=T_ATTACK)
    strip("slice", T_ATTACK, "2H_Melee_Attack_Slice")
else:   # B and H only ever show the pose the slice ends in (B plays backwards; a frozen knight reverses cleanly)
    strip("slice", -30, "2H_Melee_Attack_Slice")
if MODE == "H":
    strip("cheer", T_CHEER, "Cheer")

# ---------------------------------------------------------------- lights and camera
def light(name, kind, loc, color, energy, size=2.0, aim=(0.4, 0, 1.0)):
    bpy.ops.object.light_add(type=kind, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.color = color
    o.data.energy = energy
    if kind == "AREA":
        o.data.size = size
    o.data.cycles.is_caustics_light = False
    d = Vector(aim) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if hasattr(o, "visible_glossy"):
        o.visible_glossy = False
    return o


light("Key", "AREA", (-4.0, -6.0, 6.5), (1.0, 0.93, 0.85), 900, size=3.0)
light("RimPink", "AREA", (5.5, 4.0, 3.2), PINK, 700, size=2.5)
light("RimOrange", "AREA", (-5.5, 4.5, 3.0), ORANGE, 520, size=2.5)
light("Fill", "AREA", (3.0, -7.0, 2.0), (0.6, 0.55, 0.8), 140, size=4.0)

bpy.ops.object.camera_add()
cam = bpy.context.object
cam.name = "Camera"
scene.camera = cam
cam.data.lens = 35
cam.data.sensor_width = 36
cam.data.dof.use_dof = True
cam.data.dof.aperture_fstop = 2.4
cam.data.dof.focus_distance = 8.6
cam.data.clip_end = 200


def look_at(o, target):
    d = Vector(target) - o.location
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def cam_pose(f):
    t = min(max(f / T_CAM_STOP, 0.0), 1.0)
    e = t * t * (3 - 2 * t)
    x = -0.9 + 0.5 * e
    y = -9.4 + 1.1 * e
    z = 2.35 - 0.3 * e
    return (x, y, z), (-0.25 + 0.3 * e, 0.0, 1.2)


for f in range(0, 201, 2):
    loc, aim = cam_pose(f if MODE == "A" else T_CAM_STOP)   # B and H sit on the camera's final pose
    cam.location = loc
    look_at(cam, aim)
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)

# ---------------------------------------------------------------- bloom and a touch of vignette
scene.use_nodes = True
nt = scene.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
rl = nt.nodes.new("CompositorNodeRLayers")
glare = nt.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.threshold = 1.05
glare.mix = -0.35
glare.size = 8
comp = nt.nodes.new("CompositorNodeComposite")
nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
nt.links.new(glare.outputs["Image"], comp.inputs["Image"])

# ---------------------------------------------------------------- bake and render
bpy.context.view_layer.update()
bpy.ops.ptcache.bake_all(bake=True)

frames = ONLY or list(range(FRAMES[0], FRAMES[1] + 1, STEP))
for f in frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(OUT, f"{MODE}_{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"rendered {MODE} {f}", flush=True)
print("done", MODE, frames[0], frames[-1])
