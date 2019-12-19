import mock

import matplotlib.pyplot as plt
import numpy as np
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

import piescope

import piescope_gui.main

autoscript = pytest.importorskip(
    "autoscript_sdb_microscope_client", reason="Autoscript is not available."
)

try:
    from autoscript_sdb_microscope_client import SdbMicroscopeClient
    microscope = SdbMicroscopeClient()
    microscope.connect("localhost")
except Exception as e:
    pytest.skip("AutoScript cannot connect to localhost, skipping all AutoScript tests.",
                allow_module_level=True)


@pytest.fixture
def window(qtbot, monkeypatch):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    new_window = piescope_gui.main.GUIMainWindow(ip_address="localhost")
    assert hasattr(new_window, 'microscope')
    assert new_window.microscope is not None
    qtbot.add_widget(new_window)
    return new_window


def test_microscope_attr(window):
    assert hasattr(window, 'microscope')
    assert window.microscope is not None


def test_move_to_light_microscope(qtbot, monkeypatch):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    new_window = piescope_gui.main.GUIMainWindow(ip_address="localhost")
    old_position = new_window.microscope.specimen.stage.current_position
    new_window.move_to_light_microscope()
    new_position = new_window.microscope.specimen.stage.current_position
    expected_x_movement = +49.952e-3
    expected_y_movement = -0.1911e-3
    assert np.isclose(new_position.x, old_position.x + expected_x_movement)
    assert np.isclose(new_position.y, old_position.y + expected_y_movement)
    assert np.isclose(new_position.z, old_position.z)
    assert np.isclose(new_position.r, old_position.r)
    assert np.isclose(new_position.t, old_position.t)


def test_move_to_electron_microscope(qtbot, monkeypatch):
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    new_window = piescope_gui.main.GUIMainWindow(ip_address="localhost")
    old_position = new_window.microscope.specimen.stage.current_position
    new_window.move_to_electron_microscope()
    new_position = new_window.microscope.specimen.stage.current_position
    expected_x_movement = -49.952e-3
    expected_y_movement = +0.1911e-3
    assert np.isclose(new_position.x, old_position.x + expected_x_movement)
    assert np.isclose(new_position.y, old_position.y + expected_y_movement)
    assert np.isclose(new_position.z, old_position.z)
    assert np.isclose(new_position.r, old_position.r)
    assert np.isclose(new_position.t, old_position.t)


@pytest.mark.mpl_image_compare
def test_get_FIB_image(window):
    image = window.get_FIB_image()
    assert isinstance(image.data, np.ndarray)
    assert image.data.shape == (512, 768)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.imshow(image.data, cmap='Greys_r')
    return fig


@pytest.mark.mpl_image_compare
def test_get_last_FIB_image(window, tmpdir):
    window.DEFAULT_PATH = str(tmpdir)
    image = window.get_FIB_image()
    last_image = window.get_last_FIB_image()
    assert isinstance(image.data, np.ndarray)
    assert last_image.data.shape == (884, 1024)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.imshow(last_image.data, cmap='Greys_r')
    return fig


@pytest.mark.mpl_image_compare
def test_get_SEM_image(window):
    image = window.get_SEM_image()
    assert isinstance(image.data, np.ndarray)
    assert image.data.shape == (512, 768)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.imshow(image.data, cmap='Greys_r')
    return fig


@pytest.mark.mpl_image_compare
def test_get_last_SEM_image(window, tmpdir):
    window.DEFAULT_PATH = str(tmpdir)
    image = window.get_SEM_image()
    last_image = window.get_last_SEM_image()
    assert isinstance(image.data, np.ndarray)
    assert last_image.data.shape == (884, 1024)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.imshow(last_image.data, cmap='Greys_r')
    return fig


def test_autocontrast_ion_beam(window):
    image = window.autocontrast_ion_beam()
    assert isinstance(image.data, np.ndarray)
