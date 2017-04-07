from setuptools import setup
import pure_interface

setup(
    name='pure_interface',
    version=pure_interface.__version__,
    py_modules=['pure_interface'],
    url='https://github.com/tim-mitchell/pure_interface',
    install_requires=['six'],
    license='MIT',
    author='Tim Mitchell',
    author_email='tim.mitchell@aranzgeo.com',
    keywords="abc interface adapt adaption mapper",
    description='A Python interface library that disallows function body content on interfaces and supports adaption.',
    long_description=open('README.rst').read(),
    test_suite='tests',
    tests_require='mock',
)
