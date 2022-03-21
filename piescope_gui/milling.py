import logging
import traceback

import numpy as np
import skimage
import skimage.color
import skimage.io
import skimage.transform
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from piescope import fibsem
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from autoscript_sdb_microscope_client.structures import StagePosition
import piescope
from autoscript_sdb_microscope_client.enumerations import CoordinateSystem

import piescope_gui.qtdesigner_files.milling as gui_milling
from piescope_gui.utils import display_error_message, timestamp

logger = logging.getLogger(__name__)

MICRON_TO_METRE = 1e-6
METRE_TO_MICRON = 1e6

class GUIMillingWindow(gui_milling.Ui_MillingWindow, QtWidgets.QMainWindow):
    def __init__(self, parent_gui, adorned_image, display_image=None):
        super().__init__(parent=parent_gui)
        self.setupUi(self)

        self.imaging_current = self.parent().microscope.beams.ion_beam.beam_current.value
        logging.info(f'Imaging current recorded as: {self.imaging_current}')

        self.settings = self.parent().config['lamella'].copy()
        logging.info(f'Loaded settings: {self.settings}')

        global image

        if display_image is None:
            display_image = adorned_image.data


        # self.parent = parent_gui
        self.display_image = display_image
        image = self.display_image

        self.adorned_image = adorned_image

        self.milling_position = None

        self.wp = _WidgetPlot(self)
        self.label_image.setLayout(QtWidgets.QVBoxLayout())
        self.label_image.layout().addWidget(self.wp)

        self.upper_rectangle = Rectangle((0, 0), 0.2, 0.2, color='yellow', fill=None, alpha=1)
        self.lower_rectangle = Rectangle((0, 0), 0.2, 0.2, color='yellow', fill=None, alpha=1)

        self.wp.canvas.ax11.add_patch(self.upper_rectangle)
        self.wp.canvas.ax11.add_patch(self.lower_rectangle)

        self.upper_rectangle.set_visible(False)
        self.upper_rectangle.set_hatch('//////')
        self.lower_rectangle.set_visible(False)
        self.lower_rectangle.set_hatch('//////')

        self.wp.canvas.mpl_connect('button_press_event', self.on_click)

        self.center_x = 0
        self.center_y = 0
        self.xclick = None
        self.yclick = None

        self.doubleSpinBox_milling_depth.setValue(float(self.settings['milling_depth']) * METRE_TO_MICRON)
        self.doubleSpinBox_lamella_height.setValue(float(self.settings['lamella_height']) * METRE_TO_MICRON)
        self.doubleSpinBox_lamella_width.setValue(float(self.settings['lamella_width']) * METRE_TO_MICRON)
        self.doubleSpinBox_upper_height.setValue(float(self.settings['upper_height']) * METRE_TO_MICRON)
        self.doubleSpinBox_lower_height.setValue(float(self.settings['lower_height']) * METRE_TO_MICRON)

        self.setup_connections()


        # initial pattern
        self.center_x, self.center_y = 0, 0
        self.draw_milling_patterns()

    def on_click(self, event):
        if event.button == 1 and event.inaxes is not None:
            self.xclick = event.xdata
            self.yclick = event.ydata
            self.center_x, self.center_y = fibsem.pixel_to_realspace_coordinate((self.xclick, self.yclick), self.adorned_image)
            self.draw_milling_patterns()

    def draw_milling_patterns(self):
        self.parent().microscope.patterning.clear_patterns()
        lower_pattern, upper_pattern = mill_trench_patterns(self.parent().microscope, self.center_x, self.center_y, self.settings)

        def draw_rectangle_pattern(adorned_image, rectangle, pattern):
            image_width = adorned_image.width
            image_height = adorned_image.height
            pixel_size =  adorned_image.metadata.binary_result.pixel_size.x

            width = pattern.width / pixel_size
            height = pattern.height / pixel_size
            rectangle_left = (image_width / 2) + (pattern.center_x / pixel_size) - (width/2)
            rectangle_bottom = (image_height / 2) - (pattern.center_y / pixel_size) - (height/2)
            rectangle.set_width(width)
            rectangle.set_height(height)
            rectangle.set_xy((rectangle_left, rectangle_bottom))
            rectangle.set_visible(True)

        try:
            draw_rectangle_pattern(adorned_image=self.adorned_image, rectangle=self.upper_rectangle, pattern=upper_pattern)
            draw_rectangle_pattern(adorned_image=self.adorned_image, rectangle=self.lower_rectangle, pattern=lower_pattern)
        except:
            # NOTE: these exceptions happen when the pattern is too far outside of the FOV
            import piescope_gui.main as piescope_gui_main
            piescope_gui_main.display_error_message(traceback.format_exc())
        self.wp.canvas.draw()

    def setup_connections(self):
        self.pushButton_save_position.clicked.connect(lambda: self.save_milling_position())
        self.pushButton_start_milling.clicked.connect(lambda: self.start_patterning())
        self.pushButton_stop_milling.clicked.connect(lambda: self.stop_patterning())

        self.doubleSpinBox_milling_depth.textChanged.connect(lambda: self.update_milling_patterns())
        self.doubleSpinBox_lamella_height.valueChanged.connect(lambda: self.update_milling_patterns())
        self.doubleSpinBox_lamella_width.valueChanged.connect(lambda: self.update_milling_patterns())
        self.doubleSpinBox_upper_height.valueChanged.connect(lambda: self.update_milling_patterns())
        self.doubleSpinBox_lower_height.valueChanged.connect(lambda: self.update_milling_patterns())

    def closeEvent(self, event):
        self.set_ion_beam_current(self.imaging_current)
        logging.info('Resetting ion beam current to imaging current')

    def update_milling_patterns(self):
        logging.info('updating milling patterns')
        self.settings['milling_depth'] = self.doubleSpinBox_milling_depth.value() * MICRON_TO_METRE
        self.settings['lamella_height'] = self.doubleSpinBox_lamella_height.value() * MICRON_TO_METRE
        self.settings['lamella_width'] = self.doubleSpinBox_lamella_width.value() * MICRON_TO_METRE
        self.settings['upper_height'] = self.doubleSpinBox_upper_height.value() * MICRON_TO_METRE
        self.settings['lower_height'] = self.doubleSpinBox_lower_height.value() * MICRON_TO_METRE
        self.draw_milling_patterns()

    def save_milling_position(self):
        if self.xclick is not None:
            x_move = StagePosition(x=self.center_x, y=0, z=0)
            yz_move = piescope.fibsem.y_corrected_stage_movement(
                self.center_y,
                stage_tilt=self.parent().microscope.specimen.stage.current_position.t,
                settings=self.parent().config,
                image=self.parent().image_ion
            )
            self.parent().microscope.specimen.stage.set_default_coordinate_system(CoordinateSystem.RAW)
            current_position = self.parent().microscope.specimen.stage.current_position
            logging.info(f'Current position: {current_position}')
            self.parent().microscope.specimen.stage.set_default_coordinate_system(CoordinateSystem.SPECIMEN)

            self.parent().milling_position = StagePosition(x=current_position.x + x_move.x,
                                                            y=current_position.y + yz_move.y,
                                                            z=current_position.z + yz_move.z,
                                                            r=current_position.r,
                                                            t=current_position.t,
                                                            coordinate_system=current_position.coordinate_system)

            logging.info(f'New position: {self.parent().milling_position}')
            self.parent().microscope.patterning.clear_patterns()

    def set_ion_beam_current(self, current):
        logging.info(f'Setting current to {current}')
        self.parent().microscope.beams.ion_beam.beam_current.value = current

    def start_patterning(self):
        milling_current = self.settings['milling_current']
        logging.info(f'milling current read as: {milling_current}')

        from autoscript_core.common import ApplicationServerException
        try:
            state = self.parent().microscope.patterning.state
            if state != "Idle":
                logger.warning(
                    "Can't start milling pattern! "
                    "Patterning state is not currently Idle.\n"
                    "microscope.patterning.state = {}".format(state)
                    )
                return
            else:
                logging.info('Started milling pattern.')
                self.parent().microscope.imaging.set_active_view(2)
                self.set_ion_beam_current(current=milling_current)
                self.parent().microscope.patterning.run() # TODO: investigate using .start() to not block
                self.set_ion_beam_current(self.imaging_current)
                logging.info("Finished milling pattern")
        except Exception:
            display_error_message(traceback.format_exc())
            self.set_ion_beam_current(self.imaging_current)


    def stop_patterning(self):
        from autoscript_core.common import ApplicationServerException
        try:
            state = self.parent().microscope.patterning.state
            if state != "Running":
                logger.warning(
                    "Can't stop milling pattern! "
                    "Patterning state is not running.\n"
                    "microscope.patterning.state = {}".format(state)
                    )
                return
            else:
                self.parent().microscope.patterning.stop()
                self.set_ion_beam_current(self.imaging_current)
                logging.info('Stopped milling pattern.')
        except Exception:
            display_error_message(
                "microscope.patterning.state = {}\n".format(state) +
                traceback.format_exc()
                )

