"""Render a short clip of the character in one POSE, for the scenario suite.

POSE ∈ {fall, supine, prone, upright, kneel, pushup}. 'fall' is an animated
upright→horizontal transition (a fall event); the others are near-static postures
(a person already down, sitting/standing, kneeling). The vision witness then reads
a fall event on 'fall' and only a static posture on the rest — which is exactly
how a collapse is separated from lying down on purpose.

  CHAR=~/twin-gym/assets/char/Soldier.glb POSE=fall OUT=.../fall NFR=18 \
    blender -b -P blender_poses.py
"""
import bpy, math, os
from mathutils import Euler

CHAR = os.path.expanduser(os.environ.get("CHAR", "~/twin-gym/assets/char/Soldier.glb"))
POSE = os.environ.get("POSE", "fall")
OUT = os.path.expanduser(os.environ.get("OUT", "~/twin-gym/assets/char/pose_" + POSE))
NFR = int(os.environ.get("NFR", "18"))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
ext = os.path.splitext(CHAR)[1].lower()
(bpy.ops.import_scene.gltf if ext in (".glb", ".gltf") else bpy.ops.import_scene.fbx)(filepath=CHAR)
for a in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
    if a.animation_data:
        a.animation_data_clear()
roots = [o for o in bpy.data.objects if o.parent is None]
piv = bpy.data.objects.new("pivot", None)
sc.collection.objects.link(piv)
for o in roots:
    o.parent = piv
    o.matrix_parent_inverse = piv.matrix_world.inverted()
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
H = max((max(o.dimensions) for o in meshes), default=1.9)

# room
bpy.ops.mesh.primitive_plane_add(size=14)
floor = bpy.context.object
fmat = bpy.data.materials.new("f"); fmat.use_nodes = True
fmat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.60, 0.53, 0.44, 1)
floor.data.materials.append(fmat)
bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 3.2, 3.5), rotation=(math.radians(90), 0, 0))
wall = bpy.context.object
wmat = bpy.data.materials.new("w"); wmat.use_nodes = True
wmat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.80, 0.78, 0.73, 1)
wall.data.materials.append(wmat)
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.4, 1.8, 0.5)); bpy.context.object.scale = (0.6, 0.6, 0.5)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.6, 2.4, 0.7)); bpy.context.object.scale = (0.45, 0.3, 0.7)

# lights + camera (framed to the character height)
bpy.ops.object.light_add(type="SUN", location=(3, -3, 6)); bpy.context.object.data.energy = 3.5
bpy.ops.object.light_add(type="AREA", location=(-2, -3, 3)); bpy.context.object.data.energy = 350
cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
dist = max(4.2, H * 2.5)
cam.location = (0, -dist, H * 0.6); cam.rotation_euler = Euler((math.radians(80), 0, 0)); sc.camera = cam

# pose keyframes on the pivot (crude but sufficient for the vision witness)
def key(f, rot, loc):
    piv.rotation_euler = Euler(rot); piv.location = loc
    piv.keyframe_insert("rotation_euler", frame=f); piv.keyframe_insert("location", frame=f)

if POSE == "fall":
    key(1, (0, 0, 0), (0, 0, 0))
    key(int(NFR * 0.30), (0, 0, 0), (0, 0, 0))
    key(int(NFR * 0.72), (0, math.radians(80), 0), (-0.8, 0.4, 0))
    key(NFR, (0, math.radians(90), 0), (-1.0, 0.5, 0))
else:
    rot = {
        "supine": (math.radians(-90), 0, 0),   # lying face-up, static
        "prone":  (math.radians(90), 0, 0),    # lying face-down, static
        "upright": (0, 0, 0),                   # standing / sitting upright
        "kneel":  (math.radians(38), 0, 0),     # crouched / kneeling, intermediate
        "pushup": (0, math.radians(90), 0),     # horizontal but held off the ground
    }.get(POSE, (0, 0, 0))
    loc = (0, 0, 0) if POSE in ("upright", "kneel") else (-0.6, 0.4, 0)
    for f in (1, NFR):
        key(f, rot, loc)

sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 18
sc.cycles.use_denoising = False
try:
    bpy.context.view_layer.cycles.use_denoising = False
except Exception:
    pass
sc.render.resolution_x = 512; sc.render.resolution_y = 512
sc.frame_start = 1; sc.frame_end = NFR
for f in range(1, NFR + 1):
    sc.frame_set(f)
    sc.render.filepath = os.path.join(OUT, f"f{f-1:03d}.png")
    bpy.ops.render.render(write_still=True)
print("DONE", POSE, NFR, "->", OUT)
