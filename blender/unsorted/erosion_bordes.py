#######################
##  bordes mellados  ##
#######################

distance = 0.33   # edges más largos se cortan
threshold = 0.65  # 0-1 | más bajo -> más daño
noise = 0.005     # mueve un poco la curva
bevel = 0.10      # diámetro base de la curva

import bpy,random,mathutils
from mathutils import Vector
obj = bpy.context.object

if obj and obj.type == 'MESH':

    # hacer una copia de los edges seleccionados
    bpy.ops.object.mode_set()
    bpy.context.tool_settings.mesh_select_mode = [False, True, False]
    bpy.ops.object.mode_set(mode='EDIT')
    if not obj.data.total_edge_sel:
        bpy.ops.mesh.select_random(percent=50)
    bpy.ops.object.mode_set()
    bpy.ops.object.duplicate_move()
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_inverse()
    bpy.ops.mesh.delete(type='EDGE')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete(type='ONLY_FACE')
    bpy.ops.object.editmode_toggle()

    # cortar los edges largos (debería simplificar esto)
    bpy.context.tool_settings.mesh_select_mode = [True, False, False]
    edg = bpy.context.scene.objects.active
    edg.name = 'edge_mesh'
    ver = edg.data.vertices
    for i in range(50):
        go = True
        for i in edg.data.edges:
            d = ver[i.vertices[0]].co - ver[i.vertices[1]].co
            if d.length > distance:
                ver[i.vertices[0]].select = True
                ver[i.vertices[1]].select = True
                go = False
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.subdivide(number_cuts=1, smoothness=0)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle()
        if go: break

    # crear la curva desde los edges
    bpy.ops.object.convert(target='CURVE', keep_original=False)
    bpy.ops.object.editmode_toggle()
    bpy.ops.curve.spline_type_set(type='BEZIER')
    bpy.ops.object.editmode_toggle()
    edg.data.name = 'edge_mesh'
    edg.data.use_fill_front = False
    edg.data.use_fill_back = False
    edg.data.resolution_u = 3
    edg.data.bevel_depth = bevel
    edg.data.bevel_resolution = 2

    # variar el radio de la curva y guardar una copia
    for u in edg.data.splines:
        for v in u.bezier_points:
            v.handle_right_type = 'AUTO'
            v.handle_left_type = 'AUTO'
            v.radius = 0
            if random.random() > threshold:
                v.radius = random.random()
                for i in range(3):
                    v.co[i] += noise*(random.random()*2-1)
    copy = edg.data.copy()
    
    # crear una malla desde la curva
    bpy.ops.object.convert(target='MESH', keep_original=False)
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(limit=0.001)
    bpy.ops.object.editmode_toggle()
    edg.hide = edg.hide_render = True

    # aplicar en un modificador booleano
    erode = obj.modifiers.new('erode', 'BOOLEAN')
    erode.object = edg
    erode.operation = 'DIFFERENCE'
    curve = bpy.data.objects.new('edge_curve',copy)
    bpy.context.scene.objects.link(curve)
    curve.hide = curve.hide_render = True
    bpy.context.scene.objects.active = obj