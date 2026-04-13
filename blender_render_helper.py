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
unlit_color_hex = argv[9] if len(argv) > 9 and argv[9] != "None" else ""
flip_fb = argv[10] == 'True' if len(argv) > 10 else False
flip_lr = argv[11] == 'True' if len(argv) > 11 else False

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) != 6:
        return (0.0, 0.0, 0.0, 1.0)
    # Convert sRGB to linear for Blender rendering
    return tuple((int(hex_str[i:i+2], 16)/255.0)**2.2 for i in (0, 2, 4)) + (1.0,)

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
        # Connect alpha for transparency
        mat.node_tree.links.new(tex_node.outputs['Alpha'], bsdf.inputs['Alpha'])
    
    # Setup EEVEE transparency modes for the new material
    mat.blend_method = 'CLIP'
    mat.shadow_method = 'CLIP'
    
    # Apply material to all mesh children
    for obj in all_imported_objs:
        if obj.type == 'MESH':
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
else:
    # If no texture override, ensure existing materials on the model account for transparency
    # Many importers default to 'OPAQUE' even if textures have alpha
    for obj in all_imported_objs:
        if obj.type == 'MESH':
            for m in obj.data.materials:
                if m:
                    m.blend_method = 'CLIP'
                    m.shadow_method = 'CLIP'

if unlit_color_hex:
    unlit_rgb = hex_to_rgb(unlit_color_hex)
    for obj in all_imported_objs:
        if obj.type == 'MESH':
            for m in obj.data.materials:
                if m and m.use_nodes:
                    if m.node_tree.nodes.get('UnlitMix'):
                        continue
                    bsdf = m.node_tree.nodes.get('Principled BSDF')
                    if bsdf:
                        color_link = None
                        for link in m.node_tree.links:
                            if link.to_node == bsdf and link.to_socket.name == 'Base Color':
                                color_link = link
                                break
                        
                        color_source_socket = None
                        if color_link:
                            color_source_socket = color_link.from_socket
                        else:
                            rgb_val = bsdf.inputs['Base Color'].default_value
                            rgb_node = m.node_tree.nodes.new('ShaderNodeRGB')
                            rgb_node.outputs[0].default_value = rgb_val
                            color_source_socket = rgb_node.outputs[0]

                        if color_source_socket:
                            emission = m.node_tree.nodes.new('ShaderNodeEmission')
                            emission.name = 'UnlitEmission'
                            m.node_tree.links.new(color_source_socket, emission.inputs['Color'])
                            
                            dist = m.node_tree.nodes.new('ShaderNodeVectorMath')
                            dist.operation = 'DISTANCE'
                            dist.inputs[1].default_value = (unlit_rgb[0], unlit_rgb[1], unlit_rgb[2])
                            m.node_tree.links.new(color_source_socket, dist.inputs[0])
                            
                            compare = m.node_tree.nodes.new('ShaderNodeMath')
                            compare.operation = 'LESS_THAN'
                            compare.inputs[1].default_value = 0.05
                            m.node_tree.links.new(dist.outputs['Value'], compare.inputs[0])
                            
                            mix = m.node_tree.nodes.new('ShaderNodeMixShader')
                            mix.name = 'UnlitMix'
                            
                            output_node = None
                            for link in m.node_tree.links:
                                if link.from_node == bsdf:
                                    output_node = link.to_node
                                    break
                                    
                            if output_node:
                                m.node_tree.links.new(compare.outputs['Value'], mix.inputs['Fac'])
                                m.node_tree.links.new(bsdf.outputs['BSDF'], mix.inputs[1])
                                m.node_tree.links.new(emission.outputs['Emission'], mix.inputs[2])
                                m.node_tree.links.new(mix.outputs['Shader'], output_node.inputs['Surface'])


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
    # Handle name flipping to reverse views
    out_name = name
    if flip_fb:
        if 'front' in out_name:
            out_name = out_name.replace('front', 'TMP_BACK')
        elif 'back' in out_name:
            out_name = out_name.replace('back', 'front')
        out_name = out_name.replace('TMP_BACK', 'back')
    if flip_lr:
        if 'left' in out_name:
            out_name = out_name.replace('left', 'TMP_RIGHT')
        elif 'right' in out_name:
            out_name = out_name.replace('right', 'left')
        out_name = out_name.replace('TMP_RIGHT', 'right')

    # Apply full rotation: user corrections (X, Y) + direction angle (Z)
    rotation = (math.radians(rotX), math.radians(rotY), math.radians(ang + rotZ))
    root.rotation_euler = rotation
    bpy.context.view_layer.update()
    print(f"Rendering {name} (saved as {out_name}): rotation = ({rotX}°, {rotY}°, {ang + rotZ}°)")
    fname = os.path.join(out_dir, f"{base_name}_{out_name}.png")
    scene.render.filepath = bpy.path.abspath(fname)
    bpy.ops.render.render(write_still=True)
    print('Wrote', fname)

