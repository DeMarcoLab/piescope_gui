import skimage.io as io


def create_array_list(input_list):

    if len(input_list) > 1:
        array_list = io.imread_collection(input_list)
    else:
        array_list = io.imread(input_list[0])

    return array_list


def save_image(image, dest):
    io.imsave(dest, image)


def update_laser_list_1(self):
    if self.checkBox_laser1.isChecked():
        self.laser_list.append("laser1")
        self.power_list.append("50")
        self.slider_laser1.setEnabled(1)
    else:
        self.laser_list.remove("laser1")
        self.power_list.remove("50")
        self.slider_laser1.setEnabled(0)


def update_laser_list_2(self):
    if self.checkBox_laser2.isChecked():
        self.laser_list.append("laser2")
        self.power_list.append("25")
        self.slider_laser2.setEnabled(1)
    else:
        self.laser_list.remove("laser2")
        self.power_list.remove("25")
        self.slider_laser2.setEnabled(0)


def update_laser_list_3(self):
    if self.checkBox_laser3.isChecked():
        self.laser_list.append("laser3")
        self.power_list.append("12")
        self.slider_laser3.setEnabled(1)

    else:
        self.laser_list.remove("laser3")
        self.power_list.remove("12")
        self.slider_laser3.setEnabled(0)


def update_laser_list_4(self):
    if self.checkBox_laser4.isChecked():
        self.laser_list.append("laser4")
        self.power_list.append("1")
        self.slider_laser4.setEnabled(1)

    else:
        self.laser_list.remove("laser4")
        self.power_list.remove("1")
        self.slider_laser4.setEnabled(0)


def update_laser_power_1(self):
    print(str(self.slider_laser1.value()))