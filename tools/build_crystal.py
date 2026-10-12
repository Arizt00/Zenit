"""Reproducible Blender source + compact mesh for the live Babylon crystal.

Run: blender --background --python tools/build_crystal.py
The application consumes geometry, not a rendered image or video.
"""
import bpy,json,math,struct,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'web/assets';SOURCE=ROOT/'design';ASSETS.mkdir(exist_ok=True);SOURCE.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.film_transparent=True
scene.view_settings.view_transform='AgX'
glass=bpy.data.materials.new('Zenit optical glass');glass.use_nodes=True;bsdf=glass.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=(.86,.79,1,1);bsdf.inputs['Roughness'].default_value=.055;bsdf.inputs['IOR'].default_value=1.46;bsdf.inputs['Transmission Weight'].default_value=.96
if 'Coat Weight' in bsdf.inputs:bsdf.inputs['Coat Weight'].default_value=.22
if 'Thin Film Thickness' in bsdf.inputs:bsdf.inputs['Thin Film Thickness'].default_value=410
if 'Thin Film IOR' in bsdf.inputs:bsdf.inputs['Thin Film IOR'].default_value=1.32
meshes=[]
for name,radius in [('Crystal outer wall',1.375),('Crystal inner wall',1.337)]:
 bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64,radius=radius);obj=bpy.context.object;obj.name=name;obj.data.materials.append(glass)
 for face in obj.data.polygons:face.use_smooth=True
 obj.data.calc_loop_triangles();meshes.append(obj)
world=scene.world or bpy.data.worlds.new('Quiet studio');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.80,.83,.97,1);world.node_tree.nodes['Background'].inputs[1].default_value=.28
for name,location,color,energy,size in [('Upper softbox',(-3,-4,4),(1,.94,.98),900,3),('Cyan fill',(3,-2,-1),(.65,.88,1),550,2),('Rose rim',(2,1,3),(1,.64,.88),650,2.5)]:
 bpy.ops.object.light_add(type='AREA',location=location);light=bpy.context.object;light.name=name;light.data.color=color;light.data.energy=energy;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(0,-7,1.1));camera=bpy.context.object;camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=3.45;scene.camera=camera
chunks=[];metadata={'generator':'Blender '+bpy.app.version_string,'coordinateSystem':'Babylon right-handed Y-up','meshes':[],'material':{'ior':1.46,'roughness':.055,'outerRadius':1.375,'innerRadius':1.337},'source':'design/zenit-crystal.blend'};offset=0
for obj in meshes:
 positions=[c for vertex in obj.data.vertices for c in (vertex.co.x,vertex.co.z,-vertex.co.y)]
 normals=[c for vertex in obj.data.vertices for c in (vertex.normal.x,vertex.normal.z,-vertex.normal.y)]
 indices=[i for triangle in obj.data.loop_triangles for i in triangle.vertices]
 item={'name':obj.name,'vertices':len(obj.data.vertices),'triangles':len(indices)//3}
 for key,values,fmt in [('positions',positions,'f'),('normals',normals,'f'),('indices',indices,'I')]:
  data=struct.pack('<'+fmt*len(values),*values);item[key]={'byteOffset':offset,'count':len(values)};chunks.append(data);offset+=len(data)
 metadata['meshes'].append(item)
binary=b''.join(chunks);metadata['byteLength']=len(binary);metadata['sha256']=hashlib.sha256(binary).hexdigest()
(ASSETS/'zenit-crystal.mesh.bin').write_bytes(binary);(ASSETS/'zenit-crystal.mesh.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'zenit-crystal.blend'))
print('ZENIT_CRYSTAL',json.dumps(metadata))
