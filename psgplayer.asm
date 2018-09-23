;
; (c) 2018 Jouni Korhonen
;
; PSGPlayer v0.2 - to be modified big time
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
; Total 540 cycles
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
        cp      e           ;  4 -> 57+13*35
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
        jp p,   _exit
        ;
        ; I am not sure the below is actually needed.. the intention is not to
        ; Change envelope shape/cycle register if there is no change in the
        ; register output either..
        ;
        ld      (_regbuf+13),a
        ;
        ld      hl,(_pos)
        call    _gettags
        ld      (_pos),hl
_exit:
        ld      (_wait),a
        ret

        ;
_gettags:
        ld      a,(hl)
        and     a
        jr nz,  _not_eof
        ;
        ; TAG 00 00000 -> eof
        ;
        ld      hl,(_mod)
        ret
        ;
_not_eof:
        inc     hl
        jp m,   _tag_1xnnnnnn
        ;
        ; TAG 01 00nnnn + [8]
        ;     00 nnnnnn  
        ;
        ; Return if TAG 00 nnnnnn
        cp      01000000b
        jr nc,  _tag_0100nnnn
        dec     a               ; Decrement one wait since wait itself
        ret                     ; counts as one..
        ;
_tag_0100nnnn:
        ; TAG 01 00nnnn + [8]
        ;
        and     00001111b
        ld      e,a
        ld      d,HIGH(_regbuf)
        ldi
        xor     a
        ret
_tag_1xnnnnnn:
        ;
        ; TAGs 11 nnnnnn nnnnnnnn  -> array of [8] for registers
        ;      10 nnnnnn nnnnnnnn  -> LZ from history
        ;

        cp      11000000b
        jr nc,  _tag_11nnnnnn
        
        ;
        ; TAG 10 nnnnnn nnnnnnnn
        ;
        and     00111111b           ; Clears C-Flags, important!
        ld      b,a
        ld      c,(hl)
        inc     hl
        push    hl
        sbc     hl,bc
        ld      d,(hl)
        inc     hl
        call    _lz_skip
        pop     hl
        ret
        ;
_tag_11nnnnnn:
        ;
        ; TAG 11 nnnnnn nnnnnnnn
        ;   reg  012345 6789abcd
        ;
        ld      d,a
_lz_skip:
        ld      e,(hl)
        inc     hl
        ld      b,14
        ;
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
        xor     a
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
module:
        incbin  "q.bin"

        END main







