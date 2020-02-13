# import mock

# import numpy as np
# import pytest
# from PyQt5.QtCore import Qt
# from PyQt5.QtWidgets import QDialog

# import piescope
# from piescope_gui import main


# @pytest.fixture
# def window(qtbot, monkeypatch):
#     """Pass the application to the test functions via a pytest fixture."""
#     monkeypatch.setenv("PYLON_CAMEMU", "1")
#     with mock.patch.object(main.GUIMainWindow, 'connect_to_fibsem_microscope'):
#         new_window = main.GUIMainWindow()
#         qtbot.add_widget(new_window)
#         return new_window


# # @pytest_fixture
# # @mock.patch.object(piescope.lm.laser, 'connect_serial_port')
# # def lasers(window):
# #     window.lasers = piescope.lm.laser.initialize_lasers()
# #     assert len(window.lasers.keys()) == 4
# #     return window.lasers

# # @pytest.fixture
# # def dummy_serial_port():
# #     dummy_serial_port = SerialTestClass()
# #     return dummy_serial_port

# @mock.patch.object(piescope.lm.laser, 'connect_serial_port')
# @pytest.mark.parametrize("laser_name, laser_power", [
#     ("laser640", 0.0),
#     ("laser640", 0.5),
#     ("laser640", 1.0),
#     ("laser640", 1.5),
#     ("laser561", 0.0),
#     ("laser561", 0.5),
#     ("laser561", 1.0),
#     ("laser561", 1.5),
#     ("laser488", 0.0),
#     ("laser488", 0.5),
#     ("laser488", 1.0),
#     ("laser488", 1.5),
#     ("laser405", 0.0),
#     ("laser405", 0.5),
#     ("laser405", 1.0),
#     ("laser405", 1.5),
# ])
# def test_update_laser_dict(window, laser_name, laser_power):
#     window.lasers = piescope.lm.laser.initialize_lasers()
#     assert len(window.lasers.keys()) == 4
#     # hacky solution, set all lasers to the same power for the test
#     window.slider_laser1.setValue(laser_power)
#     window.slider_laser2.setValue(laser_power)
#     window.slider_laser3.setValue(laser_power)
#     window.slider_laser4.setValue(laser_power)
#     window.update_laser_dict(laser_name)
#     assert window.lasers[laser_name].enabled == True
#     assert np.isclose(window.lasers[laser_name].laser_power, laser_power)
