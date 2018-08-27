# addon_relay.py (c) 2012 Atom
# This open source script transfers the animation from a host object to target objects in a managed list.
# Each target can have different offset and time stretch.
# 261_addon_relay_2h.blend
# Updated 02212013 For 2.66 compatability.
# 266_addon_relay_2j.blend

import bpy
import sys
import threading, time
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty, EnumProperty
from math import acos, sin, cos, pi, radians

#bpy.app.debug = True

############################################################################
# Globals, yes ugh!
############################################################################
isRendering = False             # Global rendering state flag.
isBusy = False                  # Global busy flag. Try to avoid events if we are already busy.
isBusyCount = 0                 # Accumulate how many events we are missing.
lastFrame = -1                  # The last frame we changed to.
DEBUG = True                    # Enable disable debug output.
CONSOLE_PREFIX = "RE:Lay "

# Objects are managed by name prefix. Customize here...e.g. my_prefix (no longer than 12 characters)
PARENT_PREFIX   = "relay_"      # Objects named like this are RE:Lay objects whose custom properties are animated by the end-user.
LAYOUT_PREFIX   = "lo_"         # This is the layout mesh object that all characters will be vertex parented to.
MAX_NAME_SIZE = 21              # Maximum length of any object name.
ENTRY_LENGTH = 9                # Only grab the first 9 characters from the list entry name when constructing the particle name.
ENTRY_NAME = "_target_"         # The default name for new entries.

############################################################################
# Code for debugging.
############################################################################
def to_console (passedItem = ""):
    if DEBUG == True:
        print(CONSOLE_PREFIX + passedItem)

############################################################################
# Parameter Deffinitiions
############################################################################
def updateRELayParameter(self,context):
    # This def gets called when one of the tagged properties changes state.
    global isBusy
        
    if isBusy == False:
        if context != None:
            passedScene = context.scene
            cf = passedScene.frame_current
            to_console("")
            to_console("updateRELayParameter on frame #" + str(cf))
            reviewRELay(passedScene)
            
