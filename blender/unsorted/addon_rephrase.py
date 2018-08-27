
# RE:Phrase 1.3 allows for the animation of the body of a font object.
# New features are:
#    Sub mesh parenting allows entire phrase to use mesh based modifiers to affect layout.
#    Cap generation for characters.
#    Automatic material mapping from the RE:Phrase master object to  all characters (slot1=base,slot2=cap).
#    Render bug fix reduces the chance of ever having two character exactly overlapping (removes that black flicker in animations)
#    Multiple phrases support.
#    Selection of all characters that make up a phrase.
#    Can use the first particle system of mesh emitter for the LOC/ROT of characters on a per-phrase basis.
#    Experimental crash recovery system.
#    New auto-kerning feature for the layout engine.
#    Justification and per-word or per-character deployment. 
# Atom (c) 2012
# 265_rephrase_plus_1k
# 266_rephrase_plus_1L  02212013.

import bpy
import mathutils
from mathutils import Matrix, Vector
from math import acos, sin, cos, pi, radians

import threading, time
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty, EnumProperty

#bpy.app.debug = True

############################################################################
# Globals, yes ugh!
############################################################################
isBusy = False                  # Global busy flag. Try to avoid events if we are already busy.
isBusyCount = 0                 # Accumulate how many events we are missing.

# Objects are managed by name prefix. Customize here...e.g. my_prefix (no longer than 12 characters)

### NOTE: This code ASSUMES that the data types for the PARENT_PREFIX object is the same as the FONT_PREFIX. In this case, a font curve.
PARENT_PREFIX   = "rephrase_"   # This is the master object that you animate.
CHILD_PREFIX    = "ch_"         # This is a child object used for laying out characters and words.
CAP_PREFIX      = "cp_"         # This is a child of the child (i.e. cap).
FONT_PREFIX     = "fn_ch_"      # This is the data for the child object that recieves it's settings from the parent data which should be of the same type.
CAP_FONT_PREFIX = "fn_cp_"      # This is the data for the cap object that recieves it's settings from the parent data which should be of the same type.
LAYOUT_PREFIX     = "lo_"       # This is the layout mesh object that all characters will be vertex parented to.

MAX_NAME_SIZE = 21              # Maximum length of any object name.
ENTRY_LENGTH = 9                # Only grab the first 9 characters from the list entry name when constructing a character name.
ENTRY_NAME = "Phrase-"          # The default name for new entries.

SPLIT_DELIMITER = ";"           # Special symbol which forces a line break when generating characters.
CHAR_SPACE      = " "           # A Blender font has errors representing space.
SPACE_REPLACE   = "_"           # Swap all spaces in phrase with this replacement character.

############################################################################
# Code for debugging.
############################################################################
DEBUG = True                    # Enable disable debug output.
CONSOLE_PREFIX = "RE:Phrase "

def to_console (passedItem = ""):
    if DEBUG == True:
        if passedItem == "":
            print("")
        else:
            print(CONSOLE_PREFIX + passedItem)

############################################################################
# Parameter Definitiions
############################################################################
def updateREPhraseParameter(self,context):
    # This def gets called when one of the tagged properties changes state.
    global isBusy
        
    if isBusy == False:
        if context != None:
            passedScene = context.scene
            if passedScene != None:
                # Yes, you really need this many IF layers.
                # Even though Ijust fetched the scene it can still be None sometimes.
                cf = passedScene.frame_current
                to_console("")
                to_console("updateREPhraseParameter on frame #" + str(cf))
                reviewRePhrase(passedScene)
            else:   
                to_console("Dang you be all rough and all returnin' a worthless None scene to your homey.")
        else:
            to_console ("And he was like all up in my grill giving me a None context?")
    else:
        to_console ("And now you all busy all the time.")

# Transfer values from RE:Phrase panel directly to master font object.
def updateExtrudeParameter(self,context):
    try:
        context.object.data.extrude = self.extrude
        reviewRePhrase(context.scene)
    except:
        pass

def updateBevelDepthParameter(self,context):
    try:
        context.object.data.bevel_depth = self.bevel_depth
        reviewRePhrase(context.scene)
    except:
        pass

def updateBevelResolutionParameter(self,context):
    try:
        context.object.data.bevel_resolution = self.bevel_resolution
        reviewRePhrase(context.scene)
    except:
        pass

def updateSizeParameter(self,context):
    try:
        context.object.data.size = self.size
        reviewRePhrase(context.scene)
    except:
        pass

def updateShearParameter(self,context):
    try:
        context.object.data.shear = self.shear
        reviewRePhrase(context.scene)
    except:
        pass

def updateOffsetParameter(self,context):
    try:
        print("offset")
        context.object.data.offset = self.offset
        reviewRePhrase(context.scene)
    except:
        pass
                
def updateSpaceCharacterParameter(self,context):
    try:
        context.object.data.space_character = self.space_character
        reviewRePhrase(context.scene)
    except:
        pass

def updateSpaceWordParameter(self,context):
    try:
        context.object.data.space_word = self.space_word
        reviewRePhrase(context.scene)
    except:
        pass
        
def updateSpaceLineParameter(self,context):
    try:
        context.object.data.space_line = self.space_line
        reviewRePhrase(context.scene)
    except:
        pass
      
