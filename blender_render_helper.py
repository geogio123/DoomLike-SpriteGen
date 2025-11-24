import bpy
import os
import math
import mathutils
import sys

argv = sys.argv
if '--' in argv:
    argv = argv[argv.index('--') + 1:]
else:
    argv = []

if len(argv) < 8:
    print('Usage: blender -b --python script.py -- model texture out_dir base_name img_size rotX rotY rotZ camAngle')
    sys.exit(1)

model_path = argv[0]
texture_path = argv[1] if argv[1] else None
out_dir = argv[2]
base_name = argv[3]
img_size = int(argv[4])
rotX = float(argv[5])
rotY = float(argv[6])
rotZ = float(argv[7]) if len(argv) > 7 else 0.0
camAngle = float(argv[8]) if len(argv) > 8 else 90.0

bpy.ops.wm.read_factory_settings(use_empty=True)
os.makedirs(out_dir, exist_ok=True)

ext = os.path.splitext(model_path)[1].lower()

# Check if FBX is ASCII format (not supported by Blender)
if ext == '.fbx':
    try:
        with open(model_path, 'rb') as f:
            header = f.read(20)
            # ASCII FBX files start with "; FBX"
            if header.startswith(b'; FBX') or header.startswith(b';FBX'):
                print("=" * 80)
                print("ERROR: This FBX file is in ASCII format, which is not supported by Blender.")
                print("Please convert it to BINARY FBX format using one of these methods:")
                print("  1. Autodesk FBX Converter (free download)")
                print("  2. Open in Blender GUI and re-export as Binary FBX")
                print("  3. Use another 3D software to export as Binary FBX")
                print("  4. Try exporting your model as OBJ, GLTF, or GLB instead")
                print("=" * 80)
                sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not check FBX format: {e}")

# Import the model
try:
    if ext == '.obj':
        bpy.ops.import_scene.obj(filepath=model_path)
    elif ext in ('.fbx',):
        bpy.ops.import_scene.fbx(filepath=model_path)
    elif ext in ('.gltf', '.glb'):
        bpy.ops.import_scene.gltf(filepath=model_path)
    else:
        bpy.ops.import_scene.obj(filepath=model_path)
except RuntimeError as e:
    if "ASCII FBX" in str(e):
        print("=" * 80)
        print("ERROR: ASCII FBX format detected!")
        print("Blender only supports BINARY FBX files.")
        print("Please convert your FBX file to binary format or use OBJ/GLTF/GLB instead.")
        print("=" * 80)
    raise

objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not objs:
    print('No mesh found')
    sys.exit(1)

# Reset all armatures to rest pose and clear animation data
print("Checking for animations and armatures...")
for obj in bpy.context.scene.objects:
    # Clear animation data from all objects to prevent animations from affecting render
    if obj.animation_data:
        print(f"Clearing animation data from {obj.name}")
        obj.animation_data_clear()
    
    # For armatures, set to pose mode but don't force rest pose
    # This preserves the model's default/intended pose
    if obj.type == 'ARMATURE':
        print(f"Found armature {obj.name} - keeping current pose")
        # Don't change pose_position - keep whatever pose the model has

# Note: We are NOT applying armature modifiers anymore
# This preserves the model's intended pose (e.g., hands in correct position)
# while still preventing animations from interfering with the render

# Deselect all and reselect mesh objects for joining
bpy.ops.object.select_all(action='DESELECT')

# For GLB/GLTF files with complex hierarchies, don't join - use a parent empty instead
all_imported_objs = [o for o in bpy.context.scene.objects if o.type in ('MESH', 'ARMATURE', 'EMPTY')]

# Create a parent empty to control all imported objects
print("Creating parent empty for rotation control...")
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
root = bpy.context.active_object
root.name = "SpriteRoot"

# Parent all imported objects to this empty
for obj in all_imported_objs:
    if obj != root:
        obj.parent = root
        obj.matrix_parent_inverse = root.matrix_world.inverted()

# Update scene
bpy.context.view_layer.update()

# Force center the model at world origin first
print("Centering model...")
# Calculate bounding box of all children
min_b = [1e9]*3
max_b = [-1e9]*3
for obj in all_imported_objs:
    if obj.type == 'MESH':
        for vert in obj.data.vertices:
            vx = obj.matrix_world @ vert.co
            for i in range(3):
                min_b[i] = min(min_b[i], vx[i])
                max_b[i] = max(max_b[i], vx[i])

# Calculate center offset
center = [(min_b[i] + max_b[i]) / 2.0 for i in range(3)]
print(f"Model center before adjustment: {center}")

# Move the root empty to center the model
root.location = (-center[0], -center[1], -center[2])

if texture_path:
    mat = bpy.data.materials.new(name='SpriteMaterial')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    try:
        img = bpy.data.images.load(texture_path)
    except Exception as e:
        print('Failed to load texture:', e)
        img = None
    if img:
        tex_node.image = img
        mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
    
    # Apply material to all mesh children
    for obj in all_imported_objs:
        if obj.type == 'MESH':
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

cam_data = bpy.data.cameras.new('SpriteCam')
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('SpriteCam', cam_data)
bpy.context.collection.objects.link(cam)
light_data = bpy.data.lights.new(name='KeyLight', type='SUN')
light = bpy.data.objects.new('KeyLight', light_data)
bpy.context.collection.objects.link(light)
light.rotation_euler = (math.radians(50), 0, math.radians(30))

bpy.context.view_layer.update()

# Calculate bounding box from actual mesh vertices for camera setup
print("Calculating model bounds for camera...")
min_b = [1e9]*3
max_b = [-1e9]*3

# Get world-space coordinates of all vertices from all mesh children
for obj in all_imported_objs:
    if obj.type == 'MESH':
        for vert in obj.data.vertices:
            vx = obj.matrix_world @ vert.co
            for i in range(3):
                min_b[i] = min(min_b[i], vx[i])
                max_b[i] = max(max_b[i], vx[i])

# Calculate dimensions (but don't move the model)
dims = [max_b[i] - min_b[i] for i in range(3)]
max_dim = max(dims) if dims else 1.0

print(f"Model dimensions: {dims}")
print(f"Max dimension: {max_dim}")



# Camera setup with adjustable elevation
cam.data.ortho_scale = max_dim*1.8
distance = max_dim*3.0
height = max_dim*0.3  # Much lower height for more side-on view
cam.location = (0.0, -distance, height)
cam.rotation_euler = (math.radians(camAngle), 0, 0)

scene = bpy.context.scene
scene.camera = cam
scene.render.resolution_x = img_size
scene.render.resolution_y = img_size
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = True

DIRECTIONS = [
    ('front', 0),
    ('front_right', 45),
    ('right', 90),
    ('back_right', 135),
    ('back', 180),
    ('back_left', 225),
    ('left', 270),
    ('front_left', 315),
]

for name, ang in DIRECTIONS:
    # Apply full rotation: user corrections (X, Y) + direction angle (Z)
    rotation = (math.radians(rotX), math.radians(rotY), math.radians(ang + rotZ))
    root.rotation_euler = rotation
    bpy.context.view_layer.update()
    print(f"Rendering {name}: rotation = ({rotX}°, {rotY}°, {ang + rotZ}°)")
    fname = os.path.join(out_dir, f"{base_name}_{name}.png")
    scene.render.filepath = bpy.path.abspath(fname)
    bpy.ops.render.render(write_still=True)
    print('Wrote', fname)

