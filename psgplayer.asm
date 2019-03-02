;
; (c) 2018-19 Jouni Korhonen
;
; PSGPlayer v0.4a
;


        org     $8000


main:
        ld      hl,module
        call    psgplayer+6

loop:
        halt

        xor     a
        out     (254),a
        ld      c,3
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
;    CALL psgplayer+6
;
; To unpack a frame:
;    CALL psgplayer+4 (variable cycles)
;
; To update AY registers (cycle exact):
;    CALL psgplayer+0
;
; To stop music:
;    CALL psgplayer+2
;    CALL psgplayer+0
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
        ;
        xor     a
        ld      hl,_regbuf+13
        ld      (hl),$ff
 
        ld      b,13
_clr:   dec     l
        ld      (hl),a
        djnz    _clr
        ;
        ld      (_wait),a
        ld      hl,(_mod)
        ld      (_pos),hl
        ;
        ; At exit A=0 and HL=mod
        ;
        ret
        ;

;
; Called every frame refresh in a position that needs cycle exact timing.
; The subroutine outputs the register delta buffer into the AY registers.
;
; Total 560 cycles
;
_play:  ;
        ld      de,$bfff    ; 10
        ld      bc,$fffd    ; 10
        ld      hl,_regbuf  ; 10

        REPT    13
        out     (c),l       ; 12 OUT L to $fffd -> select
        ld      b,d         ;  4
        outi                ; 16 OUT (HL) to $bffd -> value
        ld      b,e         ;  4
        ENDM
        out     (c),l       ; 12
        ld      b,d         ;  4
        ld      a,(hl)      ;  7
        ld      (hl),e      ;  7
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
        ld      hl,(_pos)
        call m, _gettags
        ld      (_pos),hl
        ld      (_wait),a
        ret

        ;
_gettags:
        ld      a,(hl)
        and     a
        ;
        ; TAG 00 00000 -> eof
        ;
        jp z,   _stop
        ;
_not_eof:
        inc     hl
        jp m,   _tag_1xnnnnnn
        ;
        ; Return if TAG 00 nnnnnn
        cp      01000000b
        jr nc,  _tag_01rrnnnn
        dec     a               ; Decrement one wait since wait itself
        ret                     ; counts as one frame..
        ;
_tag_01rrnnnn:
        and     00111111b
        ld      d,HIGH(_regbuf)
        ld      e,a
        cp      16
        jr c,   _oneput
_lutput:
        ; TAG 01 rrnnnn
        and     00001111b
        ld      c,a
        ld      a,(de)
        ld      e,c
        ld      (de),a
        xor     a
        ret
_oneput:
        ; TAG 01 00nnnn + [8]
        push    de
        pop     ix
        ld      a,(hl)
        ldi
        ;
        ld      c,(ix+32)
        ld      (ix+16),c
        ld      c,(ix+48)
        ld      (ix+32),c
        ld      (ix+48),a
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
        ld      a,(hl)
        inc     hl
        call    _tag_11nnnnnn
        pop     hl
        ret
        ;
_tag_11nnnnnn:
        ;
        ; TAG 11 nnnnnn nnnnnnnn
        ;   reg  012345 6789abcd
        ;
        ld      c,a         ; C > 14 always..
        ld      b,(hl)
        inc     hl
        add     a,a
        add     a,a
        ld      de,_regbuf
        
        REPT    6
        add     a,a
        jr nc,  $+5
        ldi
        db      $fe
        inc     e
        ENDM
        ld      a,b
        REPT    7
        add     a,a
        jr nc,  $+5
        ldi
        db      $fe
        inc     e
        ENDM
        add     a,a
        ret nc
        ldi
        ;                   ; A = 0
        ret


;
;
_mod:   dw      0           ; PSG song initial position
_pos:   dw      0           ; PSG song position..
_wait:  db      0

        org     ($+255) & 0xff00    ; Align to 256 bytes
_regbuf:
_lut:
        ds      14+2
        ds      48


;
;
module:
        incbin  "u2.psg"

        END main







