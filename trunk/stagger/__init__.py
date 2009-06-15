# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import stagger.tags

from stagger.errors import *
from stagger.tags import read_tag, Tag22, Tag23, Tag24

def write_tag(filename, frames):
    Tag24.write(filename, frames)
