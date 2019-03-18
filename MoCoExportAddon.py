bl_info = {
    "name": "Motion Control Export Tool",
    "author": "Josh Sheldon",
    "category": "Import-Export",
    "blender": (2, 7, 9)    
}

import bpy
import bmesh
import math
from bpy.types import Panel, Operator
from mathutils import Vector
from xml.etree import ElementTree as ET

maxAxisCount = 36
removeOperators = []
moveUpOperators = []
moveDownOperators = []

props = None
updatingAxisPositions = False
exportingCameraMovement = False


# Export movement functions




class ExportMovement(Operator):
    bl_idname = 'moco.exportmovement'
    bl_label = 'Export camera movement for Dragonframe'
    
    positions = []
    numFrames = 0
    
    def saveFile(self, fileString, extension):
        bpy.ops.wm.context_set_string(data_path="area.type", value="TEXT_EDITOR")
        bpy.ops.text.new()
        bpy.ops.text.insert(text = fileString)
        bpy.ops.text.save_as(filepath = "//" + props.camera_path_file_name + extension)
        bpy.ops.text.unlink()
        bpy.ops.wm.context_set_string(data_path="area.type", value="VIEW_3D")
    
    
    # Raw export
    def writeRaw(self):
        rawMove = ""
        
        for frame in range(self.numFrames):
            for axisIndex in range(props.moco_num_axis):
                position = self.positions[axisIndex][frame]
                component = getAxisComponent(axisIndex)
                if component == 3 or component == 4 or component == 5:
                    position = math.degrees(position)
                entry = str(position) + "                "
                rawMove = rawMove + entry[:12] + "    "
            rawMove = rawMove + "\n"
        
        self.saveFile(rawMove, '.txt')
        self.report({'INFO'}, "Camera movement exported as Raw Move to " + bpy.path.abspath("//") + props.camera_path_file_name + '.txt') 
    
    def modal(self, context, event):
        global exportingCameraMovement
        
        if event.type == 'TIMER':
            if context.scene.frame_current >= context.scene.frame_end:
                self.writeRaw()
                exportingCameraMovement = False
                return {'FINISHED'}
            
            context.scene.update()
            
            for axis in range(props.moco_num_axis):
                position = getAxisInputPosition(axis)
                if position is None:
                    position = 0
                self.positions[axis].append(position)
                
            bpy.ops.screen.frame_offset(delta = 1)
            self.numFrames += 1
        
        return {'PASS_THROUGH'}


    # XML Export
    def exportXML(self, context):
        root = ET.Element('scen:scene')
        root.set('xmlns:scen', 'http://caliri.com/motion/scene')
        root.set('endframe', str(context.scene.frame_end - context.scene.frame_start))
        
        for axisIndex in range(props.moco_num_axis):
            keyframes = getAxisKeyframes(axisIndex)
            label = getAxisLabel(axisIndex)
            component = getAxisComponent(axisIndex)
            numKeyframes = len(keyframes)
            
            axis = ET.SubElement(root, 'scen:axis')
            axis.set('name', label)
            
            units = None
            if component == 0 or component == 1 or component == 2:
                unitSystem = context.scene.unit_settings.system 
                scaleLen = context.scene.unit_settings.scale_length
                if unitSystem == 'METRIC':
                    if abs(scaleLen - 1) < 0.00001:
                        units = 'm'
                    elif abs(scaleLen - 0.01) < 0.00001:
                        units = 'cm'
                    elif abs(scaleLen - 0.001) < 0.00001:
                        units = 'mm'
                elif unitSystem == 'IMPERIAL':
                    if abs(scaleLen - 1) < 0.00001:
                        units = 'in'
            elif component == 3 or component == 4 or component == 5:
                unitSystem = context.scene.unit_settings.system_rotation
                if unitSystem == 'DEGREES':
                    units = 'deg'
            
            if not (units is None):
                axis.set('units', units)
            
            yMult = 1
            if component == 3 or component == 4 or component == 5:
                yMult = 180 / math.pi
            
            for index, keyframe in enumerate(keyframes):
                point = ET.SubElement(axis, 'scen:points')
                point.set('y', str(keyframe.co[1] * yMult))
                point.set('x', str(keyframe.co[0]))
            
            for index, keyframe in enumerate(keyframes):
                if index > 0:
                    controlpoint = ET.SubElement(axis, 'scen:controlPoints')
                    controlpoint.set('y', str(keyframe.handle_left[1] * yMult))
                    controlpoint.set('x', str(keyframe.handle_left[0]))
                if index < numKeyframes - 1:
                    controlpoint = ET.SubElement(axis, 'scen:controlPoints')
                    controlpoint.set('y', str(keyframe.handle_right[1] * yMult))
                    controlpoint.set('x', str(keyframe.handle_right[0]))
            
        self.saveFile(str(ET.tostring(root))[2:-1], '.arcm')
        self.report({'INFO'}, "Camera movement exported as Arc Move XML to " + bpy.path.abspath("//") + props.camera_path_file_name + '.arcm') 
        
    
    # Export button
    def execute(self, context):
        global exportingCameraMovement
        exportingCameraMovement = True
        
        if props.moco_export_type == '0':
            bpy.ops.screen.animation_cancel(restore_frame = False)
            bpy.ops.screen.frame_jump(end = False)
            
            self.positions = []
            self.numFrames = 0
            
            for axis in range(props.moco_num_axis):
                self.positions.append([])
                
            wm = context.window_manager
            self._timer = wm.event_timer_add(0.05, context.window)
            wm.modal_handler_add(self)
            
            return {'RUNNING_MODAL'}
        
        
        elif props.moco_export_type == '1':
            self.exportXML(context)
            exportingCameraMovement = False
            
            return {'FINISHED'}

    def cancel(self, context):
        global exportingCameraMovement
        exportingCameraMovement = False
        
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        
        
