from setuptools import setup


setup(
    name='pure_interface',
    version='4.0.1',
    py_modules=['pure_interface', 'pure_contracts'],
    url='https://github.com/seequent/pure_interface',
    install_requires=['six',
                      'typing; python_version<"3.5"',
                      'funcsigs; python_version<"3.5"'],
    extras_require={'contracts': ['PyContracts>=1.7']},
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    license='MIT',
    author='Tim Mitchell',
    author_email='tim.mitchell@seequent.com',
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords="abc interface adapt adaption mapper structural typing dataclass",
    description='A Python interface library that disallows function body content on interfaces and supports adaption.',
    long_description=open('README.rst').read(),
    test_suite='tests',
    tests_require='mock',
)
