#!/usr/bin/python3
#
# Copyright (c) 2009, Karoly Lorentey
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# - Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# - Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import builtins
import struct
import abc
import re
import collections
from abc import abstractmethod
from warnings import warn
from contextlib import contextmanager
import imghdr

__all__ = ["read"]

class Error(Exception): pass

class Warning(Error, UserWarning): pass
class UntestedFrameWarning(Warning): pass
class BozoFrameWarning(Warning): pass

class NoTagError(Error): pass
class TagError(Error, ValueError): pass
class NotAFrameError(Error): pass
class FrameError(Error): pass
class IncompatibleFrameError(FrameError): pass

def xread(file, length):
    data = file.read(length)
    if len(data) != length:
        raise EOFError
    return data

class Unsync:
    @staticmethod
    def gen_decode(iterable):
        sync = False
        for b in iterable:
            if sync and b & 0xE0:
                warn("Invalid unsynched data", Warning)
            if not (sync and b == 0x00):
                yield b
            sync = (b == 0xFF)

    @staticmethod
    def gen_encode(data):
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
        return bytes(Unsync.gen_decode(data))

    @staticmethod
    def encode(data):
        return bytes(Unsync.gen_encode(data))

class UnsyncReader:
    def __init__(self, file):
        self.file = file
        self.gen = Unsync.gen_decode(self.__gen_read())

    def __gen_read(self):
        while True:
            yield xread(self.file, 1)[0]

    def read(self, n):
        try:
            buf = bytearray()
            while len(buf) != n:
                buf.append(next(self.gen))
            return buf
        except StopIteration:
            raise EOFError
    

class Syncsafe:
    @staticmethod
    def decode(data):
        "Decodes a syncsafe integer"
        value = 0
        for b in data:
            if b > 127:  # iTunes bug
                raise TagError("Invalid syncsafe integer")
            value <<= 7
            value += b
        return value

    @staticmethod
    def encode(i, *, width=-1):
        """Encodes a nonnegative integer into syncsafe format

        When width > 0, then len(result) == width
        When width < 0, then len(result) >= abs(width)
        """
        assert i >= 0
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
        if i < 0: raise ValueError("Nonnegative integer expected")
        data = bytearray()
        while i:
            data.append(i & 255)
            i >>= 8
        if width > 0 and len(data) > width:
            raise ValueError("Integer too large")
        if len(data) < abs(width):
            data.extend([0] * (abs(width) - len(data)))
        data.reverse()
        return data
    
class Tag(metaclass=abc.ABCMeta):
    known_frames = {}
    
    def __init__(self, file):
        self.flags = set()
        self.file = file

    def __str__(self):
        return "ID3v2.{0}(flags={{{1}}} size={2})".format(
            self.version, 
            " ".join(self.flags), 
            self.size)

    @abstractmethod
    def _reset(self): pass
    
    @abstractmethod
    def _read_one_frame(self): pass

    @abstractmethod
    def _encode_one_frame(self, frame): pass

    def frames(self):
        self._reset()
        fp = self._fp_frames_start
        while fp < self._fp_frames_end:
            try:
                oldfp = fp
                yield self._read_one_frame()
                fp = self.file.tell()
            except NotAFrameError:
                break

    def _is_frame_id(self, data):
        # Allow a single space at end of four-character ids
        # Some programs (e.g. iTunes 8.2) generate such frames when converting
        # from 2.2 to 2.3/2.4 tags.
        pattern = re.compile(b"^[A-Z][A-Z0-9]{2}[A-Z0-9 ]?$")
        return pattern.match(data)

    def _frame_from_data(self, frameid, data, flags=None):
        if flags is None: flags = {}
        if frameid in self.known_frames:
            return self.known_frames[frameid]._from_data(frameid, data, flags)
        flags["unknown"] = True
        if frameid.startswith('T'): # Unknown text frame
            return TextFrame._from_data(frameid, data, flags)
        elif frameid.startswith('W'): # Unknown URL frame
            return URLFrame._from_data(frameid, data, flags)
        else:
            return UnknownFrame._from_data(frameid, data, flags)

class Tag22(Tag):
    def __init__(self, file):
        self.version = 2
        super().__init__(file)
        self._fp_tag_start = file.tell()
        header = xread(file, 10)
        if header[0:5] != b"ID3\x02\00":
            raise TagError("ID3v2.2 header not found")
        if header[5] & 128:
            self.flags.add("unsynchronisation")
        if header[5] & 64: # Compression bit is ill-defined in standard
            raise TagError("ID3v2.2 tag compression is not supported")
        if header[5] & 63:
            raise TagError("Unknown ID3v2.2 flags")
        self.size = Syncsafe.decode(header[6:10])
        self._fp_frames_start = file.tell()
        self._fp_frames_end = self._fp_frames_start + 10 + self.size
        self._fp_tag_end = self._fp_frames_end
        self._reset()

    def _reset(self):
        self.file.seek(self._fp_frames_start)
        if "unsynchronisation" in self.flags:
            self.ufile = UnsyncReader(self.file)
            
    def _read(self, size):
        if "unsynchronisation" in self.flags:
            return self.ufile.read(size)
        else:
            return xread(self.file, size)

    known_frames = { }

    def _read_one_frame(self):
        header = self._read(6)
        if not self._is_frame_id(header[0:3]):
            raise NotAFrameError("Invalid frame id: {0}".format(header[0:3]))
        frameid = header[0:3].decode("ASCII")
        size = Int8.decode(header[3:6])
        data = self._read(size)
        try:
            return self._frame_from_data(frameid, data)
        except Exception as e:
            return ErrorFrame(frameid, data, e)

    def _encode_one_frame(self, frame):
        framedata = frame._to_data()

        data = bytearray()
        # Frame id
        if len(frame.frameid) != 3 or not self._is_frame_id(frame.frameid.encode("ASCII")):
            raise "Invalid ID3v2.2 frame id {0}".format(repr(frame.frameid))
        data.extend(frame.frameid.encode("ASCII"))
        # Size
        data.extend(Int8.encode(len(framedata), width=3))
        assert(len(data) == 6)
        data.extend(framedata)
        return data

