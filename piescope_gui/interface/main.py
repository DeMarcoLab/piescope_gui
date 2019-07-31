from PyQt5 import QtWidgets, QtGui
import qimage2ndarray as q
import os
import os.path as p
import piescope_gui.inputoutput.main as inout


def open_images(self):
    """Open image files and display the first"""
    [self.string_list, ext] = QtWidgets.QFileDialog.getOpenFileNames(
        self, 'Open File', filter="Images (*.bmp *.tif *.tiff *.jpg)")

    if self.string_list:
        self.array_list = inout.create_array_list(self.string_list)
        self.slider_stack.setMaximum(len(self.string_list))
        self.spinbox_slider.setMaximum(len(self.string_list))
        self.slider_stack.setValue(1)
        self.update_display()


def save_image(self):
    """Save image on display """
    if self.current_image:
        display_image = self.imagearray_list[self.slider_stack.value() - 1]
        [save_base, ext] = p.splitext(self.lineEdit_save_filename.text())
        dest = self.lineEdit_save_destination.text() + self.delim \
               + save_base + ".tiff"
        dir_exists = p.isdir(self.lineEdit_save_destination.text())
        if not dir_exists:
            os.makedirs(self.lineEdit_save_destination.text())
            inout.save_image(self, display_image, dest)
        else:
            exists = p.isfile(dest)
            if not exists:
                inout.save_image(self, display_image, dest)
            else:
                count = 1
                while exists:
                    dest = self.lineEdit_save_destination.text() + \
                           self.delim + save_base + "(" + str(count) + \
                           ").tiff"
                    exists = p.isfile(dest)
                    count = count + 1
                inout.save_image(self, display_image, dest)


def update_display(self):
    """Update the GUI display with the current image"""
    if self.string_list:
        slider_value = str(self.slider_stack.value())
        max_value = str(len(self.string_list))

        image_string = self.string_list[int(slider_value) - 1]

        if int(max_value) > 1:
            image_array = self.array_list[int(slider_value) - 1]
        else:
            image_array = self.array_list

        self.current_image = q.array2qimage(image_array)
        self.current_path = p.normpath(image_string)

        self.status.setText("Image " + slider_value + " of " + max_value)

        self.current_pixmap = QtGui.QPixmap.fromImage(self.current_image)
        self.label_image.setPixmap(self.current_pixmap)

        self.fill_save_information()
        """Updating display of GUI with current image"""


def fill_save_information(self):
    """Fills Save Destination and Save Filename using image path"""
    [destination, self.save_name] = p.split(self.current_path)
    if not self.checkBox_save_destination.isChecked():

        destination = destination + self.delim
        self.save_destination = destination
        self.lineEdit_save_destination.setText(self.save_destination)

    self.lineEdit_save_filename.setText(self.save_name)
