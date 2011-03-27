# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import stagger.frames
import stagger.tags
import stagger.id3
import stagger.util

from stagger.errors import *
from stagger.frames import Frame, ErrorFrame, UnknownFrame, TextFrame, URLFrame
from stagger.tags import read_tag, decode_tag, delete_tag, Tag22, Tag23, Tag24
from stagger.id3v1 import Tag1

version = (0, 4, 0)
versionstr = ".".join((str(v) for v in version))

default_tag = Tag24

stagger.util.python_version_check()
