Stagger is an ID3v1/ID3v2 tag manipulation package written in pure Python 3.

The ID3v2 tag format is notorious for its useless specification documents and its quirky, mutually incompatible part-implementations.  Stagger is to provide a robust tagging package that is able to handle all the various badly formatted tags out there and allow you to convert them to a consensus format.

The package is currently in beta stage, under active development.  APIs are getting stable, but not yet final.

Features currently implemented:
  * Reads and writes ID3 v1.0, 1.1, 2.2, 2.3 and 2.4 tags.
  * Supports conversion between tag versions.
  * Supports unsynchronized tags (all versions) and compressed frames (2.3 and 2.4 only).
  * Full Unicode support, with customizable text encoding preferences.
  * Has built-in support for all standard frame types (plus a few nonstandard ones). Easily extensible with additional frame types if needed.
  * Supports duplicate frames and multiple text strings in a single frame.
  * Supports reading/writing frames of unrecognized types and frames with invalid data.  Automatically recognizes unknown text and URL frames.
  * The order of frames in a tag is fully customizable.
  * Package comes with extensive unit tests for an extra measure of code kwalitee.
  * Tested under Mac OS X, Windows and GNU/Linux.

```
>>> import stagger
>>> form stagger.id3 import *       # contains ID3 frame types

>>> tag = stagger.read_tag("track01.mp3")          

>>> tag[TIT2]                                      # tag is a MutableMapping
TIT2(utf-8 "Staralfur")

>>> tag[TIT2] = TIT2(text="The Show Must Go On")   # Explicit constructor
>>> tag[TIT2] = "The Show Must Go On"              # Implicit constructor
>>> tag[TIT2] = ("Foo", "Bar", "Baz")              # Multiple strings
>>> tag.title = "The Battle of Evermore"           # Alternative, friendlier API

>>> tag.write()
```