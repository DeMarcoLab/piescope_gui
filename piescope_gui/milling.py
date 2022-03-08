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

import piescope_gui.qtdesigner_files.milling as gui_milling
from piescope_gui.utils import display_error_message, timestamp

logger = logging.getLogger(__name__)

class GUIMillingWindow(gui_milling.Ui_MillingWindow, QtWidgets.QMainWindow):
    def __init__(self, parent_gui, adorned_image, display_image=None):
        super().__init__(parent=parent_gui)
        self.setupUi(self)
        
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

        self.xclick = None
        self.yclick = None
    
    def on_click(self, event):
        if event.button == 1 and event.inaxes is not None:
            self.xclick = event.xdata
            self.yclick = event.ydata
            self.parent().microscope.patterning.clear_patterns()
            c_x, c_y = fibsem.pixel_to_realspace_coordinate((self.xclick, self.yclick), self.adorned_image)
            lower_pattern, upper_pattern = mill_trench_patterns(self.parent().microscope, c_x, c_y, self.parent().config['lamella'])

            def update_rectangle_pattern(adorned_image, rectangle, pattern):
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
            
            update_rectangle_pattern(adorned_image=self.adorned_image, rectangle=self.upper_rectangle, pattern=upper_pattern)
            update_rectangle_pattern(adorned_image=self.adorned_image, rectangle=self.lower_rectangle, pattern=lower_pattern)

            self.wp.canvas.draw()
        
    def setup_connections(self):
        self.pushButton_save_position.clicked.connect(self.save_milling_position)
        self.pushButton_start_milling.clicked.connect(self.start_patterning)
        self.pushButton_stop_milling.clicked.connect(self.stop_patterning)

    def save_milling_position(self):
        if self.milling_position:
            # TODO: calculate milling position correctly (raw position + click shift)
            self.parent().milling_position = self.milling_position

    def start_patterning(self):
        # TODO: This wont actually change the currents to mill correctly
        from autoscript_core.common import ApplicationServerException
        try:
            state = "Idle"
            # state = self.parent().microscope.patterning.state
            if state != "Idle":
                logger.warning(
                    "Can't start milling pattern! "
                    "Patterning state is not currently Idle.\n"
                    "microscope.patterning.state = {}".format(state)
                    )
                return
            else:
                # self.parent().microscope.patterning.start()
                print('Started milling pattern.')
        except Exception:
            display_error_message(traceback.format_exc())

    def stop_patterning(self):
        from autoscript_core.common import ApplicationServerException
        try:
            state = "Running"
            # state = self.parent().microscope.patterning.state
            if state != "Running":
                logger.warning(
                    "Can't stop milling pattern! "
                    "Patterning state is not running.\n"
                    "microscope.patterning.state = {}".format(state)
                    )
                return
            else:
            #     self.parent().microscope.patterning.stop()
                print('Stopped milling pattern.')
        except Exception:
            display_error_message(
                "microscope.patterning.state = {}\n".format(state) +
                traceback.format_exc()
                )




def open_milling_window(parent_gui, display_image, adorned_ion_image):
    """Opens a new window to perform correlation

    Parameters
    ----------
    parent_gui : PyQt5 Window
    display_image : numpy ndarray
        Image to display in milling GUI window.
    adorned_ion_image : Adorned Image
        Adorned image with image as the .data attribute and metadata passed from
        the fibsem image on display in the main window

    """
    global image
    image = display_image

    window = _MainWindow(parent=parent_gui, adorned_ion_image=adorned_ion_image)
    window.show()
    return window


class _MainWindow(QMainWindow):
    def __init__(self, parent=None, adorned_ion_image=None, display_image=None):
        super().__init__(parent=parent)
        self.adorned_ion_image = adorned_ion_image
        self.create_window()
        self.create_conn()

        self.show()
        self.showMaximized()
        self.wp.canvas.fig.subplots_adjust(
            left=0.01, bottom=0.01, right=0.99, top=0.99)

        self.x1 = None
        self.y1 = None
        self.xclick = None
        self.yclick = None




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
    trench_height = float(settings["trench_height"])
    upper_trench_height = float(trench_height / settings["size_ratio"])
    offset = float(settings["offset"])
    milling_depth = float(settings["milling_depth"])

    centre_upper_y = centre_y + (lamella_height / 2 + upper_trench_height / 2 + offset)
    centre_lower_y = centre_y - (lamella_height / 2 + trench_height / 2 + offset)

    lower_pattern = microscope.patterning.create_cleaning_cross_section(
        centre_x,
        centre_lower_y,
        lamella_width,
        trench_height,
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
