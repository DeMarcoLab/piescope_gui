"""Functions to interact with or get information from the piescope setup"""
import skimage.io as io
import threading
from piescope.lm import detector
import piescope.lm.objective as objective


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
    self.string_list_FM = ["Basler_image"]
    self.array_list_FM = basler.camera_grab()
    print(self.array_list_FM)
    self.slider_stack_FM.setValue(1)
    self.update_display("FM")


def basler_live_imaging(self):
    if self.liveCheck is True:
        self.stop_event = threading.Event()
        self.c_thread = threading.Thread(
            target=self.live_imaging_event_listener, args=(self.stop_event,))
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
    except:
        print('Could not connect to stage')
        return

    try:
        stage.initialise_system_parameters()
        print("Stage initialised")
    except:
        print('Could not initialise stage parameters')
        return


def move_absolute(distance):
    try:
        stage = objective.StageController()
    except:
        print('Could not connect to stage')
        return

    try:
        stage.move_absolute(distance)
    except:
        print('Could not move the stage by %s' % distance)
        return


def move_relative(distance):
    try:
        stage = objective.StageController()
    except:
        print('Could not connect to stage')
        return

    try:
        stage.move_relative(distance)
    except:
        print('Could not move the stage by %s' % distance)
        return


def current_position():
    stage = objective.StageController()
    pos = stage.current_position()
    return pos

