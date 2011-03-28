#!/usr/bin/env python3
# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

import unittest
import io
import random
import tempfile
import warnings
import os
import signal

from stagger.fileutil import *

class FileutilTestCase(unittest.TestCase):
    def testSuppressInterrupt(self):
        foo = 0
        try:
            with suppress_interrupt():
                # Verify that KeyboardInterrupts are deferred
                # until the end of this block.
                foo += 1
                os.kill(0, signal.SIGINT)  # Simulate C-c
                foo += 1
        except KeyboardInterrupt:
            # This should be triggered, but only after the second increment.
            foo += 1
        except AttributeError:
            # There is no os.kill on Windows: we can't test this feature there.
            return
        self.assertEqual(foo, 3, "Can't suppress interrupts")

    def testReplaceChunk(self):
        def compare(data, filename):
            with opened(filename, "rb") as file:
                data2 = file.read()
                return data == data2
        def random_data(length):
            return bytearray(random.randint(0, 255) for i in range(length))
        def random_offset(size):
            r = random.randint(0, 10)
            if r < 2:
                return 0
            if r < 4:
                return size
            return random.randint(0, size)
        def random_length(maxsize=None):
            if maxsize is None:
                maxsize = CHUNK_SIZE_MAX
            maxsize = min(maxsize, CHUNK_SIZE_MAX)
            r = random.randint(0, 10)
            if r < 2:
                return 0
            if r < 4:
                return maxsize
            return random.randint(0, maxsize)
        def replace_both(data, filename, offset, length, chunk, in_place):
            data[offset:offset + length] = chunk
            replace_chunk(filename, offset, length, chunk, in_place=in_place)

        FILESIZE = 100 * 1024
        CHUNK_SIZE_MAX = 10 * 1024
        
        # Create a random temp file and a matching bytearray; replace some random chunks
        # with other random chunks in both objects; results should match.
        for in_place in [False, True]:
            data = random_data(FILESIZE)
            file = tempfile.NamedTemporaryFile(prefix="staggertest-", suffix=".tmp", delete=False)
            try:
                filename = file.name
                file.write(data)
                file.close()
                size = len(data)
                for i in range(40):
                    offset = random_offset(size)
                    length = random_length(size - offset)
                    if random.randint(0, 6) == 0:
                        chunk_length = length
                    else:
                        chunk_length = random_length()
                    chunk = random_data(chunk_length)
                    #print("i={0} size={1} offset={2} length={3} chunk={4} in_place={5}"
                    #      .format(i, size, offset, length, len(chunk), in_place))
                    replace_both(data, filename, offset, length, chunk, in_place)
                    self.assertTrue(compare(data, filename))
                    size += len(chunk) - length
                    self.assertTrue(size == len(data))
            finally:
                os.unlink(filename)
        
suite = unittest.TestLoader().loadTestsFromTestCase(FileutilTestCase)

if __name__ == "__main__":
    warnings.simplefilter("always", stagger.Warning)
    unittest.main(defaultTest="suite")

