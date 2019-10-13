"""Functions that interact directly with or update the user interface"""
from PyQt5 import QtWidgets, QtGui, QtCore
import qimage2ndarray as q
import os
import os.path as p
import piescope_gui.piescope_interaction as inout


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
                display_image = self.array_list_FM[self.slider_stack.value() - 1]
                print(display_image)
            [save_base, ext] = p.splitext(self.lineEdit_save_filename.text())
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
        if self.current_image:
            max_value = len(self.string_list)
            if max_value == 1:
                display_image = self.array_list_FIBSEM
                print(display_image)
            else:
                display_image = self.array_list_FIBSEM[self.slider_stack.value() - 1]
                print(display_image)
            [save_base, ext] = p.splitext(self.lineEdit_save_filename.text())
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
            self.lineEdit_save_destination_FM.setText(self.save_destination)

        self.lineEdit_save_filename_FM.setText(self.save_name)

    elif modality == "FIBSEM":
        [destination, self.save_name] = p.split(self.current_path_FIBSEM)

        if not self.checkBox_save_destination_FIBSEM.isChecked():
            destination = destination + self.delim
            self.save_destination_FIBSEM = destination
            self.lineEdit_save_destination_FIBSEM.setText(self.save_destination)

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


def error_msg(self, message):
    error_dialog = QtWidgets.QErrorMessage()
    error_dialog.showMessage(message)
    error_dialog.exec_()
