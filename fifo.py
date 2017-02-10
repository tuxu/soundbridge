"""FIFO.

A Numpy-based of a first-in first-out buffer (FIFO) implemented as a ring buffer
that allows reading and writing chunks of data.
"""

__author__ = 'Tino Wagner <ich@tinowagner.com>'
__copyright__ = 'Copyright (c) 2017 Tino Wagner'
__license__ = 'MIT'

import numpy as np


class UnderflowError(Exception):
    """Buffer underflow exception."""
    pass


class FIFO(object):
    """Implements a FIFO based on a ring buffer.

    Parameters
    ----------
    size : int
        Buffer size.
    dtype : data-type, optional
        Data type of the buffer elements. Defaults to `np.float`.
    """

    def __init__(self, size, dtype=np.float):
        self._buf = np.zeros(size, dtype)
        self._write_index = 0
        self._read_index = 0
        self._is_full = False

    def write(self, data):
        """Write data into the buffer.

        Parameters
        ----------
        data : array_like
            Data to write.
        """
        ind = (self._write_index + np.arange(data.size)) % self._buf.size
        self._buf[ind] = data
        self._write_index = (ind[-1] + 1) % self._buf.size
        # Fix read index to oldest available data if buffer is filled.
        if data.size >= self._buf.size:
            self._read_index = self._write_index
            self._is_full = True

    def read(self, size):
        """Read a number of buffer elements.

        Parameters
        ----------
        size : int
            Number of elements to read.

        Returns
        -------
        elements : ndarray
            An array of buffer elements.

        Raises
        ------
        UnderflowError
            If more elements are requested than are available.
        """
        num_avail = self.num_available()
        if size == 0:
            return []
        if size > num_avail:
            raise UnderflowError(
                'Requested: {} Available: {}'.format(size, num_avail))
        ind = (self._read_index + np.arange(size)) % self._buf.size
        self._read_index = (ind[-1] + 1) % self._buf.size
        if self._write_index == self._read_index:
            self._is_full = False
        return self._buf[ind]

    def num_available(self):
        """Return the number of available values."""
        num_avail = (self._write_index - self._read_index) % self._buf.size
        if num_avail == 0:
            return self._buf.size if self._is_full else 0
        return num_avail
