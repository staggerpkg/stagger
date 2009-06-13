#!/usr/bin/python3

import stagger
import os
import random
import warnings
import sys
import shutil

warnings.simplefilter("always", stagger.Warning)
#warnings.simplefilter("error", stagger.Warning)

w1 = r"C:\Users\lorentey\Music"
w2 = r"S:\Music"
root3 = r"."
l4 = r"/data/public/Music"

def list_mp3s(roots):
    for root in roots:
        if root.endswith(".mp3"):
            yield root
        else:
            for root, dirs, files in os.walk(root):
                dirs.sort()
                for file in sorted(files):
                    if file.endswith(".mp3"):
                        yield os.path.join(root, file)

def head(iterable, limit):
    if limit is None:
        for elem in iterable:
            yield elem
    else:
        for elem, i in zip(iterable, range(limit)):
            yield elem

def test(*roots, wait=False, randomize=False, limit=None, catch_errors=True):
    mp3s = list_mp3s(roots)

    if randomize:
        mp3s = list(mp3s)
        print("{0} files found".format(len(mp3s)))
        random.shuffle(mp3s)

    for mp3 in head(mp3s, limit):
        try:
            print(mp3)
            with stagger.read(mp3) as tag:
                print(tag)
                for frame in tag.frames():
                    print("    " + str(frame))
        except stagger.NoTagError:
            pass
        except Exception as e:
            if catch_errors:
                print("{0}: {1} {2}".format(mp3, type(e).__name__, str(e)))
            else:
                raise
        if wait: input()

def test_encode(file):
    with stagger.read(file) as tag:
        print(tag)
        for frame in tag.frames():
            print(" " + str(frame))
            data = tag._encode_one_frame(frame)
            print("    ==> {0}/{1}{2}".format(len(data),
                                              data[:30],
                                              "..." if len(data) > 30 else ""))


def t(filename, tag, out="test.mp3"):
    warnings.simplefilter("always")
    shutil.copy(filename, out)
    frames = stagger.read(filename)
    print([f.frameid for f in frames])
    tag.write(out, frames)
    print("------------")
    frames2 = stagger.read(out)
    print([f.frameid for f in frames2])