class Tag23(Tag):
    __FRAME23_FORMAT_COMPRESSED = 0x0080
    __FRAME23_FORMAT_ENCRYPTED = 0x0040
    __FRAME23_FORMAT_GROUP = 0x0020
    __FRAME23_FORMAT_UNKNOWN_MASK = 0x001F

    __FRAME23_STATUS_DISCARD_ON_TAG_ALTER = 0x8000
    __FRAME23_STATUS_DISCARD_ON_FILE_ALTER = 0x4000
    __FRAME23_STATUS_READ_ONLY = 0x2000
    __FRAME23_STATUS_UNKNOWN_MASK = 0x1F00

    def __init__(self, file):
        self.version = 3
        super().__init__(file)
        self._fp_tag_start = file.tell()
        header = xread(file, 10)
        if header[0:5] != b"ID3\x03\x00":
            raise TagError("ID3v2.3 header not found")
        if header[5] & 0x80:
            self.flags.add("unsynchronisation")
        if header[5] & 0x40:
            self.flags.add("extended_header")
        if header[5] & 0x20:
            self.flags.add("experimental")
        if header[5] & 0x1F:
            warn("Unknown ID3v2.3 flags", Warning)
        self.size = Syncsafe.decode(header[6:10])
        if "extended_header" in self.flags:
            self.__read_extended_header()
        self._fp_frames_start = file.tell()
        self._fp_frames_end = self._fp_tag_start + 10 + self.size
        self._fp_tag_end = self._fp_frames_end
        self._reset()

    def _reset(self):
        self.file.seek(self._fp_frames_start)
        if "unsynchronisation" in self.flags:
            self.ufile = UnsyncReader(self.file)
        
    def _read(self, size):
        if "unsynchronisation" in self.flags:
            return self.ufile.read(size)
        else:
            return xread(self.file, size)

    def __read_extended_header(self):
        (size, ext_flags, self.padding_size) = struct.unpack("!IHI", self._read(10))
        if size != 6 and size != 10:
            warn("Unexpected size of ID3v2.3 extended header: {0}".format(size), Warning)
        if ext_flags & 128:
            self.flags.add("ext:crc_present")
            self.crc32 = struct.unpack("!I", self._read(4))

    def __interpret_frame_flags(self, frameid, b, data):
        flags = {}
        # Frame encoding flags
        if b & self.__FRAME23_FORMAT_UNKNOWN_MASK:
            raise FrameError("Invalid ID3v2.3 frame encoding flags: 0x{0:X}".format(b))
        if b & self.__FRAME23_FORMAT_COMPRESSED:
            flags["compressed"] = True
            expanded_size = Int8.decode(data[0:4])
            data = zlib.decompress(data[4:], expanded_size)
        if b & self.__FRAME23_FORMAT_ENCRYPTED:
            raise FrameError("Can't read ID3v2.3 encrypted frames")
        if b & self.__FRAME23_FORMAT_GROUP:
            flags["group"] = data[0]
            data = data[1:]
        # Frame status messages
        if b & self.__FRAME23_STATUS_DISCARD_ON_TAG_ALTER:
            flags["discard_on_tag_alter"] = True
        if b & self.__FRAME23_STATUS_DISCARD_ON_FILE_ALTER:
            flags["discard_on_file_alter"] = True
        if b & self.__FRAME23_STATUS_READ_ONLY:
            flags["read_only"] = True
        if b & self.__FRAME23_STATUS_UNKNOWN_MASK:
            warn("Unexpected status flags on {0} frame: 0x{1:X}".format(frameid, b), Warning)
        return flags, data
            
    def _read_one_frame(self):
        header = self._read(10)
        if not self._is_frame_id(header[0:4]):
            raise NotAFrameError("Invalid frame id: {0}".format(header[0:4]))
        frameid = header[0:4].decode("ASCII")
        size = Int8.decode(header[4:8])
        data = self._read(size)
        flags = {}
        try:
            flags, data = self.__interpret_frame_flags(frameid,
                                                       Int8.decode(header[8:10]),
                                                       data)
            return self._frame_from_data(frameid, data, flags)
        except Exception as e:
            return ErrorFrame(frameid, data, e)

    def _encode_one_frame(self, frame):
        framedata = frame._to_data()
        origlen = len(framedata)

        flagval = 0
        frameinfo = bytearray()
        if frame.flags.get("compressed"):
            framedata = zlib.compress(framedata)
            flagval |= self.__FRAME23_FORMAT_COMPRESSED
            frameinfo.extend(Int8.encode(origlen, width=4))
        if type(frame.flags.get("group")) == int:
            frameinfo.append(frame.flags["group"])
            flagval |= self.__FRAME23_FORMAT_GROUP
        if frame.flags.get("discard_on_tag_alter"):
            flagval |= self.__FRAME23_STATUS_DISCARD_ON_TAG_ALTER
        if frame.flags.get("discard_on_file_alter"):
            flagval |= self.__FRAME23_STATUS_DISCARD_ON_FILE_ALTER
        if frame.flags.get("read_only"):
            flagval |= self.__FRAME23_STATUS_READ_ONLY
        
        data = bytearray()
        # Frame id
        if len(frame.frameid) != 4 or not self._is_frame_id(frame.frameid.encode("ASCII")):
            raise "Invalid ID3v2.3 frame id {0}".format(repr(frame.frameid))
        data.extend(frame.frameid.encode("ASCII"))
        # Size
        data.extend(Int8.encode(len(frameinfo) + len(framedata), width=4))
        # Flags
        data.extend(Int8.encode(flagval, width=2))
        assert len(data) == 10
        # Format info
        data.extend(frameinfo)
        # Frame data
        data.extend(framedata)
        return data

