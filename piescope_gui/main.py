from PyQt5 import QtWidgets, QtGui, QtCore
import piescope_gui.interface.main as interface
import piescope_gui.designer.main as gui_main
import piescope_gui.inputoutput.main as inout
import piescope.lm.volume as volume
import os.path as p


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("PIEScope User Interface")
        self.statusbar.setSizeGripEnabled(0)
        self.status = QtWidgets.QLabel(self.statusbar)
        self.status.setAlignment(QtCore.Qt.AlignRight)
        self.statusbar.addPermanentWidget(self.status, 1)

        self.save_name = ""
        self.power1 = 0
        self.power2 = 0
        self.power3 = 0
        self.power4 = 0
        self.liveCheck = True
        self.array_list = []
        self.laser_dict = {}
        self.string_list = []
        self.current_path = ""
        self.current_image = ""
        self.current_pixmap = []
        self.save_destination = ""
        self.delim = p.normpath("/")

        self.actionOpen.triggered.connect(self.open_images)
        self.actionSave.triggered.connect(self.save_image)
        self.slider_stack.valueChanged.connect(self.update_display)
        self.button_save_destination.clicked.connect(self.fill_destination)

        self.short_o = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        self.short_o.activated.connect(self.open_images)
        self.short_s = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.short_s.activated.connect(self.save_image)

        self.slider_laser1.valueChanged.connect(lambda:
                                             self.update_laser_dict("laser1"))
        self.slider_laser2.valueChanged.connect(lambda:
                                             self.update_laser_dict("laser2"))
        self.slider_laser3.valueChanged.connect(lambda:
                                             self.update_laser_dict("laser3"))
        self.slider_laser4.valueChanged.connect(lambda:
                                             self.update_laser_dict("laser4"))

        self.checkBox_laser1.clicked.connect(lambda:
                                             self.update_laser_dict("laser1"))
        self.checkBox_laser2.clicked.connect(lambda:
                                             self.update_laser_dict("laser2"))
        self.checkBox_laser3.clicked.connect(lambda:
                                             self.update_laser_dict("laser3"))
        self.checkBox_laser4.clicked.connect(lambda:
                                             self.update_laser_dict("laser4"))

        self.pushButton_volume.clicked.connect(self.acquire_volume)

        self.button_get_basler.clicked.connect(self.get_basler_image)

        self.button_live_basler.clicked.connect(self.basler_live_image)

        self.pushButton_initialise_stage.connect(self.initialise_stage)

    def acquire_volume(self):
        exposure_time = self.lineEdit_exposure.text()
        laser_dict = self.laser_dict
        no_z_slices = self.lineEdit_slice_number.text()
        z_slice_distance = self.lineEdit_slice_distance.text()
        volume.volume_acquisition(exposure_time, laser_dict,
                                  no_z_slices, z_slice_distance)

    def live_imaging_event_listener(self, stop_event):
        state = True
        while state and not stop_event.isSet():
            self.get_basler_image()

    def get_basler_image(self):
        inout.get_basler_image(self)

    def basler_live_image(self):
        inout.live_imaging(self)

    def open_images(self):
        interface.open_images(self)

    def save_image(self):
        interface.save_image(self)

    def update_display(self):
        interface.update_display(self)

    def fill_save_information(self):
        interface.fill_save_information(self)

    def fill_destination(self):
        interface.fill_destination(self)

    def update_laser_dict(self, laser):
        inout.update_laser_dict(self, laser)

    def initialise_stage(self):
        inout.initialise_stage(self)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()
