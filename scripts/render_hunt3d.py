"""Render the bug hunt as a seamless 3D loop with Blender (bpy, Cycles).

Three beetles crawl in circles over a dark circuit-board floor. The crosshair
from the avatar hovers above the lead beetle, spinning and pulsing, and every
few beats a laser drops from its core, the beetle flashes green and a burst of
sparks flies out. Every motion completes a whole number of cycles per loop, so
the last frame hands off to the first without a seam.

Usage:
    python scripts/render_hunt3d.py -- <out_dir>
Env:
    HUNT_FRAMES (72)  HUNT_W (1200)  HUNT_H (360)  HUNT_SAMPLES (48)  HUNT_ONLY ("1,36")
"""
from __future__ import annotations

import math
import os
import random
import sys

import bpy

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "render_hunt")
N = int(os.environ.get("HUNT_FRAMES", "72"))
W = int(os.environ.get("HUNT_W", "1200"))
H = int(os.environ.get("HUNT_H", "360"))
SAMPLES = int(os.environ.get("HUNT_SAMPLES", "48"))
os.makedirs(OUT, exist_ok=True)

PINK = (0.925, 0.282, 0.600, 1.0)
ORANGE = (0.976, 0.451, 0.086, 1.0)
YELLOW = (0.980, 0.800, 0.082, 1.0)
GREEN = (0.247, 0.725, 0.314, 1.0)
VIOLET = (0.639, 0.443, 0.969, 1.0)
RED = (1.0, 0.12, 0.10, 1.0)
BEATS = 3  # laser strikes per loop

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
                print(f"[hunt] rendering on {kind}: {[d.name for d in gpus]}")
                break
        except Exception as e:  # noqa: BLE001
            print(f"[hunt] {kind} unavailable: {e}")
except Exception as e:  # noqa: BLE001
    print(f"[hunt] cycles prefs unavailable: {e}")
try:
    scene.cycles.denoiser = "OPTIX" if scene.cycles.device == "GPU" else "OPENIMAGEDENOISE"
except TypeError:
    pass

# ---------------------------------------------------------------- world
world = bpy.data.worlds.new("Dark")
scene.world = world
world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
for n in list(wn):
    wn.remove(n)
w_out = wn.new("ShaderNodeOutputWorld")
w_bg = wn.new("ShaderNodeBackground")
w_bg.inputs["Color"].default_value = (0.006, 0.008, 0.014, 1)
w_bg.inputs["Strength"].default_value = 1.0
wl.new(w_bg.outputs["Background"], w_out.inputs["Surface"])


# ---------------------------------------------------------------- helpers
def link_obj(obj):
    scene.collection.objects.link(obj)
    return obj


def drive(target, path, index, expr):
    fc = target.driver_add(path, index) if index is not None else target.driver_add(path)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr
    return fc


def sinf(k=1.0, phase=0.0):
    return f"sin({k:.4f}*2*pi*frame/{N} + {phase:.4f})"


def _pulse(frame, k, phase, sharp):
    return ((math.sin(k * 2 * math.pi * frame / N + phase) + 1) / 2) ** sharp


# Driver expressions are capped at a few hundred characters, so the pulse is a
# registered driver function rather than an inline product of sines.
bpy.app.driver_namespace["pulse"] = _pulse
try:
    bpy.context.preferences.filepaths.use_scripts_auto_execute = True
except Exception:  # noqa: BLE001
    pass


def pulse(k=BEATS, phase=0.0, sharp=3):
    """0..1 pulse that peaks k times per loop, sharpened by an exponent."""
    return f"pulse(frame, {k:.4f}, {phase:.4f}, {sharp})"


def set_in(node, name, value):
    if name in node.inputs:
        node.inputs[name].default_value = value


def principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes["Principled BSDF"], m.node_tree


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


