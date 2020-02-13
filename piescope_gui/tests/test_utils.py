
import mock
import time

import pytest

import piescope_gui.utils


def test_display_error_message(qtbot):
    with mock.patch.object(piescope_gui.utils.QtWidgets.QErrorMessage, 'exec_'):
        error_dialog = piescope_gui.utils.display_error_message("Error message")
        qtbot.add_widget(error_dialog)
        assert error_dialog.result() == 0


def test_timestamp():
    with mock.patch('piescope_gui.utils.time.localtime') as mocker:
        # Mock return value of time.localtime()
        # tm_year=2019, tm_mon=12, tm_mday=2, tm_hour=11, tm_min=6, tm_sec=37,
        # tm_wday=0, tm_yday=336, tm_isdst=1
        mocker.return_value = time.struct_time((2019, 12, 2, 11, 6, 37, 0, 336, 1))
        expected = '02-Dec-2019_11-06AM'
        result = piescope_gui.utils.timestamp()
        assert result == expected
