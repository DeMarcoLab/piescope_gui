import copy
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
from piescope.lm import arduino, mirror, structured
from piescope.lm.mirror import StageMode, StagePosition
from PyQt5 import QtCore, QtGui, QtWidgets

import piescope_gui.correlation.main as corr
import piescope_gui.milling
import piescope_gui.qtdesigner_files.main as gui_main
from piescope_gui.utils import display_error_message, timestamp


# TODO: Zoom function for qimage
# TODO: Slider as double
# TODO: Movement using qimage


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()

        # read config file
        config_path = os.path.join(os.path.dirname(piescope.__file__), "config.yml")
        self.config = piescope.utils.read_config(config_path)

        # set ip_address and offline_mode
        self.ip_address = self.config["system"]["ip_address"]
        self.offline = self.config["system"]["offline_mode"]

        # TODO: improve debugging
        # set up logging
        self.logger = logging.getLogger(__name__)
        if self.offline:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)

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
        self.initialise_hardware(offline=self.offline)

        # TODO: remove this if possible (used in milling window)
        self.image_ion = None  # ion beam image (AdornedImage type)

        # Set up GUI variables

        self.DEFAULT_PATH = os.path.normpath(os.path.expanduser("~/Pictures/PIESCOPE"))
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
        self.fibsem_image = (
            []
        )  # AdornedImage (for whatever is currently displayed in the FIBSEM side of the piescope GUI)
        self.array_list_FM = (
            []
        )  # list of 2D numpy arrays (how we open many images & use the slider for fluorescence images)
        self.array_list_FIBSEM = []  # TODO: REMOVE # list of AdornedImages ? probably ?
        self.current_image_FM = (
            None  # TODO: REMOVE. David not sure why these are strings.
        )
        self.current_image_FIBSEM = (
            None  # TODO: REMOVE. David not sure why these are strings.
        )
        self.current_pixmap_FM = None  # TODO: should be None, not an empty list to start with. PixMap object (pyqt)
        self.current_pixmap_FIBSEM = None  # TODO: should be None, not an empty list to start with. PixMap object (pyqt)

        self.pin_640 = "P03"
        self.pin_561 = "P02"
        self.pin_488 = "P01"
        self.pin_405 = "P00"

        self.pins = [self.pin_640, self.pin_561, self.pin_488, self.pin_405]

        if not self.offline:
            structured.single_line_onoff(onoff=False, pin=self.pin_640)
            structured.single_line_onoff(onoff=False, pin=self.pin_561)
            structured.single_line_onoff(onoff=False, pin=self.pin_488)
            structured.single_line_onoff(onoff=False, pin=self.pin_405)
            structured.single_line_onoff(onoff=False, pin="P04")

        # structured.single_line_onoff(onoff=False, pin='P13')
        # structured.single_line_onoff(onoff=False, pin='P27')
        # TODO: make laser_to_pin in detector.py consistent with this so defined in one place, protocol?
        # TODO: same with camera pin

    def initialise_hardware(self, offline=True):
        if offline is False:
            self.mirror_controller = mirror.PIController()
            self.arduino = arduino.Arduino()
            self.connect_to_fibsem_microscope(ip_address=self.ip_address)
            self.objective_stage = self.initialise_objective_stage()
        self.detector = piescope.lm.detector.Basler()
        self.laser_controller = piescope.lm.laser.LaserController(
            settings=self.config
        )

    def setup_connections(self):


        self.comboBox_resolution.currentTextChanged.connect(
            lambda: self.update_fibsem_settings()
        )
        self.lineEdit_dwell_time.textChanged.connect(
            lambda: self.update_fibsem_settings()
        )

        self.actionOpen_FM_Image.triggered.connect(lambda: self.open_images("FM"))
        self.actionOpen_FIBSEM_Image.triggered.connect(
            lambda: self.open_images("FIBSEM")
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

        self.checkBox_laser1.clicked.connect(lambda: self.update_laser_dict("laser640"))
        self.checkBox_laser2.clicked.connect(lambda: self.update_laser_dict("laser561"))
        self.checkBox_laser3.clicked.connect(lambda: self.update_laser_dict("laser488"))
        self.checkBox_laser4.clicked.connect(lambda: self.update_laser_dict("laser405"))

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

        self.button_get_image_FIB.clicked.connect(lambda: self.get_FIB_image())
        self.button_get_image_SEM.clicked.connect(lambda: self.get_SEM_image())
        self.button_last_image_FIB.clicked.connect(lambda: self.get_last_FIB_image())
        self.button_last_image_SEM.clicked.connect(lambda: self.get_last_SEM_image())

        self.buttonGroup.buttonClicked.connect(
            lambda: self.update_current_laser(
                self.buttonGroup.checkedButton().objectName()
            )
        )

        self.button_get_image_FM.clicked.connect(
            lambda: self.fluorescence_image(
                self.current_laser_wavelength,
                self.current_laser_exposure,
                self.current_laser_power,
            )
        )
        self.button_live_image_FM.clicked.connect(
            lambda: self.fluorescence_live_imaging(
                self.current_laser_wavelength,
                self.current_laser_exposure,
                self.current_laser_power,
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
            lambda: self.connect_to_fibsem_microscope(ip_address=self.ip_address)
        )
        self.to_light_microscope.clicked.connect(
            lambda: self.move_to_light_microscope()
        )
        self.to_electron_microscope.clicked.connect(
            lambda: self.move_to_electron_microscope()
        )

        self.pushButton_volume.clicked.connect(
            lambda: self.acquire_volume(mode=self.mirror_controller.get_mode())
        )
        self.pushButton_correlation.clicked.connect(lambda: self.correlateim())
        self.pushButton_milling.clicked.connect(lambda: self.milling())

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
            lambda: self.mirror_controller.set_mode(StageMode.WIDEFIELD)
        )

        self.radioButton_SIM.clicked.connect(
            lambda: self.mirror_controller.move_to(StagePosition.SIXTY)
        )
        self.radioButton_SIM.clicked.connect(
            lambda: self.mirror_controller.set_mode(StageMode.SIM)
        )

        self.pushButton_pattern_next.clicked.connect(
            lambda: self.mirror_controller.next_position()
        )

    def disconnect(self):
        print("Running cleanup/teardown")
        logging.debug("Running cleanup/teardown")
        # Change values in qtdesigner_files\main.py
        if self.objective_stage is not None and self.offline is False:
            # Return objective lens stage to the "out" position and disconnect.
            self.move_absolute_objective_stage(self.objective_stage, position=-1000)
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
        if not self.microscope and not self.offline:
            self.connect_to_fibsem_microscope()
        try:
            from piescope import fibsem

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
                self.fibsem_image = self.autocontrast_ion_beam()
            else:
                self.fibsem_image = piescope.fibsem.new_ion_image(
                    self.microscope, self.camera_settings
                )
            # TODO: Do we really need skimage img_as_ubyte? Display only?
            self.array_list_FIBSEM = skimage.util.img_as_ubyte(self.fibsem_image.data)
            # save image
            save_filename = os.path.join(
                self.save_destination_FIBSEM,
                "I_" + self.lineEdit_save_filename_FIBSEM.text() + ".tif",
            )
            if autosave is True:
                piescope.utils.save_image(self.fibsem_image, save_filename)
                print("Saved: {}".format(save_filename))
            # Update display
            self.update_display("FIBSEM")
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            self.image_ion = copy.deepcopy(self.fibsem_image)
            return self.fibsem_image

    def get_last_FIB_image(self):
        try:
            self.fibsem_image = piescope.fibsem.last_ion_image(self.microscope)
            self.array_list_FIBSEM = skimage.util.img_as_ubyte(self.fibsem_image.data)
            self.update_display("FIBSEM")
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            self.image_ion = copy.deepcopy(self.fibsem_image)
            return self.fibsem_image

    def get_SEM_image(self, autosave=True):
        try:
            if self.checkBox_Autocontrast.isChecked():
                self.autocontrast_ion_beam(view=1)
            self.fibsem_image = piescope.fibsem.new_electron_image(
                self.microscope, self.camera_settings
            )
            # TODO: should this be copied? Should it be skimage img_as_ubyte?
            self.array_list_FIBSEM = np.copy(self.fibsem_image.data)
            # TODO: Inconsistent median filtering for display - should be in update_display('FIBSEM'), if anything.
            # Also consider correlation and milling window displays
            self.array_list_FIBSEM = ndi.median_filter(self.array_list_FIBSEM, 2)
            # save image
            save_filename = os.path.join(
                self.save_destination_FIBSEM,
                "E_" + self.lineEdit_save_filename_FIBSEM.text() + ".tif",
            )
            if autosave is True:
                piescope.utils.save_image(self.fibsem_image, save_filename)
                print("Saved: {}".format(save_filename))
            # update display
            self.update_display("FIBSEM")
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            # self.image_sem = copy.deepcopy(self.fibsem_image)
            return self.fibsem_image

    def get_last_SEM_image(self):
        try:
            self.fibsem_image = piescope.fibsem.last_electron_image(self.microscope)
            self.array_list_FIBSEM = self.fibsem_image.data
            self.array_list_FIBSEM = skimage.util.img_as_ubyte(self.array_list_FIBSEM)
            self.update_display("FIBSEM")
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            # self.image_sem = copy.deepcopy(self.fibsem_image)
            return self.fibsem_image

    def autocontrast_ion_beam(self, view=2):
        try:
            self.microscope.imaging.set_active_view(view)  # the ion beam view
            piescope.fibsem.autocontrast(self.microscope, view=view)
            self.fibsem_image = piescope.fibsem.last_ion_image(self.microscope)
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            self.image_ion = copy.deepcopy(self.fibsem_image)
            return self.fibsem_image

    ############## Fluorescence detector methods ##############
    def fluorescence_image(
        self,
        wavelength,
        exposure_time,
        laser_power,
        color="rgb",
        autosave=True,
        trigger_mode="hardware",
        livecheck=False,
    ):
        """Acquire a single fluorescence image, at a single wavelength..

        Parameters
        ----------
        wavelength : str
            Laser wavelength. Can be '640nm', '561nm', '488nm', or '405nm'.
        exposure_time : float (or string resolving to float)
            Exposure time in microseconds us
        laser_power : float
            Laser power to use in live imaging.
        autosave : bool, optional
            Whether to save images automatically, by default True

        Returns
        -------
        numpy ndarray
            Fluorescence image array.
        """

        # Checks
        if livecheck:
            if not self.liveCheck:
                print("Can't take image, live imaging currently running")
                return

        try:
            # Setup
            exposure_time_microseconds = float(exposure_time)  # us
            WAVELENGTH_TO_LASERNAME = {
                "640nm": "laser640",
                "561nm": "laser561",
                "488nm": "laser488",
                "405nm": "laser405",
            }
            laser_name = WAVELENGTH_TO_LASERNAME[wavelength]
            self.lasers[laser_name].laser_power = laser_power

            # Acquire image
            image = self.detector.camera_grab(
                exposure_time=exposure_time_microseconds,
                trigger_mode=trigger_mode,
                laser_name=laser_name,
                laser_pins=self.pins,
            )
            meta = {
                "exposure_time": str(exposure_time),
                "laser_name": str(laser_name),
                "laser_power": str(laser_power),
                "timestamp": timestamp(),
            }
            # self.lasers[laser_name].emission_off()

            # Save image
            save_filename = os.path.join(
                self.save_destination_FM,
                "F_" + self.lineEdit_save_filename_FM.text() + ".tif",
            )
            if autosave is True:
                piescope.utils.save_image(image, save_filename, metadata=meta)
                print("Saved: {}".format(save_filename))
            # Update GUI
            self.array_list_FM = image
            self.update_display("FM")
        except Exception as e:
            display_error_message(traceback.format_exc())
        else:
            print("Fluorescence image acquired.")
            return image

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
        # self.array_list_FM = stack_rgb
        #
        # save_filename = os.path.join(
        #     self.save_destination_FM,
        #     'F_' + self.lineEdit_save_filename_FM.text() + '.tif')
        # self.string_list_FM = [save_filename]
        # self.slider_stack_FM.setValue(1)
        # self.update_display("FM")
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

    def live_imaging_worker(
        self,
        stop_event,
        laser_name,
        laser_power,
        exposure_time,
        image_frame_interval=None,
    ):
        """Worker function for live imaging thread.

        Parameters
        ----------
        stop_event : threading.Event()
            Signal to terminate the thread.
        laser_name : str
            Name of laser to use in live imaging.
            Available values are "laser640", "laser561", "laser488", "laser405"
        laser_power : float
            Laser power to use in live imaging.
        exposure_time : float
            Exposure time, in microseconds (us).
        image_frame_interval : float, optional
            Waiting period between acquisition of live imaging frames.
            By default, None. This means live images will be acquired as fast
            as possible. Note the laser stays on even if imaging is paused.
        """
        # TODO: Can you allow changing which laser is on during live imaging?
        # Setup
        print("Live imaging mode running...")
        exposure_time_microseconds = float(exposure_time)  # us
        self.liveCheck = False
        self.button_live_image_FM.setDown(True)
        self.lasers[laser_name].laser_power = float(laser_power)
        # self.lasers[laser_name].emission_on()

        # Running live imaging
        while not stop_event.isSet():
            # Take image
            image = self.detector.camera_grab(
                exposure_time=exposure_time_microseconds,
                trigger_mode="hardware",
                laser_name=laser_name,
                laser_pins=self.pins,
            )
            # Update GUI
            self.array_list_FM = image
            self.update_display("FM")
            # Update filename (if you want to save this image later)
            save_filename = os.path.join(
                self.save_destination_FM,
                "F_" + self.lineEdit_save_filename_FM.text() + ".tif",
            )
            # Pause between frames if desired (the laser will remain on)
            if image_frame_interval is not None:
                stop_event.wait(image_frame_interval)
        # Teardown / cleanup
        print("Stopping live imaging mode.")
        # self.lasers[laser_name].emission_off()
        self.detector.camera.Close()
        self.liveCheck = True
        self.button_live_image_FM.setDown(False)

    def fluorescence_live_imaging(
        self, wavelength, exposure_time, laser_power, image_frame_interval=None
    ):
        """Fluorescence live imaging.

        Parameters
        ----------
        wavelength : str
            Which laser wavelength to use for live imaging.
            Available values are: "640nm", "561nm", "488nm", or "405nm".
        exposure_time : float
            Exposure time, in microseconds (us).
        laser_power : float
            Laser power to use for live imaging.
        image_frame_interval : float, optional
            Waiting period between acquisition of live imaging frames.
            By default, None. This means live images will be acquired as fast
            as possible. Note the laser stays on even if imaging is paused.
        """
        try:
            WAVELENGTH_TO_LASERNAME = {
                "640nm": "laser640",
                "561nm": "laser561",
                "488nm": "laser488",
                "405nm": "laser405",
            }
            laser_name = WAVELENGTH_TO_LASERNAME[wavelength]
            if self.liveCheck is True:
                self.stop_event = threading.Event()
                self._thread = threading.Thread(
                    target=self.live_imaging_worker,
                    args=(
                        self.stop_event,
                        laser_name,
                        laser_power,
                        exposure_time,  # in ms, converted to us in function
                        image_frame_interval,
                    ),
                )
                self._thread.start()
            else:
                self.stop_event.set()
        except (KeyboardInterrupt, SystemExit):
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
            self.logger.debug("Relative move the objective stage by " "{}".format(distance))
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
        LASER_BUTTON_TO_POWER = {'radioButton_640': ['laser640', self.spinBox_laser1, self.lineEdit_exposure_1],
                                'radioButton_561': ['laser561', self.spinBox_laser2, self.lineEdit_exposure_2],
                                'radioButton_488': ['laser488', self.spinBox_laser3, self.lineEdit_exposure_3],
                                'radioButton_405': ['laser405', self.spinBox_laser4, self.lineEdit_exposure_4]}

        try:
            selected_laser_info = LASER_BUTTON_TO_POWER[selected_button]
            laser_name = selected_laser_info[0]
            current_laser = self.laser_controller.lasers[laser_name]
            self.laser_controller.current_laser = current_laser
            self.laser_controller.set_laser_power(current_laser,  float(selected_laser_info[1].text()))
            self.laser_controller.set_exposure_time(current_laser,  float(selected_laser_info[2].text()) * 1000)
        except Exception as e:
            display_error_message(traceback.format_exc())


    def update_laser_dict(self, laser):
        self.logger.debug("Updating laser dictionary")
        try:
            assert laser == self.lasers[laser].NAME
            if laser == "laser640":
                laser_selected = self.checkBox_laser1.isChecked()
                laser_power = int(self.spinBox_laser1.text())
                exposure_time = int(self.lineEdit_exposure_1.text()) * 1000  # ms -> us
                widget_spinbox = self.spinBox_laser1
                widget_slider = self.slider_laser1
                widget_textexposure = self.lineEdit_exposure_1
            elif laser == "laser561":
                laser_selected = self.checkBox_laser2.isChecked()
                laser_power = int(self.spinBox_laser2.text())
                exposure_time = int(self.lineEdit_exposure_2.text()) * 1000  # ms -> us
                widget_spinbox = self.spinBox_laser2
                widget_slider = self.slider_laser2
                widget_textexposure = self.lineEdit_exposure_2
            elif laser == "laser488":
                laser_selected = self.checkBox_laser3.isChecked()
                laser_power = int(self.spinBox_laser3.text())
                exposure_time = int(self.lineEdit_exposure_3.text()) * 1000  # ms -> us
                widget_spinbox = self.spinBox_laser3
                widget_slider = self.slider_laser3
                widget_textexposure = self.lineEdit_exposure_3
            elif laser == "laser405":
                laser_selected = self.checkBox_laser4.isChecked()
                laser_power = int(self.spinBox_laser4.text())
                exposure_time = int(self.lineEdit_exposure_4.text()) * 1000  # ms -> us
                widget_spinbox = self.spinBox_laser4
                widget_slider = self.slider_laser4
                widget_textexposure = self.lineEdit_exposure_4
            else:
                raise ValueError("No Laser selected in laser_dict")
            # Update laser object attributes
            self.lasers[laser].selected = laser_selected
            self.lasers[laser].laser_power = laser_power
            self.lasers[laser].exposure_time = exposure_time
            laser_dict = {}
            for i in self.lasers.values():
                if i.selected is True:
                    laser_dict[i.NAME] = (i.laser_power, i.exposure_time)
            self.laser_dict = laser_dict
            self.logger.debug(self.laser_dict)

            print("This is the laser dict: ")
            print(self.laser_dict)

            # Update current laser for single/live imaging
            self.update_current_laser(self.buttonGroup.checkedButton().objectName())

            # Grey out laser contol widgets if laser checkbox is not selected
            if laser_selected:
                widget_slider.setEnabled(1)
                widget_textexposure.setEnabled(1)
                widget_spinbox.setEnabled(1)
            else:
                widget_slider.setEnabled(0)
                widget_textexposure.setEnabled(0)
                widget_spinbox.setEnabled(0)
        except Exception as e:
            display_error_message(traceback.format_exc())

    ############## Image methods ##############
    def open_images(self, modality):
        """Open image files and display the first"""
        try:
            if modality == "FM":
                [open_string, ext] = QtWidgets.QFileDialog.getOpenFileNames(
                    self, "Open File", filter="Images (*.bmp *.tif *.tiff *.jpg)"
                )

                if open_string:
                    self.array_list_FM = _create_array_list(open_string, "FM")
                    self.update_display("FM")

            elif modality == "FIBSEM":
                [path_string, ext] = QtWidgets.QFileDialog.getOpenFileNames(
                    self, "Open File", filter="Images (*.bmp *.tif *.tiff *.jpg)"
                )

                if path_string:
                    self.array_list_FIBSEM = _create_array_list(path_string, "FIBSEM")
                    self.update_display("FIBSEM")
        except Exception as e:
            display_error_message(traceback.format_exc())

    def save_image(self, modality):  # TODO: standardise image saving
        """Save image on display"""
        try:
            if modality == "FM":
                if self.current_image_FM is not None:
                    display_image = self.array_list_FM
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
                if self.current_image_FIBSEM is not None:
                    display_image = self.fibsem_image
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

    def update_display(self, modality):
        """Update the GUI display with the current image"""
        try:
            if modality == "FM":
                image_array = self.array_list_FM
                FM_max = image_array.max()
                self.label_max_FM_value.setText("Max value: " + str(FM_max))

                # Ensure image for display is RGB
                if image_array.ndim >= 4:
                    msg = (
                        "Please select a 2D image for display.\n"
                        + "Image shape here is {}".format(image_array.shape)
                    )
                    logging.warning(msg)
                    display_error_message(msg)
                    return
                elif image_array.ndim == 3:
                    shape = image_array.shape
                    if image_array.shape[-1] > 3:
                        image_array = np.moveaxis(image_array, 0, -1)
                    # After any swap axis...
                    if (
                        image_array.shape[-1] > 3
                    ):  # should be the channel axis, can't have more than RGB
                        msg = (
                            "Please select a 2D image with no more than 3 color channels for display.\n"
                            + "Image shape here is {}".format(image_array.shape)
                        )
                        logging.warning(msg)
                        display_error_message(msg)
                        return
                image_array = skimage.util.img_as_ubyte(
                    piescope.utils.rgb_image(image_array)
                )
                self.array_list_FM = image_array

                image_array_crosshair = np.copy(image_array)
                xshape = image_array_crosshair.shape[0]
                yshape = image_array_crosshair.shape[1]
                midx = int(xshape / 2)
                midy = int(yshape / 2)
                thresh = 2
                mult = 25
                image_array_crosshair[
                    midx - (thresh * mult) : midx + (thresh * mult),
                    midy - thresh : midy + thresh,
                ] = 255
                image_array_crosshair[
                    midx - thresh : midx + thresh,
                    midy - (thresh * mult) : midy + (thresh * mult),
                ] = 255

                self.current_image_FM = qimage2ndarray.array2qimage(image_array)
                self.current_image_FM_crosshair = qimage2ndarray.array2qimage(
                    image_array_crosshair.copy()
                )

                self.current_pixmap_FM = QtGui.QPixmap.fromImage(
                    self.current_image_FM_crosshair
                )
                self.current_pixmap_FM = self.current_pixmap_FM.scaled(
                    640, 400, QtCore.Qt.KeepAspectRatio
                )
                self.label_image_FM.setPixmap(self.current_pixmap_FM)

            elif modality == "FIBSEM":
                image_array = self.array_list_FIBSEM

                # Ensure image for display is RGB
                if image_array.ndim >= 4:
                    msg = (
                        "Please select a 2D image for display.\n"
                        + "Image shape here is {}".format(image_array.shape)
                    )
                    logging.warning(msg)
                    display_error_message(msg)
                    return
                elif image_array.ndim == 3:
                    shape = image_array.shape
                    if image_array.shape[-1] > 3:
                        image_array = np.moveaxis(image_array, 0, -1)
                    # After any swap axis...
                    if (
                        image_array.shape[-1] > 3
                    ):  # should be the channel axis, can't have more than RGB
                        msg = (
                            "Please select a 2D image with no more than 3 color channels for display.\n"
                            + "Image shape here is {}".format(image_array.shape)
                        )
                        logging.warning(msg)
                        display_error_message(msg)
                        return

                self.current_image_FIBSEM = qimage2ndarray.array2qimage(
                    image_array.copy()
                )

                self.current_pixmap_FIBSEM = QtGui.QPixmap.fromImage(
                    self.current_image_FIBSEM
                )
                self.current_pixmap_FIBSEM = self.current_pixmap_FIBSEM.scaled(
                    640, 400, QtCore.Qt.KeepAspectRatio
                )
                self.label_image_FIBSEM.setPixmap(self.current_pixmap_FIBSEM)

        except Exception as e:
            display_error_message(traceback.format_exc())

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

    def acquire_volume(self, mode=StageMode.WIDEFIELD, autosave=True):
        print("Acquiring fluorescence volume image...")
        try:  # TODO: shorten the amount of calls under the try, or at least split

            laser_dict = self.laser_dict
            if laser_dict == {}:
                display_error_message("Please select up to four lasers.")
                return
            if len(laser_dict) > 4:
                display_error_message("Please select a maximum of 4 lasers.")
                return

            try:
                volume_height = int(self.lineEdit_volume_height.text())
            except ValueError:
                display_error_message("Volume height must be a positive integer")
                return
            else:
                if volume_height <= 0:
                    display_error_message("Volume height must be a positive integer")
                    return

            try:
                z_slice_distance = int(self.lineEdit_slice_distance.text())
            except ValueError:
                display_error_message("Slice distance must be a positive integer")
                return
            else:
                if z_slice_distance <= 0:
                    display_error_message("Slice distance must be a positive integer")
                    return

            num_z_slices = round(volume_height / z_slice_distance) + 1

            if mode == StageMode.WIDEFIELD:
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
            self.array_list_FM = rgb
            self.update_display("FM")
        except Exception as e:
            display_error_message(traceback.format_exc())

    def correlateim(self):
        tempfile = "C:"
        try:
            fluorescence_image = self.array_list_FM

            if fluorescence_image == [] or fluorescence_image == "":
                raise ValueError("No first image selected")
            fibsem_image = self.array_list_FIBSEM
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

            if filename:
                image = _create_array_list(filename, "MILLING")
            else:
                display_error_message("Please select a filename. No image is selected.")
                return

            from autoscript_sdb_microscope_client.structures import AdornedImage

            adorned_image = AdornedImage()
            adorned_image = adorned_image.load(filename)
            try:
                adorned_image.metadata.binary_result.pixel_size.x
            except AttributeError:
                display_error_message(
                    "Please acquire a new ion beam image. "
                    "The selected image is not an ion beam image including pixel size metadata."
                )
                return

            piescope_gui.milling.open_milling_window(
                self, adorned_image.data, adorned_image
            )

        except Exception as e:
            display_error_message(traceback.format_exc())

    ############## Mirror methods ##############
    def mirror_on(self):
        print("Initialising mirror")
        structured.single_line_pulse(10, self.mirror_pin)

    def pattern_on(self):
        structured.single_line_onoff(
            self.checkBox_pattern_on.isChecked(), self.pattern_pin_on
        )

    def pattern_next(self):
        structured.single_line_pulse(10, self.pattern_pin)


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
