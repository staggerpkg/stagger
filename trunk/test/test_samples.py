# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import os
import os.path
import warnings

import stagger
from stagger.id3 import *

def list_id3(path):
    for root, dirs, files in os.walk(path):
        dirs.sort()
        for file in sorted(files):
            if file.endswith(".id3"):
                yield os.path.join(root, file)

def generate_test(file):
    def test(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", stagger.Warning)
            tag = stagger.read_tag(file)

            prefix_to_class = {
                "22.": stagger.Tag22,
                "23.": stagger.Tag23,
                "24.": stagger.Tag24
                }

            # Check tag version based on filename prefix
            basename = os.path.basename(file)
            self.assertTrue(any(basename.startswith(prefix) for prefix in prefix_to_class))
            for prefix in prefix_to_class:
                if basename.startswith(prefix):
                    self.assertEqual(type(tag), prefix_to_class[prefix])
                    self.assertEqual(tag.version, int(prefix[1]))

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
    return test

class SamplesTestCase(unittest.TestCase):
    pass

sample_dir = os.path.join(os.path.dirname(__file__), "samples")

for file in list_id3(sample_dir):
    method = "test_" + os.path.basename(file).replace(".", "_")
    setattr(SamplesTestCase, method, generate_test(file))

suite = unittest.TestLoader().loadTestsFromTestCase(SamplesTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest="suite")

