"""Functions to interact with or get information from the piescope setup"""
import time
import skimage.io
import threading
from piescope.lm import detector
from piescope.lm import laser
from piescope import fibsem
import piescope_gui.correlation.main as corr
# from piescope_gui.correlation import main as corr
import piescope.lm.objective as objective
import skimage.util
import scipy.ndimage as ndi


def create_array_list(input_list, modality):
    if modality == "FM":
        if len(input_list) > 1:
            array_list_FM = skimage.io.imread_collection(input_list, conserve_memory=True)

        else:
            array_list_FM = skimage.io.imread(input_list[0])
            print("ARRAY LIST IS:", array_list_FM)

        return array_list_FM

    elif modality == "FIBSEM":
        if len(input_list) > 1:
            array_list_FIBSEM = skimage.io.imread_collection(input_list)
        else:
            array_list_FIBSEM = skimage.io.imread(input_list[0])

        return array_list_FIBSEM

    elif modality == "MILLING":
        if len(input_list) > 1:
            array_list_MILLING = skimage.io.imread_collection(input_list)
        else:
            array_list_MILLING = skimage.io.imread(input_list[0])

        return array_list_MILLING


def update_laser_dict(gui, laser):
    try:
        if laser == "laser640":
            laser_box = gui.spinBox_laser1
            laser_check = gui.checkBox_laser1
            laser_slider = gui.slider_laser1
            laser_exposure = gui.lineEdit_exposure_1
        elif laser == "laser561":
            laser_box = gui.spinBox_laser2
            laser_check = gui.checkBox_laser2
            laser_slider = gui.slider_laser2
            laser_exposure = gui.lineEdit_exposure_2
        elif laser == "laser488":
            laser_box = gui.spinBox_laser3
            laser_check = gui.checkBox_laser3
            laser_slider = gui.slider_laser3
            laser_exposure = gui.lineEdit_exposure_3
        elif laser == "laser405":
            laser_slider = gui.slider_laser4
            laser_check = gui.checkBox_laser4
            laser_box = gui.spinBox_laser4
            laser_exposure = gui.lineEdit_exposure_4

        if laser_check.isChecked():
            gui.laser_dict[laser] = [laser_box.text(), laser_exposure.text()]
            laser_slider.setEnabled(1)
            laser_exposure.setEnabled(1)
            laser_box.setEnabled(1)
            print(gui.laser_dict)
        else:
            gui.laser_dict.pop(laser)
            laser_slider.setEnabled(0)
            laser_exposure.setEnabled(0)
            laser_box.setEnabled(0)

    except Exception as e:
        gui.error_msg(str(e))


def get_basler_image(gui, wavelength, exposure, power, lasers, basler, mode):
    try:
        if wavelength == "640nm":
            las = "laser640"
        elif wavelength == "561nm":
            las = "laser561"
        elif wavelength == "488nm":
            las = "laser488"
        elif wavelength == "405nm":
            las = "laser405"

        if mode == "single":

            lasers[las].laser_power = int(power)
            lasers[las].emission_on()

            basler.camera.Open()
            basler.camera.ExposureTime.SetValue(int(exposure)*1000)
            gui.string_list_FM = [gui.DEFAULT_PATH + "_Basler_Image_" + corr._timestamp()]
            gui.array_list_FM = basler.camera_grab()

            lasers[las].emission_off()

            print(gui.array_list_FM)
            gui.slider_stack_FM.setValue(1)
            gui.update_display("FM")

        elif mode == "live":
            basler.camera.Open()
            basler.camera.ExposureTime.SetValue(int(exposure) * 1000)
            lasers[las].laser_power = int(power)
            gui.string_list_FM = [gui.DEFAULT_PATH + "_Basler_Image_" + corr._timestamp()]
            gui.array_list_FM = basler.camera_grab()
            print(gui.array_list_FM)
            gui.slider_stack_FM.setValue(1)
            gui.update_display("FM")

    except Exception as e:
        gui.error_msg(str(e))


def basler_live_imaging(gui, wavelength, exposure, power, lasers, basler):
    try:
        if wavelength == "640nm":
            las = "laser640"
        elif wavelength == "561nm":
            las = "laser561"
        elif wavelength == "488nm":
            las = "laser488"
        elif wavelength == "405nm":
            las = "laser405"
        print(las)
        if gui.liveCheck is True:
            basler.camera.Open()
            basler.camera.ExposureTime.SetValue(int(exposure) * 1000)
            lasers[las].laser_power = int(power)
            lasers[las].emission_on()
            gui.stop_event = threading.Event()
            gui.c_thread = threading.Thread(
                target=gui.live_imaging_event_listener_FM, args=(gui.stop_event,))
            gui.c_thread.start()
            gui.liveCheck = False
            gui.button_live_image_FM.setDown(True)
        else:
            # lasers[las].emission_off()
            gui.stop_event.set()
            gui.liveCheck = True
            gui.button_live_image_FM.setDown(False)
    except Exception as e:
        gui.error_msg(str(e))


def initialise_stage(gui):
    try:
        stage = objective.StageController()
        stage.initialise_system_parameters()
        time.sleep(0.3)
        pos = stage.current_position()
        gui.label_objective_stage_position.setText(str(float(pos)/1000))
        # stage.initialise_system_parameters(0, 0, 0, 0)
        print("Stage initialised")
    except Exception as e:
        gui.error_msg(str(e))


