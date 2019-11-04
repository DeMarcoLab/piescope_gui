"""Functions to interact with or get information from the piescope setup"""
import skimage.io as io
import threading
from piescope.lm import detector
from piescope.lm import laser
from piescope import fibsem
from piescope_gui.correlation import main as corr
import piescope.lm.objective as objective


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
    try:
        if laser == "laser640":
            laser_box = self.spinBox_laser1
            laser_check = self.checkBox_laser1
            laser_slider = self.slider_laser1
            laser_exposure = self.lineEdit_exposure_1
        elif laser == "laser561":
            laser_box = self.spinBox_laser2
            laser_check = self.checkBox_laser2
            laser_slider = self.slider_laser2
            laser_exposure = self.lineEdit_exposure_2
        elif laser == "laser488":
            laser_box = self.spinBox_laser3
            laser_check = self.checkBox_laser3
            laser_slider = self.slider_laser3
            laser_exposure = self.lineEdit_exposure_3
        elif laser == "laser405":
            laser_slider = self.slider_laser4
            laser_check = self.checkBox_laser4
            laser_box = self.spinBox_laser4
            laser_exposure = self.lineEdit_exposure_4

        if laser_check.isChecked():
            self.laser_dict[laser] = [laser_box.text(), laser_exposure.text()]
            laser_slider.setEnabled(1)
            laser_exposure.setEnabled(1)
            laser_box.setEnabled(1)
            print(self.laser_dict)
        else:
            self.laser_dict.pop(laser)
            laser_slider.setEnabled(0)
            laser_exposure.setEnabled(0)
            laser_box.setEnabled(0)

    except Exception as e:
        self.error_msg(str(e))


def get_basler_image(self, wavelength, exposure):
    try:
        basler = detector.Basler()
        lasers = laser.initialize_lasers()
        if wavelength == "640nm":
            lasers["laser640"].enable()
            lasers["laser561"].disable()
            lasers["laser488"].disable()
            lasers["laser405"].disable()
        elif wavelength == "561nm":
            lasers["laser640"].disable()
            lasers["laser561"].enable()
            lasers["laser488"].disable()
            lasers["laser405"].disable()
        elif wavelength == "488nm":
            lasers["laser640"].disable()
            lasers["laser561"].disable()
            lasers["laser488"].enable()
            lasers["laser405"].disable()
        elif wavelength == "405nm":
            lasers["laser640"].disable()
            lasers["laser561"].disable()
            lasers["laser488"].disable()
            lasers["laser405"].enable()

        basler.camera.ExposureTime.SetValue(int(exposure))

        self.string_list_FM = [self.DEFAULT_PATH + "_Basler_Image_" + corr._timestamp()]
        self.array_list_FM = basler.camera_grab()
        print(self.array_list_FM)
        self.slider_stack_FM.setValue(1)
        self.update_display("FM")
    except Exception as e:
        self.error_msg(str(e))


def basler_live_imaging(self):
    try:
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
    except Exception as e:
        self.error_msg(str(e))


def initialise_stage(self):
    try:
        stage = objective.StageController()
        stage.initialise_system_parameters()
        print("Stage initialised")
    except Exception as e:
        self.error_msg(str(e))


def move_absolute(self, distance):
    try:
        distance = int(distance)
        stage = objective.StageController()
        stage.move_absolute(distance)
    except Exception as e:
        self.error_msg(str(e))


def move_relative(self, distance):
    try:
        distance = int(distance)
        stage = objective.StageController()
        stage.move_relative(distance)
    except Exception as e:
        self.error_msg(str(e))


def current_position(self):
    try:
        stage = objective.StageController()
        pos = stage.current_position()
        return pos
    except Exception as e:
        self.error_msg(str(e))


def connect_to_microscope(self):
    try:
        self.microscope = fibsem.initialize()
    except Exception as e:
        self.error_msg(str(e))


def move_to_light_microscope(self, microscope, x, y):
    if self.microscope:
        try:
            fibsem.move_to_light_microscope(microscope, x, y)
        except Exception as e:
            self.error_msg(str(e))
    else:
        print("Not connected to microscope")
        self.error_msg("Not connected to microscope")


def move_to_electron_microscope(self, microscope, x, y):
    if self.microscope:
        try:
            fibsem.move_to_electron_microscope(microscope, x, y)
        except Exception as e:
            self.error_msg(str(e))
    else:
        print("Not connected to microscope")
        self.error_msg("Not connected to microscope")


def get_FIB_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.new_ion_image(microscope)
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def get_last_FIB_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.last_ion_image(microscope)
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def get_SEM_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.new_electron_image(microscope)
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def get_last_SEM_image(gui, microscope):
    if gui.microscope:
        try:
            fibsem.last_electron_image(microscope)
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")