# Axis utilities
def getAxisObject(axisIndex):
    global props
    objectName = getattr(props, "moco_axis_object_" + str(axisIndex))
    if not (bpy.data.objects.get(objectName) is None):
        return bpy.context.scene.objects[objectName]
    
    
def getAxisComponent(axisIndex):
    global props
    return int(getattr(props, "moco_axis_component_" + str(axisIndex)))


def getAxisLabel(axisIndex):
    global props
    return getattr(props, "moco_axis_label_" + str(axisIndex))


def getAxisKeyframes(axisIndex):
    global props
    if not (props.animation_data is None):
        component = getAxisComponent(axisIndex)
        pathName = None
        if component == 0 or component == 1 or component == 2:
            pathName = 'moco_axis_setlength_'
        elif component == 3 or component == 4 or component == 5:
            pathName = 'moco_axis_setrot_'
        
        for fcurve in props.animation_data.action.fcurves:
            if fcurve.data_path == pathName + str(axisIndex):
                return fcurve.keyframe_points
            elif fcurve.data_path == pathName + str(axisIndex):
                return fcurve.keyframe_points
        

def getAxisObjectPosition(axisIndex):
    global props
    
    object = getAxisObject(axisIndex)

    if not (object is None):
        component = getAxisComponent(axisIndex)
        
        if component == 0:
            return object.location[0]
        elif component == 1:
            return object.location[1]
        elif component == 2:
            return object.location[2]
        elif component == 3:
            return object.rotation_euler[0]
        elif component == 4:
            return object.rotation_euler[1]
        elif component == 5:
            return object.rotation_euler[2]
        
        
def getAxisInputPosition(axisIndex):
    global props
    
    object = getAxisObject(axisIndex)

    if not (object is None):
        component = getAxisComponent(axisIndex)
        if component == 0 or component == 1 or component == 2:
            return getattr(props, "moco_axis_setlength_" + str(axisIndex))
        elif component == 3 or component == 4 or component == 5:
            return getattr(props, "moco_axis_setrot_" + str(axisIndex))
        

