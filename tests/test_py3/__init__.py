"""
For tests that require python 3 only syntax.
"""
import six

if six.PY2:
    # don't import this package on python2
    def load_tests(loader, standard_tests, pattern):
        return standard_tests
