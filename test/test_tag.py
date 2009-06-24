# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import os.path

import stagger
from stagger.id3 import *



class TagTestCase(unittest.TestCase):
    def testBasic(self):
        for cls, frm in (stagger.Tag22, TT2), (stagger.Tag23, TIT2), (stagger.Tag24, TIT2):
            tag = cls()
            # New tag must be empty
            self.assertEqual(len(tag), 0)

            # Set a frame using a single string, see if it's in the tag
            tag[frm] = "Foobar"
            self.assertTrue(frm.frameid in tag)
            self.assertTrue(frm in tag)
            self.assertEqual(len(tag), 1)
            self.assertEqual(len(tag._frames[frm.frameid]), 1)
            # Compare value to hand-constructed frame
            self.assertEqual(len(tag[frm].text), 1)
            self.assertEqual(tag[frm].text[0], "Foobar")
            self.assertEqual(tag[frm], frm(encoding=None, text=["Foobar"]))

            # Override the above text frame with a multivalue text frame
            tag[frm] = ("Foo", "bar", "baz")
            self.assertEqual(len(tag), 1)
            self.assertEqual(len(tag._frames[frm.frameid]), 1)
            self.assertEqual(tag[frm], frm(encoding=None, text=["Foo", "bar", "baz"]))

            # Delete frame from tag, verify it's gone
            del tag[frm]
            self.assertEqual(len(tag), 0)
            self.assertTrue(frm not in tag)
            self.assertTrue(frm.frameid not in tag)

    def testPadding(self):
        for tagcls, frames in ((stagger.Tag22, (TT2, TP1)), 
                               (stagger.Tag23, (TIT2, TPE1)), 
                               (stagger.Tag23, (TIT2, TPE1))):
            # Create a simple tag
            tag = tagcls()
            for frame in frames:
                tag[frame] = frame.frameid.lower()
        
            # Try encoding tag with various padding options
            tag.padding_max = 0
            tag.padding_default = 0
            data_nopadding_nohint = tag.encode()
            data_nopadding_hint = tag.encode(size_hint=500)
            length = len(data_nopadding_nohint)
            self.assertEqual(len(data_nopadding_nohint), len(data_nopadding_hint))
            self.assertTrue(data_nopadding_nohint == data_nopadding_hint)

            tag.padding_max = 1000
            data_max_nohint = tag.encode()
            data_max_hint = tag.encode(size_hint=500)
            data_max_largehint = tag.encode(size_hint=5000)
            self.assertEqual(len(data_max_nohint), length)
            self.assertEqual(len(data_max_hint), 500)
            self.assertEqual(len(data_max_largehint), length)
            self.assertTrue(data_max_nohint[10:] == data_max_hint[10:length])

            tag.padding_default = 250
            data_default_nohint = tag.encode()
            data_default_okhint = tag.encode(size_hint=500)
            data_default_largehint = tag.encode(size_hint=2000)
            data_default_smallhint = tag.encode(size_hint=20)
            self.assertEqual(len(data_default_nohint), length + 250)
            self.assertEqual(len(data_default_okhint), 500)
            self.assertEqual(len(data_default_largehint), length + 250)
            self.assertEqual(len(data_default_smallhint), length + 250)

    def testFrameOrder(self):
        # 24.stagger.sample-01.id3 contains a simple test tag that has file frames
        # in the following order:
        #
        # TIT2("TIT2"), TPE1("TPE1"), TALB("TALB"), TRCK("TRCK"), TPE2("TPE2")
        
        testfile = os.path.join(os.path.dirname(__file__), "samples", "24.stagger.sample-01.id3")
        framelist = [TRCK, TPE2, TALB, TIT2, TPE1]

        # Read tag, verify frame ordering is preserved
        tag = stagger.read_tag(testfile)
        self.assertEqual(len(tag), 5) 
        self.assertEqual(set(tag.keys()), set(frame.frameid for frame in framelist))
        self.assertEqual([frame.frameid for frame in tag.frames()], [frame.frameid for frame in framelist])

        # Test frame contents
        for framecls in framelist:
            # tag[TIT2] == tag["TIT2"]
            self.assertTrue(framecls in tag)
            self.assertTrue(framecls.frameid in tag)
            self.assertEqual(tag[framecls], tag[framecls.frameid])

            # type(tag[TIT2]) == TIT2
            self.assertTrue(isinstance(tag[framecls], framecls))

            # Each frame contains a single string, which is the frame id in lowercase.
            self.assertEqual(len(tag[framecls].text), 1)
            self.assertEqual(tag[framecls].text[0], framecls.frameid.lower())

        # Encode tag with default frame ordering, verify result is different.

        with open(testfile, "rb") as file:
            filedata = file.read()

        tag.padding_max = 0

        # Default sorting order is different.
        tagdata = tag.encode()
        self.assertEqual(len(tagdata), len(filedata))
        self.assertFalse(tagdata == filedata)

        # Override the sort order with an empty list, verify resulting order is the same as in the original file.

        tag.frame_order = stagger.tags.FrameOrder()
        tagdata = tag.encode()
        self.assertTrue(tagdata == filedata)

        tag2 = stagger.decode_tag(tagdata)
        self.assertTrue(tag == tag2)

suite = unittest.TestLoader().loadTestsFromTestCase(TagTestCase)

if __name__ == "__main__":
    unittest.main(defaultTest="suite")


