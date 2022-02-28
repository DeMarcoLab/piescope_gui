from ast import Mod
import copy
from distutils.command.config import config
import logging
import os
import sys
import threading
import time
import traceback

import numpy as np
import piescope
import piescope.data
import piescope.fibsem
import piescope.lm
import piescope.utils
import qimage2ndarray
import scipy.ndimage as ndi
import skimage.color
import skimage.io
import skimage.util
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as _FigureCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as _NavigationToolbar
from piescope.lm import arduino, mirror, structured
from piescope.lm.detector import Basler
from piescope.lm.laser import Laser, LaserController
from piescope.lm.mirror import ImagingType, StagePosition
from piescope.utils import Modality, TriggerMode
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib import pyplot as plt

import piescope_gui.correlation.main as corr
import piescope_gui.milling
import piescope_gui.qtdesigner_files.main as gui_main
from piescope_gui.utils import display_error_message, timestamp

# TODO: Slider as double
# TODO: Movement using qimage


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()

        # read config file
        config_path = os.path.join(
            os.path.dirname(piescope.__file__), "config.yml")
        self.config = piescope.utils.read_config(config_path)

        # set ip_address and online status
        self.ip_address = self.config["system"]["ip_address"]
        self.online = self.config["system"]["online"]
        self.trigger_mode = self.config['imaging']['lm']['trigger_mode']
        self.live_imaging_running = False

        # TODO: improve debugging
        # set up logging
        self.logger = logging.getLogger(__name__)
        if self.online:
            logging.basicConfig(level=logging.WARNING)
        else:
            logging.basicConfig(level=logging.DEBUG)

        # set up UI
        self.setupUi(self)
        self.setWindowTitle("PIEScope User Interface Main Window")

        self.setup_connections()

        # setup hardware
        self.microscope = None
        self.laser_controller = None

        self.detector = None
        self.mirror_controller = None
        self.arduino = None
        self.objective_stage = None
        self.initialise_hardware(online=self.online)

        # TODO: remove this if possible (used in milling window)
        self.image_ion = None  # ion beam image (AdornedImage type)

        # Set up GUI variables

        self.DEFAULT_PATH = os.path.normpath(
            os.path.expanduser("~/Pictures/PIESCOPE"))
        self.save_destination_FM = self.DEFAULT_PATH
        self.save_destination_FIBSEM = self.DEFAULT_PATH
        self.save_destination_correlation = self.DEFAULT_PATH

        self.lineEdit_save_filename_FM.setText("Image")
        self.lineEdit_save_destination_FM.setText(self.DEFAULT_PATH)

        self.lineEdit_save_filename_FIBSEM.setText("Image")
        self.lineEdit_save_destination_FIBSEM.setText(self.DEFAULT_PATH)

        self.correlation_output_path.setText(self.DEFAULT_PATH)

        self.label_objective_stage_position.setText("Unknown")
        self.comboBox_resolution.setCurrentIndex(1)  # resolution "1536x1024"

        # colour scaling dict for 4-channel RGB display
        self.colour_dict = {
            "laser640": (148 / 255, 43 / 255, 35 / 255),
            "laser561": (255 / 255, 143 / 255, 51 / 255),
            "laser488": (0 / 255, 255 / 255, 0 / 255),
            "laser405": (0 / 255, 0 / 255, 255 / 255),
        }

        # self.liveCheck is True when ready to start live imaging,
        # and False while live imaging is running:
        self.liveCheck = True

        # self.laser_dict is a dictionary like: {"name": (power, exposure)}
        # with types {str: (int, int)}
        # Could refactor this out and rely only on self.lasers instead
        self.current_laser_wavelength = "488nm"
        self.current_laser_power = 0
        self.current_laser_exposure = 1e6

        self.laser_dict = {}  # {"name": (power, exposure)}
        self.image_ion = (
            []
        )  # AdornedImage (for whatever is currently displayed in the FIBSEM side of the piescope GUI)
        self.image_light = (
            []
        )  # list of 2D numpy arrays (how we open many images & use the slider for fluorescence images)
        self.image_ion = []  # TODO: REMOVE # list of AdornedImages ? probably ?
        # TODO: should be None, not an empty list to start with. PixMap object (pyqt)
        self.current_pixmap_FM = None
        # TODO: should be None, not an empty list to start with. PixMap object (pyqt)
        self.current_pixmap_FIBSEM = None

        self.pin_640 = "P03"
        self.pin_561 = "P02"
        self.pin_488 = "P01"
        self.pin_405 = "P00"

        self.pins = [self.pin_640, self.pin_561, self.pin_488, self.pin_405]

        if self.online:
            structured.single_line_onoff(onoff=False, pin=self.pin_640)
            structured.single_line_onoff(onoff=False, pin=self.pin_561)
            structured.single_line_onoff(onoff=False, pin=self.pin_488)
            structured.single_line_onoff(onoff=False, pin=self.pin_405)
            structured.single_line_onoff(onoff=False, pin="P04")
            # PO4 IS OBJECTIVE READY PIN

        # structured.single_line_onoff(onoff=False, pin='P13')
        # structured.single_line_onoff(onoff=False, pin='P27')
        # TODO: make laser_to_pin in detector.py consistent with this so defined in one place, protocol?
        # TODO: same with camera pin

        # set up imaging frames
        self.figure_FM = None
        self.figure_FIBSEM = None
        self.initialise_image_frames()

    def initialise_hardware(self, online=False):
        self.connect_to_fibsem_microscope(ip_address=self.ip_address)
        if online:
            self.detector = Basler(settings=self.config)
            self.laser_controller = LaserController(settings=self.config)
            self.mirror_controller = mirror.PIController()
            self.arduino = arduino.Arduino()
            self.objective_stage = self.initialise_objective_stage()

    # TODO: hardware dependent connections

    def setup_connections(self):

        self.actionOpen_FM_Image.triggered.connect(
            lambda: self.open_images(Modality.Light))
        self.actionOpen_FIBSEM_Image.triggered.connect(
            lambda: self.open_images(Modality.Ion)
        )

        self.actionSave_FM_Image.triggered.connect(
            lambda: self.save_image("FM"))
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
            lambda: self.update_display(modality=Modality.Light, settings=self.config
                                        )
        )

        self.pushButton_load_FM.clicked.connect(
            lambda: self.open_images(Modality.Light))
        self.pushButton_load_FIBSEM.clicked.connect(
            lambda: self.open_images(Modality.Ion))

        self.pushButton_save_FM.clicked.connect(lambda: self.save_image('FM'))
        self.pushButton_save_FIBSEM.clicked.connect(
            lambda: self.save_image('FIBSEM'))

        if self.online:

            self.comboBox_resolution.currentTextChanged.connect(
                lambda: self.update_fibsem_settings()
            )
            self.lineEdit_dwell_time.textChanged.connect(
                lambda: self.update_fibsem_settings()
            )

            self.checkBox_laser1.clicked.connect(lambda: self.update_volume_lasers(
                laser_name="laser640", enabled=self.checkBox_laser1.isChecked()))
            self.checkBox_laser2.clicked.connect(lambda: self.update_volume_lasers(
                laser_name="laser561", enabled=self.checkBox_laser2.isChecked()))
            self.checkBox_laser3.clicked.connect(lambda: self.update_volume_lasers(
                laser_name="laser488", enabled=self.checkBox_laser3.isChecked()))
            self.checkBox_laser4.clicked.connect(lambda: self.update_volume_lasers(
                laser_name="laser405", enabled=self.checkBox_laser4.isChecked()))

            self.slider_laser1.valueChanged.connect(
                lambda: self.update_laser_dict("laser640")
            )
            self.slider_laser2.valueChanged.connect(
                lambda: self.update_laser_dict("laser561")
            )
            self.slider_laser3.valueChanged.connect(
                lambda: self.update_laser_dict("laser488")
            )
            self.slider_laser4.valueChanged.connect(
                lambda: self.update_laser_dict("laser405")
            )

            self.spinBox_laser1.valueChanged.connect(
                lambda: self.update_laser_dict("laser640")
            )
            self.spinBox_laser2.valueChanged.connect(
                lambda: self.update_laser_dict("laser561")
            )
            self.spinBox_laser3.valueChanged.connect(
                lambda: self.update_laser_dict("laser488")
            )
            self.spinBox_laser4.valueChanged.connect(
                lambda: self.update_laser_dict("laser405")
            )

            self.lineEdit_exposure_1.textChanged.connect(
                lambda: self.update_laser_dict("laser640")
            )
            self.lineEdit_exposure_2.textChanged.connect(
                lambda: self.update_laser_dict("laser561")
            )
            self.lineEdit_exposure_3.textChanged.connect(
                lambda: self.update_laser_dict("laser488")
            )
            self.lineEdit_exposure_4.textChanged.connect(
                lambda: self.update_laser_dict("laser405")
            )

            self.button_get_image_FIB.clicked.connect(
                lambda: self.get_FIB_image())
            self.button_get_image_SEM.clicked.connect(
                lambda: self.get_SEM_image())
            self.button_last_image_FIB.clicked.connect(
                lambda: self.get_last_FIB_image())
            self.button_last_image_SEM.clicked.connect(
                lambda: self.get_last_SEM_image())

            self.buttonGroup.buttonClicked.connect(
                lambda: self.update_current_laser(
                    self.buttonGroup.checkedButton().objectName()
                )
            )

            self.button_get_image_FM.clicked.connect(
                lambda: self.fluorescence_image(
                    laser=self.laser_controller.current_laser,
                    settings=self.config,
                )
            )
            self.button_live_image_FM.clicked.connect(
                lambda: self.fluorescence_live_imaging(
                    self.laser_controller.current_laser,
                )
            )

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
                lambda: self.connect_to_fibsem_microscope(
                    ip_address=self.ip_address)
            )
            self.to_light_microscope.clicked.connect(
                lambda: self.move_to_light_microscope()
            )
            self.to_electron_microscope.clicked.connect(
                lambda: self.move_to_electron_microscope()
            )

            self.pushButton_volume.clicked.connect(
                lambda: self.acquire_volume(
                    imaging_mode=self.mirror_controller.get_mode())
            )
            self.pushButton_correlation.clicked.connect(
                lambda: self.correlateim())
            self.pushButton_milling.clicked.connect(lambda: self.milling())

            self.pushButton_get_position.clicked.connect(
                self.objective_stage_position)
            self.pushButton_save_objective_position.clicked.connect(
                self.save_objective_stage_position
            )
            self.pushButton_go_to_saved_position.clicked.connect(
                lambda: self.move_absolute_objective_stage(
                    self.objective_stage)
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
        plt.axis('off')
        plt.tight_layout()
        plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.01)
        self.canvas_FM = _FigureCanvas(self.figure_FM)
        self.toolbar_FM = _NavigationToolbar(self.canvas_FM, self)

        self.label_image_FM.setLayout(QtWidgets.QVBoxLayout())
        self.label_image_FM.layout().addWidget(self.toolbar_FM)
        self.label_image_FM.layout().addWidget(self.canvas_FM)

        self.figure_FIBSEM = plt.figure()
        plt.axis('off')
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
            self.move_absolute_objective_stage(
                self.objective_stage, position=-1000)
            self.objective_stage.disconnect()
        if self.microscope is not None:
            self.microscope.disconnect()

    ############## FIBSEM microscope methods ##############
    def connect_to_fibsem_microscope(self, ip_address="10.0.0.1"):
        """Connect to the FIBSEM microscope."""
        try:
            from piescope import fibsem

            self.microscope = piescope.fibsem.initialise(ip_address=ip_address)
            self.camera_settings = self.update_fibsem_settings()
        except Exception as e:
            display_error_message(traceback.format_exc())

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
            display_error_message(traceback.format_exc())

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
            self.image_ion = piescope.fibsem.last_electron_image(
                self.microscope)
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
        else:
            self.image_ion = copy.deepcopy(self.image_ion)
            return self.image_ion

    def fluorescence_image(
        self,
        laser: Laser,
        settings: dict,
    ):
        if self.laser_controller is None:
            display_error_message('Not connect to lasers')
            return

        # check if live imaging is possible
        # TODO: add self.live_imaging_running checks for other actions (volume etc)
        if self.live_imaging_running:
            self.button_live_image_FM.setDown(True)
            print("Can't take image, live imaging currently running")
            return

        # manually turn on laser if software mode
        if settings['imaging']['lm']['trigger_mode'] == TriggerMode.Software:
            self.laser_controller.emission_on(laser)

        image = self.detector.camera_grab(
            laser=laser,
            settings=settings
        )

        # manually turn off laser if software mode
        if settings['imaging']['lm']['trigger_mode'] == TriggerMode.Software:
            self.laser_controller.emission_off(laser)

        metadata = {
            "exposure_time": str(laser.exposure_time),
            "laser_name": str(laser.name),
            "laser_power": str(laser.power),
            "timestamp": timestamp(),
        }

        # save image
        if settings["imaging"]["lm"]['autosave'] is True:
            save_filename = os.path.join(self.save_destination_FM,
                                         "F_" + self.lineEdit_save_filename_FM.text() + ".tif",
                                         )
            piescope.utils.save_image(image, save_filename, metadata=metadata)
            self.logger.log(logging.DEBUG, "Saved: {}".format(save_filename))

        self.image_light = image

        self.update_display(modality=Modality.Light, settings=self.config)

    # ############## Fluorescence detector methods ##############
        # from old RGB - probably shows how do it well
        #     # normalisation from 0-255 -> 0-1
        #     stack_rgb = stack_rgb / 255  # for weighting
        #
        # elif color == "rgb":
        #     stack_rgb = stack_mip
        #
        # else:
        #     print('Invalid display colour')
        #     return
        #
        # #TODO: remove self.image_lm?  Or at least make consistent with FM
        # self.image_light = stack_rgb
        #
        # save_filename = os.path.join(
        #     self.save_destination_FM,
        #     'F_' + self.lineEdit_save_filename_FM.text() + '.tif')
        # self.string_list_FM = [save_filename]
        # self.slider_stack_FM.setValue(1)
        # self.update_display(modality=Modality.Light, settings=self.config)
        # self.lm_metadata = {'laser_dict': str(laser_dict),
        #                     'timestamp': timestamp()}
        # # if autosave is True:
        # #     piescope.utils.save_image(image, save_filename, metadata=self.lm_metadata)
        # #     print("Saved: {}".format(save_filename))
        # # Update GUI
        #
        # # return unaltered stack for volume/saving purposes
        # # shape: (Channels, Patterns, X, Y)
        # return stack

    def live_imaging_worker(self, laser: Laser, stop_event: threading.Event, settings: dict):
        self.live_imaging_running = True
        self.button_live_image_FM.setDown(True)

        while not stop_event.isSet():
            if settings['imaging']['lm']['trigger_mode'] == TriggerMode.Software:
                self.laser_controller.emission_on(laser)
            self.image_light = self.detector.camera_grab(laser=laser, settings=self.config
                                                         )
            if settings['imaging']['lm']['trigger_mode'] == TriggerMode.Software:
                self.laser_controller.emission_off(laser)

            self.update_display(modality=Modality.Light, settings=self.config)

            if settings['imaging']['lm']['camera']['image_frame_interval'] is not None:
                stop_event.wait(settings['imaging']['lm']
                                ['camera']['image_frame_interval'])

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
                    args=(laser,
                          self.stop_event,
                          config
                          ),
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
            logging.warning("The objective lens stage is already initizliaed.")
            return self.objective_stage
        else:
            try:
                stage = piescope.lm.objective.StageController(testing=testing)
                self.objective_stage = stage
                stage.initialise_system_parameters()
            except Exception as e:
                display_error_message(traceback.format_exc())
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
            self.label_objective_stage_position.setText(
                str(float(new_position) / 1000))
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

    def update_laser_dict(self, laser: Laser):
        self.logger.debug("Updating laser dictionary")
        try:
            # laser_selected, laser_power, exposure_time, widget_spinbox, widget_slider, widget_textexposure
            LASER_INFO = {
                "laser640": [
                    self.spinBox_laser1,
                    self.lineEdit_exposure_1,
                ],
                "laser561": [
                    self.spinBox_laser2,
                    self.lineEdit_exposure_2,
                ],
                "laser488": [
                    self.spinBox_laser3,
                    self.lineEdit_exposure_3,
                ],
                "laser405": [
                    self.spinBox_laser4,
                    self.lineEdit_exposure_4,
                ],
            }

            laser_power = float(LASER_INFO[laser][0].text())
            exposure_time = float(
                LASER_INFO[laser][1].text()) * 1000  # ms -> us

            # Update current laser for single/live imaging and sttings
            self.update_current_laser(
                self.buttonGroup.checkedButton().objectName())
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
                    dir_exists = os.path.isdir(
                        self.lineEdit_save_destination_FM.text())
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
                        os.makedirs(
                            self.lineEdit_save_destination_FIBSEM.text())
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

            # if the image is 3 dimensional, it is probably and RGB of shape (XYC)
            if image.ndim == 3:
                # if the final dimension of the image is not RGB, shape might be (CXY)
                if image.shape[-1] != 3:
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

            # make a copy of the rgb to display with crosshair
            # TODO: move this later in the process
            crosshair = piescope.utils.create_crosshair(
                self.image_light, self.config)

            # TODO: can this be moved to after all image modifications (probably)
            plt.axis('off')
            if self.canvas_FM:
                self.label_image_FM.layout().removeWidget(self.canvas_FM)
                self.canvas_FM.deleteLater()
            self.canvas_FM = _FigureCanvas(self.figure_FM)

            self.canvas_FM.mpl_connect('button_press_event', lambda event: self.on_gui_click(
                event, modality=Modality.Light))

            if settings['imaging']['lm']['filter_strength'] > 0:
                image = ndi.median_filter(image, size=int(
                    settings['imaging']['lm']['filter_strength']))

            # after modifications, if any, convert to rgb image
            self.image_light = skimage.util.img_as_ubyte(
                piescope.utils.rgb_image(image)
            )

            self.figure_FM.clear()
            self.figure_FM.patch.set_facecolor((240/255, 240/255, 240/255))
            ax_FM = self.figure_FM.add_subplot(111)
            ax_FM.set_title('Light Microscope')
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
            # TODO: move this later in the process
            crosshair = piescope.utils.create_crosshair(
                self.image_ion, self.config)

            # TODO: can this be moved to after all image modifications (probably)
            plt.axis('off')
            if self.canvas_FIBSEM:
                self.label_image_FIBSEM.layout().removeWidget(self.canvas_FIBSEM)
                self.label_image_FIBSEM.layout().removeWidget(self.toolbar_FIBSEM)
                self.canvas_FIBSEM.deleteLater()
                self.toolbar_FIBSEM.deleteLater()
            self.canvas_FIBSEM = _FigureCanvas(self.figure_FIBSEM)

            self.canvas_FIBSEM.mpl_connect(
                'button_press_event', lambda event: self.on_gui_click(event, modality=Modality.Ion))

            if settings['imaging']['ib']['filter_strength'] > 0:
                image = ndi.median_filter(image, size=int(
                    settings['imaging']['ib']['filter_strength']))

            self.figure_FIBSEM.clear()
            self.figure_FIBSEM.patch.set_facecolor((240/255, 240/255, 240/255))
            ax_FIBSEM = self.figure_FIBSEM.add_subplot(111)
            ax_FIBSEM.set_title('FIBSEM')
            ax_FIBSEM.patches = []
            for patch in crosshair.__dataclass_fields__:
                ax_FIBSEM.add_patch(getattr(crosshair, patch))
            self.toolbar_FIBSEM = _NavigationToolbar(self.canvas_FIBSEM, self)
            self.label_image_FIBSEM.layout().addWidget(self.toolbar_FIBSEM)
            self.label_image_FIBSEM.layout().addWidget(self.canvas_FIBSEM)
            ax_FIBSEM.get_xaxis().set_visible(False)
            ax_FIBSEM.get_yaxis().set_visible(False)
            ax_FIBSEM.imshow(image, cmap='gray')
            self.canvas_FIBSEM.draw()

    # TODO: reorder functions to make more sense
    def on_gui_click(self, event, modality):
        # don't allow double click functionality while zooming or panning, only stopping active window
        if modality == Modality.Light:
            image = self.image_light
            pixel_size = self.config['imaging']['lm']['camera']['pixel_size']
            if self.toolbar_FM._active == 'ZOOM' or self.toolbar_FM._active == 'PAN':
                return
        else:
            image = self.image_ion
            pixel_size = image.metadata.binary_result.pixel_size.x
            if self.toolbar_FIBSEM._active == 'ZOOM' or self.toolbar_FIBSEM._active == 'PAN':
                return

        if event.button == 1 and event.dblclick:
            x, y = piescope_gui.utils.pixel_to_realspace_coordinate(
                [event.xdata, event.ydata], image, pixel_size)

            from autoscript_sdb_microscope_client.structures import StagePosition
            x_move = StagePosition(x=x, y=0, z=0)
            y_move = StagePosition(x=0, y=y, z=0)
            #TODO: CHECK
            yz_move = piescope.fibsem.y_corrected_stage_movement(
                y,
                stage_tilt=self.microscope.specimen.stage.current_position.t,
                settings=self.config)

            if self.config['imaging']['ib']['pretilt'] != 0:
                y_move = yz_move

            self.microscope.specimen.stage.relative_move(x_move)
            self.microscope.specimen.stage.relative_move(y_move)

            if modality == Modality.Light:
                self.fluorescence_image(
                    laser=self.laser_controller.current_laser, settings=self.config)
                self.update_display(modality=Modality.Light,
                                    settings=self.config)
            else:
                self.get_FIB_image(autosave=False)
                self.update_display(modality=Modality.Ion,
                                    settings=self.config)

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
                    self.lineEdit_save_destination_FIBSEM.setText(
                        directory_path)
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
            display_error_message('No detector available')
            return
        if self.laser_controller is None:
            display_error_message('No laser controller connected')
            return
        if self.laser_controller.lasers is None:
            display_error_message('No lasers found for laser controller')
            return
        if self.objective_stage is None:
            display_error_message('Objective stage is not connected')
            return
        if self.mirror_controller is None:
            display_error_message('Mirror controller is not connected.')
            return

        # TODO: helper function
        # make sure volume_height is a positive integer
        try:
            volume_height = int(self.lineEdit_volume_height.text())
        except ValueError:
            display_error_message(
                "Volume height must be a positive integer")
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
            display_error_message(
                "Slice distance must be a positive integer")
            return
        else:
            if z_slice_distance <= 0:
                display_error_message(
                    "Slice distance must be a positive integer")
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
            settings=self.config
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
        if self.config['imaging']['volume']['autosave']:
            save_filename = os.path.join(
                self.save_destination_FM,
                "Volume_" + self.lineEdit_save_filename_FM.text() + ".tif",)
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
            # Update display
            rgb = piescope.utils.rgb_image(max_intensity)
            self.image_light = rgb
            self.update_display(modality=Modality.Light, settings=self.config)

    def acquire_volume2(self, mode=ImagingType.WIDEFIELD, autosave=True):
        print("Acquiring fluorescence volume image...")
        try:  # TODO: shorten the amount of calls under the try, or at least split

            # laser_dict = self.laser_dict
            # if laser_dict == {}:
            #     display_error_message("Please select up to four lasers.")
            #     return
            # if len(laser_dict) > 4:
            #     display_error_message("Please select a maximum of 4 lasers.")
            #     return

            # try:
            #     volume_height = int(self.lineEdit_volume_height.text())
            # except ValueError:
            #     display_error_message(
            #         "Volume height must be a positive integer")
            #     return
            # else:
            #     if volume_height <= 0:
            #         display_error_message(
            #             "Volume height must be a positive integer")
            #         return

            # try:
            #     z_slice_distance = int(self.lineEdit_slice_distance.text())
            # except ValueError:
            #     display_error_message(
            #         "Slice distance must be a positive integer")
            #     return
            # else:
            #     if z_slice_distance <= 0:
            #         display_error_message(
            #             "Slice distance must be a positive integer")
            #         return
            # num_z_slices = round(volume_height / z_slice_distance) + 1

            if mode == ImagingType.WIDEFIELD:
                mode = "widefield"
            else:
                mode = "sim"

            volume = piescope.lm.volume.volume_acquisition(
                self.laser_dict,
                num_z_slices,
                z_slice_distance,
                mode=mode,
                detector=self.detector,
                lasers=self.lasers,
                objective_stage=self.objective_stage,
                mirror_controller=self.mirror_controller,
                arduino=self.arduino,
                laser_pins=self.pins,
            )
            meta = {
                "z_slice_distance": str(z_slice_distance),
                "num_z_slices": str(num_z_slices),
                "laser_dict": str(laser_dict),
                "volume_height": str(volume_height),
            }
            max_intensity = piescope.utils.max_intensity_projection(volume)
            if autosave is True:
                # # from old ssaving of MIP, RAW, RGB, might be useful
                # reconstruct = 0
                # raw = 0
                # mip = 0
                #
                # # RAW - (ZMipYX)
                # if raw == 1:
                #     volume_mip = np.copy(volume)
                #     if volume_mip.ndim == 6:
                #         # piescope.utils.max_intensity_projection(volume_mip, )
                #         for channel, (
                #                 laser_name, (laser_power, exposure_time)) in enumerate(
                #             laser_dict.items()):
                #             max_intensity = np.max(volume_mip[channel],
                #                                    axis=(0, 2))
                #             save_filename = (
                #                     self.lineEdit_save_destination_FM +
                #                     'Raw_' + str(
                #                 laser_name) + '_' + self.lineEdit_save_filename_FM.text() + '.tif')
                #             piescope.utils.save_image(max_intensity,
                #                                       save_filename,
                #                                       metadata=meta)  # ZMipYX
                #             print('Saved: {}'.format(save_filename))
                #
                # # MIP (CAZPYX)
                # if mip == 1:
                #     volume_mip = np.copy(volume)
                #     if volume_mip.ndim == 6:
                #         # piescope.utils.max_intensity_projection(volume_mip, )
                #         for channel, (
                #                 laser_name, (laser_power, exposure_time)) in enumerate(
                #             laser_dict.items()):
                #             max_intensity = np.max(volume_mip[channel],
                #                                    axis=(0, 2))
                #             save_filename = (
                #                     self.lineEdit_save_destination_FM +
                #                     'Raw_' + str(
                #                 laser_name) + '_' + self.lineEdit_save_filename_FM.text() + '.tif')
                #             piescope.utils.save_image(max_intensity,
                #                                       save_filename,
                #                                       metadata=meta)  # ZMipYX
                #             print('Saved: {}'.format(save_filename))
                #
                # # Save volume by colour as (AZP[YX])
                # if reconstruct == 1:
                #     for channel, (
                #             laser_name, (laser_power, exposure_time)) in enumerate(
                #         laser_dict.items()):
                #         save_filename = (self.lineEdit_save_destination_FM +
                #                          'Volume_' + str(
                #                     laser_name) + '_' + self.lineEdit_save_filename_FM.text() + '.tif')
                #         save_volume = np.copy(
                #             volume[channel[0], :, :, :, :, :])
                #         laser_meta = {'laser': str(laser_name)}
                #         meta.update(laser_meta)
                #         piescope.utils.save_image(save_volume, save_filename,
                #                                   metadata=meta)
                #         print('Saved: {}'.format(save_filename))

                # Save volume
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
            # Update display
            rgb = piescope.utils.rgb_image(max_intensity)
            self.image_light = rgb
            self.update_display(modality=Modality.Light, settings=self.config)
        except Exception as e:
            display_error_message(traceback.format_exc())

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
                output_filename + image_ext + "_" +
                str(copy_count) + "temp_.tiff"
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


def _create_array_list(
    input_list, modality
):  # TODO: remove this, array_list no longer required
    if modality == "FM":
        if len(input_list) > 1:
            array_list_FM = skimage.io.imread_collection(
                input_list, conserve_memory=True
            )
        else:
            array_list_FM = skimage.io.imread(input_list[0])
        return array_list_FM
    elif modality == "FIBSEM":
        if len(input_list) > 1:
            array_list_FIBSEM = skimage.io.imread_collection(input_list)
        else:
            array_list_FIBSEM = skimage.io.imread(input_list[0])
        return array_list_FIBSEM
    elif modality == "MILLING":
        if len(input_list) > 1:
            array_list_MILLING = skimage.io.imread_collection(input_list)
        else:
            array_list_MILLING = skimage.io.imread(input_list[0])
        return array_list_MILLING


def main():
    """Launch the `piescope_gui` main application window."""
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    app.aboutToQuit.connect(qt_app.disconnect)  # cleanup & teardown
    qt_app.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
