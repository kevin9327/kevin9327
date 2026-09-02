"""Render the profile hero as a seamless 3D loop with Blender (bpy, Cycles).

Scene: chrome-and-copper "Kevin" lettering standing on a wet-black studio floor,
the crosshair mark from the avatar spinning beside it as a glowing ring, and a
field of contribution bars breathing in the background under a warm key light
and a violet rim light. Everything that moves is driven by sin(2*pi*frame/N),
so the last frame hands off to the first without a seam.

Usage:
    python scripts/render_hero.py -- <out_dir>
Env:
    HERO_FRAMES (72)  HERO_W (1200)  HERO_H (340)  HERO_SAMPLES (64)
"""
from __future__ import annotations

import math
import os
import random
import sys

import bpy

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "render")
N = int(os.environ.get("HERO_FRAMES", "72"))
W = int(os.environ.get("HERO_W", "1200"))
H = int(os.environ.get("HERO_H", "340"))
SAMPLES = int(os.environ.get("HERO_SAMPLES", "64"))
os.makedirs(OUT, exist_ok=True)

PINK = (0.925, 0.282, 0.600, 1.0)
ORANGE = (0.976, 0.451, 0.086, 1.0)
YELLOW = (0.980, 0.800, 0.082, 1.0)
GREEN = (0.247, 0.725, 0.314, 1.0)
VIOLET = (0.639, 0.443, 0.969, 1.0)
BLUE = (0.345, 0.651, 1.000, 1.0)

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.frame_start, scene.frame_end = 1, N
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.filepath = os.path.join(OUT, "frame_")
scene.render.film_transparent = False
for vt in ("AgX", "Filmic"):
    try:
        scene.view_settings.view_transform = vt
        break
    except TypeError:
        continue
try:
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    pass

# GPU if the wheel shipped with kernels for it, CPU (32 threads here) otherwise
scene.cycles.device = "CPU"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.refresh_devices()
            gpus = [d for d in prefs.devices if d.type == kind]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type == kind or d.type == "CPU"
                scene.cycles.device = "GPU"
                print(f"[hero] rendering on {kind}: {[d.name for d in gpus]}")
                break
        except Exception as e:  # noqa: BLE001
            print(f"[hero] {kind} unavailable: {e}")
except Exception as e:  # noqa: BLE001
    print(f"[hero] cycles prefs unavailable: {e}")
if scene.cycles.device == "CPU":
    print("[hero] rendering on CPU")
try:
    scene.cycles.denoiser = "OPTIX" if scene.cycles.device == "GPU" else "OPENIMAGEDENOISE"
except TypeError:
    pass

# ---------------------------------------------------------------- world
world = bpy.data.worlds.new("Studio")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
for n in list(wn):
    wn.remove(n)
out = wn.new("ShaderNodeOutputWorld")
bgn = wn.new("ShaderNodeBackground")
grad = wn.new("ShaderNodeTexGradient")
grad.gradient_type = "SPHERICAL"
ramp = wn.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.010, 0.013, 0.022, 1)
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.06, 0.05, 0.12, 1)
tc = wn.new("ShaderNodeTexCoord")
mapping = wn.new("ShaderNodeMapping")
mapping.inputs["Scale"].default_value = (0.9, 0.9, 0.9)
wl.new(tc.outputs["Generated"], mapping.inputs["Vector"])
wl.new(mapping.outputs["Vector"], grad.inputs["Vector"])
wl.new(grad.outputs["Fac"], ramp.inputs["Fac"])
wl.new(ramp.outputs["Color"], bgn.inputs["Color"])
bgn.inputs["Strength"].default_value = 1.0
wl.new(bgn.outputs["Background"], out.inputs["Surface"])


# ---------------------------------------------------------------- materials
def principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes["Principled BSDF"], m.node_tree


