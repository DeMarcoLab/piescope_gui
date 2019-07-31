from PyQt5 import QtWidgets, QtGui, QtCore
import piescope_gui.interface.main as interface
import piescope_gui.designer.main as gui_main
import os.path as p


class GUIMainWindow(gui_main.Ui_MainGui, QtWidgets.QMainWindow):
    def __init__(self):
        super(GUIMainWindow, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("PIEScope User Interface")
        self.statusbar.setSizeGripEnabled(0)
        self.status = QtWidgets.QLabel(self.statusbar)
        self.status.setAlignment(QtCore.Qt.AlignRight)
        self.statusbar.addPermanentWidget(self.status, 1)

        self.save_name = ""
        self.array_list = []
        self.string_list = []
        self.current_path = ""
        self.current_image = ""
        self.current_pixmap = []
        self.save_destination = ""
        self.delim = p.normpath("/")

        self.actionOpen.triggered.connect(self.open_images)
        self.actionSave.triggered.connect(self.save_image)

        self.short_o = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        self.short_o.activated.connect(self.open_images)
        self.short_s = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        self.short_s.activated.connect(self.save_image)

        self.slider_stack.valueChanged.connect(self.update_display)

    def open_images(self):
        interface.open_images(self)

    def save_image(self):
        interface.save_image(self)

    def update_display(self):
        interface.update_display(self)

    def fill_save_information(self):
        interface.fill_save_information(self)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    qt_app = GUIMainWindow()
    qt_app.show()
    app.exec_()
