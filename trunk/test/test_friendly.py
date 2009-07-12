#!/usr/bin/env python3
# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import os.path
import warnings

import stagger
from stagger.id3 import *

class FriendlyTestCase(unittest.TestCase):
    def testTitle22(self):
        tag = stagger.Tag22()

        tag[TT2] = "Foobar"
        self.assertEqual(tag.title, "Foobar")

        tag[TT2] = ("Foo", "Bar")
        self.assertEqual(tag.title, "Foo / Bar")
        
        tag.title = "Baz"
        self.assertEqual(tag[TT2], TT2(text=["Baz"]))
        self.assertEqual(tag.title, "Baz")
        
        tag.title = "Quux / Xyzzy"
        self.assertEqual(tag[TT2], TT2(text=["Quux", "Xyzzy"]))
        self.assertEqual(tag.title, "Quux / Xyzzy")

    def testTitle(self):
        for tagcls in stagger.Tag23, stagger.Tag24:
            tag = tagcls()

            tag[TIT2] = "Foobar"
            self.assertEqual(tag.title, "Foobar")

            tag[TIT2] = ("Foo", "Bar")
            self.assertEqual(tag.title, "Foo / Bar")

            tag.title = "Baz"
            self.assertEqual(tag[TIT2], TIT2(text=["Baz"]))
            self.assertEqual(tag.title, "Baz")

            tag.title = "Quux / Xyzzy"
            self.assertEqual(tag[TIT2], TIT2(text=["Quux", "Xyzzy"]))
            self.assertEqual(tag.title, "Quux / Xyzzy")

    def testTextFrames(self):
        for tagcls in stagger.Tag22, stagger.Tag23, stagger.Tag24:
            tag = tagcls()

            for attr, frame in (("title", TIT2),
                                ("artist", TPE1),
                                ("album_artist", TPE2),
                                ("album", TALB),
                                ("composer", TCOM),
                                ("genre", TCON),
                                ("grouping", TIT1),
                                ("sort_title", TSOT),
                                ("sort_artist", TSOP),
                                ("sort_album_artist", TSO2),
                                ("sort_album", TSOA),
                                ("sort_composer", TSOC)):
                if tagcls == stagger.Tag22:
                    frame = frame._v2_frame

                # No frame -> empty string
                self.assertEqual(getattr(tag, attr), "")

                # Set by frameid, check via friendly name
                tag[frame] = "Foobar"
                self.assertEqual(getattr(tag, attr), "Foobar")

                tag[frame] = ("Foo", "Bar")
                self.assertEqual(getattr(tag, attr), "Foo / Bar")

                # Set by friendly name, check via frame id
                setattr(tag, attr, "Baz")
                self.assertEqual(getattr(tag, attr), "Baz")
                self.assertEqual(tag[frame], frame(text=["Baz"]))

                setattr(tag, attr, "Quux / Xyzzy")
                self.assertEqual(getattr(tag, attr), "Quux / Xyzzy")
                self.assertEqual(tag[frame], frame(text=["Quux", "Xyzzy"]))

                # Set to empty string, check frame is gone
                setattr(tag, attr, "")
                self.assertTrue(frame not in tag)

                # Repeat, should not throw KeyError
                setattr(tag, attr, "")
                self.assertTrue(frame not in tag)

    def testTrackFrames(self):
        for tagcls in stagger.Tag22, stagger.Tag23, stagger.Tag24:
            tag = tagcls()
            for track, total, frame in (("track", "track_total", TRCK),
                                        ("disc", "disc_total", TPOS)):
                if tagcls == stagger.Tag22:
                    frame = frame._v2_frame
                
                # No frame -> zero values
                self.assertEqual(getattr(tag, track), 0)
                self.assertEqual(getattr(tag, total), 0)

                # Set by frameid, check via friendly name
                tag[frame] = "12"
                self.assertEqual(getattr(tag, track), 12)
                self.assertEqual(getattr(tag, total), 0)
                
                tag[frame] = "12/24"
                self.assertEqual(getattr(tag, track), 12)
                self.assertEqual(getattr(tag, total), 24)

                tag[frame] = "Foobar"
                self.assertEqual(getattr(tag, track), 0)
                self.assertEqual(getattr(tag, total), 0)

                # Set by friendly name, check via frame id
                setattr(tag, track, 7)
                self.assertEqual(getattr(tag, track), 7)
                self.assertEqual(getattr(tag, total), 0)
                self.assertEqual(tag[frame], frame(text=["7"]))

                setattr(tag, total, 21)
                self.assertEqual(getattr(tag, track), 7)
                self.assertEqual(getattr(tag, total), 21)
                self.assertEqual(tag[frame], frame(text=["7/21"]))
                
                # Set to 0/0, check frame is gone
                setattr(tag, total, 0)
                self.assertEqual(getattr(tag, track), 7)
                self.assertEqual(getattr(tag, total), 0)
                self.assertEqual(tag[frame], frame(text=["7"]))
                
                setattr(tag, track, 0) 
                self.assertEqual(getattr(tag, track), 0)
                self.assertEqual(getattr(tag, total), 0)
                self.assertTrue(frame not in tag)
               
                # Repeat, should not throw
                setattr(tag, track, 0) 
                setattr(tag, total, 0)
                self.assertTrue(frame not in tag)
                
                # Set just the total
                setattr(tag, total, 13)
                self.assertEqual(tag[frame], frame(text=["0/13"]))

suite = unittest.TestLoader().loadTestsFromTestCase(FriendlyTestCase)

if __name__ == "__main__":
    warnings.simplefilter("always", stagger.Warning)
    unittest.main(defaultTest="suite")
