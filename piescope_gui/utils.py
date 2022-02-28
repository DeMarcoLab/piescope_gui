import logging
import time
import numpy as np

from PyQt5 import QtWidgets

__all__ = [
    'display_error_message',
    'timestamp',
    ]


def display_error_message(message):
    """PyQt dialog box displaying an error message."""
    print('display_error_message')
    logging.exception(message)
    error_dialog = QtWidgets.QErrorMessage()
    error_dialog.showMessage(message)
    error_dialog.exec_()
    return error_dialog


def timestamp():
    """Create timestamp string of current local time.

    Returns
    -------
    str
        Timestamp string
    """
    timestamp = time.strftime('%d-%b-%Y_%H-%M%p', time.localtime())
    return timestamp

def move_relative(microscope, x=0.0, y=0.0, z=0.0, r=0.0, t=0.0, settings=None):
    """Move the sample stage in ion or electron beam view and take new image

    Parameters
    ----------
    microscope : Autoscript microscope object.
    x : float, optional
        Relative movement in x in realspace co-ordinates.
    y : float, optional
        Relative movement in y in realspace co-ordinates.

    Returns
    -------
    StagePosition
        FIBSEM microscope sample stage position after moving.
        If the returned stage position is called 'stage_pos' then:
        stage_pos.x = the x position of the FIBSEM sample stage (in meters)
        stage_pos.y = the y position of the FIBSEM sample stage (in meters)
        stage_pos.z = the z position of the FIBSEM sample stage (in meters)
        stage_pos.r = the rotation of the FIBSEM sample stage (in radians)
        stage_pos.t = the tilt of the FIBSEM sample stage (in radians)
    """
    current_position_x = microscope.specimen.stage.current_position.x
    current_position_y = microscope.specimen.stage.current_position.y
    if current_position_x > 10e-3 or current_position_x < -10e-3:
        logging.error("Not under electron microscope, please reposition")
        return
    new_position = StagePosition(x=x, y=y, z=z, r=r, t=t)
    microscope.specimen.stage.relative_move(new_position, settings=settings)
    logging.info(f"Old position: {current_position_x*1e6}, {current_position_y*1e6}")
    logging.info(f"Moving by: {x*1e6}, {y*1e6}")
    logging.info(
        f"New position: {(current_position_x + x)*1e6}, {(current_position_y + y)*1e6}\n"
    )

    return microscope.specimen.stage.current_position


def pixel_to_realspace_coordinate(coord, image, pixel_size):
    """Convert pixel image coordinate to real space coordinate.

    This conversion deliberately ignores the nominal pixel size in y,
    as this can lead to inaccuracies if the sample is not flat in y.

    Parameters
    ----------
    coord : listlike, float
        In x, y format & pixel units. Origin is at the top left.

    image : AdornedImage
        Image the coordinate came from.

        # do we have a sample image somewhere?
    Returns
    -------
    realspace_coord
        xy coordinate in real space. Origin is at the image center.
        Output is in (x, y) format.
    """
    coord = np.array(coord).astype(np.float64)
    if len(image.data.shape) > 2:
        y_shape, x_shape = image.data.shape[0:2]
    else:
        y_shape, x_shape = image.data.shape

    pixelsize_x = pixel_size
    # deliberately don't use the y pixel size, any tilt will throw this off
    coord[1] = y_shape - coord[1]  # flip y-axis for relative coordinate system
    # reset origin to center
    coord -= np.array([x_shape / 2, y_shape / 2]).astype(np.int32)
    realspace_coord = list(np.array(coord) * pixelsize_x)  # to real space
    return realspace_coord