class cls_REPhrase(bpy.types.PropertyGroup):
    phrase = bpy.props.StringProperty(name="Phrase", description="Type your font body copy here.", update=updateREPhraseParameter)
    emitter_name = bpy.props.StringProperty(name="Emitter Name", description="Type the name of an object with a particle system here.")
    as_words = bpy.props.BoolProperty(name="As Words", description="When active, generated objects are managed at the word level instead of the character level.", default=False, options={'ANIMATABLE'}, subtype='NONE', update=updateREPhraseParameter)
    style_weight = bpy.props.FloatProperty(name="Style Weight", description="Lower values favor kerning based upon character width, higher values favor kerning based upon perceived greyscale values of characters.", default=0.5, min=0.0, max=1.0, step=1, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateREPhraseParameter)    
    spin = bpy.props.FloatProperty(name="Spin", description="Spin characters or words around their base line centerpoint.", default=0.0, min=-360.0, max=360.0, step=36, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateREPhraseParameter)    

    # These properties are used to relay values from the panel directly to the master font object.
    extrude = bpy.props.FloatProperty(name="Extrude", description="The amount of extrusion applied to each character.", default=0.0, min=-0.0, max=0.801, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateExtrudeParameter)    
    bevel_depth = bpy.props.FloatProperty(name="Bevel Depth", description="The amount bevel depth applied to each character.", default=0.015, min=0.0, max=0.801, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateBevelDepthParameter)    
    bevel_resolution = bpy.props.IntProperty(name="Bevel Resolution", description="The amount of bevel resolution applied to each character.", default=1, min=0, max=5, update=updateBevelResolutionParameter)    
    size = bpy.props.FloatProperty(name="Size", description="The size of each character.", default=1.0, min=0.001, max=10.801, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateSizeParameter)    
    shear = bpy.props.FloatProperty(name="Shear", description="The shear of each character.", default=0.0, min=-0.311, max=0.311, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateShearParameter)    
    offset = bpy.props.FloatProperty(name="Offset", description="As bevel increases you can shrink the font outline here with a negative value.", default=0.0, min=-0.20, max=0.2, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateOffsetParameter)    

    space_character = bpy.props.FloatProperty(name="Character", description="The spacing between characters.", default=1.0, min=0.001, max=12.0, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateSpaceCharacterParameter)    
    space_word = bpy.props.FloatProperty(name="Word", description="The spacing between words.", default=1.0, min=0.0, max=12.0, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateSpaceWordParameter)    
    space_line = bpy.props.FloatProperty(name="Line", description="The spacing between lines.", default=1.0, min=0.0, max=12.0, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateSpaceLineParameter)    

    use_caps = bpy.props.BoolProperty(name="Use Caps", description="When active, caps for characters are generated.", default=False, options={'ANIMATABLE'}, subtype='NONE', update=updateREPhraseParameter)
    cap_extrude = bpy.props.FloatProperty(name="Cap Extrude", description="The amount of extrusion applied to each cap character.", default=0.0, min=-0.0, max=0.801, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateExtrudeParameter)    
    cap_bevel_depth = bpy.props.FloatProperty(name="Cap Bevel Depth", description="The amount bevel depth applied to each cap character.", default=0.015, min=0.0, max=0.801, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateBevelDepthParameter)    
    cap_bevel_resolution = bpy.props.IntProperty(name="Cap Bevel Resolution", description="The amount of bevel resolution applied to each cap character.", default=1, min=0, max=5, update=updateBevelResolutionParameter)    
    cap_offset = bpy.props.FloatProperty(name="Cap Offset", description="As bevel increases you can shrink the cap font outline here with a negative value.", default=-0.001, min=-0.20, max=0.2, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateOffsetParameter)    
    cap_z_offset = bpy.props.FloatProperty(name="Cap Z-Offset", description="Position the cap in z-space.", default=0.0, min=-4.0, max=4.0, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateOffsetParameter)    
    cap_size = bpy.props.FloatProperty(name="Cap Size", description="The size of each cap character.", default=0.01, min=0.001, max=10.801, step=3, precision=4, options={'ANIMATABLE'}, subtype='FACTOR', unit='NONE', update=updateSizeParameter)    

    align_types = [
                ("0","Left","left"),
                ("1","Right","right"),
                ("2","Center","center"),
                ]
    align = EnumProperty(name="Align", description="The alignment justification for this phrase.", default="0", items=align_types, update=updateREPhraseParameter)

bpy.utils.register_class(cls_REPhrase)

# Add these properties to every object in the entire Blender system (muha-haa!!)
bpy.types.Object.Rephrase_Selection_Index = bpy.props.IntProperty(min = 1, max = 120, default = 1, description="Animate this value to move through the selection list.", update=updateREPhraseParameter)
bpy.types.Object.Rephrase_List_Index = bpy.props.IntProperty(min= 0,default= 0, description="Internal value, do not animate.")
bpy.types.Object.Rephrase_List = bpy.props.CollectionProperty(type=cls_REPhrase, description="Internal list class.")
   
############################################################################
# Code for returning objects, curves, scenes or meshes.
############################################################################
def fetchIfObject (passedName= ""):
    try:
        result = bpy.data.objects[passedName]
    except:
        result = None
    return result

def fetchIfMesh (passedName= ""):
    try:
        result = bpy.data.meshes[passedName]
    except:
        result = None
    return result

def fetchIfCurve (passedCurveName):
    result = None
    try:
        result = bpy.data.curves[passedCurveName]
    except:
        pass
    return result
    
def fetchIfText3D (passedName):
    result = None
    tempCurve = fetchIfCurve(passedName)
    try:
        n = tempCurve.active_textbox
        #No error, this must be a font curve.
        result = tempCurve
    except:
        #Error, this is a non-font curve.
        pass
    return result

def removeMeshFromMemory (passedMeshName):
    # Extra test because this can crash Blender.
    mesh = bpy.data.meshes[passedMeshName]
    try:
        mesh.user_clear()
        can_continue = True
    except:
        can_continue = False
    
    if can_continue == True:
        try:
            bpy.data.meshes.remove(mesh)
            result = True
        except:
            result = False
    else:
        result = False
        
    return result

def returnScene (passedIndex = 0):
    try:
        return bpy.data.scenes[passedIndex]
    except:
        return None

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

############################################################################
# Code for generating and laying out characters.
############################################################################
def returnShortName(passedName):
    #Return a short portion of a passed name.
    if len(passedName) > 6:
        try:
            result = passedName[(len(passedName)-6):]    #Get the last 6 characters of the passed name.
        except:
            result = None
    else:
        #No need to chop anything, it is already shorter than 7 characters.
        result = passedName
    return result

def returnNameForNumber(passedValue):
    string_number = str(passedValue)
    l = len(string_number)
    result = string_number
    if l == 1: 
        result = "000" + string_number
    if l == 2: 
        result = "00" + string_number
    if l == 3: 
        result = "0" + string_number
    return result

def returnNameForCharacter (passedPrefix, passedCharIndex, passedChar):
    # The naming convention goes like this.
    # prefix + character index number + actual character or phrase.
    # If the length if the phase goes too long, it is trimmed and not used for the name.
    num =  returnNameForNumber(passedCharIndex) + "_"    # This produces a 5 digit number, including the underscore  (i.e. 0001_)
    result = passedPrefix + num + passedChar
    if len(result) > MAX_NAME_SIZE: result = result [:MAX_NAME_SIZE]
    return result

def returnLayoutName(passedName):
    result = LAYOUT_PREFIX + passedName
    return result

def returnChildName(passedPrefix, passedOB):
    # Return the name of a child based upon the parent.
    try:
        name = passedOB.name
    except:
        name = "NA"
    l = len(name)
    result = passedPrefix + name[(l-2):l] +"_"
    return result

def returnBoundingBoxWidth(passedObjectName):
    passedObject = fetchIfObject(passedObjectName)
    if passedObject != None:
        w = passedObject.dimensions[0]/2.0
        return w
    else:
        # ERROR.
        return 0.0001234