class Tag24(Tag):
    ITUNES_WORKAROUND = False

    __TAG24_UNSYNCHRONISED = 0x80
    __TAG24_EXTENDED_HEADER = 0x40
    __TAG24_EXPERIMENTAL = 0x20
    __TAG24_FOOTER = 0x10
    __TAG24_UNKNOWN_MASK = 0x0F

    __FRAME24_FORMAT_GROUP = 0x0040
    __FRAME24_FORMAT_COMPRESSED = 0x0008
    __FRAME24_FORMAT_ENCRYPTED = 0x0004
    __FRAME24_FORMAT_UNSYNCHRONISED = 0x0002
    __FRAME24_FORMAT_DATA_LENGTH_INDICATOR = 0x0001
    __FRAME24_FORMAT_UNKNOWN_MASK = 0xB000

    __FRAME24_STATUS_DISCARD_ON_TAG_ALTER = 0x4000
    __FRAME24_STATUS_DISCARD_ON_FILE_ALTER = 0x2000
    __FRAME24_STATUS_READ_ONLY = 0x1000
    __FRAME24_STATUS_UNKNOWN_MASK = 0x8F00

    def __init__(self, file):
        self.version = 4
        super().__init__(file)
        self._fp_tag_start = file.tell()
        header = xread(file, 10)
        if header[0:5] != b"ID3\x04\x00":
            raise TagError("ID3v2.4 header not found")
        if header[5] & self.__TAG24_UNSYNCHRONISED:
            self.flags.add("unsynchronisation")
        if header[5] & self.__TAG24_EXTENDED_HEADER:
            self.flags.add("extended_header")
        if header[5] & self.__TAG24_EXPERIMENTAL:
            self.flags.add("experimental")
        if header[5] & self.__TAG24_FOOTER:
            self.flags.add("footer")
        if header[5] & self.__TAG24_UNKNOWN_MASK:
            warn("Unknown ID3v2.4 flags", Warning)
        self.size = Syncsafe.decode(header[6:10])
        if "extended_header" in self.flags:
            self.__read_extended_header()
        self._fp_frames_start = file.tell()
        self._fp_frames_end = self._fp_tag_start + 10 + self.size
        self._fp_tag_end = (self._fp_tag_start + 10 + self.size
                            + (10 if "footer" in self.flags else 0))
        self.__decode_size = Syncsafe.decode
        if type(self).ITUNES_WORKAROUND:
            # Work around iTunes frame size encoding bug
            # Older versions of iTunes store frame sizes as straight 8bit integers, not syncsafe
            # (Fixed in iTune 8.2)
            if self.__count_frames(Int8.decode) > self.__count_frames(Syncsafe.decode):
                warn("ID3v2.4 frame size is not in syncsafe format", Warning)
                self.__decode_size = Int8.decode
            self.file.seek(self._fp_frames_start)

    def __read_extended_header_flag_data(self):
        # 1-byte length + data
        length = xread(self.file, 1)[0]
        if length & 128:
            raise TagError("Invalid size of extended header field")
        if length == 0:
            return bytes()
        return xread(self.file, length)
 
    def __read_extended_header(self):
        fp = self.file.tell()
        try:
            size = Syncsafe.decode(xread(self.file, 4))
            if size < 6:
                warn("Unexpected size of ID3v2.4 extended header: {0}".format(size), Warning)
            numflags = xread(self.file, 1)[0]
            if numflags != 1:
                warn("Unexpected number of ID3v2.4 extended flag bytes: {0}".format(numflags), Warning)
            flags = xread(self.file, numflags)[0]
            if flags & 0x40:
                self.flags.add("ext:update")
                self.__read_extended_header_flag_data()
            if flags & 0x20:
                self.flags.add("ext:crc_present")
                self.crc32 = Syncsafe.decode(self.__read_extended_header_flag_data())
            if flags & 0x10:
                self.flags.add("ext:restrictions")
                self.restrictions = self.__read_extended_header_flag_data()
        except Exception as e:
            warn("Error while reading ID3v2.4 extended header: " + e, Warning)
        finally:
            file.seek(fp + size)

    def __count_frames(self, size_decode):
        self.file.seek(self._fp_frames_start)
        count = 0
        try:
            while self.file.tell() < self._fp_frames_end:
                header = xread(self.file, 10)
                if not self._is_frame_id(header[0:4]):
                    return count
                size = size_decode(header[4:8])
                if header[8] & 0x8F or header[9] & 0xB0:
                    return count
                xread(self.file, size)
                if self.file.tell() > self._fp_frames_end:
                    warn(str(self.file.tell() - self._fp_frames_end))
                    return count # Don't count overrun frames
                count += 1
        finally:
            return count

    def __interpret_frame_flags(self, frameid, b, data):
        flags = {}
        # Frame format flags
        if b & self.__FRAME24_FORMAT_UNKNOWN_MASK:
            raise FrameError("Unknown ID3v2.4 frame encoding flags: 0x{0:X}".format(b))
        if b & self.__FRAME24_FORMAT_GROUP:
            flags["group"] = data[0]
            data = data[1:]
        if b & self.__FRAME24_FORMAT_COMPRESSED:
            flags["compressed"] = True
        if b & self.__FRAME24_FORMAT_ENCRYPTED:
            raise FrameError("Can't read ID3v2.4 encrypted frames")
        if b & self.__FRAME24_FORMAT_UNSYNCHRONISED:
            flags["unsynchronised"] = True
        expanded_size = len(data)
        if b & self.__FRAME24_FORMAT_DATA_LENGTH_INDICATOR:
            flags["data_length_indicator"]
            expanded_size = Syncsafe.decode(data[0:4])
            data = data[4:]
        if "unsynchronised" in self.flags:
            data = Unsync.decode(data)
        if "compressed" in self.flags:
            data = zlib.decompress(data, expanded_size)        
        # Frame status flags
        if b & self.__FRAME24_STATUS_DISCARD_ON_TAG_ALTER:
            flags["discard_on_tag_alter"] = True
        if b & self.__FRAME24_STATUS_DISCARD_ON_FILE_ALTER:
            flags["discard_on_file_alter"] = True
        if b & self.__FRAME24_STATUS_READ_ONLY:
            flags["read_only"] = True
        if b & self.__FRAME24_STATUS_UNKNOWN_MASK:
            warn("Unexpected status flags on {0} frame: 0x{1:X}".format(frameid, b), Warning)
        return flags, data

    def _reset(self):
        self.file.seek(self._fp_frames_start)

    def _read_one_frame(self):
        header = xread(self.file, 10)
        if not self._is_frame_id(header[0:4]):
            raise NotAFrameError("Invalid frame id: {0}".format(header[0:4]))
        frameid = header[0:4].decode("ASCII")
        size = self.__decode_size(header[4:8])
        data = xread(self.file, size)
        try:
            flags, data = self.__interpret_frame_flags(frameid,
                                                       Int8.decode(header[8:10]),
                                                       data)
            return self._frame_from_data(frameid, data, flags)
        except Exception as e:
            return ErrorFrame(frameid, data, e)

    def encode_header(self):
        # flags
        f = 0
        if frame.flags["unsynchronised"]:
            f |= __TAG24_UNSYNCHRONISED
        if frame.flags["extended_header"]:
            f |= __TAG24_EXTENDED_HEADER
        if frame.flags["experimental"]:
            f |= __TAG24_EXPERIMENTAL
        if frame.flags["footer"]:
            f |= __TAG24_FOOTER
        data.extend(Int8.encode(f, width=2))


    def _encode_one_frame(self, frame):
        framedata = frame._to_data()
        origlen = len(framedata)

        flagval = 0
        frameinfo = bytearray()
        if type(frame.flags.get("group")) == int:
            frameinfo.append(frame.flags["group"])
            flagval |= self.__FRAME24_FORMAT_GROUP
        if frame.flags.get("compressed"):
            frame.flags["data_length_indicator"] = True
            framedata = zlib.compress(framedata)
            flagval |= self.__FRAME24_FORMAT_COMPRESSED
        if frame.flags.get("unsynchronised"):
            frame.flags["data_length_indicator"] = True
            framedata = Unsync.encode(framedata)
            flagval |= self.__FRAME24_FORMAT_UNSYNCHRONISED
        if frame.flags.get("data_length_indicator"):
            frameinfo.extend(Syncsafe.encode(origlen, width=4))
            flagval |= self.__FRAME24_FORMAT_DATA_LENGTH_INDICATOR

        if frame.flags.get("discard_on_tag_alter"):
            flagval |= self.__FRAME24_STATUS_DISCARD_ON_TAG_ALTER
        if frame.flags.get("discard_on_file_alter"):
            flagval |= self.__FRAME24_STATUS_DISCARD_ON_FILE_ALTER
        if frame.flags.get("read_only"):
            flagval |= self.__FRAME24_STATUS_READ_ONLY

        data = bytearray()
        # Frame id
        if len(frame.frameid) != 4 or not self._is_frame_id(frame.frameid.encode("ASCII")):
            raise "Invalid ID3v2.4 frame id {0}".format(repr(frame.frameid))
        data.extend(frame.frameid.encode("ASCII"))
        # Size
        data.extend(Syncsafe.encode(len(frameinfo) + len(framedata), width=4))
        # Flags
        data.extend(Int8.encode(flagval, width=2))
        assert len(data) == 10
        # Format info
        data.extend(frameinfo)
        # Frame data
        data.extend(framedata)
        return data


