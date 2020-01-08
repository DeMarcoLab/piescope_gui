import os
import mock

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from piescope_gui import main


@pytest.fixture
def window(qtbot, monkeypatch):
    """Pass the application to the test functions via a pytest fixture."""
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    with mock.patch.object(main.GUIMainWindow, 'connect_to_fibsem_microscope'):
        new_window = main.GUIMainWindow()
        qtbot.add_widget(new_window)
        return new_window


def test_window_title(window):
    """Check that the window title shows as declared."""
    assert window.windowTitle() == 'PIEScope User Interface Main Window'


def test_window_geometry(window):
    """Check that the window width and height are set as declared."""
    # PyQt5 with Python>=3.5 appears buggy, window resize is off
    # We assert a relatively wide range instead of a single number
    margin_of_error = 50  # pixels
    assert window.width() > 1623 - margin_of_error
    assert window.width() < 1623 + margin_of_error
    assert window.height() > 739 - margin_of_error
    assert window.height() < 739 + margin_of_error


def test_open_images_FM(window, qtbot):
    """Check that when opening a FM image from the drop down menu,
    calls the correct function with correct input parameter 'FM'"""
    with mock.patch('piescope_gui.main.GUIMainWindow.open_images') as mock_open:
        qtbot.mouseClick(window.menuOpen, Qt.LeftButton)
        qtbot.keyClick(window.menuOpen, Qt.Key_Down)
        qtbot.keyClick(window.menuOpen, Qt.Key_Right)
        qtbot.keyClick(window.menuOpen, Qt.Key_Enter)
        mock_open.assert_called_once()
        mock_open.assert_called_with('FM')


def test_open_images_FIBSEM(window, qtbot):
    """Check that when opening a FIBSEM image from the drop down menu,
    calls the correct function with correct input parameter 'FIBSEM'"""
    with mock.patch('piescope_gui.main.GUIMainWindow.open_images') as mock_open:
        qtbot.mouseClick(window.menuOpen, Qt.LeftButton)
        qtbot.keyClick(window.menuOpen, Qt.Key_Down)
        qtbot.keyClick(window.menuOpen, Qt.Key_Right)
        qtbot.keyClick(window.menuOpen, Qt.Key_Down)
        qtbot.keyClick(window.menuOpen, Qt.Key_Enter)
        mock_open.assert_called_once()
        mock_open.assert_called_with('FIBSEM')


def test_about_dialog(window, qtbot, mocker):
    """Test the About item of the Help submenu.

    Qtbot clicks on the help sub menu and then navigates to the About item.
    Mock creates a QDialog object to be used for the test.
    """
    qtbot.mouseClick(window.menuHelp, Qt.LeftButton)
    qtbot.keyClick(window.menuHelp, Qt.Key_Down)
    mocker.patch.object(QDialog, 'exec_', return_value='accept')
    qtbot.keyClick(window.menuHelp, Qt.Key_Enter)


@pytest.mark.parametrize("modality", [
    ("FM"),
    ("FIBSEM"),
])
def test_fill_destination(window, tmpdir, modality):
    expected = str(tmpdir) + os.path.sep
    with mock.patch.object(main.QtWidgets.QFileDialog, 'getExistingDirectory') as mocker:
        mocker.return_value = tmpdir
        window.checkBox_save_destination_FM.setChecked(0)
        window.checkBox_save_destination_FIBSEM.setChecked(0)
        output = window.fill_destination(modality)
        assert output == expected
        if modality == "FM":
            assert window.lineEdit_save_destination_FM.text() == expected
        elif modality == "FIBSEM":
            assert window.lineEdit_save_destination_FIBSEM.text() == expected
        else:
            assert False  # should never reach this case, fail test if so.


def test_fill_correlation_destination(window, tmpdir):
    expected = str(tmpdir) + os.path.sep
    with mock.patch.object(main.QtWidgets.QFileDialog, 'getExistingDirectory') as mocker:
        mocker.return_value = tmpdir
        output = window.fill_correlation_destination()
        assert output == expected
        assert window.correlation_output_path.text() == expected
