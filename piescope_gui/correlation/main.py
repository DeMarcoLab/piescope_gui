import os
import sys
import time

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
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from skimage.transform import AffineTransform

def open_correlation_window(image_1, image_2, main_gui):
    global img1
    global img2
    global gui

    img1 = image_1
    img2 = image_2
    gui = main_gui

    app = QApplication(sys.argv)
