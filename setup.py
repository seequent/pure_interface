from setuptools import setup


setup(
    name='pure_interface',
    version='4.0.2',
    py_modules=['pure_interface', 'pure_contracts'],
    url='https://github.com/seequent/pure_interface',
    extras_require={'contracts': ['PyContracts>=1.7']},
    python_requires='>=3.6',
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

        # Specify the Python versions you support here.
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords="abc interface adapt adaption mapper structural typing dataclass",
    description='A Python interface library that disallows function body content on interfaces and supports adaption.',
    long_description=open('README.rst').read(),
    test_suite='tests',
)
