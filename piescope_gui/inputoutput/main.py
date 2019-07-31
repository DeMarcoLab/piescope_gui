import skimage.io as io


def create_array_list(input_list):

    if len(input_list) > 1:
        array_list = io.imread_collection(input_list)
    else:
        array_list = io.imread(input_list[0])

    return array_list


def save_image(image, dest):
    io.imsave(dest, image)