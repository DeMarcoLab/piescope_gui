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
        with mock.patch('piescope.lm.laser.connect_serial_port'):
            new_window = main.GUIMainWindow(offline=True)
            qtbot.add_widget(new_window)
            yield new_window
            new_window.disconnect()


@pytest.mark.parametrize("wavelength", [
    ("640nm"),
    ("561nm"),
    ("488nm"),
    ("405nm"),
])
@pytest.mark.parametrize("exposure_time", [
    (150),  # in milliseconds (ms)
    (200),  # in milliseconds (ms)
])
@pytest.mark.parametrize("laser_power", [
    (0.1),
    (1.0),
])
def test_fluorescence_image(window, monkeypatch, tmpdir, wavelength, exposure_time, laser_power):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    window.save_destination_FM = tmpdir
    output = window.fluorescence_image(wavelength, exposure_time, laser_power)
    expected = piescope.data.basler_image()
    # Basler emulated mode produces images with shape (1040, 1024)
    # The real Basler detector in the lab produces images with shape (1200, 1920)
    assert output.shape == (1040, 1024) or output.shape == (1200, 1920)
    if output.shape == (1040, 1024):  # emulated image
        assert np.allclose(output, expected)
        assert np.allclose(window.array_list_FM, expected)


# Do not parameterize this test function
def test_fluorescence_live_imaging(window, monkeypatch):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    wavelength = "640nm"  # "640nm", "561nm", "488nm", "405nm"
    exposure_time = 150  # in microseconds
    laser_power = 1.0
    # Start live imaging
    window.fluorescence_live_imaging(wavelength, exposure_time, laser_power)
    time.sleep(0.2)          # run live imaging for half a second
    window.stop_event.set()  # stop live imaging
    # Basler emulated mode produces images with shape (1040, 1024)
    # The real Basler detector in the lab produces images with shape (1200, 1920)
    assert window.array_list_FM.shape == (1040, 1024) or window.array_list_FM.shape == (1200, 1920)
    if window.array_list_FM.shape == (1040, 1024):  # emulated image
        expected = piescope.data.basler_image()
        assert np.allclose(window.array_list_FM, expected)


def test_fluorescence_live_imaging_stop_start(window, monkeypatch):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    wavelength = "640nm"  # "640nm", "561nm", "488nm", "405nm"
    exposure_time = 150  # in microseconds
    laser_power = 1.0
    # Start live imaging
    window.fluorescence_live_imaging(wavelength, exposure_time, laser_power)
    time.sleep(0.2)          # run live imaging for half a second
    window.stop_event.set()  # stop live imaging
    # Start live imaging again
    window.fluorescence_live_imaging(wavelength, exposure_time, laser_power)
    time.sleep(0.2)          # run live imaging for half a second
    window.stop_event.set()  # stop live imaging
    # Basler emulated mode produces images with shape (1040, 1024)
    # The real Basler detector in the lab produces images with shape (1200, 1920)
    assert window.array_list_FM.shape == (1040, 1024) or window.array_list_FM.shape == (1200, 1920)
    if window.array_list_FM.shape == (1040, 1024):  # emulated image
        expected = piescope.data.basler_image()
        assert np.allclose(window.array_list_FM, expected)
