"""Render the real contribution calendar as a 3D city, as a seamless orbit loop.

Every day of the last year becomes a tower on a 53x7 grid. Height and colour
follow the actual contribution count from assets/contrib.json (fetched from
the GraphQL API), so the skyline is the account's own history: quiet weeks are
dim slabs, busy weeks stand up and glow. The camera makes one full orbit per
loop, a light sweep rolls across the year, and everything else breathes on
sin(2*pi*frame/N), so the last frame hands off to the first without a seam.

Usage:
    python scripts/render_city.py -- <out_dir>
Env:
    CITY_FRAMES (60)  CITY_W (1000)  CITY_H (350)  CITY_SAMPLES (48)
    CITY_DATA (assets/contrib.json next to this repo)
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "render_city")
N = int(os.environ.get("CITY_FRAMES", "60"))
W = int(os.environ.get("CITY_W", "1000"))
H = int(os.environ.get("CITY_H", "350"))
SAMPLES = int(os.environ.get("CITY_SAMPLES", "48"))
DATA = os.environ.get("CITY_DATA", os.path.join(HERE, "..", "assets", "contrib.json"))
os.makedirs(OUT, exist_ok=True)

PINK = (0.925, 0.282, 0.600, 1.0)
ORANGE = (0.976, 0.451, 0.086, 1.0)
YELLOW = (0.980, 0.800, 0.082, 1.0)
GREEN = (0.247, 0.725, 0.314, 1.0)
VIOLET = (0.639, 0.443, 0.969, 1.0)
BLUE = (0.345, 0.651, 1.000, 1.0)
SLAB = (0.10, 0.12, 0.19, 1.0)

# ---------------------------------------------------------------- data
with open(DATA, encoding="utf-8") as fh:
    cal = json.load(fh)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = cal["weeks"]
days = [(wi, d["weekday"], d["contributionCount"]) for wi, w in enumerate(weeks) for d in w["contributionDays"]]
max_count = max(c for _, _, c in days) or 1
print(f"[city] {cal['totalContributions']} contributions, {len(weeks)} weeks, max/day {max_count}")

STEP = 0.62      # grid pitch
FOOT = 0.50      # tower footprint
GW = len(weeks)
CX = (GW - 1) * STEP / 2
CY = 3 * STEP


def height_for(count: int) -> float:
    if count <= 0:
        return 0.05
    q = (count / max_count) ** 0.45
    return 0.10 + 3.2 * q


def colour_for(count: int):
    if count <= 0:
        return SLAB, 0.06
    q = (count / max_count) ** 0.5
    if q < 0.22:
        return GREEN, 0.40
    if q < 0.42:
        return BLUE, 0.60
    if q < 0.62:
        return VIOLET, 0.95
    if q < 0.82:
        return ORANGE, 1.15
    return YELLOW, 1.4


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
                print(f"[city] rendering on {kind}: {[d.name for d in gpus]}")
                break
        except Exception as e:  # noqa: BLE001
            print(f"[city] {kind} unavailable: {e}")
except Exception as e:  # noqa: BLE001
    print(f"[city] cycles prefs unavailable: {e}")
if scene.cycles.device == "CPU":
    print("[city] rendering on CPU")
try:
    scene.cycles.denoiser = "OPTIX" if scene.cycles.device == "GPU" else "OPENIMAGEDENOISE"
except TypeError:
    pass

# ---------------------------------------------------------------- world
world = bpy.data.worlds.new("Night")
scene.world = world
world.use_nodes = True
wn, wl = world.node_tree.nodes, world.node_tree.links
for n in list(wn):
    wn.remove(n)
w_out = wn.new("ShaderNodeOutputWorld")
w_bg = wn.new("ShaderNodeBackground")
w_grad = wn.new("ShaderNodeTexGradient")
w_grad.gradient_type = "SPHERICAL"
w_ramp = wn.new("ShaderNodeValToRGB")
w_ramp.color_ramp.elements[0].position = 0.0
w_ramp.color_ramp.elements[0].color = (0.008, 0.010, 0.020, 1)
w_ramp.color_ramp.elements[1].position = 1.0
w_ramp.color_ramp.elements[1].color = (0.05, 0.04, 0.11, 1)
w_tc = wn.new("ShaderNodeTexCoord")
w_map = wn.new("ShaderNodeMapping")
w_map.inputs["Scale"].default_value = (0.9, 0.9, 0.9)
wl.new(w_tc.outputs["Generated"], w_map.inputs["Vector"])
wl.new(w_map.outputs["Vector"], w_grad.inputs["Vector"])
wl.new(w_grad.outputs["Fac"], w_ramp.inputs["Fac"])
wl.new(w_ramp.outputs["Color"], w_bg.inputs["Color"])
w_bg.inputs["Strength"].default_value = 1.0
wl.new(w_bg.outputs["Background"], w_out.inputs["Surface"])


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


# ---------------------------------------------------------------- materials
def tower_material():
    """One material for every tower. Tint and glow come from obj.color via
    Object Info, so a single shader serves 365 objects; the vertical gradient
    (dark base, hot top) rides on Generated Z, which is normalised per object."""
    m, p, nt = principled("Tower")
    nodes, links = nt.nodes, nt.links
    tc = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    zpow = nodes.new("ShaderNodeMath")
    zpow.operation = "POWER"
    zpow.inputs[1].default_value = 0.8
    links.new(sep.outputs["Z"], zpow.inputs[0])
    info = nodes.new("ShaderNodeObjectInfo")
    dark = nodes.new("ShaderNodeRGB")
    dark.outputs[0].default_value = (0.02, 0.025, 0.045, 1)
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MIX"
    links.new(zpow.outputs[0], mix.inputs["Factor"])
    links.new(dark.outputs[0], mix.inputs[6])
    links.new(info.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], p.inputs["Base Color"])
    # glow: colour x alpha(strength) x (0.35 + z)
    zoff = nodes.new("ShaderNodeMath")
    zoff.operation = "ADD"
    zoff.inputs[1].default_value = 0.35
    links.new(zpow.outputs[0], zoff.inputs[0])
    strength = nodes.new("ShaderNodeMath")
    strength.operation = "MULTIPLY"
    links.new(info.outputs["Alpha"], strength.inputs[0])
    links.new(zoff.outputs[0], strength.inputs[1])
    gain = nodes.new("ShaderNodeMath")
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = 2.2
    links.new(strength.outputs[0], gain.inputs[0])
    links.new(info.outputs["Color"], p.inputs["Emission Color"])
    links.new(gain.outputs[0], p.inputs["Emission Strength"])
    set_in(p, "Metallic", 0.55)
    set_in(p, "Roughness", 0.28)
    set_in(p, "Coat Weight", 0.8)
    set_in(p, "Coat Roughness", 0.06)
    return m


def floor_material():
    """Wet black mirror with faint violet grid lines, one cell per tower."""
    m, p, nt = principled("CityFloor")
    nodes, links = nt.nodes, nt.links
    tc = nodes.new("ShaderNodeTexCoord")
    mp = nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / STEP, 1 / STEP, 1.0)
    mp.inputs["Location"].default_value = (STEP / 2, STEP / 2, 0)
    links.new(tc.outputs["Object"], mp.inputs["Vector"])
    brick = nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.035
    brick.inputs["Mortar Smooth"].default_value = 0.6
    brick.inputs["Color1"].default_value = (0, 0, 0, 1)
    brick.inputs["Color2"].default_value = (0, 0, 0, 1)
    brick.inputs["Mortar"].default_value = (1, 1, 1, 1)
    links.new(mp.outputs["Vector"], brick.inputs["Vector"])
    # fade the grid out with distance so the horizon stays clean
    dist = nodes.new("ShaderNodeVectorMath")
    dist.operation = "LENGTH"
    cen = nodes.new("ShaderNodeVectorMath")
    cen.operation = "SUBTRACT"
    cen.inputs[1].default_value = (CX, CY, 0)
    links.new(tc.outputs["Object"], cen.inputs[0])
    links.new(cen.outputs[0], dist.inputs[0])
    fade = nodes.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = 14.0
    fade.inputs["From Max"].default_value = 30.0
    fade.inputs["To Min"].default_value = 1.0
    fade.inputs["To Max"].default_value = 0.0
    links.new(dist.outputs["Value"], fade.inputs["Value"])
    line = nodes.new("ShaderNodeMath")
    line.operation = "MULTIPLY"
    links.new(brick.outputs["Fac"], line.inputs[0])
    links.new(fade.outputs["Result"], line.inputs[1])
    glow = nodes.new("ShaderNodeMath")
    glow.operation = "MULTIPLY"
    glow.inputs[1].default_value = 0.55
    links.new(line.outputs[0], glow.inputs[0])
    set_in(p, "Base Color", (0.010, 0.012, 0.020, 1))
    set_in(p, "Metallic", 0.4)
    set_in(p, "Roughness", 0.10)
    set_in(p, "Coat Weight", 0.7)
    set_in(p, "Emission Color", VIOLET)
    links.new(glow.outputs[0], p.inputs["Emission Strength"])
    return m


tower_mat = tower_material()
floor_mat = floor_material()
sweep_mat = solid("Sweep", YELLOW, rough=0.5, emit=(1.0, 0.72, 0.25, 1), strength=7.0)
spark_mats = [
    solid("SparkY", YELLOW, emit=YELLOW, strength=8.0),
    solid("SparkP", PINK, emit=PINK, strength=8.0),
    solid("SparkV", VIOLET, emit=VIOLET, strength=7.0),
]

# ---------------------------------------------------------------- floor
bpy.ops.mesh.primitive_plane_add(size=160, location=(CX, CY, 0))
floor = bpy.context.object
floor.name = "Floor"
floor.data.materials.append(floor_mat)

# ---------------------------------------------------------------- towers
base_mesh = None
towers = []
mass_x = mass_y = mass = 0.0
for wi, wd, count in days:
    h = height_for(count)
    col, glow = colour_for(count)
    x, y = wi * STEP, (6 - wd) * STEP
    if base_mesh is None:
        bpy.ops.mesh.primitive_cube_add(size=1)
        proto = bpy.context.object
        bev = proto.modifiers.new("Bevel", "BEVEL")
        bev.width = 0.03
        bev.segments = 3
        bev.limit_method = "NONE"
        base_mesh = proto.data
        base_mesh.materials.append(tower_mat)
        t = proto
    else:
        t = link_obj(bpy.data.objects.new("Tower", base_mesh))
        bev = t.modifiers.new("Bevel", "BEVEL")
        bev.width = 0.03
        bev.segments = 3
        bev.limit_method = "NONE"
    t.name = f"Day_{wi:02d}_{wd}"
    t.scale = (FOOT, FOOT, h)
    t.location = (x, y, h / 2)
    t.color = (col[0], col[1], col[2], glow)
    if count > 0:
        amp = 0.02 + 0.06 * (count / max_count) ** 0.5
        drive(t, "location", 2, f"{h / 2:.3f} + {amp:.3f}*{sinf(wi * 0.35 + wd * 0.5)}")
        mass_x += x * count
        mass_y += y * count
        mass += count
    towers.append(t)
focus_x, focus_y = (mass_x / mass, mass_y / mass) if mass else (CX, CY)
print(f"[city] {len(towers)} towers, focus at ({focus_x:.1f}, {focus_y:.1f})")

# ---------------------------------------------------------------- light sweep across the year
bpy.ops.mesh.primitive_cube_add(size=1)
sweep = bpy.context.object
sweep.name = "Sweep"
sweep.data.materials.append(sweep_mat)
sweep.scale = (0.05, 7 * STEP + 1.2, 1.6)
sweep.location = (0, CY, -1.0)
drive(sweep, "location", 0, f"{-1.0:.2f} + {(GW - 1) * STEP + 2.0:.2f}*frame/{N}")
# rises out of the floor, crosses, sinks back under it: invisible at the wrap
drive(sweep, "location", 2, f"-0.9 + 1.5*sin(pi*frame/{N})*sin(pi*frame/{N})")

# ---------------------------------------------------------------- sparks
rng = random.Random(2965)
for i in range(30):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=rng.uniform(0.02, 0.045), subdivisions=2)
    s = bpy.context.object
    s.name = f"Spark{i}"
    s.data.materials.append(rng.choice(spark_mats))
    x = rng.uniform(-2, (GW - 1) * STEP + 2)
    y = rng.uniform(-2, 6 * STEP + 2)
    z = rng.uniform(0.4, 4.5)
    ph = rng.uniform(0, 6.28)
    s.location = (x, y, z)
    drive(s, "location", 2, f"{z:.2f} + 0.35*{sinf(ph)}")
    drive(s, "location", 0, f"{x:.2f} + 0.18*cos(2*pi*frame/{N} + {ph * 0.6:.3f})")


# ---------------------------------------------------------------- lights
def area(name, loc, energy, color, size=6.0, target=(CX, CY, 0.8)):
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
        lo.visible_camera = False  # light the scene, never appear in it...
        lo.visible_glossy = False  # ...and never as a white square in the mirror floor
    except AttributeError:
        pass
    return lo


area("Key", (CX - 14, CY - 18, 16), 9000, (1.0, 0.85, 0.70), size=10)
area("Rim", (CX + 16, CY + 16, 11), 9000, (0.55, 0.42, 1.0), size=8)
area("Fill", (CX + 12, CY - 20, 6), 2500, (0.70, 0.82, 1.0), size=12)

# ---------------------------------------------------------------- camera: one full orbit per loop
cam_pivot = link_obj(bpy.data.objects.new("CamPivot", None))
cam_pivot.location = (CX, CY, 0)
drive(cam_pivot, "rotation_euler", 2, f"2*pi*frame/{N} + radians(-35)")
cam_target = link_obj(bpy.data.objects.new("CamTarget", None))
cam_target.location = (CX, CY, 0.6)
focus = link_obj(bpy.data.objects.new("Focus", None))
focus.location = (focus_x, focus_y, 1.2)
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 32
cam_data.dof.use_dof = True
cam_data.dof.focus_object = focus
cam_data.dof.aperture_fstop = 5.0
cam = link_obj(bpy.data.objects.new("Cam", cam_data))
cam.parent = cam_pivot
cam.location = (0, -30.0, 11.0)
drive(cam, "location", 2, f"11.0 + 1.6*{sinf(1.1)}")
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
    for iname, val in (("Threshold", 1.0), ("Size", 0.6), ("Strength", 0.55)):
        if iname in glare.inputs:
            try:
                glare.inputs[iname].default_value = val
            except Exception:  # noqa: BLE001
                pass
    nt.links.new(rl.outputs["Image"], glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"], comp.inputs["Image"])
    print("[city] bloom on")
except Exception as e:  # noqa: BLE001
    print(f"[city] no bloom: {e}")

# ---------------------------------------------------------------- go
only = os.environ.get("CITY_ONLY", "").strip()
if only:
    for f in (int(x) for x in only.split(",")):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(OUT, f"frame_{f:04d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[city] still frame {f}")
else:
    print(f"[city] {N} frames @ {W}x{H}, {SAMPLES} spp")
    bpy.ops.render.render(animation=True)
print("[city] done")
