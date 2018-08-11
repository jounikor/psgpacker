#
# (c) 2018 by Jouni 'Mr.Spiv' Korhonen
# version 0.1
#
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org/>
#

import sys
import argparse

#
#
#
#

class PSGHeader(object):
    def __init__(self, tag, ver, freq, resv):
        self.tag = tag
        self.version = ver
        self.reserved = resv

        if (ver >= 10):
            self.freq = freq
        else:
            self.freq = 0

#
#
#
#

class PSGFrame(object):
    def __init__(self, sync, regs):
        self.numSync = sync
        self.regList = regs

#
#
#
#

class PSGio(object):
    def __enter__(self):
        return self

    def __exit__(self,exc_type, exc_val, exc_tb):
        if (self.ifile):
            self.ihndl.close()
        if (self.ofile):
            self.ohndl.close()

    def __init__(self, inp, oup):
        self.ihndl = inp
        self.ohndl = oup
        self.iptr = 0
        self.optr = 0
        self.ifile = False
        self.ofile = False

        if (type(inp) == file):
            self.getb = self._file_getb
        elif (type(inp) == bytearray):
            self.getb = self._mem_getb
        elif (type(inp) == str):
            self.ihndl = open(inp,"rb")
            self.getb = self._file_getb
            self.ifile = True
        else:
            raise NotImplementedError("Input method")

        if (type(oup) == file):
            self.putb = self._file_putb
        elif (type(oup) == bytearray):
            self.putb = self._mem_putb
        elif (type(oup) == str):
            self.ohndl = open(oup,"wb")
            self.ofile = True
            self.putb = self._file_putb
        else:
            raise NotImplementedError("Output method")
    
    #
    #
    #
    def close(self):
       self.__exit__(None,None,None)


    # returns one int between 0-255, -1 if EOF, or raises IOError if error
    #def getb(self)

    # input one int between 0-255 and -1 if error
    #def putb(self,b)

    #
    #
    #
    def _file_getb(self):
        b = self.ihndl.read(1)

        if (b == ""):
            return -1
        else:
            self.iptr += 1
            return ord(b)

    def _file_putb(self,b):
        self.ohndl.write(chr(b))
        self.optr += 1

    def _mem_getb(self):
        if (self.iptr >= self.ihndl.__len__()):
            return -1
        
        b = self.ihndl[self.iptr]
        self.iprt += 1
        return b 
        
    def _mem_putb(self,b):
        if (self.optr >= self.ohndl.__len__()):
            raise IOError("Write past bytearray end")

        self.ohndl[self.optr] = b
        self.optr += 1


#
#
#
#

