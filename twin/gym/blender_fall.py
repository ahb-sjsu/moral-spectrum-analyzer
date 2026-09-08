"""Render a home-care fall as a headless Blender animation.

Character-agnostic: set CHAR to any rigged glb/fbx (CesiumMan by default; drop in
a photoreal Mixamo "With Skin" FBX or a Ready Player Me glb to upgrade the look
and the prone-detection reliability -- nothing else changes). The fall is authored
on the skeleton (a forward tip + descent, with a spine/limb crumple) so it reads
as a collapse, not a toppling plank, and the descent -- the robust witness signal
-- is fully in view.

Run on Atlas:
  CHAR=~/twin-gym/assets/char/CesiumMan.glb OUT=~/twin-gym/assets/char/fall_anim \
    blender -b -P blender_fall.py
Produces OUT/f000.png .. and is fed to erisml encode_video (geometry backend).
"""
import bpy, math, os
from mathutils import Euler

CHAR = os.path.expanduser(os.environ.get("CHAR", "~/twin-gym/assets/char/CesiumMan.glb"))
OUT = os.path.expanduser(os.environ.get("OUT", "~/twin-gym/assets/char/fall_anim"))
NFR = int(os.environ.get("NFR", "40"))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# --- character ---
ext = os.path.splitext(CHAR)[1].lower()
if ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=CHAR)
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=CHAR)
else:
    raise SystemExit(f"unsupported character format: {ext}")

# drop any non-character helper meshes the sample ships (e.g. CesiumMan Icosphere)
for m in [o for o in bpy.data.objects if o.type == "MESH"]:
    nm = m.name.lower()
    if "cesium" not in nm and "man" not in nm and "body" not in nm and "avatar" not in nm and "wolf3d" not in nm:
        bpy.data.objects.remove(m, do_unlink=True)

arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
arm = arms[0] if arms else None
if arm and arm.animation_data:
    arm.animation_data_clear()  # drop the built-in walk; our keyframes drive it

roots = [o for o in bpy.data.objects if o.parent is None and o.type in ("ARMATURE", "MESH", "EMPTY")]
piv = bpy.data.objects.new("pivot", None)
sc.collection.objects.link(piv)
for o in roots:
    o.parent = piv
    o.matrix_parent_inverse = piv.matrix_world.inverted()

# --- room ---
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
floor = bpy.context.object
fmat = bpy.data.materials.new("floor"); fmat.use_nodes = True
fmat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.62, 0.55, 0.45, 1)
floor.data.materials.append(fmat)
bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 3, 3), rotation=(math.radians(90), 0, 0))  # back wall
wall = bpy.context.object
wmat = bpy.data.materials.new("wall"); wmat.use_nodes = True
wmat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.80, 0.78, 0.74, 1)
wall.data.materials.append(wmat)
# a chair + a cabinet as props
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.2, 1.6, 0.5)); bpy.context.object.scale = (0.5, 0.5, 0.5)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.4, 2.2, 0.6)); bpy.context.object.scale = (0.4, 0.3, 0.6)

# --- lights + camera ---
bpy.ops.object.light_add(type="SUN", location=(3, -3, 6)); bpy.context.object.data.energy = 3.5
bpy.ops.object.light_add(type="AREA", location=(-2, -3, 3)); bpy.context.object.data.energy = 300
cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
cam.location = (0, -4.9, 1.5); cam.rotation_euler = Euler((math.radians(77), 0, 0)); sc.camera = cam

# --- fall animation on the skeleton + pivot ---
def key_pivot(f, rot, loc):
    piv.rotation_euler = Euler(rot); piv.location = loc
    piv.keyframe_insert("rotation_euler", frame=f); piv.keyframe_insert("location", frame=f)

# stand, tip sideways across the view (about Y), descend; settle prone
key_pivot(1,  (0, 0, 0), (0, 0, 0))
key_pivot(int(NFR*0.25), (0, 0, 0), (0, 0, 0))
key_pivot(int(NFR*0.70), (0, math.radians(78), 0), (-0.8, 0.5, 0))
key_pivot(NFR, (0, math.radians(90), 0), (-1.0, 0.6, 0))

# modest skeletal crumple so it is a collapse, not a plank
def key_bone(name, f, rot):
    if not arm or name not in arm.pose.bones:
        return
    pb = arm.pose.bones[name]; pb.rotation_mode = "XYZ"
    pb.rotation_euler = Euler(rot); pb.keyframe_insert("rotation_euler", frame=f)

for nm in ("Skeleton_torso_joint_1", "leg_joint_L_1", "leg_joint_R_1",
           "Skeleton_arm_joint_L__4_", "Skeleton_arm_joint_R"):
    key_bone(nm, 1, (0, 0, 0))
    key_bone(nm, int(NFR*0.25), (0, 0, 0))
key_bone("Skeleton_torso_joint_1", NFR, (math.radians(28), 0, 0))
key_bone("leg_joint_L_1", NFR, (math.radians(35), 0, 0))
key_bone("leg_joint_R_1", NFR, (math.radians(20), 0, 0))
key_bone("Skeleton_arm_joint_L__4_", NFR, (0, 0, math.radians(40)))
key_bone("Skeleton_arm_joint_R", NFR, (0, 0, math.radians(-40)))

# --- render ---
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 20
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
print("DONE", NFR, "frames ->", OUT)
