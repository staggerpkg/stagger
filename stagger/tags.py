# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import abc
import struct
import re

from abc import abstractmethod
from warnings import warn
from contextlib import contextmanager

from stagger.errors import *
from stagger.conversion import *
import stagger.frames as Frames
import stagger.id3 as id3
import stagger.fileutil as fileutil

def _tag_chunk(filename):
    with fileutil.opened(filename, "rb") as file:
        start = file.tell()
        try:
            with lazy_read(file) as tag:
                end = tag._fp_tag_end
            return (start, end - start)
        except NoTagError:
            return (start, 0)
        finally:
            file.seek(start)

@contextmanager
def lazy_read(filename):
    with fileutil.opened(filename, "rb") as file:
        header = file.peek(10)
        if len(header) < 10:
            raise EOFError
        if header[0:3] != b"ID3":
            raise NoTagError("ID3v2 tag not found")
        if header[3] not in _tag_versions or header[4] != 0:
            raise TagError("Unknown ID3 version: 2.{0}.{1}".format(*header[3:5]))
        yield _tag_versions[header[3]](file)


class FrameOrder:
    """Order frames based on their position in a predefined list of patterns.

    A pattern may be a frame class, or a regular expression that is to be
    matched against the frame id.

    >>> order = FrameOrder(TIT1, "T.*", TXXX)
    >>> order.key(TIT1())
    (0,)
    >>> order.key(TPE1())
    (1,)
    >>> order.key(TXXX())
    (2,)
    >>> order.key(APIC())
    (3,)
    """
    def __init__(self, *patterns):
        self.re_keys = []
        self.frame_keys = dict()
        for (i, pattern) in zip(range(len(patterns)), patterns):
            if isinstance(pattern, str):
                self.re_keys.append((pattern, (i,)))
            else:
                assert issubclass(pattern, Frames.Frame)
                self.frame_keys[pattern] = (i,)
        self.unknown_key = (i + 1,)

    def key(self, frame):
        "Return the sort key for the given frame."
        # Look up frame by exact match
        if type(frame) in self.frame_keys:
            return self.frame_keys[type(frame)]

        # Look up parent frame for v2.2 frames
        if frame._in_version(2) and type(frame).__bases__[0] in self.frame_keys:
            return self.frame_keys[type(frame).__bases__[0]]

        # Try each pattern
        for (pattern, key) in self.re_keys:
            if re.match(pattern, frame.frameid):
                return key

        return self.unknown_key


class Tag(metaclass=abc.ABCMeta):
    known_frames = { cls.__name__: cls for cls in Frames.gen_frame_classes(id3) }

    frame_order = FrameOrder(id3.TIT2, id3.TPE1, id3.TALB, id3.TRCK, id3.TCOM, 
                             id3.TPOS,
                             id3.TDRC, id3.TYER, id3.TRDA, id3.TDAT, id3.TIME,
                             "T.*", id3.COMM, "W*", id3.TXXX, id3.WXXX,
                             id3.UFID, id3.PCNT, id3.POPM,
                             id3.APIC, id3.PIC, id3.GEOB, id3.PRIV,
                             ".*")

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

    @classmethod
    def _encode_one_frame(cls, frame):
        raise NotImplemented

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

    @staticmethod
    def _is_frame_id(data):
        # Allow a single space at end of four-character ids
        # Some programs (e.g. iTunes 8.2) generate such frames when converting
        # from 2.2 to 2.3/2.4 tags.
        pattern = re.compile(b"^[A-Z][A-Z0-9]{2}[A-Z0-9 ]?$")
        return pattern.match(data)

    @classmethod
    def _frame_from_data(cls, frameid, data, flags=None):
        if flags is None: flags = {}
        if frameid in cls.known_frames:
            return cls.known_frames[frameid]._from_data(frameid, data, flags)
        flags["unknown"] = True
        if frameid.startswith('T'): # Unknown text frame
            return Frames.TextFrame._from_data(frameid, data, flags)
        elif frameid.startswith('W'): # Unknown URL frame
            return Frames.URLFrame._from_data(frameid, data, flags)
        else:
            return Frames.UnknownFrame._from_data(frameid, data, flags)

    @classmethod
    def _prepare_framedict(cls, framedict):
        pass

    @classmethod
    def _prepare_frames(cls, frames):
        # Generate dictionary of frames
        d = dict()
        for frame in frames:
            l = d.get(frame.frameid, [])
            l.append(frame)
            d[frame.frameid] = l

        # Merge duplicate frames
        for frameid in d.keys():
            d[frameid] = d[frameid][0]._merge(d[frameid])

        cls._prepare_framedict(d)

        # Convert frames
        d2 = dict()
        for frameid in d.keys():
            fs = []
            try:
                for frame in d[frameid]:
                    fs.append(frame._to_version(cls.version))
            except IncompatibleFrameError:
                warn("Skipping incompatible frame {0}".format(frameid))
            except ValueError as e:
                warn("Skipping invalid frame {0} ({1})".format(frameid, e))
            else:
                d2[frameid] = fs

        # Sort frames
        newframes = []
        for fs in d2.values():
            for f in fs:
                assert isinstance(f, Frames.Frame)
                newframes.append(f)
        newframes.sort(key=self.frame_order.key)
        return newframes

    @classmethod
    def _bake_tag(cls, frames, flags,
                  padding_default, padding_max, size_hint=None):
        raise NotImplemented

    @classmethod
    def write(cls, filename, frames, flags=None,
              padding_default=1024, padding_max=10240):
        frames = cls._prepare_frames(frames)
        with fileutil.opened(filename, "rb+") as file:
            (offset, length) = _tag_chunk(file)
            tag_data = cls._bake_tag(frames, flags, padding_default, padding_max,
                                     size_hint=length)
            _replace_chunk(file, offset, length, tag_data)

