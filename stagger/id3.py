# Copyright (c) 2009, Karoly Lorentey  <karoly@lorentey.hu>

"""List of frames defined in the various ID3 versions.
"""

import imghdr

import stagger.frames as Frames
from stagger.specs import *



# ID3v2.4

# 4.2.1. Identification frames
class UFID(Frames.Frame):
    "Unique file identifier"
    _framespec = (NullTerminatedStringSpec("owner"), BinaryDataSpec("data"))
    _allow_duplicates = True

class TIT1(Frames.TextFrame): 
    "Content group description"

class TIT2(Frames.TextFrame): 
    "Title/songname/content description"

class TIT3(Frames.TextFrame): 
    "Subtitle/Description refinement"

class TALB(Frames.TextFrame): 
    "Album/Movie/Show title"

class TOAL(Frames.TextFrame): 
    "Original album/movie/show title"

class TRCK(Frames.TextFrame): 
    "Track number/Position in set"
# #/#

class TPOS(Frames.TextFrame): 
    "Part of a set"
# #/#

class TSST(Frames.TextFrame):
    "Set subtitle"
    _version = 4

class TSRC(Frames.TextFrame): 
    "ISRC (international standard recording code)"


# 4.2.2. Involved persons frames
class TPE1(Frames.TextFrame): 
    "Lead performer(s)/Soloist(s)"

class TPE2(Frames.TextFrame): 
    "Band/orchestra/accompaniment"

class TPE3(Frames.TextFrame): 
    "Conductor/performer refinement"

class TPE4(Frames.TextFrame): 
    "Interpreted, remixed, or otherwise modified by"

class TOPE(Frames.TextFrame): 
    "Original artist(s)/performer(s)"

class TEXT(Frames.TextFrame): "Lyricist/Text writer"
class TOLY(Frames.TextFrame): "Original lyricist(s)/text writer(s)"
class TCOM(Frames.TextFrame): "Composer"

class TMCL(Frames.CreditsFrame):
    "Musician credits list"
    _version = 4

class TIPL(Frames.CreditsFrame):
    "Involved people list"
    _version = 4

class TENC(Frames.TextFrame): "Encoded by"



# 4.2.3. Derived and subjective properties frames

class TBPM(Frames.TextFrame): "BPM (beats per minute)"
# integer in string format

class TLEN(Frames.TextFrame): "Length"
# milliseconds in string format

class TKEY(Frames.TextFrame): "Initial key"
# /^([CDEFGAB][b#]?[m]?|o)$/

class TLAN(Frames.TextFrame): "Language(s)"
# /^...$/  ISO 639-2

class TCON(Frames.TextFrame): "Content type"
# integer  - ID3v1
# RX - Remix
# CR - Cover
# Freeform text
# id3v2.3: (number), 

class TFLT(Frames.TextFrame): "File type"
class TMED(Frames.TextFrame): "Media type"
class TMOO(Frames.TextFrame):
    "Mood"
    _version = 4


# 4.2.4. Rights and license frames

class TCOP(Frames.TextFrame): "Copyright message"
class TPRO(Frames.TextFrame):
    "Produced notice"
    _version = 4
    
class TPUB(Frames.TextFrame): "Publisher"
class TOWN(Frames.TextFrame): "File owner/licensee"
class TRSN(Frames.TextFrame): "Internet radio station name"
class TRSO(Frames.TextFrame): "Internet radio station owner"



# 4.2.5. Other text frames

class TOFN(Frames.TextFrame): "Original filename"
class TDLY(Frames.TextFrame): "Playlist delay"
# milliseconds

class TDEN(Frames.TextFrame):
    # timestamp
    "Encoding time"
    _version = 4

class TDOR(Frames.TextFrame):
    "Original release time"
    # timestamp
    _version = 4

class TDRC(Frames.TextFrame):
    "Recording time"
    # timestamp
    _version = 4

class TDRL(Frames.TextFrame):
    "Release time"
    # timestamp
    _version = 4

class TDTG(Frames.TextFrame):
    "Tagging time"
    # timestamp
    _version = 4

