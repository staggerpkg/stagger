# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import os
import os.path

import stagger

class SamplesTestCase(unittest.TestCase):
    sample_dir = os.path.join(os.path.dirname(__file__), "samples")
    
    def list_id3(self, path):
        for root, dirs, files in os.walk(path):
            dirs.sort()
            for file in sorted(files):
                if file.endswith(".id3"):
                    yield os.path.join(root, file)

    def testLoadSamples(self):
        for file in self.list_id3(self.sample_dir):
            tag = stagger.read_tag(file)

suite = unittest.TestLoader().loadTestsFromTestCase(SamplesTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest="suite")

