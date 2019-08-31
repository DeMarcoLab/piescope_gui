from PyQt5 import QtWidgets, QtGui, QtCore
import piescope_gui.interface.main as interface
import piescope_gui.designer.main as gui_main
import piescope_gui.inputoutput.main as inout
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
        self.laser_list = []
        self.power_list = []
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

        self.slider_laser1.valueChanged.connect(self.update_laser_power_1)
        self.slider_laser2.valueChanged.connect(self.update_laser_power_2)
        self.slider_laser3.valueChanged.connect(self.update_laser_power_3)
        self.slider_laser4.valueChanged.connect(self.update_laser_power_4)

        self.checkBox_laser1.clicked.connect(self.update_laser_list_1)
        self.checkBox_laser2.clicked.connect(self.update_laser_list_2)
        self.checkBox_laser3.clicked.connect(self.update_laser_list_3)
        self.checkBox_laser4.clicked.connect(self.update_laser_list_4)

        # self.pushButton_volume.clicked.connect(self.acquire_volume)

        self.short_o = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        self.short_o.activated.connect(self.open_images)
        self.short_s = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.short_s.activated.connect(self.save_image)

        self.button_get_basler.clicked.connect(self.get_basler_image)

        self.button_live_basler.clicked.connect(self.basler_live_image)

    # need to import piescope and ensure all 3 parts are working together before implementing this
    # def acquire_volume(self):
        # Write tests/error checking
        # piescope.volume(params)

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

    def update_laser_list_1(self):
        inout.update_laser_list_1(self)

    def update_laser_list_2(self):
        inout.update_laser_list_2(self)

    def update_laser_list_3(self):
        inout.update_laser_list_3(self)

    def update_laser_list_4(self):
        inout.update_laser_list_4(self)

    def update_laser_power_1(self):
        inout.update_laser_power_1(self)

    def update_laser_power_2(self):
        inout.update_laser_power_2(self)

    def update_laser_power_3(self):
        inout.update_laser_power_3(self)

    def update_laser_power_4(self):
        inout.update_laser_power_4(self)
        

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()
