"""
For tests that require python 3 only syntax.
"""
import sys

if sys.version_info < (3, 6):
    # These tests require annotations
    def load_tests(loader, standard_tests, pattern):
        return standard_tests
