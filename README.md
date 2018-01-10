# BlenderMoco
This is a Blender addon to export motion control movement paths from Blender to Dragonframe. Up to 32 axes of motionm can be added. The value that is exported for each axis is determined by a reference to some object in the Blender scene and the relevent component of the object's position: position X/Y/Z or rotaiton X/Y/Z.

**How to use**

* To run the addon, open File -> User Preferences -> Addons -> Install Add-on from file -> Select the MoCoExportAddon.py file.
* Click "Add New MoCo Axis" to add a new axis. Each axis can be named for your reference.
* Select the object and component in the axis box. LX/LY/LZ are position components and RX/RY/RZ are rotation components.
* Axes can be organized by moving them up and down. The order they apear in will be order exported for Dragonframe.
* To animate the axes, animate the position values in the addon panel, do not animate the location and rotation values for the actual referenced object.

**Tips**

* To get an object to rotate with a pan/tilt/roll or heading/attitude/bank style, use the YXZ Euler rotation mode.
* It can be very useful to parent referenced objects to other objects, so that the position being recorded is with respect to the parent object's origin, not the global origin. For example, parenting a slider block to a slider allows the slider to be positioned in any location and orientation in space, but the position of the slider block remains a relevent value that can be used for moco export.

**Known issues/future work**

* There is an occasional issue in which an axis position does not update from the previous frame, yielding a "flat spot" of two identical position values in the Dragonframe export. If this happens, try exporting again or try restarting blender.
* Support for a focus axis that works for both digital lenses and geared lenses.