class cls_RELay(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    target_name = bpy.props.StringProperty(name="Target", description="Type the name of the object that will inherit this objects motion here.")
    apply_to_delta = bpy.props.BoolProperty(name="ApplyToDelta", description="When active, results are applied to the delta coordinates instead.", default=True, options={'ANIMATABLE'}, subtype='NONE', update=updateRELayParameter)
    offset = bpy.props.FloatProperty(name="Offset", description="Number of frames to delay transformation.", default=0.0, min=-1800.0, max=1800, step=3, precision=2, options={'ANIMATABLE'}, subtype='TIME', unit='TIME', update=updateRELayParameter)    
    stretch = bpy.props.FloatProperty(name="Stretch", description="Stretch time to slow it down.", default=1.0, min=0.001, max=10.0, step=3, precision=2, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateRELayParameter)

    axis_types = [
                ("0","None","None"),
                ("1","X","X"),
                ("2","Y","Y"),
                ("3","Z","Z"),
                ("4","XY","XY"),
                ("5","YZ","YZ"),
                ("6","XZ","XZ"),
                ("7","XYZ","XYZ"),
                ("8","ZXY","ZXY"),
                ("9","XZY","XZY"),
                ]
    axis_loc = EnumProperty(name="AxisLoc", description="The axis that will be relayed to the target.", default="7", items=axis_types, update=updateRELayParameter)
    axis_rot = EnumProperty(name="AxisRot", description="The axis that will be relayed to the target.", default="7", items=axis_types, update=updateRELayParameter)
    axis_scale = EnumProperty(name="AxisScale", description="The axis that will be relayed to the target.", default="7", items=axis_types, update=updateRELayParameter)

bpy.utils.register_class(cls_RELay)

# Add these properties to every object in the entire Blender system (muha-haa!!)
bpy.types.Object.Relay_List_Index = bpy.props.IntProperty(min= 0,default= 0)
bpy.types.Object.Relay_List = bpy.props.CollectionProperty(type=cls_RELay)

############################################################################
# Code for returning names, objects, curves, scenes or meshes.
############################################################################
def fetchIfObject (passedName= ""):
    try:
        result = bpy.data.objects[passedName]
    except:
        result = None
    return result

def fetchIfAction (passedName= ""):
    try:
        result = bpy.data.actions[passedName]
    except:
        result = None
    return result

def returnScene (passedIndex = 0):
    try:
        return bpy.data.scenes[passedIndex]
    except:
        return None

def returnChildren(passedParent, passedScene):
    return [ob_child for ob_child in passedScene.objects if ob_child.parent == passedParent]

def returnLayoutName(passedName):
    result = LAYOUT_PREFIX + passedName
    return result

def returnAllObjectNames ():
    # NOTE: This returns all object names in Blender, not scene specific.
    result = []
    for ob in bpy.data.objects:
        result.append(ob.name)
    return result 

def returnObjectNamesLike(passedName):
    # Return objects named like our passedName.
    result = []
    isLike = passedName
    l = len(isLike)
    all_obs = returnAllObjectNames()
    for name in all_obs:
        candidate = name[0:l]
        if isLike == candidate:
            result.append(name)
    return result

def returnRePhraseObjects(passedName, passedScene):
    ob_layout_name = returnLayoutName(passedName)
    ob_layout = fetchIfObject(ob_layout_name)
    if ob_layout != None:
        # Get the children of the layout object, these are RE:Phrase+ 1.3 characters.
        ob_list = returnChildren(ob_layout,passedScene)
    else:
        ob_list = []
    return ob_list

############################################################################
# FRAME CHANGE (or parameter update) code. 
############################################################################
def frameChangeRELay(passedScene):
    global isBusy, isBusyCount, lastFrame

    if passedScene != None:
        if isBusy == False:
            isBusy = True
            cf = passedScene.frame_current
            if cf != lastFrame:
                reviewRELay(passedScene)
                lastFrame = cf
            isBusy = False
            isBusyCount = 0
        else:
            # We are either still busy in reviewRePhrase or we crashed inside reviewRePhrase.
            # Sometimes a crash can occur when Blender gives us bad data or just bad timing (i.e. bpy.data is in a wierd state).
            isBusyCount = isBusyCount + 1
            if isBusyCount > 1:    #Arbitrary number, you decide.
                # We have missed a number of events so it may have been a crash.
                # If the crash was caused simply by bad timing or data error,
                # somethimes abandoning this isBusy = True state can allow the AddOn to function again.
                isBusy = False      # Allow the AddOn to try to function again.
                isBusyCount = 0     # Reset to zero, if it is a true crash we will just end up here again.
                to_console("Attempting to recover from an isBusy crash state.")
    else:
        to_console("Received bad scene. None.")

def reviewRELay(passedScene):
    localScene = passedScene    #returnScene()
    frame_current = localScene.frame_current
    
    ob_list = returnObjectNamesLike(PARENT_PREFIX)
    if len(ob_list) > 0:
        for name in ob_list:
            #to_console("Processing REL:Lay target [" + name + "].")
            ob = fetchIfObject(name)
            if ob !=None:
                # This is an object that is managed by this script.
                
                # See if we are supposed to maintain a list link between a RE:Phrase object.
                try:
                    rephrase_name = ob["rephrase_object"]
                except:
                    rephrase_name = ""
                ob_rephrase = fetchIfObject(rephrase_name)
                if ob_rephrase != None:
                    to_console("possible rephrase link to [" + rephrase_name + "].")
                    # An object, is it RE:Phrase?
                    isRephrase = False
                    try:
                        col_rephrase = ob_rephrase["Rephrase_List"]
                    except:
                        col_rephrase = None
                        
                    if col_rephrase != None:
                        to_console("Proceeding with RE:Phrase mapping.")
                        # It does have Rephrase_List so it probably is a RE:Phrase+ 1.3 object.
                        lo_name = returnLayoutName(rephrase_name)
                        ob_layout = fetchIfObject(lo_name)
                        if ob_layout != None:
                            # In RE:Phrase+ 1.3 the characters are actually parented to the layout object, not the RE:Phrase object.
                            names_to_target = []
                            lst_names = returnChildren(ob_layout, passedScene)
                            for name in reversed(lst_names):
                                names_to_target.append(name)
                           
                            if len(names_to_target) > 0:
                                # I guess we have some new targets to manage.
                                try:
                                    col_relay = ob.Relay_List
                                except:
                                    col_relay = None
                                if col_relay != None:
                                    # Remove old targets.
                                    l = len(col_relay)
                                    #print(type(col_relay))
                                    #print("old target length:" + str(l))
                                    for i in range(l):
                                        #print(i,col_relay[i])
                                        col_relay.remove(0)
                                    
                                    # Add new targets.
                                    c = 0
                                    frame_spacing = ob["auto_list_step"]
                                    #print("frame_spacing:" + str(frame_spacing))
                                    for item in names_to_target:
                                        # This adds at the end of the collection list.
                                        col_relay.add()
                                        l = len(col_relay)
                                        col_relay[-1].name= (str(l)+ ENTRY_NAME + item.name)
                                        col_relay[-1].target_name = (item.name)
                                        col_relay[-1].offset = frame_spacing * (c)
                                        c = c + 1
                                    ob.Relay_List_Index = len(col_relay)-1
                                    to_console("Target list was derived from [" + rephrase_name + "].")
                                    isRephrase = True
                                        
                                else:
                                    # Problem accessig the List collection of parameters.
                                    to_console("Problem with [" + name + "] accessing Relay_List.")
                                    pass
                            else:
                                # RE:Phrase object has no children. (i.e. generated characters)
                                to_console("[" + lo_name + "] has no child objects.")
                                pass
                        else:
                            # No layout object detected for RE:Phrase+ 1.3.
                            to_console("Can not locate [" + lo_name + "] layout object.")
                            pass
                    else:
                        # Probably not a RE:Phrase object.
                        to_console("[" + rephrase_name + "] is probably not a RE:Phrase+ 1.3 object.")        
                        pass
                else:
                    # Object does not exist.
                    #to_console("Can not locate [" + rephrase_name + "] for RE:Phrase+ 1.3 mapping.")
                    pass
            
                #try:
                # Try to fetch custom properties.
                # NOTE: If the propertry does not exist or BPY is in an inaccessible state an error can occur here.
                custom_properties_valid = True      # Default to sucess, a TRY error will set this False.
                l = len(ob.Relay_List)
                #to_console("# of targets is " + str(l))
                if l > 0:
                    for n in range(l):
                        current_target = ob.Relay_List[n].target_name
                        
                        ob_target = fetchIfObject(current_target)
                        if ob_target != None:
                            offset = ob.Relay_List[n].offset
                            #to_console("Current offset is " + str(offset))
                            apply_to_delta = ob.Relay_List[n].apply_to_delta
                            #to_console("Current apply_to_delta is " + str(apply_to_delta))
                            axis_loc = ob.Relay_List[n].axis_loc
                            #to_console("Current axis_loc is " + str(axis_loc) + " the type is:" + str(type(axis_loc)))
                            axis_rot = ob.Relay_List[n].axis_rot
                            #to_console("Current axis_rot is " + str(axis_rot))
                            axis_scale = ob.Relay_List[n].axis_scale
                            #to_console("Current axis_scale is " + str(axis_scale))
                            try: 
                                offset_frame = int((frame_current-offset)*ob.Relay_List[n].stretch)
                            except:
                                to_console("ERROR calculating offset_frame for [" + current_target + "].")
                                offset_frame = 0.0
                            #to_console("Data I require resides on frame #" + str(offset_frame) +".")

                            # Time to start relaying animation data.
                            # REMEMBER: There are OBJECT actions and DATA actions.
                            
                            # Transfer the DATA action.
                            try:
                                da_source = ob.data
                                action_name = da_source.animation_data.action.name
                            except:
                                action_name = ""
                            try:
                                action = bpy.data.actions[action_name]
                                can_proceed = True
                            except:
                                can_proceed = False
                            if can_proceed == True:
                                da_target = ob_target.data
                                for i,fcurve in enumerate(action.fcurves):
                                    v = fcurve.evaluate(offset_frame)
                                    # Construct a string that will set the value directly when executed.
                                    s = "da_target." + fcurve.data_path + " = " + str(v)
                                    name_space = {}
                                    code = compile(s, '<string>', 'exec')
                                    try:
                                        exec (code) in name_space
                                    except:
                                        to_console ("Target [" + current_target + "] can not receive data for [" + str(fcurve.data_path) + "].")
                                                            
                            # Transfer the OBJECT action.
                            try:       
                                action_name = ob.animation_data.action.name
                            except:
                                action_name = ""
                            try:
                                action = bpy.data.actions[action_name]
                                can_proceed = True
                            except:
                                can_proceed = False
                            if can_proceed == True:
                                #to_console("Transfering action [" + action_name + "] to [" + current_target + "].")
                                # New approaoch, read f-curve directly.
                                loc = [0.0,0.0,0.0] #ob_target.location        #[0.0,0.0,0.0]
                                rot = [0.0,0.0,0.0] #ob_target.rotation_euler  #[0.0,0.0,0.0]
                                scale = [1.0,1.0,1.0]   #ob_target.scale         #[1.0,1.0,1.0]
                                for i,fcurve in enumerate(action.fcurves):
                                    #try:
                                    v = fcurve.evaluate(offset_frame)
                                    if fcurve.data_path == "location":
                                        loc[fcurve.array_index] = v
                                        #ob_target.delta_location[fcurve.array_index]=v
                                        #to_console("Assigning delta_location[" + str(fcurve.array_index) + "] to (" + str(v) + ").")
                                    elif fcurve.data_path == "rotation_euler":
                                        rot[fcurve.array_index] = v
                                        #ob_target.delta_rotation_euler[fcurve.array_index]=v 
                                        #to_console("Assigning delta_rotation_euler[" + str(fcurve.array_index) + "] to (" + str(v) + ").")
                                    elif fcurve.data_path == "scale":
                                        scale[fcurve.array_index] = v
                                        #ob_target.delta_scale[fcurve.array_index]=v
                                        #to_console("Assigning delta_scale[" + str(fcurve.array_index) + "] to (" + str(v) + ").")
                                    else:
                                        to_console ("Unsupported data_path [" + fcurve.data_path + "].")
                                    #except:
                                    #    to_console("refresh problem operating upon bpy.data.")
                                                                                      
                                try:
                                    # Apply the data to the delta portion of the object.
                                    #if isRephrase == True:
                                    #    #ReWire axis for RE:Phrase link.
                                    #    axis_loc = "7"
                                    #    axis_rot = "7"
                                    #    axis_scale = "7"
                                        
                                    if axis_loc == "9":
                                        #ZXY
                                        ob_target.delta_location[0] = loc[2]
                                        ob_target.delta_location[1] = loc[0]
                                        ob_target.delta_location[2] = loc[1]
                                    if axis_loc == "8":
                                        #XZY
                                        ob_target.delta_location[0] = loc[0]
                                        ob_target.delta_location[1] = loc[2]
                                        ob_target.delta_location[2] = loc[1]                                        
                                    if axis_loc == "7":
                                        #XYZ
                                        ob_target.delta_location = loc
                                    if axis_loc == "6":
                                        #XZ
                                        ob_target.delta_location[0] = loc[0]
                                        ob_target.delta_location[2] = loc[2]
                                    if axis_loc == "5":
                                        #YZ
                                        ob_target.delta_location[1] = loc[1]
                                        ob_target.delta_location[2] = loc[2]
                                    if axis_loc == "4":
                                        #XY
                                        ob_target.delta_location[0] = loc[0]
                                        ob_target.delta_location[1] = loc[1]
                                    if axis_loc == "3":
                                        #Z
                                        ob_target.delta_location[2] = loc[2]
                                    if axis_loc == "2":
                                        #Y
                                        ob_target.delta_location[1] = loc[1]
                                    if axis_loc == "1":
                                        #X
                                        ob_target.delta_location[0] = loc[0]

                                    if axis_rot == "9":
                                        #ZXY
                                        ob_target.delta_rotation_euler[0] = rot[2]
                                        ob_target.delta_rotation_euler[1] = rot[0]
                                        ob_target.delta_rotation_euler[2] = rot[1]
                                    if axis_rot == "8":
                                        #XZY
                                        ob_target.delta_rotation_euler[0] = rot[0]
                                        ob_target.delta_rotation_euler[1] = rot[2]
                                        ob_target.delta_rotation_euler[2] = rot[1]         
                                    if axis_rot == "7":
                                        #XYZ
                                        ob_target.delta_rotation_euler = rot
                                    if axis_rot == "6":
                                        #XZ
                                        ob_target.delta_rotation_euler[0] = rot[0]
                                        ob_target.delta_rotation_euler[2] = rot[2]
                                    if axis_rot == "5":
                                        #YZ
                                        ob_target.delta_rotation_euler[1] = rot[1]
                                        ob_target.delta_rotation_euler[2] = rot[2]
                                    if axis_rot == "4":
                                        #XY
                                        ob_target.delta_rotation_euler[0] = rot[0]
                                        ob_target.delta_rotation_euler[1] = rot[1]
                                    if axis_rot == "3":
                                        #Z
                                        ob_target.delta_rotation_euler[2] = rot[2]
                                    if axis_rot == "2":
                                        #Y
                                        ob_target.delta_rotation_euler[1] = rot[1]
                                    if axis_rot == "1":
                                        #X
                                        ob_target.delta_rotation_euler[0] = rot[0]

                                    if axis_scale == "9":
                                        #ZXY
                                        ob_target.delta_scale[0] = scale[2]
                                        ob_target.delta_scale[1] = scale[0]
                                        ob_target.delta_scale[2] = scale[1]
                                    if axis_scale == "8":
                                        #XZY
                                        ob_target.delta_scale[0] = scale[0]
                                        ob_target.delta_scale[1] = scale[2]
                                        ob_target.delta_scale[2] = scale[1]         
                                    if axis_scale == "7":
                                        #XYZ
                                        ob_target.delta_scale = scale
                                        #ob_target.scale = scale
                                    if axis_scale == "6":
                                        #XZ
                                        ob_target.delta_scale[0] = scale[0]
                                        ob_target.delta_scale[2] = scale[2]
                                    if axis_scale == "5":
                                        #YZ
                                        ob_target.delta_scale[1] = scale[1]
                                        ob_target.delta_scale[2] = scale[2]
                                    if axis_scale == "4":
                                        #XY
                                        ob_target.delta_scale[0] = scale[0]
                                        ob_target.delta_scale[1] = scale[1]
                                    if axis_scale == "3":
                                        #Z
                                        ob_target.delta_scale[2] = scale[2]
                                    if axis_scale == "2":
                                        #Y
                                        ob_target.delta_scale[1] = scale[1]
                                    if axis_scale == "1":
                                        #X
                                        ob_target.delta_scale[0] = scale[0]
                                except:
                                    to_console("refresh problem operating upon bpy.data.")

                                #to_console("Transfer complete.")
                            else:
                                # No actions to process.
                                pass
                        else:
                            to_console("[" + current_target + "] is in list, but not in memory.")
                else:
                    # We end up here when the end user renames an existing non-RE:Lay object to a RE:Lay object.
                    # Zero items in the list means no collection or additional properties either.
                    custom_properties_valid = False
                    to_console("Zero targets in list means no custom properties either.")
                #except:
                #    custom_properties_valid = False
                #    to_console ("Problem accessing or setting RE:Lay object properties.")
                    
                if custom_properties_valid == False:
                    # This object is named like our PARENT_PREFIX but is missing some or all of it's custom properties.
                    to_console("Unsupported RE:Lay object, missing custom properties.")
                    '''
                    try:                    
                        to_console("Fetching target list collection.")
                        collection = ob.Relay_List
                        to_console("Adding a target to the list.")
                        collection.add()
                        to_console("Assigning default properties to target item.")
                        collection[-1].name = "Target #1"
                        collection[-1].target_name = ""
                        collection[-1].offset = 0
                        collection[-1].apply_to_delta = True
                        to_console("Setting the target list index.")
                        ob["Relay_List_Index"] = 0
                        to_console("Enabling the RE:Lay AddOn.")
                        ob["enabled"] = 1
                        to_console("Default for list_from_rephrase.")
                        ob["list_from_rephrase"] = ""
                        to_console("Auto list operations will use this step between characters.")
                        ob["auto_list_step"] = 5
                        #to_console("Attempting to set the UI tool tips, min and max.")
                        ob["_RNA_UI"] = {"auto_list_step": {"min":0, "max":180, "description":"List operations use this value as the frame delay offset between targets."}, "Relay_List_Index": {"min":0, "max":240, "description":"Internal value, do not animate!"}, "list_from_rephrase": {"description":"Type name of a RE:Phrase object here to auto-populate this RE:Lay targets list."}, "enabled": {"min":0, "max":1, "description":"Enable or Disable this RE:Lay object."}}
                
                        #ob["_RNA_UI"] = {"Relay_List_Index": {"min":0, "max":100, "description":"Internal value, do not animate!"}, "enabled": {"min":0, "max":1, "description":"Enable or Disable this RE:Lay object."}}
                    except:
                        #Ugh! More failure, give up.
                        to_console("Giving up adding custom properties to make this a valid RE:Lay object.")
                    '''
            else:
                to_console ("Failed to fetch RE:Lay object [" + name + "].")
    else:
        to_console("No RE:Lay objects named like [" + PARENT_PREFIX + "] detected in the scene.")

############################################################################
# Thread processing for parameters that are invalid to set in a DRAW context.
# By performing those operations in these threads we can get around the invalid CONTEXT error within a draw event.
# This is fairly abusive to the system and may result in instability of operation.
# Then again as long as you trap for stale data it just might work..?
# For best result keep the sleep time as quick as possible...no long delays here.
############################################################################
def relay_new_source(lock, passedSourceName, passedSleepTime):
    time.sleep(passedSleepTime) # Feel free to alter time in seconds as needed.   
    to_console("Threading: relay_new_source")
    ob_source = fetchIfObject(passedSourceName)
    if ob_source !=None:
            ob_source.show_name = True
            ob_source.hide_render = True  
                                                
            # Populate the new entry in the collection list.
            collection = ob_source.Relay_List
            collection.add() 
            l = len(collection)
            collection[-1].name= (str(l)+ ENTRY_NAME)
           
            to_console("Threading: New entry established on [" + passedSourceName + "].")
    else:
        to_console("Threading: " + CONSOLE_PREFIX + " source not found [" + passedSourceName + "].") 

def relay_add_properties(lock, passedSourceName, passedSleepTime):
    time.sleep(passedSleepTime) # Feel free to alter time in seconds as needed.   
    to_console("Threading: relay_add_properties")
    ob_source = fetchIfObject(passedSourceName)
    if ob_source != None:
        try:
            ob_source["enabled"] = 1
            ob_source["rephrase_object"] = ""
            ob_source["auto_list_step"] = 5.0
            ob_source["_RNA_UI"] = {"rephrase_object":{"description":"Type the name of a RE:Phrase+ 1.3 text object here."}, "auto_list_step":{"description":"Time delay, in frames, between entries."}, "enabled":{"description":"Boolean value that determines the enabled state of this AddOn."}}

            to_console("Threading: custom properties added to [" + passedSourceName + "].")
        except:
            to_console("Threading: unable to add enabled custom property to [" + passedSourceName + "] at this time.") 
             
############################################################################
# PANEL code.
############################################################################
# Create operator to rename this object with the relay_ preifix.   
class OBJECT_OT_Rename_To_Relay(bpy.types.Operator):
    bl_label = "Rename To RE:Lay"
    bl_idname = "op.rename_to_relay"
    bl_description = "Click this button to rename this object with the relay_ prefix. This will make it a RE:Lay object."
    
    def invoke(self, context, event):
        ob = context.object
        if ob != None:
            relay_name = PARENT_PREFIX + ob.name
            if len(relay_name) > MAX_NAME_SIZE:
                # Name too long.
                relay_name = relay_name[:MAX_NAME_SIZE]
            ob_source = fetchIfObject(relay_name)
            if ob_source != None:
                # Hmm...already and object named like this.
                s = "Conflict with name [" + relay_name + "] rename this object, try again."
                self.report({'WARNING'}, "%s" % s)
                to_console (s)
            else:
                ob.name = relay_name
        return {'FINISHED'}
    
# Create operator to to transfer the current selection to the list.
class OBJECT_OT_Relay_Get_Selection(bpy.types.Operator):
    bl_label = "Get Selection And Distribute In Time"
    bl_description ="Replace the current target list with a new list of the objects in the current selection."
    bl_idname = "relay.get_selection"
    
    offset = IntProperty(name="Offset: ",description="The frame delay that accumulates as each item in the selection is added to the target list.",default=5,min=0,max=300)
    rephrase_object = StringProperty(name="Name: ",description="Use this RE:Phrase object's characters to populate the target list. Leave blank to transfer current viewport selection to target list.",default="")

    def invoke(self, context, event):
        #Popup a dialog the user can interact with.
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
    def draw(self,context):
        layout = self.layout
        layout.prop(self,"offset")
        layout.separator()
        box = layout.box() 
        layout.label(" RE:Phrase+ 1.3 Link:", icon="LINK_AREA")
        layout.prop(self,"rephrase_object",icon="QUESTION")
        layout.separator()

    def execute(self, context):
        global isBusy
        
        if isBusy == False:
            isBusy = True
            ob_relay = context.object
            if ob_relay != None:
                to_console("[" + ob_relay.name + "].")
                try:
                    ob_relay["rephrase_object"] = self.rephrase_object
                    ob_relay["auto_list_step"] = self.offset
                    to_console("Assigning rephrase_object value to [" + ob_relay.name + "].")
                except:
                    # ob_relay is not a RE:Lay object...?
                    to_console("This RE:Lay object is missing a custom property.")
                
                localScene = context.scene 
                ob_rephrase = fetchIfObject(self.rephrase_object)
                if ob_rephrase == None:
                    # Proceed with acquiring targets from the scene selection.       
                    ob_list = context.selected_objects
                                    
                    # Sort the list alphabetically and remove ourself from the list.
                    from operator import itemgetter, attrgetter
                    ob_list = sorted(ob_list,key=attrgetter('name'))
                    sorted(ob_list, key=attrgetter('name'), reverse=True)
                    to_console("Use object list from selected scene object.")
                else:
                    # Proceed with fetching the characters from a RE:Phrase+ 1.3 object.
                    ob_list = returnRePhraseObjects(self.rephrase_object, localScene)
                    to_console("Use object list derived from RE:Phrase+ 1.3 managed font.")
    
                if len(ob_list) > 0:
                    to_console("Removing previous target list")
                    collection = ob_relay.Relay_List
                    l = len(collection)
                    if l > 0:
                        #Remove previous data.
                        to_console("1:" + str(isBusy))
                        for n in range(l):
                            collection.remove(0)
                        to_console("We now have zero entries in our list.")
                        to_console("2:" + str(isBusy))    
                    else:
                        to_console("No list to remove, this is odd..?")
    
                    offset = 0
                    for ob in ob_list:
                        to_console("OB [" + ob.name + "].")
                        # Don't ever add self, RE:Phrase or RE:Phrase layout object to list.
                        skip = False
                        lo_name = returnLayoutName(self.rephrase_object)
                        if ob.name == ob_relay.name: skip = True
                        if ob.name == self.rephrase_object: skip = True
                        if ob.name == lo_name: skip = True
                        if skip == False:
                            # Only add objects that are not ourself.
                            to_console("3:" + str(isBusy))  
                            collection.add()
                            l = len(collection)
                            collection[-1].name= (str(l)+ ENTRY_NAME + ob.name)
                            collection[-1].target_name = (ob.name)
                            collection[-1].offset = (offset)
                            offset = offset + self.offset
                            to_console("4:" + str(isBusy))
                    ob_relay.Relay_List_Index = len(collection)-1  
                else:
                    to_console ("No items selected, list population not possible.")
            else:
                to_console ("Problem with context.object.")
            isBusy = False
        else:
            to_console("Still busy, operator [ot.get_selection] was not executed.")
        return {'FINISHED'}
    
# Create operator to add or remove entries to/from the Collection    
class OBJECT_OT_Relay_Add_Remove_String_Items(bpy.types.Operator):
    bl_label = "Add or Remove"
    bl_description = "Add or remove a list item."
    bl_idname = "relay_collection.add_remove"
    add = bpy.props.BoolProperty(default = True)
    
    def invoke(self, context, event):
        add = self.add
        ob = context.object
        if ob != None:
            collection = ob.Relay_List
            if add:
                # This adds at the end of the collection list.
                collection.add()
                l = len(collection)
                collection[-1].name= (str(l)+ ENTRY_NAME)
                collection[-1].target_name = ("")
            else:
                l = len(collection)
                if l > 1:
                    # This removes one item in the collection list function of index value
                    index = ob.Relay_List_Index
                    collection.remove(index)
                    ob.Relay_List_Index = len(collection)-1
                else:
                    to_console ("Can not remove last item.")
        return {'FINISHED'}
    
# ------- Template List Draw Routines -------
class ATOMS_265_UI_Template_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # draw_item must handle the three layout types... Usually 'DEFAULT' and 'COMPACT' can share the same code.
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, translate=False, icon_value=icon)
        # 'GRID' layout type should be as compact as possible (typically a single icon!).
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)
             