class _WidgetPlot(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas = _PlotCanvas(self)
        self.layout().addWidget(self.canvas)


class _PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        self.fig = Figure()
        FigureCanvasQTAgg.__init__(self, self.fig)

        self.setParent(parent)
        FigureCanvasQTAgg.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvasQTAgg.updateGeometry(self)
        self.plot()
        self.createConn()

        self.figureActive = False
        self.axesActive = None
        self.cursorGUI = "arrow"
        self.cursorChanged = False

    def plot(self):
        gs0 = self.fig.add_gridspec(1, 1)

        self.ax11 = self.fig.add_subplot(
            gs0[0], xticks=[], yticks=[], title="")
        self.ax11.imshow(image)

    def updateCanvas(self, event=None):
        ax11_xlim = self.ax11.get_xlim()
        ax11_xvis = ax11_xlim[1] - ax11_xlim[0]

        while len(self.ax11.patches) > 0:
            [p.remove() for p in self.ax11.patches]
        while len(self.ax11.texts) > 0:
            [t.remove() for t in self.ax11.texts]

        ax11_units = ax11_xvis * 0.003
        self.fig.canvas.draw()

    def createConn(self):
        self.fig.canvas.mpl_connect("figure_enter_event", self.activeFigure)
        self.fig.canvas.mpl_connect("figure_leave_event", self.leftFigure)
        self.fig.canvas.mpl_connect("button_press_event", self.mouseClicked)
        self.ax11.callbacks.connect("xlim_changed", self.updateCanvas)

    def activeFigure(self, event):
        self.figureActive = True

    def leftFigure(self, event):
        self.figureActive = False
        if self.cursorGUI != "arrow":
            self.cursorGUI = "arrow"
            self.cursorChanged = True

    def mouseClicked(self, event):
        x = event.xdata
        y = event.ydata



def mill_trench_patterns(microscope, c_x, c_y, settings: dict):
    """Calculate the trench milling patterns"""

    centre_x = c_x
    centre_y = c_y

    lamella_width = float(settings["lamella_width"])
    lamella_height = float(settings["lamella_height"])
    lower_trench_height = float(settings["lower_height"])
    upper_trench_height = float(settings["upper_height"])
    milling_depth = float(settings["milling_depth"])

    centre_upper_y = centre_y + (lamella_height / 2 + upper_trench_height / 2 )
    centre_lower_y = centre_y - (lamella_height / 2 + lower_trench_height / 2 )

    lower_pattern = microscope.patterning.create_cleaning_cross_section(
        centre_x,
        centre_lower_y,
        lamella_width,
        lower_trench_height,
        milling_depth,
    )
    lower_pattern.scan_direction = "BottomToTop"

    upper_pattern = microscope.patterning.create_cleaning_cross_section(
        centre_x,
        centre_upper_y,
        lamella_width,
        upper_trench_height,
        milling_depth,
    )
    upper_pattern.scan_direction = "TopToBottom"

    return [lower_pattern, upper_pattern]
