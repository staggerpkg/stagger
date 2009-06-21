# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import os
import os.path
import warnings

import stagger
from stagger.id3 import *

class SamplesTestCase(unittest.TestCase):
    sample_dir = os.path.join(os.path.dirname(__file__), "samples")
    
    def list_id3(self, path):
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for file in sorted(files):
                if file.endswith(".id3"):
                    yield os.path.join(root, file)

    def testLoadSamples(self):
        warnings.simplefilter("ignore", stagger.Warning)
        for file in self.list_id3(self.sample_dir):
            tag = stagger.read_tag(file)

            # Scrub iTunes-produced invalid frames with frameids ending with space.
            # Stagger won't save these, so they would result in a tag mismatch below.
            badfile = False
            for key in list(tag.keys()):
                if key.endswith(" "):
                    del tag[key]
                    badfile = True

            tag.padding_max = 0
            data = tag.encode()
            tag2 = stagger.decode_tag(data)
            tag.padding_max = 0
            data2 = tag.encode()

            self.assertEqual(data, data2, "data mismatch in file {0}".format(file))
            self.assertEqual(tag, tag2, "tag mismatch in file{0}".format(file))

suite = unittest.TestLoader().loadTestsFromTestCase(SamplesTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest="suite")