def returnCharacterWidthViaImportance (passedCharacters, passedStyleWeight, passedWordSpacing):
    # Rank character weight by most important to least important, following these guide lines by Emil Ruder.
    # Gaps occur, for example, around letters whose forms angle outward or frame an open space (W, Y, V, T, L).
    # In short always try to have a keen eye for the spacing between lettering at large sizes.
    # Emil Ruder refers to a pattern of grey.
    # A wider set text will produce a lighter grey.
    # And closer set will produce a denser black grey.
    # The correct measure for a text should be something between 7-12 words per line.
    # Leading is the pace between lines of text in a given paragraph.
    # Generally a leading of 120% is roughly correct.                        
    # The counter or interior "white" also shares in the form of a letter in greyscale considered layouts.
    
    result = 0.0
    for ch in passedCharacters:
        # Set defaults if character fails all tests.
        width_modifier = 1.0        # Weight based upon the width of the character.
        greyscale_modifier = 1.0    # Weight based upon the greyscale value of the character.
        
        # Do not have the same character in two strings.
        s_LEVEL0 = "W"                          # Extreme width characters go here.
        s_LEVEL1 = "YVTLF7Zmw"                  # Large characters with sloping angles deserve more space.
        s_LEVEL2 = "ABCDEGHJKMNOPQRSUX"         # Other large characters.
        s_LEVEL3 = "nhkrpqdba#@&%_=-+~?"        # Other medium characters.
        s_LEVEL4 = "ijlI`1!+[](){}|\:'/.,*^"    # Thinner characters.
        s_LEVEL5 = " "                          # Control spacing directly.
        if s_LEVEL0.find(ch) != -1: width_modifier = 1.75
        if s_LEVEL1.find(ch) != -1: width_modifier = 1.25      # Make up these values for yourself.
        if s_LEVEL2.find(ch) != -1: width_modifier = 1.0
        if s_LEVEL3.find(ch) != -1: width_modifier = 0.9
        if s_LEVEL4.find(ch) != -1: width_modifier = 0.75
        if s_LEVEL5.find(ch) != -1: width_modifier = 1.0 * passedWordSpacing       # Space for width based layout.
       
        # Do not have the same character in two strings.
        s_OPEN0 = "0OPBCDRQUGS"                 # Characters with large round open areas.
        s_OPEN1 = "HWMNFKEZX%=#&@"              # Characters with dense blocky areas.
        s_OPEN2 = "abdp689"                     # Characters with small round open areas.
        s_OPEN3 = "4Ae57<>vxzw"                 # Characters with angular open areas.
        s_OPEN4 = " "                           # Control spacing directly.
        if s_OPEN0.find(ch) != -1: greyscale_modifier = 1.2    # Make up these values for yourself.
        if s_OPEN1.find(ch) != -1: greyscale_modifier = 1.1
        if s_OPEN2.find(ch) != -1: greyscale_modifier = 0.9
        if s_OPEN3.find(ch) != -1: greyscale_modifier = 0.8
        if s_OPEN4.find(ch) != -1: greyscale_modifier = 1.15 * passedWordSpacing    # Space is worth a little more in a greyscale considered layout.
    
        # We now have two measurements of our character weight.
        # Mix them together based upon the passedWeighStyle.
        if passedStyleWeight < 0.0: passedStyleWeight = 0.0
        if passedStyleWeight > 1.0: passedStyleWeight = 1.0
        wm = width_modifier * (1.0-passedStyleWeight)
        gm = greyscale_modifier * passedStyleWeight
        result = result + (wm + gm)  # Add the two weights together for the final result.
    return result
  
def returnTotalCharactersWidth(passedListOfChars, passedEntry):
    result = 0.0
    widthList = []
    
    #Scan the list of characters.
    for ch in passedListOfChars:
        # Get each characters width from our new kerning def.
        tempWidth = returnCharacterWidthViaImportance(ch,passedEntry.style_weight, passedEntry.space_word) * passedEntry.space_character
        result = result + tempWidth 
        widthList.append(tempWidth)
    return result,widthList

def returnListOfTextItems (passedString, passedMode = 'CHARS'):
    result = []
    # Return a list made up of either characters or words from the passedString.
    if passedMode == "CHARS":
        for ch in passedString:
            result.append(ch)
    else:
        # Return words only delimited by a SPACE.
        result = passedString.split(SPACE_REPLACE)
    return result

def returnFontCurve (passedName,passedChar):
    txt = fetchIfText3D(passedName)
    if txt == None:
        txt = bpy.data.curves.new(passedName,'FONT')
    txt.body = passedChar
    return txt

def unLinkObjectsLike(passedName, passedScene, parentName = ""):
    # Unlink objects named like our passedName.
    isLike = passedName
    l = len(isLike)
    localScene = passedScene
    if localScene != None:
        #print("searching for objects named like [" +isLike + "].")
        #print("parent nane [" + parentName + "].")
        for ob in localScene.objects:
            candidate = ob.name[0:l]
            if isLike == candidate:
                if len(parentName) > 0:
                    try:
                        if ob.parent.name == parentName:
                            #print("unlinking [" + ob.name + "]")
                            localScene.objects.unlink(ob)
                        else:
                            # Has a parent different than the one we are processing.
                            pass
                    except:
                        # No parent specified.
                        #print("UNlinking [" + ob.name + "]")
                        localScene.objects.unlink(ob)    
                else:
                    #print("unLINKing [" + ob.name + "]")
                    localScene.objects.unlink(ob)
    else:
        to_console("ERROR: No scene available, are we rendering?")

def cleanSceneOfRP(passedBaseName):
    # Remove any RE:Phrase constructed objects from memory associated with a given base name.
    result = False
        
    # Construct the custom names for this managed object's stuff.
    name_base = passedBaseName
    localScene = returnScene()

    # Create the names that are related to this managed object.
    myRPOBName = passedBaseName 
    #myTaperOBName = FONT_PREFIX + name_base
    
    # Cleanup font curves.
    ob_list = returnObjectNamesLike(myRPOBName)
    for name in ob_list:
        ob = fetchIfObject(name)
        if ob != None:
            to_console("Cleaning RE:Phrase object [" + name + "].")            
            #cu_temp = ob.data                       # Save the linked data from this object we are removing.
            try:
                localScene.objects.unlink(ob)       # Unlink the object from the scene.
                result = True
            except:
                result = False
    return result
       
def generateCappedCharacter (passedCharacter, passedIndex, passedParent = None, passedScene = None, passedEntry = None):
    result = 0              #Default to successful generation.
    newChar = False         #If a new character is generated, set True, else character was fetched from memory.
    ch = passedCharacter
    charIndex = passedIndex
    #localScene = returnScene()
    
    # Create Text3D datablocks with our specific names and settings.
    tempFontName = returnNameForCharacter(returnChildName(FONT_PREFIX, passedParent), charIndex, ch)
    txtBase = returnFontCurve (tempFontName,passedCharacter)    # This def sets the character body/text.
                    
    # Create a scene object to link our 3D base text to.
    tempObjectName = returnNameForCharacter(returnChildName(CHILD_PREFIX, passedParent), charIndex, ch)
    obBase = fetchIfObject(tempObjectName)
    if obBase == None:
        newChar = True
        to_console("Generating a new BASE object [" + tempObjectName + "].")
        txtBase.align = 'CENTER'
        obBase = bpy.data.objects.new(tempObjectName, txtBase)
    
    # Linking...
    try:
        passedScene.objects.link(obBase)     # Make sure the font object is linked to scene.
    except:
        pass
    
    if passedCharacter == SPACE_REPLACE:
        # Make sure our space replacer does not get rendered.
        obBase.hide_render = True
    else:
        if passedEntry.use_caps == True:
            # If it is not a space let's generate a CAP.
            # Create Text3D datablocks with our specific names and settings.
            tempFontName = returnNameForCharacter(returnChildName(CAP_FONT_PREFIX, passedParent), charIndex, ch)
            txtCap = returnFontCurve (tempFontName,passedCharacter)    # This def sets the character body/text.
                            
            # Create a scene object to link our 3D base text to.
            tempObjectName = returnNameForCharacter(returnChildName(CAP_PREFIX, passedParent), charIndex, ch)
            obCap = fetchIfObject(tempObjectName)
            if obCap == None:
                newChar = True
                to_console("Generating a new CAP object [" + tempObjectName + "].")
                txtCap.align = 'CENTER'
                obCap = bpy.data.objects.new(tempObjectName, txtCap)
            
            # Linking...
            try:
                passedScene.objects.link(obCap)     # Make sure the font object is linked to scene.
                obCap.parent = obBase
            except:
                pass

    #No need to allow selections on these managed characters or words.
    #obBase.hide_select = False
    
    return newChar

