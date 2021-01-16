#
# (c) 2018-21 by Jouni 'Mr.Spiv' Korhonen
# version 0.7
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
from io import BufferedWriter
from io import BufferedReader
from io import BytesIO

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
            input (sys.stdin.buffer, str or bytearray): A reference to a mode 'rb' opened
                file object, filename to open or a bytearray object containing
                the data to read,
            output (sys.stdout.buffer, str or bytearray): A reference to a mode 'wb' opened
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

        if (isinstance(inp,BufferedReader)):
            self.getb = self._file_getb
        elif (type(inp) == bytearray):
            self.getb = self._mem_getb
        elif (type(inp) == str):
            self.ihndl = open(inp,"rb")
            self.getb = self._file_getb
            self.ifile = True
        elif (inp is None):
            pass
        else:
            raise NotImplementedError("Input method")

        if (isinstance(oup,BufferedWriter)):
            self.putb = self._file_putb
        elif (type(oup) == bytearray):
            self.putb = self._mem_putb
        elif (type(oup) == str):
            self.ohndl = open(oup,"wb")
            self.ofile = True
            self.putb = self._file_putb
        elif (oup is None):
            pass
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

        if (b.__len__() == 0):
            return -1
        else:
            self.iptr += 1
            return ord(b)

    def _file_putb(self,b):
        self.ohndl.write(bytes([b,]))
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

class PSGToken(object):
    TAG_EOF        = 0
    TAG_SYNC       = 1
    TAG_ONEPUT     = 2
    TAG_BANKSWITCH = 3
    TAG_CACHED     = 4
    TAG_MULTILZ    = 5
    TAG_SINGLELZ   = 6
    TAG_MULTIPUT   = 7

    def __init__(self,tag,encoding,r15=-1):
        self.tag = tag
        
        # This must be a bytes type..
        self.encoding = encoding
        self.r15 = r15
        self.instances = 0
        self.cache_line = 0
        self.index = 0

    # Could use properties here but I won't.
    # This is just a simple container.


#
#
#
#

