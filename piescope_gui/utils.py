import logging
import time
import traceback

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
