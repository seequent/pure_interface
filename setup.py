from setuptools import setup


setup(
    name='pure_interface',
    version='3.0.0',
    py_modules=['pure_interface', 'pure_contracts'],
    url='https://github.com/aranzgeo/pure_interface',
    install_requires=['six', 'typing'],
    extras_require={'contracts': ['PyContracts>=1.7']},
    license='MIT',
    author='Tim Mitchell',
    author_email='tim.mitchell@seequent.com',
    keywords="abc interface adapt adaption mapper structural typing",
    description='A Python interface library that disallows function body content on interfaces and supports adaption.',
    long_description=open('README.rst').read(),
    test_suite='tests',
    tests_require='mock',
)
