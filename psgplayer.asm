;
; (c) 2018-21 Jouni Korhonen
;
; PSGPlayer v0.5
;



        org     $8000


main:
        ld      hl,callback
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


        ; A dummy callback that just returns the same module location
        ; The callback MUST return the module address in HL and "wait"
        ; amount in A.
        ; On entry A = 0 if this was called by the _init/_stop function.
        ;          A > 0 then this was called for a bankswitch.
callback:
        ld      hl,module
        xor     a
        ret


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; To init player:
;    LD   HL,callback_for_bankswitch
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
; Backswitch function:
;  Inputs:
;     A = 0 if called for init/stop
;     A > 0 if called for bankswitch
;  Returns:
;     HL = ptr to the "new" module
;     A = 0

psgplayer:
        jr      _play   ; 0
        jr      _stop   ; 2
        jr      _next   ; 4
_init:                  ; 6

;
; Input:
;  HL = ptr to callback function to return the module ptr.
;
        ld      (_cb),hl
        ;

_stop:
; _stop also resets the current song position.
;
        ;
        xor     a
        ld      hl,_regbuf

        ; Clears _regbuf and _rep 
        ld      b,14+1
_clr:   ld      (hl),a
        inc     l
        djnz    _clr
        ;

        ld      hl,_ret
        push    hl
        ld      hl,(_cb)
        jp      (hl)

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
_ret:   ;
        ld      (_wait),a
        ld      (_pos),hl
        ret
        ;
_gettags:
        ; A = $ff
        ;
        ld      a,(_rep)
        sub     1
        jr c,   _norestore
        ld      (_rep),a
        jr nz,  _norestore
        ld      hl,(_resume)
_norestore:
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
        cp      15
        jr z,   _callback
        
        cp      32
        jr nc,   _lz
        cp      16
        jr nc,  _cache
_oneput:
        ; TAG 01 00nnnn + [8]
        ld      e,a
        ldi
        xor     a
        ret
        ;
_callback:                      ; This code is still untested!
        ; TAG 01 001111 + [8]
        ld      a,(hl)
        ld      hl,_norestore
        push    hl
        ld      hl,(_cb)
        ; A > 0
        jp      (hl)
        ;
_lz:
        ; TAG 01 rrrrrr nnnnnnnn nnnnnnnn
        ;
        add     a,-31           ; Sets C-flag. This is important!
        ld      (_rep),a
        ld      b,(hl)
        inc     hl
        ld      c,(hl)
        inc     hl
        ld      (_resume),hl
        sbc     hl,bc
        jr      _norestore

_cache:
        ; Placeholder for a AY reg caching
        xor	a
        ret

_tag_1xnnnnnn:
        ;
        ; TAGs 11 llllll hhhhhhhh  -> array of [8] for registers
        ;      10 nnnnnn nnnnnnnn  -> single count LZ from history
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
        ; TAG 11 llllll hhhhhhhh
        ;   reg  543210 dcba9876
        ;
        
        ld      c,a         ; C > 14 always..
        ld      b,(hl)
        inc     hl
        ld      de,_regbuf
        
        REPT    6
        rrca
        jr nc,  $+5
        ldi
        db      $fe
        inc     e
        ENDM
        ld      a,b
        REPT    8
        rrca
        jr nc,  $+5
        ldi
        db      $fe
        inc     e
        ENDM
        xor     a
        ret

        ;
_pos:   dw      0           ; PSG song position..
_resume:
        dw      0           ; PSG resume song position after LZ  
_cb:    dw      0           ; Backswitch code callback function

        org     ($+255) & 0xff00    ; Align to 256 bytes
_regbuf:
        ds      14
_rep:   db      0           ; LZ repeat counter
_wait:  db      0
        ; The remaining 240 will likely be used in future
        ; for the register line caching.

;
;
module:
        incbin  "u2.pac"

        END main