def move_absolute(gui, distance):
    try:
        distance2 = int(float(distance)*1000)
        # print("Distance: {}nm".format(distance2))
        stage = objective.StageController()
        ans = stage.move_absolute(distance2)
        time.sleep(0.3)
        pos = stage.current_position()
        gui.label_objective_stage_position.setText(str(float(pos)/1000))
    except Exception as e:
        gui.error_msg(str(e))


def move_relative(gui, distance):
    try:
        distance2 = int(float(distance) * 1000)
        # print("Distance: {}nm".format(distance2))
        stage = objective.StageController()
        ans = stage.move_relative(distance2)
        time.sleep(0.3)
        pos = stage.current_position()
        gui.label_objective_stage_position.setText(str(float(pos)/1000))
    except Exception as e:
        gui.error_msg(str(e))


def current_position(gui):
    try:
        stage = objective.StageController()
        pos = stage.current_position()
        return pos
    except Exception as e:
        gui.error_msg(str(e))


def connect_to_microscope(gui):
    try:
        gui.microscope = fibsem.initialize()
        gui.camera_settings = update_fibsem_settings(gui)
    except Exception as e:
        gui.error_msg(str(e))


def move_to_light_microscope(gui, microscope, x, y):
    if gui.microscope:
        try:
            fibsem.move_to_light_microscope(microscope, x, y)
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def move_to_electron_microscope(gui, microscope, x, y):
    if gui.microscope:
        try:
            fibsem.move_to_electron_microscope(microscope, x, y)
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def get_FIB_image(gui, microscope, camera_settings):
    if gui.microscope:
        try:
            if gui.checkBox_Autocontrast.isChecked():
                autocontrast_ion_beam(gui, microscope, camera_settings)
            gui.fibsem_image = fibsem.new_ion_image(microscope, camera_settings)
            gui.array_list_FIBSEM = gui.fibsem_image.data
            print(gui.array_list_FIBSEM.dtype)
            gui.string_list_FIBSEM = [gui.DEFAULT_PATH + "FIB_Image_" + corr._timestamp()]
            print(gui.array_list_FIBSEM)
            gui.update_display("FIBSEM")
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def get_last_FIB_image(gui, microscope):
    if gui.microscope:
        try:
            gui.fibsem_image = fibsem.last_ion_image(microscope)
            gui.array_list_FIBSEM = gui.fibsem_image.data
            gui.array_list_FIBSEM = skimage.util.img_as_ubyte(gui.array_list_FIBSEM)
            print(gui.array_list_FIBSEM.dtype)
            print(gui.array_list_FIBSEM)
            gui.string_list_FIBSEM = [gui.DEFAULT_PATH + "Last_FIB_Image_" + corr._timestamp()]
            print(gui.array_list_FIBSEM)
            gui.update_display("FIBSEM")
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def get_SEM_image(gui, microscope, camera_settings):
    if gui.microscope:
        try:
            gui.fibsem_image = fibsem.new_electron_image(microscope, camera_settings)
            gui.array_list_FIBSEM = gui.fibsem_image.data
            if gui.checkBox_Autocontrast.isChecked():
                gui.array_list_FIBSEM = ndi.median_filter(gui.array_list_FIBSEM, 2)
                # autocontrast_ion_beam(gui, microscope, camera_settings)
            # print(gui.array_list_FIBSEM.dtype)
            gui.string_list_FIBSEM = [gui.DEFAULT_PATH + "SEM_Image_" + corr._timestamp()]
            # print(gui.array_list_FIBSEM)
            gui.update_display("FIBSEM")
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def get_last_SEM_image(gui, microscope):
    if gui.microscope:
        try:
            gui.fibsem_image = fibsem.last_electron_image(microscope)
            gui.array_list_FIBSEM = gui.fibsem_image.data
            gui.array_list_FIBSEM = skimage.util.img_as_ubyte(gui.array_list_FIBSEM)
            gui.string_list_FIBSEM = [gui.DEFAULT_PATH + "SEM_Image_" + corr._timestamp()]
            print(gui.array_list_FIBSEM)
            gui.update_display("FIBSEM")
        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def autocontrast_ion_beam(gui, microscope, settings):
    if gui.microscope:
        try:
            fibsem.autocontrast(microscope)
            # gui.fibsem_image = fibsem.new_ion_image(microscope, settings)
            # gui.array_list_FIBSEM = gui.fibsem_image.data
            # gui.array_list_FIBSEM = skimage.util.img_as_ubyte(gui.array_list_FIBSEM)
            # gui.string_list_FIBSEM = [gui.DEFAULT_PATH + "SEM_Image_" + corr._timestamp()]
            # print(gui.array_list_FIBSEM)
            # gui.update_display("FIBSEM")

        except Exception as e:
            gui.error_msg(str(e))
    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")


def update_fibsem_settings(gui):
    if gui.microscope:
        try:
            dwell_time = float(gui.lineEdit_dwell_time.text())*1.e-6
            resolution = gui.comboBox_resolution.currentText()
            fibsem_settings = fibsem.update_camera_settings(dwell_time, resolution)
            gui.camera_settings = fibsem_settings
            return fibsem_settings

        except Exception as e:
            gui.error_msg(str(e))

    else:
        print("Not connected to microscope")
        gui.error_msg("Not connected to microscope")