# Spec system comes from Mutagen
class Spec:
    def __init__(self, name):
        self.name = name
        
    @abstractmethod
    def read(self, frame, data): pass

    @abstractmethod
    def write(self, frame, value): pass

    def validate(self, frame, value):
        return value

    def to_str(self, value):
        return "{0}={1}".format(self.name, repr(value))

class ByteSpec(Spec):
    def read(self, frame, data):
        return data[0], data[1:]
    def write(self, frame, value):
        return bytes([value])
    def validate(self, frame, value):
        if value is not int:
            raise ValueError("Not a byte")
        if value not in range(256):
            raise ValueError("Invalid byte value")
        return value

class IntegerSpec(Spec):
    def __init__(self, name, width):
        super().__init__(name)
        self.width = width
    def read(self, frame, data):
        return Int8.decode(data[:self.width]), data[self.width:]
    def write(self, frame, value):
        if type(value) is not int: 
            raise ValueError("Not an integer: {0}".format(repr(value)))
        return Int8.encode(value, width=self.width)
    def validate(self, frame, value):
        self.write(frame, value)
        return value

class SignedIntegerSpec(Spec):
    def __init__(self, name, width):
        super().__init__(name)
        self.width = width
    def read(self, frame, data):
        val = Int8.decode(data[:self.width])
        if data[0] & 0x80:
            # Negative value
            val -= (1 << (self.width << 3))
        return val, data[self.width:]
    def write(self, frame, value):
        if value is not int: raise ValueError("Not an integer")
        if value >= (1 << ((self.width << 3) - 1)): raise ValueError("Value too large")
        if value < -(1 << ((self.width << 3) - 1)): raise ValueError("Value too small")
        if val < 0:
            val += (1 << (self.width << 3))
        return Int8.encode(val, self.width)
    def validate(self, frame, value):
        self.write(frame, value)
        return value

class VarIntSpec(Spec):
    def read(self, frame, data):
        bits = data[0]
        data = data[1:]
        bytes = (bits + 7) >> 3
        return Int8.decode(data[:bytes]), data
    def write(self, frame, value):
        bytes = 0
        t = value
        while t > 0:
            t >> 32
            bytes += 4
        return Int8.encode(bytes * 8, 1) + Int8.encode(value, width=bytes)
    def validate(self, frame, value):
        self.write(frame, value)
        return value

class BinaryDataSpec(Spec):
    def read(self, frame, data):
        return data, bytes()
    def write(self, frame, value):
        return bytes(value)
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
            return b"\x00" * self.length
        data =  value.encode('iso-8859-1')
        if len(data) != self.length:
            raise ValueError("Invalid string({0}) data: {1}".format(self.length, value))
        return data
    def validate(self, frame, value):
        if len(value) != self.length: raise ValueError("String length mismatch")
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

class EncodingSpec(ByteSpec):
    def read(self, frame, data):
        enc, data = super().read(frame, data)
        if enc & 0xFC:
            raise FrameError("Invalid encoding")
        return enc, data
    def write(self, frame, value):
        if value & 0xFC:
            raise ValueError("Invalid encoding 0x{0:X}".format(value))
        return super().write(frame, value)
    def to_str(self, value):
        return EncodedStringSpec._encodings[value][0]

class EncodedStringSpec(Spec):
    _encodings = (('iso-8859-1', b"\x00"),
                  ('utf-16', b"\x00\x00"),
                  ('utf-16be', b"\x00\x00"),
                  ('utf-8', b"\x00"))

    def __widechars(self, data):
        for i in range(0, len(data), 2):
            yield data[i:i+2]
        
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
            rawstr = data[:index]
            data = data[index+2:]
        return rawstr.decode(enc), data

    def write(self, frame, value):
        enc, term = self._encodings[frame.encoding]
        return value.encode(enc) + term

class EncodedFullTextSpec(EncodedStringSpec):
    pass # TODO

class SequenceSpec(Spec):
    def __init__(self, name, spec):
        super().__init__(name)
        self.spec = spec
    def read(self, frame, data):
        seq = []
        while data:
            elem, data = self.spec.read(frame, data)
            seq.append(elem)
        return seq, data
    def write(self, frame, values):
        data = bytearray()
        for v in values:
            data.extend(self.spec.write(frame, v))
        return data
    def validate(self, frame, values):
        for v in values:
            self.spec.validate(frame, v)
        return values

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
            seq.append(record)
        return seq, data
    def write(self, frame, values):
        data = bytearray()
        for v in values:
            for i in range(len(self.specs)):
                data.append(self.specs[i].write(frame, v[i]))
        return data
    def validate(self, frame, values):
        for v in values:
            for i in range(len(self.specs)):
                self.specs[i].validate(frame, v[i])
        return values

