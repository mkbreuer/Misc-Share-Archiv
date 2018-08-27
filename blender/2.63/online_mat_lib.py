# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENSE BLOCK *****

bl_info = {
    "name": "Online Material Library",
    "author": "Peter Cassetta",
    "version": (0, 1),
    "blender": (2, 6, 3),
    "location": "Properties > Material > Online Material Library",
    "description": "Browse and download materials from a online CC0 library.",
    "warning": "Alpha version",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Material"}

import bpy
import http.client

library = "testing"

mat_lib_contents = "Please refresh."
mat_lib_category_filenames = []
mat_lib_category_types = []
mat_lib_category_names = []
mat_lib_categories = 0

category_enum_items = [("None0", "None", "No Category Selected")]
bpy.types.Scene.material_category = bpy.props.EnumProperty(name = "", items = category_enum_items, description = "Choose a category")

subcategory_enum_items = [("None0", "None", "No Subcategory Selected")]
bpy.types.Scene.material_subcategory = bpy.props.EnumProperty(name = "", items = subcategory_enum_items, description = "Choose a subcategory")

category_contents = "None"
category_name = ""
category_filename = ""
category_materials = 0

category_type = "none"

parent_category_contents = "None"
parent_category_name = ""
parent_category_filename = ""
parent_category_categories = 0
parent_category_names = []
parent_category_filenames = []

material_names = []
material_filenames = []
material_contributors = []
material_ratings = []
material_file_contents = ""

current_material_number = -1

show_success_message = True
show_success_message_timeout = 0

indicator_message = "Alpha version"
indicator_icon = 'INFO'
indicator_default_message = "Alpha version"
indicator_default_icon = 'INFO'

class OnlineMaterialLibraryPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Online Material Library"
    bl_idname = "OnlineMaterialLibraryPanel"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    
    def draw(self, context):
        global show_success_message
        global show_success_message_timeout
        global indicator_message
        global indicator_icon
        global current_material_number
        
        layout = self.layout
        
        if str(context.scene.render.engine) == "CYCLES":
            #Cycles is enabled!
            row = layout.row()
            
            #Main Indicator
            row.label(text=indicator_message, icon=indicator_icon)
            
            if mat_lib_contents == "" or mat_lib_contents == "Please refresh.":
                #Material Library Contents variable is empty -- ask user to refresh
                indicator_message = "Please refresh."
                indicator_icon = 'ERROR'
                row.operator("material.refreshlibrary",text="Refresh",icon="FILE_REFRESH")
            else:
                #Material Library variable has contents
                row.operator("material.refreshlibrary",text="Refresh",icon="FILE_REFRESH")
                row = layout.row()
                
                if mat_lib_contents[:7] == "mat-lib":
                    #We have a valid material library
                    if category_contents == "None":
                        if show_success_message:
                            if show_success_message_timeout < 15:
                                show_success_message_timeout = show_success_message_timeout + 1
                                indicator_message = "Retrieved library!"
                                indicator_icon = 'FILE_TICK'
                            else:
                                show_success_message = False
                                indicator_message = indicator_default_message
                                indicator_icon = indicator_default_icon
                    
                    if category_type == "none":
                        #Not browsing category
                        
                        row = layout.row(align=True)
                        row.alignment = 'EXPAND'
                        row.prop(bpy.context.scene, "material_category")
                        
                        if bpy.context.scene.material_category != category_enum_items[0][0]:
                            i = 0
                            while i < len(category_enum_items):
                                if category_enum_items[i][0] == bpy.context.scene.material_category:
                                    browse_button = row.operator("material.opencategory", text="", icon='FORWARD', emboss=True)
                                    browse_button.filename = mat_lib_category_filenames[i - 1]
                                    browse_button.name = mat_lib_category_names[i - 1]
                                i = i + 1
                        
                        row = layout.row()
                        row.label(text="%d categories in library." % mat_lib_categories)
                        
                    elif category_type == "category":
                        row = layout.row(align=True)
                        row.alignment = 'EXPAND'
                        row.prop(bpy.context.scene, "material_category")
                        
                        if bpy.context.scene.material_category == category_enum_items[0][0]:
                            browse_button = row.operator("material.closecategory", text="", icon='LOOP_BACK', emboss=True)
                        else:
                            i = 0
                            while i < len(category_enum_items):
                                if category_enum_items[i][0] == bpy.context.scene.material_category:
                                    browse_button = row.operator("material.opencategory", text="", icon='FORWARD', emboss=True)
                                    browse_button.filename = mat_lib_category_filenames[i - 1]
                                    browse_button.name = mat_lib_category_names[i - 1]
                                i = i + 1
                        
                        #Materials
                        row = layout.row()
                        matwrap = row.box()
                        i = 0
                        while i < category_materials:
                            if (i == current_material_number):
                                matwraprow = matwrap.row()
                                matwrapbox = matwraprow.box()
                                matwrapboxrow = matwrapbox.row()
                                matwrapboxrow.operator("material.viewmaterial", text=material_names[i], icon='MATERIAL', emboss=False).material = i
                                matwrapboxrowcol = matwrapboxrow.column()
                                matwrapboxrowcolrow = matwrapboxrowcol.row()
                                matwrapboxrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapboxrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapboxrowcol = matwrapboxrow.column()
                                matwrapboxrowcolrow = matwrapboxrowcol.row()
                                matwrapboxrowcolrowsplit = matwrapboxrowcolrow.split(percentage=0.8)
                                matwrapboxrowcolrowsplitrow = matwrapboxrowcolrowsplit.row()
                                
                                #Ratings
                                e = 0
                                while e < material_ratings[i]:
                                    matwrapboxrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_ON', emboss=False).material = i
                                    e = e + 1
                                
                                if material_ratings[i] is not 5:    
                                    e = 0
                                    while e < (5 - material_ratings[i]):
                                        matwrapboxrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_OFF', emboss=False).material = i
                                        e = e + 1
                            else:
                                matwraprow = matwrap.row()
                                matwrapcol = matwraprow.column()
                                matwrapcolrow = matwrapcol.row()
                                matwrapcolrow.operator("material.viewmaterial", text=material_names[i], icon='MATERIAL', emboss=False).material = i
                                matwrapcolrowcol = matwrapcolrow.column()
                                matwrapcolrowcolrow = matwrapcolrowcol.row()
                                matwrapcolrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapcolrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapcolrowcol = matwrapcolrow.column()
                                matwrapcolrowcolrow = matwrapcolrowcol.row()
                                matwrapcolrowcolrowsplit = matwrapcolrowcolrow.split(percentage=0.8)
                                matwrapcolrowcolrowsplitrow = matwrapcolrowcolrowsplit.row()
                                
                                #Ratings
                                e = 0
                                while e < material_ratings[i]:
                                    matwrapcolrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_ON', emboss=False).material = i
                                    e = e + 1
                                
                                if material_ratings[i] is not 5:    
                                    e = 0
                                    while e < (5 - material_ratings[i]):
                                        matwrapcolrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_OFF', emboss=False).material = i
                                        e = e + 1
                            i = i + 1
                        
                        if current_material_number is not -1:
                            #Display selected material's info
                            row = layout.row()
                            infobox = row.box()
                            inforow = infobox.row()
                            
                            inforow.label(text=material_names[current_material_number])
                            inforow.operator("material.viewmaterial", text="", icon='PANEL_CLOSE').material = -1
                            inforow = infobox.row()
                            
                            #Display a preview
                            if bpy.data.textures.find("mat_lib_preview_texture") == -1:
                                bpy.data.textures.new("mat_lib_preview_texture", "IMAGE")
                                preview_texture = bpy.data.textures["mat_lib_preview_texture"]
                                inforowcol = inforow.column(align=True)
                                inforowcol.alignment = 'EXPAND'
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.operator("material.downloadpreview", text="Download Preview", icon='IMAGE_COL')
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.template_preview(preview_texture)
                            else:
                                preview_texture = bpy.data.textures['mat_lib_preview_texture']
                                inforowcol = inforow.column(align=True)
                                inforowcol.alignment = 'EXPAND'
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.operator("material.downloadpreview", text="Download Preview", icon='IMAGE_COL')
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.template_preview(preview_texture)
                            
                            inforowcol = inforow.column()
                            inforowcolrow = inforowcol.row()
                            if bpy.data.materials.find(material_names[current_material_number]) is not -1:
                                inforowcolrow.label(text="Material exists", icon='ERROR')
                            if material_contributors[current_material_number] == "Unknown" or material_contributors[current_material_number] == "Anonymous":
                                inforowcolrow = inforowcol.row()
                            else:
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.label(text="By %s." % material_contributors[current_material_number])
                                inforowcolrow = inforowcol.row()
                            if bpy.data.materials.find(material_names[current_material_number]) is not -1:
                                inforowcolrow.label(text="\"Add\" will overwrite.")
                            inforowcolcol = inforowcol.column(align=True)
                            inforowcolcol.alignment = 'EXPAND'
                            
                            
                            #Display "Add" or "Overwrite" button
                            mat_button = inforowcolcol.operator("material.libraryadd", text="Add", icon='ZOOMIN')
                            mat_button.name = material_names[current_material_number]
                            mat_button.filename = material_filenames[current_material_number]
                            mat_button.library = library
                            
                            #Display "Paste" button
                            mat_button = inforowcolcol.operator("material.download", text="Paste to active", icon='PASTEDOWN')
                            mat_button.name = bpy.context.object.active_material.name
                            mat_button.filename = material_filenames[current_material_number]
                            mat_button.library = library
                            
                            #Display "Save" button
                            mat_button = inforowcolcol.operator("material.librarysave", text="Save", icon='DISK_DRIVE')
                            mat_button.name = bpy.context.object.active_material.name
                            mat_button.filename = material_filenames[current_material_number]
                            mat_button.library = library
                    
                    elif category_type == "subcategory":
                        row = layout.row(align=True)
                        row.alignment = 'EXPAND'
                        row.prop(bpy.context.scene, "material_category")
                        row.prop(bpy.context.scene, "material_subcategory")
                        #Browsing a category
                        row.operator("material.closecategory", text="", icon='LOOP_BACK')
                        
                        #Materials
                        row = layout.row()
                        matwrap = row.box()
                        i = 0
                        while i < category_materials:
                            if (i == current_material_number):
                                matwraprow = matwrap.row()
                                matwrapbox = matwraprow.box()
                                matwrapboxrow = matwrapbox.row()
                                matwrapboxrow.operator("material.viewmaterial", text=material_names[i], icon='MATERIAL', emboss=False).material = i
                                matwrapboxrowcol = matwrapboxrow.column()
                                matwrapboxrowcolrow = matwrapboxrowcol.row()
                                matwrapboxrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapboxrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapboxrowcol = matwrapboxrow.column()
                                matwrapboxrowcolrow = matwrapboxrowcol.row()
                                matwrapboxrowcolrowsplit = matwrapboxrowcolrow.split(percentage=0.8)
                                matwrapboxrowcolrowsplitrow = matwrapboxrowcolrowsplit.row()
                                
                                #Ratings
                                e = 0
                                while e < material_ratings[i]:
                                    matwrapboxrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_ON', emboss=False).material = i
                                    e = e + 1
                                
                                if material_ratings[i] is not 5:    
                                    e = 0
                                    while e < (5 - material_ratings[i]):
                                        matwrapboxrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_OFF', emboss=False).material = i
                                        e = e + 1
                            else:
                                matwraprow = matwrap.row()
                                matwrapcol = matwraprow.column()
                                matwrapcolrow = matwrapcol.row()
                                matwrapcolrow.operator("material.viewmaterial", text=material_names[i], icon='MATERIAL', emboss=False).material = i
                                matwrapcolrowcol = matwrapcolrow.column()
                                matwrapcolrowcolrow = matwrapcolrowcol.row()
                                matwrapcolrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapcolrowcolrow.operator("material.viewmaterial", text="", icon='BLANK1', emboss=False).material = i
                                matwrapcolrowcol = matwrapcolrow.column()
                                matwrapcolrowcolrow = matwrapcolrowcol.row()
                                matwrapcolrowcolrowsplit = matwrapcolrowcolrow.split(percentage=0.8)
                                matwrapcolrowcolrowsplitrow = matwrapcolrowcolrowsplit.row()
                                
                                #Ratings
                                e = 0
                                while e < material_ratings[i]:
                                    matwrapcolrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_ON', emboss=False).material = i
                                    e = e + 1
                                
                                if material_ratings[i] is not 5:    
                                    e = 0
                                    while e < (5 - material_ratings[i]):
                                        matwrapcolrowcolrowsplitrow.operator("material.viewmaterial", text="", icon='SOLO_OFF', emboss=False).material = i
                                        e = e + 1
                            i = i + 1
                        
                        if current_material_number is not -1:
                            #Display selected material's info
                            row = layout.row()
                            infobox = row.box()
                            inforow = infobox.row()
                            
                            inforow.label(text=material_names[current_material_number])
                            inforow.operator("material.viewmaterial", text="", icon='PANEL_CLOSE').material = -1
                            inforow = infobox.row()
                            
                            ##Display a preview
                            if bpy.data.textures.find("mat_lib_preview_texture") == -1:
                                bpy.data.textures.new("mat_lib_preview_texture", "IMAGE")
                                preview_texture = bpy.data.textures["mat_lib_preview_texture"]
                                inforowcol = inforow.column(align=True)
                                inforowcol.alignment = 'EXPAND'
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.operator("material.downloadpreview", text="Download Preview", icon='IMAGE_COL')
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.template_preview(preview_texture)
                            else:
                                preview_texture = bpy.data.textures['mat_lib_preview_texture']
                                inforowcol = inforow.column(align=True)
                                inforowcol.alignment = 'EXPAND'
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.operator("material.downloadpreview", text="Download Preview", icon='IMAGE_COL')
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.template_preview(preview_texture)
                            
                            inforowcol = inforow.column()
                            inforowcolrow = inforowcol.row()
                            if bpy.data.materials.find(material_names[current_material_number]) is not -1:
                                inforowcolrow.label(text="Material exists", icon='ERROR')
                            if material_contributors[current_material_number] == "Unknown" or material_contributors[current_material_number] == "Anonymous":
                                inforowcolrow = inforowcol.row()
                            else:
                                inforowcolrow = inforowcol.row()
                                inforowcolrow.label(text="By %s." % material_contributors[current_material_number])
                                inforowcolrow = inforowcol.row()
                            if bpy.data.materials.find(material_names[current_material_number]) is not -1:
                                inforowcolrow.label(text="\"Add\" will overwrite.")
                            inforowcolcol = inforowcol.column(align=True)
                            inforowcolcol.alignment = 'EXPAND'
                            
                            
                            #Display "Add" or "Overwrite" button
                            mat_button = inforowcolcol.operator("material.libraryadd", text="Add to materials", icon='ZOOMIN')
                            mat_button.name = material_names[current_material_number]
                            mat_button.filename = material_filenames[current_material_number]
                            mat_button.library = library
                            
                            #Display "Paste" button
                            mat_button = inforowcolcol.operator("material.download", text="Apply to active", icon='PASTEDOWN')
                            mat_button.name = bpy.context.object.active_material.name
                            mat_button.filename = material_filenames[current_material_number]
                            mat_button.library = library
                            
                            #Display "Save" button
                            mat_button = inforowcolcol.operator("material.librarysave", text="Save", icon='DISK_DRIVE')
                            mat_button.name = bpy.context.object.active_material.name
                            mat_button.filename = material_filenames[current_material_number]
                            mat_button.library = library
                    
                    elif category_type == "parent":
                        row = layout.row(align=True)
                        row.alignment = 'EXPAND'
                        row.prop(bpy.context.scene, "material_category")
                        
                        if bpy.context.scene.material_category != category_enum_items[0][0]:
                            i = 0
                            while i < len(category_enum_items):
                                if category_enum_items[i][0] == bpy.context.scene.material_category:
                                    browse_button = row.operator("material.opencategory", text="", icon='FORWARD', emboss=True)
                                    browse_button.filename = mat_lib_category_filenames[i - 1]
                                    browse_button.name = mat_lib_category_names[i - 1]
                                i = i + 1
                        else:
                            browse_button = row.operator("material.closecategory", text="", icon='LOOP_BACK', emboss=True)
                            browse_button.filename = mat_lib_category_filenames[i - 1]
                            browse_button.name = mat_lib_category_names[i - 1]
                        
                        #Browsing a category
                        row = layout.row()
                        row.label(text="%d sub-categories in category." % parent_category_categories)
                        row.operator("material.closecategory", text="", icon='LOOP_BACK')
                        
                        #Create labels with category names
                        row = layout.row()
                        box = row.box()
                                                
                        i = 0
                        while i < parent_category_categories:
                            subrow = box.row()
                            browse_button = subrow.operator("material.opencategory", text=parent_category_names[i] , icon='FILE_TEXT', emboss=False)
                            browse_button.filename = parent_category_filenames[i]
                            browse_button.name = parent_category_names[i]
                            browse_button = subrow.operator("material.opencategory", text="", icon='FORWARD', emboss=False)
                            browse_button.filename = parent_category_filenames[i]
                            browse_button.name = parent_category_names[i]
                            i = i + 1
                else:
                    #We do not have a valid material library. Bummer. 
                    row.label(text="Could not retrieve material library.", icon='CANCEL')
                    row = layout.row()
                    row.label(text=mat_lib_contents)
        else:
            #Dude, you gotta switch to Cycles to use this.
            row = layout.row()
            row.label(text="Sorry, Cycles only at the moment.",icon='ERROR')

class RefreshLibrary(bpy.types.Operator):
    '''Refresh Material Library'''
    bl_idname = "material.refreshlibrary"
    bl_label = "Connect to peter.cassetta.info"

    def execute(self, context):
        global mat_lib_contents
        global mat_lib_categories
        global mat_lib_category_names
        global mat_lib_category_types
        global mat_lib_category_filenames
        
        global category_enum_items
        global subcategory_enum_items
        
        global show_success_message
        global show_success_message_timeout
        
        #Connect and download
        connection = http.client.HTTPConnection("peter.cassetta.info")
        
        if library == "release":
            connection.request("GET", "/material-library/release/index.txt")
        else:
            connection.request("GET", "/material-library/testing/index.txt")
        
        #Format nicely
        mat_lib_contents = str(connection.getresponse().read()).replace("b'\\xef\\xbb\\xbf",'')[:-1]
        
        #Find category names
        mat_lib_category_names = eval(mat_lib_contents[(mat_lib_contents.index('[names]') + 7):mat_lib_contents.index('[/names]')])
        
        #Find category types
        mat_lib_category_types = eval(mat_lib_contents[(mat_lib_contents.index('[types]') + 7):mat_lib_contents.index('[/types]')])
        
        #Get category filenames
        mat_lib_category_filenames = eval(mat_lib_contents[(mat_lib_contents.index('[filenames]') + 11):mat_lib_contents.index('[/filenames]')])
        
        #Find amount of categories
        mat_lib_categories = len(mat_lib_category_names)
        
        #Set enum items for category dropdown
        category_enum_items = [("None0", "None", "No Category Selected")]
        
        i = 0
        while i < mat_lib_categories:
            category_enum_items.append(((mat_lib_category_names[i] + str(i + 1)), mat_lib_category_names[i], (mat_lib_category_names[i] + " category")))
            i = i + 1
        bpy.types.Scene.material_category = bpy.props.EnumProperty(name = "", items = category_enum_items, description = "Choose a category")
            
            
        self.report({'INFO'}, "Retrieved library!")
        show_success_message = True
        show_success_message_timeout = 0
        
        return {'FINISHED'}

class OpenMaterialCategory(bpy.types.Operator):
    '''Open specified material category'''
    bl_idname = "material.opencategory"
    bl_label = "open specified material category"
    name = bpy.props.StringProperty()
    filename = bpy.props.StringProperty()
    
    def execute(self, context):
        global category_contents
        global category_name
        global category_filename
        global category_materials
        
        global category_type
        
        global parent_category_contents
        global parent_category_name
        global parent_category_filename
        global parent_category_categories
        global parent_category_names
        global parent_category_filenames
        
        global material_names
        global material_filenames
        global material_contributors
        global material_ratings
        
        global show_success_message_timeout
        global show_success_message
        global indicator_message
        global indicator_icon
        
        global current_material_number
                
        connection = http.client.HTTPConnection("peter.cassetta.info")
        
        if category_type == "parent":
            if library == "release":
                connection.request("GET", "/material-library/release/" + parent_category_filename + "/" + self.filename + "/index.txt")
            else:
                connection.request("GET", "/material-library/testing/" + parent_category_filename + "/" + self.filename + "/index.txt")
        else:
            if library == "release":
                connection.request("GET", "/material-library/release/" + self.filename + "/index.txt")
            else:
                connection.request("GET", "/material-library/testing/" + self.filename + "/index.txt")
        
        #Format nicely
        response = str(connection.getresponse().read()).replace("b'\\xef\\xbb\\xbf",'')[:-1]
        
        if response[0:6] == "parent":
            parent_category_contents = response
        else:
            category_contents = response
        
        #Check file for validitity
        if response[0:8] == "category":
            current_material_number = -1
            
            #Get material names
            material_names = eval(category_contents[(category_contents.index("[names]") + 7):category_contents.index("[/names]")])
            
            #Get material filenames
            material_filenames = eval(category_contents[(category_contents.index("[filenames]") + 11):category_contents.index("[/filenames]")])
            
            #Get material contributors
            material_contributors = eval(category_contents[(category_contents.index("[contributors]") + 14):category_contents.index("[/contributors]")])
            
            #Get material ratings
            material_ratings = eval(category_contents[(category_contents.index("[ratings]") + 9):category_contents.index("[/ratings]")])
            
            #Set category name for header
            category_name = self.name
            
            #Set category filename for refresh button
            category_filename = self.filename
            
            #Set amount of materials in selected category
            category_materials = len(material_names)
        
            if show_success_message_timeout < 15:
                show_success_message_timeout = 15
                show_success_message = False
                indicator_message = indicator_default_message
                indicator_icon = indicator_default_icon
            
            category_type = "category"
        
        elif response[0:6] == "parent":
            current_material_number = -1
            
            #Find category names
            parent_category_names = eval(parent_category_contents[(parent_category_contents.index('[names]') + 7):parent_category_contents.index('[/names]')])
            
            #Get category filenames
            parent_category_filenames = eval(parent_category_contents[(parent_category_contents.index('[filenames]') + 11):parent_category_contents.index('[/filenames]')])
            
            #Set parent category name for header
            parent_category_name = self.name
            
            #Set parent category filename
            parent_category_filename = self.filename
            
            #Set amount of categories in parent category
            parent_category_categories = len(parent_category_names)
            
            if show_success_message_timeout < 15:
                show_success_message_timeout = 15
                show_success_message = False
                indicator_message = indicator_default_message
                indicator_icon = indicator_default_icon
            
            category_type = "parent"
        
        elif response[0:11] == "subcategory":
            current_material_number = -1
            
            #Get material names
            material_names = eval(category_contents[(category_contents.index("[names]") + 7):category_contents.index("[/names]")])
            
            #Get material filenames
            material_filenames = eval(category_contents[(category_contents.index("[filenames]") + 11):category_contents.index("[/filenames]")])
            
            #Get material contributors
            material_contributors = eval(category_contents[(category_contents.index("[contributors]") + 14):category_contents.index("[/contributors]")])
            
            #Get material ratings
            material_ratings = eval(category_contents[(category_contents.index("[ratings]") + 9):category_contents.index("[/ratings]")])
            
            #Set category name for header
            category_name = self.name
            
            #Set category filename for refresh button
            category_filename = self.filename
            
            #Set amount of materials in selected category
            category_materials = len(material_names)
            
            category_type = "subcategory"
        
        else:
            self.report({'ERROR'}, "Invalid category! See console for details.")
            print ("Invalid category!")
            print (category_contents)
        return {'FINISHED'}

class CloseMaterialCategory(bpy.types.Operator):
    '''Close open material category'''
    bl_idname = "material.closecategory"
    bl_label = "close open material category"

    def execute(self, context):
        global category_contents
        global parent_category_contents
        global current_material_number
        global category_type
        
        if category_type == "subcategory":
            category_contents = "None"
            current_material_number = -1
            category_type = "parent"
        else:
            parent_category_contents = "None"
            category_contents = "None"
            current_material_number = -1
            category_type = "none"
        
        return {'FINISHED'}

class ViewMaterial(bpy.types.Operator):
    '''View material details'''
    bl_idname = "material.viewmaterial"
    bl_label = "view material details"
    material = bpy.props.IntProperty()

    def execute(self, context):
        global current_material_number
        
        current_material_number = self.material
        
        return {'FINISHED'}
    
class DownloadPreview(bpy.types.Operator):
    '''Download Preview'''
    bl_idname = "material.downloadpreview"
    bl_label = "download preview from library"
    name = bpy.props.StringProperty()
    filename = bpy.props.StringProperty()
    library = bpy.props.StringProperty()
    
    def execute(self, context):
        #connection = http.client.HTTPConnection("peter.cassetta.info")
        #if self.library == "release":
        #    if is_subcategory:
        #        connection.request("GET", "/material-library/release/" + category_filename + "/" + subcategory_filename + "/" + self.filename + ".bcm")
        #    else:
        #        connection.request("GET", "/material-library/release/" + category_filename + "/" + self.filename + ".bcm")
        #else:
        #    if is_subcategory:
        #        connection.request("GET", "/material-library/testing/" + category_filename + "/" + subcategory_filename + "/" + self.filename + ".bcm")
        #    else:
        #        connection.request("GET", "/material-library/testing/" + category_filename + "/" + self.filename + ".bcm")
        #        
        # = str(connection.getresponse().read())[14:-1]
        if bpy.data.images.find("mat_lib_preview_texture") == -1:
            bpy.data.images.new(name="mat_lib_preview_image", width=64, height=64, alpha=False)
            bpy.data.images["mat_lib_preview_image"].generated_type = 'UV_GRID'
        if bpy.data.textures["mat_lib_preview_texture"].image != bpy.data.images["mat_lib_preview_image"]:
            bpy.data.textures["mat_lib_preview_texture"].image = bpy.data.images["mat_lib_preview_image"]
        self.report({'INFO'}, "Cannot download yet.")
        return {'FINISHED'}

class AddLibraryMaterial(bpy.types.Operator):
    '''Add material from library'''
    bl_idname = "material.libraryadd"
    bl_label = "add material from library"
    name = bpy.props.StringProperty()
    filename = bpy.props.StringProperty()
    library = bpy.props.StringProperty()
    
    def execute(self, context):
        global material_file_contents
        
        connection = http.client.HTTPConnection("peter.cassetta.info")
        if category_type == "subcategory":
            if self.library == "release":
                connection.request("GET", "/material-library/release/" + parent_category_filename + "/" + category_filename + "/" + self.filename + ".bcm")
            else:
                connection.request("GET", "/material-library/testing/" + parent_category_filename + "/" + category_filename + "/" + self.filename + ".bcm")
        else:
            if self.library == "release":
                connection.request("GET", "/material-library/release/" + category_filename + "/" + self.filename + ".bcm")
            else:
                connection.request("GET", "/material-library/testing/" + category_filename + "/" + self.filename + ".bcm")
                
        material_file_contents = str(connection.getresponse().read())
        material_file_contents = material_file_contents[material_file_contents.index("cyclesmat"):-1]
        node_amount = int(material_file_contents[(material_file_contents.index("[nodeamount]") + 12):material_file_contents.index('[/nodeamount]')])
        print (material_file_contents)
        
        #Check file for validitity
        if material_file_contents[0:9] == "cyclesmat":
            print ("Valid material file!")
            
            #Create new material
            if bpy.data.materials.find(self.name) == -1:
                bpy.data.materials.new(self.name)
            bpy.data.materials[self.name].use_nodes = True
            bpy.data.materials[self.name].node_tree.nodes.clear()
            
            #Add nodes
            addNodes(node_amount, self.name)
            
            #Below here adds the links.
            link_amount = int(material_file_contents[(material_file_contents.index("[linkamount]") + 12):material_file_contents.index('[/linkamount]')])
            
            i = 0
            while i < link_amount:
                
                link_data = eval(material_file_contents[(material_file_contents.index("[link" + str(i) + "]") + (6 + len(str(i)))):material_file_contents.index("[/link" + str(i) + "]")])
                print (link_data)
                
                bpy.data.materials[self.name].node_tree.links.new(bpy.data.materials[self.name].node_tree.nodes[link_data[0]].inputs[link_data[1]], bpy.data.materials[self.name].node_tree.nodes[link_data[2]].outputs[link_data[3]])
                i = i + 1
        else:
            print ("Not a valid material file!")
        return {'FINISHED'}

class DownloadMaterial(bpy.types.Operator):
    '''Paste to active material'''
    bl_idname = "material.download"
    bl_label = "paste to active material "
    name = bpy.props.StringProperty()
    filename = bpy.props.StringProperty()
    library = bpy.props.StringProperty()
    
    def execute(self, context):
        global material_file_contents
        
        connection = http.client.HTTPConnection("peter.cassetta.info")
        if self.library == "release":
            if category_type == "subcategory":
                connection.request("GET", "/material-library/release/" + category_filename + "/" + subcategory_filename + "/" + self.filename + ".bcm")
            else:
                connection.request("GET", "/material-library/release/" + category_filename + "/" + self.filename + ".bcm")
        else:
            if category_type == "subcategory":
                connection.request("GET", "/material-library/testing/" + category_filename + "/" + subcategory_filename + "/" + self.filename + ".bcm")
            else:
                connection.request("GET", "/material-library/testing/" + category_filename + "/" + self.filename + ".bcm")
                
        material_file_contents = str(connection.getresponse().read())
        print (material_file_contents)
        material_file_contents = material_file_contents[material_file_contents.index("cyclesmat"):-1]
        node_amount = int(material_file_contents[(material_file_contents.index("[nodeamount]") + 12):material_file_contents.index('[/nodeamount]')])
        print (node_amount)
        
        #Check file for validitity
        if material_file_contents[0:9] == "cyclesmat":
            print ("Valid material file!")
            
            #Out with the old...
            bpy.data.materials[self.name].node_tree.nodes.clear()
            
            #in with the new!
            addNodes(node_amount, self.name)
            
            #Below here adds the links.
            link_amount = int(material_file_contents[(material_file_contents.index("[linkamount]") + 12):material_file_contents.index('[/linkamount]')])
            
            i = 0
            while i < link_amount:
                
                link_data = eval(material_file_contents[(material_file_contents.index("[link" + str(i) + "]") + (6 + len(str(i)))):material_file_contents.index("[/link" + str(i) + "]")])
                bpy.data.materials[self.name].node_tree.links.new(bpy.data.materials[self.name].node_tree.nodes[link_data[0]].inputs[link_data[1]], bpy.data.materials[self.name].node_tree.nodes[link_data[2]].outputs[link_data[3]])
                
                print (link_data)
                
                i = i + 1
        else:
            print ("Invalid material file!")
        return {'FINISHED'}

class SaveLibraryMaterial(bpy.types.Operator):
    '''Save material to disk'''
    bl_idname = "material.librarysave"
    bl_label = "save material to disk"
    name = bpy.props.StringProperty()
    filename = bpy.props.StringProperty()
    library = bpy.props.StringProperty()
    
    def execute(self, context):
        #global material_file_contents
        #
        #connection = http.client.HTTPConnection("peter.cassetta.info")
        #if self.library == "release":
        #    if category_type == "subcategory":
        #        connection.request("GET", "/material-library/release/" + category_filename + "/" + subcategory_filename + "/" + self.filename + ".bcm")
        #    else:
        #        connection.request("GET", "/material-library/release/" + category_filename + "/" + self.filename + ".bcm")
        #else:
        #    if category_type == "subcategory":
        #        connection.request("GET", "/material-library/testing/" + category_filename + "/" + subcategory_filename + "/" + self.filename + ".bcm")
        #    else:
        #        connection.request("GET", "/material-library/testing/" + category_filename + "/" + self.filename + ".bcm")
        #        
        #material_file_contents = str(connection.getresponse().read())[14:-1]
        
        print ("Not working yet.")
        return {'FINISHED'}
    
def addNodes(node_amount, mat):
    i = 0
    while i < node_amount:
        print (node_amount)
        node_data = eval(material_file_contents[(material_file_contents.index("[node" + str(i) + "]") + (6 + len(str(i)))):material_file_contents.index("[/node" + str(i) + "]")])
        print (node_data)
                
        #Below here checks the type of the node and adds the correct type
        
        #INPUT TYPES
        #This is totally crafty, but some of these nodes actually
        # store their values as their output's defualt value!
        if node_data[0] == "ATTRIBUTE":
            print ("ATTRIBUTE")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.attribute_name = node_data[1]
            node.location = eval(node_data[2])
        
        elif node_data[0] == "CAMERA":
            print ("CAMERA")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.location = eval(node_data[1])
        
        elif node_data[0] == "FRESNEL":
            print ("FRESNEL")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = float(node_data[1])
            node.location = eval(node_data[2])
                
        elif node_data[0] == "LAYER_WEIGHT":
            print ("LAYER_WEIGHT")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = float(node_data[1])
            node.location = eval(node_data[2])
                
        elif node_data[0] == "LIGHT_PATH":
            print ("LIGHT_PATH")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.location = eval(node_data[1])
        
        elif node_data[0] == "NEW_GEOMETRY":
            print ("NEW_GEOMETRY")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.location = eval(node_data[1])
        
        elif node_data[0] == "RGB":
            print ("RGB")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.outputs[0].default_value = eval(node_data[1])
            node.location = eval(node_data[2])
        
        elif node_data[0] == "TEX_COORD":
            print ("TEX_COORD")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.location = eval(node_data[1])
        
        elif node_data[0] == "VALUE":
            print ("VALUE")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.outputs[0].default_value = float(node_data[1])
            node.location = eval(node_data[2])
            
            #OUTPUT TYPES
        elif node_data[0] == "OUTPUT_LAMP":
            print ("OUTPUT_LAMP")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.location = eval(node_data[1])
        
        elif node_data[0] == "OUTPUT_MATERIAL":
                    print ("OUTPUT_MATERIAL")
                    node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
                    node.location = eval(node_data[1])
        
        elif node_data[0] == "OUTPUT_WORLD":
            print ("OUTPUT_WORLD")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.location = eval(node_data[1])
        
            #SHADER TYPES
        elif node_data[0] == "ADD_SHADER":
            print ("ADD_SHADER")
            addShader(mat, node_data[0], "", "", "", "", node_data[1])
        
        elif node_data[0] == "BACKGROUND":
            print ("BACKGROUND")
            addShader(mat, node_data[0], "", node_data[1], node_data[2], "", node_data[3])
                
        elif node_data[0] == "BSDF_DIFFUSE":
            print ("BSDF_DIFFUSE")
            addShader(mat, node_data[0], "", node_data[1], node_data[2], "", node_data[3])
        
        elif node_data[0] == "BSDF_GLASS":
            print ("BSDF_GLASS")
            addShader(mat, node_data[0], node_data[1], node_data[2], node_data[3], node_data[4], node_data[5])
            
        elif node_data[0] == "BSDF_GLOSSY":
            print ("BSDF_GLOSSY")
            addShader(mat, node_data[0], node_data[1], node_data[2], node_data[3], "", node_data[4])
        
        elif node_data[0] == "BSDF_TRANSLUCENT":
            print ("BSDF_TRANSLUCENT")
            addShader(mat, node_data[0], "", node_data[1], "", "", node_data[2])
        
        elif node_data[0] == "BSDF_TRANSPARENT":
            print ("BSDF_TRANSPARENT")
            addShader(mat, node_data[0], "", node_data[1], "", "", node_data[2])
        
        elif node_data[0] == "BSDF_VELVET":
            print ("BSDF_VELVET")
            addShader(mat, node_data[0], "", node_data[1], node_data[2], "", node_data[3])
        
        elif node_data[0] == "EMISSION":
            print ("EMISSION")
            addShader(mat, node_data[0], "", node_data[1], node_data[2], "", node_data[3])
        
        elif node_data[0] == "HOLDOUT":
            print ("HOLDOUT")
            addShader(mat, node_data[0], "", "", "", "", node_data[1])
        
        elif node_data[0] == "MIX_SHADER":
            print ("MIX_SHADER")
            addShader(mat, node_data[0], "", "", node_data[1], "", node_data[2])
        
            #TEXTURE TYPES
        elif node_data[0] == "TEX_CHECKER":
            print ("TEX_CHECKER")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[1].default_value = eval(node_data[1])
            node.inputs[2].default_value = eval(node_data[2])
            node.inputs[3].default_value = float(node_data[3])
            node.location = eval(node_data[4])
        
        elif node_data[0] == "TEX_GRADIENT":
            print ("TEX_GRADIENT")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.gradient_type = node_data[1]
            node.location = eval(node_data[2])
        
        elif node_data[0] == "TEX_IMAGE":
            print ("TEX_IMAGE")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            #Need to download image somehow...
            #node.image = node_data[1]
            node.color_space = node_data[2]
            node.location = eval(node_data[3])
            
        elif node_data[0] == "TEX_MAGIC":
            print ("TEX_MAGIC")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.turbulence_depth = int(node_data[1])
            node.inputs[1].default_value = float(node_data[2])
            node.inputs[2].default_value = float(node_data[3])
            node.location = eval(node_data[4])
        
        elif node_data[0] == "TEX_MUSGRAVE":
            print ("TEX_MUSGRAVE")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.musgrave_type = node_data[1]
            node.inputs[1].default_value = float(node_data[2])
            node.inputs[2].default_value = float(node_data[3])
            node.inputs[3].default_value = float(node_data[4])
            node.inputs[4].default_value = float(node_data[5])
            node.inputs[5].default_value = float(node_data[6])
            node.inputs[6].default_value = float(node_data[7])
            node.location = eval(node_data[8])
        
        elif node_data[0] == "TEX_NOISE":
            print ("TEX_NOISE")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[1].default_value = float(node_data[1])
            node.inputs[2].default_value = float(node_data[2])
            node.inputs[3].default_value = float(node_data[3])
            node.location = eval(node_data[4])
                        
        elif node_data[0] == "TEX_SKY":
            print ("TEX_SKY")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.sun_direction = eval(node_data[1])
            node.turbidity = float(node_data[2])
            node.location = eval(node_data[3])
        
        elif node_data[0] == "TEX_VORONOI":
            print ("TEX_VORONOI")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.coloring = node_data[1]
            node.inputs[1].default_value = float(node_data[2])
            node.location = eval(node_data[3])
        
        elif node_data[0] == "TEX_WAVE":
            print ("TEX_WAVE")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.wave_type = node_data[1]
            node.inputs[1].default_value = float(node_data[2])
            node.inputs[2].default_value = float(node_data[3])
            node.inputs[3].default_value = float(node_data[4])
            node.inputs[4].default_value = float(node_data[5])
            node.location = eval(node_data[6])
        
            #COLOR TYPES
        elif node_data[0] == "BRIGHTCONTRAST":
            print ("BRIGHTCONTRAST")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = eval(node_data[1])
            node.inputs[1].default_value = float(node_data[2])
            node.inputs[2].default_value = float(node_data[3])
            node.location = eval(node_data[4])
        
        elif node_data[0] == "GAMMA":
            print ("GAMMA")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = eval(node_data[1])
            node.inputs[1].default_value = float(node_data[2])
            node.location = eval(node_data[3])
        
        elif node_data[0] == "HUE_SAT":
            print ("HUE_SAT")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = float(node_data[1])
            node.inputs[1].default_value = float(node_data[2])
            node.inputs[2].default_value = float(node_data[3])
            node.inputs[3].default_value = float(node_data[4])
            node.inputs[4].default_value = eval(node_data[5])
            node.location = eval(node_data[6])
            
        elif node_data[0] == "INVERT":
            print ("INVERT")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = float(node_data[1])
            node.inputs[1].default_value = eval(node_data[2])
            node.location = eval(node_data[3])
        
        elif node_data[0] == "MIX_RGB":
            print ("MIX_RGB")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.blend_type = node_data[1]
            node.inputs[0].default_value = float(node_data[2])
            node.inputs[1].default_value = eval(node_data[3])
            node.inputs[2].default_value = eval(node_data[4])
            node.location = eval(node_data[5])
        
            #VECTOR TYPES
        elif node_data[0] == "MAPPING":
            print ("MAPPING")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.translation = eval(node_data[1])
            node.rotation = eval(node_data[2])
            node.scale = eval(node_data[3])
            if node_data[4] == "True":
                node.use_min = True
                node.min = node_data[5]
            if node_data[6] == "True":
                node.use_max = True
                node.max = node_data[7]
            node.inputs[0].default_value = eval(node_data[8])
            node.location = eval(node_data[9])
        
        elif node_data[0] == "NORMAL":
            print ("NORMAL")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.outputs[0].default_value = eval(node_data[1])
            node.inputs[0].default_value = eval(node_data[2])
            node.location = eval(node_data[3])
        
            #CONVERTER TYPES
            
            #This node is going to be a pain to implement.
            #if node_data[0] == "VALTORGB":
            #    print ("VALTORGB")
            #    node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            #    node.inputs[0].default_value = float(node_data[1])
            #    node.location = eval(node_data[2])
        
        elif node_data[0] == "COMBRGB":
            print ("COMBRGB")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = float(node_data[1])
            node.inputs[1].default_value = float(node_data[2])
            node.inputs[2].default_value = float(node_data[3])
            node.location = eval(node_data[4])
        
        elif node_data[0] == "MATH":
            print ("MATH")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.operation = node_data[1]
            node.inputs[0].default_value = float(node_data[2])
            node.inputs[1].default_value = float(node_data[3])
            node.location = eval(node_data[4])
        
        elif node_data[0] == "RGBTOBW":
            print ("RGBTOBW")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = eval(node_data[1])
            node.location = eval(node_data[2])
        
        elif node_data[0] == "SEPRGB":
            print ("SEPRGB")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.inputs[0].default_value = eval(node_data[1])
            node.location = eval(node_data[2])
        
        elif node_data[0] == "VECT_MATH":
            print ("VECT_MATH")
            node = bpy.data.materials[mat].node_tree.nodes.new(node_data[0])
            node.operation = node_data[1]
            node.inputs[0].default_value = eval(node_data[2])
            node.inputs[1].default_value = eval(node_data[3])
            node.location = eval(node_data[4])
        else:
            print ("The material file contains the node name \"%s\", which is not known. The material file may contain a typo, or you may need to check for updates to this addon." % node_data[0])
        i = i + 1

def addShader(mat, type, distribution_type, color, fac, ior, location):
    shader = bpy.data.materials[mat].node_tree.nodes.new(type)
    shader.location = eval(location)
    
    if distribution_type is not "":
        shader.distribution = distribution_type
    if color is not "":
        shader.inputs[0].default_value = eval(color)
    if type == "MIX_SHADER":
        shader.inputs[0].default_value = float(fac)
    else:
        if fac is not "":
            shader.inputs[1].default_value = float(fac)
    if ior is not "":
        shader.inputs[2].default_value = float(ior)

def register():
    bpy.utils.register_class(OnlineMaterialLibraryPanel)
    bpy.utils.register_class(RefreshLibrary)
    bpy.utils.register_class(OpenMaterialCategory)
    bpy.utils.register_class(CloseMaterialCategory)
    bpy.utils.register_class(ViewMaterial)
    bpy.utils.register_class(DownloadPreview)
    bpy.utils.register_class(AddLibraryMaterial)
    bpy.utils.register_class(SaveLibraryMaterial)
    bpy.utils.register_class(DownloadMaterial)


def unregister():
    bpy.utils.unregister_class(OnlineMaterialLibraryPanel)
    bpy.utils.unregister_class(RefreshLibrary)
    bpy.utils.unregister_class(OpenMaterialCategory)
    bpy.utils.unregister_class(CloseMaterialCategory)
    bpy.utils.unregister_class(ViewMaterial)
    bpy.utils.unregister_class(DownloadPreview)
    bpy.utils.unregister_class(AddLibraryMaterial)
    bpy.utils.unregister_class(SaveLibraryMaterial)
    bpy.utils.unregister_class(DownloadMaterial)

if __name__ == "__main__":
    register()