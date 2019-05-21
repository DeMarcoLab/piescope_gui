import sys

import pkg_resources

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction,
                             QApplication,
                             QDesktopWidget,
                             QDialog,
                             QFileDialog,
                             QHBoxLayout,
                             QLabel,
                             QMainWindow,
                             QToolBar,
                             QVBoxLayout,
                             QWidget)


class Template(QMainWindow):
    """Main window with all widgets necessary for the application."""

    def __init__(self, parent=None):
        """Initialize the components of the main window."""
        super(Template, self).__init__(parent)
        self.resize(1000, 750)
        self.setWindowTitle('Template')
        window_icon = pkg_resources.resource_filename(
            'fibsem_gui.images', 'ic_insert_drive_file_black_48dp_1x.png')
        self.setWindowIcon(QIcon(window_icon))

        self.widget = QWidget()
        self.layout = QHBoxLayout(self.widget)

        self.menu_bar = self.menuBar()
        self.about_dialog = AboutDialog()

        self.status_bar = self.statusBar()
        self.status_bar.showMessage('Ready', 5000)

        self.file_menu()
        self.help_menu()

        self.tool_bar_items()

    def file_menu(self):
        """Create file submenu with an Open File item to open a file dialog."""
        self.file_sub_menu = self.menu_bar.addMenu('File')

        self.open_action = QAction('Open File', self)
        self.open_action.setStatusTip('Open a file into Template.')
        self.open_action.setShortcut('CTRL+O')
        self.open_action.triggered.connect(self.open_file)

        self.exit_action = QAction('Exit Application', self)
        self.exit_action.setStatusTip('Exit the application.')
        self.exit_action.setShortcut('CTRL+Q')
        self.exit_action.triggered.connect(lambda: QApplication.quit())

        self.file_sub_menu.addAction(self.open_action)
        self.file_sub_menu.addAction(self.exit_action)

    def help_menu(self):
        """Create help submenu with an About item tha opens an about dialog."""
        self.help_sub_menu = self.menu_bar.addMenu('Help')

        self.about_action = QAction('About', self)
        self.about_action.setStatusTip('About the application.')
        self.about_action.setShortcut('CTRL+H')
        self.about_action.triggered.connect(lambda: self.about_dialog.exec_())

        self.help_sub_menu.addAction(self.about_action)

    def tool_bar_items(self):
        """Create a tool bar for the main window."""
        self.tool_bar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self.tool_bar)
        self.tool_bar.setMovable(False)

        open_icon = pkg_resources.resource_filename(
            'fibsem_gui.images', 'ic_open_in_new_black_48dp_1x.png')
        tool_bar_open_action = QAction(QIcon(open_icon), 'Open File', self)
        tool_bar_open_action.triggered.connect(self.open_file)

        self.tool_bar.addAction(tool_bar_open_action)

    def open_file(self):
        """Allow user to open a file into the application with QFileDialog."""
        filename, accepted = QFileDialog.getOpenFileName(self, 'Open File')

        if accepted:
            with open(filename) as file:
                file.read()


class AboutDialog(QDialog):
    """Create the necessary elements to show helpful text in a dialog."""

    def __init__(self, parent=None):
        """Display a dialog that shows application information."""
        super(AboutDialog, self).__init__(parent)

        self.setWindowTitle('About')
        help_icon = pkg_resources.resource_filename(
            'fibsem_gui.images', 'ic_help_black_48dp_1x.png')
        self.setWindowIcon(QIcon(help_icon))
        self.resize(300, 200)

        author = QLabel('DeMarco Lab')
        author.setAlignment(Qt.AlignCenter)

        icons = QLabel('Material design icons created by Google')
        icons.setAlignment(Qt.AlignCenter)

        github = QLabel('GitHub: ''')
        github.setAlignment(Qt.AlignCenter)

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignVCenter)

        self.layout.addWidget(author)
        self.layout.addWidget(icons)
        self.layout.addWidget(github)

        self.setLayout(self.layout)


def main():
    application = QApplication(sys.argv)
    window = Template()
    desktop = QDesktopWidget().availableGeometry()
    width = (desktop.width() - window.width()) / 2
    height = (desktop.height() - window.height()) / 2
    window.show()
    window.move(width, height)
    sys.exit(application.exec_())


if __name__ == '__main__':
    main()
