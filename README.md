psgpacker v0.7 - an experimental PSG packer and Z80 player for ZX Spectrum

The psgpacker.py requires python3 to run. It coverts PSG files for AY-3-8910 into
a compact (compressed) form and the companion player written in Z80 assembly 
depacks the compressed file on fly before outputting data to AY.

The player is divided into two parts: 
 - Depack next frame of AY register data. This routine has variable cycle count.
 - Play depacked AY register data. This routine is cycle exact (560 at the moment).
This arrangement is made to allow using music with raster/timing critical effects.


usage: psgpacker.py [-h] [--verbose] [--debug] [--lz] [--multi] [--delta]
                    [--oneput] [--bankswitch]
                    input_file [output_file]

positional arguments:
  input_file        PSG file or '' if stdin
  output_file       Output file or stdout if missing

optional arguments:
  -h, --help        show this help message and exit
  --verbose, -v     Show some process output
  --debug           Show debug output
  --lz, -z          Enable history references
  --multi, -m       Enable multi-frame matches of history references
  --delta, -d       Enable delta coding of AY register writes
  --oneput, -o      Enable single changed register output
  --bankswitch, -b  Add 16K bank boundary marks


To init player:
   LD   HL,bankswitch_callback
   CALL psgplayer+6

To unpack a frame:
   CALL psgplayer+4 (variable cycles)

To update AY registers (cycle exact):
    CALL psgplayer+0

To stop music:
   CALL psgplayer+2
   CALL psgplayer+0

Note 1: that the '_regbuf' really needs to be 256 byte aligned.
Note 2: the player has the following assumotions on the bank switching callback function:
  - No registers are changed except HL and A on return. The HL contains the location of
    the "new" data and the A contains the wait amount (should be 0).
  - No init is called.
  - _regbuf and other player variables remain unchanged.
Note 3: The _init and _stop functions actually call the callback to get the module ptr.