def board_material():
    """Near-black board with faint green trace grid and a soft violet haze."""
    m, p, nt = principled("Board")
    nodes, links = nt.nodes, nt.links
    tc = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.2, 2.2, 1.0)
    links.new(tc.outputs["Object"], mp.inputs["Vector"])
    brick = nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.03
    brick.inputs["Mortar Smooth"].default_value = 0.7
    brick.inputs["Color1"].default_value = (0, 0, 0, 1)
    brick.inputs["Color2"].default_value = (0, 0, 0, 1)
    brick.inputs["Mortar"].default_value = (1, 1, 1, 1)
    links.new(mp.outputs["Vector"], brick.inputs["Vector"])
    dist = nodes.new("ShaderNodeVectorMath")
    dist.operation = "LENGTH"
    links.new(tc.outputs["Object"], dist.inputs[0])
    fade = nodes.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = 3.0
    fade.inputs["From Max"].default_value = 9.0
    fade.inputs["To Min"].default_value = 0.45
    fade.inputs["To Max"].default_value = 0.0
    links.new(dist.outputs["Value"], fade.inputs["Value"])
    line = nodes.new("ShaderNodeMath")
    line.operation = "MULTIPLY"
    links.new(brick.outputs["Fac"], line.inputs[0])
    links.new(fade.outputs["Result"], line.inputs[1])
    set_in(p, "Base Color", (0.012, 0.016, 0.022, 1))
    set_in(p, "Metallic", 0.3)
    set_in(p, "Roughness", 0.18)
    set_in(p, "Coat Weight", 0.5)
    set_in(p, "Emission Color", (0.30, 0.85, 0.45, 1))
    links.new(line.outputs[0], p.inputs["Emission Strength"])
    return m


board_mat = board_material()
shell_mat = solid("Shell", (0.30, 0.04, 0.07, 1), metallic=0.65, rough=0.22, coat=1.0)
shell_hit = solid("ShellHit", (0.30, 0.04, 0.07, 1), metallic=0.65, rough=0.22, emit=GREEN, strength=0.0, coat=1.0)
leg_mat = solid("Leg", (0.02, 0.02, 0.025, 1), metallic=0.5, rough=0.35)
eye_mat = solid("Eye", RED, emit=RED, strength=6.0)
ring_mat = solid("Ring", ORANGE, metallic=0.3, rough=0.3, emit=ORANGE, strength=6.0)
core_mat = solid("Core", YELLOW, metallic=0.2, rough=0.3, emit=YELLOW, strength=9.0)
laser_mat = solid("Laser", ORANGE, emit=(1.0, 0.45, 0.15, 1), strength=0.0)
spark_mats = [
    solid("SparkY", YELLOW, emit=YELLOW, strength=11.0),
    solid("SparkG", GREEN, emit=GREEN, strength=11.0),
    solid("SparkP", PINK, emit=PINK, strength=11.0),
]

# ---------------------------------------------------------------- board
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
board = bpy.context.object
board.name = "Board"
board.data.materials.append(board_mat)


# ---------------------------------------------------------------- beetles
def beetle(name, radius, speed, phase, shell, size=1.0):
    """A beetle crawling a circle of `radius`; `speed` whole laps per loop."""
    path = link_obj(bpy.data.objects.new(f"{name}Path", None))
    path.location = (0, 0, 0)
    drive(path, "rotation_euler", 2, f"{speed:.1f}*2*pi*frame/{N} + {phase:.4f}")
    root = link_obj(bpy.data.objects.new(name, None))
    root.parent = path
    root.location = (radius, 0, 0.12 * size)
    root.rotation_euler = (0, 0, math.radians(90) if speed > 0 else math.radians(-90))
    drive(root, "location", 2, f"{0.12 * size:.3f} + {0.015 * size:.4f}*{sinf(12, phase)}")
    drive(root, "rotation_euler", 1, f"radians(4)*{sinf(12, phase + 1.0)}")

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=40, ring_count=20)
    body = bpy.context.object
    body.name = f"{name}Body"
    body.scale = (0.24 * size, 0.34 * size, 0.15 * size)
    body.parent = root
    body.location = (0, 0, 0)
    body.data.materials.append(shell)
    bpy.ops.object.shade_smooth()

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11 * size, segments=32, ring_count=16)
    head = bpy.context.object
    head.name = f"{name}Head"
    head.parent = root
    head.location = (0, 0.36 * size, -0.02 * size)
    head.data.materials.append(shell)
    bpy.ops.object.shade_smooth()

    for sx in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03 * size, segments=16, ring_count=8)
        eye = bpy.context.object
        eye.name = f"{name}Eye{sx}"
        eye.parent = root
        eye.location = (sx * 0.06 * size, 0.44 * size, 0.02 * size)
        eye.data.materials.append(eye_mat)

    for i, ly in enumerate((0.18, 0.0, -0.18)):
        for sx in (-1, 1):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.018 * size, depth=0.34 * size, vertices=10)
            leg = bpy.context.object
            leg.name = f"{name}Leg{i}{sx}"
            leg.parent = root
            leg.location = (sx * 0.30 * size, ly * size, -0.06 * size)
            leg.rotation_euler = (0, sx * math.radians(60), 0)
            leg.data.materials.append(leg_mat)
            # legs scissor at 6 strides per loop, alternating sides and rows
            drive(leg, "rotation_euler", 0, f"radians(16)*{sinf(6, phase + (i % 2) * 3.14159 + (0 if sx > 0 else 3.14159))}")
    return root


