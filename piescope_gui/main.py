import os.path as p
import os

import piescope.lm.volume as volume
import piescope_gui.milling.main as mill
import piescope_gui.correlation.main as correlate
import piescope_gui.piescope_interaction as inout
import piescope_gui.qtdesigner_files.main as gui_main

from PyQt5 import QtWidgets, QtGui, QtCore
import qimage2ndarray as q


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()
        self.setupUi(self)
        self.DEFAULT_PATH = "C:\\Users\\Admin\\Pictures\\Basler"

        self.setWindowTitle("PIEScope User Interface")
        self.statusbar.setSizeGripEnabled(0)
        self.status = QtWidgets.QLabel(self.statusbar)
        self.status.setAlignment(QtCore.Qt.AlignRight)

        self.statusbar.addPermanentWidget(self.status, 1)
        self.lineEdit_save_destination_FM.setText(self.DEFAULT_PATH)
        self.checkBox_save_destination_FM.setChecked(1)
        self.lineEdit_save_filename_FM.setText("Image")
        self.lineEdit_save_destination_FIBSEM.setText(self.DEFAULT_PATH)
        self.checkBox_save_destination_FIBSEM.setChecked(1)
        self.lineEdit_save_filename_FIBSEM.setText("Image")

        self.temp = None
        self.microscope = None
        self.save_name = ""
        self.power1 = 0
        self.power2 = 0
        self.power3 = 0
        self.power4 = 0
        self.liveCheck = True
        self.array_list_FM = []
        self.array_list_FIBSEM = []
        self.laser_dict = {}
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
        self.delim = p.normpath("/")

        self.actionOpen_FM_Image.triggered.connect(
            lambda: self.open_images("FM"))
        self.actionSave_FM_Image.triggered.connect(
            lambda: self.save_image("FM"))
        self.slider_stack_FM.valueChanged.connect(
            lambda: self.update_display("FM"))
        self.button_save_destination_FM.clicked.connect(
            lambda: self.fill_destination("FM"))

        self.actionOpen_FIBSEM_Image.triggered.connect(
            lambda: self.open_images("FIBSEM"))
        self.actionSave_FIBSEM_Image.triggered.connect(
            lambda: self.save_image("FIBSEM"))
        self.slider_stack_FIBSEM.valueChanged.connect(
            lambda: self.update_display("FIBSEM"))
        self.button_save_destination_FIBSEM.clicked.connect(
            lambda: self.fill_destination("FIBSEM"))

        self.slider_laser1.valueChanged.connect(lambda: self.update_laser_dict(
                                                "laser640"))
        self.slider_laser2.valueChanged.connect(lambda: self.update_laser_dict(
                                                "laser561"))
        self.slider_laser3.valueChanged.connect(lambda: self.update_laser_dict(
                                                "laser488"))
        self.slider_laser4.valueChanged.connect(lambda: self.update_laser_dict(
                                                "laser405"))

        self.checkBox_laser1.clicked.connect(lambda: self.update_laser_dict(
                                                "laser640"))
        self.checkBox_laser2.clicked.connect(lambda: self.update_laser_dict(
                                                "laser561"))
        self.checkBox_laser3.clicked.connect(lambda: self.update_laser_dict(
                                                "laser488"))
        self.checkBox_laser4.clicked.connect(lambda: self.update_laser_dict(
                                                "laser405"))

        self.to_light_microscope.clicked.connect(
            lambda: self.move_to_light_microscope(
                self.microscope, 50.0e-3, 0.0))

        self.to_electron_microscope.clicked.connect(
            lambda: self.move_to_electron_microscope(
                self.microscope, -50.0e-3, 0.0))

        self.button_get_image_FIB.clicked.connect(
            lambda: self.get_FIB_image(self.microscope))

        self.button_get_image_SEM.clicked.connect(
            lambda: self.get_SEM_image(self.microscope))

        self.pushButton_volume.clicked.connect(self.acquire_volume)

        self.button_get_image_FM.clicked.connect(self.get_basler_image)

        self.button_live_image_FM.clicked.connect(self.basler_live_image)

        self.pushButton_move_absolute.clicked.connect(self.current_position)

        self.pushButton_move_relative.clicked.connect(self.move_relative)

        self.pushButton_initialise_stage.clicked.connect(self.initialise_stage)

        self.pushButton_correlation.clicked.connect(self.correlateim)

        self.connect_microscope.clicked.connect(self.connect_to_microscope)

        self.button_last_image_FIB.clicked.connect(self.get_last_FIB_image)

        self.button_last_image_SEM.clicked.connect(self.get_last_SEM_image)

        self.pushButton_milling.clicked.connect(self.milling)

    def open_images(self, modality):
        """Open image files and display the first"""
        if modality == "FM":
            [self.string_list_FM, ext] = QtWidgets.QFileDialog.getOpenFileNames(
                self, 'Open File', filter="Images (*.bmp *.tif *.tiff *.jpg)")

            if self.string_list_FM:
                self.array_list_FM = inout.create_array_list(self.string_list_FM, "FM")
                self.slider_stack_FM.setMaximum(len(self.string_list_FM))
                self.spinbox_slider_FM.setMaximum(len(self.string_list_FM))
                self.slider_stack_FM.setValue(1)
                self.update_display("FM")

        elif modality == "FIBSEM":
            [self.string_list_FIBSEM, ext] = QtWidgets.QFileDialog.getOpenFileNames(
                self, 'Open File', filter="Images (*.bmp *.tif *.tiff *.jpg)")

            if self.string_list_FIBSEM:
                self.array_list_FIBSEM = inout.create_array_list(self.string_list_FIBSEM, "FIBSEM")
                self.slider_stack_FIBSEM.setMaximum(len(self.string_list_FIBSEM))
                self.spinbox_slider_FIBSEM.setMaximum(len(self.string_list_FIBSEM))
                self.slider_stack_FIBSEM.setValue(1)
                self.update_display("FIBSEM")

    def save_image(self, modality):
        """Save image on display """
        if modality == "FM":
            if self.current_image_FM:
                max_value = len(self.string_list_FM)
                if max_value == 1:
                    display_image = self.array_list_FM
                    print(display_image)
                else:
                    display_image = self.array_list_FM[self.slider_stack_FM.value() - 1]
                    print(display_image)
                [save_base, ext] = p.splitext(self.lineEdit_save_filename_FM.text())
                dest = self.lineEdit_save_destination_FM.text() + self.delim \
                       + save_base + ".tiff"
                dir_exists = p.isdir(self.lineEdit_save_destination_FM.text())
                if not dir_exists:
                    os.makedirs(self.lineEdit_save_destination_FM.text())
                    inout.save_image(display_image, dest)
                else:
                    exists = p.isfile(dest)
                    if not exists:
                        inout.save_image(display_image, dest)
                    else:
                        count = 1
                        while exists:
                            dest = self.lineEdit_save_destination_FM.text() + \
                                   self.delim + save_base + "(" + str(count) + \
                                   ").tiff"
                            exists = p.isfile(dest)
                            count = count + 1
                        inout.save_image(display_image, dest)

        elif modality == "FIBSEM":
            if self.current_image_FIBSEM:
                max_value = len(self.string_list_FIBSEM)
                if max_value == 1:
                    display_image = self.array_list_FIBSEM
                    print(display_image)
                else:
                    display_image = self.array_list_FIBSEM[self.slider_stack_FIBSEM.value() - 1]
                    print(display_image)
                [save_base, ext] = p.splitext(self.lineEdit_save_filename_FIBSEM.text())
                dest = self.lineEdit_save_destination_FIBSEM.text() + self.delim \
                       + save_base + ".tiff"
                dir_exists = p.isdir(self.lineEdit_save_destination_FIBSEM.text())
                if not dir_exists:
                    os.makedirs(self.lineEdit_save_destination_FIBSEM.text())
                    inout.save_image(display_image, dest)
                else:
                    exists = p.isfile(dest)
                    if not exists:
                        inout.save_image(display_image, dest)
                    else:
                        count = 1
                        while exists:
                            dest = self.lineEdit_save_destination_FIBSEM.text() + \
                                   self.delim + save_base + "(" + str(count) + \
                                   ").tiff"
                            exists = p.isfile(dest)
                            count = count + 1
                        inout.save_image(display_image, dest)

    def update_display(self, modality):
        """Update the GUI display with the current image"""
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

            self.status.setText("Image " + slider_value + " of " + max_value)

            self.current_pixmap_FM = QtGui.QPixmap.fromImage(self.current_image_FM)
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

            self.status.setText("Image " + slider_value + " of " + max_value)

            self.current_pixmap_FIBSEM = QtGui.QPixmap.fromImage(self.current_image_FIBSEM)
            self.current_pixmap_FIBSEM = self.current_pixmap_FIBSEM.scaled(
                640, 400, QtCore.Qt.KeepAspectRatio)
            self.label_image_FIBSEM.setPixmap(self.current_pixmap_FIBSEM)

            self.fill_save_information("FIBSEM")
            """Updating display of GUI with current FIBSEM image"""

    def fill_save_information(self, modality):
        """Fills Save Destination and Save Filename using image path"""

        if modality == "FM":
            [destination, self.save_name] = p.split(self.current_path_FM)

            if not self.checkBox_save_destination_FM.isChecked():
                destination = destination + self.delim
                self.save_destination_FM = destination
                self.lineEdit_save_destination_FM.setText(self.save_destination_FM)

            self.lineEdit_save_filename_FM.setText(self.save_name)

        elif modality == "FIBSEM":
            [destination, self.save_name] = p.split(self.current_path_FIBSEM)

            if not self.checkBox_save_destination_FIBSEM.isChecked():
                destination = destination + self.delim
                self.save_destination_FIBSEM = destination
                self.lineEdit_save_destination_FIBSEM.setText(self.save_destination_FIBSEM)

            self.lineEdit_save_filename_FIBSEM.setText(self.save_name)

    def fill_destination(self, modality):
        """Fills the destination box with the text from the directory"""
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
                destination_text = self.save_destination_FIBSEM + self.delim
                self.lineEdit_save_destination_FIBSEM.setText(destination_text)

    def acquire_volume(self):
        exposure_time = self.lineEdit_exposure.text()
        laser_dict = self.laser_dict
        no_z_slices = self.lineEdit_slice_number.text()
        z_slice_distance = self.lineEdit_slice_distance.text()
        try:
            volume.volume_acquisition(self, exposure_time, laser_dict,
                                  no_z_slices, z_slice_distance)
        except Exception as e:
            print(e)

    def correlateim(self):
        input_filename_1 = self.array_list_FM
        input_filename_2 = self.array_list_FIBSEM
        output_filename = self.correlation_output_path.text()
        correlate.open_correlation_window(self, input_filename_1,
                                          input_filename_2, output_filename)

    def milling(self):
        [image, ext] = QtWidgets.QFileDialog.getOpenFileNames(self,
        'Open Milling Image', filter="Images (*.bmp *.tif *.tiff *.jpg)")
        if image:
            image = inout.create_array_list(image, "MILLING")
        else:
            print("No image selected")
            return
        mill.open_milling_window(self, image)

    def error_msg(self, message):
        error_dialog = QtWidgets.QErrorMessage()
        error_dialog.showMessage(message)
        error_dialog.exec_()

    def connect_to_microscope(self):
        inout.connect_to_microscope(self)

    def move_to_light_microscope(self, microscope, x, y):
        inout.move_to_light_microscope(self, microscope, x, y)

    def move_to_electron_microscope(self, microscope, x, y):
        inout.move_to_electron_microscope(self, microscope, x, y)

    def live_imaging_event_listener_FM(self, stop_event):
        state = True
        while state and not stop_event.isSet():
            self.get_basler_image()

    def get_SEM_image(self, microscope):
        inout.get_SEM_image(self, microscope)

    def get_FIB_image(self, microscope):
        inout.get_FIB_image(self, microscope)

    def get_last_SEM_image(self, microscope):
        inout.get_last_SEM_image(self, microscope)

    def get_last_FIB_image(self, microscope):
        inout.get_last_FIB_image(self, microscope)

    def get_basler_image(self):
        try:
            inout.get_basler_image(self)
        except Exception as e:
            print(e)
            print('Could not grab basler image')
            return

    def basler_live_image(self):
        try:
            inout.basler_live_imaging(self)
        except Exception as e:
            print(e)
            print('Live imaging failed')
            return

    def update_laser_dict(self, laser):
        inout.update_laser_dict(self, laser)

    def initialise_stage(self):
        inout.initialise_stage()

    def move_absolute(self):
        distance = int(self.lineEdit_move_absolute.text())
        inout.move_absolute(distance)

    def move_relative(self):
        distance = int(self.lineEdit_move_relative.text())
        inout.move_relative(distance)

    def current_position(self):
        current_position = inout.current_position()
        print(current_position)


def main():
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()


if __name__ == '__main__':
    main()
