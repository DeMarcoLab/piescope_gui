from PyQt5 import QtWidgets, QtGui, QtCore
import os.path as p
import os
import ui.main as gui_main
import qimage2ndarray
import numpy as np
import inputoutput.main as inout
import time
import serial
import asyncio
from threading import Thread


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("FIBSEM User Interface")
        self.statusbar.setSizeGripEnabled(0)


        self.status = QtWidgets.QLabel(self.statusbar)
        self.status.setAlignment(QtCore.Qt.AlignRight)
        self.statusbar.addPermanentWidget(self.status, 1)
        self.basler = inout.Basler()

        self.image_list = []
        self.basler_raw = []
        self.basler_list = []
        self.basler_images = []
        self.current_image = ""
        self.current_path = ""
        self.laser = ""
        self.power = 0
        self.queue = asyncio.Queue()

        self.current_pixmap = ""
        self.save_destination = ""
        self.save_name = ""

        self.delim = p.normpath("/")

        # self.laser_change()

        self.actionOpen.triggered.connect(self.open_images)
        self.actionSave.triggered.connect(self.save_image)

        self.short_o = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        self.short_o.activated.connect(self.open_images)
        self.short_s = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.short_s.activated.connect(self.save_image)
        self.slider_stack.valueChanged.connect(self.update_display)
        self.button_save_destination.clicked.connect(self.fill_destination)
        self.button_get_basler.clicked.connect(self.get_basler_image)
        # self.button_live_basler.clicked.connect(self.live_basler_view)
        # self.comboBox_Laser.currentTextChanged.connect(self.laser_change)
        # self.checkBox_Enabled.clicked.connect(self.laser_enable)
        # self.checkBox_Emit.clicked.connect(self.laser_emit)
        # self.button_power.clicked.connect(self.laser_power)
        self.button_live_basler.clicked.connect(self.asyncsetup)
    def update_display(self):
        """Updating display of GUI with current_image"""
        if self.image_list:
            list_image = self.image_list[self.slider_stack.value()-1]
            display_image = self.imagearray_list[self.slider_stack.value()-1]

            self.current_image = qimage2ndarray.array2qimage(display_image)
            self.current_path = p.normpath(list_image)

            current_value = str(self.slider_stack.value())
            max_value = str(len(self.image_list))
            self.status.setText("Image " + current_value + " of " + max_value)

            self.current_pixmap = QtGui.QPixmap.fromImage(self.current_image)
            self.label_image.setPixmap(self.current_pixmap)
            self.fill_save_information()

    def open_images(self):
        """Open image files and display the first"""
        [self.image_list, ext] = QtWidgets.QFileDialog.getOpenFileNames(
            self, 'Open File', filter="Images (*.bmp *.tif *.tiff *.jpg)")
        print(self.image_list)
        if self.image_list:
            inout.toArrayList(self, self.image_list)
            self.slider_stack.setMaximum(len(self.image_list))
            self.spinbox_slider.setMaximum(len(self.image_list))
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
                inout.saveImage(self, display_image, dest)
            else:
                exists = p.isfile(dest)
                if not exists:
                    inout.saveImage(self, display_image, dest)
                else:
                    count = 1
                    while exists:
                        dest = self.lineEdit_save_destination.text() + \
                               self.delim + save_base + "(" + str(count) + \
                               ").tiff"
                        exists = p.isfile(dest)
                        count = count + 1
                    inout.saveImage(self, display_image, dest)

    def fill_save_information(self):
        """Fills Save Destination and Save Filename using image path"""
        [destination, self.save_name] = p.split(self.current_path)
        if not self.checkBox_save_destination.isChecked():
            destination = destination + self.delim
            self.save_destination = destination
            self.lineEdit_save_destination.setText(self.save_destination)
        self.lineEdit_save_filename.setText(self.save_name)

    def fill_destination(self):
        """Fills the destination box with the text from the directory"""
        if not self.checkBox_save_destination.isChecked():
            self.save_destination = p.normpath(
                QtWidgets.QFileDialog.getExistingDirectory(
                    self, 'File Destination'))
            destination_text = self.save_destination + self.delim
            self.lineEdit_save_destination.setText(destination_text)

    def get_basler_image(self):
        """Grab an image from the basler and display it"""
        self.basler_raw = self.basler.camera_grab()
        self.create_basler_list()
        self.imagearray_list = self.basler_list
        self.update_display()

    def create_basler_list(self):
        self.image_list = []
        self.basler_list = []
        for n in range(0, len(self.basler_raw)):
            self.image_list.append("test" + str(n))
            self.basler_list.append(np.array(self.basler_raw[n]))

        self.slider_stack.setMaximum(len(self.image_list))
        self.spinbox_slider.setMaximum(len(self.image_list))
        self.slider_stack.setValue(1)

    def live_basler_view(self):
        for i in range(1, 100):
            self.get_basler_image()
            print("Hi" + str(i))
            time.sleep(1/15)

    async def produce(self, queue, n):
        for x in range(n):
            item = self.basler.camera_grab()
            await asyncio.sleep(4)
            print(x)
            await queue.put(item)

    async def consume(self, queue):
        while True:
            item = await queue.get()
            await asyncio.sleep(1)
            print(item)
            queue.task_done()

    async def run(self, n):
        queue = self.queue
        consumer = asyncio.ensure_future(self.consume(queue))
        await self.produce(queue, n)
        consumer.cancel()

    def asyncsetup(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.run(10))
        loop.close()

    # def laser_change(self):
    #     #     self.laser = self.comboBox_Laser.currentText().replace(" ", "")
    #     #     self.laser = self.laser.replace("L", "l")
    #     #     print(self.laser)
    #     #     onoff = "f"
    #     #     command = "(param-set! '" + self.laser + ":enable #" + onoff + ")\r"
    #     #     print(command)
    #     #     self.checkBox_Enabled.setChecked(0)
    #     #     self.checkBox_Emit.setChecked(0)
    #     #     self.checkBox_Emit.setEnabled(0)
    #     #     self.spinBox_level.setValue(0)
    #     #     self.laser_power()
    #
    # def laser_enable(self):
    #     if (self.checkBox_Enabled.isChecked() == 1):
    #         self.checkBox_Emit.setEnabled(1)
    #         onoff = "t"
    #         command = "(param-set! '" + self.laser + ":enable #" + onoff + ")\r"
    #         print(command)
    #     else:
    #         self.checkBox_Emit.setChecked(0)
    #         self.checkBox_Emit.setEnabled(0)
    #
    #         onoff = "f"
    #         command = "(param-set! '" + self.laser + ":enable #" + onoff + ")\r"
    #         print(command)
    #
    # def laser_emit(self):
    #     if (self.checkBox_Emit.isChecked() == 1):
    #         onoff = "t"
    #         command = "(param-set! '" + self.laser + ":cw #" + onoff + ")\r"
    #         print(command)
    #     else:
    #         onoff = "f"
    #         command = "(param-set! '" + self.laser + ":cw #" + onoff + ")\r"
    #         print(command)
    #
    # def laser_power(self):
    #     self.level = self.spinBox_level.value()
    #     command = "(param-set! '" + self.laser + ":level " + str(self.level) + ")\r"
    #     print(command)
    #     self.serial_write(command)
    #
    #
    # def serial_write(self, command):
    #
    #     ser = serial.Serial(port='COM15', baudrate=115200, timeout=1)
    #     ser.write(bytes(command,'utf-8'))
    #     time.sleep(3)
    #     output = ser.read(500)
    #     print(output)
    #     # time.sleep(3)
    #     # ser.write(bytes("(param-disp 'laser1)",'utf-8'))
    #     # time.sleep(3)
    #     # output = ser.read(500)
    #     # print(output)
    #     ser.close()
    #


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()
