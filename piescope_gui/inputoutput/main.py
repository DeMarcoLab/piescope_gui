import skimage.io as io
import threading
from piescope.lm import detector


def create_array_list(input_list):

    if len(input_list) > 1:
        array_list = io.imread_collection(input_list)
    else:
        array_list = io.imread(input_list[0])

    return array_list


def save_image(image, dest):
    io.imsave(dest, image)


def update_laser_list(self, laser):
    if laser == "laser1":
        laser_box = self.spinBox_laser1
        laser_check = self.checkBox_laser1
        laser_slider = self.slider_laser1
    elif laser == "laser2":
        laser_box = self.spinBox_laser2
        laser_check = self.checkBox_laser2
        laser_slider = self.slider_laser2
    elif laser == "laser3":
        laser_box = self.spinBox_laser3
        laser_check = self.checkBox_laser3
        laser_slider = self.slider_laser3
    elif laser == "laser4":
        laser_slider = self.slider_laser4
        laser_check = self.checkBox_laser4
        laser_box = self.spinBox_laser4
    else:
        ValueError()

    if laser_check.isChecked():
        self.laser_list[laser] = laser_box.text()
        laser_slider.setEnabled(1)
        laser_box.setEnabled(1)
        print(self.laser_list)
    else:
        self.laser_list.pop(laser)
        laser_slider.setEnabled(0)
        laser_box.setEnabled(0)


def update_laser_list_1(self):
    if self.checkBox_laser1.isChecked():
        x = self.spinBox_laser1.text()
        self.laser_list["laser1"] = x#self.spinBox_laser1.text()
        self.slider_laser1.setEnabled(1)
        self.spinBox_laser1.setEnabled(1)
        print(self.laser_list)
    else:
        self.laser_list.pop("laser1")
        self.slider_laser1.setEnabled(0)
        self.spinBox_laser1.setEnabled(0)
        print(self.laser_list)


def update_laser_list_2(self):
    if self.checkBox_laser2.isChecked():
        self.laser_list.append("laser2")
        self.power_list.append("25")
        self.slider_laser2.setEnabled(1)
        self.spinBox_laser2.setEnabled(1)
    else:
        self.laser_list.remove("laser2")
        self.power_list.remove("25")
        self.slider_laser2.setEnabled(0)
        self.spinBox_laser2.setEnabled(0)


def update_laser_list_3(self):
    if self.checkBox_laser3.isChecked():
        self.laser_list.append("laser3")
        self.power_list.append("12")
        self.slider_laser3.setEnabled(1)
        self.spinBox_laser3.setEnabled(1)
    else:
        self.laser_list.remove("laser3")
        self.power_list.remove("12")
        self.slider_laser3.setEnabled(0)
        self.spinBox_laser3.setEnabled(0)


def update_laser_list_4(self):
    if self.checkBox_laser4.isChecked():
        self.laser_list.append("laser4")
        self.power_list.append("1")
        self.slider_laser4.setEnabled(1)
        self.spinBox_laser4.setEnabled(1)
    else:
        self.laser_list.remove("laser4")
        self.power_list.remove("1")
        self.slider_laser4.setEnabled(0)
        self.spinBox_laser4.setEnabled(0)


def update_laser_power_1(self):
    if self.checkBox_laser1.isChecked():
        print(str(self.slider_laser1.value()))


def update_laser_power_2(self):
    print(str(self.slider_laser2.value()))


def update_laser_power_3(self):
    print(str(self.slider_laser3.value()))


def update_laser_power_4(self):
    print(str(self.slider_laser4.value()))


def get_basler_image(self):
    basler = detector.Basler()
    self.string_list = ["Basler_image"]
    self.array_list = basler.camera_grab()
    print(self.array_list)
    self.update_display()


def live_imaging(self):
    if self.liveCheck is True:
        self.stop_event = threading.Event()
        self.c_thread = threading.Thread(
            target=self.live_imaging_event_listener, args=(self.stop_event,))
        self.c_thread.start()
        self.liveCheck = False
        self.button_live_basler.setDown(True)
    else:
        self.stop_event.set()
        self.liveCheck = True
        self.button_live_basler.setDown(False)
