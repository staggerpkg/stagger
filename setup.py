#!/usr/bin/env python

from distutils.core import setup;

setup(
    name="stagger",
    version="0.2.0",
    url="http://code.google.com/p/stagger",
    author="Karoly Lorentey",
    author_email="karoly@lorentey.hu",
    packages=["stagger"],
    description="ID3v1/ID3v2 tag manipulation package in pure Python 3",
    long_description="""
The package is currently in alpha stage, under active development.

The ID3v2 tag format is notorious for its useless specification
documents and its quirky, mutually incompatible
part-implementations. Stagger is to provide a robust tagging package
that is able to handle all the various badly formatted tags out there
and allow you to convert them to a consensus format.
""",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Sound/Audio"
        ],
    )
