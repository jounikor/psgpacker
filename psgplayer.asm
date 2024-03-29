;
; (c) 2018-21 Jouni Korhonen
;
; PSGPlayer v0.72
;


; This must be set to 1 if PSGPacker used --cache and must be 0 otherwise
USE_CACHE   equ 1
; This must be set to 1 if PSGPacker used --oneput
USE_ONEPUT  equ 1


;-----------------------------------------------------------------------------
; Example main loop

        org     $8000


main:
        ld      hl,callback
        call    psgplayer+6

loop:
        halt
        ;nop

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
;     D = HIGH(_regbuf)
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
_stop2:
        ld      hl,_regbuf+13

        ; Set R15 to $ff so that _play() will skip it if not exlicitly
        ; changed by the _next() 
        ld      (hl),$ff

        ; Clears _regbuf 
_clr:   dec     l
        ld      (hl),a
        jr nz,  _clr

        ; D = HIGH(_regbuf)
        ld      d,h
        
        ld      hl,_ret
        push    hl
        ld      hl,(_cb)
        jp      (hl)

;
; Called every frame refresh in a position that needs cycle exact timing.
; The subroutine outputs the register delta buffer into the AY registers.
;
; Total 562 cycles

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
        cp      e           ;  4 -> 64+13*36
        ;
        jr z,   _nops       ; 12 if jr, 7 if pass through
        ;
        out     (c),a       ; 12
        ret                 ; 10 if cc true, 5 if cc false (pass through)
_nops:  cp      0           ; 7
        ret                 ; 10
        ;
        ; jr z -> 12+7+10 == 29
        ; out  -> 7+12+10 == 29

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
        jp z,   _stop2
        ;
_not_eof:
        ld      d,HIGH(_regbuf)
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
        
        cp      32
        jr nc,   _lz
        cp      16
        jr nc,  _cached_tag
        
        IF USE_ONEPUT           ; Does not harm to leave included even if
        cp      15              ; the packed PSGPacker did not use --oneput
        jr z,   _callback
_oneput:
        ; TAG 01 00nnnn + [8]
        ld      e,a
        ldi
        xor     a
        ret
        ENDIF
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

_cached_tag:
        push    hl
        ld      h,d             ; D = HIGH(_regbuf) 
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      l,a
        call    _norestore
        pop     hl
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
        ;ld      de,_regbuf
        ld      e,0

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
        ; A dummy callback that handles just two part banks switched module
        ; without actully doing any bank switching..
        ;
        ; You need to modify the callback to work properly in your own project.
        ;
        ; On return the callback MUST return the module address in HL and wait
        ; amount in A.
        ;
        ; On entry A = 0 if this was called by the _init/_stop function.
        ;          A > 0 then this was called for a bankswitch.
        ;          D = HIGH(_regbuf) = HIGH(_cache)
callback:
        and     a
        jr nz,  _not_init
        
        ld      hl,module

        ; This code must be included when A=0 and PSGPacker used --cache
        ; What it does is to move cache information from the beginning of
        ; the packed module into the proper location within the _regbuf.
        IF  USE_CACHE
        ;ld      d,HIGH(_cache)
        ld      b,a
        ld      a,00010000b
_prep_cache:
        ld      c,(hl)
        inc     hl
        ld      e,a
        ldir
        add     a,16
        jr nc,  _prep_cache
        ;
        ENDIF
        ret

_not_init:
        ld      hl,module1
        xor     a
        ret

        ;
_pos:   dw      0           ; PSG song position..
_resume:
        dw      0           ; PSG resume song position after LZ  
_cb:    dw      0           ; Backswitch code callback function
_rep:   db      0           ; LZ repeat counter
_wait:  db      0

        org     ($+255) & 0xff00    ; Align to 256 bytes
_regbuf:
        ds      14
        ds      2           ; padding

        IF USE_CACHE
        ds      15*16       ; 15 cached lines; must be 16 bytes aligned
                            ; within 256 bytes aligned block.
        ENDIF
        
;
;
module:
        incbin  "u8.pac0"
module1:
        incbin  "u8.pac1"

        END main







