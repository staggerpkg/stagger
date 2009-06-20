# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import abc
import collections

from abc import abstractmethod

from stagger.conversion import *
from stagger.errors import *

# The idea for the Spec system comes from Mutagen.

def optionalspec(spec):
    spec._optional = True
    return spec

class Spec(metaclass=abc.ABCMeta):
    def __init__(self, name):
        self.name = name

    _optional = False
        
    @abstractmethod
    def read(self, frame, data): pass

    @abstractmethod
    def write(self, frame, value): pass

    def validate(self, frame, value):
        self.write(frame, value)
        return value

    def to_str(self, value):
        return "{0}={1}".format(self.name, repr(value))

class ByteSpec(Spec):
    def read(self, frame, data):
        if len(data) < 1:
            raise EOFError()
        return data[0], data[1:]
    def write(self, frame, value):
        return bytes([value])
    def validate(self, frame, value):
        if not isinstance(value, int):
            raise TypeError("Not a byte")
        if  value not in range(256):
            raise ValueError("Invalid byte value")
        return value

class IntegerSpec(Spec):
    def __init__(self, name, width):
        super().__init__(name)
        self.width = width
    def read(self, frame, data):
        if len(data) < self.width:
            raise EOFError()
        return Int8.decode(data[:self.width]), data[self.width:]
    def write(self, frame, value):
        return Int8.encode(value, width=self.width)
    def validate(self, frame, value):
        if type(value) is not int: 
            raise TypeError("Not an integer: {0}".format(repr(value)))
        if value < 0:
            raise ValueError("Value is negative")
        if value >= 1 << (self.width << 3):
            raise ValueError("Value is too large")
        return value

class SignedIntegerSpec(Spec):
    def __init__(self, name, width):
        super().__init__(name)
        self.width = width
    def read(self, frame, data):
        if len(data) < self.width:
            raise EOFError()
        val = Int8.decode(data[:self.width])
        if data[0] & 0x80:
            # Negative value
            val -= (1 << (self.width << 3))
        return val, data[self.width:]
    def write(self, frame, value):
        if value < 0:
            value += (1 << (self.width << 3))
        return Int8.encode(value, width=self.width)
    def validate(self, frame, value):
        if type(value) is not int: 
            raise TypeError("Not an integer")
        if value >= (1 << ((self.width << 3) - 1)):
            raise ValueError("Value is too large")
        if value < -(1 << ((self.width << 3) - 1)):
            raise ValueError("Value is too small")
        return value

class VarIntSpec(Spec):
    def read(self, frame, data):
        if len(data) == 0:
            raise EOFError()
        bits = data[0]
        data = data[1:]
        bytes = (bits + 7) >> 3
        if len(data) < bytes:
            raise EOFError()
        return Int8.decode(data[:bytes]), data[bytes:]
    def write(self, frame, value):
        bytes = 4
        t = value >> 32
        while t > 0:
            t >>= 32
            bytes += 4
        return Int8.encode(bytes * 8, width=1) + Int8.encode(value, width=bytes)
    def validate(self, frame, value):
        if type(value) is not int:
            raise TypeError("Not an integer")
        if value < 0:
            raise ValueError("Value is negative")
        return value

class BinaryDataSpec(Spec):
    def read(self, frame, data):
        return data, bytes()
    def write(self, frame, value):
        return bytes(value)
    def validate(self, frame, value):
        if not isinstance(value, collections.ByteString):
            raise TypeError("Not a byte sequence")
        return value
    def to_str(self, value):
        return '{0}={1}{2}'.format(self.name, value[0:16], "..." if len(value) > 16 else "")

class SimpleStringSpec(Spec):
    def __init__(self, name, length):
        super().__init__(name)
        self.length = length
    def read(self, frame, data):
        return data[:self.length].decode('iso-8859-1'), data[self.length:]
    def write(self, frame, value):
        if value is None:
            return b" " * self.length
        data = value.encode('iso-8859-1')
        if len(data) != self.length:
            raise ValueError("String length mismatch")
        return data
    def validate(self, frame, value):
        if not isinstance(value, str):
            raise TypeError("Not a string")
        if len(value) != self.length: 
            raise ValueError("String length mismatch")
        value.encode('iso-8859-1')
        return value

class LanguageSpec(SimpleStringSpec):
    def __init__(self, name):
        super().__init__(name, 3)
    
class NullTerminatedStringSpec(Spec):
    def read(self, frame, data):
        rawstr, sep, data = data.partition(b"\x00")
        return rawstr.decode('iso-8859-1'), data
    def write(self, frame, value):
        return value.encode('iso-8859-1') + b"\x00"
    def validate(self, frame, value):
        if not isinstance(value, str):
            raise TypeError("Not a string")
        value.encode('iso-8859-1')
        return value