def generateCharacters(passedEntry, passedParent = None, passedScene = None):
    passedPhrase = passedEntry.phrase
    #Generate letters or words in memory.
    if passedEntry.as_words == True: 
        mode = 'WORDS'
    else:
        mode = 'CHARS'

    # Let's examine the characters and split into new lines where our ; delimiter is encountered.
    linesOfText = passedPhrase.split(SPLIT_DELIMITER)

    # External loop variables.
    lineIndex = 1
    charIndex = 1
    for lineOfCharacters in linesOfText:
        if len(lineOfCharacters) > 0:
            listOfItems = returnListOfTextItems (lineOfCharacters, mode)  # Can also pass 'WORDS'
            for singleItem in listOfItems:
                ch = singleItem
                generateCappedCharacter(ch,charIndex, passedParent, passedScene, passedEntry)
                charIndex = charIndex + 1                       # Move to the next character in the text.
        else:
            to_console("generateCharacters: Blank line encountered?")
        lineIndex = lineIndex + 1

def returnParticleLOCROT(passedMatrix, passedParticleSystem, passedParticleIndex):
    resultLOC = None
    resultROT = None
    # Location matrix.
    m1 = mathutils.Matrix(passedMatrix)
    m1.invert()
    ps = passedParticleSystem 
    if ps != None:
        #to_console("particle system is valid.")
        # Create a list of alive particles that our characters can be bound to.
        alive_particles = []
        n = 1
        for x in ps.particles:
            if x.alive_state == 'ALIVE':
                #alive_particles.append(n)
                if n == passedParticleIndex:
                    resultLOC = x.location * m1
                    resultROT = x.rotation
                    break;
            n = n + 1
    return resultLOC, resultROT
            
