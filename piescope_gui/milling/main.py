import skimage
import skimage.color
import skimage.io
import skimage.transform

from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from piescope import fibsem


def open_milling_window(main_gui, image, adorned_metadata):
    """

    :param main_gui:
    :param image: numpy array
    :param adorned_metadata: adorned_image.metadata
    :return:
    """
    global gui
    global img
    gui = main_gui
    img = image
    img = skimage.color.gray2rgb(image)

    window = _MainWindow()
    window.show()
    return


class _MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(parent=gui)
        self.create_window()
        self.create_conn()

        self.show()
        self.showMaximized()
        self.wp.canvas.fig.subplots_adjust(
            left=0.01, bottom=0.01, right=0.99, top=0.99)

        self.x1 = None

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


        self.exitButton = QPushButton("Return")
        self.exitButton.setFixedWidth(250)
        self.exitButton.setFixedHeight(60)
        self.exitButton.setStyleSheet("font-size: 16px;")

        self.pattern_creation_button = QPushButton("Create milling pattern")
        self.pattern_creation_button.setFixedWidth(250)
        self.pattern_creation_button.setFixedHeight(60)
        self.pattern_creation_button.setStyleSheet("font-size: 16px;")

        self.pattern_start_button = QPushButton("Start milling pattern")
        self.pattern_start_button.setFixedWidth(250)
        self.pattern_start_button.setFixedHeight(60)
        self.pattern_start_button.setStyleSheet("font-size: 16px;")

        self.pattern_pause_button = QPushButton("Pause milling pattern")
        self.pattern_pause_button.setFixedWidth(250)
        self.pattern_pause_button.setFixedHeight(60)
        self.pattern_pause_button.setStyleSheet("font-size: 16px;")

        self.pattern_stop_button = QPushButton("Stop milling pattern")
        self.pattern_stop_button.setFixedWidth(250)
        self.pattern_stop_button.setFixedHeight(60)
        self.pattern_stop_button.setStyleSheet("font-size: 16px;")

        self.x0_label = QLabel("X0:")
        self.x0_label.setFixedHeight(30)
        self.x0_label.setStyleSheet("font-size: 16px;")

        self.x0_label2 = QLabel("")
        self.x0_label2.setFixedWidth(120)
        self.x0_label2.setFixedHeight(30)
        self.x0_label2.setStyleSheet("font-size: 16px;")

        self.y0_label = QLabel("Y0:")
        self.y0_label.setFixedHeight(30)
        self.y0_label.setStyleSheet("font-size: 16px;")

        self.y0_label2 = QLabel("")
        self.y0_label2.setFixedWidth(120)
        self.y0_label2.setFixedHeight(30)
        self.y0_label2.setStyleSheet("font-size: 16px;")

        self.x1_label = QLabel("X1:")
        self.x1_label.setFixedHeight(30)
        self.x1_label.setStyleSheet("font-size: 16px;")

        self.x1_label2 = QLabel("")
        self.x1_label2.setFixedWidth(120)
        self.x1_label2.setFixedHeight(30)
        self.x1_label2.setStyleSheet("font-size: 16px;")

        self.y1_label = QLabel("Y1:")
        self.y1_label.setFixedHeight(30)
        self.y1_label.setStyleSheet("font-size: 16px;")

        self.y1_label2 = QLabel("")
        self.y1_label2.setFixedWidth(120)
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
        hlay.addSpacerItem(spacerItem)
        hlay.addWidget(self.pattern_creation_button)
        hlay.addWidget(self.pattern_start_button)
        hlay.addWidget(self.pattern_pause_button)
        hlay.addWidget(self.pattern_stop_button)
        hlay.addWidget(self.exitButton)
        vlay.addLayout(hlay)

        self.setCentralWidget(widget)
        self.rect = Rectangle((0, 0), 0.2, 0.2, color='yellow', fill=None, alpha=1)
        self.wp.canvas.ax11.add_patch(self.rect)
        self.rect.set_visible(False)

        self.wp.canvas.mpl_connect('button_press_event', self.on_click)
        self.wp.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.wp.canvas.mpl_connect('button_release_event', self.on_release)

    def create_conn(self):
        self.exitButton.clicked.connect(self.menu_quit)
        self.pattern_creation_button.clicked.connect(
            lambda: fibsem.create_rectangular_pattern(gui.microscope, gui.FIBSEM_adorned_image, self.xclick,
                                                      self.x1, self.yclick, self.y1, depth=1e-6))
        self.close()

    def on_click(self, event):
        if event.button == 1 or event.button == 3:
            if event.inaxes is not None:
                self.xclick = event.xdata
                self.yclick = event.ydata
                print(self.xclick)
                print(self.yclick)
                self.dragged = False
                print(self.dragged)
                self.on_press = True

    def on_motion(self, event):
        if event.button == 1 or event.button == 3 and self.on_press:
            if (self.xclick is not None and self.yclick is not None):
                x0, y0 = self.xclick, self.yclick
                self.x1, self.y1 = event.xdata, event.ydata

                if (self.x1 is not None or self.y1 is not None):
                    self.dragged = True
                    self.rect.set_width(self.x1 - x0)
                    self.rect.set_height(self.y1 - y0)
                    self.rect.set_xy((x0, y0))
                    self.rect.set_visible(True)
                    print("x0 %s", str(x0))
                    print("y0 %s", str(y0))
                    print("x1 %s", str(self.x1))
                    print("y1 %s", str(self.y1))
                    self.wp.canvas.draw()

    def on_release(self, event):
        if event.button == 1 and self.dragged:
            print(self.dragged)
            try:
                self.x1_label2.setText("%.1f" % self.x1)
            except:
                gui_interaction.error_msg(gui, "Mouse released outside image.  Please try again")
            self.x0_label2.setText("%.1f" % self.xclick)
            self.y0_label2.setText("%.1f" % self.yclick)
            self.y1_label2.setText("%.1f" % self.y1)


class _WidgetPlot(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas = _PlotCanvas(self)
        self.layout().addWidget(self.canvas)


class _PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure()
        FigureCanvas.__init__(self, self.fig)

        self.setParent(parent)
        FigureCanvas.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
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
        self.ax11.imshow(img)

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


if __name__ == "__main__":
    open_milling_window()