def swapAxisFCurves(axisIndex1, axisIndex2):
    global props
    
    if not (props.animation_data is None) and not (props.animation_data.action is None):
        for fcurve in props.animation_data.action.fcurves:
            for pathName in ['moco_axis_setlength_', 'moco_axis_setrot_']:
                if fcurve.data_path == pathName + str(axisIndex1):
                    fcurve.data_path = pathName + str(axisIndex2)
                elif fcurve.data_path == pathName + str(axisIndex2):
                    fcurve.data_path = pathName + str(axisIndex1)
    


# Add axis button
class AddAxis(Operator):
    bl_idname = 'moco.addmovementaxis'
    bl_label = 'Add a moco movement axis'
 
    def execute(self, context):
        global props, maxAxisCount
        
        if props.moco_num_axis < maxAxisCount:
            props.moco_num_axis += 1
            
            setattr(props, "moco_axis_component_" + str(props.moco_num_axis - 1), str((props.moco_num_axis - 1) % 6))
            setattr(props, "moco_axis_object_" + str(props.moco_num_axis - 1),  "")
        
        return {'FINISHED'}


# Create button operators for each axis slot
for i in range(maxAxisCount):
    
    # Remove axis button
    class RemoveAxis(Operator):
        index = i
        bl_idname = 'moco.removemovementaxis' + str(index)
        bl_label = 'Remove moco movement axis'
        
        def execute(self, context):
            global props, updatingAxisSlots
            updatingAxisPositions = True
 
            for i in range(self.index, props.moco_num_axis):
                for propName in ['moco_axis_component_', 'moco_axis_object_', 'moco_axis_label_']:
                    setattr(props, propName + str(i), getattr(props, propName + str(i + 1)))
                    
                swapAxisFCurves(i, i + 1)
                
            props.moco_num_axis -= 1
            updatePositionInputs()
            return {'FINISHED'}

    # Move axis up button
    class MoveAxisUp(Operator):
        index = i
        bl_idname = 'moco.moveaxisup' + str(index)
        bl_label = 'Move axis up'
        
        def execute(self, context):
            global props, updatingAxisSlots
            updatingAxisPositions = True

            for propName in ['moco_axis_component_', 'moco_axis_object_', 'moco_axis_label_']:
                thisProp = getattr(props, propName + str(self.index))
                otherProp = getattr(props, propName + str(self.index - 1))
                setattr(props, propName + str(self.index), otherProp)
                setattr(props, propName+ str(self.index - 1), thisProp)
            
            swapAxisFCurves(self.index, self.index - 1)
                
            updatePositionInputs()
            return {'FINISHED'}

    # Move axis down button
    class MoveAxisDown(Operator):
        index = i
        bl_idname = 'moco.moveaxisdown' + str(index)
        bl_label = 'Move axis down'
        
        def execute(self, context):
            global props, updatingAxisSlots
            updatingAxisPositions = True
            
            for propName in ['moco_axis_component_', 'moco_axis_object_', 'moco_axis_label_']:
                thisProp = getattr(props, propName + str(self.index))
                otherProp = getattr(props, propName + str(self.index + 1))
                setattr(props, propName + str(self.index), otherProp)
                setattr(props, propName+ str(self.index + 1), thisProp)
                
            swapAxisFCurves(self.index, self.index + 1)
            
            updatePositionInputs()
            return {'FINISHED'}
        
    removeOperators.append(RemoveAxis)
    moveUpOperators.append(MoveAxisUp)
    moveDownOperators.append(MoveAxisDown)
    
    
    
