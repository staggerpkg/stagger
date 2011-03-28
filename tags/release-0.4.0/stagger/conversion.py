# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

from stagger.errors import *
from warnings import warn

class Unsync:
    "Conversion from/to unsynchronized byte sequences."
    @staticmethod
    def gen_decode(iterable):
        "A generator for de-unsynchronizing a byte iterable."
        sync = False
        for b in iterable:
            if sync and b & 0xE0:
                warn("Invalid unsynched data", Warning)
            if not (sync and b == 0x00):
                yield b
            sync = (b == 0xFF)

    @staticmethod
    def gen_encode(data):
        "A generator for unsynchronizing a byte iterable."
        sync = False
        for b in data:
            if sync and (b == 0x00 or b & 0xE0):
                yield 0x00 # Insert sync char
            yield b
            sync = (b == 0xFF)
        if sync:
            yield 0x00 # Data ends on 0xFF

    @staticmethod
    def decode(data):
        "Remove unsynchronization bytes from data."
        return bytes(Unsync.gen_decode(data))

    @staticmethod
    def encode(data):
        "Insert unsynchronization bytes into data."
        return bytes(Unsync.gen_encode(data))

class UnsyncReader:
    "Unsynchronized file reader."
    def __init__(self, file):
        self.file = file
        self.gen = Unsync.gen_decode(self.__gen_readchar())

    def __gen_readchar(self):
        try:
            while True:
                yield self.file.read(1)[0]
        except EOFError:
            pass

    def read(self, n):
        data = bytes(b for i, b in zip(range(n), self.gen))
        if len(data) < n:
            raise EOFError
        return data

class Syncsafe:
    """Conversion to/from syncsafe integers.
    Syncsafe integers are big-endian 7-bit byte sequences.
    """
    @staticmethod
    def decode(data):
        "Decodes a syncsafe integer"
        value = 0
        for b in data:
            if b > 127:  # iTunes bug
                raise ValueError("Invalid syncsafe integer")
            value <<= 7
            value += b
        return value

    @staticmethod
    def encode(i, *, width=-1):
        """Encodes a nonnegative integer into syncsafe format

        When width > 0, then len(result) == width
        When width < 0, then len(result) >= abs(width)
        """
        if i < 0:
            raise ValueError("value is negative")
        assert width != 0
        data = bytearray()
        while i:
            data.append(i & 127)
            i >>= 7
        if width > 0 and len(data) > width:
            raise ValueError("Integer too large")
        if len(data) < abs(width):
            data.extend([0] * (abs(width) - len(data)))
        data.reverse()
        return data

class Int8:
    """Conversion to/from binary integer values of any length."""

    @staticmethod
    def decode(data):
        "Decodes an 8-bit big-endian integer of any length"
        value = 0
        for b in data:
            value <<= 8
            value += b
        return value

    @staticmethod
    def encode(i, *, width=-1):
        "Encodes a nonnegative integer into a big-endian bytearray of given length"
        assert width != 0
        if i is None:
            i = 0
        if i < 0: raise ValueError("Nonnegative integer expected")
        data = bytearray()
        while i:
            data.append(i & 255)
            i >>= 8
        if width > 0 and len(data) > width:
            raise ValueError("Integer too large")
        if len(data) < abs(width):
            data.extend([0] * (abs(width) - len(data)))
        return bytes(data[::-1])