class Frame(metaclass=abc.ABCMeta):
    _framespec = tuple()
    _version = tuple()
    
    def __init__(self, frameid=None, flags=None, **kwargs):
        self.frameid = frameid if frameid else type(self).__name__
        self.flags = flags if flags else {}
        for spec in self._framespec:
            val = kwargs.get(spec.name, None)
            if val != None: spec.validate(self, val)
            setattr(self, spec.name, val)

    @classmethod
    def _from_data(cls, frameid, data, flags=None):
        frame = cls(frameid, flags)
        if getattr(frame, "_untested", False):
            warn("Support for {0} is untested; please verify results".format(frameid), UntestedFrameWarning)
        for spec in frame._framespec:
            val, data = spec.read(frame, data)
            setattr(frame, spec.name, val)
        return frame

    @classmethod
    def _from_frame(cls, frame):
        "Copy constructor"
        assert frame._framespec == cls._framespec
        new = cls(flags=frame.flags)
        for spec in cls._framespec:
            setattr(new, spec.name, getattr(frame, spec.name, None))
        return new

    @classmethod
    def _in_version(self, version):
        return (self._version == version
                or (isinstance(self._version, collections.Container) 
                    and version in self._version))

    def _to_version(self, version):
        if self._in_version(version):
            return self
        if version == 2 and hasattr(self, "_v2_frame"):
            return self._v2_frame._from_frame(self)
        if self._in_version(2):
            base = type(self).__bases__[0]
            if issubclass(base, Frame) and base._in_version(version): 
                return base._from_frame(self)
        raise IncompatibleFrameError()

    def _to_data(self):
        if getattr(self, "_bozo", False):
            warn("General support for frame {0} is virtually nonexistent; its use is discouraged".format(self.frameid), BozoFrameWarning)
        data = bytearray()
        for spec in self._framespec:
            data.extend(spec.write(self, getattr(self, spec.name)))
        return data

    def __repr__(self):
        stype = type(self).__name__
        args = []
        if stype != self.frameid:
            args.append("frameid={0!r}".format(self.frameid))
        if self.flags:
            args.append("flags={0!r}".format(self.flags))
        args.extend("{0}={1!r}".format(spec.name, getattr(self, spec.name)) for spec in self._framespec)
        return "{0}({1})".format(stype, ", ".join(args))

    def _str_fields(self):
        fields = []
        for spec in self._framespec:
            fields.append(spec.to_str(getattr(self, spec.name, None)))
        return ", ".join(fields)
        
    def __str__(self):
        flag = " "
        if "unknown" in self.flags: flag = "?"
        if isinstance(self, ErrorFrame): flag = "!"
        return "{0}{1}({2})".format(flag, self.frameid, self._str_fields())

class UnknownFrame(Frame):
    _framespec = (BinaryDataSpec("data"),)

class ErrorFrame(Frame):
    _framespec = (BinaryDataSpec("data"),)

    def __init__(self, frameid, data, exception, **kwargs):
        super().__init__(frameid, {}, **kwargs)
        self.data = data
        self.exception = exception

    def _str_fields(self):
        strs = ["ERROR"]
        if self.exception:
            strs.append(str(self.exception))
        strs.append(repr(self.data))
        return ", ".join(strs)
    
    
class TextFrame(Frame):
    _framespec = (EncodingSpec("encoding"),
                  SequenceSpec("text", EncodedStringSpec("text")))
    def _str_fields(self):
        return "{0} {1}".format(EncodedStringSpec._encodings[self.encoding][0],
                                ", ".join(repr(t) for t in self.text))

class URLFrame(Frame):
    _framespec = (URLStringSpec("url"), )
    def _str_fields(self):
        return repr(self.url)

class CreditsFrame(Frame):
    _framespec = (EncodingSpec("encoding"),
                  MultiSpec("people",
                            EncodedStringSpec("involvement"),
                            EncodedStringSpec("person")))


# ID3v2.4

# 4.2.1. Identification frames
class UFID(Frame):
    "Unique file identifier"
    _framespec = (NullTerminatedStringSpec("owner"), BinaryDataSpec("data"))

class TIT1(TextFrame): 
    "Content group description"

class TIT2(TextFrame): 
    "Title/songname/content description"

class TIT3(TextFrame): 
    "Subtitle/Description refinement"

class TALB(TextFrame): 
    "Album/Movie/Show title"

class TOAL(TextFrame): 
    "Original album/movie/show title"

class TRCK(TextFrame): 
    "Track number/Position in set"
# #/#

class TPOS(TextFrame): 
    "Part of a set"
# #/#

class TSST(TextFrame):
    "Set subtitle"
    _version = 4

class TSRC(TextFrame): 
    "ISRC (international standard recording code)"


# 4.2.2. Involved persons frames
class TPE1(TextFrame): 
    "Lead performer(s)/Soloist(s)"

class TPE2(TextFrame): 
    "Band/orchestra/accompaniment"

class TPE3(TextFrame): 
    "Conductor/performer refinement"

class TPE4(TextFrame): 
    "Interpreted, remixed, or otherwise modified by"

class TOPE(TextFrame): 
    "Original artist(s)/performer(s)"

class TEXT(TextFrame): "Lyricist/Text writer"
class TOLY(TextFrame): "Original lyricist(s)/text writer(s)"
class TCOM(TextFrame): "Composer"

class TMCL(CreditsFrame):
    "Musician credits list"
    _version = 4

class TIPL(CreditsFrame):
    "Involved people list"
    _version = 4

class TENC(TextFrame): "Encoded by"



# 4.2.3. Derived and subjective properties frames

class TBPM(TextFrame): "BPM (beats per minute)"
# integer in string format

class TLEN(TextFrame): "Length"
# milliseconds in string format

class TKEY(TextFrame): "Initial key"
# /^([CDEFGAB][b#]?[m]?|o)$/

class TLAN(TextFrame): "Language(s)"
# /^...$/  ISO 639-2

class TCON(TextFrame): "Content type"
# integer  - ID3v1
# RX - Remix
# CR - Cover
# Freeform text
# id3v2.3: (number), 

class TFLT(TextFrame): "File type"
class TMED(TextFrame): "Media type"
class TMOO(TextFrame):
    "Mood"
    _version = 4


# 4.2.4. Rights and license frames

class TCOP(TextFrame): "Copyright message"
class TPRO(TextFrame):
    "Produced notice"
    _version = 4
    
