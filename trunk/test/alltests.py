#!/usr/bin/env python3
# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import warnings

import stagger

import test_fileutil
import test_conversion
import test_specs
import test_samples
import test_tag
import test_id3v1
import test_id3v1_fileop

suite = unittest.TestSuite()
suite.addTest(test_fileutil.suite)
suite.addTest(test_conversion.suite)
suite.addTest(test_specs.suite)
suite.addTest(test_samples.suite)
suite.addTest(test_tag.suite)
suite.addTest(test_id3v1.suite)
suite.addTest(test_id3v1_fileop.suite)

if __name__ == "__main__":
    warnings.simplefilter("always", stagger.Warning)
    unittest.main(defaultTest="suite")