class URLStringSpec(Spec):
    def read(self, frame, data):
        rawstr, sep, data = data.partition(b"\x00")
        if len(rawstr) == 0 and len(data) > 0:
            # iTunes prepends an extra null byte to WFED frames (encoding spec?)
            #warn("Frame {0} includes a text encoding byte".format(frame.frameid), Warning)
            rawstr, sep, data = data.partition(b"\x00")
        return rawstr.decode('iso-8859-1'), data
    def write(self, frame, value):
        return value.encode('iso-8859-1') + b"\x00"
    def validate(self, frame, value):
        if not isinstance(value, str):
            raise TypeError("Not a string")
        value.encode('iso-8859-1')
        return value

class EncodingSpec(ByteSpec):
    "EncodingSpec must be the first spec."
    def read(self, frame, data):
        enc, data = super().read(frame, data)
        if enc & 0xFC:
            raise FrameError("Invalid encoding")
        return enc, data
    def write(self, frame, value):
        return super().write(frame, value)
    def validate(self, frame, value):
        if isinstance(value, str):
            value = value.lower().replace("-", "")
            for i in range(len(EncodedStringSpec._encodings)):
                if EncodedStringSpec._encodings[i][0].lower().replace("-", "") == value:
                    value = i
                    break
        if not isinstance(value, int):
            raise TypeError("Not an encoding")
        if 0 <= value <= 3:
            return value
        raise ValueError("Invalid encoding 0x{0:X}".format(value))
    def to_str(self, value):
        return EncodedStringSpec._encodings[value][0]

class EncodedStringSpec(Spec):
    _encodings = (('iso-8859-1', b"\x00"),
                  ('utf-16', b"\x00\x00"),
                  ('utf-16-be', b"\x00\x00"),
                  ('utf-8', b"\x00"))
    preferred_encodings = (0, 1)

    def read(self, frame, data):
        enc, term = self._encodings[frame.encoding]
        if len(term) == 1:
            rawstr, sep, data = data.partition(term)
        else:
            index = len(data)
            for i in range(0, len(data), 2):
                if data[i:i+2] == term:
                    index = i
                    break
            #if index == len(data):
            #    warn("Unterminated string in frame '{0}'".format(frame.frameid), Warning)
            if index & 1:
                raise EOFError()
            rawstr = data[:index]
            data = data[index+2:]
        return rawstr.decode(enc), data

    def write(self, frame, value):
        if frame.encoding != None:
            enc, term = self._encodings[frame.encoding]
            return value.encode(enc) + term
        else:
            enc, term = self._encodings[frame.encoding]
            return value.encode(enc) + term

    def validate(self, frame, value):
        if not isinstance(value, str):
            raise TypeError("Not a string")
        self.write(frame, value)
        return value

class EncodedFullTextSpec(EncodedStringSpec):
    pass # TODO

class SequenceSpec(Spec):
    """Recognizes a sequence of values, all of the same spec."""
    def __init__(self, name, spec):
        super().__init__(name)
        self.spec = spec

    def read(self, frame, data):
        "Returns a list of values, eats all of data."
        seq = []
        while data:
            elem, data = self.spec.read(frame, data)
            seq.append(elem)
        return seq, data

    def write(self, frame, values):
        if isinstance(values, str):
            return self.spec.write(frame, values)
        data = bytearray()
        for v in values:
            data.extend(self.spec.write(frame, v))
        return data

    def validate(self, frame, values):
        if isinstance(values, str):
            values = [values]
        return [self.spec.validate(frame, v) for v in values]

class MultiSpec(Spec):
    def __init__(self, name, *specs):
        super().__init__(name)
        self.specs = specs

    def read(self, frame, data):
        seq = []
        while data:
            record = []
            for s in self.specs:
                elem, data = s.read(frame, data)
                record.append(elem)
            seq.append(tuple(record))
        return seq, data

    def write(self, frame, values):
        data = bytearray()
        for v in values:
            for i in range(len(self.specs)):
                data.extend(self.specs[i].write(frame, v[i]))
        return bytes(data)

    def validate(self, frame, values):
        res = []
        for v in values:
            if not isinstance(v, collections.Sequence) or isinstance(v, str):
                raise TypeError("Records must be sequences")
            if len(v) != len(self.specs):
                raise ValueError("Invalid record length")
            res.append(tuple(self.specs[i].validate(frame, v[i])
                             for i in range(len(self.specs))))
        return res

class ASPISpec(Spec):
    "A list of frame.N integers whose width depends on frame.b."
    def read(self, frame, data):
        width = 1 if frame.b == 1 else 2
        value = []
        if len(data) < width * frame.N:
            raise EOFError
        for i in range(frame.N):
            value.append(Int8.decode(data[:width]))
            data = data[width:]
        return value, data

    def write(self, frame, values):
        width = 1 if frame.b == 1 else 2
        data = bytearray()
        for v in values:
            data.extend(Int8.encode(v, width=width))
        return data
    
    def validate(self, frame, values):
        if not isinstance(values, collections.Sequence) or isinstance(values, str):
            raise TypeError("ASPISpec needs a sequence of integers")
        if len(values) != frame.N:
            raise ValueError("ASPISpec needs {0} integers".format(frame.N))
        self.write(frame, values)
        res = []
        for v in values:
            res.append(v)
        return res