class TPUB(TextFrame): "Publisher"
class TOWN(TextFrame): "File owner/licensee"
class TRSN(TextFrame): "Internet radio station name"
class TRSO(TextFrame): "Internet radio station owner"



# 4.2.5. Other text frames

class TOFN(TextFrame): "Original filename"
class TDLY(TextFrame): "Playlist delay"
# milliseconds

class TDEN(TextFrame):
    # timestamp
    "Encoding time"
    _version = 4

class TDOR(TextFrame):
    "Original release time"
    # timestamp
    _version = 4

class TDRC(TextFrame):
    "Recording time"
    # timestamp
    _version = 4

class TDRL(TextFrame):
    "Release time"
    # timestamp
    _version = 4

class TDTG(TextFrame):
    "Tagging time"
    # timestamp
    _version = 4

class TSSE(TextFrame): "Software/Hardware and settings used for encoding"
class TSOA(TextFrame):
    "Album sort order"
    _version = 4
class TSOP(TextFrame):
    "Performer sort order"
    _version = 4
class TSOT(TextFrame):
    "Title sort order"
    _version = 4


# 4.2.6. User defined information frame

class TXXX(Frame):
    "User defined text information frame"
    _framespec = (EncodingSpec("encoding"),
                  EncodedStringSpec("description"),
                  EncodedStringSpec("value"))


# 4.3. URL link frames

class WCOM(URLFrame): "Commercial information"
class WCOP(URLFrame): "Copyright/Legal information"
class WOAF(URLFrame): "Official audio file webpage"
class WOAR(URLFrame): "Official artist/performer webpage"
class WOAS(URLFrame): "Official audio source webpage"
class WORS(URLFrame): "Official Internet radio station homepage"
class WPAY(URLFrame): "Payment"
class WPUB(URLFrame): "Publishers official webpage"

class WXXX(Frame):
    "User defined URL link frame"
    _framespec = (EncodingSpec("encoding"),
                  EncodedStringSpec("description"),
                  URLStringSpec("url"))


# 4.4.-4.13  Junk frames
class MCDI(Frame):
    "Music CD identifier"
    _framespec = (BinaryDataSpec("cd_toc"),)

class ETCO(Frame):
    "Event timing codes"
    _framespec = (ByteSpec("format"),
                  MultiSpec("events", ByteSpec("type"), IntegerSpec("timestamp", 4)))
    _untested = True
    _bozo = True

class MLLT(Frame):
    "MPEG location lookup table"
    _framespec = (IntegerSpec("frames", 2), IntegerSpec("bytes", 3),
                  IntegerSpec("milliseconds", 3),
                  ByteSpec("bits_for_bytes"), ByteSpec("bits_for_milliseconds"),
                  BinaryDataSpec("data"))
    _untested = True
    _bozo = True

class SYTC(Frame):
    "Synchronised tempo codes"
    _framespec = (ByteSpec("format"), BinaryDataSpec("data"))
    _untested = True
    _bozo = True

class USLT(Frame):
    "Unsynchronised lyric/text transcription"
    _framespec = (EncodingSpec("encoding"), LanguageSpec("lang"),
                  EncodedStringSpec("desc"), EncodedFullTextSpec("text"))
    _untested = True

class SYLT(Frame):
    "Synchronised lyric/text"
    _framespec = (EncodingSpec("encoding"), LanguageSpec("lang"),
                  ByteSpec("format"), ByteSpec("type"),
                  EncodedStringSpec("desc"),
                  MultiSpec("data", EncodedFullTextSpec("text"), IntegerSpec("timestamp", 4)))
    _untested = True
    _bozo = True

class COMM(Frame):
    "Comments"
    _framespec = (EncodingSpec("encoding"), LanguageSpec("lang"),
                  EncodedStringSpec("desc"), EncodedFullTextSpec("text"))

class RVA2(Frame):
    "Relative volume adjustment (2)"
    _framespec = (NullTerminatedStringSpec("desc"),
                  MultiSpec("adjustment",
                            ByteSpec("channel"),
                            IntegerSpec("gain", 2),  # * 512
                            VarIntSpec("peak")))
    _untested = True

class EQU2(Frame):
    "Equalisation (2)"
    _framespec = (ByteSpec("method"), NullTerminatedStringSpec("desc"),
                  MultiSpec("adjustments",
                            IntegerSpec("frequency", 2), # in 0.5Hz
                            SignedIntegerSpec("adjustment", 2))) # * 512x
    _untested = True
    _bozo = True

class RVRB(Frame):
    "Reverb"
    _framespec = (IntegerSpec("left", 2),
                  IntegerSpec("right", 2),
                  ByteSpec("bounce_left"), ByteSpec("bounce_right"),
                  ByteSpec("feedback_ltl"), ByteSpec("feedback_ltr"),
                  ByteSpec("feedback_rtr"), ByteSpec("feedback_rtl"),
                  ByteSpec("premix_ltr"), ByteSpec("premix_rtl"))
    _untested = True
    _bozo = True

class APIC(Frame):
    "Attached picture"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("mime"),
                  ByteSpec("type"),
                  EncodedStringSpec("desc"),
                  BinaryDataSpec("data"))
    def _str_fields(self):
        img = "{0} bytes of {1} data".format(len(self.data), 
                                             imghdr.what(None, self.data[:32]))
        return "{0}({1}), desc={2}, mime={3}: {4}".format(self.type,
                                                          picture_types[self.type],
                                                          repr(self.desc),
                                                          repr(self.mime),
                                                          img)
    

class GEOB(Frame):
    "General encapsulated object"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("mime"),
                  EncodedStringSpec("filename"),
                  EncodedStringSpec("desc"),
                  BinaryDataSpec("data"))

class PCNT(Frame):
    "Play counter"
    _framespec = (IntegerSpec("count", 4),)

class POPM(Frame):
    "Popularimeter"
    _framespec = (NullTerminatedStringSpec("email"),
                  ByteSpec("rating"),
                  IntegerSpec("count", 4))

class RBUF(Frame):
    "Recommended buffer size"
    _framespec = (IntegerSpec("size", 4),
                  #optional:
                  ByteSpec("info"),
                  IntegerSpec("offset", 4))
    _untested = True
    _bozo = True

class AENC(Frame):
    "Audio encryption"
    _framespec = (NullTerminatedStringSpec("owner"),
                  IntegerSpec("preview_start", 2),
                  IntegerSpec("preview_length", 2),
                  BinaryDataSpec("data"))
    _untested = True
    _bozo = True

