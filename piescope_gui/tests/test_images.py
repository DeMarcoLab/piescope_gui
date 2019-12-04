import mock
import os

import numpy as np
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog
import skimage.data
import skimage.io

import piescope_gui
from piescope_gui import main


@pytest.fixture
def window(qtbot, monkeypatch):
    """Pass the application to the test functions via a pytest fixture."""
    monkeypatch.setenv("PYLON_CAMEMU", "1")
    with mock.patch.object(piescope_gui.main.GUIMainWindow, 'connect_to_fibsem_microscope'):
        new_window = piescope_gui.main.GUIMainWindow()
        qtbot.add_widget(new_window)
        return new_window


def test_open_images_fluorescence(window, tmpdir):
    filename = os.path.join(str(tmpdir), 'astronaut.tif')
    skimage.io.imsave(filename, skimage.data.astronaut())
    with mock.patch.object(piescope_gui.main.QtWidgets.QFileDialog, "getOpenFileNames") as mocker:
        mocker.return_value = [[filename], '.tif']
        window.open_images("FM")


def test_open_images_fibsem(window, tmpdir):
    filename = os.path.join(str(tmpdir), 'camera.tif')
    skimage.io.imsave(filename, skimage.data.camera())
    with mock.patch.object(piescope_gui.main.QtWidgets.QFileDialog, "getOpenFileNames") as mocker:
        mocker.return_value = [[filename], '.tif']
        window.open_images("FIBSEM")


def test_save_image_fluorescence(window, tmpdir):
    input_image = skimage.data.astronaut()
    window.lineEdit_save_destination_FM.setText(str(tmpdir))
    expected_filename = 'test_save_image_FM_filename'
    window.lineEdit_save_filename_FM.setText(expected_filename)
    window.current_image_FM = input_image
    window.array_list_FM = [input_image]
    window.save_image("FM")
    assert expected_filename + '.tif' in os.listdir(tmpdir)
    full_filepath = os.path.join(str(tmpdir), expected_filename + '.tif')
    result = skimage.io.imread(full_filepath)
    assert np.allclose(result, input_image)


def test_save_image_fibsem(window, tmpdir):
    input_image = skimage.data.astronaut()
    window.lineEdit_save_destination_FIBSEM.setText(str(tmpdir))
    expected_filename = 'test_save_image_FIBSEM_filename'
    window.lineEdit_save_filename_FIBSEM.setText(expected_filename)
    window.fibsem_image = input_image
    window.current_image_FIBSEM = input_image
    window.array_list_FIBSEM = [input_image]
    window.save_image("FIBSEM")
    assert expected_filename + '.tif' in os.listdir(tmpdir)
    full_filepath = os.path.join(str(tmpdir), expected_filename + '.tif')
    result = skimage.io.imread(full_filepath)
    assert np.allclose(result, input_image)

############# Test you can't overwrite existing images ##############
def test_save_image_fluorescence_no_overwrite(window, tmpdir):
    input_image = skimage.data.astronaut()
    window.lineEdit_save_destination_FM.setText(str(tmpdir))
    expected_filename = 'test_save_image_FM_filename'
    window.lineEdit_save_filename_FM.setText(expected_filename)
    window.current_image_FM = input_image
    window.array_list_FM = [input_image]
    window.save_image("FM")
    assert expected_filename + '.tif' in os.listdir(tmpdir)
    full_filepath = os.path.join(str(tmpdir), expected_filename + '.tif')
    result = skimage.io.imread(full_filepath)
    assert np.allclose(result, input_image)
    # Try to save a second image with the same filepath
    window.save_image("FM")
    assert expected_filename + '(1).tif' in os.listdir(tmpdir)
    full_filepath_1 = os.path.join(str(tmpdir), expected_filename + '(1).tif')
    result_1 = skimage.io.imread(full_filepath_1)
    assert np.allclose(result_1, input_image)


def test_save_image_fibsem_no_overwrite(window, tmpdir):
    input_image = skimage.data.astronaut()
    window.lineEdit_save_destination_FIBSEM.setText(str(tmpdir))
    expected_filename = 'test_save_image_FIBSEM_filename'
    window.lineEdit_save_filename_FIBSEM.setText(expected_filename)
    window.fibsem_image = input_image
    window.current_image_FIBSEM = input_image
    window.array_list_FIBSEM = [input_image]
    window.save_image("FIBSEM")
    assert expected_filename + '.tif' in os.listdir(tmpdir)
    full_filepath = os.path.join(str(tmpdir), expected_filename + '.tif')
    result = skimage.io.imread(full_filepath)
    assert np.allclose(result, input_image)
    # Try to save a second image with the same filepath
    window.save_image("FIBSEM")
    assert expected_filename + '(1).tif' in os.listdir(tmpdir)
    full_filepath = os.path.join(str(tmpdir), expected_filename + '(1).tif')
    result = skimage.io.imread(full_filepath)
    assert np.allclose(result, input_image)