lead = beetle("Bug1", 1.35, 1.0, 0.0, shell_hit, size=1.0)
beetle("Bug2", 2.6, -1.0, 2.1, shell_mat, size=0.85)
beetle("Bug3", 3.4, 1.0, 4.3, shell_mat, size=0.7)

# the lead beetle flashes green on every laser beat
try:
    inp = shell_hit.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    fc = inp.driver_add("default_value")
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = f"0.9*{pulse(BEATS, 0.0, 4)}"
except Exception as e:  # noqa: BLE001
    print(f"[hunt] no flash driver: {e}")

# ---------------------------------------------------------------- crosshair locked on the lead beetle
hunter = link_obj(bpy.data.objects.new("Hunter", None))
# follow Bug1's position in world space but keep a world-space tilt toward the
# camera: a child of the orbit would carry the tilt around with it and turn the
# ring edge-on halfway through the loop.
follow = hunter.constraints.new("COPY_LOCATION")
follow.target = lead
follow.use_offset = True
hunter.location = (0, 0, 0.88)
hunter.rotation_euler = (math.radians(-58), 0, 0)   # face the camera, not the sky
drive(hunter, "rotation_euler", 0, f"radians(-58) + radians(6)*{sinf(1, 0.4)}")
drive(hunter, "location", 2, f"0.88 + 0.06*{sinf(2, 1.3)}")
spinner = link_obj(bpy.data.objects.new("Spinner", None))
spinner.parent = hunter
drive(spinner, "rotation_euler", 2, f"2*2*pi*frame/{N}")         # two spins per loop, about its own face
for axis in (0, 1, 2):
    drive(spinner, "scale", axis, f"1.0 + 0.10*{pulse(BEATS, 0.0, 2)}")

bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.075, major_segments=96, minor_segments=32)
ring = bpy.context.object
ring.name = "Ring"
ring.parent = spinner
ring.location = (0, 0, 0)
ring.data.materials.append(ring_mat)
for i, (dx, dy) in enumerate(((0.7, 0), (-0.7, 0), (0, 0.7), (0, -0.7))):
    bpy.ops.mesh.primitive_cube_add(size=1)
    arm = bpy.context.object
    arm.name = f"Arm{i}"
    arm.scale = (0.26, 0.10, 0.10) if dy == 0 else (0.10, 0.26, 0.10)
    arm.location = (dx, dy, 0)
    arm.parent = spinner
    arm.data.materials.append(ring_mat)
    bev = arm.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.02
    bev.segments = 3
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, segments=48, ring_count=24)
core = bpy.context.object
core.name = "Core"
core.parent = spinner
core.location = (0, 0, 0)
core.data.materials.append(core_mat)
bpy.ops.object.shade_smooth()

# laser: a vertical column from the crosshair down onto the beetle, only there on the beat
bpy.ops.mesh.primitive_cylinder_add(radius=1, depth=1.0, vertices=24)
laser = bpy.context.object
laser.name = "Laser"
laser.parent = lead.parent
laser.location = (1.35, 0, 0.5)
laser.data.materials.append(laser_mat)
for axis in (0, 1):
    drive(laser, "scale", axis, f"0.03*{pulse(BEATS, 0.0, 6)}")
