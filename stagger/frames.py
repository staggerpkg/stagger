# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

"""Class definitions for ID3v2 frames."""

import abc
import collections
from abc import abstractmethod

from stagger.errors import *
from stagger.specs import *

class Frame(metaclass=abc.ABCMeta):
    _framespec = tuple()
    _version = tuple()
    _allow_duplicates = False
    
    def __init__(self, frameid=None, flags=None, **kwargs):
        self.frameid = frameid if frameid else type(self).__name__
        self.flags = flags if flags else {}
        assert len(self._framespec) > 0
        for spec in self._framespec:
            val = kwargs.get(spec.name, None)
            setattr(self, spec.name, val)

    def __setattr__(self, name, value):
        # Automatic validation on assignment
        if value is not None:
            for spec in self._framespec:
                if name == spec.name:
                    value = spec.validate(self, value)
                    break
        super().__setattr__(name, value)

    @classmethod
    def _from_data(cls, frameid, data, flags=None):
        frame = cls(frameid=frameid, flags=flags)
        if getattr(frame, "_untested", False):
            warn("Support for {0} is untested; please verify results".format(frameid), 
                 UntestedFrameWarning)
        for spec in frame._framespec:
            try:
                val, data = spec.read(frame, data)
                setattr(frame, spec.name, val)
            except EOFError:
                if not spec._optional:
                    raise
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
    def _merge(cls, frames):
        if cls._allow_duplicates:
            return frames
        else:
            if len(frames) > 1:
                warn("Frame {0} duplicated, only the last instance is kept".format(frames[0].frameid))
            return frames[-1:]

    @classmethod
    def _in_version(self, *versions):
        "Returns true if this frame is defined in any of the specified versions of ID3."
        for version in versions:
            if (self._version == version
                or (isinstance(self._version, collections.Container) 
                    and version in self._version)):
                return True
        return False

    def _to_version(self, version):
        if self._in_version(version):
            return self
        if version == 2 and hasattr(self, "_v2_frame"):
            return self._v2_frame._from_frame(self)
        if self._in_version(2):
            base = type(self).__bases__[0]
            if issubclass(base, Frame) and base._in_version(version): 
                return base._from_frame(self)
        raise IncompatibleFrameError("Frame {0} cannot be converted to ID3v2.{1} format".format(self.frameid, version))

    def _to_data(self):
        if getattr(self, "_bozo", False):
            warn("General support for frame {0} is virtually nonexistent; its use is discouraged".format(self.frameid), BozoFrameWarning)
        
        def encode():
            data = bytearray()
            for spec in self._framespec:
                data.extend(spec.write(self, getattr(self, spec.name)))
            return data

        def try_preferred_encodings():
            for encoding in EncodedStringSpec.preferred_encodings:
                try:
                    self.encoding = encoding
                    return encode()
                except UnicodeEncodeError:
                    pass
                finally:
                    self.encoding = None
            raise ValueError("Could not encode strings")
        
        if isinstance(self._framespec[0], EncodingSpec) and self.encoding is None:
            return try_preferred_encodings()
        else:
            try:
                return encode()
            except UnicodeEncodeError:
                return try_preferred_encodings()

    def __repr__(self):
        stype = type(self).__name__
        args = []
        if stype != self.frameid:
            args.append("frameid={0!r}".format(self.frameid))
        if self.flags:
            args.append("flags={0!r}".format(self.flags))
        for spec in self._framespec:
            if isinstance(spec, BinaryDataSpec):
                data = getattr(self, spec.name)
                if isinstance(data, (bytes, bytearray)):
                    args.append("{0}=<{1} bytes of binary data {2!r}{3}>".format(
                            spec.name, len(data), 
                            data[:20], "..." if len(data) > 20 else ""))
                else:
                    args.append(repr(data))
            else:
                args.append("{0}={1!r}".format(spec.name, getattr(self, spec.name)))
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

    def __init__(self, *values, frameid=None, flags=None, **kwargs):
        def extract_strs(values):
            if values is None:
                return
            if isinstance(values, str):
                yield values
            elif isinstance(values, collections.Iterable):
                for val in values:
                    for v in extract_strs(val):
                        yield v
            else:
                raise ValueError("Invalid text frame value")
        super().__init__(frameid=frameid, flags=flags, **kwargs)
        self.text = list(extract_strs(values))

    def _str_fields(self):
        return "{0} {1}".format((EncodedStringSpec._encodings[self.encoding][0] 
                                if self.encoding != None else "<undef>"),
                                ", ".join(repr(t) for t in self.text))

    @classmethod
    def _merge(cls, frames):
        frame = cls(text=[])
        for f in frames:
            frame.text.extend(f.text)
        return [frame]

class URLFrame(Frame):
    _framespec = (URLStringSpec("url"), )
    def _str_fields(self):
        return repr(self.url)

class CreditsFrame(Frame):
    _framespec = (EncodingSpec("encoding"),
                  MultiSpec("people",
                            EncodedStringSpec("involvement"),
                            EncodedStringSpec("person")))


def is_frame_class(cls):
    return (isinstance(cls, type)
            and issubclass(cls, Frame)
            and 3 <= len(cls.__name__) <= 4
            and cls.__name__ == cls.__name__.upper())
