;-----------------------------------------------------------------------------
; (c) 2018-25 Jouni Korhonen
;
; PSGPlayer v0.73
;
; An example with propwer bank switching callback code/example.
; Use USR0 mode to run this.
;
; Assembler used is Pasmo (available at https://github.com/jounikor/pasmo/):
;  Pasmo v. 0.5.5.paged (C) 2004-2021 Julian Albo (2018-2023 Jouni Korhonen)
;
; Assembler command:
;  pasmo --tapbas128 --memmap -d psgplayer.asm test.tap
;
; PSGPacker command used to compress bbt2.psg:
;  python3 psgpacker.py --lz --multi --cache --oneput --bankswitch  -v bbt2.psg bbt2.pac
;
; bbt2 AY song (c) Fudgepacker
;
;
; This must be set to 1 if PSGPacker used --cache and must be 0 otherwise
USE_CACHE   equ 1
; This must be set to 1 if PSGPacker used --oneput
USE_ONEPUT  equ 1
; Put your bank swithing macro here..
; A   must be preserved when exiting the macro
BANKSWITCH  macro
        local   _skip
		push    af
        cp      2
        jr nz, _skip
        inc     a
_skip:
		or      0x10
        ld      bc,32765
		out     (c),a
		pop     af
        
        endm



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
;     A = $ff if called for init/stop
;     A >= 0 if called for bankswitch
;  Returns:
;     HL = ptr to the "new" module
;     A = 0

psgplayer:
        jr      _play   ; 0
        jr      _stop   ; 2
        jr      _next   ; 4
;_init:                  ; 6
;
; Input:
;  HL = ptr to callback function to return the module ptr.
;
        ld      (_smc_cb+1),hl
;

_stop:
; _stop also resets the current song position.
;
        ; Set to initial bank so tha the bank switching routine
        ; we also do the required initialization for cached lines
        ; etc..
        ld      a,$ff
_stop2:
        ld      hl,_regbuf+13

        ; Set R15 to $ff so that _play() will skip it if not exlicitly
        ; changed by the _next() 
        ld      (hl),$ff

        ; Clears _regbuf 
_clr:   dec     l
        ld      (hl),0
        jr nz,  _clr

        ld      hl,_ret
        push    hl
        ld      hl,(_smc_cb+1)
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
_smc_wait:
        ld      a,0
        dec     a
_smc_pos:
        ld      hl,0
        call m, _gettags
_ret:   ;
        ld      (_smc_wait+1),a
        ld      (_smc_pos+1),hl
        ret
        ;
_gettags:
        ; A = $ff
        ;
_smc_rep:
        ld      a,0
        sub     1
        jr c,   _norestore
        ld      (_smc_rep+1),a
        jr nz,  _norestore
_smc_resume:
        ld      hl,0
_norestore:
        ld      a,(hl)
        and     a
        ;
        ; TAG 00 00000 -> eof
        ;
        jp z,   _stop2          ; Implicitly switch to bank 0 (A=0) 
        ;
        ; Not eof of song yet..
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
        ;
        ; TAG 01 00nnnn + [8]
        ld      e,a
        ldi
        xor     a
        ret
        ENDIF
        ;
_callback:
        ; TAG 01 001111 + [8]
        ld      a,(hl)
        ld      hl,_norestore
        push    hl
_smc_cb:
        jp      0
        ;ld      hl,0
        ; A > 0
        ;jp      (hl)
        ;
_lz:
        ; TAG 01 rrrrrr nnnnnnnn nnnnnnnn
        ;
        add     a,-31           ; Sets C-flag. This is important!
        ld      (_smc_rep+1),a
        ld      b,(hl)
        inc     hl
        ld      c,(hl)
        inc     hl
        ld      (_smc_resume+1),hl
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


;-----------------------------------------------------------------------------
; A dummy callback that handles just two part banks switched module
; without actully doing any bank switching..
; In a case your song does not need to be banked, e.g. you can dedicate more
; than 16K for it, the bank switching is mostly a blank function taking
; care of the first time initialization of the song.
;
; You need to modify the callback to work properly in your own project.
;
; On return the callback MUST return the module address in HL and wait
; amount in A.
;
; On entry A = $ff if this was called by the _init/_stop function.
;          A >= 0 then this was called for a bankswitch.

callback:
        ld      hl,$c000
        cp      $ff
        jr nz,  _not_init

        xor     a
        BANKSWITCH

;
; This code must be included when A=0 and PSGPacker used --cache
; Note that the first "bank" or the first ~16K contains the cache information,
; which is needed only during the initialization time. The cache lines are
; used over the entire compressed song and must be skipped by the "normal"
; runtime bank switching code. Look at the example code below how to do that, which
; stores the pointer to the song bank0 after the cache information for the runtime
; back switching callback routine.
; Cache lines share the 256 bytes area starting with _regbuf. The cache lines
; are copied to a separate buffer to avoid alignment requirements for the song
; itself..
;
; There are 15 cache lines with the following (byte aligned) format:
;   byte   0 = n = number of bytes in cacheline
;   byte   1 to 1+n of cache line information
;
; D = HIGH(_regbuf) = HIGH(_cache)
;
        IF  USE_CACHE
        ld      d,HIGH(_regbuf)
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
        ld      (_smc_hl+1),hl

;
;
_not_init:
        and     a
        jr nz,  _not_first
_smc_hl:
        ld      hl,0
_not_first:
        BANKSWITCH
        ret

        ;
	    org     ($+255) & $ff00
_regbuf:
        ds      14
        ds      2           ; padding

        IF USE_CACHE
        ds      15*16       ; 15 cached lines; must be 16 bytes aligned
                            ; within 256 bytes aligned block.
        ENDIF
        
;-----------------------------------------------------------------------------
; Banked packed songs parts
        
        BANK    0
        org     $c000
        incbin  "bbt2.pac0"
        
        BANK    1
        org     $c000
        incbin  "bbt2.pac1"

        BANK    3
        org     $c000
        incbin  "bbt2.pac2"


        END main







