import skimage.io as io
from pypylon import pylon

class Basler():
    def __init__(self):
        super(Basler, self).__init__()
        self.camera = pylon.InstantCamera(
            pylon.TlFactory.GetInstance().CreateFirstDevice())
        print("Using device ", self.camera.GetDeviceInfo().GetModelName());
        self.camera.MaxNumBuffer = 5
        self.imageCount = 1
        self.currentImageIndex = 0
        self.image = []

    def camera_grab(self):
        self.camera.StartGrabbingMax(self.imageCount)
        self.image = []

        while self.camera.IsGrabbing():
            grabResult = self.camera.RetrieveResult(
                5000, pylon.TimeoutHandling_ThrowException)

            if grabResult.GrabSucceeded():
                print("SizeX: ", grabResult.Width)
                print("SizeY: ", grabResult.Height)
                self.image = grabResult.Array
            else:
                print("Error: ", grabResult.Errorcode, grabResult.ErrorDescription)
            grabResult.Release()
        return self.image


def create_array_list(input_list):

    if len(input_list) > 1:
        array_list = io.imread_collection(input_list)
    else:
        array_list = io.imread(input_list[0])

    return array_list


def save_image(image, dest):
    io.imsave(dest, image)


def get_basler_image(self):
    basler = Basler()
    self.string_list = ["Basler_image"]
    self.array_list = basler.camera_grab()
    self.update_display()