class Tag22(Tag):
    version = 2
    def __init__(self, file):
        super().__init__(file)
        self._fp_tag_start = file.tell()
        header = fileutil.xread(file, 10)
        if header[0:5] != b"ID3\x02\00":
            raise TagError("ID3v2.2 header not found")
        if header[5] & 0x80:
            self.flags.add("unsynchronisation")
        if header[5] & 0x40: # Compression bit is ill-defined in standard
            raise TagError("ID3v2.2 tag compression is not supported")
        if header[5] & 0x3F:
            raise TagError("Unknown ID3v2.2 flags")
        self.size = Syncsafe.decode(header[6:10])
        self._fp_frames_start = file.tell()
        self._fp_frames_end = self._fp_frames_start + self.size
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
            return fileutil.xread(self.file, size)

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
            return Frames.ErrorFrame(frameid, data, e)

    @classmethod
    def _encode_one_frame(cls, frame):
        framedata = frame._to_data()

        data = bytearray()
        # Frame id
        if len(frame.frameid) != 3 or not cls._is_frame_id(frame.frameid.encode("ASCII")):
            raise "Invalid ID3v2.2 frame id {0}".format(repr(frame.frameid))
        data.extend(frame.frameid.encode("ASCII"))
        # Size
        data.extend(Int8.encode(len(framedata), width=3))
        assert(len(data) == 6)
        data.extend(framedata)
        return data

    @classmethod
    def _bake_tag(cls, frames, flags,
                  padding_default, padding_max, size_hint=None ):
        if flags == None: flags = {}

        framedata = bytearray().join(cls._encode_one_frame(frame)
                                     for frame in frames)
        if "unsynchronisation" in flags:
            framedata = Unsync.encode(framedata)

        size = len(framedata)
        if (size_hint != None and size < size_hint
            and (padding_max == None or size_hint - size <= padding_max)):
            size = size_hint
        elif padding_default:
            size += padding_default

        data = bytearray()
        data.extend(b"ID3\x02\x00")
        data.append(0x80 if "unsynchronisation" in flags else 0x00)
        data.extend(Syncsafe.encode(size, width=4))
        data.extend(framedata)
        if size > len(framedata):
            data.extend(b"\x00" * (size - len(framedata)))
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

    version = 3
    def __init__(self, file):
        super().__init__(file)
        self._fp_tag_start = file.tell()
        header = fileutil.xread(file, 10)
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
            return fileutil.xread(self.file, size)

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
            return Frames.ErrorFrame(frameid, data, e)

    @classmethod
    def _encode_one_frame(cls, frame):
        framedata = frame._to_data()
        origlen = len(framedata)

        flagval = 0
        frameinfo = bytearray()
        if frame.flags.get("compressed"):
            framedata = zlib.compress(framedata)
            flagval |= cls.__FRAME23_FORMAT_COMPRESSED
            frameinfo.extend(Int8.encode(origlen, width=4))
        if type(frame.flags.get("group")) == int:
            frameinfo.append(frame.flags["group"])
            flagval |= cls.__FRAME23_FORMAT_GROUP
        if frame.flags.get("discard_on_tag_alter"):
            flagval |= cls.__FRAME23_STATUS_DISCARD_ON_TAG_ALTER
        if frame.flags.get("discard_on_file_alter"):
            flagval |= cls.__FRAME23_STATUS_DISCARD_ON_FILE_ALTER
        if frame.flags.get("read_only"):
            flagval |= cls.__FRAME23_STATUS_READ_ONLY

        data = bytearray()
        # Frame id
        if len(frame.frameid) != 4 or not cls._is_frame_id(frame.frameid.encode("ASCII")):
            raise ValueError("Invalid ID3v2.3 frame id {0}".format(repr(frame.frameid)))
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

    @classmethod
    def _bake_tag(cls, frames, flags,
                  padding_default, padding_max, size_hint=None ):
        if flags == None: flags = {}

        if "unsynchronisation" in flags:
            for frame in frames: frame.flags["unsynchronisation"] = True
        framedata = bytearray().join(cls._encode_one_frame(frame)
                                     for frame in frames)

        size = len(framedata)
        if (size_hint != None and size < size_hint
            and (padding_max == None or size_hint - size <= padding_max)):
            size = size_hint
        elif padding_default:
            size += padding_default

        data = bytearray()
        data.extend(b"ID3\x03\x00")
        flagval = 0x00
        if "unsynchronisation" in flags:
            flagval |= 0x80
        data.append(flagval)
        data.extend(Syncsafe.encode(size, width=4))
        data.extend(framedata)
        if size > len(framedata):
            data.extend(b"\x00" * (size - len(framedata)))
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

    version = 4
    def __init__(self, file):
        super().__init__(file)
        self._fp_tag_start = file.tell()
        header = fileutil.xread(file, 10)
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
        length = fileutil.xread(self.file, 1)[0]
        if length & 128:
            raise TagError("Invalid size of extended header field")
        if length == 0:
            return bytes()
        return fileutil.xread(self.file, length)

    def __read_extended_header(self):
        fp = self.file.tell()
        try:
            size = Syncsafe.decode(fileutil.xread(self.file, 4))
            if size < 6:
                warn("Unexpected size of ID3v2.4 extended header: {0}".format(size), Warning)
            numflags = fileutil.xread(self.file, 1)[0]
            if numflags != 1:
                warn("Unexpected number of ID3v2.4 extended flag bytes: {0}".format(numflags), Warning)
            flags = fileutil.xread(self.file, numflags)[0]
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
                header = fileutil.xread(self.file, 10)
                if not self._is_frame_id(header[0:4]):
                    return count
                size = size_decode(header[4:8])
                if header[8] & 0x8F or header[9] & 0xB0:
                    return count
                fileutil.xread(self.file, size)
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
        header = fileutil.xread(self.file, 10)
        if not self._is_frame_id(header[0:4]):
            raise NotAFrameError("Invalid frame id: {0}".format(header[0:4]))
        frameid = header[0:4].decode("ASCII")
        size = self.__decode_size(header[4:8])
        data = fileutil.xread(self.file, size)
        try:
            flags, data = self.__interpret_frame_flags(frameid,
                                                       Int8.decode(header[8:10]),
                                                       data)
            return self._frame_from_data(frameid, data, flags)
        except Exception as e:
            return Frames.ErrorFrame(frameid, data, e)

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


    @classmethod
    def _encode_one_frame(cls, frame):
        framedata = frame._to_data()
        origlen = len(framedata)

        flagval = 0
        frameinfo = bytearray()
        if type(frame.flags.get("group")) == int:
            frameinfo.append(frame.flags["group"])
            flagval |= cls.__FRAME24_FORMAT_GROUP
        if frame.flags.get("compressed"):
            frame.flags["data_length_indicator"] = True
            framedata = zlib.compress(framedata)
            flagval |= cls.__FRAME24_FORMAT_COMPRESSED
        if frame.flags.get("unsynchronised"):
            frame.flags["data_length_indicator"] = True
            framedata = Unsync.encode(framedata)
            flagval |= cls.__FRAME24_FORMAT_UNSYNCHRONISED
        if frame.flags.get("data_length_indicator"):
            frameinfo.extend(Syncsafe.encode(origlen, width=4))
            flagval |= cls.__FRAME24_FORMAT_DATA_LENGTH_INDICATOR

        if frame.flags.get("discard_on_tag_alter"):
            flagval |= cls.__FRAME24_STATUS_DISCARD_ON_TAG_ALTER
        if frame.flags.get("discard_on_file_alter"):
            flagval |= cls.__FRAME24_STATUS_DISCARD_ON_FILE_ALTER
        if frame.flags.get("read_only"):
            flagval |= cls.__FRAME24_STATUS_READ_ONLY

        data = bytearray()
        # Frame id
        if len(frame.frameid) != 4 or not cls._is_frame_id(frame.frameid.encode("ASCII")):
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

    @classmethod
    def _bake_tag(cls, frames, flags,
                  padding_default, padding_max, size_hint=None ):
        if flags == None: flags = {}

        framedata = bytearray().join(cls._encode_one_frame(frame)
                                     for frame in frames)
        if "unsynchronisation" in flags:
            framedata = Unsync.encode(framedata)

        size = len(framedata)
        if (size_hint != None and size < size_hint
            and (padding_max == None or size_hint - size <= padding_max)):
            size = size_hint
        elif padding_default:
            size += padding_default

        data = bytearray()
        data.extend(b"ID3\x04\x00")
        flagval = 0x00
        if "unsynchronisation" in flags:
            flagval |= 0x80
        data.append(flagval)
        data.extend(Syncsafe.encode(size, width=4))
        data.extend(framedata)
        if size > len(framedata):
            data.extend(b"\x00" * (size - len(framedata)))
        return data


_tag_versions = {
    2: Tag22,
    3: Tag23,
    4: Tag24,
    }
