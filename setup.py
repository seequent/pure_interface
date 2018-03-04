from setuptools import setup
import pure_interface

setup(
    name='pure_interface',
    version=pure_interface.__version__,
    py_modules=['pure_interface', 'pure_contracts'],
    url='https://github.com/aranzgeo/pure_interface',
    install_requires=['six'],
    extras_require={'contracts': ['PyContracts>=1.7']},
    license='MIT',
    author='Tim Mitchell',
    author_email='tim.mitchell@seequent.com',
    keywords="abc interface adapt adaption mapper",
    description='A Python interface library that disallows function body content on interfaces and supports adaption.',
    long_description=open('README.rst').read(),
    test_suite='tests',
    tests_require='mock',
)
