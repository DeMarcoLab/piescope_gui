import logging
import traceback

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import skimage
import skimage.color
import skimage.io
import skimage.transform

from piescope import fibsem

from piescope_gui.utils import display_error_message, timestamp
    
logger = logging.getLogger(__name__)


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

        q1 = QTimer(self)
        q1.setSingleShot(False)
        q1.start(10000)

    def create_window(self):
        self.setWindowTitle("Milling Parameter Selection")

        widget = QWidget(self)

        vlay = QVBoxLayout(widget)
        hlay = QHBoxLayout()

        self.wp = _WidgetPlot(self)
        vlay.addWidget(self.wp)

        button_width = 230
        button_height = 60
        label_width = 60

        self.exitButton = QPushButton("Exit")
        self.exitButton.setFixedWidth(button_width)
        self.exitButton.setFixedHeight(button_height)
        self.exitButton.setStyleSheet("font-size: 16px;")

        self.button_move_to_fibsem = QPushButton("Move to FIBSEM")
        self.button_move_to_fibsem.setFixedWidth(button_width)
        self.button_move_to_fibsem.setFixedHeight(button_height)
        self.button_move_to_fibsem.setStyleSheet("font-size: 16px;")

        self.button_move_to_fluorescence = QPushButton("Move to fluorescence")
        self.button_move_to_fluorescence.setFixedWidth(button_width)
        self.button_move_to_fluorescence.setFixedHeight(button_height)
        self.button_move_to_fluorescence.setStyleSheet("font-size: 16px;")

        self.pattern_creation_button = QPushButton("Add milling pattern")
        self.pattern_creation_button.setFixedWidth(button_width)
        self.pattern_creation_button.setFixedHeight(button_height)
        self.pattern_creation_button.setStyleSheet("font-size: 16px;")

        self.pattern_start_button = QPushButton("Start milling pattern")
        self.pattern_start_button.setFixedWidth(button_width)
        self.pattern_start_button.setFixedHeight(button_height)
        self.pattern_start_button.setStyleSheet("font-size: 16px;")

        self.pattern_pause_button = QPushButton("Pause milling pattern")
        self.pattern_pause_button.setFixedWidth(button_width)
        self.pattern_pause_button.setFixedHeight(button_height)
        self.pattern_pause_button.setStyleSheet("font-size: 16px;")

        self.pattern_stop_button = QPushButton("Stop milling pattern")
        self.pattern_stop_button.setFixedWidth(button_width)
        self.pattern_stop_button.setFixedHeight(button_height)
        self.pattern_stop_button.setStyleSheet("font-size: 16px;")

        self.x0_label = QLabel("X0:")
        self.x0_label.setFixedHeight(30)
        self.x0_label.setStyleSheet("font-size: 16px;")

        self.x0_label2 = QLabel("")
        self.x0_label2.setFixedWidth(label_width)
        self.x0_label2.setFixedHeight(30)
        self.x0_label2.setStyleSheet("font-size: 16px;")

        self.y0_label = QLabel("Y0:")
        self.y0_label.setFixedHeight(30)
        self.y0_label.setStyleSheet("font-size: 16px;")

        self.y0_label2 = QLabel("")
        self.y0_label2.setFixedWidth(label_width)
        self.y0_label2.setFixedHeight(30)
        self.y0_label2.setStyleSheet("font-size: 16px;")

        self.x1_label = QLabel("X1:")
        self.x1_label.setFixedHeight(30)
        self.x1_label.setStyleSheet("font-size: 16px;")

        self.x1_label2 = QLabel("")
        self.x1_label2.setFixedWidth(label_width)
        self.x1_label2.setFixedHeight(30)
        self.x1_label2.setStyleSheet("font-size: 16px;")

        self.y1_label = QLabel("Y1:")
        self.y1_label.setFixedHeight(30)
        self.y1_label.setStyleSheet("font-size: 16px;")

        self.y1_label2 = QLabel("")
        self.y1_label2.setFixedWidth(label_width)
        self.y1_label2.setFixedHeight(30)
        self.y1_label2.setStyleSheet("font-size: 16px;")

        spacerItem = QtWidgets.QSpacerItem(0, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        hlay.addWidget(self.x0_label)
        hlay.addWidget(self.x0_label2)
        hlay.addWidget(self.x1_label)
        hlay.addWidget(self.x1_label2)
        hlay.addWidget(self.y0_label)
        hlay.addWidget(self.y0_label2)
        hlay.addWidget(self.y1_label)
        hlay.addWidget(self.y1_label2)
        # hlay.addSpacerItem(spacerItem)
        hlay.addWidget(self.button_move_to_fibsem)
        hlay.addWidget(self.button_move_to_fluorescence)
        hlay.addWidget(self.pattern_creation_button)
        hlay.addWidget(self.pattern_start_button)
        hlay.addWidget(self.pattern_pause_button)
        hlay.addWidget(self.pattern_stop_button)
        hlay.addWidget(self.exitButton)
        vlay.addLayout(hlay)

        self.setCentralWidget(widget)
        self.rect = Rectangle((0, 0), 0.2, 0.2, color='yellow', fill=None, alpha=1)
        self.rect2 = Rectangle((0, 0), 0.2, 0.2, color='yellow', fill=None, alpha=1)
            
        self.wp.canvas.ax11.add_patch(self.rect)
        self.wp.canvas.ax11.add_patch(self.rect2)
        self.rect.set_visible(False)
        self.rect2.set_visible(False)
        self.rect.set_hatch("//////")
        self.rect2.set_hatch("//////")

        self.wp.canvas.mpl_connect('button_press_event', self.on_click)
        # self.wp.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.wp.canvas.mpl_connect('button_release_event', self.on_release)
        
    def create_conn(self):
        self.exitButton.clicked.connect(self.menu_quit)

        self.button_move_to_fibsem.clicked.connect(
            lambda: self.parent().move_to_electron_microscope())
        self.button_move_to_fluorescence.clicked.connect(
            lambda: self.parent().move_to_light_microscope())

        self.pattern_creation_button.clicked.connect(self.add_milling_pattern)
        self.pattern_start_button.clicked.connect(self.start_patterning)
        self.pattern_pause_button.clicked.connect(self.pause_patterning)
        self.pattern_stop_button.clicked.connect(self.stop_patterning)

    def menu_quit(self):
        self.close()

    def add_milling_pattern(self):
        try:
            fibsem.create_rectangular_pattern(
                self.parent().microscope, self.adorned_ion_image,
                self.xclick, self.x1, self.yclick, self.y1, depth=1e-6)
            print('Added milling pattern to the FIBSEM microscope.')
        except Exception:
            display_error_message(traceback.format_exc())

    def start_patterning(self):
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
                self.parent().microscope.patterning.start()
                print('Started milling pattern.')
        except Exception:
            display_error_message(traceback.format_exc())

    def pause_patterning(self):
        from autoscript_core.common import ApplicationServerException
        try:
            state = self.parent().microscope.patterning.state
            if state != "Running":
                logger.warning(
                    "Can't pause milling pattern! "
                    "Patterning state is not currently running.\n"
                    "microscope.patterning.state = {}".format(state)
                    )
                return
            else:
                self.parent().microscope.patterning.pause()
                print('Paused milling pattern.')
        except Exception:
            display_error_message(
                "microscope.patterning.state = {}\n".format(state) +
                traceback.format_exc()
                )

    def stop_patterning(self):
        from autoscript_core.common import ApplicationServerException
        try:
            state = self.parent().microscope.patterning.state
            if state != "Running" and state != "Paused":
                logger.warning(
                    "Can't stop milling pattern! "
                    "Patterning state is not running or paused.\n"
                    "microscope.patterning.state = {}".format(state)
                    )
                return
            else:
                self.parent().microscope.patterning.stop()
                print('Stopped milling pattern.')
        except Exception:
            display_error_message(
                "microscope.patterning.state = {}\n".format(state) +
                traceback.format_exc()
                )

    def on_click(self, event):
        if event.button == 1 or event.button == 3:
            if event.inaxes is not None:
                self.xclick = event.xdata
                self.yclick = event.ydata
                logger.debug(self.xclick)
                logger.debug(self.yclick)
                self.dragged = False
                logger.debug(self.dragged)
                self.on_press = True

    # def on_motion(self, event):
    #     if event.button == 1 or event.button == 3 and self.on_press:
    #         if (self.xclick is not None and self.yclick is not None):
    #             x0, y0 = self.xclick, self.yclick
    #             self.x1, self.y1 = event.xdata, event.ydata

    #             if (self.x1 is not None or self.y1 is not None):
    #                 self.dragged = True
    #                 # return
    #                 # self.rect.set_width(self.x1 - x0)
    #                 # self.rect.set_height(self.y1 - y0)
    #                 # self.rect.set_xy((x0, y0))
    #                 # self.rect.set_visible(True)
    #                 # logger.debug("x0 %s", str(x0))
    #                 # logger.debug("y0 %s", str(y0))
    #                 # logger.debug("x1 %s", str(self.x1))
    #                 # logger.debug("y1 %s", str(self.y1))
    #                 # self.wp.canvas.draw()

    def on_release(self, event):
        # if event.button == 1 and self.dragged:
        #     return
        #     logger.debug(self.dragged)
        #     try:
        #         self.x1_label2.setText("%.1f" % self.x1)
        #     except Exception as e:
        #         display_error_message("Mouse released outside image. Please try again")
        #     self.x0_label2.setText("%.1f" % self.xclick)
        #     self.y0_label2.setText("%.1f" % self.yclick)
        #     self.y1_label2.setText("%.1f" % self.y1)
        if event.button == 1:
            self.parent().microscope.patterning.clear_patterns()
            c_x, c_y = fibsem.pixel_to_realspace_coordinate((self.xclick, self.yclick), self.adorned_ion_image)
            lower_pattern, upper_pattern = mill_trench_patterns(self.parent().microscope, c_x, c_y, self.parent().config['lamella'])
            l_y = lower_pattern.center_y - lower_pattern.width 

            image_width = self.adorned_ion_image.width
            image_height = self.adorned_ion_image.height
            pixel_size =  self.adorned_ion_image.metadata.binary_result.pixel_size.x

            l_width = lower_pattern.width / pixel_size
            l_height = lower_pattern.height / pixel_size
            rectangle_left = (image_width / 2) + (lower_pattern.center_x / pixel_size) - (l_width/2)
            rectangle_bottom = (image_height / 2) - (lower_pattern.center_y / pixel_size) - (l_height/2)
            self.rect.set_width(l_width)
            self.rect.set_height(l_height)
            self.rect.set_xy((rectangle_left, rectangle_bottom))
            self.rect.set_visible(True)
        
            u_width = upper_pattern.width / pixel_size
            u_height = upper_pattern.height / pixel_size
            rectangle2_left = (image_width / 2) + (upper_pattern.center_x / pixel_size) - (u_width/2)
            rectangle2_bottom = (image_height / 2) - (upper_pattern.center_y / pixel_size) - (u_height/2)
            self.rect2.set_width(u_width)
            self.rect2.set_height(u_height)
            self.rect2.set_xy((rectangle2_left, rectangle2_bottom))
            self.rect2.set_visible(True)
            self.wp.canvas.draw()
        

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