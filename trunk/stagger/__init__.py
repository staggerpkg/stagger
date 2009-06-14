# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import stagger.tags

from stagger.errors import *
from stagger.tags import Tag22, Tag23, Tag24

def read_tag(filename):
    with stagger.tags.lazy_read(filename) as tag:
        return [frame for frame in tag.frames()]

def write_tag(filename, frames):
    Tag24.write(filename, frames)
