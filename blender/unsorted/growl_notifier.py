# ***** BEGIN GPL LICENSE BLOCK *****
#
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
# ***** END GPL LICENCE BLOCK *****


import bpy, aud, gntplib, os
from bpy.app.handlers import persistent

### register blender with gntp:

publisher = gntplib.Publisher('Blender',['DESKTOP','EMAIL'])
gntplib.Publisher.register(publisher)

#determine notification style



##Currently, I guess at whether we are rendering animation by looking for render_pre, then frame_change, then render_post.
###

handle = "" #XXX UGLY\

rendering_check = 0
animation_count = 0

@persistent
def render_started(scene):  #This gets assigned to render_pre
    global handle, rendering_check, animation_count
    rendering_check = 1
    #print(rendering_check)

@persistent
def check_animation(scene): #This gets assigned to frame_change_post, used to count frames rendered.
    global handle, rendering_check, animation_count
    if rendering_check == 1:
        animation_count = animation_count + 1
    
    #Display growl notification if warranted
    if scene.growl_notifier.notify_frame:
        if rendering_check:
            frame_current = bpy.context.scene.frame_current
            frame_end = bpy.context.scene.frame_end
            publisher.publish(scene.growl_notifier.notify_style,'Blender',
                              'finished rendering frame ' + str(frame_current))
            if frame_current == frame_end:
                rendering_check = 0

@persistent
def kill_render(scene): #This gets assigned to render_cancel
    global handle, rendering_check, animation_count

    if hasattr(handle, "status") and handle.status == True:
        print("render finished/cancelled.")
        rendering_check = 0
        animation_count = 0

@persistent
def end_render(scene): #This gets assigned to render_complete
    global rendering_check, animation_count
        
    #print("anim:" + str(animation_count))
    if scene.growl_notifier.notify_anim:
        notify_threshold = 2
    elif scene.growl_notifier.notify_image:
        notify_threshold = 1000000
    else:
        notify_threshold = 1000000

    #Gather scene info to display in growl notification.

    filename = str(bpy.data.filepath.rsplit("/")[-1])
    if filename == "":
        file_print = "unsaved blend"
    else:
        file_print = filename
    
    fstart = bpy.context.scene.frame_start
    fend = bpy.context.scene.frame_end
    output_dir = bpy.context.scene.render.filepath
    filetype = bpy.context.scene.render.file_extension
            
    #Display Growl Notification if warranted
    if scene.growl_notifier.notify_image:
        publisher.publish(scene.growl_notifier.notify_style,'Blender', 'Finished rendering ' + file_print + ". \n")
        animation_count=0
        rendering_check=0

    if scene.growl_notifier.notify_anim:
        if animation_count >= notify_threshold:
            
            publisher.publish(scene.growl_notifier.notify_style,'Blender',
                              'Finished rendering ' + file_print + ". \n" 
                              + "Frames: " + str(fstart) + " to " + str(fend) + ". \n"
                              + "Saved to: " + str(output_dir) + " \n"
                              #  + str(percent_rendered*100) +  "% of frames rendered." + ". \n"
                              )
            animation_count = 0
            rendering_check = 0




