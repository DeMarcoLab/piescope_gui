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
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as _FigureCanvas
from matplotlib.backends.backend_qt5agg import (
    NavigationToolbar2QT as _NavigationToolbar,
)
from piescope.lm import arduino, mirror, structured
from piescope.lm.detector import Basler
from piescope.lm.laser import Laser, LaserController
from piescope.lm.mirror import ImagingType, StagePosition
from piescope.utils import Modality, TriggerMode
from PyQt5 import QtCore, QtGui, QtWidgets

import piescope_gui.correlation.main as corr
import piescope_gui.milling
import piescope_gui.qtdesigner_files.main as gui_main
from piescope_gui.utils import display_error_message, timestamp

# TODO: add arduino code to repo
# TODO: Slider as double


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()
        self.setupUi(MainGui=self)
        self.read_config_file()
        self.setup_logging()
        self.setup_initial_values()
        self.initialise_image_frames()
        self.setup_connections()
        self.initialise_hardware()
        self.update_connections()

    def setup_initial_values(self):
        self.live_imaging_running = False
        self.image_light = None
        self.image_ion = None

        self.lineEdit_save_filename_FM.setText("Fluorescence Image")
        self.lineEdit_save_filename_FIBSEM.setText("FIBSEM Image")
        self.label_objective_stage_position.setText("Unknown")

        self.save_destination_FM = self.logging_path
        self.save_destination_FIBSEM = self.logging_path
        self.save_destination_correlation = self.logging_path
        self.lineEdit_save_destination_FM.setText(self.logging_path)
        self.lineEdit_save_destination_FIBSEM.setText(self.logging_path)
        self.correlation_output_path.setText(self.logging_path)

        self.comboBox_resolution.setCurrentIndex(1)  # resolution "1536x1024"

    def read_config_file(self):
        # read config file
        config_path = os.path.join(os.path.dirname(piescope.__file__), "config.yml")
        self.config = piescope.utils.read_config(config_path)

        # set ip_address and online status
        self.ip_address = self.config["system"]["ip_address"]
        self.online = self.config["system"]["online"]
        self.trigger_mode = self.config["imaging"]["lm"]["trigger_mode"]

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

    def initialise_hardware(self):
        self.microscope = None
        self.detector = None
        self.laser_controller = None
        self.objective_stage = None
        self.mirror_controller = None
        self.arduino = None

        if self.online:
            self.connect_to_fibsem_microscope()
            self.connect_to_basler_detector()
            self.connect_to_laser_controller()
            self.connect_to_objective_controller()
            # self.connect_to_mirror_controller()
            self.connect_to_arduino()
            # TODO: Figure out these pins
            # structured.single_line_onoff(onoff=False, pin='P13')
            # structured.single_line_onoff(onoff=False, pin='P27')

    # TODO: hardware dependent connections

    def update_microscope_connections(self):

        if self.microscope:
            self.comboBox_resolution.setEnabled(True)
            self.lineEdit_dwell_time.setEnabled(True)
            self.button_get_image_FIB.setEnabled(True)
            self.button_get_image_SEM.setEnabled(True)
            self.button_last_image_FIB.setEnabled(True)
            self.button_last_image_SEM.setEnabled(True)
            self.to_light_microscope.setEnabled(True)
            self.to_electron_microscope.setEnabled(True)
            self.pushButton_milling.setEnabled(True)

            self.comboBox_resolution.currentTextChanged.connect(
                lambda: self.update_fibsem_settings()
            )
            self.lineEdit_dwell_time.textChanged.connect(
                lambda: self.update_fibsem_settings()
            )

            self.button_get_image_FIB.clicked.connect(lambda: self.get_FIB_image())
            self.button_get_image_SEM.clicked.connect(lambda: self.get_SEM_image())
            self.button_last_image_FIB.clicked.connect(
                lambda: self.get_last_FIB_image()
            )
            self.button_last_image_SEM.clicked.connect(
                lambda: self.get_last_SEM_image()
            )

            self.to_light_microscope.clicked.connect(
                lambda: self.move_to_light_microscope()
            )
            self.to_electron_microscope.clicked.connect(
                lambda: self.move_to_electron_microscope()
            )

            self.pushButton_milling.clicked.connect(lambda: self.milling())

        else:
            self.comboBox_resolution.setEnabled(False)
            self.lineEdit_dwell_time.setEnabled(False)
            self.button_get_image_FIB.setEnabled(False)
            self.button_get_image_SEM.setEnabled(False)
            self.button_last_image_FIB.setEnabled(False)
            self.button_last_image_SEM.setEnabled(False)
            self.to_light_microscope.setEnabled(False)
            self.to_electron_microscope.setEnabled(False)
            self.pushButton_milling.setEnabled(False)

    def update_connections(self):
        self.update_microscope_connections()
        self.update_laser_connections()

    def update_laser_connections(self):
        if self.laser_controller and not self.checkBox_laser1.isEnabled:
            self.checkBox_laser1.setEnabled(True)
            self.checkBox_laser2.setEnabled(True)
            self.checkBox_laser3.setEnabled(True)
            self.checkBox_laser4.setEnabled(True)
            self.slider_laser1.setEnabled(True)
            self.slider_laser2.setEnabled(True)
            self.slider_laser3.setEnabled(True)
            self.slider_laser4.setEnabled(True)
            self.spinBox_laser1.setEnabled(True)
            self.spinBox_laser2.setEnabled(True)
            self.spinBox_laser3.setEnabled(True)
            self.spinBox_laser4.setEnabled(True)
            self.lineEdit_exposure_1.setEnabled(True)
            self.lineEdit_exposure_2.setEnabled(True)
            self.lineEdit_exposure_3.setEnabled(True)
            self.lineEdit_exposure_4.setEnabled(True)
            self.buttonGroup.setEnabled(True)

            self.checkBox_laser1.clicked.connect(
                lambda: self.update_volume_lasers(
                    laser_name="laser640", enabled=self.checkBox_laser1.isChecked()
                )
            )
            self.checkBox_laser2.clicked.connect(
                lambda: self.update_volume_lasers(
                    laser_name="laser561", enabled=self.checkBox_laser2.isChecked()
                )
            )
            self.checkBox_laser3.clicked.connect(
                lambda: self.update_volume_lasers(
                    laser_name="laser488", enabled=self.checkBox_laser3.isChecked()
                )
            )
            self.checkBox_laser4.clicked.connect(
                lambda: self.update_volume_lasers(
                    laser_name="laser405", enabled=self.checkBox_laser4.isChecked()
                )
            )

            self.slider_laser1.valueChanged.connect(
                lambda: self.update_lasers("laser640")
            )
            self.slider_laser2.valueChanged.connect(
                lambda: self.update_lasers("laser561")
            )
            self.slider_laser3.valueChanged.connect(
                lambda: self.update_lasers("laser488")
            )
            self.slider_laser4.valueChanged.connect(
                lambda: self.update_lasers("laser405")
            )

            self.spinBox_laser1.valueChanged.connect(
                lambda: self.update_lasers("laser640")
            )
            self.spinBox_laser2.valueChanged.connect(
                lambda: self.update_lasers("laser561")
            )
            self.spinBox_laser3.valueChanged.connect(
                lambda: self.update_lasers("laser488")
            )
            self.spinBox_laser4.valueChanged.connect(
                lambda: self.update_lasers("laser405")
            )


            self.lineEdit_exposure_1.textChanged.connect(
                lambda: self.update_lasers("laser640")
            )
            self.lineEdit_exposure_2.textChanged.connect(
                lambda: self.update_lasers("laser561")
            )
            self.lineEdit_exposure_3.textChanged.connect(
                lambda: self.update_lasers("laser488")
            )
            self.lineEdit_exposure_4.textChanged.connect(
                lambda: self.update_lasers("laser405")
            )

            self.buttonGroup.buttonClicked.connect(
                lambda: self.update_current_laser(
                    self.buttonGroup.checkedButton().objectName()
                )
            )

        if self.laser_controller and self.detector and not self.button_get_image_FIB.isEnabled():
            self.button_get_image_FM.clicked.connect(
                lambda: self.fluorescence_image(
                    laser=self.laser_controller.current_laser, settings=self.config,
                )
            )
            self.button_live_image_FM.clicked.connect(
                lambda: self.fluorescence_live_imaging(
                    self.laser_controller.current_laser,
                )
            )
            self.button_get_image_FM.clicked.connect(
                lambda: self.fluorescence_image(
                    laser=self.laser_controller.current_laser, settings=self.config,
                )
            )
            self.button_live_image_FM.clicked.connect(
                lambda: self.fluorescence_live_imaging(
                    self.laser_controller.current_laser,
                )
            )


    def setup_connections(self):
        self.actionOpen_FM_Image.triggered.connect(
            lambda: self.open_images(Modality.Light)
        )
        self.actionOpen_FIBSEM_Image.triggered.connect(
            lambda: self.open_images(Modality.Ion)
        )

        self.actionSave_FM_Image.triggered.connect(lambda: self.save_image("FM"))
        self.actionSave_FIBSEM_Image.triggered.connect(
            lambda: self.save_image("FIBSEM")
        )

        self.button_save_destination_FM.clicked.connect(
            lambda: self.fill_destination("FM")
        )
        self.button_save_destination_FIBSEM.clicked.connect(
            lambda: self.fill_destination("FIBSEM")
        )
        self.toolButton_correlation_output.clicked.connect(
            lambda: self.fill_destination("correlation")
        )

        self.comboBox_cmap.currentTextChanged.connect(
            lambda: self.update_display(modality=Modality.Light, settings=self.config)
        )

        self.pushButton_load_FM.clicked.connect(
            lambda: self.open_images(Modality.Light)
        )
        self.pushButton_load_FIBSEM.clicked.connect(
            lambda: self.open_images(Modality.Ion)
        )

        self.pushButton_save_FM.clicked.connect(lambda: self.save_image("FM"))
        self.pushButton_save_FIBSEM.clicked.connect(lambda: self.save_image("FIBSEM"))

        if self.online:


            self.pushButton_initialise_stage.clicked.connect(
                self.initialise_objective_stage
            )
            self.pushButton_move_absolute.clicked.connect(
                lambda: self.move_absolute_objective_stage(
                    self.objective_stage, self.lineEdit_move_absolute.text()
                )
            )
            self.pushButton_move_relative.clicked.connect(
                lambda: self.move_relative_objective_stage(
                    self.objective_stage, self.lineEdit_move_relative.text()
                )
            )
            self.toolButton_negative.clicked.connect(
                lambda: self.move_relative_objective_stage(
                    self.objective_stage,
                    self.lineEdit_move_relative.text(),
                    direction="negative",
                )
            )
            self.toolButton_positive.clicked.connect(
                lambda: self.move_relative_objective_stage(
                    self.objective_stage,
                    self.lineEdit_move_relative.text(),
                    direction="positive",
                )
            )

            self.connect_microscope.clicked.connect(
                lambda: self.connect_to_fibsem_microscope(ip_address=self.ip_address)
            )

            self.pushButton_volume.clicked.connect(
                lambda: self.acquire_volume(
                    imaging_mode=self.mirror_controller.get_mode()
                )
            )
            self.pushButton_correlation.clicked.connect(lambda: self.correlateim())

            self.pushButton_get_position.clicked.connect(self.objective_stage_position)
            self.pushButton_save_objective_position.clicked.connect(
                self.save_objective_stage_position
            )
            self.pushButton_go_to_saved_position.clicked.connect(
                lambda: self.move_absolute_objective_stage(self.objective_stage)
            )

            self.radioButton_Widefield.clicked.connect(
                lambda: self.mirror_controller.move_to(StagePosition.WIDEFIELD)
            )
            self.radioButton_Widefield.clicked.connect(
                lambda: self.mirror_controller.set_mode(ImagingType.WIDEFIELD)
            )

            self.radioButton_SIM.clicked.connect(
                lambda: self.mirror_controller.move_to(StagePosition.SIXTY)
            )
            self.radioButton_SIM.clicked.connect(
                lambda: self.mirror_controller.set_mode(ImagingType.SIM)
            )

            self.pushButton_pattern_next.clicked.connect(
                lambda: self.mirror_controller.next_position()
            )

    def initialise_image_frames(self):
        self.figure_FM = plt.figure()
        plt.axis("off")
        plt.tight_layout()
        plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.01)
        self.canvas_FM = _FigureCanvas(self.figure_FM)
        self.toolbar_FM = _NavigationToolbar(self.canvas_FM, self)
        self.canvas_FM.mpl_connect(
            "button_press_event",
            lambda event: self.on_gui_click(event, modality=Modality.Light),
        )

        self.label_image_FM.setLayout(QtWidgets.QVBoxLayout())
        self.label_image_FM.layout().addWidget(self.toolbar_FM)
        self.label_image_FM.layout().addWidget(self.canvas_FM)

        self.figure_FIBSEM = plt.figure()
        plt.axis("off")
        plt.tight_layout()
        plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.01)
        self.canvas_FIBSEM = _FigureCanvas(self.figure_FIBSEM)
        self.toolbar_FIBSEM = _NavigationToolbar(self.canvas_FIBSEM, self)

        self.label_image_FIBSEM.setLayout(QtWidgets.QVBoxLayout())
        self.label_image_FIBSEM.layout().addWidget(self.toolbar_FIBSEM)
        self.label_image_FIBSEM.layout().addWidget(self.canvas_FIBSEM)

    def disconnect(self):
        print("Running cleanup/teardown")
        logging.debug("Running cleanup/teardown")
        # Change values in qtdesigner_files\main.py
        if self.objective_stage is not None and self.online:
            # Return objective lens stage to the "out" position and disconnect.
            self.move_absolute_objective_stage(self.objective_stage, position=-1000)
            self.objective_stage.disconnect()
        if self.microscope is not None:
            self.microscope.disconnect()

    def connect_to_arduino(self):
        try:
            self.arduino = arduino.Arduino()
        except:
            display_error_message(
                f"Unable to connect to Arduino. <br><br>{traceback.format_exc()}"
            )

    def connect_to_mirror_controller(self):
        try:
            self.mirror_controller = mirror.PIController()
        except:
            display_error_message(
                f"Unable to connect to mirror controller. <br><br>{traceback.format_exc()}"
            )

    def connect_to_objective_controller(self):
        try:
            self.objective_stage = self.initialise_objective_stage()
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
        try:
            self.laser_controller = LaserController(settings=self.config)
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

    def connect_to_basler_detector(self):
        try:
            self.detector = Basler(settings=self.config)
            try:
                structured.single_line_onoff(
                    onoff=False, pin=self.config["imaging"]["lm"]["camera"]["pin"]
                )
            except:
                display_error_message(
                    f"Unable to connect to niqadmx device. <br><br>{traceback.format_exc()}"
                )
        except:
            display_error_message(
                f"Unable to connect to Basler device. <br><br>{traceback.format_exc()}"
            )

    ############## FIBSEM microscope methods ##############
    def connect_to_fibsem_microscope(self):
        """Connect to the FIBSEM microscope."""
        try:
            self.microscope = piescope.fibsem.initialise(ip_address=self.ip_address)
            self.camera_settings = self.update_fibsem_settings()
        except Exception as e:
            display_error_message(
                f"Unable to connect to the FIB-SEM. <br><br>{traceback.format_exc()}"
            )

    def update_fibsem_settings(self):
        if not self.microscope and self.online:
            self.connect_to_fibsem_microscope()
        try:
            dwell_time = float(self.lineEdit_dwell_time.text()) * 1.0e-6
            resolution = self.comboBox_resolution.currentText()
            fibsem_settings = piescope.fibsem.update_camera_settings(
                dwell_time, resolution
            )
            self.camera_settings = fibsem_settings
            return fibsem_settings
        except Exception as e:
            display_error_message(
                f"Unable to update FIB-SEM settings {traceback.format_exc()}"
            )

    ############## FIBSEM sample stage methods ##############
    def move_to_light_microscope(
        self, x=+49.9092e-3, y=-0.1143e-3
    ):  # TODO: Alex wants one function
        # TODO: Stage shift in fluorescence
        if not self.liveCheck:
            print("Cannot move stage, live imaging currently running")
            return
        try:
            piescope.fibsem.move_to_light_microscope(self.microscope, x, y)
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            print("Moved to light microscope.")

    def move_to_electron_microscope(self, x=-49.9092e-3, y=+0.1143e-3):
        if not self.liveCheck:
            print("Cannot move stage, live imaging currently running")
            return
        try:
            piescope.fibsem.move_to_electron_microscope(self.microscope, x, y)
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            print("Moved to electron microscope.")

    ############## FIBSEM image methods ##############
    def get_FIB_image(self, autosave=True):
        try:
            if self.checkBox_Autocontrast.isChecked():
                self.image_ion = self.autocontrast_ion_beam()
            else:
                self.image_ion = piescope.fibsem.new_ion_image(
                    self.microscope, self.camera_settings
                )

            if autosave is True:
                save_filename = os.path.join(
                    self.save_destination_FIBSEM,
                    "I_" + self.lineEdit_save_filename_FIBSEM.text() + ".tif",
                )
                piescope.utils.save_image(self.image_ion, save_filename)
                print("Saved: {}".format(save_filename))

            # Update display
            self.update_display(modality=Modality.Ion, settings=self.config)

        except Exception as e:
            display_error_message(traceback.format_exc())

    def get_last_FIB_image(self):
        try:
            self.image_ion = piescope.fibsem.last_ion_image(self.microscope)
            self.update_display(modality=Modality.Ion, settings=self.config)
        except Exception as e:
            display_error_message(traceback.format_exc())

    def get_SEM_image(self, autosave=True):
        try:
            if self.checkBox_Autocontrast.isChecked():
                self.autocontrast_ion_beam(view=1)
            self.image_ion = piescope.fibsem.new_electron_image(
                self.microscope, self.camera_settings
            )

            if autosave is True:
                save_filename = os.path.join(
                    self.save_destination_FIBSEM,
                    "E_" + self.lineEdit_save_filename_FIBSEM.text() + ".tif",
                )
                piescope.utils.save_image(self.image_ion, save_filename)
                print("Saved: {}".format(save_filename))
            # update display
            self.update_display(modality=Modality.Ion, settings=self.config)
        except Exception as e:
            display_error_message(traceback.format_exc())

    def get_last_SEM_image(self):
        try:
            self.image_ion = piescope.fibsem.last_electron_image(self.microscope)
            self.update_display(modality=Modality.Ion, settings=self.config)
        except Exception as e:
            display_error_message(traceback.format_exc())

    def autocontrast_ion_beam(self, view=2):
        try:
            self.microscope.imaging.set_active_view(view)  # the ion beam view
            piescope.fibsem.autocontrast(self.microscope, view=view)
            self.image_ion = piescope.fibsem.last_ion_image(self.microscope)
        except Exception as e:
            display_error_message(traceback.format_exc())

    def fluorescence_image(
        self, laser: Laser, settings: dict,
    ):
        if self.laser_controller is None:
            display_error_message("Not connect to lasers")
            return

        # check if live imaging is possible
        if self.live_imaging_running:
            self.button_live_image_FM.setDown(True)
            print("Can't take image, live imaging currently running")
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

        self.update_display(modality=Modality.Light, settings=self.config)

    def live_imaging_worker(
        self, laser: Laser, stop_event: threading.Event, settings: dict
    ):
        self.live_imaging_running = True
        self.button_live_image_FM.setDown(True)

        while not stop_event.isSet():
            if settings["imaging"]["lm"]["trigger_mode"] == TriggerMode.Software:
                self.laser_controller.emission_on(laser)
            self.image_light = self.detector.camera_grab(
                laser=laser, settings=self.config
            )
            if settings["imaging"]["lm"]["trigger_mode"] == TriggerMode.Software:
                self.laser_controller.emission_off(laser)

            self.update_display(modality=Modality.Light, settings=self.config)

            if settings["imaging"]["lm"]["camera"]["image_frame_interval"] is not None:
                stop_event.wait(
                    settings["imaging"]["lm"]["camera"]["image_frame_interval"]
                )

        self.detector.camera.Close()
        self.button_live_image_FM.setDown(False)
        self.live_imaging_running = False

    def fluorescence_live_imaging(self, laser: Laser):
        config = self.config.copy()
        try:
            if not self.live_imaging_running:
                self.live_imaging_running = True

                self.radioButton_640.setEnabled(False)
                self.radioButton_561.setEnabled(False)
                self.radioButton_488.setEnabled(False)
                self.radioButton_405.setEnabled(False)

                self.stop_event = threading.Event()
                self._thread = threading.Thread(
                    target=self.live_imaging_worker,
                    args=(laser, self.stop_event, config),
                )
                self._thread.start()
            else:
                self.radioButton_640.setEnabled(True)
                self.radioButton_561.setEnabled(True)
                self.radioButton_488.setEnabled(True)
                self.radioButton_405.setEnabled(True)
                self.stop_event.set()
        except (KeyboardInterrupt, SystemExit):

            self.radioButton_640.setEnabled(True)
            self.radioButton_561.setEnabled(True)
            self.radioButton_488.setEnabled(True)
            self.radioButton_405.setEnabled(True)
            self.stop_event.set()

        except Exception as e:
            display_error_message(traceback.format_exc())

    ############## Fluorescence objective lens stage methods ##############

    def initialise_objective_stage(self, time_delay=0.3, testing=False):
        """initialise the fluorescence objective lens stage."""
        if self.objective_stage is not None:
            logging.warning("The objective lens stage is already initialised.")
            return self.objective_stage
        else:
            try:
                stage = piescope.lm.objective.StageController(testing=testing)
                self.objective_stage = stage
                stage.initialise_system_parameters()
            except Exception as e:
                display_error_message(
                    f"Unable to connect to objective stage. <br><br>{traceback.format_exc()}"
                )
            else:
                return stage

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

    def move_absolute_objective_stage(
        self, stage, position="", time_delay=0.3, testing=False
    ):
        if position is "":
            position = self.label_objective_stage_saved_position.text()
            if position is "":
                display_error_message(
                    "Please provide user input to 'Move relative' for the "
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
                "Absolute move the objective stage to position " "{}".format(position)
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
            self.label_objective_stage_position.setText(str(float(new_position) / 1000))
            return new_position

    def move_relative_objective_stage(
        self, stage, distance="", time_delay=0.3, testing=False, direction="positive"
    ):
        if distance is "":
            distance = self.lineEdit_move_relative.text()
            if distance is "":
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
            self.logger.debug(
                "Relative move the objective stage by " "{}".format(distance)
            )
            ans = stage.move_relative(distance)
            time.sleep(time_delay)
            new_position = stage.current_position()
            self.logger.debug(
                "After relative move, objective stage is now at "
                "position: {}".format(new_position)
            )
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            self.label_objective_stage_position.setText(str(float(new_position) / 1000))
            return new_position

    ############## Fluorescence laser methods ##############
    # TODO: dataclass this
    def update_current_laser(self, selected_button):
        self.logger.debug("Updating current laser")
        LASER_BUTTON_TO_POWER = {
            "radioButton_640": [
                "laser640",
                self.spinBox_laser1,
                self.lineEdit_exposure_1,
            ],
            "radioButton_561": [
                "laser561",
                self.spinBox_laser2,
                self.lineEdit_exposure_2,
            ],
            "radioButton_488": [
                "laser488",
                self.spinBox_laser3,
                self.lineEdit_exposure_3,
            ],
            "radioButton_405": [
                "laser405",
                self.spinBox_laser4,
                self.lineEdit_exposure_4,
            ],
        }

        try:
            selected_laser_info = LASER_BUTTON_TO_POWER[selected_button]
            laser_name = selected_laser_info[0]
            current_laser = self.laser_controller.lasers[laser_name]
            self.laser_controller.current_laser = current_laser
            self.laser_controller.set_laser_power(
                current_laser, float(selected_laser_info[1].text())
            )
            self.laser_controller.set_exposure_time(
                current_laser, float(selected_laser_info[2].text()) * 1000
            )

            print(current_laser)
        except Exception as e:
            display_error_message(traceback.format_exc())

    def update_volume_lasers(self, laser_name: str, enabled: bool = False):
        self.laser_controller.lasers[laser_name].volume_enabled = enabled
        print(self.laser_controller.lasers)

    def update_lasers(self, laser: Laser):
        self.logger.debug("Updating laser dictionary")
        try:
            # laser_selected, laser_power, exposure_time, widget_spinbox, widget_slider, widget_textexposure
            LASER_INFO = {
                "laser640": [self.spinBox_laser1, self.lineEdit_exposure_1,],
                "laser561": [self.spinBox_laser2, self.lineEdit_exposure_2,],
                "laser488": [self.spinBox_laser3, self.lineEdit_exposure_3,],
                "laser405": [self.spinBox_laser4, self.lineEdit_exposure_4,],
            }

            laser_power = float(LASER_INFO[laser][0].text())
            exposure_time = float(LASER_INFO[laser][1].text()) * 1000  # ms -> us

            # Update current laser for single/live imaging and sttings
            self.update_current_laser(self.buttonGroup.checkedButton().objectName())
            self.laser_controller.set_laser_power(
                self.laser_controller.lasers[laser], laser_power
            )
            self.laser_controller.set_exposure_time(
                self.laser_controller.lasers[laser], exposure_time
            )

        except Exception as e:
            display_error_message(traceback.format_exc())

    ############## Image methods ##############
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
                old_mod = "FM"
            else:
                self.image_ion = image
                old_mod = "FIBSEM"

            self.update_display(modality, settings=self.config)

        except Exception as e:
            display_error_message(traceback.format_exc())

    def save_image(self, modality):  # TODO: standardise image saving - replace modality
        """Save image on display"""
        try:
            if modality == "FM":
                if self.image_light is not None:
                    display_image = self.image_light
                    [save_base, ext] = os.path.splitext(
                        self.lineEdit_save_filename_FM.text()
                    )
                    dest = (
                        self.lineEdit_save_destination_FM.text()
                        + os.path.sep
                        + save_base
                        + ".tif"
                    )
                    dir_exists = os.path.isdir(self.lineEdit_save_destination_FM.text())
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
                                dest = (
                                    self.lineEdit_save_destination_FM.text()
                                    + os.path.sep
                                    + save_base
                                    + "("
                                    + str(count)
                                    + ").tif"
                                )
                                exists = os.path.isfile(dest)
                                count = count + 1
                                piescope.utils.save_image(display_image, dest)
                else:
                    display_error_message("No image to save")

            elif modality == "FIBSEM":
                if self.image_ion is not None:
                    display_image = self.image_ion
                    [save_base, ext] = os.path.splitext(
                        self.lineEdit_save_filename_FIBSEM.text()
                    )
                    dest = (
                        self.lineEdit_save_destination_FIBSEM.text()
                        + os.path.sep
                        + save_base
                        + ".tif"
                    )
                    dir_exists = os.path.isdir(
                        self.lineEdit_save_destination_FIBSEM.text()
                    )
                    if not dir_exists:
                        os.makedirs(self.lineEdit_save_destination_FIBSEM.text())
                        piescope.utils.save_image(display_image, dest)
                    else:
                        exists = os.path.isfile(dest)
                        if not exists:
                            piescope.utils.save_image(display_image, dest)
                        else:
                            count = 1
                            while exists:
                                dest = (
                                    self.lineEdit_save_destination_FIBSEM.text()
                                    + os.path.sep
                                    + save_base
                                    + "("
                                    + str(count)
                                    + ").tif"
                                )
                                exists = os.path.isfile(dest)
                                count = count + 1
                                piescope.utils.save_image(display_image, dest)

                else:
                    display_error_message("No image to save")

        except Exception as e:
            display_error_message(traceback.format_exc())

    def update_display(self, modality: Modality, settings: dict):
        if modality == Modality.Light:

            max_value = self.image_light.max()
            self.label_max_FM_value.setText(f"Max value: {str(max_value)}")

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

            crosshair = piescope.utils.create_crosshair(self.image_light, self.config)
            if settings["imaging"]["lm"]["filter_strength"] > 0:
                image = ndi.median_filter(
                    image, size=int(settings["imaging"]["lm"]["filter_strength"])
                )

            self.figure_FM.clear()
            self.figure_FM.patch.set_facecolor((240 / 255, 240 / 255, 240 / 255))
            ax_FM = self.figure_FM.add_subplot(111)
            ax_FM.set_title("Light Microscope")
            ax_FM.patches = []
            for patch in crosshair.__dataclass_fields__:
                ax_FM.add_patch(getattr(crosshair, patch))
            if self.toolbar_FM is None:
                self.toolbar_FM = _NavigationToolbar(self.canvas_FM, self)
            self.label_image_FM.layout().addWidget(self.toolbar_FM)
            self.label_image_FM.layout().addWidget(self.canvas_FM)
            ax_FM.get_xaxis().set_visible(False)
            ax_FM.get_yaxis().set_visible(False)
            ax_FM.imshow(image, cmap=str(self.comboBox_cmap.currentText()))
            # FIBSEM is image.data
            self.canvas_FM.draw()

        else:
            image = self.image_ion.data

            # make a copy of the rgb to display with crosshair
            crosshair = piescope.utils.create_crosshair(self.image_ion, self.config)

            plt.axis("off")
            if self.canvas_FIBSEM:
                self.label_image_FIBSEM.layout().removeWidget(self.canvas_FIBSEM)
                self.label_image_FIBSEM.layout().removeWidget(self.toolbar_FIBSEM)
                self.canvas_FIBSEM.deleteLater()
                self.toolbar_FIBSEM.deleteLater()
            self.canvas_FIBSEM = _FigureCanvas(self.figure_FIBSEM)

            self.canvas_FIBSEM.mpl_connect(
                "button_press_event",
                lambda event: self.on_gui_click(event, modality=Modality.Ion),
            )

            if settings["imaging"]["ib"]["filter_strength"] > 0:
                image = ndi.median_filter(
                    image, size=int(settings["imaging"]["ib"]["filter_strength"])
                )

            self.figure_FIBSEM.clear()
            self.figure_FIBSEM.patch.set_facecolor((240 / 255, 240 / 255, 240 / 255))
            ax_FIBSEM = self.figure_FIBSEM.add_subplot(111)
            ax_FIBSEM.set_title("FIBSEM")
            ax_FIBSEM.patches = []
            for patch in crosshair.__dataclass_fields__:
                ax_FIBSEM.add_patch(getattr(crosshair, patch))
            self.toolbar_FIBSEM = _NavigationToolbar(self.canvas_FIBSEM, self)
            self.label_image_FIBSEM.layout().addWidget(self.toolbar_FIBSEM)
            self.label_image_FIBSEM.layout().addWidget(self.canvas_FIBSEM)
            ax_FIBSEM.get_xaxis().set_visible(False)
            ax_FIBSEM.get_yaxis().set_visible(False)
            ax_FIBSEM.imshow(image, cmap="gray")
            self.canvas_FIBSEM.draw()

    # TODO: reorder functions to make more sense
    def on_gui_click(self, event, modality):
        # don't allow double click functionality while zooming or panning, only stopping active window
        if modality == Modality.Light:
            image = self.image_light
            pixel_size = self.config["imaging"]["lm"]["camera"]["pixel_size"]
            if self.toolbar_FM._active == "ZOOM" or self.toolbar_FM._active == "PAN":
                return
        else:
            image = self.image_ion
            pixel_size = image.metadata.binary_result.pixel_size.x
            if (
                self.toolbar_FIBSEM._active == "ZOOM"
                or self.toolbar_FIBSEM._active == "PAN"
            ):
                return

        if event.button == 1 and event.dblclick:
            x, y = piescope_gui.utils.pixel_to_realspace_coordinate(
                [event.xdata, event.ydata], image, pixel_size
            )

            from autoscript_sdb_microscope_client.structures import StagePosition

            x_move = StagePosition(x=x, y=0, z=0)
            y_move = StagePosition(x=0, y=y, z=0)
            # TODO: Test out on FIB when working
            yz_move = piescope.fibsem.y_corrected_stage_movement(
                y,
                stage_tilt=self.microscope.specimen.stage.current_position.t,
                settings=self.config,
            )

            if self.config["imaging"]["ib"]["pretilt"] != 0:
                y_move = yz_move

            self.microscope.specimen.stage.relative_move(x_move)
            self.microscope.specimen.stage.relative_move(y_move)

            if modality == Modality.Light:
                self.fluorescence_image(
                    laser=self.laser_controller.current_laser, settings=self.config
                )
                self.update_display(modality=Modality.Light, settings=self.config)
            else:
                self.get_FIB_image(autosave=False)
                self.update_display(modality=Modality.Ion, settings=self.config)

    def fill_destination(self, modality):
        """Fills the destination box with the text from the directory"""
        try:
            user_input = QtWidgets.QFileDialog.getExistingDirectory(
                self, "File Destination"
            )
            if user_input == "":
                directory_path = self.DEFAULT_PATH
            else:
                directory_path = os.path.normpath(user_input) + os.path.sep

            if modality == "FM":
                self.save_destination_FM = directory_path
                self.lineEdit_save_destination_FM.setText(directory_path)
                return directory_path
            elif modality == "FIBSEM":
                if not self.checkBox_save_destination_FIBSEM.isChecked():
                    self.save_destination_FIBSEM = directory_path
                    self.lineEdit_save_destination_FIBSEM.setText(directory_path)
                    return directory_path
            elif modality == "correlation":
                self.save_destination_correlation = directory_path
                self.correlation_output_path.setText(directory_path)
                return directory_path
        except Exception as e:
            display_error_message(traceback.format_exc())

    # def check_volume_imaging_settings(self):

    def acquire_volume(self, imaging_mode: ImagingType = ImagingType.WIDEFIELD):

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
                display_error_message("Volume height must be a positive integer")
                return

        # make sure z_slice_distance is a positive integer
        try:
            z_slice_distance = int(self.lineEdit_slice_distance.text())
        except ValueError:
            display_error_message("Slice distance must be a positive integer")
            return
        else:
            if z_slice_distance <= 0:
                display_error_message("Slice distance must be a positive integer")
                return
        num_z_slices = int(round(volume_height / z_slice_distance) + 1)

        volume = piescope.lm.volume.acquire_volume(
            num_z_slices=num_z_slices,
            z_slice_distance=z_slice_distance,
            imaging_mode=imaging_mode,
            laser_controller=self.laser_controller,
            mirror_controller=self.mirror_controller,
            objective_stage=self.objective_stage,
            detector=self.detector,
            arduino=self.arduino,
            settings=self.config,
        )
        print("VOLUME: ", volume.shape)

        meta = {
            "z_slice_distance": str(z_slice_distance),
            "num_z_slices": str(num_z_slices),
            "laser_dict": str(self.laser_controller.lasers),
            "volume_height": str(volume_height),
        }

        max_intensity = piescope.utils.max_intensity_projection(volume)
        print("MAX INTENSITY", max_intensity.shape)

        colour_dict = []
        for laser in self.laser_controller.lasers.values():
            if laser.volume_enabled:
                colour_dict.append(laser.colour)

        print(colour_dict)

        rgb = piescope.utils.rgb_image(max_intensity, colour_dict=colour_dict)
        self.image_light = rgb

        if self.config["imaging"]["volume"]["autosave"]:
            # save full volume
            save_filename = os.path.join(
                self.save_destination_FM,
                "Volume_" + self.lineEdit_save_filename_FM.text() + ".tif",
            )
            piescope.utils.save_image(volume, save_filename, metadata=meta)
            print("Saved: {}".format(save_filename))

            # Save maximum intensity projection
            save_filename_max_intensity = os.path.join(
                self.save_destination_FM,
                "MIP_" + self.lineEdit_save_filename_FM.text() + ".tif",
            )
            piescope.utils.save_image(
                max_intensity, save_filename_max_intensity, metadata=meta
            )
            print("Saved: {}".format(save_filename_max_intensity))

            # Save maximum intensity rgb
            save_filename_rgb = os.path.join(
                self.save_destination_FM,
                "RGB_" + self.lineEdit_save_filename_FM.text() + ".tif",
            )
            piescope.utils.save_image(rgb, save_filename_rgb, metadata=meta)
            print("Saved: {}".format(save_filename_rgb))

        # Update display
        self.update_display(modality=Modality.Light, settings=self.config)

    def correlateim(self):
        tempfile = "C:"
        try:
            fluorescence_image = self.image_light

            if fluorescence_image == [] or fluorescence_image == "":
                raise ValueError("No first image selected")
            fibsem_image = self.image_ion
            if fibsem_image == [] or fibsem_image == "":
                raise ValueError("No second image selected")

            output_filename = self.correlation_output_path.text()
            if output_filename == "":
                raise ValueError("No path selected")
            if not os.path.isdir(output_filename):
                raise ValueError("Please select a valid directory")

            image_ext = os.path.sep + "correlated_image_" + timestamp()
            copy_count = 1

            while os.path.isfile(
                output_filename + image_ext + "_" + str(copy_count) + ".tiff"
            ):
                copy_count = copy_count + 1

            tempfile = (
                output_filename + image_ext + "_" + str(copy_count) + "temp_.tiff"
            )
            open(tempfile, "w+")

            output_filename = (
                output_filename + image_ext + "_" + str(copy_count) + ".tiff"
            )

            window = corr.open_correlation_window(
                self, fluorescence_image, fibsem_image, output_filename
            )
            window.showMaximized()
            window.show()

            window.exitButton.clicked.connect(
                lambda: self.mill_window_from_correlation(window)
            )

            if os.path.isfile(tempfile):
                os.remove(tempfile)

        except Exception as e:
            if os.path.isfile(tempfile):
                os.remove(tempfile)
            display_error_message(traceback.format_exc())

    def mill_window_from_correlation(self, window):
        aligned_image = window.menu_quit()
        try:
            piescope_gui.milling.open_milling_window(
                self, aligned_image, self.image_ion
            )
        except Exception:
            display_error_message(traceback.format_exc())

    def milling(self):
        try:

            filename, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Open Milling Image", filter="Images (*.bmp *.tif *.tiff *.jpg)"
            )

            adorned_image = piescope.utils.load_image(filename)

            piescope_gui.milling.open_milling_window(
                self, adorned_image.data, adorned_image
            )

        except Exception as e:
            display_error_message(traceback.format_exc())


def main():
    """Launch the `piescope_gui` main application window."""
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    app.aboutToQuit.connect(qt_app.disconnect)  # cleanup & teardown
    qt_app.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
