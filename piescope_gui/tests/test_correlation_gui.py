import os
import mock

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
import skimage.data

import piescope.data
from piescope.data.mocktypes import MockAdornedImage

import piescope_gui.correlation.main
from piescope_gui import main


@pytest.fixture
def main_window(qtbot, monkeypatch):
    """Pass the application to the test functions via a pytest fixture."""
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    with mock.patch.object(main.GUIMainWindow, 'connect_to_fibsem_microscope'):
        new_window = main.GUIMainWindow()
        qtbot.add_widget(new_window)
        return new_window


def test_open_correlation_window(qtbot, main_window, tmpdir):
    fluorescence_image = skimage.data.astronaut()
    fibsem_image = MockAdornedImage(skimage.data.camera())
    window = piescope_gui.correlation.main.open_correlation_window(
        main_window, fluorescence_image, fibsem_image, tmpdir)
    qtbot.add_widget(window)