try:
    inp = laser_mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    fc = inp.driver_add("default_value")
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = f"12*{pulse(BEATS, 0.0, 2)}"
except Exception as e:  # noqa: BLE001
    print(f"[hunt] no laser driver: {e}")

# sparks burst out of the beetle on each beat, then fall back in
rng = random.Random(9327)
for i in range(18):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.02, 0.04), subdivisions=2)
    s = bpy.context.object
    s.name = f"Burst{i}"
    s.parent = lead
    s.data.materials.append(rng.choice(spark_mats))
    ang = rng.uniform(0, 6.28)
    ux, uy = math.cos(ang), math.sin(ang)
    uz = rng.uniform(0.6, 1.4)
    reach = rng.uniform(0.5, 1.1)
    p = pulse(BEATS, -0.9, 1)
    drive(s, "location", 0, f"{ux * reach:.3f}*{p}")
    drive(s, "location", 1, f"{uy * reach:.3f}*{p}")
    drive(s, "location", 2, f"0.1 + {uz * reach:.3f}*{p}")
    for axis in (0, 1, 2):
        drive(s, "scale", axis, f"0.2 + 1.2*{p}")

# ambient motes
for i in range(26):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.012, 0.03), subdivisions=2)
    s = bpy.context.object
    s.name = f"Mote{i}"
    s.data.materials.append(rng.choice(spark_mats))
    x, y, z = rng.uniform(-5, 5), rng.uniform(-3, 5), rng.uniform(0.2, 2.6)
    ph = rng.uniform(0, 6.28)
    s.location = (x, y, z)
    drive(s, "location", 2, f"{z:.2f} + 0.2*{sinf(1, ph)}")
    drive(s, "location", 0, f"{x:.2f} + 0.1*cos(2*pi*frame/{N} + {ph * 0.7:.3f})")


# ---------------------------------------------------------------- lights
def area(name, loc, energy, color, size=4.0, target=(0, 0, 0.4)):
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
    try:
        lo.visible_camera = False
        lo.visible_glossy = False
    except AttributeError:
        pass
    return lo


area("Key", (-4.0, -5.0, 5.5), 1400, (1.0, 0.88, 0.75), size=5)
area("Rim", (4.5, 5.0, 4.0), 1600, (0.35, 0.95, 0.70), size=3)
area("Fill", (5.0, -6.0, 2.5), 320, (0.70, 0.80, 1.0), size=6)

# ---------------------------------------------------------------- camera
cam_target = link_obj(bpy.data.objects.new("CamTarget", None))
cam_target.location = (0.0, 0.2, 0.62)
cam_pivot = link_obj(bpy.data.objects.new("CamPivot", None))
drive(cam_pivot, "rotation_euler", 2, f"radians(4)*{sinf(1, 0.3)}")
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 35
cam_data.dof.use_dof = True
cam_data.dof.focus_object = lead
cam_data.dof.aperture_fstop = 2.8
cam = link_obj(bpy.data.objects.new("Cam", cam_data))
cam.parent = cam_pivot
cam.location = (0.3, -6.2, 1.9)
drive(cam, "location", 2, f"1.9 + 0.10*{sinf(1, 2.0)}")
c = cam.constraints.new("TRACK_TO")
c.target = cam_target
c.track_axis = "TRACK_NEGATIVE_Z"
c.up_axis = "UP_Y"
scene.camera = cam

# ---------------------------------------------------------------- bloom
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
    for iname, val in (("Threshold", 1.0), ("Size", 0.55), ("Strength", 0.5)):
        if iname in glare.inputs:
            try:
                glare.inputs[iname].default_value = val
            except Exception:  # noqa: BLE001
                pass
    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], comp.inputs["Image"])
    print("[hunt] bloom on")
except Exception as e:  # noqa: BLE001
    print(f"[hunt] no bloom: {e}")

# ---------------------------------------------------------------- go
only = os.environ.get("HUNT_ONLY", "").strip()
if only:
    for f in (int(x) for x in only.split(",")):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(OUT, f"frame_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[hunt] still frame {f}")
else:
    print(f"[hunt] {N} frames @ {W}x{H}, {SAMPLES} spp")
    bpy.ops.render.render(animation=True)
print("[hunt] done")
