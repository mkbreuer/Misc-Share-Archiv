## simple agregador de 'particulas' / mallas
## copia los objetos seleccionados sobre el objeto activo
## basado en la posicion del cursor y un volumen definido
## permite animar el crecimiento usando un modificador Build
## necesita un Blender r38676 o mas reciente

import bpy, random, time, mathutils
from mathutils import Matrix

def r(n): return (round(random.gauss(0,n),2))

def remover(sel=False):
    bpy.ops.object.editmode_toggle()
    if sel: bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(limit=0.001)
    bpy.ops.object.mode_set()

bpy.types.WindowManager.volX = bpy.props.FloatProperty(name='Volumen X', min=0.1, max=25, default=3, description='Alrededor del cursor')
bpy.types.WindowManager.volY = bpy.props.FloatProperty(name='Volumen Y', min=0.1, max=25, default=3, description='Alrededor del cursor')
bpy.types.WindowManager.volZ = bpy.props.FloatProperty(name='Volumen Z', min=0.1, max=25, default=3, description='Alrededor del cursor')
bpy.types.WindowManager.baseSca = bpy.props.FloatProperty(name='Escala', min=0.01, max=5, default=.1, description='Escala particulas')
bpy.types.WindowManager.varSca = bpy.props.FloatProperty(name='Var', min=0, max=1, default=0, description='Variacion en la Escala particulas')
bpy.types.WindowManager.rotX = bpy.props.FloatProperty(name='Rot Var X', min=0, max=2, default=0, description='Variacion en la Rotacion X particulas')
bpy.types.WindowManager.rotY = bpy.props.FloatProperty(name='Rot Var Y', min=0, max=2, default=0, description='Variacion en la Rotacion Y particulas')
bpy.types.WindowManager.rotZ = bpy.props.FloatProperty(name='Rot Var Z', min=0, max=2, default=1, description='Variacion en la Rotacion Z particulas')
bpy.types.WindowManager.numP = bpy.props.IntProperty(name='Cantidad', min=1, max=1000, default=50, description='Cantidad de particulas')
bpy.types.WindowManager.nor = bpy.props.BoolProperty(name='Orientar con Normales', default=False, description='Alinear eje Z de particulas con las normales del objeto base')
bpy.types.WindowManager.cent = bpy.props.BoolProperty(name='Centrar en las Caras', default=False, description='Utilizar el centro de las caras para ubicar las particulas')
bpy.types.WindowManager.anim = bpy.props.BoolProperty(name='Animar / Sin Materiales', default=False, description='Ordena los indices para reconstruir con un modificador Build / no soporta materiales')
bpy.types.WindowManager.remo = bpy.props.BoolProperty(name='Remover Vertices Dobles', default=False, description='Elimina vertices coincidentes en cada ciclo... es mas lento')


class Agregar(bpy.types.Operator):
    bl_idname = 'object.agregar'
    bl_label = 'Agregar'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return(len(bpy.context.selected_objects) > 1 and bpy.context.object.type == 'MESH')

    def execute(self, context):
        tim = time.time()
        scn = bpy.context.scene
        obj = bpy.context.active_object
        wm = context.window_manager
        mat = Matrix(((1.0, 0.0, 0.0, 0.0),(0.0, 1.0, 0.0, 0.0),(0.0, 0.0, 1.0, 0.0),(0.0, 0.0, 0.0, 1.0)))
        if obj.matrix_world != mat:
            self.report({'WARNING'}, 'Aplicar las transformaciones al objeto base...')
            return{'FINISHED'}
        par = [o for o in bpy.context.selected_objects if o.type == 'MESH' and o != obj]
        if not par: return{'FINISHED'}

        bpy.ops.object.mode_set()
        bpy.ops.object.select_all(action='DESELECT')
        obj.select = True
        msv = []

        for i in range(len(obj.modifiers)):
            msv.append(obj.modifiers[i].show_viewport)
            obj.modifiers[i].show_viewport = False

        cur = scn.cursor_location
        for i in range (wm.numP):
            mes = random.choice(par).data
            x = bpy.data.objects.new('nuevo', mes)
            scn.objects.link(x)
            origen = (r(wm.volX)+cur[0], r(wm.volY)+cur[1], r(wm.volZ)+cur[2])
            cpom = obj.closest_point_on_mesh(origen)

            if wm.cent:
                x.location = obj.data.faces[cpom[2]].center
            else:
                x.location = cpom[0]

            if wm.nor:
                x.rotation_mode = 'QUATERNION'
                x.rotation_quaternion = cpom[1].to_track_quat('Z','Y')
                x.rotation_mode = 'XYZ'
                x.rotation_euler[0] += r(wm.rotX)
                x.rotation_euler[1] += r(wm.rotY)
                x.rotation_euler[2] += r(wm.rotZ)
            else:
                x.rotation_euler = (r(wm.rotX), r(wm.rotY), r(wm.rotZ))

            x.scale = [wm.baseSca + wm.baseSca * r(wm.varSca)] * 3

            if wm.anim:
                x.select = True
                bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', obdata=True)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                tmp = x.data
                num_v = len(obj.data.vertices)
                obj.data.vertices.add(len(tmp.vertices))
                for v in range(len(tmp.vertices)):
                    obj.data.vertices[num_v + v].co = tmp.vertices[v].co
                    if tmp.vertices[v].select:
                        obj.data.vertices[num_v + v].select = True
                num_f = len(obj.data.faces)
                obj.data.faces.add(len(tmp.faces))
                for f in range(len(tmp.faces)):
                    x_fv = tmp.faces[f].vertices
                    o_fv = [i + num_v for i in x_fv]
                    if len(x_fv) == 4: obj.data.faces[num_f + f].vertices_raw = o_fv
                    else: obj.data.faces[num_f + f].vertices = o_fv
                obj.data.update(calc_edges=True)
                scn.update()

                if wm.remo: remover()

                tmp.user_clear()
                bpy.data.meshes.remove(tmp)
                scn.objects.unlink(x)
            else:
                scn.objects.active = obj
                x.select = True
                bpy.ops.object.join()
        
        for i in range(len(msv)): obj.modifiers[i].show_viewport = msv[i]
        for o in par: o.select = True
        obj.select = True

        print ('Tiempo:',round(time.time()-tim,4),'segundos')
        return{'FINISHED'}


class PanelA(bpy.types.Panel):
    bl_label = 'Agregador'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        wm = context.window_manager
        layout = self.layout
        
        column = layout.column(align=True)
        column.prop(wm, 'volX', slider=True)
        column.prop(wm, 'volY', slider=True)
        column.prop(wm, 'volZ', slider=True)
        
        layout.label(text='Particulas:')
        column = layout.column(align=True)
        column.prop(wm, 'baseSca', slider=True)
        column.prop(wm, 'varSca', slider=True)
        
        column = layout.column(align=True)
        column.prop(wm, 'rotX', slider=True)
        column.prop(wm, 'rotY', slider=True)
        column.prop(wm, 'rotZ', slider=True)
        
        column = layout.column(align=True)
        column.prop(wm, 'nor')
        column.prop(wm, 'cent')
        column.prop(wm, 'anim')
        if wm.anim and wm.nor: column.prop(wm, 'remo')
        
        layout.separator()
        layout.prop(wm, 'numP')
        layout.operator('object.agregar')


def register():
    bpy.utils.register_class(Agregar)
    bpy.utils.register_class(PanelA)

def unregister():
    bpy.utils.unregister_class(Agregar)
    bpy.utils.unregister_class(PanelaA)

if __name__ == '__main__':
    register()