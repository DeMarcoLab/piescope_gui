import os
import logging
import threading
import time
import traceback

import numpy as np
from PyQt5 import QtWidgets, QtGui, QtCore
import qimage2ndarray
import scipy.ndimage as ndi
import skimage.io
import skimage.util

import piescope

import piescope_gui.milling
import piescope_gui.correlation.main as corr
import piescope_gui.qtdesigner_files.main as gui_main

logger = logging.getLogger(__name__)


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self, ip_address="10.0.0.1"):
        super(GUIMainWindow, self).__init__()
        self.setupUi(self)
        self.setup_connections()
        self.microscope = None
        self.connect_to_fibsem_microscope(ip_address=ip_address)

        self.DEFAULT_PATH = "C:\\Users\\Admin\\Pictures\\Basler"
        self.setWindowTitle("PIEScope User Interface Main Window")
        self.statusbar.setSizeGripEnabled(0)
        self.status = QtWidgets.QLabel(self.statusbar)
        self.status.setAlignment(QtCore.Qt.AlignRight)
        self.statusbar.addPermanentWidget(self.status, 1)
        self.lineEdit_save_destination_FM.setText(self.DEFAULT_PATH)
        self.lineEdit_save_destination_FIBSEM.setText(self.DEFAULT_PATH)
        self.checkBox_save_destination_FM.setChecked(1)
        self.checkBox_save_destination_FIBSEM.setChecked(1)
        self.lineEdit_save_filename_FM.setText("Image")
        self.lineEdit_save_filename_FIBSEM.setText("Image")
        self.label_objective_stage_position.setText("Unknown")
        self.delim = os.path.normpath("/")
        self.liveCheck = True

        self.save_name = ""
        self.laser_dict = {}
        self.fibsem_image = []
        self.array_list_FM = []
        self.array_list_FIBSEM = []
        self.string_list_FM = []
        self.string_list_FIBSEM = []
        self.current_path_FM = ""
        self.current_path_FIBSEM = ""
        self.current_image_FM = ""
        self.current_image_FIBSEM = ""
        self.current_pixmap_FM = []
        self.current_pixmap_FIBSEM = []
        self.save_destination_FM = ""
        self.save_destination_FIBSEM = ""
        self.save_destination_correlation = ""

    def setup_connections(self):

        self.lasers = piescope.lm.laser.initialize_lasers()
        self.basler = piescope.lm.detector.Basler()

        self.comboBox_resolution.currentTextChanged.connect(
            lambda: self.update_fibsem_settings(self))
        self.lineEdit_dwell_time.textChanged.connect(
            lambda: self.update_fibsem_settings(self))

        self.actionOpen_FM_Image.triggered.connect(
            lambda: self.open_images("FM"))
        self.actionOpen_FIBSEM_Image.triggered.connect(
            lambda: self.open_images("FIBSEM"))

        self.actionSave_FM_Image.triggered.connect(
            lambda: self.save_image("FM"))
        self.actionSave_FIBSEM_Image.triggered.connect(
            lambda: self.save_image("FIBSEM"))

        self.slider_stack_FM.valueChanged.connect(
            lambda: self.update_display("FM"))
        self.slider_stack_FIBSEM.valueChanged.connect(
            lambda: self.update_display("FIBSEM"))

        self.button_save_destination_FM.clicked.connect(
            lambda: self.fill_destination("FM"))
        self.button_save_destination_FIBSEM.clicked.connect(
            lambda: self.fill_destination("FIBSEM"))
        self.toolButton_correlation_output.clicked.connect(
            self.fill_correlation_destination)

        self.checkBox_laser1.clicked.connect(
            lambda: self.update_laser_dict("laser640"))
        self.checkBox_laser2.clicked.connect(
            lambda: self.update_laser_dict("laser561"))
        self.checkBox_laser3.clicked.connect(
            lambda: self.update_laser_dict("laser488"))
        self.checkBox_laser4.clicked.connect(
            lambda: self.update_laser_dict("laser405"))

        self.slider_laser1.valueChanged.connect(
            lambda: self.update_laser_dict("laser640"))
        self.slider_laser2.valueChanged.connect(
            lambda: self.update_laser_dict("laser561"))
        self.slider_laser3.valueChanged.connect(
            lambda: self.update_laser_dict("laser488"))
        self.slider_laser4.valueChanged.connect(
            lambda: self.update_laser_dict("laser405"))

        self.lineEdit_exposure_1.textChanged.connect(
            lambda: self.update_laser_dict("laser640"))
        self.lineEdit_exposure_2.textChanged.connect(
            lambda: self.update_laser_dict("laser561"))
        self.lineEdit_exposure_3.textChanged.connect(
            lambda: self.update_laser_dict("laser488"))
        self.lineEdit_exposure_4.textChanged.connect(
            lambda: self.update_laser_dict("laser405"))

        self.button_get_image_FIB.clicked.connect(
            lambda: self.get_FIB_image())
        self.button_get_image_SEM.clicked.connect(
            lambda: self.get_SEM_image())
        self.button_last_image_FIB.clicked.connect(
            lambda: self.get_last_FIB_image())
        self.button_last_image_SEM.clicked.connect(
            lambda: self.get_last_SEM_image())

        self.button_get_image_FM.clicked.connect(
            lambda: self.get_basler_image(self.comboBox_laser_basler.currentText(),
                                          self.lineEdit_exposure_basler.text(),
                                          self.lineEdit_power_basler_2.text(),
                                          self.lasers,
                                          self.basler,
                                          "single"))
        self.button_live_image_FM.clicked.connect(
            lambda: self.basler_live_imaging(self.comboBox_laser_basler.currentText(),
                                             self.lineEdit_exposure_basler.text(),
                                             self.lineEdit_power_basler_2.text(),
                                             self.lasers, self.basler))

        self.pushButton_initialize_stage.clicked.connect(
            lambda: self.initialize_objective_stage())
        self.pushButton_move_absolute.clicked.connect(
            lambda: self.move_absolute_objective_stage(
                self, self.lineEdit_move_absolute.text()))
        self.pushButton_move_relative.clicked.connect(
            lambda: self.move_relative_objective_stage())

        self.connect_microscope.clicked.connect(
            lambda: self.connect_to_fibsem_microscope())
        self.to_light_microscope.clicked.connect(
            lambda: self.move_to_light_microscope())
        self.to_electron_microscope.clicked.connect(
            lambda: self.move_to_electron_microscope())

        self.pushButton_volume.clicked.connect(self.acquire_volume)
        self.pushButton_correlation.clicked.connect(self.correlateim)
        self.pushButton_milling.clicked.connect(self.milling)

        self.pushButton_save_objective_position.clicked.connect(self.save_objective_stage_position)
        self.pushButton_go_to_saved_position.clicked.connect(self.move_absolute_objective_stage)
        self.pushButton_get_position.clicked.connect(self.objective_stage_position)

    ############## FIBSEM microscope methods ##############
    def connect_to_fibsem_microscope(self, ip_address="10.0.0.1"):
        """Connect to the FIBSEM microscope."""
        try:
            from piescope import fibsem
            self.microscope = piescope.fibsem.initialize(ip_address=ip_address)
            self.camera_settings = self.update_fibsem_settings()
        except Exception as e:
            _error_message( traceback.format_exc())

    def update_fibsem_settings(self):
        if not self.microscope:
            self.connect_to_fibsem_microscope()
        try:
            from piescope import fibsem
            dwell_time = float(self.lineEdit_dwell_time.text())*1.e-6
            resolution = self.comboBox_resolution.currentText()
            fibsem_settings = piescope.fibsem.update_camera_settings(dwell_time, resolution)
            self.camera_settings = fibsem_settings
            return fibsem_settings
        except Exception as e:
            _error_message( traceback.format_exc())

    ############## FIBSEM sample stage methods ##############
    def move_to_light_microscope(self, x=+49.952e-3, y=-0.1911e-3):
        try:
            piescope.fibsem.move_to_light_microscope(self.microscope, x, y)
        except Exception as e:
            traceback_message = traceback.format_exc()
            logger.exception(traceback_message)
            _error_message(traceback_message)

    def move_to_electron_microscope(self, x=-49.952e-3, y=+0.1911e-3):
        try:
            piescope.fibsem.move_to_electron_microscope(self.microscope, x, y)
        except Exception as e:
            _error_message( traceback.format_exc())

    ############## FIBSEM image methods ##############
    def get_FIB_image(self):
        try:
            if self.checkBox_Autocontrast.isChecked():
                self.autocontrast_ion_beam()
            self.fibsem_image = piescope.fibsem.new_ion_image(self.microscope, self.camera_settings)
            self.array_list_FIBSEM = self.fibsem_image.data
            self.string_list_FIBSEM = [self.DEFAULT_PATH + "FIB_Image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())]
            self.update_display("FIBSEM")
        except Exception as e:
            _error_message( traceback.format_exc())
        else:
            return self.fibsem_image

    def get_last_FIB_image(self):
        try:
            self.fibsem_image = piescope.fibsem.last_ion_image(self.microscope)
            self.array_list_FIBSEM = skimage.util.img_as_ubyte(self.fibsem_image.data)
            self.string_list_FIBSEM = [gui.DEFAULT_PATH + "Last_FIB_Image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())]
            self.update_display("FIBSEM")
        except Exception as e:
            _error_message( traceback.format_exc())
        else:
            return self.fibsem_image

    def get_SEM_image(self, camera_settings):
        try:
            self.fibsem_image = piescope.fibsem.new_electron_image(self.microscope, self.camera_settings)
            self.array_list_FIBSEM = np.copy(self.fibsem_image.data)
            self.array_list_FIBSEM = ndi.median_filter(self.array_list_FIBSEM, 2)
            self.string_list_FIBSEM = [gui.DEFAULT_PATH + "SEM_Image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())]
            self.update_display("FIBSEM")
        except Exception as e:
            _error_message( traceback.format_exc())
        else:
            return self.fibsem_image

    def get_last_SEM_image(self):
        try:
            self.fibsem_image = piescope.fibsem.last_electron_image(self.microscope)
            self.array_list_FIBSEM = self.fibsem_image.data
            self.array_list_FIBSEM = skimage.util.img_as_ubyte(self.array_list_FIBSEM)
            self.string_list_FIBSEM = [self.DEFAULT_PATH + "SEM_Image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())]
            print(self.array_list_FIBSEM)
            self.update_display("FIBSEM")
        except Exception as e:
            _error_message( traceback.format_exc())
        else:
            return self.fibsem_image

    def autocontrast_ion_beam(self):
        try:
            self.microscope.imaging.set_active_view(2)  # the ion beam view
            piescope.fibsem.autocontrast(self.microscope)
            self.fibsem_image = piescope.fibsem.last_ion_image(self.microscope)
            self.array_list_FIBSEM = skimage.util.img_as_ubyte(self.fibsem_image.data)
            self.string_list_FIBSEM = [self.DEFAULT_PATH + "FIB_Image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())]
            self.update_display("FIBSEM")
        except Exception as e:
            _error_message( traceback.format_exc())
        else:
            return self.fibsem_image

    ############## Fluorescence detector methods ##############
    def get_basler_image(self, wavelength, exposure, power, lasers, basler, mode):
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
                self.string_list_FM = [gui.DEFAULT_PATH + "_Basler_Image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())]
                self.array_list_FM = basler.camera_grab()

                lasers[las].emission_off()

                print(gui.array_list_FM)
                self.slider_stack_FM.setValue(1)
                self.update_display("FM")

            elif mode == "live":
                basler.camera.Open()
                basler.camera.ExposureTime.SetValue(int(exposure) * 1000)
                lasers[las].laser_power = int(power)
                self.string_list_FM = [gui.DEFAULT_PATH + "_Basler_Image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())]
                self.array_list_FM = basler.camera_grab()
                print(self.array_list_FM)
                self.slider_stack_FM.setValue(1)
                self.update_display("FM")

        except Exception as e:
            _error_message( traceback.format_exc())

    def basler_live_imaging(self, wavelength, exposure, power, lasers, basler):
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
            if self.liveCheck is True:
                basler.camera.Open()
                basler.camera.ExposureTime.SetValue(int(exposure) * 1000)
                lasers[las].laser_power = int(power)
                lasers[las].emission_on()
                self.stop_event = threading.Event()
                self.c_thread = threading.Thread(
                    target=gui.live_imaging_event_listener_FM, args=(self.stop_event,))
                self.c_thread.start()
                self.liveCheck = False
                self.button_live_image_FM.setDown(True)
            else:
                self.stop_event.set()
                self.liveCheck = True
                # lasers[las].emission_off()
                self.button_live_image_FM.setDown(False)
        except Exception as e:
            _error_message(traceback.format_exc())

    ############## Fluorescence objective lens stage methods ##############
    def initialize_objective_stage(self, time_delay=0.3):
        """Initialize the fluorescence objective lens stage."""
        try:
            stage = piescope.lm.objective.StageController()
            stage.initialise_system_parameters()
            time.sleep(time_delay)
            pos = stage.current_position()
        except Exception as e:
            _error_message(traceback.format_exc())
        else:
            self.label_objective_stage_position.setText(str(float(pos)/1000))
            print("Stage initialised")

    def objective_stage_position(self):
        try:
            stage = piescope.lm.objective.StageController()
            pos = stage.current_position()
        except Exception as e:
            _error_message( traceback.format_exc())
        else:
            self.label_objective_stage_position.setTextstr(float(pos)/1000)

    def save_objective_stage_position(self):
        try:
            pos = self.label_objective_stage_position.text()
            self.label_objective_stage_saved_position.setText(pos)
        except Exception as e:
            _error_message( traceback.format_exc())

    def move_absolute_objective_stage(self, position=None, time_delay=0.3):
        if position is None:
            position = int(float(self.label_objective_stage_saved_position.text()))
        position = int(float(position)*1000)
        # print("Moving to position: {}nm".format(position))
        try:
            stage = piescope.lm.objective.StageController()
            ans = stage.move_absolute(position)
            time.sleep(time_delay)
            pos = stage.current_position()
        except Exception as e:
            _error_message(traceback.format_exc())
        else:
            self.label_objective_stage_position.setText(str(float(pos)/1000))

    def move_relative_objective_stage(self, distance=None, time_delay=0.3):
        if distance is None:
            distance = self.lineEdit_move_relative.text()
        distance = int(float(distance) * 1000)
        try:
            stage = piescope.lm.objective.StageController()
            ans = stage.move_relative(distance)
            time.sleep(time_delay)
            pos = stage.current_position()
        except Exception as e:
            _error_message(traceback.format_exc())
        else:
            self.label_objective_stage_position.setText(str(float(pos)/1000))

    ############## Fluorescence laser methods ##############
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
                gui.laser_dict[laser] = [laser_box.text(), laser_exposure.text()]
                laser_slider.setEnabled(1)
                laser_exposure.setEnabled(1)
                laser_box.setEnabled(1)
                print(self.laser_dict)
            else:
                gui.laser_dict.pop(laser)
                laser_slider.setEnabled(0)
                laser_exposure.setEnabled(0)
                laser_box.setEnabled(0)
        except Exception as e:
            _error_message(traceback.format_exc())

    ############## Image methods ##############
    def open_images(self, modality):
        """Open image files and display the first"""
        try:
            if modality == "FM":
                [self.string_list_FM,
                 ext] = QtWidgets.QFileDialog.getOpenFileNames(
                    self, 'Open File',
                    filter="Images (*.bmp *.tif *.tiff *.jpg)")

                if self.string_list_FM:
                    self.array_list_FM = _create_array_list(
                        self.string_list_FM, "FM")
                    self.slider_stack_FM.setMaximum(len(self.string_list_FM))
                    self.spinbox_slider_FM.setMaximum(len(self.string_list_FM))
                    self.slider_stack_FM.setValue(1)
                    self.update_display("FM")

            elif modality == "FIBSEM":
                [self.string_list_FIBSEM,
                 ext] = QtWidgets.QFileDialog.getOpenFileNames(
                    self, 'Open File',
                    filter="Images (*.bmp *.tif *.tiff *.jpg)")

                if self.string_list_FIBSEM:
                    self.array_list_FIBSEM = _create_array_list(
                        self.string_list_FIBSEM, "FIBSEM")
                    self.slider_stack_FIBSEM.setMaximum(
                        len(self.string_list_FIBSEM))
                    self.spinbox_slider_FIBSEM.setMaximum(
                        len(self.string_list_FIBSEM))
                    self.slider_stack_FIBSEM.setValue(1)
                    self.update_display("FIBSEM")
        except Exception as e:
            _error_message( traceback.format_exc())

    def save_image(self, modality):
        """Save image on display """
        try:
            if modality == "FM":
                if self.current_image_FM is not None:
                    max_value = len(self.string_list_FM)
                    if max_value == 1:
                        display_image = self.array_list_FM
                        print(display_image)
                    else:
                        display_image = self.array_list_FM[
                            self.slider_stack_FM.value() - 1]
                        print(display_image)
                    [save_base, ext] = os.path.splitext(
                        self.lineEdit_save_filename_FM.text())
                    dest = self.lineEdit_save_destination_FM.text() + self.delim \
                           + save_base + ".tif"
                    dir_exists = os.path.isdir(
                        self.lineEdit_save_destination_FM.text())
                    if not dir_exists:
                        os.makedirs(self.lineEdit_save_destination_FM.text())
                        piescope.utils.save_image(display_image, dest)
                    else:
                        exists = os.path.isfile(dest)
                        if not exists:
                            piescope.utils.save_image(display_image, dest)
                        else:
                            count = 1
                            while exists:
                                dest = self.lineEdit_save_destination_FM.text() + \
                                       self.delim + save_base + "(" + str(
                                    count) + \
                                       ").tif"
                                exists = os.path.isfile(dest)
                                count = count + 1
                                piescope.utils.save_image(display_image,
                                                   dest)
                else:
                    _error_message("No image to save")

            elif modality == "FIBSEM":

                if self.current_image_FIBSEM is not None:
                    # if self.array_list_FIBSEM.all == self.fibsem_image.data.all:
                    #     display_image = self.fibsem_image
                    # else:
                    #     max_value = len(self.string_list_FIBSEM)
                    #     if max_value == 1:
                    #         display_image = self.array_list_FIBSEM
                    #         print(display_image)
                    #     else:
                    #         display_image = self.array_list_FIBSEM[
                    #             self.slider_stack_FIBSEM.value() - 1]
                    #         print(display_image)
                    display_image = self.fibsem_image
                    [save_base, ext] = os.path.splitext(
                        self.lineEdit_save_filename_FIBSEM.text())
                    dest = self.lineEdit_save_destination_FIBSEM.text() + \
                           self.delim + save_base + ".tif"
                    dir_exists = os.path.isdir(
                        self.lineEdit_save_destination_FIBSEM.text())
                    if not dir_exists:
                        os.makedirs(
                            self.lineEdit_save_destination_FIBSEM.text())
                        piescope.utils.save_image(display_image, dest)
                    else:
                        exists = os.path.isfile(dest)
                        if not exists:
                            piescope.utils.save_image(display_image, dest)
                        else:
                            count = 1
                            while exists:
                                dest = self.lineEdit_save_destination_FIBSEM.text() + \
                                       self.delim + save_base + "(" + str(
                                    count) + \
                                       ").tif"
                                exists = os.path.isfile(dest)
                                count = count + 1
                                piescope.utils.save_image(display_image, dest)

                else:
                    _error_message("No image to save")

        except Exception as e:
            _error_message( traceback.format_exc())

    def update_display(self, modality):
        """Update the GUI display with the current image"""
        try:
            if modality == "FM" and self.string_list_FM:
                slider_value = str(self.slider_stack_FM.value())
                max_value = str(len(self.string_list_FM))

                image_string = self.string_list_FM[int(slider_value) - 1]
                self.current_path_FM = os.path.normpath(image_string)

                if int(max_value) > 1:
                    image_array = self.array_list_FM[int(slider_value) - 1]
                else:
                    image_array = self.array_list_FM
                image_array = np.flipud(image_array)
                FM_max = image_array.max()
                self.label_max_FM_value.setText("Max value: " + str(FM_max))
                image_array_crosshair = np.copy(image_array)
                xshape = image_array_crosshair.shape[0]
                yshape = image_array_crosshair.shape[1]
                midx = int(xshape/2)
                midy = int(yshape/2)
                thresh = 2
                mult = 25
                image_array_crosshair[midx-(thresh*mult):midx+(thresh*mult), midy-thresh:midy+thresh] = 255
                image_array_crosshair[midx - thresh:midx + thresh, midy - (thresh * mult):midy + (thresh * mult)] = 255

                self.current_image_FM = qimage2ndarray.array2qimage(image_array)
                self.current_image_FM_crosshair = qimage2ndarray.array2qimage(image_array_crosshair)
                print(self.current_image_FM)

                self.status.setText(
                    "Image " + slider_value + " of " + max_value)

                self.current_pixmap_FM = QtGui.QPixmap.fromImage(
                    self.current_image_FM_crosshair)
                self.current_pixmap_FM = self.current_pixmap_FM.scaled(
                    640, 400, QtCore.Qt.KeepAspectRatio)
                self.label_image_FM.setPixmap(self.current_pixmap_FM)

                self.fill_save_information("FM")
                """Updating display of GUI with current FM image"""

            elif modality == "FIBSEM" and self.string_list_FIBSEM:
                slider_value = str(self.slider_stack_FIBSEM.value())
                max_value = str(len(self.string_list_FIBSEM))

                image_string = self.string_list_FIBSEM[0]

                if int(max_value) > 1:
                    image_array = self.array_list_FIBSEM[1]
                else:
                    image_array = self.array_list_FIBSEM

                self.current_image_FIBSEM = qimage2ndarray.array2qimage(image_array)
                print(self.current_image_FIBSEM)
                self.current_path_FIBSEM = os.path.normpath(image_string)

                self.status.setText(
                    "Image " + slider_value + " of " + max_value)

                self.current_pixmap_FIBSEM = QtGui.QPixmap.fromImage(
                    self.current_image_FIBSEM)
                self.current_pixmap_FIBSEM = self.current_pixmap_FIBSEM.scaled(
                    640, 400, QtCore.Qt.KeepAspectRatio)
                self.label_image_FIBSEM.setPixmap(self.current_pixmap_FIBSEM)

                self.fill_save_information("FIBSEM")
                """Updating display of GUI with current FIBSEM image"""

        except Exception as e:
            _error_message( traceback.format_exc())

    def fill_save_information(self, modality):
        """Fills Save Destination and Save Filename using image path"""
        try:
            if modality == "FM":
                [destination, self.save_name] = os.path.split(self.current_path_FM)

                if not self.checkBox_save_destination_FM.isChecked():
                    destination = destination + self.delim
                    self.save_destination_FM = destination
                    self.lineEdit_save_destination_FM.setText(
                        self.save_destination_FM)

                self.lineEdit_save_filename_FM.setText(self.save_name)

            elif modality == "FIBSEM":
                [destination, self.save_name] = os.path.split(
                    self.current_path_FIBSEM)

                if not self.checkBox_save_destination_FIBSEM.isChecked():
                    destination = destination + self.delim
                    self.save_destination_FIBSEM = destination
                    self.lineEdit_save_destination_FIBSEM.setText(
                        self.save_destination_FIBSEM)

                self.lineEdit_save_filename_FIBSEM.setText(self.save_name)
        except Exception as e:
            _error_message( traceback.format_exc())

    def fill_destination(self, modality):
        """Fills the destination box with the text from the directory"""
        try:
            if modality == "FM":
                if not self.checkBox_save_destination_FM.isChecked():
                    self.save_destination_FM = os.path.normpath(
                        QtWidgets.QFileDialog.getExistingDirectory(
                            self, 'File Destination'))
                    destination_text = self.save_destination_FM + self.delim
                    self.lineEdit_save_destination_FM.setText(destination_text)
            elif modality == "FIBSEM":
                if not self.checkBox_save_destination_FIBSEM.isChecked():
                    self.save_destination_FIBSEM = os.path.normpath(
                        QtWidgets.QFileDialog.getExistingDirectory(
                            self, 'File Destination'))
                    destination_text = \
                        self.save_destination_FIBSEM + self.delim
                    self.lineEdit_save_destination_FIBSEM.setText(
                        destination_text)
        except Exception as e:
            _error_message( traceback.format_exc())

    def fill_correlation_destination(self):
        self.save_destination_correlation = os.path.normpath(
            QtWidgets.QFileDialog.getExistingDirectory(
                self, 'File Destination'))
        destination_text = self.save_destination_correlation + self.delim
        self.correlation_output_path.setText(destination_text)

    def acquire_volume(self):
        try:
            laser_dict = self.laser_dict
            if laser_dict == {}:
                raise ValueError("No lasers selected")
            if len(laser_dict) > 3:
                raise ValueError("Select max 3 lasers")

            no_z_slices = int(self.lineEdit_slice_number.text())
            if no_z_slices < 0:
                raise ValueError("Number of slices must be a positive integer")

            z_slice_distance = int(self.lineEdit_slice_distance.text())
            if z_slice_distance < 0:
                raise ValueError("Slice distance must be a positive integer")

            destination_for_continual_saving = self.lineEdit_save_destination_FM.text()
            volume = piescope.lm.volume.volume_acquisition(
                laser_dict, no_z_slices, z_slice_distance, destination_for_continual_saving)
            max_intensity = piescope.utils.max_intensity_projection(volume)
            channel = 0

            rgb = self.create_rgb(max_intensity)

            self.string_list_FM = ["RGB image"]
            self.array_list_FM = rgb
            self.update_display("FM")

            for las in laser_dict:
                destination = self.lineEdit_save_destination_FM.text() + \
                              "\\volume_stack_wavelength_" + str(las) + "_" + \
                              time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())
                os.makedirs(destination)
                channel_max = max_intensity[:, :, channel]
                piescope.utils.save_image(image=channel_max, dest=destination + "\\Maximum_intensity_projection.tif")

                for z_slice in range(0, np.shape(volume)[0]):
                    piescope.utils.save_image(image=volume[z_slice, :, :, channel], dest=destination + "\\slice__" + str(z_slice) + ".tif")

                channel = channel + 1

        except Exception as e:
            _error_message( traceback.format_exc())

    def create_rgb(self, max_intensity):
        """

        :param max_intensity: np.ndarray with shape (col, row, channels).  Expecting at most 3 channels.
        :return: rgb image
        """
        col = max_intensity.shape[0]
        row = max_intensity.shape[1]
        rgb = np.zeros(shape=(col, row, 3), dtype=np.uint8)
        if max_intensity.shape[2] > 3:
            raise ValueError("Too many channels")
        elif max_intensity.shape[2] == 3:
            rgb = max_intensity
        elif max_intensity.shape[2] == 2:
            rgb[:, :, 0] = max_intensity[:, :, 0]
            rgb[:, :, 1] = max_intensity[:, :, 1]
        else:
            rgb[:, :, 0] = max_intensity[:, :, 0]

        return rgb

    def correlateim(self):
        tempfile = "C:"
        try:
            fluorescence_image = self.array_list_FM
            print(type(fluorescence_image))

            if fluorescence_image == [] or fluorescence_image == "":
                raise ValueError("No first image selected")
            fibsem_image = self.array_list_FIBSEM
            if fibsem_image == [] or fibsem_image == "":
                raise ValueError("No second image selected")

            output_filename = self.correlation_output_path.text()
            if output_filename == "":
                raise ValueError("No path selected")
            if not os.path.isdir(output_filename):
                raise ValueError("Please select a valid directory")

            image_ext = "\\correlated_image_" + time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())
            copy_count = 1

            while os.path.isfile(output_filename + image_ext + "_" + str(copy_count) + ".tiff"):
                copy_count = copy_count + 1

            tempfile = output_filename + image_ext + "_" + str(copy_count) + "temp_.tiff"
            open(tempfile, "w+")

            output_filename = output_filename + image_ext + "_" + str(copy_count) + ".tiff"

            window = corr.open_correlation_window(self, fluorescence_image,
                                                                  fibsem_image,
                                                                  output_filename)
            window.showMaximized()
            window.show()

            window.exitButton.clicked.connect(lambda: self.mill_window_from_correlation(window))

            if os.path.isfile(tempfile):
                os.remove(tempfile)

        except Exception as e:
            if os.path.isfile(tempfile):
                os.remove(tempfile)
            _error_message( traceback.format_exc())

    def mill_window_from_correlation(self, window):
        result, overlay_adorned_image, fluorescence_image_rgb, fluorescence_original, output, matched_points_dict = window.menu_quit()
        piescope_gui.milling.open_milling_window(self, result, overlay_adorned_image, fluorescence_image_rgb, fluorescence_original, output, matched_points_dict)

    def milling(self):
        try:
            [image, ext] = QtWidgets.QFileDialog.getOpenFileNames(
                self, 'Open Milling Image',
                filter="Images (*.bmp *.tif *.tiff *.jpg)"
                )

            from autoscript_sdb_microscope_client.structures import AdornedImage
            adorned_image = AdornedImage()
            adorned_image = adorned_image.load(image[0])
            if image:
                image = _create_array_list(image, "MILLING")
            else:
                raise ValueError("No image selected")

            piescope_gui.milling.open_milling_window(self, image, adorned_image)

        except Exception as e:
            _error_message( traceback.format_exc())

    def live_imaging_event_listener_FM(self, stop_event):
        state = True

        while state and not stop_event.isSet():
            self.get_basler_image(self.comboBox_laser_basler.currentText(),
                                  self.lineEdit_exposure_basler.text(),
                                  self.lineEdit_power_basler_2.text(),
                                  self.lasers, self.basler, "live")


def _create_array_list(input_list, modality):
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


def _error_message(message):
    logging.exception(message)
    error_dialog = QtWidgets.QErrorMessage()
    error_dialog.showMessage(message)
    error_dialog.exec_()
    return error_dialog


def main():
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()


if __name__ == '__main__':
    main()
