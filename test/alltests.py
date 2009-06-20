import unittest

import test_conversion
import test_specs
import test_samples

suite = unittest.TestSuite()
suite.addTest(test_conversion.suite)
suite.addTest(test_specs.suite)
suite.addTest(test_samples.suite)

if __name__ == "__main__":
    unittest.main(defaultTest="suite")
