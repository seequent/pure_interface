"""
For tests that require python 3.8 positional only argument syntax.
"""
import sys

if sys.version_info < (3, 8):
    # These tests require positional only arguments
    def load_tests(loader, standard_tests, pattern):
        return standard_tests
