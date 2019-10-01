from PyQt5 import QtWidgets, QtGui, QtCore
import piescope_gui.gui_interaction as interface
import piescope_gui.qtdesigner_files.main as gui_main
import piescope_gui.piescope_interaction as inout
import piescope.lm.volume as volume
import os.path as p
import piescope_gui.correlation.main as correlate


DEFAULT_PATH = "C:\\Users\\Admin\\Pictures\\Basler"


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("PIEScope User Interface")
        self.statusbar.setSizeGripEnabled(0)
        self.status = QtWidgets.QLabel(self.statusbar)
        self.status.setAlignment(QtCore.Qt.AlignRight)

        self.statusbar.addPermanentWidget(self.status, 1)
        self.lineEdit_save_destination_FM.setText(DEFAULT_PATH)
        self.checkBox_save_destination_FM.setChecked(1)
        self.lineEdit_save_filename_FM.setText("Image")
        self.lineEdit_save_destination_FIBSEM.setText(DEFAULT_PATH)
        self.checkBox_save_destination_FIBSEM.setChecked(1)
        self.lineEdit_save_filename_FIBSEM.setText("Image")

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

        self.pushButton_volume.clicked.connect(self.acquire_volume)

        self.button_get_image_FM.clicked.connect(self.get_basler_image)

        self.button_live_image_FM.clicked.connect(self.basler_live_image)

        self.pushButton_move_absolute.clicked.connect(self.current_position)

        self.pushButton_move_relative.clicked.connect(self.move_relative)

        self.pushButton_initialise_stage.clicked.connect(self.initialise_stage)

        self.pushButton_correlation.clicked.connect(self.correlateim)

    def acquire_volume(self):
        exposure_time = self.lineEdit_exposure.text()
        laser_dict = self.laser_dict
        no_z_slices = self.lineEdit_slice_number.text()
        z_slice_distance = self.lineEdit_slice_distance.text()
        volume.volume_acquisition(self, exposure_time, laser_dict,
                                  no_z_slices, z_slice_distance)

    def live_imaging_event_listener(self, stop_event):
        state = True
        while state and not stop_event.isSet():
            self.get_basler_image()

    def get_basler_image(self):
        try:
            inout.get_basler_image(self)
        except:
            print('Could not grab basler image')
            return

    def basler_live_image(self):
        try:
            inout.basler_live_imaging(self)
        except:
            print('Live imaging failed')
            return

    def open_images(self, modality):
        interface.open_images(self, modality)

    def save_image(self, modality):
        try:
            interface.save_image(self, modality)
        except:
            print('Could not save image')
            return

    def update_display(self, modality):
        interface.update_display(self, modality)

    def fill_save_information(self, modality):
        interface.fill_save_information(self, modality)

    def fill_destination(self):
        interface.fill_destination(self)

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

    def correlateim(self):
        input_filename_1 = "C:\\Users\\David\\images\\worm_fluorescence-microscopy.tif"
        input_filename_2 = "C:\\Users\\David\\images\\worm_ion-beam-microscopy-tilted.tif"
        output_filename = "C:\\Users\\David\\images\\output.tiff" #"C:\\Users\\David Dierickx\\Pictures\\output.tiff"
        correlate.open_correlation_window(self, input_filename_1, input_filename_2, output_filename)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()