# When position input has been changed in axis panel, update object positions
def updateObjectPositions():
    global maxAxisCount, props, updatingAxisPositions
    
    if updatingAxisPositions:
        return
    
    if not ("moco_num_axis" in props):
        return
    
    for i in range(props.moco_num_axis):
        object = getAxisObject(i)

        if not (object is None):
            component = getAxisComponent(i)
            position = getAxisInputPosition(i)
            
            if component == 0 or component == 1 or component == 2:
                object.location[component] = position
            elif component == 3 or component == 4 or component == 5:
                object.rotation_euler[component - 3] = position
                


# Update position inputs to reflect actual model position values
def updatePositionInputs():
    global maxAxisCount, props, updatingAxisPositions
    
    updatingAxisPositions = True
    
    for i in range(props.moco_num_axis):
        object = getAxisObject(i)

        if not (object is None):
            component = getAxisComponent(i)
            position = getAxisObjectPosition(i)
            
            if component == 0 or component == 1 or component == 2:
                setattr(props, "moco_axis_setlength_" + str(i), position)
            elif component == 3 or component == 4 or component == 5:
                setattr(props, "moco_axis_setrot_" + str(i), position)
                
    updatingAxisPositions = False


# Update object positions to reflect keyframed position inputs during animation playback
def animationUpdate(scene):
    global props
    props = scene
    updateObjectPositions()
    bpy.context.scene.update()


