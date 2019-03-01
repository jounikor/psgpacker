#
# (c) 2018-19 by Jouni 'Mr.Spiv' Korhonen
# version 0.6
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

    def read(self):
        return self.iptr


#
#
#
#

class PSGCompressor(object):
    NUMREGS = 14
    LUTSIZE = 48
    
    def __init__(self, io):
        self.io = io
        self.regList = []
        self.history = {}
        self.numSync = 0
        self.numPrevSync = 0
        self.lut = [-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
                    -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
                    -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
                    -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1
                    ]
        self.lutIndex = 0
        self.regBuffer = bytearray(14)

        for n in xrange(14):
            self.regBuffer[n] = 0

    #
    # Parse a PSG1 style file with 16 octet header..
    #

    def parseHeader(self):
        tag = b"PSG\x1a"
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
    # Parse a PSG frame..
    #

    def parseFrames(self):
        self.regList = []
        self.numSync = self.numPrevSync
        self.numPrevSync = 0

        if (args.debug):
            sys.stderr.write("Parsing at {:5x}\n".format(self.io.read()))

        while (True):
            t = self.io.getb()

            if (t == -1):
                return False

            if (t == 0xff):
                # found empty frame..
                self.numSync += 1
                continue

            if (t == 0xfe):
                # found several empty frames..
                v = self.io.getb()
                
                if (v == -1):
                    raise RuntimeError("Premature end of file #1")
               
                self.numSync = self.numSync +  4 * v
                continue
            
            if (t == 0xfd):
                # end of file..
                return False
            
            # it was a register write..

            while (True):
                if (t >= 16 and t < 252):
                    raise NotImplementedError("Outing to MSX devices")
                
                # Read register index + value or possible end mark
                
                v = self.io.getb()
            
                if (v == -1):
                    raise RuntimeError("Premature end of file #2")
                
                self.regList.append( (t,v) )
                t = self.io.getb()
                 
                if (t == -1):
                    return False

                if (t == 0xff):
                    self.numPrevSync = 1
                    return True

                if (t == 0xfe):
                    t = self.io.getb()

                    if (t == -1):
                        raise RuntimeError("Premature end of file #3")
                    
                    if (t == 0):
                        raise RuntimeError("Multiple end of frames is zero")
                    
                    self.numPrevSync = t * 4
                    return True

    #
    # Calculate "used registers" bitmap and also update the
    # internal PSG register buffer only with values that
    # change the buffer state.
    # Also store the last change register index for "oneput" use.
    #

    def update(self):
        self.used = 0
        self.only = -1

        for reg,val in self.regList:
            if (self.regBuffer[reg] != val):
                self.used = self.used | (1 << (self.NUMREGS - 1 - reg))
                self.regBuffer[reg] = val
                self.only = reg

        return self.used

    #
    # Output "end of interrupt" marks i.e. frame waits.
    # In a case of "last frame" possible tailing waits
    # from the parser are also included into outputted
    # frame waits.
    #

    def outputSyncTokens(self,lastFrame):
        numSync = self.numSync

        if (lastFrame):
            numSync += self.numPrevSync

        if (numSync > 0):
            numSync -= 1

            while (numSync > 63):
                self.io.putb(0b00111111)
                if (args.debug):
                    sys.stderr.write("  wait: 00 111111\n")
                
                numSync -= 63
            
            if (numSync > 0):
                self.io.putb(0b00000000 | (numSync))
            
                if (args.debug):
                    sys.stderr.write("  wait: 00 {:06b}\n".format(numSync))
    
    #
    # Output PSG data in compressed form.
    #

    def outputFrames(self):
        used = self.used

        # output 0 or 1 reglists
        if (used == 0):
            return False

        if (used & (used - 1) == 0):
            # only 1 bit set here..
          
            n = self.only
            m = self.regBuffer[n]

            if (args.lut):
                n = self.checkLUT(n,m)
        
            self.io.putb(0b01000000 | n)
           
            if (n < 16):
                self.io.putb(m)
                s = "oneput: 01 00{:04b} {:02x}".format(self.io.len(),n,m)
            else:
                s = "lutput: 01 {:06b} -> {:02x}".format(self.io.len(),n,m)
        
            if (args.debug):
                ss = "{:5d} - {:s} : {:d},{:d}\n".format(self.io.len(),s,\
                        self.numSync,self.numPrevSync)
                sys.stderr.write(ss)
            
            return True
        
        # .. 

        dis = -1

        # condense a key for lookups
        key = ""

        for n in xrange(self.NUMREGS):
            if (used & (1 << (self.NUMREGS - 1- n))):
                key += chr(n)
                key += chr(self.regBuffer[n])

        if (args.lz):
            dis = self.checkHistory(key)

        if (dis >= 0):
            regs = chr(0b10000000 | (dis >> 8))
            regs += chr(dis & 0xff)
            s = "lz: 10 {:06b}{:08b} -> {:d}".format(dis>>8,dis&0xff,dis-2)
        else:
            s = "regput: 11 {:014b} ".format(used)
            regs  = chr(0b11000000 | (used >> 8))
            regs += chr(used & 0xff)
        
            for n in xrange(1,key.__len__(),2):
                regs += key[n]
                s += "{:02x} ".format(ord(key[n]))

        for n in regs:
            self.io.putb(ord(n))

        #
        if (args.debug):
            ss = "{:5d} - {:s} : {:d},{:d}\n".format(self.io.len(),s,\
                    self.numSync,self.numPrevSync)
            sys.stderr.write(ss)
        
        return True

    #
    # Check it the register data is available in the LUT
    # buffer.. also update the buffer in a FIFO manner if
    # the regoster value was not found.
    # 3 LUT positions are maintained for each register.
    #
    
    def checkLUT(self,n,r):
        if (r == self.lut[n+16]):
            return n+16
        if (r == self.lut[n+32]):
            return n+32
        if (r == self.lut[n+48]):
            return n+48

        self.lut[n+16] = self.lut[n+32]
        self.lut[n+32] = self.lut[n+48]
        self.lut[n+48] = r
        return n

    #
    # Check if the regiter+value array has already been
    # seen in past. The history is maintained for past
    # 16382 locations in the file. 2 byte adjustment is
    # done in the distance from the current location to the
    # history to speed up the decompression routine.
    #

    def checkHistory(self,key):
        if (self.history.has_key(key)):
            pos = self.history[key]
        else:
            pos = -1

        if (pos == -1):
            self.history[key] = self.io.len()
            return -1

        # +2 compensates increment of 2 in the depacker..
        dis = self.io.len() - pos  + 2
        
        if (dis >= 2**14):
            self.history[key] = self.io.len()
            dis = -1

        return dis
        
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
prs.add_argument("--lut",dest="lut",action="store_true",default=False,help="enable rotating "
    "lookup tables")
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

        while (cont):
            cont = psg.parseFrames()
            used = psg.update()

            #
            if (cont and used == 0x0000):
                raise RuntimeError( "Spurious empty frame - check the PSG file")

            psg.outputSyncTokens(False)
            psg.outputFrames()

        #

        psg.outputSyncTokens(True)
        psg.outputEOF()

#
#
# 00 000000               -> EOF
# 00 nnnnnn               -> wait sync & repeat previour line nnnnnn times
# 01 00nnnn               -> register nnnn followed by 1 times [8]
# 01 rrnnnn               -> if rr > 0 then take register from LUT[rrnnnn]
# 10 nnnnnn nnnnnnnn      -> point at 2^14-1 bytes in history for a TAG "11 nnnnnn nnnnnnnn"
# 11 nnnnnn nnnnnnnn      -> regs 0 to 13 followed by 1 to 14 times [8]
#

