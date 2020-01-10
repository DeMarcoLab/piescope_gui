# Getting started  with `piescope_gui` #

## Turn on hardware in the lab ##

make sure:
1. the lasers are switched on,
2. the fluorescence detector is switched on,
3. the SMARACT objective lens stage is switched on and connected,
4. you have loaded your sample into the FIBSEM 

Make sure you remember to turn off all of these things at the end of your session!

## Opening the GUI ##

The `piescope_gui` has been installed on the PFIB2 support machine.

1. Open the "*Anaconda Prompt*" from the start menu of the PFIB2 computer.
2. At the command prompt type:
```
conda activate piescope-dev
piescope
```

You should then see `piescope_gui` launch on the screen.

![piescope_gui screenshot 1](imgs/screenshot_1.png)

## Troubleshooting
If you run into problems, there are two places you can look to find information to help:

1. The content of any error messages that might pop up on screen.
2. The terminal output in the Anaconda Prompt you used to launch `piescope`.
*(You can copy-paste this by opeining the main menu (click the icon at the top left corner of the Anaconda Prompt window) then Edit > Select All and Edit > Copy.)*

This information, along with a detailed description of what happened, will help your friendly developer figure out what might have happened.

Additionally, here are

* Lasers: make sure 
Make sure turned on (image)
Make sure Toptica is not controlling

Basler
Make sure plugged in
Make sure that Pylon software suite is not open at the same time.

(IP address stuff too complicated for troubleshooting)

# Standard operations #

[**Imaging**](#imaging)
- [FIBSEM imaging](FIBSEM-imaging)
- [Fluorescence imaging](#fluorescence-imaging)

[**Stage movement**](#stage-movement)
- [Sample stage](#sample-stage)
- [Objective stage](#objective-stage)

[**Additional functions**](#additional-functions)
- [Fluorescence volume acquisition](#fluorescence-volume-acquisition)
- [Image correlation](#image-correlation)
- [Milling](#milling)

----------------------------------------
## Overview ##

![](imgs/screenshot_annotated.png)

There are three main regions of the GUI:

1. Left hand sidebar (includes red, blue, green, and orange outlines): Control panel
2. Center left (purple outline): Flourescence image acquisition and display
3. Right side (light blue outline): FIBSEM image acquisition and display

The left hand sidebar controls are grouped according by function:
* Red outline: Fluorescence volume imaging
* Blue outline: Image correlation and milling pattern creation
* Green outline: Sample stage movement between FIBSEM and fluorescence imaging positions
* Orange outline: Objective lens stage movement for focussing fluorescence images

## Imaging ##

----------------------------------------

### FIBSEM imaging ###


![](imgs/screenshot_2_fibsem.png)



#### Taking images ####

INSERT IMAGE OF IMAGE BUTTONS~~~~~~~~~~~!!!!!!!!!!!!!!!!!!!!!!

*Note:*  Ensure to check settings before taking images

To take a new ion beam image press the "Get FIB Image" Button.

To grab the last taken ion beamimage press the "Grab Last FIB" Button.

To take a new electron image press the "Get SEM Image" Button.

To grab the last taken electron image press the "Grab Last SEM" Button.

#### Settings ####

INSERT IMAGE OF FILE SAVING SECTION~~~~~~~~~~~!!!!!!!!!!!!!!!!!!!!!!

File saving settings are changed in the top section of the Fluorescence Microscope Section:

To change the folder in which fluorescence images are saved you can either manually enter the save path folder or press the [ ... ] button to navigate to the desired folder [Dark Blue].

**Note**:  In order to use the [ ... ] button the "Lock Save Destination" button must be unchecked.

To change the save filename manually enter the desired name in the "Save Filename" box [Dark Green].

INSERT IMAGE OF IMAGING PARAMETER SECTION~~~~~~~~~~~!!!!!!!!!!!!!!!!!!!!!!


### Fluorescence imaging ###

![](imgs/screenshot_2_fluorescence.png)


#### Taking images ####

INSERT IMAGE OF IMAGE BUTTONS~~~~~~~~~~~!!!!!!!!!!!!!!!!!!!!!!

*Note:*  Ensure to check settings before taking images

To take a single basler image simply press the "Get Basler Image" Button.  

To conduct live imaging press the "Live Basler View" button.  In order to stop live imaging press this button again.

#### Settings ####
INSERT IMAGE OF FILE SAVING SECTION~~~~~~~~~~~!!!!!!!!!!!!!!!!!!!!!!

File saving settings are changed in the top section of the Fluorescence Microscope Section:

To change the folder in which fluorescence images are saved you can either manually enter the save path folder or press the [ ... ] button to navigate to the desired folder [Dark Blue].

*Note*:  In order to use the [ ... ] button the "Lock Save Destination" button must be unchecked.

To change the save filename manually enter the desired name in the "Save Filename" box [Dark Green].

INSERT IMAGE OF IMAGING PARAMETER SECTION~~~~~~~~~~~!!!!!!!!!!!!!!!!!!!!!!

Imaging parameters are changed in the bottom section [Orange].

First choose the laser wavelength (Available options are 640nm, 561nm, 488nm, 
405nm) from the drop down menu on the left.  

Then enter the desired power level as a percentage (Integer with range from 0-100).

Finally set the exposure time in ms.

------------------------------------------------------------------------------------



## Stage movement

### Sample stage
Buttons and reading

![](screenshot_annotated-controls)

### Objective stage
Buttons and reading 

## Additional functions

### Fluorescence volume acquisition
settings
Path etc
Press
Output rgb

### Image correlation
Load two images/take
Path
Click control points on new window
return
overlays and opens milling window

![](imgs/screenshot_correlation.png)

![](imgs/screenshot_correlation_picking.png)

### Milling 
drag rectangle
press buttons

![piescope_gui milling pattern screenshot](imgs/screenshot_milling.png)


