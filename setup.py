from os import path
from codecs import open  # To use a consistent encoding
import glob

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='atn-tools',

    version='0.0.1a0',

    description='Tools for running and analyzing ATN simulations',
    long_description=long_description,

    url='https://github.com/brsaylor/atn-tools',

    author='Ben Saylor',
    author_email='brsaylor@gmail.com',

    license='GNU General Public License v3 or later (GPLv3+)',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='atn simulation ecology machine learning',

    packages=find_packages(),
    scripts=glob.glob('bin/*'),

    # FIXME: reference environment.yml?
    # install_requires=[],

    package_data={
        'atntools': ['data/*.*', 'data/*/*.*'],
    },
)