#Class for the panel with input UI
class View3dPanel(Panel):
    bl_idname = "OBJECT_PT_moco_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = 'MoCo Export'
    bl_context = 'objectmode'
    bl_category = 'MoCo Export'
    
    global maxAxisCount, setAxisLength, setAxisRotation
    
    # Custom parameters for moco pos, filepath, num axis in use
    bpy.types.Scene.camera_path_file_name = bpy.props.StringProperty(name="Filename", description = "Filename for Dragonframe raw move file. Will be exported to Blender file directory.", default = "CameraMovement")
    bpy.types.Scene.moco_export_type = bpy.props.EnumProperty(items = (('0', 'Raw Move', ''), ('1', 'Arc Move', '')), name ="File Type", description = "Type of file to export. Raw Move exports axis positions for each frame, Arc Move exports raw keyframe curves. Arc Move can be edited in Dragonframe, but require axis setup after import. For Arc Move, there be slight discrepancies between how Blender and Dragonframe interpolate between keyframes.")
    bpy.types.Scene.moco_num_axis = bpy.props.IntProperty()
    
    # Custom parameters for each axis slot: component, object string, position
    axisCompnentItems = (('0', 'LX', 'X Location'), ('1', 'LY', 'Y Location'), ('2', 'LZ', 'Z Location'), ('3', 'RX', 'X Rotation'), ('4', 'RY', 'Y Rotation'), ('5', 'RZ', 'Z Rotation'))


    def update(self, context):
        updateObjectPositions()

    for i in range(maxAxisCount):
        label = bpy.props.StringProperty(name = "Axis " + str(i), description = "Label for user reference. Also included in .arcm XML exports.")
        componentProp = bpy.props.EnumProperty(items = axisCompnentItems, name ="Component", description = "Relevent component of movement.", default = str(i % 6))
        objectProp = bpy.props.StringProperty(name ="Object", description = "Object that represents relevent motion.")
        setAxisLengthProp = bpy.props.FloatProperty(name="Pos " + str(i), description = "Set axis position. Animate this value, not the object directly.", unit = 'LENGTH', update = update)
        setAxisRotProp = bpy.props.FloatProperty(name="Pos " + str(i), description = "Set axis position. Animate this value, not the object directly.", unit = 'ROTATION', update = update)
        
        setattr(bpy.types.Scene, "moco_axis_label_" + str(i), label)
        setattr(bpy.types.Scene, "moco_axis_component_" + str(i), componentProp)
        setattr(bpy.types.Scene, "moco_axis_object_" + str(i), objectProp)
        setattr(bpy.types.Scene, "moco_axis_setlength_" + str(i), setAxisLengthProp)
        setattr(bpy.types.Scene, "moco_axis_setrot_" + str(i), setAxisRotProp)
        
    

    # Add UI elements here
    # draw method executed every time anything changes.
    def draw(self, context): 
        global maxAxisCount, props, exportingCameraMovement
        
        layout = self.layout
        scene = context.scene
        props = scene
        
        # Axis definitions
        row = layout.row()
        row.operator("wm.url_open", text="Info", icon = 'QUESTION').url = "https://github.com/Defaultio/BlenderMoco"
        layout.separator()
    
    
        layout.label(text="Axis Definitions", icon = 'MANIPUL')
        row = layout.row()
        row.operator('moco.addmovementaxis', text = 'Add New MoCo Axis', icon = 'ZOOMIN')
        
        # All the axis slots
        for i in range(props.moco_num_axis):
            box = layout.box()
            
            row = box.row()
            row.prop(props, 'moco_axis_label_' + str(i), icon = 'IPO_CONSTANT')
            
            mainSplit = box.split()
            
            # Left upper side: axis label and position input
            mainLeft = mainSplit.column()
            leftSplit = mainLeft.split()
            row = leftSplit.row()
            #row.label(text = str(i) , icon = 'IPO_CONSTANT')
            
            object = getAxisObject(i)
            if not (object is None):
                component = getAxisComponent(i)
                if component == 0 or component == 1 or component == 2:
                    row.prop(props, 'moco_axis_setlength_' + str(i))
                elif component == 3 or component == 4 or component == 5:
                    row.prop(props, 'moco_axis_setrot_' + str(i))
                    
                    
             # Right upper side: move up, move down, delete buttons
            mainRight = mainSplit.column()
            rightSplit = mainRight.split()
            col = rightSplit.column()
            col.operator('moco.moveaxisup' + str(i), text = 'Up', icon = 'TRIA_UP')
            col.enabled = i > 0
            col = rightSplit.column()
            col.operator('moco.moveaxisdown' + str(i), text = 'Down', icon = 'TRIA_DOWN')
            col.enabled = i < props.moco_num_axis - 1
            col = rightSplit.column()
            col.operator('moco.removemovementaxis' + str(i), text = 'Remove', icon = 'CANCEL')
            
            # Lower side: object and component
            row = box.row()
            row.prop_search(props, "moco_axis_object_" + str(i), scene, "objects")
            row.prop(props, "moco_axis_component_" + str(i))
     
     
        # Camera export filepath and button
        layout.separator()
        layout.label(text="File export", icon = 'FILE_TEXT')
        row = layout.row(align=True)
        row.prop(context.scene, "frame_start")
        row.prop(context.scene, "frame_end")
        row = layout.row()
        row.prop(props, "camera_path_file_name")
        row = layout.row()
        row.prop(props, "moco_export_type")
        row = layout.row()
        row.scale_y = 2.0
        
        row.operator('moco.exportmovement', text = 'Export Movement', icon = 'CAMERA_DATA')
        row.enabled = not exportingCameraMovement
    
    
# Register
def register():
    bpy.utils.register_class(View3dPanel)
    bpy.utils.register_class(ExportMovement)
    bpy.utils.register_class(AddAxis)

    bpy.app.handlers.frame_change_post.append(animationUpdate)
        
    for remove, up, down in zip(removeOperators, moveUpOperators, moveDownOperators):
        bpy.utils.register_class(remove)
        bpy.utils.register_class(up)
        bpy.utils.register_class(down)
        
    
# Unregister
def unregister():
    bpy.utils.unregister_class(View3dPanel)
    bpy.utils.unregister_class(ExportMovement)
    bpy.utils.unregister_class(AddAxis)
    
    bpy.app.handlers.frame_change_post.remove(animationUpdate)
    
    for remove, up, down in zip(removeOperators, moveUpOperators, moveDownOperators):
        bpy.utils.unregister_class(remove)
        bpy.utils.unregister_class(up)
        bpy.utils.unregister_class(down)
        
    
    
    
# Needed to run script in Text Editor
if __name__ == '__main__':
    register()
