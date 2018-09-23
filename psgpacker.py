#
# (c) 2018 by Jouni 'Mr.Spiv' Korhonen
# version 0.2
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
    """PSGio(input, output) -> PSGio object
    
    Creates an IO object that has both input and output methods defines.
    The input can be an existing file object, a name to a file, or a
    bytearray object. The same applies also for output methods.
    
    If an existing file object is used for the input, it should have been
    opened using mode 'rb'. If an existing file object is used for the
    output, it should have been opened using mode 'wb'. The file objects
    can also be sys.stdin or sys.stdout.

    If a file name is used for either inout or output, the PSGio object
    will open the appropriate file and also take care of closing the
    opened file objects.

    If a bytearray object is used then the PSGio object assumes the input
    and ouput earrays are appropriately set up.

    Methods generated runtime:

    getb(...)
        x.getb() -> str. Read annd returns a str on length 1.

        Read a byte from an input source defined during the
        instantiation of the PSGio object. The method is overloaded
        accordingly during the initialization.

        Args:
            None.

        Returns:
            A value in range(0,255) and -1 if EOF.

        Raises:
            May raise IOError.

    putb(...)
        x.putb(value) -> None.
  
        Write a byte into an output destination defined during the
        instantiation of the PSGio object. The method is overloaded
        accordingly during the initialization.
    
        Args:
            value (int): A value in range(0,255).

        Returns:
            None.

        Raises:
            IOError exception when a write fails or goes beyond
            the bytearray bounds.

            ValueError exception if the value is not in range(0,255).
    """

    def __enter__(self):
        """x.__enter__() -> self

        Support for x using 'with' statement.
        """
        return self

    def __exit__(self,exc_type, exc_val, exc_tb):
        """x.__exit__(exc_type,exc_val,exc_tb) -> None.  
        
        Closes possible files objects opened by the PSGio object
        itself for input and/or output purposes.
        
        Args:
            exc_type
            exc_val
            exc_tb

        Returns:
            None.

        Raises:
            None.
        
        """

        if (self.ifile):
            self.ihndl.close()
        if (self.ofile):
            self.ohndl.close()

    def __init__(self, inp, oup):
        """x.__init__(input,output) -> None.
        
        Initialized x; input and/or output is a file object, a file
        name or a bytearray.

        Args:
            input (file, str or bytearray): A reference to a mode 'rb' opened
                file object, filename to open or a bytearray object containing
                the data to read,
            output (file, str or bytearray): A reference to a mode 'wb' opened
                file object, a filename to create or a bytearray object with
                enough space to hold the output file.

        Returns:
            None.

        Raises:
            None.
        """
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
        """x.close() -> None.

        Closes possible files objects opened by the PSGio object
        itself for input and/or output purposes.
        """
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


    # return outputted bytes
    def len(self):
        return self.optr

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
        self.history = {}
        self.numSync = 0

        for n in xrange(PSGCompressor.NUMREGS):
            self.regState[n] = 0

    def parseHeader(self):
        tag = b"PSG\x1a"
        #hdr = bytearray([self.io.getb() for n in xrange(16)])
        #
        #if (hdr.__len__() != 16):
        #    raise IOError("File length too small.")
        
        hdr = bytearray(16)

        for n in xrange(16):
            b = self.io.getb()
            if (b < 0):
                raise IOError("Premature end of file")
            else:
                hdr[n] = b

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
            while numSync > 63:
                self.io.putb(0b00111111)
                if (args.debug):
                    sys.stderr.write("  wait: 00 111111\n")
                
                numSync -= 63
            
            self.io.putb(0b00000000 | (numSync))
            if (args.debug):
                sys.stderr.write("  wait: 00 {:06b}\n".format(numSync))

    #
    #
    #
    def outputFrames(self):
        used = self.used
        numSync = self.numSync

        if (self.numSync == 0):
            raise AssertionError(self.numSync)
      
        if (used > 0):
            # If there are changes in the register list we need to subtract one
            # sync wait since the register update implicitly contains a sync
            # wait itself..
            numSync = numSync - 1

        self._outputSyncTokens(numSync)

        # output 0 or 1 reglists
        if (used == 0):
            return False

        if (used & (used - 1) == 0):
            # only 1 bit set here..
            n = 0
            while not (used & (1 << (self.NUMREGS - 1 - n))):
                n += 1
            
            self.io.putb(0b01000000 | n)
            self.io.putb(self.regState[n])
            
            s = "oneput: 01 00{:04b} {:02x}\n".format(n,self.regState[n])
        else:
            regs  = chr(0b11000000 | (used >> 8))
            regs += chr(used & 0xff)
            s = "{:5d} - regput: 11 {:014b} ".format(self.io.len(),used) 
       
            for n in xrange(self.NUMREGS):
                if (used & (1 << (self.NUMREGS - 1 - n))):
                    regs += chr(self.regState[n])
                    s += "{:02x} ".format(self.regState[n])
            else:
                s += "\n"
       
            if (args.lz):
                regs,s = self.checkHistory(regs,s)

            for n in regs:
                self.io.putb(ord(n))

        #
        #

        if (args.debug):
            sys.stderr.write(s)
        
        return True

    #
    #
    #

    def checkHistory(self,regs,s):
        if (regs.__len__() < 3):
            return regs,s
      
        if (self.history.has_key(regs)):
            pos = self.history[regs]
        else:
            pos = -1

        if (pos == -1):
            self.history[regs] = self.io.len()
            return regs,s

        dis = self.io.len() - pos + 2
        # +2 compensates increment of 2 in the depacker..
        
        if (dis < 2**14):
            regs  = chr(0b10000000 | (dis >> 8))
            regs += chr(dis & 0xff)
            s = "{:5d} - lz: 10 {:014b} ({})\n".format(self.io.len(),dis,dis-2)
        else:
            self.history[regs] = self.io.len()

        return regs,s
        
    #
    #
    #
    def outputEOF(self):
        if (args.debug):
            sys.stderr.write("output: 00 000000\n")
        
        self.io.putb(0x00)

#
#
#
#

prs = argparse.ArgumentParser()
prs.add_argument("input_file",metavar="input_file",type=str,help="PSG file or '' if stdin")
prs.add_argument("output_file",metavar="output_file",type=str,nargs="?",help="Output file or stdout "
                 "if missing", default=sys.stdout)
prs.add_argument("--debug",dest="debug",action="store_true",default=False,help="show debug output")
prs.add_argument("--lz",dest="lz",action="store_true",default=False,help="enable history references")
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
                sys.stderr.write("{}\n".format(hdr.tag))
        else:
            sys.stderr.write("not a PSG file\n")
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
                    sys.stderr.write("{} {} {}\n".format(o,w,psg.pendingFrameSync))

            psg.outputFrames()

        #

        psg.outputFrames()
        psg.outputEOF()

#
#
# 00 000000               -> EOF
# 00 nnnnnn               -> wait sync & repeat previour line nnnnnn times
# 01 00nnnn               -> register nnnn followed by 1 times [8]
# 10 nnnnnn nnnnnnnn      -> point at 2^14-1 bytes in history for a TAG "11 nnnnnn nnnnnnnn"
# 11 nnnnnn nnnnnnnn      -> regs 0 to 13 followed by 1 to 14 times [8]
#

