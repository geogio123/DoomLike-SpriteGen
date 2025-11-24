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
if ext == '.obj':
    bpy.ops.import_scene.obj(filepath=model_path)
elif ext in ('.fbx',):
    bpy.ops.import_scene.fbx(filepath=model_path)
elif ext in ('.gltf', '.glb'):
    bpy.ops.import_scene.gltf(filepath=model_path)
else:
    bpy.ops.import_scene.obj(filepath=model_path)

objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not objs:
    print('No mesh found')
    sys.exit(1)

ctx = bpy.context.copy()
for o in objs:
    o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
try:
    bpy.ops.object.join()
    root = bpy.context.view_layer.objects.active
except Exception:
    root = objs[0]

bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
root.location = (0,0,0)

# Apply rotation correction
root.rotation_euler = (math.radians(rotX), math.radians(rotY), math.radians(rotZ))

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
    if root.data.materials:
        root.data.materials[0] = mat
    else:
        root.data.materials.append(mat)

cam_data = bpy.data.cameras.new('SpriteCam')
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('SpriteCam', cam_data)
bpy.context.collection.objects.link(cam)
light_data = bpy.data.lights.new(name='KeyLight', type='SUN')
light = bpy.data.objects.new('KeyLight', light_data)
bpy.context.collection.objects.link(light)
light.rotation_euler = (math.radians(50), 0, math.radians(30))

bpy.context.view_layer.update()
min_b = [1e9]*3
max_b = [-1e9]*3
for v in root.bound_box:
    vx = root.matrix_world @ mathutils.Vector(v)
    for i in range(3):
        min_b[i] = min(min_b[i], vx[i])
        max_b[i] = max(max_b[i], vx[i])
dims = [max_b[i]-min_b[i] for i in range(3)]
max_dim = max(dims) if dims else 1.0

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
    root.rotation_euler[2] = math.radians(ang) + math.radians(rotZ)
    bpy.context.view_layer.update()
    fname = os.path.join(out_dir, f"{base_name}_{name}.png")
    scene.render.filepath = bpy.path.abspath(fname)
    bpy.ops.render.render(write_still=True)
    print('Wrote', fname)
