import mock

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


@pytest.mark.parametrize("expected_position", [
    # expected position in microns (um) for convenience
    # (SMARACT stage expects & works in nanometer units)
    (-1),
    (0),
    (2.5),
])
@mock.patch.object(main.piescope.lm.objective.StageController, 'current_position')
@mock.patch.object(main.piescope.lm.objective.StageController, 'recv')
@mock.patch.object(main.piescope.lm.objective.StageController, 'sendall')
def test_initialize_objective_stage(mock_sendall, mock_recv, mock_pos, window, expected_position):
    mock_pos.return_value = expected_position * 1000 # nanometers for SMARACT
    result = window.initialize_objective_stage(testing=True)
    assert isinstance(result, main.piescope.lm.objective.StageController)
    result_label = float(window.label_objective_stage_position.text())  # um
    assert np.isclose(result_label, expected_position)


@pytest.mark.parametrize("expected_position", [
    # expected position in microns (um) for convenience
    # (SMARACT stage expects & works in nanometer units)
    (-1),
    (0),
    (2.5),
])
@mock.patch.object(main.piescope.lm.objective.StageController, 'current_position')
@mock.patch.object(main.piescope.lm.objective.StageController, 'recv')
@mock.patch.object(main.piescope.lm.objective.StageController, 'sendall')
def test_get_objective_stage_position(mock_sendall, mock_recv, mock_pos, window, expected_position):
    mock_pos.return_value = expected_position * 1000  # nanometers for SMARACT
    window.objective_stage = main.piescope.lm.objective.StageController(testing=True)
    result = window.get_objective_stage_position()
    result_label = float(window.label_objective_stage_position.text())  # um
    assert np.isclose(result_label, expected_position)
    assert np.isclose(result, expected_position)  # mocked, so not very useful


@pytest.mark.parametrize("expected_position", [
    # expected position in microns (um) for convenience
    # (SMARACT stage expects & works in nanometer units)
    (-0.001),
    (0.0),
    (0.0025),
])
@mock.patch.object(main.piescope.lm.objective.StageController, 'current_position')
@mock.patch.object(main.piescope.lm.objective.StageController, 'recv')
@mock.patch.object(main.piescope.lm.objective.StageController, 'sendall')
def test_save_objective_stage_position(mock_sendall, mock_recv, mock_pos, window, expected_position):
    mock_pos.return_value = expected_position * 1000  # nanometers for SMARACT
    window.objective_stage = main.piescope.lm.objective.StageController(testing=True)
    window.label_objective_stage_saved_position.setText("")
    assert window.label_objective_stage_saved_position.text() == ""
    position_text = str(expected_position)
    window.label_objective_stage_position.setText(position_text)
    assert window.label_objective_stage_position.text() == position_text
    window.save_objective_stage_position()
    assert window.label_objective_stage_saved_position.text() == position_text


@pytest.mark.parametrize("input_position", [
    # expected position in microns (um) for convenience
    # (SMARACT stage expects & works in nanometer units)
    (-1),
    (0),
    (2.5),
])
@mock.patch.object(main.piescope.lm.objective.StageController, 'current_position')
@mock.patch.object(main.piescope.lm.objective.StageController, 'recv')
@mock.patch.object(main.piescope.lm.objective.StageController, 'sendall')
def test_move_to_saved_objective_position(mock_sendall, mock_recv, mock_pos, window, input_position):
    window.objective_stage = main.piescope.lm.objective.StageController(testing=True)
    window.label_objective_stage_saved_position.setText(str(float(input_position)))
    mock_pos.return_value = input_position * 1000  # nanometers for SMARACT
    output = window.move_to_saved_objective_position()
    # This is all mocked, so we expect of course this will be the case:
    assert window.label_objective_stage_saved_position.text() == str(float(input_position))
    assert window.label_objective_stage_position.text() == str(float(input_position))
    assert np.isclose(output, input_position)


@pytest.mark.parametrize("input_position", [
    # expected position in microns (um) for convenience
    # (SMARACT stage expects & works in nanometer units)
    (-1),
    (0),
    (2.5),
])
@mock.patch.object(main.piescope.lm.objective.StageController, 'current_position')
@mock.patch.object(main.piescope.lm.objective.StageController, 'recv')
@mock.patch.object(main.piescope.lm.objective.StageController, 'sendall')
def test_move_absolute_objective_stage(mock_sendall, mock_recv, mock_pos, window, input_position):
    window.objective_stage = main.piescope.lm.objective.StageController(testing=True)
    mock_pos.return_value = input_position * 1000  # nanometers for SMARACT
    output = window.move_absolute_objective_stage(position=input_position,
                                                  time_delay=0.01)
    output_label = float(window.label_objective_stage_position.text())
    assert np.isclose(output, input_position)
    assert np.isclose(output_label, input_position)


@pytest.mark.parametrize("relative_distance", [
    (-1),
    (0),
    (2.5),
])
@pytest.mark.parametrize("original_position", [
    (0),
    (2),
])
@mock.patch.object(main.piescope.lm.objective.StageController, 'current_position')
@mock.patch.object(main.piescope.lm.objective.StageController, 'recv')
@mock.patch.object(main.piescope.lm.objective.StageController, 'sendall')
def test_move_relative_objective_stage(mock_sendall, mock_recv, mock_pos, window, relative_distance, original_position):
    window.objective_stage = main.piescope.lm.objective.StageController(testing=True)
    expected = original_position + relative_distance
    mock_pos.return_value = expected * 1000  # nanometers for SMARACT
    output = window.move_relative_objective_stage(distance=relative_distance,
                                                  time_delay=0.01)
    output_label = float(window.label_objective_stage_position.text())
    assert np.isclose(output, expected)
    assert np.isclose(output_label, expected)
