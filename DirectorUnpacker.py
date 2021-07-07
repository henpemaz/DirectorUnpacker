
import os
import subprocess
import struct
from chunk import Chunk
from io import BytesIO

#from PIL import Image

outfolder = ".\\out\\"
#convert = "./ImageMagick-7.0.8-32-portable-Q16-x64/convert.exe"

#filename = "D:/Henpemaz/Software/RWEditor2 - Copy/runnMazeLevelEditor22.dir"
filename = "E:/Henpemaz/Software/RWEditor2 - Copy/runnMazeLevelEditor22.dir"
filesize = os.path.getsize(filename)
file = open(filename, "rb")
contents = file.read()
file.close()
file = BytesIO(contents)
bigendian = contents[0:4] == "RIFX"
align = True
inclheader = False

class BetterChunk(Chunk):
    bigendian = bigendian
    align = align
    inclheader = inclheader
    def __init__(self, file, offset=-1):
        if offset != -1:
            file.seek(offset)
        super().__init__(file, align=BetterChunk.align, bigendian=BetterChunk.bigendian, inclheader=BetterChunk.inclheader)
        self.endianness = BetterChunk.bigendian
        if not self.endianness:
            self.chunkname = self.chunkname[::-1]
    def readInt(self):
        return struct.unpack_from(">L" if self.endianness else "<L",self.read(4))[0];
    def readShort(self):
        return struct.unpack_from(">H" if self.endianness else "<H",self.read(2))[0];
    def readByte(self):
        return struct.unpack_from(">B" if self.endianness else "<B",self.read(1))[0];
    def readFourCC(self):
        value = self.read(4).decode()
        return value if self.endianness else value[::-1]
    def dump(self):
        self.seek(0)
        return self.read()
    def __repr__(self):
        return f"Chunk {self.chunkname} at {self.offset} long {self.chunksize}"

class DirectorMovie(BetterChunk):
    def __init__(self, file, offset=-1):
        super().__init__(file, offset=offset)
        self.codec = self.readFourCC()
        print("Movie got codec " + self.codec)
        self.imap = IMAP(file)
        print("Got imap")
        print("mmap count is " + self.imap.mapcount.__str__())
        print("mmap offset is " + self.imap.mapoffset.__str__())
        self.file.seek(self.imap.mapoffset)
        print("at map pos reads " + self.readFourCC())
        self.mmap = MMAP(file, self.imap.mapoffset)
        self.keys = KEYS(file, self.mmap.getFirstEntry("KEY*").offset)
        self.conf = CONF(file, self.mmap.entries[self.keys.FindAllOfType(1024, "DRCF")[0].ownedid].offset)
        self.mcsl = MCSL(file, self.mmap.entries[self.keys.FindAllOfType(1024, "MCsL")[0].ownedid].offset)
        self.castmps = {}
        self.castscriptmanagers = {}
        for c in self.mcsl.castlist:
            entries = self.keys.FindAllOfType(c.castid, "CAS*")
            if len(entries) != 0:
                print("found castlist entry for cast " + c.name)
                self.castmps[c.castid] = CastMemberPointers(file, self.mmap.entries[entries[0].ownedid].offset, c)
            else:
                print("no castlist entry for cast " + c.name)

            entries = self.keys.FindAllOfType(c.castid, "LctX")
            if len(entries) != 0:
                print("found scriptmanager entry for cast " + c.name)
                self.castscriptmanagers[c.castid] = CastScriptManager(file, self.mmap.entries[entries[0].ownedid].offset, c)
            else:
                print("no scriptmanager entry for cast " + c.name)


class IMAP(BetterChunk):
    def __init__(self, file:DirectorMovie, offset=-1):
        super().__init__(file, offset=offset)
        self.mapcount = self.readInt()
        self.mapoffset = self.readInt()
    def __repr__(self):
        return f"IMAP count {self.mapcount} offset {self.mapoffset}; " + super().__repr__()

class MMAP(BetterChunk):
    def __init__(self, file:DirectorMovie, offset=-1):
        super().__init__(file, offset=offset)
        self.headerLength = self.readShort()
        self.entryLength = self.readShort()
        self.chunkCountMax = self.readInt()
        self.chunkCountUsed = self.readInt()
        self.junkHead = self.readInt()
        self.junkHead2 = self.readInt()
        self.freeHead = self.readInt()
        self.entries = []
        for i in range(self.chunkCountUsed):
            self.entries.append(MMAPEntry(self, i))
            #if(self.entries[-1].code != "free"):
            #    print(self.entries[-1])

    def getFirstEntry(self, code:str):
        for entry in self.entries:
            if entry.code == code:
                return entry
        return null

    def __repr__(self):
        return f"MMAP used {self.chunkCountUsed} max {self.chunkCountMax}; " + super().__repr__()

class MMAPEntry:
    def __init__(self, mmap:MMAP, i:int):
        self.index = i
        self.code = mmap.readFourCC()
        self.length = mmap.readInt()
        self.offset = mmap.readInt()
        self.flags = mmap.readShort()
        self.unknown = mmap.readShort()
        self.next = mmap.readInt()
    def __repr__(self):
        return f"index:{self.index};code:{self.code};length:{self.length};offset:{self.offset};flags:{self.flags};next:{self.next};"

