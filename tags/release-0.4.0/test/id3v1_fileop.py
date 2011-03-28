#!/usr/bin/env python3
# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import random
import io
import warnings

import stagger
from stagger.errors import *

class ID3v1FileOpTestCase(unittest.TestCase):
    def testAddDeleteTag(self):
        """Add/delete random tags to a file, verify integrity."""
        origdata = bytearray(random.randint(0, 255) for i in range(512))
        origdata[-128:-125] = b'\xFF\xFF\xFF'
        data = bytearray(origdata)
        file = io.BytesIO(data)
        try:
            self.assertRaises(NoTagError, stagger.id3v1.Tag1.read, file)
            tag = stagger.id3v1.Tag1()
            tag.title = "Title"
            tag.artist = "Artist"
            tag.album = "Album"
            tag.year = "2009"
            tag.comment = "Comment"
            tag.track = 13
            tag.genre = "Salsa"
            tag.write(file)
            tag.write(file)
            tag2 = stagger.id3v1.Tag1.read(file)
            self.assertEqual(tag, tag2)
            stagger.id3v1.Tag1.delete(file)
            self.assertEqual(file.getvalue(), origdata)
        finally:
            file.close()

suite = unittest.TestLoader().loadTestsFromTestCase(ID3v1FileOpTestCase)

if __name__ == "__main__":
    warnings.simplefilter("always", stagger.Warning)
    unittest.main(defaultTest="suite")
