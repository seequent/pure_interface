from setuptools import setup, find_packages

setup(
    name='pure_interface',
    version='1.0',
    packages=find_packages(),
    url='https://github.com/tim-mitchell/pure_interface',
    install_requires=['six'],
    license='MIT',
    author='Tim Mitchell',
    author_email='tim.mitchell@aranzgeo.com',
    keywords="abc interface adapt adaption mapper",
    description='A Python interface library that disallows function body content on interfaces and supports adaption.'
)