class TSSE(Frames.TextFrame): 
    "Software/Hardware and settings used for encoding"

class TSOA(Frames.TextFrame):
    "Album sort order"
    _version = 4

class TSOP(Frames.TextFrame):
    "Performer sort order"
    _version = 4

class TSOT(Frames.TextFrame):
    "Title sort order"
    _version = 4


# 4.2.6. User defined information frame

class TXXX(Frames.Frame):
    "User defined text information frame"
    _framespec = (EncodingSpec("encoding"),
                  EncodedStringSpec("description"),
                  EncodedStringSpec("value"))
    _allow_duplicates = True


# 4.3. URL link frames

class WCOM(Frames.URLFrame): 
    "Commercial information"
    _allow_duplicates = True

class WCOP(Frames.URLFrame): 
    "Copyright/Legal information"

class WOAF(Frames.URLFrame): 
    "Official audio file webpage"

class WOAR(Frames.URLFrame): 
    "Official artist/performer webpage"
    _allow_duplicates = True

class WOAS(Frames.URLFrame): 
    "Official audio source webpage"

class WORS(Frames.URLFrame): 
    "Official Internet radio station homepage"

class WPAY(Frames.URLFrame): 
    "Payment"

class WPUB(Frames.URLFrame): 
    "Publishers official webpage"

class WXXX(Frames.Frame):
    "User defined URL link frame"
    _framespec = (EncodingSpec("encoding"),
                  EncodedStringSpec("description"),
                  URLStringSpec("url"))
    _allow_duplicates = True


# 4.4.-4.13  Junk frames
class MCDI(Frames.Frame):
    "Music CD identifier"
    _framespec = (BinaryDataSpec("cd_toc"),)

class ETCO(Frames.Frame):
    "Event timing codes"
    _framespec = (ByteSpec("format"),
                  MultiSpec("events", ByteSpec("type"), IntegerSpec("timestamp", 4)))
    _untested = True
    _bozo = True

class MLLT(Frames.Frame):
    "MPEG location lookup table"
    _framespec = (IntegerSpec("frames", 2), IntegerSpec("bytes", 3),
                  IntegerSpec("milliseconds", 3),
                  ByteSpec("bits_for_bytes"), ByteSpec("bits_for_milliseconds"),
                  BinaryDataSpec("data"))
    _untested = True
    _bozo = True

class SYTC(Frames.Frame):
    "Synchronised tempo codes"
    _framespec = (ByteSpec("format"), BinaryDataSpec("data"))
    _untested = True
    _bozo = True

class USLT(Frames.Frame):
    "Unsynchronised lyric/text transcription"
    _framespec = (EncodingSpec("encoding"), LanguageSpec("lang"),
                  EncodedStringSpec("desc"), EncodedFullTextSpec("text"))
    _allow_duplicates = True
    _untested = True
    
class SYLT(Frames.Frame):
    "Synchronised lyric/text"
    _framespec = (EncodingSpec("encoding"), LanguageSpec("lang"),
                  ByteSpec("format"), ByteSpec("type"),
                  EncodedStringSpec("desc"),
                  MultiSpec("data", EncodedFullTextSpec("text"), IntegerSpec("timestamp", 4)))
    _allow_duplicates = True
    _untested = True
    _bozo = True

class COMM(Frames.Frame):
    "Comments"
    _framespec = (EncodingSpec("encoding"), LanguageSpec("lang"),
                  EncodedStringSpec("desc"), EncodedFullTextSpec("text"))
    _allow_duplicates = True

class RVA2(Frames.Frame):
    "Relative volume adjustment (2)"
    _framespec = (NullTerminatedStringSpec("desc"),
                  MultiSpec("adjustment",
                            ByteSpec("channel"),
                            IntegerSpec("gain", 2),  # * 512
                            VarIntSpec("peak")))
    _allow_duplicates = True
    _untested = True

class EQU2(Frames.Frame):
    "Equalisation (2)"
    _framespec = (ByteSpec("method"), NullTerminatedStringSpec("desc"),
                  MultiSpec("adjustments",
                            IntegerSpec("frequency", 2), # in 0.5Hz
                            SignedIntegerSpec("adjustment", 2))) # * 512x
    _allow_duplicates = True
    _untested = True
    _bozo = True

