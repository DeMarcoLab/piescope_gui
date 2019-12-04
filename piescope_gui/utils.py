import logging
import time

from PyQt5 import QtWidgets


def display_error_message(message):
    """PyQt dialog box displaying an error message."""
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
