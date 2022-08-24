import logging
import os
import sys
import threading
import time
import traceback

import numpy as np
import piescope
import piescope.fibsem
import piescope.lm
import piescope.utils
import scipy.ndimage as ndi
from fibsem import acquire, conversions, movement
from fibsem import utils as fibsem_utils
from fibsem.structures import BeamType
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as _FigureCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as _NavigationToolbar
from piescope.lm import arduino, mirror, structured
from piescope.lm.detector import Basler, Hamamatsu
from piescope.lm.laser import Laser, LaserController
from piescope.lm.mirror import ImagingType, MirrorPosition
from piescope.utils import Modality, TriggerMode
from PyQt5 import QtCore, QtGui, QtWidgets

import piescope_gui.correlation.main as corr
import piescope_gui.milling
import piescope_gui.qtdesigner_files.main as gui_main
from piescope_gui.utils import display_error_message, timestamp

# TODO: (NOT YET) add serial connection checks (if needed)
# TODO: (NOT YET) Move objective forward/back with scroll wheel

MS_TO_US = 1000.0
US_TO_MS = 1 / MS_TO_US

class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    window_close = QtCore.pyqtSignal()
    def __init__(self, parent_gui=None):
        super().__init__(parent=parent_gui)
        self.setupUi(MainGui=self)
        self.setStyleSheet("""QPushButton {
        border: 1px solid #e3e3e3;
        border-radius: 5px;
        background-color: #e3e3e3;
        }""")
        self.lock = threading.Lock()
        self.read_config_file()
        self.setup_logging()
        self.setup_initial_values()
        self.initialise_image_frames()
        self.initialise_hardware()
        self.setup_connections()
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

    ## Initialisation functions ##
    def read_config_file(self):
        # read config file
        self.config_path = os.path.join(
            os.path.dirname(piescope.__file__), "config.yml")
        self.config = piescope.utils.read_config(self.config_path)


        self.settings = fibsem_utils.load_settings_from_config()


        # set ip_address and online status
        # self.ip_address = self.config["system"]["ip_address"]
        self.online = self.config["system"]["online"]
        self.trigger_mode = self.config["imaging"]["lm"]["trigger_mode"]

        # imaging settings
        self.filter_strength_lm = self.config["imaging"]["lm"]["filter_strength"]
        self.filter_strength_ib = self.config["imaging"]["ib"]["filter_strength"]

        self.magnification_lm = self.config["imaging"]["lm"]["camera"]["objective_mag"] * self.config["imaging"]["lm"]["camera"]["telescope_mag"]
        self.pixel_size_lm = self.config["imaging"]["lm"]["camera"]["pixel_size"]  / self.magnification_lm


    def setup_logging(self):
        start_time = piescope_gui.utils.timestamp()
        self.logging_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "log", start_time
        )
        if not os.path.isdir(self.logging_path):
            os.makedirs(self.logging_path)

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        formatter = logging.Formatter(" %(asctime)s %(levelname)s %(message)s")

        # set handler formatting and levels
        file_handler = logging.FileHandler(f"{self.logging_path}/log.log")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level=logging.INFO)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        if self.online:
            stream_handler.setLevel(level=logging.INFO)
        else:
            stream_handler.setLevel(level=logging.DEBUG)

        # add the handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def setup_initial_values(self):
        self.live_imaging_running = False
        self.image_light = None
        self.image_ion = None
        self.milling_position = None

        # threading event used to start/stop live imaging
        self.stop_event = None

        self.lineEdit_save_filename_FM.setText("Fluorescence Image")
        self.lineEdit_save_filename_FIBSEM.setText("FIBSEM Image")
        self.correlation_output_name.setText("Correlation Image")
        self.label_objective_stage_position.setText("Unknown")

        self.save_destination_FM = self.logging_path
        self.save_destination_FIBSEM = self.logging_path
        self.save_destination_correlation = self.logging_path
        self.lineEdit_save_destination_FM.setText(self.logging_path)
        self.lineEdit_save_destination_FIBSEM.setText(self.logging_path)
        self.correlation_output_path.setText(self.logging_path)

        self.comboBox_resolution.setCurrentIndex(1)  # resolution "1536x1024"

    def initialise_image_frames(self):
        self.figure_FM = plt.figure(figsize=(4, 1))
        plt.axis("off")
        plt.tight_layout()
        plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.01)
        self.canvas_FM = _FigureCanvas(self.figure_FM)
        self.toolbar_FM = _NavigationToolbar(self.canvas_FM, self)
        self.canvas_FM.mpl_connect(
            "button_press_event",
            lambda event: self.on_gui_click(event, modality=Modality.Light),
        )
        self.ax_FM = None
        self.label_image_FM.setLayout(QtWidgets.QVBoxLayout())
        self.label_image_FM.layout().addWidget(self.toolbar_FM)
        self.label_image_FM.layout().addWidget(self.canvas_FM)

        self.figure_FIBSEM = plt.figure()
        plt.axis("off")
        plt.tight_layout()
        plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.01)
        self.canvas_FIBSEM = _FigureCanvas(self.figure_FIBSEM)
        # self.toolbar_FIBSEM = _NavigationToolbar(self.canvas_FIBSEM, self)
        self.current_click_event_id = None

        self.label_image_FIBSEM.setLayout(QtWidgets.QVBoxLayout())
        # self.label_image_FIBSEM.layout().addWidget(self.toolbar_FIBSEM)
        self.label_image_FIBSEM.layout().addWidget(self.canvas_FIBSEM)

        self.figure_histogram = plt.figure()
        # plt.axis("off")
        # plt.tight_layout()
        # plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.01)
        self.canvas_histogram = _FigureCanvas(self.figure_histogram)

        self.label_histogram.setLayout(QtWidgets.QVBoxLayout())
        self.label_histogram.layout().addWidget(self.canvas_histogram)


    def initialise_hardware(self):
        self.microscope = None
        self.detector = None
        self.laser_controller = None
        self.objective_stage = None
        self.mirror_controller = None
        self.arduino = None

        if self.online:
            self.connect_to_fibsem_microscope()
            self.connect_to_light_detector()
            self.connect_to_laser_controller()
            self.connect_to_objective_controller()
            self.connect_to_mirror_controller()
            self.connect_to_arduino()
            self.update_connections()

    def setup_connections(self):
        self.actionOpen_FM_Image.triggered.connect(
            lambda: self.open_images(modality=Modality.Light))
        self.actionOpen_FIBSEM_Image.triggered.connect(
            lambda: self.open_images(modality=Modality.Ion))
        self.actionSave_FM_Image.triggered.connect(
            lambda: self.save_image(modality=Modality.Light))
        self.actionSave_FIBSEM_Image.triggered.connect(
            lambda: self.save_image(modality=Modality.Ion))
        self.button_save_destination_FM.clicked.connect(
            lambda: self.fill_destination(mode="FM"))
        self.button_save_destination_FIBSEM.clicked.connect(
            lambda: self.fill_destination(mode="FIBSEM"))
        self.toolButton_correlation_output.clicked.connect(
            lambda: self.fill_destination(mode="correlation"))
        self.pushButton_save_FM.clicked.connect(
            lambda: self.save_image(modality=Modality.Light))
        self.pushButton_save_FIBSEM.clicked.connect(
            lambda: self.save_image(modality=Modality.Ion))
        self.pushButton_load_FM.clicked.connect(
            lambda: self.open_images(Modality.Light))
        self.pushButton_load_FIBSEM.clicked.connect(
            lambda: self.open_images(Modality.Ion))
        self.comboBox_cmap.currentTextChanged.connect(
            lambda: self.update_display(modality=Modality.Light))

        if not self.online:
            return
        self.pushButton_connect_objective.clicked.connect(
            self.connect_to_objective_controller)
        self.pushButton_connect_detector.clicked.connect(
            self.connect_to_light_detector)
        self.pushButton_connect_microscope.clicked.connect(
            self.connect_to_fibsem_microscope)
        self.pushButton_connect_laser_controller.clicked.connect(
            self.connect_to_laser_controller)
        self.pushButton_connect_mirror_controller.clicked.connect(
            self.connect_to_mirror_controller)
        self.pushButton_connect_arduino.clicked.connect(
            self.connect_to_arduino)

        self.pushButton_connect_objective.clicked.connect(
            self.update_connections)
        self.pushButton_connect_detector.clicked.connect(
            self.update_connections)
        self.pushButton_connect_microscope.clicked.connect(
            self.update_connections)
        self.pushButton_connect_laser_controller.clicked.connect(
            self.update_connections)
        self.pushButton_connect_mirror_controller.clicked.connect(
            self.update_connections)
        self.pushButton_connect_arduino.clicked.connect(
            self.update_connections)

    ## Update functions ##
    def update_connections(self):
        self.update_microscope_connections()
        self.update_laser_connections()
        self.update_objective_connections()
        self.update_mirror_connections()
        self.update_connection_button_ui()

    def update_mirror_connections(self):
        if not self.online or not self.mirror_controller:
            return
        if self.comboBox_imaging_type.isEnabled():
            return

        self.comboBox_imaging_type.setEnabled(True)
        self.update_imaging_type()

        self.comboBox_imaging_type.currentTextChanged.connect(
            lambda: self.update_imaging_type(mode=self.comboBox_imaging_type.currentText()))
        self.comboBox_pattern.currentTextChanged.connect(
            lambda: self.update_pattern_position(pattern=self.comboBox_pattern.currentText(), phase=self.comboBox_phase.currentText()))
        self.comboBox_phase.currentTextChanged.connect(
            lambda: self.update_pattern_position(pattern=self.comboBox_pattern.currentText(), phase=self.comboBox_phase.currentText()))

    def update_pattern_position(self, pattern='0 deg', phase='0 deg'):
        """Move to the selected mirror stage angle"""

        position = pattern + ' ' + phase

        mirror_stage_positions = {
            "0 deg 0 deg": MirrorPosition.HORIZONTAL,
            "0 deg 120 deg": MirrorPosition.HORIZONTAL_120,
            "0 deg 240 deg": MirrorPosition.HORIZONTAL_240,
            "60 deg 0 deg": MirrorPosition.SIXTY,
            "60 deg 120 deg": MirrorPosition.SIXTY_120,
            "60 deg 240 deg": MirrorPosition.SIXTY_240,
            "120 deg 0 deg": MirrorPosition.ONETWENTY,
            "120 deg 120 deg": MirrorPosition.ONETWENTY_120,
            "120 deg 240 deg": MirrorPosition.ONETWENTY_240,
        }

        self.mirror_controller.move_to(
            mirror_position=mirror_stage_positions[position])
        return

    def update_imaging_type(self, mode='Widefield'):
        if mode == 'Widefield':
            self.mirror_controller.set_mode(ImagingType.WIDEFIELD)
            self.mirror_controller.move_to(MirrorPosition.WIDEFIELD)
            self.comboBox_pattern.setEnabled(False)
            self.comboBox_phase.setEnabled(False)
            return
        if mode == 'SIM':
            self.mirror_controller.set_mode(ImagingType.SIM)

            self.comboBox_pattern.setEnabled(True)
            self.comboBox_phase.setEnabled(True)

            pattern = self.comboBox_pattern.currentText()
            phase = self.comboBox_phase.currentText()

            position = pattern + ' ' + phase

            mirror_stage_positions = {
            "0 deg 0 deg": MirrorPosition.HORIZONTAL,
            "0 deg 120 deg": MirrorPosition.HORIZONTAL_120,
            "0 deg 240 deg": MirrorPosition.HORIZONTAL_240,
            "60 deg 0 deg": MirrorPosition.SIXTY,
            "60 deg 120 deg": MirrorPosition.SIXTY_120,
            "60 deg 240 deg": MirrorPosition.SIXTY_240,
            "120 deg 0 deg": MirrorPosition.ONETWENTY,
            "120 deg 120 deg": MirrorPosition.ONETWENTY_120,
            "120 deg 240 deg": MirrorPosition.ONETWENTY_240,
            }

            self.mirror_controller.move_to(
                mirror_position=mirror_stage_positions[position])
            return

    def update_microscope_connections(self):
        if not self.online or not self.microscope:
            return
        if self.comboBox_resolution.isEnabled():
            return
        self.comboBox_resolution.setEnabled(True)
        self.lineEdit_dwell_time.setEnabled(True)
        self.button_get_image_FIB.setEnabled(True)
        self.button_get_image_SEM.setEnabled(True)
        self.button_last_image_FIB.setEnabled(True)
        self.button_last_image_SEM.setEnabled(True)
        self.checkBox_Autocontrast.setEnabled(True)
        self.pushButton_stage_movement.setEnabled(True)

        self.comboBox_resolution.currentTextChanged.connect(
            lambda: self.update_image_settings())
        self.lineEdit_dwell_time.textChanged.connect(
            lambda: self.update_image_settings())
        self.button_get_image_FIB.clicked.connect(
            lambda: self.get_image(BeamType.ION, save=True))
        self.button_get_image_SEM.clicked.connect(
            lambda: self.get_image(BeamType.ELECTRON, save=True))
        self.button_last_image_FIB.clicked.connect(
            lambda: self.get_last_image(BeamType.ION))
        self.button_last_image_SEM.clicked.connect(
            lambda: self.get_last_image(BeamType.ELECTRON))
        self.pushButton_stage_movement.clicked.connect(self.move_to_microscope)

    def update_laser_connections(self):
        # all subsequent connections require the laser controller
        if not self.online or not self.laser_controller:
            return
        # update laser only connections if not already enabled
        if not self.checkBox_laser1.isEnabled():
            self.checkBox_laser1.setEnabled(True)
            self.checkBox_laser2.setEnabled(True)
            self.checkBox_laser3.setEnabled(True)
            self.checkBox_laser4.setEnabled(True)
            self.doubleSpinBox_laser1.setEnabled(True)
            self.doubleSpinBox_laser2.setEnabled(True)
            self.doubleSpinBox_laser3.setEnabled(True)
            self.doubleSpinBox_laser4.setEnabled(True)
            self.lineEdit_exposure_1.setEnabled(True)
            self.lineEdit_exposure_2.setEnabled(True)
            self.lineEdit_exposure_3.setEnabled(True)
            self.lineEdit_exposure_4.setEnabled(True)
            self.comboBox_wavelength.setEnabled(True)
            self.pushButton_correlation.setEnabled(True)

            self.checkBox_laser1.clicked.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser640"]))
            self.checkBox_laser2.clicked.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser561"]))
            self.checkBox_laser3.clicked.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser488"]))
            self.checkBox_laser4.clicked.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser405"]))
            self.doubleSpinBox_laser1.valueChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser640"]))
            self.doubleSpinBox_laser2.valueChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser561"]))
            self.doubleSpinBox_laser3.valueChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser488"]))
            self.doubleSpinBox_laser4.valueChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser405"]))
            self.lineEdit_exposure_1.textChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser640"]))
            self.lineEdit_exposure_2.textChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser561"]))
            self.lineEdit_exposure_3.textChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser488"]))
            self.lineEdit_exposure_4.textChanged.connect(
                lambda: self.update_lasers(self.laser_controller.lasers["laser405"]))
            self.comboBox_wavelength.currentTextChanged.connect(
                lambda: self.update_current_laser(wavelength=self.comboBox_wavelength.currentText()))
            self.pushButton_correlation.clicked.connect(
                lambda: self.correlateim())

            self.comboBox_wavelength.setCurrentText(
                str(self.laser_controller.current_laser.wavelength) + ' nm')

        # FM imaging requires connection to laser controller and detector
        if self.button_get_image_FM.isEnabled() or not self.detector:
            return

        self.button_get_image_FM.setEnabled(True)
        self.button_live_image_FM.setEnabled(True)
        self.comboBox_cmap.setEnabled(True)

        self.button_get_image_FM.clicked.connect(
            lambda: self.fluorescence_image(
                laser=self.laser_controller.current_laser,
                settings=self.config,))
        self.button_live_image_FM.clicked.connect(
            lambda: self.fluorescence_live_imaging(
                self.laser_controller.current_laser,))

        # Volume imaging requires laser controller, detector and objective
        if not self.objective_stage:
            return
        self.pushButton_volume.setEnabled(True)
        self.pushButton_volume.clicked.connect(
            lambda: self.acquire_volume())

    def update_objective_connections(self):
        if not self.online or not self.objective_stage:
            return
        if self.pushButton_move_absolute.isEnabled():
            return

        self.pushButton_move_absolute.setEnabled(True)
        self.pushButton_move_relative.setEnabled(True)
        self.toolButton_negative.setEnabled(True)
        self.toolButton_positive.setEnabled(True)
        self.pushButton_get_position.setEnabled(True)
        self.pushButton_save_objective_position.setEnabled(True)
        self.pushButton_go_to_saved_position.setEnabled(True)
        self.lineEdit_move_absolute.setEnabled(True)
        self.lineEdit_move_relative.setEnabled(True)

        self.pushButton_move_absolute.clicked.connect(
            lambda: self.move_absolute_objective_stage(
                self.objective_stage,
                self.lineEdit_move_absolute.text()))
        self.pushButton_move_relative.clicked.connect(
            lambda: self.move_relative_objective_stage(
                self.objective_stage,
                self.lineEdit_move_relative.text()))
        self.toolButton_negative.clicked.connect(
            lambda: self.move_relative_objective_stage(
                self.objective_stage,
                self.lineEdit_move_relative.text(),
                direction="negative",))
        self.toolButton_positive.clicked.connect(
            lambda: self.move_relative_objective_stage(
                self.objective_stage,
                self.lineEdit_move_relative.text(),
                direction="positive",))
        self.pushButton_get_position.clicked.connect(
            self.objective_stage_position)
        self.pushButton_save_objective_position.clicked.connect(
            self.save_objective_stage_position)
        self.pushButton_go_to_saved_position.clicked.connect(
            lambda: self.move_absolute_objective_stage(
                self.objective_stage))

    def update_image_settings(self):
        if not self.microscope and self.online:
            self.connect_to_fibsem_microscope()
        try:

            # update image settings       
            self.settings.image.resolution = self.comboBox_resolution.currentText()
            self.settings.image.dwell_time = float(self.lineEdit_dwell_time.text()) * 1.0e-6
            self.settings.image.autocontrast=self.checkBox_Autocontrast.isChecked(),
            self.settings.image.gamma.enabled = False
            self.settings.image.save=bool(self.config['imaging']['ib']['autosave'])
            self.settings.image.save_path=self.save_destination_FIBSEM
            self.settings.image.label=str(self.lineEdit_save_filename_FIBSEM.text())

        except Exception as e:
            display_error_message(f"Unable to update image settings: {e}")

    ## Connection functions ##
    def connect_to_arduino(self):
        if self.arduino is not None:
            return
        try:
            self.arduino = arduino.Arduino()
        except:
            display_error_message(
                f"Unable to connect to Arduino. <br><br>{traceback.format_exc()}"
            )

    def connect_to_mirror_controller(self):
        if self.mirror_controller is not None:
            return
        try:
            self.mirror_controller = mirror.PIController()
        except:
            display_error_message(
                f"Unable to connect to mirror controller. <br><br>{traceback.format_exc()}"
            )

    def connect_to_objective_controller(self):
        if self.objective_stage is not None:
            return
        try:
            self.objective_stage = piescope.lm.objective.StageController(
                testing=False)
            self.objective_stage.initialise_system_parameters()
            try:
                structured.single_line_onoff(
                    onoff=False, pin=self.config["lm_objective"]["pin"]
                )
            except:
                display_error_message(
                    f"Unable to connect to niqadmx device. <br><br>{traceback.format_exc()}"
                )
        except:
            display_error_message(
                f"Unable to connect to lm objective controller. <br><br>{traceback.format_exc()}"
            )

    def connect_to_laser_controller(self):
        if self.laser_controller is not None:
            return
        try:
            self.laser_controller = LaserController(settings=self.config)

            # connect laser ui elements (spinbox, lineedit, checkbox) -> (power, exposure_time, volume_enabled)
            self.laser_controller.set_double_spin_box(laser=self.laser_controller.lasers['laser640'], spinBox=self.doubleSpinBox_laser1)
            self.laser_controller.set_double_spin_box(laser=self.laser_controller.lasers['laser561'], spinBox=self.doubleSpinBox_laser2)
            self.laser_controller.set_double_spin_box(laser=self.laser_controller.lasers['laser488'], spinBox=self.doubleSpinBox_laser3)
            self.laser_controller.set_double_spin_box(laser=self.laser_controller.lasers['laser405'], spinBox=self.doubleSpinBox_laser4)

            self.laser_controller.set_line_edit(laser=self.laser_controller.lasers['laser640'], lineEdit=self.lineEdit_exposure_1)
            self.laser_controller.set_line_edit(laser=self.laser_controller.lasers['laser561'], lineEdit=self.lineEdit_exposure_2)
            self.laser_controller.set_line_edit(laser=self.laser_controller.lasers['laser488'], lineEdit=self.lineEdit_exposure_3)
            self.laser_controller.set_line_edit(laser=self.laser_controller.lasers['laser405'], lineEdit=self.lineEdit_exposure_4)

            self.laser_controller.set_check_box(laser=self.laser_controller.lasers['laser640'], checkBox=self.checkBox_laser1)
            self.laser_controller.set_check_box(laser=self.laser_controller.lasers['laser561'], checkBox=self.checkBox_laser2)
            self.laser_controller.set_check_box(laser=self.laser_controller.lasers['laser488'], checkBox=self.checkBox_laser3)
            self.laser_controller.set_check_box(laser=self.laser_controller.lasers['laser405'], checkBox=self.checkBox_laser4)

            self.doubleSpinBox_laser1.setValue(
                self.laser_controller.lasers["laser640"].power)
            self.doubleSpinBox_laser2.setValue(
                self.laser_controller.lasers["laser561"].power)
            self.doubleSpinBox_laser3.setValue(
                self.laser_controller.lasers["laser488"].power)
            self.doubleSpinBox_laser4.setValue(
                self.laser_controller.lasers["laser405"].power)
            self.lineEdit_exposure_1.setText(
                str(self.laser_controller.lasers["laser640"].exposure_time))
            self.lineEdit_exposure_2.setText(
                str(self.laser_controller.lasers["laser561"].exposure_time))
            self.lineEdit_exposure_3.setText(
                str(self.laser_controller.lasers["laser488"].exposure_time))
            self.lineEdit_exposure_4.setText(
                str(self.laser_controller.lasers["laser405"].exposure_time))
            self.checkBox_laser1.setChecked(
                self.laser_controller.lasers["laser640"].volume_enabled)
            self.checkBox_laser2.setChecked(
                self.laser_controller.lasers["laser561"].volume_enabled)
            self.checkBox_laser3.setChecked(
                self.laser_controller.lasers["laser488"].volume_enabled)
            self.checkBox_laser4.setChecked(
                self.laser_controller.lasers["laser405"].volume_enabled)

            self.update_lasers(self.laser_controller.lasers["laser640"])
            self.update_lasers(self.laser_controller.lasers["laser561"])
            self.update_lasers(self.laser_controller.lasers["laser488"])
            self.update_lasers(self.laser_controller.lasers["laser405"])

            try:
                for laser in self.laser_controller.lasers.values():
                    structured.single_line_onoff(onoff=False, pin=laser.pin)
            except:
                display_error_message(
                    f"Unable to connect to niqadmx device. <br><br>{traceback.format_exc()}"
                )
        except:
            display_error_message(
                f"Unable to connect to laser controller. <br><br>{traceback.format_exc()}"
            )

    def connect_to_light_detector(self):
        if self.detector is not None:
            return
        try:
            #TODO: make this a self.config[] thing
            basler = False
            if basler:
                self.detector = Basler(settings=self.config)
            else:
                self.detector = Hamamatsu(settings=self.config)
        except Exception as e:
            display_error_message(
                f"Unable to connect to light detector. <br><br>{e}"
            )

    def connect_to_fibsem_microscope(self):
        if self.microscope is not None:
            return
        """Connect to the FIBSEM microscope."""
        try:
            self.microscope = fibsem_utils.connect_to_microscope(self.settings.system.ip_address)
        except Exception as e:
            display_error_message(
                f"Unable to connect to the FIB-SEM Microscope. <br><br>{e}"
            )

    def update_connection_button_ui(self):
        """ Change the color of the hardware connection buttons when they are connection"""

        if self.microscope:
            self.pushButton_connect_microscope.setStyleSheet(
                "background-color: lightgreen")
        else:
            self.pushButton_connect_microscope.setStyleSheet(
                "background-color: #e3e3e3")

        if self.detector:
            self.pushButton_connect_detector.setStyleSheet(
                "background-color: lightgreen")
        else:
            self.pushButton_connect_detector.setStyleSheet(
                "background-color: #e3e3e3")

        if self.objective_stage:
            self.pushButton_connect_objective.setStyleSheet(
                "background-color: lightgreen")
        else:
            self.pushButton_connect_objective.setStyleSheet(
                "background-color: #e3e3e3")

        if self.mirror_controller:
            self.pushButton_connect_mirror_controller.setStyleSheet(
                "background-color: lightgreen")
        else:
            self.pushButton_connect_mirror_controller.setStyleSheet(
                "background-color: #e3e3e3")

        if self.laser_controller:
            self.pushButton_connect_laser_controller.setStyleSheet(
                "background-color: lightgreen")
        else:
            self.pushButton_connect_laser_controller.setStyleSheet(
                "background-color: #e3e3e3")

        if self.arduino:
            self.pushButton_connect_arduino.setStyleSheet(
                "background-color: lightgreen")
        else:
            self.pushButton_connect_arduino.setStyleSheet(
                "background-color: #e3e3e3")

    def disconnect(self):
        logging.info("Running cleanup/teardown")
        logging.debug("Running cleanup/teardown")
        # Change values in qtdesigner_files\main.py
        if self.objective_stage is not None and self.online:
            # Return objective lens stage to the "out" position and disconnect.
            self.move_absolute_objective_stage(
                self.objective_stage, position=-1000)
            self.objective_stage.disconnect()
        if self.microscope is not None:
            self.microscope.disconnect()

        if self.laser_controller:
            # shut off lasers
            logging.info("shutting off lasers")
            try:
                for laser in self.laser_controller.lasers.values():
                    structured.single_line_onoff(onoff=False, pin=laser.pin)
            except:
                display_error_message(
                    f"Unable to connect to niqadmx device. <br><br>{traceback.format_exc()}"
                )
            if self.stop_event:
                logging.info("Stopping Live Imaging")
                self.stop_event.set()
                logging.info("Thread stopped")
        # edit config
        if self.config['system']['save_config_on_exit']:
            piescope.utils.write_config(self.config_path, self.config)
        logging.info("Disconnect finished. Shutting Down.")

    def move_to_microscope(self):
        try:
            piescope.fibsem.move_to_microscope(
                self.microscope, settings=self.config)
        except:
            display_error_message(
                f"Unable to move, please recentre the stage in one of the views: <br><br>{traceback.format_exc()}")

    def move_absolute_objective_stage(
        self, stage, position="", time_delay=0.3, testing=False
    ):
        if position == "":
            position = self.label_objective_stage_saved_position.text()
            if position == "":
                display_error_message(
                    "Please provide user input to 'Move absolute' for the "
                    "objective stage (an empty string was received)."
                )
                return
        try:
            position = int(float(position) * 1000)
        except ValueError:
            display_error_message(
                "Please provide a number as user input to 'Move relative' "
                "for the objective stage (the string could not be converted)."
            )
            return
        try:
            self.logger.debug(
                "Absolute move the objective stage to position " "{}".format(
                    position)
            )
            ans = stage.move_absolute(position)
            time.sleep(time_delay)
            new_position = stage.current_position()
            self.logger.debug(
                "After absolute move, objective stage is now at "
                "position: {}".format(new_position)
            )
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            self.label_objective_stage_position.setText(
                str(float(new_position) / 1000))
            return new_position

    def move_relative_objective_stage(
        self, stage, distance="", time_delay=0.3, direction="positive"
    ):
        if distance == "":
            distance = self.lineEdit_move_relative.text()
            if distance == "":
                display_error_message(
                    "Please provide user input to 'Move relative' for the "
                    "objective stage (an empty string was received)."
                )
                return
        try:
            distance = int(float(distance) * 1000)
        except ValueError:
            display_error_message(
                "Please provide a number as user input to 'Move relative' "
                "for the objective stage (the string could not be converted)."
            )
            return
        if direction == "positive":
            distance = abs(distance)
        elif direction == "negative":
            distance = -abs(distance)

        try:
            with self.lock:
                self.logger.debug(
                    "Relative move the objective stage by " "{}".format(distance)
                )
                ans = stage.move_relative(distance) # objective stage
                time.sleep(time_delay)
                new_position = stage.current_position()
                self.logger.debug(
                    "After relative move, objective stage is now at "
                    "position: {}".format(new_position)
                )
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            self.label_objective_stage_position.setText(
                str(float(new_position) / 1000))
            return new_position

    def get_image(self, beam_type: BeamType, save: bool = False):
        try:
            
            self.update_image_settings()
            self.settings.image.save = save
            self.settings.image.beam_type = beam_type
            self.image_ion = acquire.new_image(self.microscope, self.settings.image)

            # Update display
            modality = Modality.Ion if BeamType is BeamType.ION else Modality.Electron
            self.update_display(modality=modality)

        except Exception as e:
            display_error_message(f"Unable to get {beam_type} image: {e}")

    def get_last_image(self, beam_type: BeamType):
        try:
            self.image_ion = acquire.last_image(self.microscope, beam_type)
            modality = Modality.Ion if beam_type is BeamType.ION else Modality.Electron
            self.update_display(modality=modality)
        except Exception as e:
            display_error_message(f"Unable to get last image: {e}")

    def fluorescence_image(
        self, laser: Laser, settings: dict,
    ):
        if self.laser_controller is None:
            display_error_message("Not connect to lasers")
            return

        # check if live imaging is possible
        if self.live_imaging_running:
            self.button_live_image_FM.setDown(True)
            logging.info("Can't take image, live imaging currently running")
            return

        # manually turn on laser if software mode
        if settings["imaging"]["lm"]["trigger_mode"] == TriggerMode.Software:
            self.laser_controller.emission_on(laser)

        image = self.detector.camera_grab(laser=laser, settings=settings)

        # manually turn off laser if software mode
        if settings["imaging"]["lm"]["trigger_mode"] == TriggerMode.Software:
            self.laser_controller.emission_off(laser)

        metadata = {
            "exposure_time": str(laser.exposure_time),
            "laser_name": str(laser.name),
            "laser_power": str(laser.power),
            "timestamp": timestamp(),
        }

        # save image
        if settings["imaging"]["lm"]["autosave"] is True:
            save_filename = os.path.join(
                self.save_destination_FM,
                "F_" + self.lineEdit_save_filename_FM.text() + ".tif",
            )
            piescope.utils.save_image(image, save_filename, metadata=metadata)
            self.logger.log(logging.DEBUG, "Saved: {}".format(save_filename))

        self.image_light = image

        self.update_display(modality=Modality.Light)

    def live_imaging_worker(
        self, laser: Laser, stop_event: threading.Event, settings: dict, lock: threading.Lock
    ):
        self.live_imaging_running = True
        self.button_live_image_FM.setDown(True)

        image_frame_interval = settings["imaging"]["lm"]["camera"]["image_frame_interval"]

        while not stop_event.isSet():

            with lock: # thread fun
                self.image_light = self.detector.camera_grab(
                    laser=laser, settings=settings
                )

                self.update_display(modality=Modality.Light)

            if image_frame_interval is not None:
                stop_event.wait(image_frame_interval)

        self.detector.close_camera()
        self.button_live_image_FM.setDown(False)
        self.live_imaging_running = False

    def fluorescence_live_imaging(self, laser: Laser):
        config = self.config.copy()
        try:
            if not self.live_imaging_running:
                self.live_imaging_running = True
                self.button_live_image_FM.setStyleSheet(
                    "background-color: LightGreen")

                self.comboBox_wavelength.setEnabled(False)
                self.comboBox_cmap.setEnabled(False)

                self.stop_event = threading.Event()
                self._thread = threading.Thread(
                    target=self.live_imaging_worker,
                    args=(laser, self.stop_event, config, self.lock),
                )
                self._thread.start()
            else:
                self.comboBox_wavelength.setEnabled(True)
                self.comboBox_cmap.setEnabled(True)
                self.stop_event.set()
                self.button_live_image_FM.setStyleSheet(
                    "background-color: #e3e3e3")

        except (KeyboardInterrupt, SystemExit):

            self.comboBox_wavelength.setEnabled(True)
            self.comboBox_cmap.setEnabled(True)
            self.stop_event.set()
            self.button_live_image_FM.setStyleSheet(
                "background-color: #e3e3e3")

        except Exception as e:
            display_error_message(traceback.format_exc())

    ## Objective functions ##
    def objective_stage_position(self, testing=False):
        try:
            stage = self.objective_stage
            pos = stage.current_position()
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            self.label_objective_stage_position.setText(str(float(pos) / 1000))
            return pos

    def save_objective_stage_position(self):
        try:
            pos = self.label_objective_stage_position.text()
            self.label_objective_stage_saved_position.setText(pos)
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            return pos

    ## Laser functions ##
    def update_current_laser(self, wavelength):
        self.logger.debug("Updating current laser")

        # TODO: change name of laser to wavelength, to clean up
        LASER_WAVELENGTH_TO_NAME = {
            "640 nm": "laser640",
            "561 nm": "laser561",
            "488 nm": "laser488",
            "405 nm": "laser405",
        }

        try:
            laser_name = LASER_WAVELENGTH_TO_NAME[wavelength]
            current_laser = self.laser_controller.lasers[laser_name]
            self.laser_controller.current_laser = current_laser
            self.laser_controller.set_laser_power(
                current_laser, float(self.laser_controller.current_laser.spinBox.text())
            )
            self.laser_controller.set_exposure_time(
                current_laser, float(self.laser_controller.current_laser.lineEdit.text()) * MS_TO_US
            )

        except Exception as e:
            display_error_message(traceback.format_exc())

    # put volume enabled into update_lasers
    def update_volume_lasers(self, laser_name: str, enabled: bool = False):
        self.laser_controller.lasers[laser_name].volume_enabled = enabled

        for config_laser in self.config['lm']['lasers']:
            if config_laser['name'] == laser_name:
                config_laser['volume_enabled'] = enabled

    def update_lasers(self, laser: Laser):
        self.logger.debug("Updating laser dictionary")
        try:
            with self.lock:
                # TODO: clip the exposure time to zero, not empty string
                laser_power = float(laser.spinBox.text())
                exposure_time = float(laser.lineEdit.text()) * MS_TO_US  # ms -> us
                volume_enabled = laser.volumeCheckBox.isChecked()

                # Update current laser for single/live imaging and sttings
                for config_laser in self.config['lm']['lasers']:
                    if config_laser['name'] == laser.name:
                        config_laser['power'] = laser_power
                        config_laser['exposure_time'] = exposure_time * US_TO_MS
                        config_laser['volume_enabled'] = volume_enabled

                self.laser_controller.set_laser_power(
                    self.laser_controller.lasers[laser.name], laser_power
                )

                self.laser_controller.set_exposure_time(
                    self.laser_controller.lasers[laser.name], exposure_time
                )

                self.laser_controller.set_volume_enabled(
                    self.laser_controller.lasers[laser.name], volume_enabled)

        except Exception as e:
            display_error_message(traceback.format_exc())

    ## GUI functions ##
    def open_images(self, modality: Modality):
        """Open image files and display the first"""
        try:

            adorned = False if modality == Modality.Light else True

            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open Milling Image", filter="Images (*.bmp *.tif *.tiff *.jpg)"
            )

            image = piescope.utils.load_image(filename, adorned)

            if modality == Modality.Light:
                self.image_light = image
            else:
                self.image_ion = image

            self.update_display(modality)

        except Exception as e:
            display_error_message(traceback.format_exc())

    def save_image(self, modality: Modality):
        """Save image on display"""
        try:
            if modality == Modality.Light:
                image = self.image_light
                save_path = self.lineEdit_save_destination_FM.text()
                save_name = self.lineEdit_save_filename_FM.text()
            elif modality == Modality.Ion or modality == Modality.Electron:
                image = self.image_ion
                save_path = self.lineEdit_save_destination_FIBSEM.text()
                save_name = self.lineEdit_save_filename_FIBSEM.text()

            if image is None:
                raise ValueError('Tried to save image but no image given')

            os.makedirs(save_path, exist_ok=True)
            dest = os.path.join(save_path, save_name)
            piescope.utils.save_image(image, dest)
        except Exception as e:
            display_error_message(f'{e}')

    def update_display(self, modality: Modality):
        if modality == Modality.Light:
            if self.image_light is None:
                return

            # copy the current light image to modify and check shape etc.
            image = self.image_light

            # raise error if image shape has too many dimensions
            if image.ndim >= 4:
                msg = (
                    "Please select a 2D image for display.\n"
                    + "Image shape here is {}".format(image.shape)
                )
                logging.warning(msg)
                display_error_message(msg)
                return

            # if the image is 3 dimensional, it is probably an RGB of shape (XYC)
            if image.ndim == 3:
                # if the final dimension of the image is not RGB, shape might be (CXY)
                if image.shape[-1] > 3:
                    # shift the first dimension to the final dimension (XYC)
                    image = np.moveaxis(image, 0, -1)
                    # if the final dimension of the image is still not RGB (CXY)
                    if image.shape[-1] != 3:
                        msg = (
                            "Please select a 2D image with no more than 3 color channels for display.\n"
                            + "Image shape here is {}".format(image.shape)
                        )
                        logging.warning(msg)
                        display_error_message(msg)
                        return

            # clip image values
            MAX_FLOAT_VALUE = np.iinfo(image.dtype).max
            min_value = self.doubleSpinBox_clip_min.value() * MAX_FLOAT_VALUE
            max_value = self.doubleSpinBox_clip_max.value() * MAX_FLOAT_VALUE
            image = np.clip(image, min_value, max_value)

            # current_max_value = np.max(image)
            self.label_max_FM_value.setText(f"Image Range: {np.min(image)} - {np.max(image)}")

            crosshair = piescope.utils.create_crosshair(self.image_light, self.config)
            if self.filter_strength_lm > 0:
                image = ndi.median_filter(image, size=int(self.filter_strength_lm))

            fov_percent = 1. # TODO: attach to slider?, add to config
            cy, cx = image.shape[0] //2 , image.shape[1] // 2
            h, w = int(image.shape[0]*fov_percent / 2), int(image.shape[1]*fov_percent / 2)
            image = image[cy -h : cy+ h, cx -w : cx+ w]

            if self.ax_FM is not None and self.toolbar_FM._active == "ZOOM":
                x_lim = self.ax_FM.get_xlim()
                y_lim = self.ax_FM.get_ylim()
            else:
                # x_lim = (cx-w, cx+w)
                # y_lim = (cy-h, cy+h)
                x_lim = (0, image.shape[1])
                y_lim = (0, image.shape[0])          

            self.figure_FM.clear()
            self.figure_FM.patch.set_facecolor(
                (240 / 255, 240 / 255, 240 / 255))
            self.ax_FM = self.figure_FM.add_subplot(111)
            self.ax_FM.set_title("Light Microscope")
            self.ax_FM.patches.clear()
            for patch in crosshair.__dataclass_fields__:
                self.ax_FM.add_patch(getattr(crosshair, patch))

            self.ax_FM.get_xaxis().set_visible(False)
            self.ax_FM.get_yaxis().set_visible(False)
            self.ax_FM.imshow(image, cmap=str(self.comboBox_cmap.currentText()))

            self.ax_FM.set_xlim(x_lim)
            self.ax_FM.set_ylim(y_lim)

            # FIBSEM is image.data
            self.canvas_FM.draw()

            # draw histogram
            self.figure_histogram.clear()
            ax_hist = self.figure_histogram.add_subplot(111)
            ax_hist.hist(np.ravel(image), bins=30)
            ax_hist.set_title("Image Histogram")
            ax_hist.get_yaxis().set_visible(False)
            ax_hist.grid()
            ax_hist.set_xlim((0, max_value))
            self.canvas_histogram.draw()


        else:
            image = self.image_ion.data

            # make a copy of the rgb to display with crosshair
            crosshair = piescope.utils.create_crosshair(
                self.image_ion, self.config)

            plt.axis("off")
            if self.canvas_FIBSEM is not None:
                if self.current_click_event_id:
                    self.canvas_FIBSEM.mpl_disconnect(self.current_click_event_id) 
                self.label_image_FIBSEM.layout().removeWidget(self.canvas_FIBSEM)
                # self.label_image_FIBSEM.layout().removeWidget(self.toolbar_FIBSEM)
                self.canvas_FIBSEM.deleteLater()
                # self.toolbar_FIBSEM.deleteLater()

            self.canvas_FIBSEM = _FigureCanvas(self.figure_FIBSEM)

            self.current_click_event_id = self.canvas_FIBSEM.mpl_connect(
                "button_press_event",
                lambda event: self.on_gui_click(event, modality=Modality.Ion),
            )

            if self.filter_strength_ib > 0:
                image = ndi.median_filter(image, size=int(self.filter_strength_ib))

            self.figure_FIBSEM.clear()
            self.figure_FIBSEM.patch.set_facecolor(
                (240 / 255, 240 / 255, 240 / 255))
            ax_FIBSEM = self.figure_FIBSEM.add_subplot(111)
            ax_FIBSEM.set_title("FIBSEM")
            ax_FIBSEM.patches.clear()
            for patch in crosshair.__dataclass_fields__:
                ax_FIBSEM.add_patch(getattr(crosshair, patch))
            # self.toolbar_FIBSEM = _NavigationToolbar(self.canvas_FIBSEM, self)
            # self.label_image_FIBSEM.layout().addWidget(self.toolbar_FIBSEM)
            self.label_image_FIBSEM.layout().addWidget(self.canvas_FIBSEM)
            ax_FIBSEM.get_xaxis().set_visible(False)
            ax_FIBSEM.get_yaxis().set_visible(False)
            ax_FIBSEM.imshow(image, cmap="gray")
            self.canvas_FIBSEM.draw()

    def remove_canvas(self):
        
        if self.canvas_FIBSEM is not None:

            self.label_image_FIBSEM.layout().removeWidget(self.canvas_FIBSEM)
            # self.label_image_FIBSEM.layout().removeWidget(self.toolbar_FIBSEM)
            self.canvas_FIBSEM.deleteLater()
            # self.toolbar_FIBSEM.deleteLater()

            # del self.canvas_FIBSEM
            # del self.toolbar_FIBSEM

            # TODO: replace this with update canvas, or just update the image

    def on_gui_click(self, event, modality):

        if event.button == 1 and event.dblclick:

            # don't allow double click functionality while zooming or panning, only stopping active window
            if modality == Modality.Light:
                
                image = self.image_light
                pixel_size = self.pixel_size_lm
                if self.toolbar_FM._active == "ZOOM" or self.toolbar_FM._active == "PAN":
                    return
            else:
                image = self.image_ion
                pixel_size = image.metadata.binary_result.pixel_size.x
                # if (
                #     self.toolbar_FIBSEM._active == "ZOOM"
                #     or self.toolbar_FIBSEM._active == "PAN"
                # ):
                #     return

            # check if we have both types of images
            if self.image_light is None:
                display_error_message("Unable to move, no Light Microscope Image available. Please take a light microscope image.")
                return

            if self.image_ion is None:
                display_error_message("Unable to move, no FIBSEM Image available. Please get the last Electron / Ion Image")
                return

            dx, dy = conversions.pixel_to_realspace_coordinate(
                [event.xdata, event.ydata], image, pixel_size
            )

            # updated movement
            if modality is Modality.Light:
                beam_type = BeamType.ION 
            else:
                beam_type = BeamType[image.metadata.acquisition.beam_type.upper()]

            movement.move_stage_relative_with_corrected_movement(
                self.microscope, self.settings, dx=dx, dy=dy, beam_type=beam_type 
            )

            if modality == Modality.Light:
                if not self.live_imaging_running:
                    self.fluorescence_image(laser=self.laser_controller.current_laser, settings=self.config)
                    self.update_display(modality=Modality.Light)
            else:
                beam_type = BeamType[image.metadata.acquisition.beam_type.upper()]
                self.get_image(beam_type, save=False)
                self.update_display(modality=Modality.Ion)

    def fill_destination(self, mode: str):
        """Fills the destination box with the text from the directory"""
        try:
            user_input = QtWidgets.QFileDialog.getExistingDirectory(
                self, "File Destination"
            )
            if user_input == "":
                directory_path = self.DEFAULT_PATH
            else:
                directory_path = os.path.normpath(user_input) + os.path.sep

            if mode == "FM":
                self.save_destination_FM = directory_path
                self.lineEdit_save_destination_FM.setText(directory_path)
                return directory_path
            elif mode == "FIBSEM":
                self.save_destination_FIBSEM = directory_path
                self.lineEdit_save_destination_FIBSEM.setText(
                    directory_path)
                return directory_path
            elif mode == "correlation":
                self.save_destination_correlation = directory_path
                self.correlation_output_path.setText(directory_path)
                return directory_path
        except Exception as e:
            display_error_message(traceback.format_exc())

    ## Acquisition functions ##
    def acquire_volume(self):

        if self.detector is None:
            display_error_message("No detector available")
            return
        if self.laser_controller is None:
            display_error_message("No laser controller connected")
            return
        if self.laser_controller.lasers is None:
            display_error_message("No lasers found for laser controller")
            return
        if self.objective_stage is None:
            display_error_message("Objective stage is not connected")
            return
        if self.mirror_controller is None:
            display_error_message("Mirror controller is not connected.")
            return

        if self.live_imaging_running:
            display_error_message('Live imaging running, cannot take volue')
        try:
            volume_height = int(self.lineEdit_volume_height.text())
        except ValueError:
            display_error_message("Volume height must be a positive integer")
            return
        else:
            if volume_height <= 0:
                display_error_message(
                    "Volume height must be a positive integer")
                return

        # make sure z_slice_distance is a positive integer
        try:
            z_slice_distance = int(self.lineEdit_slice_distance.text())
        except ValueError:
            display_error_message("Slice distance must be a positive integer")
            return
        else:
            if z_slice_distance <= 0:
                display_error_message(
                    "Slice distance must be a positive integer")
                return
        num_z_slices = int(round(volume_height / z_slice_distance) + 1)

        colour_dict = []
        for laser in self.laser_controller.lasers.values():
            if laser.volume_enabled:
                logging.debug(f'This laser is volume enabled: {laser.name}')
                colour_dict.append(laser.colour)

        if colour_dict == []:
            display_error_message('No lasers chosen for volume')
            return

        imaging_type = ImagingType[str(
            self.comboBox_imaging_type.currentText()).upper()]

        volume = piescope.lm.volume.acquire_volume(
            num_z_slices=num_z_slices,
            z_slice_distance=z_slice_distance,
            imaging_type=imaging_type,
            laser_controller=self.laser_controller,
            mirror_controller=self.mirror_controller,
            objective_stage=self.objective_stage,
            detector=self.detector,
            arduino=self.arduino,
            settings=self.config,
        )

        #CPZAYX
        meta = {
            "z_slice_distance": str(z_slice_distance),
            "num_z_slices": str(num_z_slices),
            "laser_dict": str(self.laser_controller.lasers),
            "volume_height": str(volume_height),
        }

        max_intensity = piescope.utils.max_intensity_projection(volume)
        #YXC

        rgb = piescope.utils.rgb_image(max_intensity, colour_dict=colour_dict)
        self.image_light = rgb

        if self.config["imaging"]["volume"]["autosave"]:
            # save full volume
            #CPZAYX
            save_filename = os.path.join(
                self.save_destination_FM,
                "Volume_" + self.lineEdit_save_filename_FM.text(),
            )
            piescope.utils.save_image(volume, save_filename, metadata=meta)
            logging.info("Saved: {}".format(save_filename))

            # Save maximum intensity projection
            save_filename_max_intensity = os.path.join(
                self.save_destination_FM,
                "MIP_" + self.lineEdit_save_filename_FM.text(),
            )
            piescope.utils.save_image(
                max_intensity, save_filename_max_intensity, metadata=meta
            )
            logging.info("Saved: {}".format(save_filename_max_intensity))

            # Save maximum intensity rgb
            save_filename_rgb = os.path.join(
                self.save_destination_FM,
                "RGB_" + self.lineEdit_save_filename_FM.text(),
            )
            piescope.utils.save_image(rgb, save_filename_rgb, metadata=meta)
            logging.info("Saved: {}".format(save_filename_rgb))

        # Update display
        self.update_display(modality=Modality.Light)

    def correlateim(self):
        try:
            if self.image_light is None:
                raise ValueError('No fluorescence image provided')

            if self.image_ion is None:
                raise ValueError('No FIBSEM image provided')

            if self.image_ion.metadata.acquisition.beam_type != "Ion":
                raise TypeError(
                    'Need to correlate with an ion image (for the moment)')

            output_filepath = self.correlation_output_path.text()
            output_filename = self.correlation_output_name.text()
            if output_filepath == "":
                raise ("No path selected")
            if not os.path.isdir(output_filepath):
                raise ValueError("Please select a valid directory")
            if output_filename == "":
                raise ValueError(
                    "Please select a name for the correlated image")

            output_path = os.path.join(output_filepath, output_filename)

            image_ext = "_" + timestamp() + ".tiff"

            output_path = (output_path + image_ext)
            import skimage.color
            correlation_image_lm = np.copy(self.image_light)
            correlation_image_ion = skimage.color.gray2rgb(
                np.copy(self.image_ion.data.astype(np.uint8)))

            # resize lm image to ion image size
            correlation_image_lm = skimage.transform.resize(
                correlation_image_lm, correlation_image_ion.shape)

            self.correlation_window = corr.CorrelationWindow(
                parent=self, fluorescence_image=correlation_image_lm,
                fibsem_image=correlation_image_ion, output_path=output_path, settings=self.config)

            self.correlation_window.showMaximized()
            self.correlation_window.show()

            # on exit, run milling
            self.correlation_window.exitButton.clicked.connect(
                lambda: self.milling(
                    display_image=self.correlation_window.pass_image())
            )

        except Exception as e:
            display_error_message(f'{e}')

    def milling(self, display_image=None):
        aligned_image = display_image
        if aligned_image is None:
            display_error_message('No aligned image loaded')
            return
        self.milling_window = piescope_gui.milling.GUIMillingWindow(
            parent_gui=self, adorned_image=self.image_ion, display_image=aligned_image)
        self.microscope.imaging.set_active_view(2)
        self.milling_window.pushButton_save_correlated_image.clicked.connect(
            lambda: piescope.utils.save_image(display_image, self.correlation_window.output_path))

        # self.milling_window.window_close.connect(self.pass_milling_complete)
        if self.parent() is not None:
            self.milling_window.pushButton_save_position.setEnabled(True)
        else:
            self.milling_window.pushButton_start_milling.setEnabled(True)
            self.milling_window.pushButton_stop_milling.setEnabled(True)

        self.milling_window.pushButton_save_position.clicked.connect(
            lambda: self.close())
        self.milling_window.pushButton_save_position.clicked.connect(
            lambda: self.milling_window.close())
        self.milling_window.show()

    def closeEvent(self, event):
        event.accept()
        self.window_close.emit()

def main():
    """Launch the `piescope_gui` main application window."""
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    app.aboutToQuit.connect(qt_app.disconnect)  # cleanup & teardown
    qt_app.showNormal()

    # set into roughly middle of screen
    desktop = QtWidgets.QDesktopWidget()
    qt_app.move((desktop.width()-qt_app.width())/2, (desktop.height()-qt_app.height())/3.)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
