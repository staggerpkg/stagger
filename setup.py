#!/usr/bin/env python3
 
import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup;

setup(
    name="stagger",
    version="0.4.0",
    url="http://code.google.com/p/stagger",
    author="Karoly Lorentey",
    author_email="karoly@lorentey.hu",
    packages=["stagger"],
    entry_points = {
        'console_scripts': ['stagger = stagger.commandline:main']
    },
    test_suite = "test.alltests.suite",
    license="BSD",
    description="ID3v1/ID3v2 tag manipulation package in pure Python 3",
    long_description="""
The ID3v2 tag format is notorious for its useless specification
documents and its quirky, mutually incompatible
part-implementations. Stagger is to provide a robust tagging package
that is able to handle all the various badly formatted tags out there
and allow you to convert them to a consensus format.
""",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio"
        ],
    )