class KEYS(BetterChunk):
    def __init__(self, file, offset=-1):
        super().__init__(file, offset=offset)
        self.unknown0 = self.readInt();
        self.keycount = self.readInt();
        self.unknown1 = self.readInt();
        self.entries = []
        for i in range(self.keycount):
            self.entries.append(KEYEntry(self,i))
    def __repr__(self):
        return f"KEYS count {self.keycount}; " + super().__repr__()

    def FindAllOwned(self, owner:int):
        return [f for f in self.entries if f.ownerid == owner]
    def FindAllOfType(self, owner:int, typecode:str):
        return [f for f in self.entries if f.ownerid == owner and f.typecode == typecode]

class KEYEntry:
    def __init__(self, keys:KEYS, i:int):
        self.index = i
        self.ownedid = keys.readInt()
        self.ownerid = keys.readInt()
        self.typecode = keys.readFourCC()
    def __repr__(self):
        return f"index:{self.index};ownedid:{self.ownedid};ownerid:{self.ownerid};typecode:{self.typecode};"

class CONF(BetterChunk):
    def __init__(self, file, offset=-1):
        super().__init__(file, offset=offset)
        self.endianness = True ## only god knows why
        self.conflength = self.readShort()
        self.fileversion = self.readShort()
        self.movietop = self.readShort()
        self.movieleft = self.readShort()
        self.moviebottom = self.readShort()
        self.movieright = self.readShort()
        self.minmember = self.readShort()
        self.maxmember = self.readShort()
        self.seek(36) ## skip some 
        self.directorversion = self.readShort()

class MCSL(BetterChunk):
    def __init__(self, file, offset=-1):
        super().__init__(file, offset=offset)
        self.endianness = True ## only god knows why
        self.dataoffset = self.readInt()# should be use to find offsettable but its at a fixed position anyways
        self.unknown0 = self.readShort()
        self.castcount = self.readShort()
        self.itemspercast = self.readShort()
        self.unknown1 = self.readShort()
        # should seek dataoffset here but its already at the right spot
        self.offsettablelen = self.readShort()
        self.offsettable = []
        for i in range(self.offsettablelen):
            self.offsettable.append(self.readInt())
        self.datalen = self.readInt()
        self.offsettable.append(self.datalen)# "max offset" of the sorts for checking n+1 offset
        self.startofdata = self.tell()
        self.endianness = BetterChunk.bigendian
        self.castlist = []
        for i in range(self.castcount):
            self.castlist.append(CastListEntry(self, i, self.itemspercast))

    def seekTable(self, index:int):
        self.seek(self.startofdata + self.offsettable[index])
    def tableString(self, index:int):
        if self.offsettable[index+1] == self.offsettable[index]:
            return ""
        self.seekTable(index)
        l = self.readByte()
        return self.read(l).decode()

class CastListEntry:
    def __init__(self, mcsl:MCSL, i:int, ipc:int):
        self.index = i
        self.name = mcsl.tableString(ipc*i+1)
        self.filepath  = mcsl.tableString(ipc*i+2)
        mcsl.seekTable(ipc*i+3)
        self.preloadsettings = mcsl.readShort()
        mcsl.seekTable(ipc*i+4)
        self.minmember = mcsl.readShort()
        self.maxmember = mcsl.readShort()
        self.castid = mcsl.readInt()

    def __repr__(self):
        return f"index:{self.index};name:{self.name};castid:{self.castid};"

class CastMemberPointers(BetterChunk):
    def __init__(self, file, offset, c:CastListEntry):
        super().__init__(file, offset=offset)
        self.endianness = True
        self.members = {}
        for i in range(c.minmember, c.minmember + self.chunksize//4):
            self.members[i] = self.readInt()

class CastScriptManager(BetterChunk):
    def __init__(self, file, offset, c:CastListEntry):
        super().__init__(file, offset=offset)
        self.endianness = True
        self.skip(8)
        self.entrycount = self.readInt()
        self.entrycount2 = self.readInt()
        self.entriesoffset = self.readShort()
        self.skip(14)
        self.lnamsection = self.readInt()
        self.validcount = self.readShort()
        self.flags = self.readShort()
        self.freepointer = self.readShort()
        self.seek(self.entriesoffset)
        self.sectionmap = []
        for i in range(self.entrycount):
            self.sectionmap.append(ScriptContextEntry(self, i))
        self.lnam = 

class ScriptContextEntry:
    def __init__(self, mngr:CastScriptManager, i:int):
        self.index = i
        self.unk0 = keys.readInt()
        self.sectorid = keys.readInt()
        self.unk1 = keys.readInt()

#form = Chunk(BytesIO(contents[form_i:]), bigendian=False)
#file.seek(form_i)
form = DirectorMovie(file)
form_size = form.getsize()
print("name:", form.getname())
print("size:", form_size)
print("filesize:", filesize)
