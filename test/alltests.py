#!/usr/bin/env python3
# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import warnings

import stagger

import test.fileutil
import test.conversion
import test.specs
import test.samples
import test.tag
import test.friendly
import test.id3v1
import test.id3v1_fileop

suite = unittest.TestSuite()
suite.addTest(test.fileutil.suite)
suite.addTest(test.conversion.suite)
suite.addTest(test.specs.suite)
suite.addTest(test.samples.suite)
suite.addTest(test.tag.suite)
suite.addTest(test.friendly.suite)
suite.addTest(test.id3v1.suite)
suite.addTest(test.id3v1_fileop.suite)

if __name__ == "__main__":
    warnings.simplefilter("always", stagger.Warning)
    unittest.main(defaultTest="suite")