class LINK(Frame):
    "Linked information"
    _framespec = (SimpleStringSpec("linked_frameid", 4),
                  NullTerminatedStringSpec("url"),
                  # optional
                  BinaryDataSpec("data"))
    _untested = True
    _bozo = True

class POSS(Frame):
    "Position synchronisation frame"
    _framespec = (ByteSpec("format"),
                  IntegerSpec("position", 4))
    _untested = True
    _bozo = True

class USER(Frame):
    "Terms of use"
    # TODO: emusic.com forgets the language field
    _framespec = (EncodingSpec("encoding"),
                  LanguageSpec("lang"),
                  EncodedStringSpec("text"))

class OWNE(Frame):
    "Ownership frame"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("price"),
                  SimpleStringSpec("date", 8),
                  NullTerminatedStringSpec("seller"))
    _untested = True
    _bozo = True

class COMR(Frame):
    "Commercial frame"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("price"),
                  NullTerminatedStringSpec("valid"),
                  NullTerminatedStringSpec("contact"),
                  ByteSpec("format"),
                  EncodedStringSpec("seller"),
                  EncodedStringSpec("desc"),
                  NullTerminatedStringSpec("mime"),
                  BinaryDataSpec("logo"))
    _untested = True
    _bozo = True

class ENCR(Frame):
    "Encryption method registration"
    _framespec = (NullTerminatedStringSpec("owner"),
                  ByteSpec("symbol"),
                  BinaryDataSpec("data"))
    _untested = True
    _bozo = True


class GRID(Frame):
    "Group identification registration"
    _framespec = (NullTerminatedStringSpec("owner"),
                  ByteSpec("symbol"),
                  BinaryDataSpec("data"))
    _untested = True
    _bozo = True

class PRIV(Frame):
    "Private frame"
    _framespec = (NullTerminatedStringSpec("owner"),
                  BinaryDataSpec("data"))

class SIGN(Frame):
    "Signature frame"
    _framespec = (ByteSpec("group"),
                  BinaryDataSpec("data"))
    _untested = True
    _bozo = True
    _version = 4

class SEEK(Frame):
    "Seek frame"
    _framespec = (IntegerSpec("offset", 4), )
    _untested = True
    _bozo = True
    _version = 4

class ASPISpec(Spec):
    def read(self, frame, data):
        width = 1 if frame.b == 1 else 2
        value = []
        for i in range(frame.N):
            value.append(Int8.decode(data[:width]))
            data = data[width:]
        return value, data
    def write(self, frame, values):
        width = 1 if frame.b == 1 else 2
        data = bytearray()
        for v in values:
            data.append(Int8.encode(v, width=width))
        return data
    
class ASPI(Frame):
    "Audio seek point index"
    _framespec = (IntegerSpec("S", 4),
                  IntegerSpec("L", 4),
                  IntegerSpec("N", 2),
                  ByteSpec("b"),
                  ASPISpec("Fi"))
    _untested = True
    _bozo = True
    _version = 4


# ID3v2.3

class TDAT(TextFrame):
    """Date
    A numerical string in DDMM format containing the date for the recording.
    Replaced by TDRC in id3v2.4
    """
    _version = 3

class TIME(TextFrame):
    """Time
    A numerical string in HHMM format containing the time for the recording.
    Replaced by TDRC in id3v2.4
    """
    _version = 3

class TORY(TextFrame):
    """Original release year
    Replaced by TDOR in id3v2.4
    """
    _version = 3

class TRDA(TextFrame):
    """Recording dates
    Replaced by TDRC in id3v2.4
    """
    _version = 3

class TSIZ(TextFrame):
    """Size
    Size of the audio file in bytes, excluding the ID3v2 tag.
    Removed in id3v2.4
    """
    _version = 3

class TYER(TextFrame):
    """Year
    A numerical string with the year of the recording.
    Replaced by TDRC in id3v2.4
    """
    _version = 3
    
class IPLS(CreditsFrame):
    """Involved people list
    Replaced by TMCL and TIPL in id3v2.4
    """
    _framespec = (BinaryDataSpec("data"),)
    _untested = True
    _bozo = True
    _version = 3

class EQUA(Frame):
    """Equalisation
    Replaced by EQU2 in id3v2.4
    """
    _framespec = (ByteSpec("bits"), BinaryDataSpec("data"))
    _untested = True
    _bozo = True
    _version = 3

class RVAD(Frame):
    """Relative volume adjustment
    Replaced by RVA2 in id3v2.4
    """
    _framespec = (BinaryDataSpec("data"),)
    _untested = True
    _bozo = True
    _version = 3

# ID3v2.2

class UFI(UFID): pass
class TT1(TIT1): pass
class TT2(TIT2): pass
class TT3(TIT3): pass
class TP1(TPE1): pass
class TP2(TPE2): pass
class TP3(TPE3): pass
class TP4(TPE4): pass
class TCM(TCOM): pass
class TXT(TEXT): pass
class TLA(TLAN): pass
class TCO(TCON): pass
class TAL(TALB): pass
class TPA(TPOS): pass
class TRK(TRCK): pass
class TRC(TSRC): pass
class TYE(TYER): pass
class TDA(TDAT): pass
class TIM(TIME): pass
class TRD(TRDA): pass
class TMT(TMED): pass
class TFT(TFLT): pass
class TBP(TBPM): pass
class TCR(TCOP): pass
class TPB(TPUB): pass
class TEN(TENC): pass
class TSS(TSSE): pass
class TOF(TOFN): pass
class TLE(TLEN): pass
class TSI(TSIZ): pass
class TDY(TDLY): pass
class TKE(TKEY): pass
class TOT(TOAL): pass
class TOA(TOPE): pass
class TOL(TOLY): pass
class TOR(TORY): pass

class TXX(TXXX): pass

class WAF(WOAF): pass
class WAR(WOAR): pass
class WAS(WOAS): pass
class WCM(WCOM): pass
class WCP(WCOP): pass
class WPB(WPUB): pass

class WXX(WXXX): pass

class IPL(IPLS): pass

class MCI(MCDI): pass
class ETC(ETCO): pass
class MLL(MLLT): pass
class STC(SYTC): pass
class ULT(USLT): pass
class SLT(SYLT): pass

class COM(COMM): pass

class RVA(RVAD): pass
class EQU(EQUA): pass
class REV(RVRB): pass