def set_in(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def solid(name, base, metallic=0.0, rough=0.4, emit=None, strength=0.0, coat=0.0):
    m, p, _ = principled(name)
    set_in(p, "Base Color", base)
    set_in(p, "Metallic", metallic)
    set_in(p, "Roughness", rough)
    set_in(p, "Coat Weight", coat)
    if emit is not None:
        set_in(p, "Emission Color", emit)
        set_in(p, "Emission Strength", strength)
    return m


def hot_gradient(name, along="X", lo=-1.9, hi=2.1, metallic=0.9, rough=0.22, glow=0.35):
    """Pink -> orange -> yellow across the object's own X, like the avatar."""
    m, p, nt = principled(name)
    nodes, links = nt.nodes, nt.links
    tc = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    mr = nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = lo
    mr.inputs["From Max"].default_value = hi
    cr = nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.0
    cr.color_ramp.elements[0].color = PINK
    mid = cr.color_ramp.elements.new(0.5)
    mid.color = ORANGE
    cr.color_ramp.elements[-1].position = 1.0
    cr.color_ramp.elements[-1].color = YELLOW
    links.new(tc.outputs["Object"], sep.inputs["Vector"])
    links.new(sep.outputs[along], mr.inputs["Value"])
    links.new(mr.outputs["Result"], cr.inputs["Fac"])
    links.new(cr.outputs["Color"], p.inputs["Base Color"])
    if "Emission Color" in p.inputs:
        links.new(cr.outputs["Color"], p.inputs["Emission Color"])
        set_in(p, "Emission Strength", glow)
    set_in(p, "Metallic", metallic)
    set_in(p, "Roughness", rough)
    set_in(p, "Coat Weight", 1.0)
    set_in(p, "Coat Roughness", 0.05)
    return m


floor_mat = solid("Floor", (0.012, 0.014, 0.022, 1), metallic=0.35, rough=0.13, coat=0.6)
text_mat = hot_gradient("KevinMetal")
ring_mat = solid("Ring", ORANGE, metallic=0.3, rough=0.3, emit=ORANGE, strength=6.0)
core_mat = solid("Core", YELLOW, metallic=0.2, rough=0.3, emit=YELLOW, strength=9.0)
bar_mats = [
    solid("BarDim", (0.05, 0.16, 0.08, 1), rough=0.35, emit=GREEN, strength=0.25),
    solid("BarGreen", GREEN, rough=0.3, emit=GREEN, strength=0.9),
    solid("BarViolet", VIOLET, rough=0.3, emit=VIOLET, strength=1.1),
    solid("BarBlue", BLUE, rough=0.3, emit=BLUE, strength=0.8),
]
spark_mats = [
    solid("SparkY", YELLOW, emit=YELLOW, strength=14.0),
    solid("SparkP", PINK, emit=PINK, strength=14.0),
]


# ---------------------------------------------------------------- helpers
def link_obj(obj):
    scene.collection.objects.link(obj)
    return obj


def drive(obj, path, index, expr):
    fc = obj.driver_add(path, index)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr
    return fc


def sinf(phase=0.0):
    return f"sin(2*pi*frame/{N} + {phase:.4f})"


def cosf(phase=0.0):
    return f"cos(2*pi*frame/{N} + {phase:.4f})"


# ---------------------------------------------------------------- floor
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
floor = bpy.context.object
floor.name = "Floor"
floor.data.materials.append(floor_mat)

# ---------------------------------------------------------------- lettering
bpy.ops.object.text_add(location=(0, 0, 0))
text = bpy.context.object
text.name = "Kevin"
text.data.body = "Kevin"
for font in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
    if os.path.exists(font):
        try:
            text.data.font = bpy.data.fonts.load(font)
            break
        except RuntimeError:
            pass
text.data.size = 1.75
text.data.extrude = 0.16
text.data.bevel_depth = 0.028
text.data.bevel_resolution = 5
text.data.align_x = "CENTER"
text.data.align_y = "CENTER"
text.data.materials.append(text_mat)
text.rotation_euler = (math.radians(90), 0, 0)
text.location = (0.85, 0.0, 0.66)
# a lazy sway that loops: yaw and pitch on sines
drive(text, "rotation_euler", 2, f"radians(9)*{sinf(0.0)}")
drive(text, "rotation_euler", 0, f"radians(90) + radians(4)*{sinf(1.7)}")
drive(text, "location", 2, f"0.66 + 0.05*{sinf(0.9)}")

# ---------------------------------------------------------------- crosshair
pivot = link_obj(bpy.data.objects.new("CrosshairPivot", None))
pivot.location = (-2.9, 0.2, 1.02)
drive(pivot, "rotation_euler", 2, f"2*pi*frame/{N}")            # full turn per loop
drive(pivot, "rotation_euler", 0, f"radians(12)*{sinf(0.6)}")   # gentle tilt
drive(pivot, "location", 2, f"1.02 + 0.07*{sinf(2.4)}")

bpy.ops.mesh.primitive_torus_add(major_radius=0.78, minor_radius=0.105,
                                 major_segments=96, minor_segments=32)
ring = bpy.context.object
ring.name = "Ring"
ring.rotation_euler = (math.radians(90), 0, 0)
ring.data.materials.append(ring_mat)
ring.parent = pivot  # no parent-inverse: the ring must sit ON the pivot, not at the world origin
ring.location = (0, 0, 0)

for i, (dx, dz) in enumerate(((1.06, 0), (-1.06, 0), (0, 1.06), (0, -1.06))):
    bpy.ops.mesh.primitive_cube_add(size=1)
    arm = bpy.context.object
    arm.name = f"Arm{i}"
    arm.scale = (0.36, 0.15, 0.15) if dz == 0 else (0.15, 0.15, 0.36)
    arm.location = (dx, 0, dz)
    arm.data.materials.append(ring_mat)
    arm.parent = pivot
    # rounded edges catch the light
    bev = arm.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.03
    bev.segments = 3

bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, segments=48, ring_count=24)
core = bpy.context.object
core.name = "Core"
core.location = (0, 0, 0)
core.data.materials.append(core_mat)
core.parent = pivot
bpy.ops.object.shade_smooth()

