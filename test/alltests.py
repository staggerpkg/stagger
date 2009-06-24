import unittest

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
    unittest.main(defaultTest="suite")
