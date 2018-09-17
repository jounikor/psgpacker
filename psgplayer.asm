;
; (c) 2018 Jouni Korhonen
;
; PSGPlayer v0.1 - to be modified big time
;


        org     $8000


main:
        ld      hl,module
        call    psgplayer+6

loop:
        halt

        xor     a
        out     (254),a
        ld      c,8
.wait1:
        ld      b,0
.wait2:
        djnz    .wait2
        dec c
        jr nz,  .wait1

        ld      a,2
        out     (254),a
        ;
        call    psgplayer+0
        ;
        ld      a,1
        out     (254),a
        call    psgplayer+4
        xor     a
        out     (254),a

        jr      loop



;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; To init player:
;    LD   HL,packedPSG
;    CALL plagplayer+6
;
; To unpack a frame:
;    CALL psgplayer+4 (variable cycles)
;
; To update AY registers (cycle exact):
;    CALL psgplayer+0
;
; To stop music:
;    CALL psgplayer+2
;

psgplayer:
        jr      _play   ; 0
        jr      _stop   ; 2
        jr      _next   ; 4
_init:                  ; 6

;
; Input:
;  HL = ptr to the packed PSG file.
;
        ld      (_mod),hl
        ;

_stop:
; _stop also resets the current song position.
;
        xor     a
        ld      hl,(_mod)
        ld      (_pos),hl
        ld      hl,_wait
        ld      (hl),a
        ;
        ld      hl,_regbuf
        ld      b,13
_clr:   ld      (hl),a
        inc     l
        djnz    _clr
        ;
        cpl
        ld      (hl),a
        ;


;
; Called every frame refresh in a position that needs cycle exact timing.
; The subroutine outputs the register delta buffer into the AY registers.
;
; Total 543 cycles
;
_play:  ;
        ld      de,$bfff    ; 10
        ld      bc,$fffd    ; 10
        ld      hl,_regbuf  ; 10

        REPT    13
        out     (c),l       ; 12 OUT L to $fffd -> select
        ld      b,d         ;  4
        outi                ; 15 OUT (HL) to $bffd -> value
        ld      b,e         ;  4
        ENDM
        out     (c),l       ; 12
        ld      b,d         ;  4
        ld      a,(hl)      ;  7
        cp      $ff         ;  7 -> 60+13*35
        ;
        jr z,   _nops       ; 12 if jr, 5 if pass through
        ;
        out     (c),a       ; 12
_nops:
        ret nz              ; 11 if out, 5 if jr
        ret z               ; 11 if jr, 5 ..
        ;
        ; jr z -> 12+5+11 == 28
        ; out  -> 5+12+11 == 28

;
; Unpacks the next "frame" of PSG data.
;
; Called every frame in a position that does not have cycle exact 
; timing requirements.
;
_next:  ;
        ld      a,(_wait)
        dec     a
        ld      (_wait),a
        ret     p
        ;
        ; I am not sure the below is actually needed.. the intention is not to
        ; Change envelope shape/cycle register if there is no change in the
        ; register output either..
        ;
        ld      a,$ff
        ld      (_regbuf+13),a
        ;
        ld      hl,(_pos)
        ld      a,(hl)
        and     a
        jr nz,  _not_eof
        ;
        ; TAG 00 00000 -> eof
        ;
        ld      hl,(_mod)
        ld      a,(hl)
_not_eof:
        inc     hl
        ld      b,a
        and     11000000b
        jr nz,  _not_00nnnnnn
        ;
        ; TAG 00 000001 -> 00 111111 -> regs 0 to 5 + number of nnnnnn bits * [8]
        ;   reg  012345
        ;
_tag_00nnnnnn:
        ld      d,b
        ld      e,0
        ld      b,6
        jr      _deltainit
        ;
_not_00nnnnnn:
        ;
        ; TAGs 01 nnnnnn  -> sync + repeat previous regs buffer nnnnnn+1 times
        ;      10 00 nnnn -> register nnnn followed by 1 times [8]
        ;      10 01 nnnn -> reserved (previous stored regs buffer 1-15, 0 is current)
        ;      10 10 rrrr -> reserved
        ;      10 11 rrrr -> reserved

        cp      01000000b
        jr nz,  _not_01nnnnnn
        ;
        ; TAG 01 nnnnnn
        ;
        xor     b
        jr      _exit
        ;
_not_01nnnnnn;
        cp      10000000b
        jr nz,  _not_10nnnnnn
        ;
        ; TAG 10 00 nnnn -> register nnnn followed by 1 [8]
        ;
        ; Note that currently 1001nnnn, 1010rrrr and 1011rrrr are not even decoded as they
        ; cannot appear in the packed stream.
        xor     b
        ld      e,a
        ld      d,HIGH(_regbuf)
        ldi
        jr      _exit0
        ;
_not_10nnnnnn:
        ;
        ; TAG 11 nnnnnn nnnnnnnn
        ;   reg  012345 6789abcd
        ;
        ld      d,b
        ld      e,(hl)
        inc     hl
        ld      b,14
_deltainit:
        push    de
        exx
        pop     hl
        add     hl,hl
        add     hl,hl
        exx
        ;
        ld      de,_regbuf
        ;
_deltaloop:
        exx
        add     hl,hl
        exx
        jr nc,  _skip
_delta:
        ld      a,(hl)
        ld      (de),a
        inc     hl
_skip:
        inc     e
        djnz    _deltaloop
_exit0:  
        xor     a
_exit:  ;        
        ld      (_pos),hl
        ld      (_wait),a
        ret

;
;
_mod:   dw      0           ; PSG song initial position
_pos:   dw      0           ; PSG song position..
_wait:  db      0

        org     ($+255) & 0xff00    ; Aligh to 256 bytes
_regbuf:
        ds      14


;
;
;
;
;

module:
        incbin  "o.bin"





        END main







