"""Functions to interact with or get information from the piescope setup"""
import skimage.io as io
import threading
from piescope.lm import detector
from piescope import fibsem
from piescope_gui.correlation import main as corr
import piescope.lm.objective as objective
import piescope_gui.main as main


def save_image(image, dest):
    io.imsave(dest, image)


def create_array_list(input_list, modality):
    if modality == "FM":
        if len(input_list) > 1:
            array_list_FM = io.imread_collection(input_list)
        else:
            array_list_FM = io.imread(input_list[0])

        return array_list_FM

    elif modality == "FIBSEM":
        if len(input_list) > 1:
            array_list_FIBSEM = io.imread_collection(input_list)
        else:
            array_list_FIBSEM = io.imread(input_list[0])

        return array_list_FIBSEM

    elif modality == "MILLING":
        if len(input_list) > 1:
            array_list_MILLING = io.imread_collection(input_list)
        else:
            array_list_MILLING = io.imread(input_list[0])

        return array_list_MILLING


def update_laser_dict(self, laser):
    if laser == "laser640":
        laser_box = self.spinBox_laser1
        laser_check = self.checkBox_laser1
        laser_slider = self.slider_laser1
    elif laser == "laser561":
        laser_box = self.spinBox_laser2
        laser_check = self.checkBox_laser2
        laser_slider = self.slider_laser2
    elif laser == "laser488":
        laser_box = self.spinBox_laser3
        laser_check = self.checkBox_laser3
        laser_slider = self.slider_laser3
    elif laser == "laser405":
        laser_slider = self.slider_laser4
        laser_check = self.checkBox_laser4
        laser_box = self.spinBox_laser4
    else:
        ValueError()

    if laser_check.isChecked():
        self.laser_dict[laser] = laser_box.text()
        laser_slider.setEnabled(1)
        laser_box.setEnabled(1)
        print(self.laser_dict)
    else:
        self.laser_dict.pop(laser)
        laser_slider.setEnabled(0)
        laser_box.setEnabled(0)


def get_basler_image(self):
    basler = detector.Basler()
    self.string_list_FM = [self.DEFAULT_PATH + "_Basler_Image_" + corr._timestamp()]
    self.array_list_FM = basler.camera_grab()
    print(self.array_list_FM)
    self.slider_stack_FM.setValue(1)
    self.update_display("FM")


def basler_live_imaging(self):
    if self.liveCheck is True:
        self.stop_event = threading.Event()
        self.c_thread = threading.Thread(
            target=self.live_imaging_event_listener_FM, args=(self.stop_event,))
        self.c_thread.start()
        self.liveCheck = False
        self.button_live_image_FM.setDown(True)
    else:
        self.stop_event.set()
        self.liveCheck = True
        self.button_live_image_FM.setDown(False)


def initialise_stage():
    try:
        stage = objective.StageController()
    except Exception as e:
        print(e)
        print('Could not connect to stage')
        return

    try:
        stage.initialise_system_parameters()
        print("Stage initialised")
    except Exception as e:
        print(e)
        print('Could not initialise stage parameters')
        return


def move_absolute(distance):
    try:
        stage = objective.StageController()
    except Exception as e:
        print(e)
        print('Could not connect to stage')
        return

    try:
        stage.move_absolute(distance)
    except Exception as e:
        print(e)
        print('Could not move the stage by %s' % distance)
        return


def move_relative(distance):
    try:
        stage = objective.StageController()
    except Exception as e:
        print(e)
        print('Could not connect to stage')
        return

    try:
        stage.move_relative(distance)
    except Exception as e:
        print(e)
        print('Could not move the stage by %s' % distance)
        return


def current_position():
    stage = objective.StageController()
    pos = stage.current_position()
    return pos


def connect_to_microscope(self):
    try:
        self.microscope = fibsem.initialize()
    except Exception as e:
        print(e)
        print("Failed to connect to microscope")
        self.error_msg(message="Could not connect to microscope")
        return


def move_to_light_microscope(self, microscope, x, y):
    if self.microscope is not None:
        try:
            fibsem.move_to_light_microscope(microscope, x, y)
        except Exception as e:
            print(e)
            print("Could not move to light microscope")
            return
    else:
        print("Not connected to microscope")


def move_to_electron_microscope(self, microscope, x, y):
    if self.microscope:
        try:
            fibsem.move_to_electron_microscope(microscope, x, y)
        except Exception as e:
            print(e)
            print("Could not move to electron microscope")
            # return
    else:
        print("Not connected to microscope")


def get_FIB_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.new_ion_image(microscope)
        except Exception as e:
            print(e)
            print("Could not take ion beam image")
            return
    else:
        print("Not connected to microscope")


def get_last_FIB_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.last_ion_image(microscope)
        except Exception as e:
            print(e)
            print("Could not take ion beam image")
            return
    else:
        print("Not connected to microscope")


def get_SEM_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.new_electron_image(microscope)
        except Exception as e:
            print(e)
            print("Could not take electron beam image")

            return
    else:
        print("Not connected to microscope")


def get_last_SEM_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.last_electron_image(microscope)
        except Exception as e:
            print(e)
            print("Could not take ion beam image")
            return
    else:
        print("Not connected to microscope")