def layoutCharacters(passedScene, passedObjectName, passedEntry):
    # Layout the generated characters based upon settings..
    passedPhraseCharacters = passedEntry.phrase
    result = 0                      # Assume successful layout.
    localScene = passedScene
    obParent = fetchIfObject(passedObjectName)      # obParent is the RE:Phrase font object.
    if obParent != None:
        if passedEntry.as_words == True: 
            mode = 'WORDS'
        else:
            mode = 'CHARS'
            
        # Fetch the material from the parent object.
        if len(obParent.data.materials) > 0:
            mat_parent = obParent.data.materials[0]         # Transfer the first material to the base.
            if len(obParent.data.materials) > 1:
                mat_cap = obParent.data.materials[1]        # Transfer the second material to the cap.
            else:
                mat_cap = None
        else:
            # Should we make a default material here?
            mat_parent = None
            mat_cap = None
          
        # External loop variables.
        tempLocX = 0.0  #obParent.LocX
        tempLocY = 0.0  #obParent.LocY
        tempLocZ = 0.0  #obParent.LocZ
        tempAlign = 0
        render_bug_fix = 0.001
        
        try:
            da = obParent.data
            wordSpacing      = passedEntry.space_word
            charSpacing      = passedEntry.space_character
            charExtrude      = passedEntry.extrude
            charBevelDepth   = passedEntry.bevel_depth
            charBevelReso    = passedEntry.bevel_resolution
            charSize         = passedEntry.size
            charShear        = passedEntry.shear
            charOffset       = passedEntry.offset
            charResoU        = da.resolution_u
            charPassIndex    = obParent.pass_index
            #to_console("Fetching font parameters from [" + passedObjectName + "].")
        except:
            # Sometimes fetching properties fails when rendering.
            wordSpacing = 1.0
            charSpacing = 1.0
            charExtrude = 0.05
            charBevelDepth = 0.003
            charBevelReso = 3
            charPassIndex = 2
            charSize = 1.0
            charShear = 0.0
            charOffset = 0.0
            charResoU = 12
            to_console("ERROR: Fetching font values from [" + passedObjectName + "].")

        # Let's examine the characters and split into new lines where our ; delimiter is encountered.
        linesOfText = passedPhraseCharacters.split(SPLIT_DELIMITER)        
        lineIndex = 1
        charIndex = 1
        for lineOfCharacters in linesOfText:
            if len(lineOfCharacters) > 0:
                accumulatedCharacterWidth = 0.0
                listOfItems = returnListOfTextItems (lineOfCharacters, mode)
                space_width = (returnCharacterWidthViaImportance(" ", passedEntry.style_weight, passedEntry.space_word)* wordSpacing)
                totalLineWidth,charsWidthList = returnTotalCharactersWidth(listOfItems,passedEntry)
                for singleItem in listOfItems:
                    ch = singleItem
                    tempChildName = returnNameForCharacter(returnChildName(CHILD_PREFIX, obParent), charIndex, ch)
                    tempCapName = returnNameForCharacter(returnChildName(CAP_PREFIX, obParent), charIndex, ch)
                    obChar = fetchIfObject(tempChildName)
                    if obChar != None:
                        # Transfer the font from the master font object to the child if they are not the same.
                        try:
                            if obParent.data.font.name != obChar.data.font.name:
                                # Try to assign font.
                                obChar.data.font = obParent.data.font
                        except:
                            to_console("Font transfer to child character failed.")
                        
                        if passedEntry.as_words == True:
                            # Just get the bounding box width for this word and add a space to it.    
                            characterWidth = obChar.dimensions[0] + space_width 
                        else:
                            # Use new kerning def to determine character width.
                            characterWidth = (returnCharacterWidthViaImportance(ch, passedEntry.style_weight, passedEntry.space_word))
                        
                        #print("[" + ch + "] " + str(obChar.dimensions[0]))
                        # Assign the material from the parent to the generated character.
                        if mat_parent != None:
                            if len(obChar.data.materials) == 0:
                                obChar.data.materials.append(mat_parent)
                                    
                        try:               
                            # Relay some settings from our parent font object to this specific character.
                            obChar.data.extrude = charExtrude
                            obChar.data.bevel_depth = charBevelDepth
                            obChar.data.bevel_resolution = charBevelReso
                            obChar.pass_index = charPassIndex
                            obChar.data.size = charSize
                            obChar.data.shear = charShear
                            obChar.data.offset = charOffset
                            obChar.data.resolution_u = charResoU
                        except:
                            to_console("Context error, more than likely.")
                                                        
                        # Determine our horizontal offset based upon our alignment choice.
                        if passedEntry.align == "0":
                            # Left align.
                            alignLocX = obParent.location.x
                            #to_console("Align Left produces an initial LocX:" + str(alignLocX) + ".")
                        if passedEntry.align == "1":
                            # Right align.
                            alignLocX = obParent.location.x-totalLineWidth 
                            #to_console("Align Right produces an initial LocX:" + str(alignLocX) + ".")
                        if passedEntry.align == "2":
                            # Center align.
                            alignLocX = obParent.location.x-(totalLineWidth/2.0)
                            #to_console("Align Center produces an initial LocX:" + str(alignLocX) + ".")

                        # Calculate our characters location.
                        # Offset  even/odd characters slightly in z-space to prevent render bug when face share same exact space (i.e. tightly spaced phrases)
                        tempLocX = alignLocX + accumulatedCharacterWidth
                        if charIndex%2==0:
                            # Even.
                            tempLocZ = tempLocZ + render_bug_fix
                            tempLocY = tempLocY + render_bug_fix
                        else:
                            # Odd.
                            tempLocZ = tempLocZ - render_bug_fix
                            tempLocY = tempLocY - render_bug_fix
                        
                        # Assign location and rotation based upon whether or not a valid particle system is provided.
                        use_particle = False
                        if passedEntry.emitter_name != "":
                            # Use particle system for location of characters.
                            ob_emitter = fetchIfObject(passedEntry.emitter_name)
                            if ob_emitter != None:
                                # Got an object.
                                if ob_emitter.particle_systems:
                                    # RE:Phrase only operates on the first particle system in the list.
                                    ps = ob_emitter.particle_systems[0]
                                    if ps != None:
                                        tempLOC, tempROT = returnParticleLOCROT(ob_emitter.matrix_world, ps, charIndex)
                                        if tempLOC != None:
                                            if tempROT != None:
                                                use_particle = True

                        if use_particle == False:
                            # Assign LOC/ROT.
                            obChar.rotation_mode = 'XYZ'
                            obChar.location = [tempLocX, tempLocY, tempLocZ]
                            obChar.rotation_euler = [0.0,0.0,0.0]
                        else:
                            # Assign from particle data.
                            obChar.rotation_mode = 'QUATERNION'
                            obChar.location = tempLOC
                            obChar.rotation_quaternion = tempROT
                            
                        obCap = fetchIfObject(tempCapName)
                        if obCap != None:
                            if obCap.type == 'FONT':
                                if passedEntry.use_caps == True:
                                    # Transfer the font from the master font object to the cap child if they are not the same.
                                    try:
                                        if obParent.data.font.name != obCap.data.font.name:
                                            # Try to assign font.
                                            obCap.data.font = obParent.data.font
                                        else:
                                            pass
                                            #to_console("Font name [" + obParent.data.font.name+"] equals [" + obCap.data.font.name + "].")
                                    except:
                                        to_console("Font transfer to cap child character failed.")
                                        
                                    try:
                                        # Copy base settings.
                                        obCap.data.extrude = passedEntry.cap_extrude
                                        obCap.data.bevel_depth = passedEntry.cap_bevel_depth
                                        obCap.data.bevel_resolution = passedEntry.cap_bevel_resolution
                                        obCap.pass_index = charPassIndex
                                        obCap.data.size = charSize  #passedEntry.cap_size
                                        obCap.data.shear = charShear
                                        obCap.data.offset = passedEntry.cap_offset
                                        obCap.data.resolution_u = charResoU 
                                    except:
                                        to_console("Context error, more thaN likely.")

                                    # Assign the material from the parent to the generated cap character.
                                    if mat_cap != None:
                                        if len(obCap.data.materials) == 0:
                                            obCap.data.materials.append(mat_cap)
                                        else:
                                            pass
                                            #print("cap already has material")
                                    else:
                                        print ("cap material is None.")
                                                
                                    obCap.location[2] = passedEntry.cap_z_offset        
                                else:
                                    # Make sure cap characters are removed from the scene.
                                    try:
                                        passedScene.objects.unlink(obCap)
                                    except:
                                        # Already unlinked.
                                        pass
                                    
                        # Update our counters and accumulators.        
                        charIndex = charIndex + 1                       # Move to the next character in the text.

                        # Determine spacing.
                        if ch == SPACE_REPLACE:
                            # This character is a space, so let's use the word spacing parameter instead.
                            accumulatedCharacterWidth = accumulatedCharacterWidth + (characterWidth * wordSpacing)
                        else:
                            # Character or phrase spacing.
                            accumulatedCharacterWidth = accumulatedCharacterWidth + (characterWidth * charSpacing)
                    else:
                        result = 1
                        to_console("layoutCharacters: WARNING: Could not locate generated character [" + tempChildName + "].")
                lineIndex = lineIndex + 1
            else:
                result = 2
                to_console("layoutCharacters: WARNING: No characters to generate?")
            tempLocY = tempLocY - float(obParent.data.space_line)
            tempLocX = obParent.location.x
    else:
        result = 2
        to_console("layoutCharacters: WARNING: RE:Phrase parent [" + passedObjectName + "] does not exist.")
    
############################################################################
# Code for vertex parenting objects to a generated mesh.
############################################################################ 
def returnSingleTriangleMesh(passedName, passedLocation):
    me = fetchIfMesh (passedName)
    if me == None:
        vp_points = []
        vp_faces = []
        vp_objects = []
        
        # A triangle that points to top of screen when looking straight down on it.
        vp_D1 = Vector([0.5, 0.5, 0.0])
        vp_D2 = Vector([0.0, -1.0, 0.0])
        vp_D3 = Vector([1.0, -1.0, 0.0])
        vp_scale = 0.1
        c = 0
    
        # Single triangle object at world origin.
        dd = Vector(passedLocation)
        vp_points.append(dd+vp_D1*vp_scale)
        vp_points.append(dd+vp_D2*vp_scale)
        vp_points.append(dd+vp_D3*vp_scale)
        vp_faces.append([c,c+1,c+2])        
    
        me = bpy.data.meshes.new(passedName)
        me.from_pydata(vp_points,[],vp_faces)
    else:
        # Just use the existing mesh.
        pass
    
    # Make sure all verts are deselected.
    for v in me.vertices:
        v.select = False
    me.update()
    return me

def returnLayoutObject (passedName, passedScene):
    ob = None
    me = returnSingleTriangleMesh("me_" + passedName,[0.0,0.0,0.0])
    if me != None:
        try:
            ob = bpy.data.objects.new(passedName,me)
            passedScene.objects.link(ob)
        except:
            pass    
    return ob