class RVRB(Frames.Frame):
    "Reverb"
    _framespec = (IntegerSpec("left", 2),
                  IntegerSpec("right", 2),
                  ByteSpec("bounce_left"), ByteSpec("bounce_right"),
                  ByteSpec("feedback_ltl"), ByteSpec("feedback_ltr"),
                  ByteSpec("feedback_rtr"), ByteSpec("feedback_rtl"),
                  ByteSpec("premix_ltr"), ByteSpec("premix_rtl"))
    _untested = True
    _bozo = True

class APIC(Frames.Frame):
    "Attached picture"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("mime"),
                  ByteSpec("type"),
                  EncodedStringSpec("desc"),
                  BinaryDataSpec("data"))
    _allow_duplicates = True

    def _to_version(self, version):
        if version in (3, 4):
            return self
        if self.mime.lower() not in ("image/jpeg", "image/jpg", "image/png"):
            raise ValueError("Unsupported image format")
        return PIC(format="PNG" if self.mime.lower() == "image/png" else "JPG",
                   type=self.type,
                   desc=self.desc,
                   data=self.data)
            
    def _str_fields(self):
        img = "{0} bytes of {1} data".format(len(self.data), 
                                             imghdr.what(None, self.data[:32]))
        return "{0}({1}), desc={2}, mime={3}: {4}".format(self.type,
                                                          picture_types[self.type],
                                                          repr(self.desc),
                                                          repr(self.mime),
                                                          img)
    

class GEOB(Frames.Frame):
    "General encapsulated object"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("mime"),
                  EncodedStringSpec("filename"),
                  EncodedStringSpec("desc"),
                  BinaryDataSpec("data"))
    _allow_duplicates = True

class PCNT(Frames.Frame):
    "Play counter"
    _framespec = (IntegerSpec("count", 4),)

class POPM(Frames.Frame):
    "Popularimeter"
    _framespec = (NullTerminatedStringSpec("email"),
                  ByteSpec("rating"),
                  IntegerSpec("count", 4))
    _allow_duplicates = True

class RBUF(Frames.Frame):
    "Recommended buffer size"
    _framespec = (IntegerSpec("size", 4),
                  #optional:
                  ByteSpec("info"),
                  IntegerSpec("offset", 4))
    _untested = True
    _bozo = True

class AENC(Frames.Frame):
    "Audio encryption"
    _framespec = (NullTerminatedStringSpec("owner"),
                  IntegerSpec("preview_start", 2),
                  IntegerSpec("preview_length", 2),
                  BinaryDataSpec("data"))
    _allow_duplicates = True
    _untested = True
    _bozo = True

class LINK(Frames.Frame):
    "Linked information"
    _framespec = (SimpleStringSpec("linked_frameid", 4),
                  NullTerminatedStringSpec("url"),
                  # optional
                  BinaryDataSpec("data"))
    _allow_duplicates = True
    _untested = True
    _bozo = True

class POSS(Frames.Frame):
    "Position synchronisation frame"
    _framespec = (ByteSpec("format"),
                  IntegerSpec("position", 4))
    _untested = True
    _bozo = True

class USER(Frames.Frame):
    "Terms of use"
    # TODO: emusic.com forgets the language field
    _framespec = (EncodingSpec("encoding"),
                  LanguageSpec("lang"),
                  EncodedStringSpec("text"))
    _allow_duplicates = True

class OWNE(Frames.Frame):
    "Ownership frame"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("price"),
                  SimpleStringSpec("date", 8),
                  NullTerminatedStringSpec("seller"))
    _untested = True
    _bozo = True

class COMR(Frames.Frame):
    "Commercial frame"
    _framespec = (EncodingSpec("encoding"),
                  NullTerminatedStringSpec("price"),
                  NullTerminatedStringSpec("valid"),
                  NullTerminatedStringSpec("contact"),
                  ByteSpec("format"),
                  EncodedStringSpec("seller"),
                  EncodedStringSpec("desc"),
                  NullTerminatedStringSpec("mime"),
                  BinaryDataSpec("logo"))
    _allow_duplicates = True
    _untested = True
    _bozo = True

