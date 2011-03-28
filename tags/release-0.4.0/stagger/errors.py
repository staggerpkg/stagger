# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

class Error(Exception): pass

class Warning(Error, UserWarning): pass

class FrameWarning(Warning): pass
class ErrorFrameWarning(FrameWarning): pass
class UnknownFrameWarning(FrameWarning): pass
class EmptyFrameWarning(FrameWarning): pass
class DuplicateFrameWarning(FrameWarning): pass
class UntestedFrameWarning(FrameWarning): pass
class BozoFrameWarning(FrameWarning): pass

class TagWarning(Warning): pass

class NoTagError(Error): pass
class TagError(Error, ValueError): pass
class NotAFrameError(Error): pass
class FrameError(Error): pass
class IncompatibleFrameError(FrameError): pass