class PSGCompressor(object):
    NUMREGS = 14
    
    def __init__(self, io):
        self.io = io
        self.pendingFrameSync = 0
        self.regState = bytearray(PSGCompressor.NUMREGS)

        self.regList = []
        self.numSync = 0

        for n in xrange(PSGCompressor.NUMREGS):
            self.regState[n] = 0

    def parseHeader(self):
        tag = b"PSG\x1a"
        hdr = bytearray([self.io.getb() for n in xrange(16)])

        if (hdr.__len__() != 16):
            raise IOError("File length too small.")

        if (hdr[0:4] == tag[0:4]):
            return PSGHeader(tag,hdr[4],hdr[5],hdr[6:10])
        else:
            return None

    #
    #
    #
    def parseFrames(self):
        self.regList = []
        self.numSync = self.pendingFrameSync
        byteRead = False

        while True:
            if (byteRead is False):
                t = self.io.getb()

                if (t == -1):
                    return False
           
            if (t == 0xff):
                if (byteRead is True):
                    self.pendingFrameSync = 1
                    return True
                else:
                    self.numSync += 1
                    continue

            if (t == 0xfe):
                v = self.io.getb()
                
                if (v == -1):
                    return False
                
                if (byteRead is True):
                    self.pendingFrameSync = v
                    return True
                else:
                    self.numSync += v
                    continue
            
            if (t == 0xfd):
                    return False

            while (True):
                # Read register index + value or possible end mark
                v = self.io.getb()
            
                if (v == -1):
                    self.pendingFrameSync = 0
                    return False
                
                if (t >= 16 and t < 252):
                    raise NotImplementedError("Outing to MSX devices")
                else:
                    self.regList.append( (t,v) )

                t = self.io.getb()
                 
                if (t == -1):
                    return False

                if (t == 0xff or t == 0xfe):
                    byteRead = True
                    break

    #
    #
    #
    def update(self):
        self.used = 0

        for reg,val in self.regList:
            if (self.regState[reg] != val):
                self.used = self.used | (1 << (self.NUMREGS - 1 - reg))
                self.regState[reg] = val

        return self.numSync,self.used

    #
    #
    #
    def updateDeltaZero(self):
        self.pendingFrameSync += self.numSync

    #
    #
    #
    def _outputSyncTokens(self,numSync):
        # output 0 or more sync waits
        if (numSync > 0):
            while numSync > 64:
                self.io.putb(0b01111111)
                if (args.debug):
                    print "output: 01 111111"
                
                numSync -= 64
            
            self.io.putb(0b01000000 | (numSync-1))
            if (args.debug):
                print "output: 01 {:06b}".format(numSync-1)

    #
    #
    #
    def outputFrames(self):
        used = self.used
        numSync = self.numSync
        regs = self.regState

        if (self.numSync == 0):
            raise AssertionError(self.numSync)
      
        if (used > 0):
            # If there are changes in the register list we need to subtract ine
            # sync wait since the register update implicitly contains a sync
            # wait itself..
            numSync = numSync - 1

        self._outputSyncTokens(numSync)

        # output 0 or 1 reglists
        if (used == 0):
            return False

        # now output the register lists.. check for the pitch output..
        if (((used & 0b0011111100000000) ^ used) == 0):
            self.io.putb(used>>8)
            s = "output: 00 {:06b} ".format(used >> 8)
        elif (0):
            # can it be found from the history?
            # 10 00nnnn
            pass
        elif (used & (used - 1) == 0):
            # only 1 bit set here..
            n = 0
            while not (used & (1 << (self.NUMREGS - 1 - n))):
                n += 1
            
            self.io.putb(0b10010000 | n)
            s = "output: 10 01{:04b} ".format(n)
        else:
            self.io.putb(0b11000000 | (used >> 8))
            self.io.putb(used & 0xff)
            s = "output: 11 {:014b} ".format(used) 
       
        for n in xrange(self.NUMREGS):
            if (used & (1 << (self.NUMREGS - 1 - n))):
                self.io.putb(regs[n])
                s += "{:02x} ".format(regs[n])

        if (args.debug):
            print s
        
        return True

        
    #
    #
    #
    def outputEOF(self):
        if (args.debug):
            print "output: 00 000000"
        
        self.io.putb(0x00)


# 
# PSG compressed format:
#
# 
#  followed by reqister write value (1 octet) for each x=1
#  starting from r0 -> r14


#
#
#
#
#

prs = argparse.ArgumentParser()
prs.add_argument("input_file",metavar="input_file",type=str,help="PSG file or '' if stdin")
prs.add_argument("output_file",metavar="output_file",type=str,nargs="?",help="Output file or stdout "
                 "if missing", default=sys.stdout)
prs.add_argument("--debug","-d",dest="debug",action="store_true",default=False,help="show debug output")
args = prs.parse_args()

if __name__ == "__main__":
    if (args.input_file == ""):
        input_file = sys.stdin
    else:
        input_file = args.input_file

    with PSGio(input_file,args.output_file) as io:
        psg = PSGCompressor(io)

        hdr = psg.parseHeader()

        if (hdr is not None):
            if (args.debug):
                print hdr.tag
        else:
            print "not a PSG file"
            exit()

        cont = True

        while cont:
            cont = psg.parseFrames()
            w,u = psg.update()

            #
            if (u == 0x000):
                # if there is no change to the previous frame treat it as
                # another sync mark..
                psg.updateDeltaZero()
                continue

            o = "{:04x} ".format(u)
            for a in xrange(PSGCompressor.NUMREGS):
                o = o + "{:02x} ".format(psg.regState[a])
            else:
                if (args.debug):
                    print o, w,psg.pendingFrameSync

            psg.outputFrames()

        #

        psg.outputFrames()
        psg.outputEOF()

#
#
# 00 000000               -> EOF
# 00 nnnnnn               -> regs 0 to 5 followed by 1 to 6 times [8]
# 01 nnnnnn  -> wait sync & repeat previour line nnnnnn+1 times
# 10 00nnnn               -> previous delta line 1-15, 0 is current
# 10 01nnnn               -> register nnnn followed by 1 times [8]
# 10 10rrrr               -> reserved
# 10 11rrrr               -> reserved
# 11 nnnnnn nnnnnnnn      -> regs 0 to 13 followed by 1 to 14 times [8]
#
