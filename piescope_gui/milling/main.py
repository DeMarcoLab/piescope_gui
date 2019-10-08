import os
import os.path as p
import sys
import time

import matplotlib
import numpy as np
import scipy.ndimage as ndi
import skimage
import skimage.color
import skimage.io
import skimage.transform

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import \
    FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from skimage.transform import AffineTransform
from matplotlib.patches import Rectangle

from piescope_gui import gui_interaction


def open_milling_window(main_gui, image):
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
        self.wp.canvas.fig.subplots_adjust(
            left=0.01, bottom=0.01, right=0.99, top=0.99)

        q1 = QTimer(self)
        q1.setSingleShot(False)
        q1.start(10000)

    def create_window(self):
        self.setWindowTitle("Milling Parameter Selection")

        widget = QWidget(self)


        hlay = QHBoxLayout(widget)
        vlay = QVBoxLayout()
        vlay2 = QVBoxLayout()
        vlay2.setSpacing(20)
        hlay_buttons = QHBoxLayout()

        hlay.addLayout(vlay)
        hlay.addLayout(vlay2)

        self.wp = _WidgetPlot(self)
        vlay.addWidget(self.wp)

        self.exitButton = QPushButton("Return")
        self.exitButton.setFixedHeight(60)
        self.exitButton.setStyleSheet("font-size: 16px;")
        hlay_buttons.addWidget(self.exitButton)

        self.setCentralWidget(widget)
        self.rect = Rectangle((0, 0), 0.2, 0.2, color='k', fill=None, alpha=1)
        self.wp.canvas.ax11.add_patch(self.rect)
        self.rect.set_visible(False)

        self.wp.canvas.mpl_connect('button_press_event', self.on_click)
        self.wp.canvas.mpl_connect('motion_notify_event', self.on_motion)


    def create_conn(self):
        self.exitButton.clicked.connect(self.menu_quit)

    def menu_quit(self):
        self.close()

    def on_click(self, event):
        if event.button == 1 or event.button == 3:
            if event.inaxes is not None:
                self.xclick = event.xdata
                self.yclick = event.ydata
                print(self.xclick)
                print(self.yclick)
                self.on_press = True

    def on_motion(self, event):
        if event.button == 1 or event.button == 3 and self.on_press == True:
            if (self.xclick is not None and self.yclick is not None):
                x0, y0 = self.xclick, self.yclick
                x1, y1 = event.xdata, event.ydata
                if (x1 is not None or y1 is not None):
                    self.rect.set_width(x1 - x0)
                    self.rect.set_height(y1 - y0)
                    self.rect.set_xy((x0, y0))
                    self.rect.set_visible(True)
                    print("x0 %s", str(x0))
                    print("y0 %s", str(y0))
                    print("x1 %s", str(x1))
                    print("y1 %s", str(y1))
                    self.wp.canvas.draw()

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
            gs0[0], xticks=[], yticks=[], title="Image")
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