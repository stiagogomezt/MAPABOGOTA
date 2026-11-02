import bpy, os, math, json, numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HM = os.path.join(ROOT, 'data', 'processed', 'terrain', 'heightmap_blender.png')
SAT = os.path.join(ROOT, 'data', 'processed', 'terrain', 'texture_satellite_4096.jpg')
OUT_MEDIA = os.path.join(ROOT, 'web', 'media')
OUT_DATA = os.path.join(ROOT, 'data', 'processed', 'terrain')
os.makedirs(OUT_MEDIA, exist_ok=True)

# Scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 900  # 30s

# Heightmap image
img = bpy.data.images.load(HM)
W, H = img.size[0], img.size[1]

# Terrain plane
bpy.ops.mesh.primitive_plane_add(size=2, location=(0,0,0))
plane = bpy.context.active_object
plane.name = 'Terrain'
# subdivide
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.subdivide(number_cuts=W-1)
# Actually subdivide to grid W x H is too many; use a grid primitive instead
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.delete()
# downsample grid
W = 512; H = 605
bpy.ops.mesh.primitive_grid_add(x_subdivisions=W-1, y_subdivisions=H-1, size=2, location=(0,0,0))
plane = bpy.context.active_object
plane.name = 'Terrain'

# Scale to real meters: 55000 x 65000, centered at origin
scale_x = 55000.0/2.0
scale_y = 65000.0/2.0
plane.scale = (scale_x, scale_y, 1.0)
bpy.ops.object.transform_apply(scale=True)

# Displace modifier using heightmap
tex = bpy.data.textures.new('HeightTex', type='IMAGE')
tex.image = img
disp = plane.modifiers.new(name='Displace', type='DISPLACE')
disp.texture = tex
disp.texture_coords = 'UV'
disp.strength = 2522.66 * 1.5  # height range * exaggeration
disp.mid_level = 0.0

# UV map
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.uv.unwrap(method='ANGLE_BASED')
bpy.ops.object.mode_set(mode='OBJECT')

# Material with satellite texture
mat = bpy.data.materials.new(name='TerrainMat')
mat.use_nodes = True
bsdf = mat.node_tree.nodes['Principled BSDF']
texnode = mat.node_tree.nodes.new('ShaderNodeTexImage')
sat_img = bpy.data.images.load(SAT)
texnode.image = sat_img
mat.node_tree.links.new(texnode.outputs['Color'], bsdf.inputs['Base Color'])
plane.data.materials.append(mat)

# Camera
bpy.ops.object.camera_add(location=(0, -35000, 8000))
cam = bpy.context.active_object
cam.name = 'Camera'
scene.camera = cam

# Sun light
bpy.ops.object.light_add(type='SUN', location=(10000, -10000, 5000))
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(35), 0, math.radians(250))

# World background dark
world = bpy.data.worlds.new('World')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']
bg.inputs[0].default_value = (0.02, 0.02, 0.04, 1.0)
bg.inputs[1].default_value = 0.5

# Fog (mist)
scene.eevee.use_volumetric_shadows = True

# Camera animation: keyframes at frames 1, 338, 675, 1013, 1350
# Positions (x,y,z) in meters, origin center
keyframes = [
 (1, (0, -32000, 6000), (0, 0, 2000)),
 (225, (15000, -10000, 4000), (5000, 0, 2500)),
 (450, (5000, 5000, 2500), (0, 0, 2600)),
 (675, (-5000, 10000, 3000), (-10000, 5000, 2600)),
 (900, (0, 28000, 7000), (0, 25000, 2600)),
]
for frame, loc, target in keyframes:
    scene.frame_set(frame)
    cam.location = Vector(loc)
    # point camera at target
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert(data_path='location')
    cam.keyframe_insert(data_path='rotation_euler')

# Render output
frames_dir = os.path.join(OUT_MEDIA, 'frames')
os.makedirs(frames_dir, exist_ok=True)
scene.render.filepath = os.path.join(frames_dir, 'frame_')
scene.render.image_settings.file_format = 'PNG'

# Save camera path JSON
camera_path = []
for f in range(1, scene.frame_end+1):
    scene.frame_set(f)
    loc = cam.location
    # target approximated by forward direction
    camera_path.append({'frame': f, 'position': [loc.x, loc.y, loc.z], 'rotation': [cam.rotation_euler.x, cam.rotation_euler.y, cam.rotation_euler.z]})
with open(os.path.join(OUT_DATA, 'camera_path.json'), 'w') as fh:
    json.dump(camera_path, fh)
print('camera path saved')

# Decimate and export GLB
bpy.ops.object.select_all(action='DESELECT')
plane.select_set(True)
bpy.context.view_layer.objects.active = plane
# apply modifiers
bpy.ops.object.modifier_apply(modifier='Displace')
# decimate
dec = plane.modifiers.new(name='Decimate', type='DECIMATE')
dec.ratio = 0.1
bpy.ops.object.modifier_apply(modifier='Decimate')
# export GLB with Draco
glb_path = os.path.join(OUT_DATA, 'terrain.glb')
bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB', export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6)
print('glb exported', glb_path)

# Render (background)
bpy.ops.render.render(animation=True)
print('render done')
EOF