def returnTriangleForEachObject(passedNameList):
    vp_points = []
    vp_faces = []
    vp_objects = []
    
    # A triangle that points to top of screen when looking straight down on it.
    vp_D1 = Vector([0.5, 0.5, 0.0])
    vp_D2 = Vector([0.0, -1.0, 0.0])
    vp_D3 = Vector([1.0, -1.0, 0.0])
    vp_scale = 0.1
            
    c = 0
    l = len(passedNameList)
    if l > 0:
        for name in passedNameList:
            ob = fetchIfObject(name)
            if ob != None:
                vp_objects.append(ob)
                dd = ob.location
                vp_points.append(dd+vp_D2*vp_scale)
                vp_points.append(dd+vp_D3*vp_scale)
                vp_points.append(dd+vp_D1*vp_scale)
                vp_faces.append([c,c+1,c+2])
                c+=3
    else:
        # If no list is passed assume single object at world origin.
        dd = Vector([0.0,0.0,0.0])
        vp_points.append(dd+vp_D1*vp_scale)
        vp_points.append(dd+vp_D2*vp_scale)
        vp_points.append(dd+vp_D3*vp_scale)
        vp_faces.append([c,c+1,c+2])        

    me = bpy.data.meshes.new('me_RE_layout')
    me.from_pydata(vp_points,[],vp_faces)
    
    # Make sure all verts are deselected.
    for v in me.vertices:
        v.select = False
    me.update()
    return me

def vertexParentObjectsToMesh(passedNameList, passedParent, passedEntry):
    if passedParent != None:
        if passedParent.type == 'MESH':
            me = passedParent.data
            for c,face in enumerate(me.polygons):
                # Try to alter the way the triangle is oriented, this is a HACK (that offers up an opportunity for a feature).
                localRotateDegrees = passedEntry.spin
                # We lost our face.center when bMesh was implmented. (Boo!)
                p_center = [0.0, 0.0, 0.0]
                for v in face.vertices:
                    p_center[0] += me.vertices[v].co[0]        
                    p_center[1] += me.vertices[v].co[1]
                    p_center[2] += me.vertices[v].co[2]
                p_center[0] /= len(face.vertices) # division by zero               
                p_center[1] /= len(face.vertices) # division by zero               
                p_center[2] /= len(face.vertices) # division by zero        
                #print (p_center) # center in local coordinates
    
                rotateFaceAroundPoint (me, face.vertices,p_center,face.normal,localRotateDegrees)
               
                ob = fetchIfObject(passedNameList[c])
                #to_console("Vertex parenting [" +passedNameList[c]+ "] to  [" + passedParent.name + "].")
                if ob != None:
                    ob.parent = passedParent
                    ob.matrix_world = passedParent.matrix_world
                    ob.parent_type = 'VERTEX_3'
                    v = (c*3)
                    ob.parent_vertices = [v,v+1,v+2]
                else:
                    to_console("vertexParentObjectsToMesh: [" + passedNameList[c] +"] in vertex parent list, but not available?")
            passedParent.data.update()
        else:
            # Our parent is not a mesh...?
            to_console("vertexParentObjectsToMesh: Our parent is not a mesh..?")
    else:
        to_console("vertexParentObjectsToMesh: Parent received was None.")

# Begin FunkyWyrm code.
def rotateFaceAroundPoint(passedMesh, passedVertList, point, axis, angle):
    translation = Vector(point)
    rotation = Matrix.Rotation(radians(angle), 4, -Vector(axis))
    
    for vert_index in passedVertList:
        passedMesh.vertices[vert_index].co = passedMesh.vertices[vert_index].co - translation
        passedMesh.vertices[vert_index].co = passedMesh.vertices[vert_index].co * rotation
        passedMesh.vertices[vert_index].co = passedMesh.vertices[vert_index].co + translation
# End FunkyWyrm code.
            
############################################################################
# frameChange code.
############################################################################
def frameChangeRePhrase(passedScene):
    global isBusy, isBusyCount

    if isBusy == False:
        isBusy = True
        reviewRePhrase(passedScene)
        isBusy = False
        isBusyCount = 0
    else:
        # We are either still busy in reviewRePhrase or we crashed inside reviewRePhrase.
        # Sometimes a crash can occur when Blender gives us bad data or just bad timing (i.e. bpy.data is in a wierd state).
        isBusyCount = isBusyCount + 1
        if isBusyCount > 64:    #Arbitrary number, you decide.
            # We have missed a number of events so it may have been a crash.
            # If the crash was caused simply by bad timing or data error,
            # somethimes abandoning this isBusy = True state can allow the AddOn to function again.
            isBusy = False      # Allow the AddOn to try to function again.
            isBusyCount = 0     # Reset to zero, if it is a true crash we will just end up here again.
            to_console("Attempting to recover from an isBusy crash state.")

def reviewRePhrase(passedScene):
    passedFrame = passedScene.frame_current
    ob_list = returnObjectNamesLike(PARENT_PREFIX)
    if len(ob_list) > 0:
        for name in ob_list:
            current_phrase = ""
            ob = fetchIfObject(name)
            if ob !=None:
                # This is an object that is managed by this script.
                try:
                    ob.data.body = ""   # The parent object is assumed to still be a font data type, but it's body is blank.
                except:
                    pass
                
                # Try to fetch custom properties. 
                try:
                    enabled = ob["enabled"]
                except:
                    enabled = 0
                    to_console("FAILED: enabled")
                                    
                try:
                    phrase_index = ob["Rephrase_Selection_Index"]
                    phrase_index = phrase_index - 1
                    # Keep it in bound if possible.
                    if phrase_index < 0: phrase_index = 0
                    if phrase_index > len(ob.Rephrase_List):phrase_index = len(ob.Rephrase_List)
                except:
                    enabled = 0
                    to_console("FAILED: Rephrase_List_Index")
                                      
                try: 
                    entry = ob.Rephrase_List[phrase_index] 
                    current_phrase = entry.phrase
                    current_phrase = current_phrase.replace(CHAR_SPACE, SPACE_REPLACE)
                except:
                    enabled = 0
                    to_console("FAILED: current_phrase")

                if enabled == 1:
                    # unlink caps first because they are parented to the child.
                    unLinkObjectsLike(returnChildName(CAP_PREFIX, ob), passedScene, "")                             # Unlink all child objects named like our prefix.     
                    unLinkObjectsLike(returnChildName(CHILD_PREFIX, ob), passedScene, returnLayoutName(name))       # Unlink all child objects named like our prefix.
            
                    if len(current_phrase) > 0:
                        to_console("")
                        to_console("#" + str(passedFrame) + " Updating [" + name + "] using phrase [" + current_phrase + "].")

                        generateCharacters(entry, ob, passedScene)
                        layoutCharacters (passedScene, name, entry)
                
                        # Review the characters just generated and make a mesh that we can vertex parent all those characters to.
                        chars_prefix = returnChildName(CHILD_PREFIX, ob)
                        ob_list = returnObjectNamesLike(chars_prefix)
                        lo_name = returnLayoutName(ob.name)
                        ob_lo = fetchIfObject(lo_name)
                        if ob_lo == None:
                            # The layout mesh object does not exist, lets create it.
                            # RE:Phrase uses a sub-mesh parenting system so mesh based modifiers can be applied to generated characters.
          
                            # This means we need to create the sub-parent mesh now and derive it's name from our name.
                            lo_name = returnLayoutName(ob.name)
                            ob_lo = returnLayoutObject (lo_name, passedScene)
                            # Make the layout object a child of the master reprhase object.
                            ob_lo.parent = ob       
                            ob_lo.hide_render = True
                            ob_lo.draw_type = 'WIRE'
                        old_mesh = ob_lo.data
                        me_new = returnTriangleForEachObject(ob_list)
                        ob_lo.data = me_new                           # Assign the new triangle mesh to the object.
                        vertexParentObjectsToMesh(ob_list,ob_lo,entry)
                        removeMeshFromMemory (old_mesh.name)
                    else:
                        # A zero length phrase.
                        pass
                else:
                    # Rephrase is not enabled.
                    to_console("is not enabled.")
            else:
                to_console ("Failed to fetch RE:Phrase object [" + name + "].")
    else:
        to_console("No RE:Phrase objects named like [" + PARENT_PREFIX + "] detected in the scene.")

