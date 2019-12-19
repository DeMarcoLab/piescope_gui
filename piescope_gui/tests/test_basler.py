import mock
import time

import numpy as np
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

import piescope

from piescope_gui import main


@pytest.fixture
def window(qtbot, monkeypatch):
    """Pass the application to the test functions via a pytest fixture."""
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    with mock.patch.object(main.GUIMainWindow, 'connect_to_fibsem_microscope'):
        new_window = main.GUIMainWindow()
        qtbot.add_widget(new_window)
        return new_window


@pytest.mark.parametrize("wavelength", [
    ("640nm"),
    ("561nm"),
    ("488nm"),
    ("405nm"),
])
@pytest.mark.parametrize("exposure_time", [
    (150),  # in microseconds
    (200),  # in microseconds
])
@pytest.mark.parametrize("laser_power", [
    (0.1),
    (1.0),
])
def test_fluorescence_image(window, monkeypatch, wavelength, exposure_time, laser_power):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    output = window.fluorescence_image(wavelength, exposure_time, laser_power)
    expected = piescope.data.basler_image()
    # Basler emulated mode produces images with shape (1040, 1024)
    # The real Basler detector in the lab produces images with shape (1200, 1920)
    assert output.shape == (1040, 1024) or output.shape == (1200, 1920)
    if output.shape == (1040, 1024):  # emulated image
        assert np.allclose(output, expected)
        assert np.allclose(window.array_list_FM, expected)


@pytest.mark.parametrize("wavelength", [
    ("640nm"),
    ("561nm"),
    ("488nm"),
    ("405nm"),
])
def test_fluorescence_live_imaging(window, monkeypatch, wavelength):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    exposure_time = 150  # in microseconds
    laser_power = 1.0
    window.fluorescence_live_imaging(wavelength, exposure_time, laser_power)
    time.sleep(0.5)          # run live imaging for half a second
    window.stop_event.set()  # stop live imaging
    # Basler emulated mode produces images with shape (1040, 1024)
    # The real Basler detector in the lab produces images with shape (1200, 1920)
    assert window.array_list_FM.shape == (1040, 1024) or window.array_list_FM.shape == (1200, 1920)
    if window.array_list_FM.shape == (1040, 1024):  # emulated image
        expected = piescope.data.basler_image()
        assert np.allclose(window.array_list_FM, expected)