class OBJECT_PT_RELay(bpy.types.Panel):
    bl_label = "RE:Lay 1.3"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    
    def draw(self, context):
        global isBusy
        
        if isBusy == False:
            try:
                # Looks like all is good, we can proceed.
                ob = context.object
                can_proceed = True
            except:
                # We got an error, Blender is in a crashed state.
                # Skip this update.
                can_proceed = False
            if can_proceed == True:
                ob = context.object
                if ob != None:
                    layout = self.layout
                    l = len(PARENT_PREFIX)
                    if ob.name[:l] == PARENT_PREFIX:
                        try:
                            enabled = ob["enabled"]
                        except:
                            enabled = 0
                            
                        if enabled == 1:
                            try:
                                l = len(ob.Relay_List)
                            except:
                                l = 0
                            if l > 0:
                                try:
                                    rephrase_name = ob["rephrase_object"]
                                except:
                                    rephrase_name = ""
                                    
                                # Display list of targets in panel.
                                box1 = layout.box()
                                if rephrase_name != "":
                                    box1.label(" Targets Come From: " + rephrase_name,icon="OUTLINER_DATA_FONT")
                                else:
                                    box1.label("Managed Targets:")
                                #box1.operator("ot.get_selection", icon="FILE", text="Replace This List With Selection")
                                row = box1.row()
                                row.template_list("ATOMS_265_UI_Template_List","relay_entry",ob, "Relay_List", ob, "Relay_List_Index",4,4)          # This show list for the collection
                                
                                # Display Add/Remove Operato.r
                                col = row.column(align=True)
                                col.operator("relay_collection.add_remove", icon="ZOOMIN", text="")              # This show a plus sign button
                                col.operator("relay_collection.add_remove", icon="ZOOMOUT", text="").add = False # This show a minus sign button
                                col.separator()
                                col.separator()
                                col.operator("relay.get_selection", icon="RESTRICT_SELECT_OFF", text="")
                                   
                                # Change name of target.
                                if ob.Relay_List:
                                    # Display self created properties.
                                    try:
                                        entry = ob.Relay_List[ob.Relay_List_Index]
                                    except:
                                        entry = None
                                    if entry != None:
                                        box1.prop(entry, "name", text = "Name")
                                        box = layout.box()  #Separator 
                                        box1 = layout.box() 
                                        row1 = box1.row()
                                        row1.label(" Target:", icon='CURSOR')
                                        
                                        # Let's let the icon offer a little feedback.
                                        if fetchIfObject(entry.target_name) == None:
                                            box1.prop(entry, "target_name", icon='QUESTION')
                                        else:
                                            box1.prop(entry, "target_name", icon='OBJECT_DATAMODE')
        
                                        box1.prop(entry, "offset")
                                        box1.prop(entry, "stretch")
                                        layout.separator()
                                        
                                        box2 = box1.box() 
                                        box2.label("Animation Mapping:", icon="FORCE_HARMONIC")              
                                        #box2.prop(entry, "apply_to_delta", text = "Apply To Delta Transformation")
                
                                        box2.prop(entry, 'axis_loc', text = "Location")
                                        box2.prop(entry, 'axis_rot', text = "Rotation")
                                        box2.prop(entry, 'axis_scale', text = "Scale")
                                    else:
                                        # Invalid index, most likley.
                                        ob.Relay_List_Index = 0
    
                            else:
                                # This object has a zero length Relay_List collection. 
                                # It is named like 'relay_' so lets convert it into a RE:Lay managed object.
                                    
                                # Add a new entry in the collection list. We only want one.
                                #collection = ob.Relay_List
                                #collection.add()                                     
                                
                                # Launch a thread to populate the collection entry that would generate a CONTEXT error, if issued now, in a thread it does not.
                                lock = threading.Lock()
                                lock_holder = threading.Thread(target=relay_new_source, args=(lock,ob.name,0.02), name='RELay_New_Source')
                                lock_holder.setDaemon(True)
                                lock_holder.start()
                        else:
                            # A RELay named object without an enabled custom property.
                            # Lets add the custom property and turn it on.
                            # Launch a thread to create ans set the remaining required custom properties values that would generate a CONTEXT error if issued now. (listed below)
                            #ob["enabled"] = 1
                            #ob["rephrase_object"] = ""
                            lock = threading.Lock()
                            lock_holder = threading.Thread(target=relay_add_properties, args=(lock,ob.name,0.02), name='RELay_Add_Properties')
                            lock_holder.setDaemon(True)
                            lock_holder.start()
                    else:
                        layout.label("Not a " + CONSOLE_PREFIX + " object yet.",icon='INFO')  
                        #layout.label("(rename with '" + PARENT_PREFIX +"' prefix to enable)")
                        layout.operator("op.rename_to_relay", icon="SORTALPHA", text="(rename with '" + PARENT_PREFIX +"' prefix to enable)")
            else:
                # This can happen sometimes after a render.
                to_console (CONSOLE_PREFIX + " was given an invalid context, imagine that..")
                self.layout.label(CONSOLE_PREFIX + " was given an invalid context.",icon='HELP')
                
#### REGISTER ####
def register():
    # Panel
    bpy.utils.register_class(OBJECT_PT_RELay)
    bpy.utils.register_class(OBJECT_OT_Relay_Add_Remove_String_Items)
    bpy.utils.register_class(OBJECT_OT_Relay_Get_Selection)
    bpy.utils.register_class(OBJECT_OT_Rename_To_Relay)
    bpy.utils.register_class(ATOMS_265_UI_Template_List)

def unregister():
    # Panel
    bpy.utils.unregister_class(OBJECT_PT_RELay)
    bpy.utils.unregister_class(OBJECT_OT_Relay_Add_Remove_String_Items)
    bpy.utils.unregister_class(OBJECT_OT_Relay_Get_Selection)
    bpy.utils.unregister_class(OBJECT_OT_Rename_To_Relay)
    bpy.utils.unregister_class(ATOMS_265_UI_Template_List)
    

#if __name__ == '__main__':
register()  

# Setup our event handlers.
#bpy.app.handlers.render_pre.append(frameChangeRELay)  
bpy.app.handlers.frame_change_pre.append(frameChangeRELay)
#bpy.app.handlers.frame_change_pre.insert(0,frameChangeRELay)
to_console(CONSOLE_PREFIX + " event handlers established.")
