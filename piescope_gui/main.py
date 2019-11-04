import os.path as p
import os

import piescope.lm.volume as volume_function
import piescope_gui.milling.main as milling_function
import piescope_gui.correlation.main as correlation_function
import piescope_gui.piescope_interaction as piescope_hardware
import piescope_gui.qtdesigner_files.main as gui_main
import piescope.utils as util
import piescope.maximum_intensity_projection as mip

from PyQt5 import QtWidgets, QtGui, QtCore
import qimage2ndarray as q
import logging
import numpy as np

logger = logging.getLogger(__name__)


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()
        self.setupUi(self)
        self.setup_connections()

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

        self.delim = p.normpath("/")
        self.liveCheck = True
        self.microscope = None

        self.save_name = ""
        self.laser_dict = {}
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
            lambda: piescope_hardware.update_laser_dict(self, "laser640"))
        self.checkBox_laser2.clicked.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser561"))
        self.checkBox_laser3.clicked.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser488"))
        self.checkBox_laser4.clicked.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser405"))

        self.slider_laser1.valueChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser640"))
        self.slider_laser2.valueChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser561"))
        self.slider_laser3.valueChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser488"))
        self.slider_laser4.valueChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser405"))

        self.lineEdit_exposure_1.textChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser640"))
        self.lineEdit_exposure_2.textChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser561"))
        self.lineEdit_exposure_3.textChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser488"))
        self.lineEdit_exposure_4.textChanged.connect(
            lambda: piescope_hardware.update_laser_dict(self, "laser405"))

        self.button_get_image_FIB.clicked.connect(
            lambda: piescope_hardware.get_FIB_image(self, self.microscope))
        self.button_get_image_SEM.clicked.connect(
            lambda: piescope_hardware.get_SEM_image(self, self.microscope))
        self.button_last_image_FIB.clicked.connect(
            lambda: piescope_hardware.get_last_FIB_image(self,
                                                         self.microscope))
        self.button_last_image_SEM.clicked.connect(
            lambda: piescope_hardware.get_last_SEM_image(self,
                                                         self.microscope))

        self.button_get_image_FM.clicked.connect(
            lambda: piescope_hardware.get_basler_image(self,
                self.comboBox_laser_basler.currentText(),
                self.lineEdit_exposure_basler.text()))
        self.button_live_image_FM.clicked.connect(
            lambda: piescope_hardware.basler_live_imaging(self))

        self.pushButton_initialise_stage.clicked.connect(
            lambda: piescope_hardware.initialise_stage(self))
        self.pushButton_move_absolute.clicked.connect(
            lambda: piescope_hardware.move_absolute(
                self, self.lineEdit_move_absolute.text()))
        self.pushButton_move_relative.clicked.connect(
            lambda: piescope_hardware.move_relative(
                self, self.lineEdit_move_relative.text()))

        self.connect_microscope.clicked.connect(
            lambda: piescope_hardware.connect_to_microscope(self))
        self.to_light_microscope.clicked.connect(
            lambda: piescope_hardware.move_to_light_microscope(
                self, self.microscope, 50.0e-3, 0.0))
        self.to_electron_microscope.clicked.connect(
            lambda: piescope_hardware.move_to_electron_microscope(
                self, self.microscope, -50.0e-3, 0.0))

        self.pushButton_volume.clicked.connect(self.acquire_volume)
        self.pushButton_correlation.clicked.connect(self.correlateim)
        self.pushButton_milling.clicked.connect(self.milling)

    def open_images(self, modality):
        """Open image files and display the first"""
        try:
            if modality == "FM":
                [self.string_list_FM,
                 ext] = QtWidgets.QFileDialog.getOpenFileNames(
                    self, 'Open File',
                    filter="Images (*.bmp *.tif *.tiff *.jpg)")

                if self.string_list_FM:
                    self.array_list_FM = piescope_hardware.create_array_list(
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
                    self.array_list_FIBSEM = piescope_hardware.\
                        create_array_list(self.string_list_FIBSEM, "FIBSEM")
                    self.slider_stack_FIBSEM.setMaximum(
                        len(self.string_list_FIBSEM))
                    self.spinbox_slider_FIBSEM.setMaximum(
                        len(self.string_list_FIBSEM))
                    self.slider_stack_FIBSEM.setValue(1)
                    self.update_display("FIBSEM")
        except Exception as e:
            logger.exception(e)
            self.error_msg(str(e))

    def save_image(self, modality):
        """Save image on display """
        try:
            if modality == "FM":
                if self.current_image_FM:
                    max_value = len(self.string_list_FM)
                    if max_value == 1:
                        display_image = self.array_list_FM
                        print(display_image)
                    else:
                        display_image = self.array_list_FM[
                            self.slider_stack_FM.value() - 1]
                        print(display_image)
                    [save_base, ext] = p.splitext(
                        self.lineEdit_save_filename_FM.text())
                    dest = self.lineEdit_save_destination_FM.text() + self.delim \
                           + save_base + ".tiff"
                    dir_exists = p.isdir(
                        self.lineEdit_save_destination_FM.text())
                    if not dir_exists:
                        os.makedirs(self.lineEdit_save_destination_FM.text())
                        util.save_image(display_image, dest)
                    else:
                        exists = p.isfile(dest)
                        if not exists:
                            util.save_image(display_image, dest)
                        else:
                            count = 1
                            while exists:
                                dest = self.lineEdit_save_destination_FM.text() + \
                                       self.delim + save_base + "(" + str(
                                    count) + \
                                       ").tiff"
                                exists = p.isfile(dest)
                                count = count + 1
                                util.save_image(display_image,
                                                             dest)
                else:
                    logger.error("No image to save")
                    self.error_msg("No image to save")

            elif modality == "FIBSEM":
                if self.current_image_FIBSEM:
                    max_value = len(self.string_list_FIBSEM)
                    if max_value == 1:
                        display_image = self.array_list_FIBSEM
                        print(display_image)
                    else:
                        display_image = self.array_list_FIBSEM[
                            self.slider_stack_FIBSEM.value() - 1]
                        print(display_image)
                    [save_base, ext] = p.splitext(
                        self.lineEdit_save_filename_FIBSEM.text())
                    dest = self.lineEdit_save_destination_FIBSEM.text() + \
                           self.delim + save_base + ".tiff"
                    dir_exists = p.isdir(
                        self.lineEdit_save_destination_FIBSEM.text())
                    if not dir_exists:
                        os.makedirs(
                            self.lineEdit_save_destination_FIBSEM.text())
                        util.save_image(display_image, dest)
                    else:
                        exists = p.isfile(dest)
                        if not exists:
                            util.save_image(display_image, dest)
                        else:
                            count = 1
                            while exists:
                                dest = self.lineEdit_save_destination_FIBSEM.text() + \
                                       self.delim + save_base + "(" + str(
                                    count) + \
                                       ").tiff"
                                exists = p.isfile(dest)
                                count = count + 1
                                util.save_image(display_image,
                                                             dest)
                else:
                    logger.error("No image to save")
                    self.error_msg("No image to save")

        except Exception as e:
            logger.exception(e)
            self.error_msg(str(e))

    def update_display(self, modality):
        """Update the GUI display with the current image"""
        try:
            if modality == "FM" and self.string_list_FM:
                slider_value = str(self.slider_stack_FM.value())
                max_value = str(len(self.string_list_FM))

                image_string = self.string_list_FM[int(slider_value) - 1]

                if int(max_value) > 1:
                    image_array = self.array_list_FM[int(slider_value) - 1]
                else:
                    image_array = self.array_list_FM

                self.current_image_FM = q.array2qimage(image_array)
                print(self.current_image_FM)
                self.current_path_FM = p.normpath(image_string)

                self.status.setText(
                    "Image " + slider_value + " of " + max_value)

                self.current_pixmap_FM = QtGui.QPixmap.fromImage(
                    self.current_image_FM)
                self.current_pixmap_FM = self.current_pixmap_FM.scaled(
                    640, 400, QtCore.Qt.KeepAspectRatio)
                self.label_image_FM.setPixmap(self.current_pixmap_FM)

                self.fill_save_information("FM")
                """Updating display of GUI with current FM image"""

            elif modality == "FIBSEM" and self.string_list_FIBSEM:
                slider_value = str(self.slider_stack_FIBSEM.value())
                max_value = str(len(self.string_list_FIBSEM))

                image_string = self.string_list_FIBSEM[int(slider_value) - 1]

                if int(max_value) > 1:
                    image_array = self.array_list_FIBSEM[int(slider_value) - 1]
                else:
                    image_array = self.array_list_FIBSEM

                self.current_image_FIBSEM = q.array2qimage(image_array)
                print(self.current_image_FIBSEM)
                self.current_path_FIBSEM = p.normpath(image_string)

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
            logger.exception(e)
            self.error_msg(str(e))

    def fill_save_information(self, modality):
        """Fills Save Destination and Save Filename using image path"""
        try:
            if modality == "FM":
                [destination, self.save_name] = p.split(self.current_path_FM)

                if not self.checkBox_save_destination_FM.isChecked():
                    destination = destination + self.delim
                    self.save_destination_FM = destination
                    self.lineEdit_save_destination_FM.setText(
                        self.save_destination_FM)

                self.lineEdit_save_filename_FM.setText(self.save_name)

            elif modality == "FIBSEM":
                [destination, self.save_name] = p.split(
                    self.current_path_FIBSEM)

                if not self.checkBox_save_destination_FIBSEM.isChecked():
                    destination = destination + self.delim
                    self.save_destination_FIBSEM = destination
                    self.lineEdit_save_destination_FIBSEM.setText(
                        self.save_destination_FIBSEM)

                self.lineEdit_save_filename_FIBSEM.setText(self.save_name)
        except Exception as e:
            logger.exception(e)
            self.error_msg(str(e))

    def fill_destination(self, modality):
        """Fills the destination box with the text from the directory"""
        try:
            if modality == "FM":
                if not self.checkBox_save_destination_FM.isChecked():
                    self.save_destination_FM = p.normpath(
                        QtWidgets.QFileDialog.getExistingDirectory(
                            self, 'File Destination'))
                    destination_text = self.save_destination_FM + self.delim
                    self.lineEdit_save_destination_FM.setText(destination_text)
            elif modality == "FIBSEM":
                if not self.checkBox_save_destination_FIBSEM.isChecked():
                    self.save_destination_FIBSEM = p.normpath(
                        QtWidgets.QFileDialog.getExistingDirectory(
                            self, 'File Destination'))
                    destination_text = \
                        self.save_destination_FIBSEM + self.delim
                    self.lineEdit_save_destination_FIBSEM.setText(
                        destination_text)
        except Exception as e:
            logger.exception(e)
            self.error_msg(str(e))

    def fill_correlation_destination(self):
        self.save_destination_correlation = p.normpath(
            QtWidgets.QFileDialog.getExistingDirectory(
                self, 'File Destination'))
        destination_text = self.save_destination_correlation + self.delim
        self.correlation_output_path.setText(destination_text)

    def acquire_volume(self):
        try:
            laser_dict = self.laser_dict
            if laser_dict == {}:
                raise ValueError("No lasers selected")

            no_z_slices = int(self.lineEdit_slice_number.text())
            if no_z_slices < 0:
                raise ValueError("Number of slices must be a positive integer")

            z_slice_distance = int(self.lineEdit_slice_distance.text())
            if z_slice_distance < 0:
                raise ValueError("Slice distance must be a positive integer")

            volume = volume_function.volume_acquisition(
                laser_dict, no_z_slices, z_slice_distance)
            max_intensity = mip.max_intensity_projection(volume)
            channel = 0

            for las in laser_dict:
                destination = self.lineEdit_save_destination_FM.text() + \
                              "\\volume_stack_wavelength_" + str(las) + "_" + \
                              correlation_function._timestamp()
                os.makedirs(destination)
                channel_max = max_intensity[:, :, channel]
                util.save_image(image=channel_max, dest=destination + "\\Maximum_intensity_projection.tiff")

                for z_slice in range(0, np.shape(volume)[0]):
                    util.save_image(image=volume[z_slice, :, :, channel], dest=destination + "\\slice__" + str(z_slice) + ".tiff")

                channel = channel + 1

        except Exception as e:
            self.error_msg(str(e))
            print(e)

    def correlateim(self):
        tempfile = "C:"
        try:
            input_filename_1 = self.array_list_FM
            print(type(input_filename_1))

            if input_filename_1 == [] or input_filename_1 == "":
                raise ValueError("No first image selected")
            input_filename_2 = self.array_list_FIBSEM
            if input_filename_2 == [] or input_filename_2 == "":
                raise ValueError("No second image selected")

            output_filename = self.correlation_output_path.text()
            if output_filename == "":
                raise ValueError("No path selected")
            if not p.isdir(output_filename):
                raise ValueError("Please select a valid directory")

            image_ext = "\\correlated_image_" + correlation_function._timestamp()
            copy_count = 1

            while p.isfile(output_filename + image_ext + "_" + str(copy_count) + ".tiff"):
                copy_count = copy_count + 1

            tempfile = output_filename + image_ext + "_" + str(copy_count) + "temp_.tiff"
            open(tempfile, "w+")

            output_filename = output_filename + image_ext + "_" + str(copy_count) + ".tiff"

            correlation_function.open_correlation_window(self, input_filename_1,
                                                        input_filename_2,
                                                        output_filename)
            if p.isfile(tempfile):
                os.remove(tempfile)

        except Exception as e:
            if p.isfile(tempfile):
                os.remove(tempfile)
            self.error_msg(str(e))
            print(e)

    def milling(self):
        try:
            [image, ext] = QtWidgets.QFileDialog.getOpenFileNames(self,
                'Open Milling Image',
                filter="Images (*.bmp *.tif *.tiff *.jpg)")
            if image:
                image = piescope_hardware.create_array_list(image, "MILLING")
            else:
                raise ValueError("No image selected")
            milling_function.open_milling_window(self, image)

        except Exception as e:
            self.error_msg(str(e))
            print(e)

    def live_imaging_event_listener_FM(self, stop_event):
        state = True
        while state and not stop_event.isSet():
            piescope_hardware.get_basler_image(self)

    def error_msg(self, message):
        error_dialog = QtWidgets.QErrorMessage()
        error_dialog.showMessage(message)
        error_dialog.exec_()


def main():
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()


if __name__ == '__main__':
    main()