class ENCR(Frames.Frame):
    "Encryption method registration"
    _framespec = (NullTerminatedStringSpec("owner"),
                  ByteSpec("symbol"),
                  BinaryDataSpec("data"))
    _allow_duplicates = True
    _untested = True
    _bozo = True


class GRID(Frames.Frame):
    "Group identification registration"
    _framespec = (NullTerminatedStringSpec("owner"),
                  ByteSpec("symbol"),
                  BinaryDataSpec("data"))
    _allow_duplicates = True
    _untested = True
    _bozo = True

class PRIV(Frames.Frame):
    "Private frame"
    _framespec = (NullTerminatedStringSpec("owner"),
                  BinaryDataSpec("data"))
    _allow_duplicates = True

class SIGN(Frames.Frame):
    "Signature frame"
    _framespec = (ByteSpec("group"),
                  BinaryDataSpec("data"))
    _allow_duplicates = True
    _untested = True
    _bozo = True
    _version = 4

class SEEK(Frames.Frame):
    "Seek frame"
    _framespec = (IntegerSpec("offset", 4), )
    _untested = True
    _bozo = True
    _version = 4

class ASPI(Frames.Frame):
    "Audio seek point index"
    _framespec = (IntegerSpec("S", 4),
                  IntegerSpec("L", 4),
                  IntegerSpec("N", 2),
                  ByteSpec("b"),
                  ASPISpec("Fi"))
    _version = 4
    _untested = True
    _bozo = True


# ID3v2.3

class TYER(Frames.TextFrame):
    """Year
    A numerical string with the year of the recording.
    Replaced by TDRC in id3v2.4
    """
    _version = 3
    
class TDAT(Frames.TextFrame):
    """Date
    A numerical string in DDMM format containing the date for the recording.
    Replaced by TDRC in id3v2.4
    """
    _version = 3

class TIME(Frames.TextFrame):
    """Time
    A numerical string in HHMM format containing the time for the recording.
    Replaced by TDRC in id3v2.4
    """
    _version = 3

class TORY(Frames.TextFrame):
    """Original release year
    Replaced by TDOR in id3v2.4
    """
    _version = 3

class TRDA(Frames.TextFrame):
    """Recording dates
    Replaced by TDRC in id3v2.4
    """
    _version = 3

class TSIZ(Frames.TextFrame):
    """Size
    Size of the audio file in bytes, excluding the ID3v2 tag.
    Removed in id3v2.4
    """
    _version = 3

class IPLS(Frames.CreditsFrame):
    """Involved people list
    Replaced by TMCL and TIPL in id3v2.4
    """
    _framespec = (BinaryDataSpec("data"),)
    _untested = True
    _bozo = True
    _version = 3

class EQUA(Frames.Frame):
    """Equalisation
    Replaced by EQU2 in id3v2.4
    """
    _framespec = (ByteSpec("bits"), BinaryDataSpec("data"))
    _untested = True
    _bozo = True
    _version = 3

class RVAD(Frames.Frame):
    """Relative volume adjustment
    Replaced by RVA2 in id3v2.4
    """
    _framespec = (BinaryDataSpec("data"),)
    _untested = True
    _bozo = True
    _version = 3

# ID3v2.2

class UFI(UFID): pass
class TT1(TIT1): pass
class TT2(TIT2): pass
class TT3(TIT3): pass
class TP1(TPE1): pass
class TP2(TPE2): pass
class TP3(TPE3): pass
class TP4(TPE4): pass
class TCM(TCOM): pass
class TXT(TEXT): pass
class TLA(TLAN): pass
class TCO(TCON): pass
class TAL(TALB): pass
class TPA(TPOS): pass
class TRK(TRCK): pass
class TRC(TSRC): pass
class TYE(TYER): pass
class TDA(TDAT): pass
class TIM(TIME): pass
class TRD(TRDA): pass
class TMT(TMED): pass
class TFT(TFLT): pass
class TBP(TBPM): pass
class TCR(TCOP): pass
class TPB(TPUB): pass
class TEN(TENC): pass
class TSS(TSSE): pass
class TOF(TOFN): pass
class TLE(TLEN): pass
class TSI(TSIZ): pass
class TDY(TDLY): pass
class TKE(TKEY): pass
class TOT(TOAL): pass
class TOA(TOPE): pass
class TOL(TOLY): pass
class TOR(TORY): pass