############################################################################
# Thread processing for parameters that are invalid to set in a DRAW context.
# By performing those operations in these threads we can get around the invalid CONTEXT error within a draw event.
# This is fairly abusive to the system and may result in instability of operation.
# Then again as long as you trap for stale data it just might work..?
# For best result keep the sleep time as quick as possible...no long delays here.
############################################################################
def rephrase_new_source(lock, passedSourceName, passedSleepTime):
    global isBusy
    
    myBusy = isBusy
    isBusy = True
    time.sleep(passedSleepTime) # Feel free to alter time in seconds as needed.   
    to_console("Threading: rephrase_new_source")
    ob_source = fetchIfObject(passedSourceName)
    if ob_source !=None:
        ob_source.show_name = True
        ob_source.hide_render = True  
                                            
        # Populate the new entry in the collection list.
        collection = ob_source.Rephrase_List
        collection.add()
        l = len(collection)
        collection[-1].name= (ENTRY_NAME+str(l))
        try:
            collection[-1].phrase = ob_source.data.body    # Assign the current font body as the initial phrase.
            ob_source.data.body = ""                       # Make the current font body blank.
            to_console("Threading: New entry established on [" + passedSourceName + "].")
        except:
            pass
            to_console("Threading: Managing the text body of [" + passedSourceName + "].")
    else:
        to_console("Threading: " + CONSOLE_PREFIX + " source not found [" + passedSourceName + "].") 
    isBusy = myBusy
    
def rephrase_add_properties(lock, passedSourceName, passedSleepTime):
    global isBusy
    
    myBusy = isBusy
    isBusy = True
    time.sleep(passedSleepTime) # Feel free to alter time in seconds as needed.   
    to_console("Threading: rephrase_add_properties")
    ob_source = fetchIfObject(passedSourceName)
    if ob_source != None:
        try:
            ob_source["enabled"] = 1
            ob_source["Rephrase_List_Index"] = 0
            ob_source["Rephrase_Selection_Index"] = 1
            to_console("Threading: custom properties added to [" + passedSourceName + "].")
        except:
            to_console("Threading: unable to add enabled custom property to [" + passedSourceName + "] at this time.") 
    isBusy = myBusy
            
############################################################################
# PANEL code.
############################################################################
# Create operator to rename this object with the relay_ preifix.   
class OBJECT_OT_rename_to_rephrase(bpy.types.Operator):
    bl_label = "Rename To RE:Phrase"
    bl_idname = "op.rename_to_rephrase"
    bl_description = "Click this button to rename this object with the rephrase_ prefix. This will make it a RE:Phrase object."
    
    def invoke(self, context, event):
        ob = context.object
        if ob != None:
            rephrase_name = PARENT_PREFIX + ob.name
            if len(rephrase_name) > MAX_NAME_SIZE:
                # Name too long.
                rephrase_name = rephrase_name[:MAX_NAME_SIZE]
            ob_source = fetchIfObject(rephrase_name)
            if ob_source != None:
                # Hmm...already and object named like this.
                to_console ("Already an object named like [" + rephrase_name + "] rename manualy.")
            else:
                ob.name = rephrase_name
        return {'FINISHED'}

    
# Create operator to select the characters.
class OBJECT_OT_Select_Characters(bpy.types.Operator):
    bl_label = "SelectCharacters"
    bl_description ="Select the characters that are part of this phrase."
    bl_idname = "op.select_characters"
    
    def invoke(self,context,event):
        ob = context.object
        if ob != None:
            bpy.ops.object.select_all(action='DESELECT')
            lo_name = returnLayoutName(ob.name)
            lst = returnObjectNamesLike(CHILD_PREFIX)
            for name in lst:
                to_console(name)
                ob_candidate = fetchIfObject(name)
                if ob_candidate != None:
                    if ob_candidate.parent.name == lo_name:
                        # Select this object
                        ob_candidate.select = True
        return {'FINISHED'}
    
# create operator to add or remove entries to/from  the Collection
class OBJECT_OT_add_remove_Phrase_Items(bpy.types.Operator):
    bl_label = "Add or Remove"
    bl_idname = "collection.add_remove"
    add = bpy.props.BoolProperty(default = True)
    
    def invoke(self, context, event):
        add = self.add
        ob = context.object
        if ob != None:
            collection = ob.Rephrase_List
            if add:
                # This adds at the end of the collection list.
                collection.add()
                l = len(collection)
                collection[-1].name= (ENTRY_NAME+str(l))
                collection[-1].phrase = ("RE:Phrase+ "+str(l))
            else:
                l = len(collection)
                if l > 1:
                    # This removes one item in the collection list function of index value
                    index = ob.Rephrase_List_Index
                    collection.remove(index)
                else:
                    to_console ("Can not remove last phrase.")
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
             