class PIC(Frame):
    "Attached picture"
    _framespec = (EncodingSpec("encoding"),
                  SimpleStringSpec("format", 3),
                  ByteSpec("type"),
                  NullTerminatedStringSpec("desc"),
                  BinaryDataSpec("data"))
    _version = 2
    def _str_fields(self):
        img = "{0} bytes of {1} data".format(len(self.data), 
                                               imghdr.what(None, self.data[:32]))
        return "{0}({1}), desc={2}, format={3}: {4}".format(self.type,
                                                          picture_types[self.type],
                                                          repr(self.desc),
                                                repr(self.format),
                                                img)


class GEO(GEOB): pass
class CNT(PCNT): pass
class POP(POPM): pass

class BUF(RBUF): pass
class CRM(Frame):
    "Encrypted meta frame"
    _framespec = (NullTerminatedStringSpec("owner"),
                  NullTerminatedStringSpec("content"),
                  BinaryDataSpec("data"))
    _bozo = True
    _untested = True
    _version = 2

class CRA(AENC): pass

class LNK(Frame):
    "Linked information"
    _framespec = (SimpleStringSpec("frameid", 3),
                  NullTerminatedStringSpec("url"),
                  BinaryDataSpec("data"))
    _bozo = True
    _untested = True
    _version = 2

# Nonstandard frames
class TCMP(TextFrame): "iTunes: Part of a compilation"
class TCP(TCMP): pass

class TDES(TextFrame): "iTunes: Podcast description"
class TDS(TDES): pass

class TGID(TextFrame): "iTunes: Podcast identifier"
class TID(TGID): pass

class TDRL(TextFrame): "iTunes: Podcast release date"
class TDR(TGID): pass

class WFED(URLFrame): "iTunes: Podcast feed URL"
class WFD(WFED): pass

class TCAT(TextFrame): "iTunes: Podcast category"
class TCT(TCAT): pass

class TKWD(TextFrame): 
    """iTunes: Podcast keywords
    Comma-separated list of keywords.
    """
class TKW(TKWD): pass

class PCST(Frame):
    """iTunes: Podcast flag.

    If this frame is present, iTunes considers the file to be a podcast.
    Value should be zero.
    """
    _framespec = (IntegerSpec("value", 4),)
class PCS(PCST): pass


# Attached picture (APIC & PIC) types
picture_types = ["Other", "32x32 icon", "Other icon", "Front Cover", 
                 "Back Cover", "Leaflet", "Media", "Lead artist", "Artist", 
                 "Conductor", "Band/Orchestra", "Composer", 
                 "Lyricist/text writer", "Recording Location", "Recording", 
                 "Performance", "Screen capture", "A bright coloured fish", 
                 "Illustration", "Band/artist", "Publisher/Studio"]

# ID3v1 genre list
genres = ( "Blues", "Classic Rock", "Country", "Dance", "Disco", "Funk",
           "Grunge", "Hip-Hop", "Jazz", "Metal", "New Age", "Oldies", 
           "Other", "Pop", "R&B", "Rap", "Reggae", "Rock", "Techno", 
           "Industrial", "Alternative", "Ska", "Death Metal", "Pranks", 
           "Soundtrack", "Euro-Techno", "Ambient", "Trip-Hop", "Vocal", 
           "Jazz+Funk", "Fusion", "Trance", "Classical", "Instrumental", 
           "Acid", "House", "Game", "Sound Clip","Gospel", "Noise", 
           "AlternRock", "Bass", "Soul", "Punk", "Space", "Meditative", 
           "Instrumental Pop", "Instrumental Rock", "Ethnic", "Gothic", 
           "Darkwave", "Techno-Industrial", "Electronic", "Pop-Folk", 
           "Eurodance", "Dream", "Southern Rock", "Comedy", "Cult",
           "Gangsta", "Top 40", "Christian Rap", "Pop/Funk", "Jungle",
           "Native American", "Cabaret", "New Wave", "Psychadelic",
           "Rave", "Showtunes", "Trailer", "Lo-Fi", "Tribal", "Acid Punk", 
           "Acid Jazz", "Polka", "Retro", "Musical", "Rock & Roll", 
           "Hard Rock",
           # Winamp extensions
           "Folk", "Folk-Rock", "National Folk", "Swing", "Fast Fusion", 
           "Bebob", "Latin", "Revival", "Celtic", "Bluegrass", "Avantgarde",
           "Gothic Rock", "Progressive Rock", "Psychedelic Rock", 
           "Symphonic Rock", "Slow Rock", "Big Band", "Chorus", 
           "Easy Listening", "Acoustic", "Humour", "Speech", "Chanson",
           "Opera", "Chamber Music", "Sonata", "Symphony", "Booty Bass",
           "Primus", "Porn Groove", "Satire", "Slow Jam", "Club", "Tango",
           "Samba", "Folklore", "Ballad", "Power Ballad", "Rhythmic Soul",
           "Freestyle", "Duet", "Punk Rock", "Drum Solo", "A capella",
           "Euro-House", "Dance Hall" )

_tag_versions = {
    2: Tag22,
    3: Tag23,
    4: Tag24,
    }
          
@contextmanager
def read(filename):
    file = open(filename, "rb")
    try:
        header = file.peek(10)
        if len(header) < 10:
            raise EOFError
        if header[0:3] != b"ID3":
            raise NoTagError("ID3v2 tag not found")
        if header[3] not in _tag_versions or header[4] != 0:
            raise NoTagError("Unknown ID3 version: 2.{0}.{1}".format(*header[3:5]))
        yield _tag_versions[header[3]](file)
    finally:
        file.close()


def register_frame(cls):
    assert isinstance(cls, type) and issubclass(cls, Frame) and cls is not Frame
    assert 3 <= len(cls.__name__) <= 4
    if len(cls.__name__) == 3:
        cls._version = 2
    if len(cls.__name__) == 4 and cls._version == tuple():
        cls._version = (3, 4)                
    for version in _tag_versions:
        if cls._in_version(version):
            _tag_versions[version].known_frames[cls.__name__] = cls

# Package initialization

def _register_builtin_frames():
    for obj in globals().values():
        if not (isinstance(obj, type) 
                and issubclass(obj, Frame) 
                and 3 <= len(obj.__name__) <= 4):
            continue
        register_frame(obj)
        # Register v2.2 names of v2.3 & v2.4 frames
        if obj._in_version(2):
            base = obj.__bases__[0]
            if (issubclass(base, Frame) and (base._in_version(3) 
                                             or base._in_version(4))):
                assert not hasattr(base, "_v2_frame")
                base._v2_frame = obj



_register_builtin_frames()