# ---------------------------------------------------------------- bar field
rng = random.Random(9327)
bars = []
for gx in range(-9, 10):
    for gy in range(0, 6):
        if rng.random() < 0.22:
            continue
        x = gx * 0.62 + rng.uniform(-0.05, 0.05)
        y = 4.6 + gy * 0.62
        h = rng.choice((0.12, 0.12, 0.22, 0.4, 0.7, 1.1, 1.5))
        bpy.ops.mesh.primitive_cube_add(size=1)
        b = bpy.context.object
        b.name = f"Bar_{gx}_{gy}"
        b.scale = (0.26, 0.26, h / 2)
        b.location = (x, y, h / 2)
        mat = bar_mats[0] if h < 0.3 else rng.choice(bar_mats[1:])
        b.data.materials.append(mat)
        phase = (gx + 9) * 0.32 + gy * 0.2
        drive(b, "location", 2, f"{h / 2:.3f} + {0.05 + h * 0.08:.3f}*{sinf(phase)}")
        bars.append(b)

# ---------------------------------------------------------------- sparks
for i in range(22):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.025, 0.055), subdivisions=2)
    s = bpy.context.object
    s.name = f"Spark{i}"
    s.data.materials.append(rng.choice(spark_mats))
    x, y, z = rng.uniform(-6, 6), rng.uniform(-1.5, 3.5), rng.uniform(0.3, 3.2)
    ph = rng.uniform(0, 6.28)
    s.location = (x, y, z)
    drive(s, "location", 2, f"{z:.2f} + 0.25*{sinf(ph)}")
    drive(s, "location", 0, f"{x:.2f} + 0.12*{cosf(ph * 0.7)}")

# ---------------------------------------------------------------- lights
def area(name, loc, energy, color, size=4.0, target=(0, 0, 0.8)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.size = size
    lo = link_obj(bpy.data.objects.new(name, ld))
    lo.location = loc
    tgt = link_obj(bpy.data.objects.new(name + "Target", None))
    tgt.location = target
    c = lo.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return lo


area("Key", (-4.5, -6.0, 6.5), 1500, (1.0, 0.86, 0.72), size=5)
area("Rim", (5.5, 5.0, 4.5), 2200, (0.55, 0.42, 1.0), size=3)
area("Fill", (5.0, -7.0, 2.0), 350, (0.75, 0.85, 1.0), size=6)

# ---------------------------------------------------------------- camera
cam_target = link_obj(bpy.data.objects.new("CamTarget", None))
cam_target.location = (-0.65, 0.0, 0.9)
cam_pivot = link_obj(bpy.data.objects.new("CamPivot", None))
cam_pivot.location = (0, 0, 0)
drive(cam_pivot, "rotation_euler", 2, f"radians(3.2)*{sinf(0.3)}")
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 42
cam_data.dof.use_dof = True
cam_data.dof.focus_object = text
cam_data.dof.aperture_fstop = 2.2
cam = link_obj(bpy.data.objects.new("Cam", cam_data))
cam.location = (0.3, -8.6, 2.1)
cam.parent = cam_pivot
c = cam.constraints.new("TRACK_TO")
c.target = cam_target
c.track_axis = "TRACK_NEGATIVE_Z"
c.up_axis = "UP_Y"
scene.camera = cam

# ---------------------------------------------------------------- bloom (compositor)
try:
    scene.use_nodes = True
    nt = scene.node_tree
    rl = next(n for n in nt.nodes if n.type == "R_LAYERS")
    comp = next(n for n in nt.nodes if n.type == "COMPOSITE")
    glare = nt.nodes.new("CompositorNodeGlare")
    for kind in ("BLOOM", "FOG_GLOW"):
        try:
            glare.glare_type = kind
            break
        except TypeError:
            continue
    for attr, val in (("threshold", 1.0), ("size", 8), ("mix", 0.0), ("quality", "MEDIUM")):
        if hasattr(glare, attr):
            try:
                setattr(glare, attr, val)
            except Exception:  # noqa: BLE001
                pass
    for iname, val in (("Threshold", 1.0), ("Size", 0.55), ("Strength", 0.5)):
        if iname in glare.inputs:
            try:
                glare.inputs[iname].default_value = val
            except Exception:  # noqa: BLE001
                pass
    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], comp.inputs["Image"])
    print("[hero] bloom on")
except Exception as e:  # noqa: BLE001
    print(f"[hero] no bloom: {e}")

# ---------------------------------------------------------------- go
print(f"[hero] {N} frames @ {W}x{H}, {SAMPLES} spp, {len(bars)} bars")
bpy.ops.render.render(animation=True)
print("[hero] done")
