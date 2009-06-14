# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

class Error(Exception): pass

class Warning(Error, UserWarning): pass
class UntestedFrameWarning(Warning): pass
class BozoFrameWarning(Warning): pass

class NoTagError(Error): pass
class TagError(Error, ValueError): pass
class NotAFrameError(Error): pass
class FrameError(Error): pass
class IncompatibleFrameError(FrameError): pass