class PSGCompressor(object):
    NUMREGS = 14

    def __init__(self, io):
        self.io = io
        self.regList = []
        self.history = {}
        self.numSync = 0
        self.numPrevSync = 0
        self.regBuffer = bytearray(self.NUMREGS)
        self.tokens = []
        self.global_used = 0
        self.cached_tags = {}

        for n in range(self.NUMREGS):
            self.regBuffer[n] = 0

    #
    # Parse a PSG1 style file with 16 octet header..
    #

    def parseHeader(self):
        tag = b"PSG\x1a"
        hdr = bytearray(16)

        for n in range(16):
            b = self.io.getb()
            if (b < 0):
                raise IOError("Premature end of file")
            else:
                hdr[n] = b

        if (hdr[0:4] == tag[0:4]):
            return PSGHeader(tag,hdr[4],hdr[5],hdr[6:10])
        else:
            return None
            
            
            
    def get_output_size(self):
        len = 0

        for current_token in self.tokens:
            if (current_token is not None):
                len += current_token.encoding.__len__()

        return len

    #
    # Parse a PSG frame..
    #

    def PASS1_parseFrames(self):
        self.regList = []
        self.numSync += self.numPrevSync
        self.numPrevSync = 0

        if (args.debug):
            sys.stderr.write("Parsing at {:5x}, numSync: {:d}\n".\
                format(self.io.read(),self.numSync))

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

    def PASS1_update(self):
        self.used = 0
        self.only = -1
        cnt = 0

        for reg,val in self.regList:
            if (self.regBuffer[reg] != val):
                self.used = self.used | (1 << reg)
                self.regBuffer[reg] = val
                self.only = reg
                cnt += 1

        # Gather usage of AY registers over the entire PSG file
        self.global_used |= self.used

        return cnt

    #
    # Output "end of interrupt" marks i.e. frame waits.
    # In a case of "last frame" possible tailing waits
    # from the parser are also included into outputted
    # frame waits.
    #

    def PASS1_outputSyncTokens(self,lastFrame):
        numSync = self.numSync
        self.numSync = 0

        if (lastFrame):
            numSync += self.numPrevSync

        if (numSync > 0):
            numSync -= 1

            while (numSync > 63):
                self.tokens.append(PSGToken(PSGToken.TAG_SYNC,bytes([0b00111111,])))
                if (args.debug):
                    sys.stderr.write("TOKEN  wait: 00 111111\n")
                
                numSync -= 63
            
            if (numSync > 0):
                self.tokens.append(PSGToken(PSGToken.TAG_SYNC,bytes([0b00000000|numSync,])))

                if (args.debug):
                    sys.stderr.write("TOKEN  wait: 00 {:06b}\n".format(numSync))
    

    #
    # Output PSG data in compressed form.
    #

    def PASS1_outputFrames(self):
        used = self.used

        # output 0 or 1 reglists
        if (used == 0):
            return False

        # Check if there is only a single changed register and '--oneput' is enabled
        if (args.oneput and (used & (used - 1) == 0)):
            n = self.only
            m = self.regBuffer[n]

            self.tokens.append(PSGToken(PSGToken.TAG_ONEPUT,bytes([0b01000000|n,m]),self.regBuffer[13]))
            s = "oneput: 01 00{:04b} {:02x}".format(n,m)
        
            if (args.debug):
                ss = "TOKEN  {:s} : {:d},{:d}\n".format(s,\
                        self.numSync,self.numPrevSync)
                sys.stderr.write(ss)
           
            return True
        
        # Do we output all 14 registers or just the changed ones? 
        if (args.sparse is False):
            #used = 0b11111111111111
            used = self.global_used

        s = f"regput: 11 {used:014b} "
        # Note! bytes are swapped to help the ASM depacker
        regs  = bytes([0b11000000 | (used & 0x3f), used >> 6])
       
        for n in range(self.NUMREGS):
            if (used & 0x0001):
                regs += self.regBuffer[n].to_bytes(1,byteorder='big')

                s += f"{self.regBuffer[n]:02x} "

            used >>= 1

        self.tokens.append(PSGToken(PSGToken.TAG_MULTIPUT,regs,self.regBuffer[13]))

        #
        if (args.debug):
            ss = "TOKEN  {:s} : {:d},{:d}\n".format(s,\
                    self.numSync,self.numPrevSync)
            sys.stderr.write(ss)
        
        return True

    #
    #
    #
   
    def PASS2_build_cache(self):
        cache = {}

        for current_token in self.tokens:
            # We only cache multiple register writes i.e. TAG 11 llllll hhhhhhhh
            if (current_token.tag == PSGToken.TAG_MULTIPUT):
                if (current_token.encoding in cache):
                    cache[current_token.encoding].instances += 1
                else:
                    cache[current_token.encoding] = current_token

        # Get 15 best gaining reg write lines
        best_lines = sorted(cache.items(),key=lambda x:x[1].instances*x[0].__len__(),reverse=True)[:15]

        orig=pack=0
        unused_cache_line = 1

        if (args.debug):
            sys.stderr.write("PASS #2 found the following cached tags:\n")

        for n in range(best_lines.__len__()):
            cached_token_key,cached_token = best_lines[n]
            
            # Assign cache line from 1 to 15
            cached_token.cache_line = unused_cache_line
            unused_cache_line += 1

            if (args.debug):
                sys.stderr.write(f" Tag '{cached_token_key}' has length {cached_token.encoding.__len__()} "
                    f"and seen {cached_token.instances} times\n")
            
            orig += cached_token_key.__len__() * cached_token.instances
            pack += cached_token.instances
            self.cached_tags[cached_token_key] = cached_token

        if (args.debug):
            sys.stderr.write(f" PASS #2 original {orig} and packed {pack}\n")

    def PASS2_replace_with_cached(self):
        max_head = self.tokens.__len__()
        current_head = 0

        while (current_head < max_head):
            current_token = self.tokens[current_head]

            if (current_token.encoding in self.cached_tags):
                # TAG 01 010001 to 01 011111
                cache_line = self.cached_tags[current_token.encoding].cache_line 
                self.tokens[current_head] = PSGToken(PSGToken.TAG_CACHED,bytes([0b01010000|cache_line,]))

                if (args.debug):
                    sys.stderr.write(f"cache_line {cache_line:2d} replaces '{current_token.encoding}'\n")

            current_head += 1

    def PASS3_lz_null(self):
        # TODO..
        pass


    def PASS3_lz_multi(self):
        max_head = self.tokens.__len__()
        encoded_pos = 0
        current_head = 0

        while (current_head < max_head):
            current_token = self.tokens[current_head]
            current_token_length = current_token.encoding.__len__()
            match_count = 0
            match_offset = 65536
            skip_count = 1
            temp_match_length = 0

            if (current_token.encoding not in self.history):
                # add this new frame position if not ever seen before..
                self.history[current_token.encoding] = (encoded_pos,current_head)
            else:
                history_pos,history_head  = self.history[current_token.encoding]
                match_offset = encoded_pos - history_pos + 2
                
                if (match_offset > 65535):
                    # Past maximum offset.. initialize to this frame and advance to the next token
                    self.history[current_token.encoding] = (encoded_pos,current_head)
                else:
                    temp_current_head = current_head
                    temp_history_head = history_head

                    while (temp_current_head < max_head and match_count < 32):
                        if (self.tokens[temp_history_head].encoding.__len__() < 4):
                            break

                        # Do PSG frames match? 
                        if (self.tokens[temp_current_head].encoding != self.tokens[temp_history_head].encoding):
                            break

                        temp_match_length += self.tokens[temp_history_head].encoding.__len__()
                        temp_current_head += 1
                        temp_history_head += 1
                        match_count += 1

            # Did we find any matching frames?
            if (match_count == 1 and temp_match_length > 2 and match_offset < 16384):
                if (args.debug):
                    sys.stderr.write(f"single LZ match ({match_offset})\n")
                # Encode single short LZ
                match_offset |= 0b1000000000000000
                self.tokens[current_head].encoding = match_offset.to_bytes(2,byteorder='big')
                self.tokens[current_head].tag = PSGToken.TAG_SINGLELZ
                current_token_length = 2
            elif (temp_match_length > 3):
                if (args.debug):
                    sys.stderr.write(f"multipass LZ match ({match_offset},{match_count})\n")
                # Encode multipass LZA - Note.. match_offset is one too short here.
                # The offset must be adjusted in the player!
                skip_count = match_count
                match_count += 31
                match_count |= 0b01000000
                match_count = (match_count << 8) | (match_offset >> 8)
                match_count = (match_count << 8) | (match_offset & 0xff)
                # This breaks if match_count becomes "negative"..
                self.tokens[current_head].encoding = match_count.to_bytes(3,byteorder='big')
                self.tokens[current_head].tag = PSGToken.TAG_MULTILZ

                # And "None" skipped tokens..
                for to_none in range(current_head+1,temp_current_head):
                    self.tokens[to_none] = None

                current_token_length = 3

            # Advance to the next token..
            encoded_pos   += current_token_length
            current_head  += skip_count

    #
    # Greedy parsing of history data..
    #
    def PASS3_lz_single(self):
        encoded_pos = 0

        for current_head in range(self.tokens.__len__()):
            current_token = self.tokens[current_head]
            current_token_length = current_token.encoding.__len__()

            if (current_token.encoding not in self.history):
                self.history[current_token.encoding] = (encoded_pos,current_head)
            else:
                # There should not b more than 1 match anyway..
                history_pos,history_head = self.history[current_token.encoding]
                match_offset = encoded_pos - history_pos + 2
        
                # Make sure we only match against a regput tag..
                if (current_token_length > 2):
                    if (match_offset < 16384):
                        if (args.debug):
                            sys.stderr.write(f"LZ match ({match_offset},{current_token_length})\n")
                        
                        match_offset |= 0b1000000000000000
                        self.tokens[current_head].encoding = match_offset.to_bytes(2,byteorder='big')
                        self.tokens[current_head].tag = PSGToken.TAG_MULTILZ

                        # LZ tag is 2 bytes total..
                        current_token_length = 2
                    else:
                        # If we are outside offset reach discard the match and update new macth position..
                        self.history[current_token.encoding] = (encoded_pos,current_head)

            encoded_pos += current_token_length

    #
    #
    #
    
    def PASS1_outputEOF(self):
        if (args.debug):
            sys.stderr.write("TOKEN  end: 00 000000\n")
        
        self.tokens.append(PSGToken(PSGToken.TAG_EOF,bytes([0b00000000,])))