class TXX(TXXX): pass

class WAF(WOAF): pass
class WAR(WOAR): pass
class WAS(WOAS): pass
class WCM(WCOM): pass
class WCP(WCOP): pass
class WPB(WPUB): pass

class WXX(WXXX): pass

class IPL(IPLS): pass

class MCI(MCDI): pass
class ETC(ETCO): pass
class MLL(MLLT): pass
class STC(SYTC): pass
class ULT(USLT): pass
class SLT(SYLT): pass

class COM(COMM): pass

class RVA(RVAD): pass
class EQU(EQUA): pass
class REV(RVRB): pass

class PIC(Frames.Frame):
    "Attached picture"
    _framespec = (EncodingSpec("encoding"),
                  SimpleStringSpec("format", 3),
                  ByteSpec("type"),
                  EncodedStringSpec("desc"),
                  BinaryDataSpec("data"))
    _allow_duplicates = True
    _version = 2

    def _to_version(self, version):
        if version == 2:
            return self
        assert version in (3, 4)
        if self.format.upper() == "PNG":
            mime = "image/png"
        elif self.format.upper() == "JPG":
            mime = "image/jpeg"
        else:
            mime = imghdr.what(io.StringIO(self.data))
            if mime == None:
                raise ValueError("Unknown image format")
            mime = "image/" + mime.lower()
        return APIC(mime=mime, type=self.type, desc=self.desc, data=self.data)
        
    def _str_fields(self):
        img = "{0} bytes of {1} data".format(len(self.data), 
                                               imghdr.what(None, self.data[:32]))
        return "{0}({1}), desc={2}, format={3}: {4}".format(self.type,
                                                          picture_types[self.type],
                                                          repr(self.desc),
                                                repr(self.format),
                                                img)


class GEO(GEOB): pass
class CNT(PCNT): pass
class POP(POPM): pass

class BUF(RBUF): pass
class CRM(Frames.Frame):
    "Encrypted meta frame"
    _framespec = (NullTerminatedStringSpec("owner"),
                  NullTerminatedStringSpec("content"),
                  BinaryDataSpec("data"))
    _bozo = True
    _untested = True
    _version = 2

class CRA(AENC): pass

class LNK(Frames.Frame):
    "Linked information"
    _framespec = (SimpleStringSpec("frameid", 3),
                  NullTerminatedStringSpec("url"),
                  BinaryDataSpec("data"))
    _bozo = True
    _untested = True
    _version = 2

# Nonstandard frames
class TCMP(Frames.TextFrame): 
    "iTunes: Part of a compilation"
    _nonstandard = True

class TCP(TCMP): pass

class TDES(Frames.TextFrame): 
    "iTunes: Podcast description"
    _nonstandard = True
class TDS(TDES): pass

class TGID(Frames.TextFrame): 
    "iTunes: Podcast identifier"
    _nonstandard = True
class TID(TGID): pass

class TDRL(Frames.TextFrame): 
    "iTunes: Podcast release date"
    _nonstandard = True
class TDR(TGID): pass

class WFED(Frames.URLFrame): 
    "iTunes: Podcast feed URL"
    _nonstandard = True
class WFD(WFED): pass

class TCAT(Frames.TextFrame): 
    "iTunes: Podcast category"
    _nonstandard = True
class TCT(TCAT): pass

class TKWD(Frames.TextFrame): 
    """iTunes: Podcast keywords
    Comma-separated list of keywords.
    """
    _nonstandard = True
class TKW(TKWD): pass