class OBJECT_PT_RePhrase(bpy.types.Panel):
    bl_label = "RE:Phrase+ 1.4"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
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
                if ob.type == 'FONT':
                    layout = self.layout
                    l = len(PARENT_PREFIX)
                    if ob.name[:l] == PARENT_PREFIX:
                        try:
                            enabled = ob["enabled"]
                        except:
                            enabled = 0
                            
                        if enabled == 1:
                            try:
                                l = len(ob.Rephrase_List)
                            except:
                                l = 0
                            if l > 0:
                                layout = self.layout
                                box1 = layout.box()
                                
                                #show collection in Panel:
                                box1.label(" Phrases:",icon="OUTLINER_DATA_FONT")
                                row = box1.row()
                                row.template_list("ATOMS_265_UI_Template_List","rephrase_entry",ob, "Rephrase_List", ob, "Rephrase_List_Index",4,4)          # This show list for the collection
                                
                                #show add/remove Operator
                                col = row.column(align=True)
                                col.operator("collection.add_remove", icon="ZOOMIN", text="")              # This show a plus sign button
                                col.operator("collection.add_remove", icon="ZOOMOUT", text="").add = False # This show a minus sign button
                                col.separator()
                                col.separator()
                                col.operator("op.select_characters", icon="RESTRICT_SELECT_OFF", text="")
                                
                                #change name of Entry:
                                if ob.Rephrase_List:
                                    #show self created properties of Phrases
                                    entry = ob.Rephrase_List[ob.Rephrase_List_Index]
                                    box1.prop(entry, "phrase")
                                    #box1.prop(entry, 'align')
                                    #box1.prop(entry, "as_words")
                                    row = box1.row()             # Create a new row to move to the next line in the box or layout.
                                    col_1 = row.split(50)
                                    col_2 = row.split(50)
                                    col_1.prop(entry, 'as_words')
                                    col_2.prop(entry, "align")
                                    
                                    #box1.prop(entry, "resolution_u", text = "Viewport Resolution")

                                    box = box1.box()
                                    box.label(" Geometry:",icon="MOD_SOLIDIFY")
                                    box.prop(entry, "extrude")
                                    box.prop(entry, "bevel_depth")
                                    box.prop(entry, "bevel_resolution")
                                    box.prop(entry, "offset")
                                    box.prop(entry, "size")
                                    box.prop(entry, "shear")
                                    box.prop(entry, "spin")

                                    box = box1.box()
                                    box.label(" Caps:",icon="MOD_UVPROJECT")
                                    box.prop(entry, "use_caps")
                                    box.prop(entry, "cap_extrude")
                                    box.prop(entry, "cap_bevel_depth")
                                    box.prop(entry, "cap_bevel_resolution")
                                    box.prop(entry, "cap_offset")
                                    #box.prop(entry, "cap_size")
                                    box.prop(entry, "cap_z_offset")
                                                                                                            
                                    box = box1.box()
                                    box.label(" Spacing:",icon="ARROW_LEFTRIGHT")
                                    box.prop(entry, "style_weight")
                                    box.prop(entry, "space_character")
                                    box.prop(entry, "space_word")
                                    box.prop(entry, "space_line")
                                    
                                    box1.separator()
                                    box = box1.box()
                                    box.label(" Particle System:",icon="PARTICLES")
                                    
                                    # Let's let the icon offer a little feedback.
                                    if fetchIfObject(entry.emitter_name) == None:      # Should be fetchIfPsys()
                                        box.prop(entry, "emitter_name", icon='QUESTION')
                                    else:
                                        box.prop(entry, "emitter_name", icon='PARTICLES')
                                    
                                layout.separator()
                                box = layout.box()     
                                layout.separator()
                                
                                # New box for new items.
                                box = layout.box()
                                box.label(" Animation:", icon="FORCE_HARMONIC")
                                box.prop(ob,'["Rephrase_Selection_Index"]', text="Animate Active Phrase")
                            else:
                                # This object has a zero length Relay_List collection. 
                                # It is named like 'rephrase_' so lets convert it into a REPhrase managed object.
                                    
                                # Add a new entry in the collection list. We only want one.
                                #collection = ob.Rephrase_List
                                #collection.add()                                     
                                
                                # Launch a thread to set the remaining values that would generate a CONTEXT error if issued now. (listed below)
                                lock = threading.Lock()
                                lock_holder = threading.Thread(target=rephrase_new_source, args=(lock,ob.name,0.02), name='REPhrase_New_Source')
                                lock_holder.setDaemon(True)
                                lock_holder.start()
                        else:
                            # A REPhrase named object without an 'enabled' custom property.
                            # This is basically a new object creation intercept.

                            # Lets add the 'enabled' custom property and turn it on.
                            #ob["enabled"] = 1
                            #ob["REPhrase_Selection_Index"] = 0
                            
                            # Launch a thread to set any values that would generate a CONTEXT error if issued now.
                            lock = threading.Lock()
                            lock_holder = threading.Thread(target=rephrase_add_properties, args=(lock,ob.name,0.02), name='REPhrase_Add_Properties')
                            lock_holder.setDaemon(True)
                            lock_holder.start()                            
                    else:
                        l1 = len(CHILD_PREFIX)
                        l2 = len(CAP_PREFIX)
                        if ob.name[:l1] == CHILD_PREFIX:
                            layout.label("This may be a " + CONSOLE_PREFIX + " character.",icon='FONT_DATA')  
                        elif ob.name[:l2] == CAP_PREFIX:
                            layout.label("This may be a " + CONSOLE_PREFIX + " cap character.",icon='FONT_DATA') 
                        else:
                            layout.label("Not a " + CONSOLE_PREFIX + " object yet.",icon='INFO')  
                            #layout.label("(rename with '" + PARENT_PREFIX +"' prefix to enable)")
                            layout.operator("op.rename_to_rephrase", icon="SORTALPHA", text="(rename with '" + PARENT_PREFIX +"' prefix to enable)")
                else:
                    # Only allow a font object to be extended with RE:Phrase properties.
                    pass
        else:
            # This can happen sometimes after a render.
            to_console (CONSOLE_PREFIX + " was given an invalid context, imagine that..")
            self.layout.label(CONSOLE_PREFIX + " was given an invalid context.",icon='HELP')
                
#### REGISTER ####
def register():
    # Panel
    to_console("Registering classes...")
    bpy.utils.register_class(OBJECT_PT_RePhrase)
    bpy.utils.register_class(OBJECT_OT_add_remove_Phrase_Items)
    bpy.utils.register_class(OBJECT_OT_rename_to_rephrase)
    bpy.utils.register_class(OBJECT_OT_Select_Characters)
    bpy.utils.register_class(ATOMS_265_UI_Template_List)

def unregister():
    # Panel
    to_console("Unregistering classes...")
    bpy.utils.unregister_class(OBJECT_PT_RePhrase)
    bpy.utils.unregister_class(OBJECT_OT_add_remove_Phrase_Items)
    bpy.utils.unregister_class(OBJECT_OT_rename_to_rephrase)
    bpy.utils.unregister_class(OBJECT_OT_Select_Characters)
    bpy.utils.unregister_class(ATOMS_265_UI_Template_List)

register()   

#bpy.app.driver_namespace['frameChangeRePhrase'] = frameChangeRePhrase

# Setup our event handlers.
#bpy.app.handlers.render_pre.append(framePreREticular)
#bpy.app.handlers.render_post.append(framePostREticular)                      
#bpy.app.handlers.frame_change_pre.append(frameChangeRePhrase)
bpy.app.handlers.frame_change_pre.insert(0,frameChangeRePhrase) #Must run before RE:Lay in a shared handler space.
to_console("Event handlers established.")
    