#
#
#
#

prs = argparse.ArgumentParser()
prs.add_argument("input_file",metavar="input_file",type=str,help="PSG file or '' if stdin")
prs.add_argument("output_file",metavar="output_file",type=str,nargs="?",help="Output file or stdout "
                 "if missing", default="")
prs.add_argument("--verbose","-v",dest="verbose",action="store_true",default=False,help="Show some process output")
prs.add_argument("--debug",dest="debug",action="store_true",default=False,help="Show debug output")
prs.add_argument("--lz","-z",dest="lz",action="store_true",default=False,help="Enable history references")
prs.add_argument("--multi","-m",dest="multi",action="store_true",default=False,help="Enable multi-frame matches of history references")
prs.add_argument("--delta","-d",dest="sparse",action="store_true",default=False,
    help="Enable delta coding of AY register writes")
prs.add_argument("--oneput","-o",dest="oneput",action="store_true",default=False,
    help="Enable single changed register output")
prs.add_argument("--bankswitch","-b",dest="bankswitch",action="store_true",default=False,
    help="Add 16K bank boundary marks")
prs.add_argument("--cache","-c",dest="cache",action="store_true",default=False,
    help="Cache most used AY register writes")

args = prs.parse_args()

if __name__ == "__main__":
    if (args.input_file == ""):
        input_file = sys.stdin.buffer
    else:
        input_file = args.input_file

    if (args.output_file == ""):
        if (args.bankswitch):
            sys.stderr.write("--bankswitch work only with output files\n")
            exit(0)

        output_file = sys.stdout.buffer
    else:
        output_file = args.output_file

    if (args.bankswitch):
        raise NotImplementedError("--bankswitch")
        exit()

    if (args.debug):
        args.verbose = True

    with PSGio(input_file,output_file) as io:
        psg = PSGCompressor(io)
        hdr = psg.parseHeader()

        if (hdr is not None):
            if (args.debug):
                sys.stderr.write(f"{hdr.tag}\n")
        else:
            sys.stderr.write("not a PSG file\n")
            exit()

        cont = True



        # PASS #1

        if (args.verbose):
            d = "enabled" if args.sparse else "disabled"
            o = "enabled" if args.oneput else "disabled"
            sys.stderr.write(f"PASS #1 - tokenizing with delta coding {d} and oneput {o}\n")

        while (cont):
            cont = psg.PASS1_parseFrames()
            used = psg.PASS1_update()

            #
            if (cont and used == 0):
                #
                # For some reason PSG file was constructed so that it has outputs
                # without register changes -> empty frame after delta coding.
                # Substitute such frame as a frame wait. The wait frame is passed
                # to frame parser in the psg.numPrevSync
                #
                if (args.debug):
                    sys.stderr.write("Spurious empty frame - check the PSG file\n")
                continue

            psg.PASS1_outputSyncTokens(False)
            psg.PASS1_outputFrames()

        #
        if (args.verbose):
            sys.stderr.write(f"  Input PSG file length is {io.read()} bytes\n")
        
        psg.PASS1_outputSyncTokens(True)
        psg.PASS1_outputEOF()

        if (args.verbose):
            sys.stderr.write(f"  PSG file length after PASS1 is {psg.get_output_size()} bytes\n")

        # PASS #2 - not implemented yet

        if (args.cache):
            if (args.verbose):
                sys.stderr.write("PASS #2 - cache lines\n")

            psg.PASS2_build_cache()
            psg.PASS2_replace_with_cached()

            if (args.verbose):
                sys.stderr.write(f"  PSG file length after PASS2 is {psg.get_output_size()} bytes\n")
        
        # PASS #3

        if (args.lz):
            if (args.verbose):
                m = "enabled" if args.multi else "disabled"

                sys.stderr.write(f"PASS #3 - LZ crunching with multiple matches {m}\n")
            
            if (args.multi):
                # Refined multistep LZ
                psg.PASS3_lz_multi()
            else:
                # Legacy single shot LZ
                psg.PASS3_lz_single()

            if (args.verbose):
                sys.stderr.write(f"  PSG file length after PASS3 is {psg.get_output_size()} bytes\n")

        else:
            # Fake PASS #3 to add bank switching and alignment support
            psg.PASS3_lz_null()
        
        # PASS #4 - saving

        if (args.verbose):
            sys.stderr.write("PASS #4 - saving PSGPacker output\n")
       
        # Write cached lines if any
        if (args.cache):
            cached_lines = sorted(psg.cached_tags.items(),key=lambda x:x[1].cache_line)
            for cached_tag,cached_token in cached_lines:
                io.putb(cached_tag.__len__())
                
                for n in range(cached_tag.__len__()):
                    io.putb(cached_tag[n])

        # write packed tokens
        for b in psg.tokens:
            if (b is not None):
                for n in range(b.encoding.__len__()):
                    io.putb(b.encoding[n])

        if (args.verbose):
            packed = psg.get_output_size()
            original = io.read()
            sys.stderr.write(f"Final PSG file length is {packed} bytes, packed to {packed/original*100:.1f}%\n")


#
#
# 00 000000          -> EOF
# 00 nnnnnn          -> wait sync & repeat previour PSG reg output nnnnnn times
# 01 00nnnn          -> register nnnn (0-13) followed by 1 time [8]
# 01 001110          -> reserved tag
# 01 001111 bbbbbbbb  -> bank switch mark followed by the next bank number > 0
# 01 rrrrrr >= 16
# 01 ffffff          -> Play from cached register bank rrrrrr-16
#    rrrrrr >= 32
# 01 rrrrrr nnnnnnnn nnnnnnnn -> point at 2^16-1 bytes in history and play from there for rrrrrr-31 times
# 10 nnnnnn nnnnnnnn -> point at 2^14-1 bytes in history and play from there once
# 11 llllll hhhhhhhh -> regs 0 to 13 followed by 1 to 14 times [8]
#


# // vim: set autoindent cursorline tabstop=4 softtabstop=4 expandtab