class PCST(Frames.Frame):
    """iTunes: Podcast flag.

    If this frame is present, iTunes considers the file to be a podcast.
    Value should be zero.
    """
    _framespec = (IntegerSpec("value", 4),)
    _nonstandard = True
class PCS(PCST): pass


def _register_frames(module=None):
    """Supply missing version fields and register v2.2 names 
    of v2.3 & v2.4 frames based on class inheritance.
    """
    for obj in globals().values():
        if Frames.is_frame_class(obj):
            if len(obj.__name__) == 3:
                obj._version = 2
            if len(obj.__name__) == 4 and not obj._version:
                obj._version = (3, 4)
            if obj._in_version(2):
                base = obj.__bases__[0]
                if issubclass(base, Frames.Frame) and base._in_version(3, 4):
                    assert not hasattr(base, "_v2_frame")
                    base._v2_frame = obj

_register_frames()


# Attached picture (APIC & PIC) types
picture_types = (
    "Other", "32x32 icon", "Other icon", "Front Cover", "Back Cover",
    "Leaflet", "Media", "Lead artist", "Artist", "Conductor",
    "Band/Orchestra", "Composer", "Lyricist/text writer",
    "Recording Location", "Recording", "Performance", "Screen capture",
    "A bright coloured fish", "Illustration", "Band/artist",
    "Publisher/Studio")

# ID3v1 genre list
genres = (
    "Blues", "Classic Rock", "Country", "Dance", "Disco", "Funk", "Grunge",
    "Hip-Hop", "Jazz", "Metal", "New Age", "Oldies", "Other", "Pop", "R&B",
    "Rap", "Reggae", "Rock", "Techno", "Industrial", "Alternative", "Ska",
    "Death Metal", "Pranks", "Soundtrack", "Euro-Techno", "Ambient",
    "Trip-Hop", "Vocal", "Jazz+Funk", "Fusion", "Trance", "Classical",
    "Instrumental", "Acid", "House", "Game", "Sound Clip","Gospel", "Noise",
    "AlternRock", "Bass", "Soul", "Punk", "Space", "Meditative",
    "Instrumental Pop", "Instrumental Rock", "Ethnic", "Gothic", "Darkwave",
    "Techno-Industrial", "Electronic", "Pop-Folk", "Eurodance", "Dream",
    "Southern Rock", "Comedy", "Cult", "Gangsta", "Top 40", "Christian Rap",
    "Pop/Funk", "Jungle", "Native American", "Cabaret", "New Wave",
    "Psychadelic", "Rave", "Showtunes", "Trailer", "Lo-Fi", "Tribal",
    "Acid Punk", "Acid Jazz", "Polka", "Retro", "Musical", "Rock & Roll",
    "Hard Rock",
    # 80-125: Winamp extensions
    "Folk", "Folk-Rock", "National Folk", "Swing", "Fast Fusion", "Bebob",
    "Latin", "Revival", "Celtic", "Bluegrass", "Avantgarde", "Gothic Rock",
    "Progressive Rock", "Psychedelic Rock", "Symphonic Rock", "Slow Rock",
    "Big Band", "Chorus", "Easy Listening", "Acoustic", "Humour", "Speech",
    "Chanson", "Opera", "Chamber Music", "Sonata", "Symphony", "Booty Bass",
    "Primus", "Porn Groove", "Satire", "Slow Jam", "Club", "Tango", "Samba",
    "Folklore", "Ballad", "Power Ballad", "Rhythmic Soul", "Freestyle",
    "Duet", "Punk Rock", "Drum Solo", "A capella", "Euro-House",
    "Dance Hall",
    # 126-147: Even more esoteric Winamp extensions
    "Goa", "Drum & Bass", "Club House", "Hardcore", "Terror", "Indie",
    "BritPop", "Negerpunk", "Polsk Punk", "Beat", "Christian Gangsta Rap",
    "Heavy Metal", "Black Metal", "Crossover", "Contemporary Christian",
    "Christian Rock", "Merengue", "Salsa", "Thrash Metal", "Anime", "JPop",
    "Synthpop")


__all__ = [ obj.__name__ for obj in globals().values() 
            if Frames.is_frame_class(obj)]
