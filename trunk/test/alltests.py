import unittest

import test_conversion
import test_specs


suite = unittest.TestSuite()
suite.addTest(test_conversion.suite)
suite.addTest(test_specs.suite)

if __name__ == "__main__":
    unittest.main(defaultTest="suite")
