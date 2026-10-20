; REWIND - native ZX Spectrum 128K AY music quiz.
; Resident code in bank 2; LZ+delta music banks 0,1,3,4; decode cache bank 7.
 org 32768
 jp start
 jp tape_start

tape_start:
 di
 ld sp,0xbc00
 im 1
 ; Read the screen before the music banks; subsequent ROM calls keep it visible.
 ld ix,16384
 ld de,6912
 ld a,255
 scf
 call 0x0556
 jp nc,tape_load_error
 ld a,16
 call tape_bank
 ld a,17
 call tape_bank
 ld a,19
 call tape_bank
 ld a,20
 call tape_bank
 ld a,16
 ld bc,0x7ffd
 out (c),a
 jp start
tape_bank:
 ld bc,0x7ffd
 out (c),a
 ld ix,49152
 ld de,16384
 ld a,255
 scf
 call 0x0556
 ret c
tape_load_error:
 ; Visible loading error, rather than starting with missing music.
 ld a,2
 out (254),a
 di
tape_error:
 halt
 jr tape_error

start:
 di
 ld sp,0xbc00
 xor a
 out (254),a
 ld (lastkey),a
 ld (mode),a
 ld (playing),a
 ld hl,0x735d
 ld (seed),hl
 ; IM2 handler stays in fixed bank 2. No ROM or system variables used in play.
 ld hl,0xbe00
 ld de,0xbe01
 ld bc,256
 ld (hl),0xbd
 ldir
 ld a,0xfb
 ld (0xbdbd),a
 ld a,0xed
 ld (0xbdbe),a
 ld a,0x4d
 ld (0xbdbf),a
 ld a,0xbe
 ld i,a
 im 2
 call silence
 call show_intro
 ei
main_loop:
 halt
 call music_tick
 call read_key
 ld b,a
 ld a,(lastkey)
 cp b
 jr z,no_new_key
 ld a,b
 ld (lastkey),a
 or a
 call nz,dispatch
no_new_key:
 ; Human timing changes the shuffle seed without touching the active tune.
 ld a,(mode)
 or a
 jr nz,main_loop
 call random
 jr main_loop

dispatch:
 cp 81
 jp z,go_menu
 ld b,a
 ld a,(mode)
 or a
 jr z,menu_key
 cp 1
 jr z,question_key
 cp 2
 jr z,feedback_key
 cp 3
 jr z,results_key
 cp 4
 jr z,intro_key
 ret
intro_key:
 ld a,b
 cp 32
 jp z,go_menu
 ret
menu_key:
 ld a,b
 sub 49
 cp 2
 ret nc
 ld (category),a
 call new_round
 ret
question_key:
 ld a,b
 cp 82
 jp z,start_music
 cp 32
 jr z,toggle_music
 sub 49
 cp 4
 ret nc
 jp answer
feedback_key:
 ld a,b
 cp 32
 ret nz
 jp next_question
results_key:
 ld a,b
 cp 32
 jp z,new_round
 ret

toggle_music:
 ld a,(playing)
 or a
 jr z,resume_music
 xor a
 ld (playing),a
 call silence
 ld hl,msg_paused
 jp music_status
resume_music:
 ld hl,(frames_left)
 ld a,h
 or l
 jp z,start_music
 ld a,1
 ld (playing),a
 ld hl,msg_playing
 jp music_status

go_menu:
 call silence
 xor a
 ld (playing),a
 jp menu

show_intro:
 ld a,4
 ld (mode),a
 ; Replace the SCR loading footer once loading is complete.
 ld hl,0x50e0
 ld b,8
intro_clear_line:
 push bc
 push hl
 ld d,h
 ld e,l
 inc de
 ld bc,31
 ld (hl),0
 ldir
 pop hl
 inc h
 pop bc
 djnz intro_clear_line
 ld d,23
 ld e,0
 ld b,32
 ld a,0x45
 call color_row
 ld hl,msg_intro
 ld d,23
 jp print_center

menu:
 call silence
 xor a
 ld (playing),a
 ld (mode),a
 call clear_screen
 ld hl,menu_layout
 call draw_layout
 ld d,1
 ld e,1
 ld b,30
 ld a,0x45
 call color_row
 ld d,2
 ld a,0x43
 call color_row
 ld d,4
 ld a,0x46
 call color_row
 ld d,7
 ld a,0x45
 call color_row
 ld d,10
 ld a,0x45
 call color_row
 ld d,13
 ld a,0x46
 call color_row
 ld d,16
 ld a,0x43
 call color_row
 ld d,18
 ld a,0x45
 call color_row
 ld d,21
 ld a,0x46
 call color_row
 ret

new_round:
 call silence
 xor a
 ld (playing),a
 ld (question_index),a
 ld (score),a
 ld (score+1),a
 ld (correct_count),a
 ld hl,used_wrong
 ld de,used_wrong+1
 ld bc,249
 ld (hl),a
 ldir
 ; Shuffle all fifty, then take a unique random subset for Normal.
 ld a,(category)
 or a
 ld a,25
 jr z,round_size_ready
 ld a,50
round_size_ready:
 ld (round_length),a
 ld hl,order
 ld b,50
 ld c,0
round_fill_loop:
 ld (hl),c
 inc c
 inc hl
 djnz round_fill_loop
 ld hl,order
 ld b,50
 call shuffle
 jp prepare_question

prepare_question:
 ld a,1
 ld (mode),a
 ld a,(question_index)
 ld e,a
 ld d,0
 ld hl,order
 add hl,de
 ld a,(hl)
 ld (current_song),a
 ; Locate the current category's pool of 25 answer labels.
 ld b,0
find_group:
 cp 5
 jr c,group_ready
 sub 5
 inc b
 jr find_group
group_ready:
 ld a,b
 ld (song_category),a
 add a,a
 ld e,a
 ld d,0
 ld hl,answer_pool_table
 add hl,de
 ld e,(hl)
 inc hl
 ld d,(hl)
 ld (option_pool),de
 ld hl,options
 ld a,(current_song)
 ld (hl),a
 ld a,1
 ld (pick_index),a
pick_distractor:
 ld b,25
 call random_mod
 ld e,a
 ld d,0
 ld hl,(option_pool)
 add hl,de
 ld b,(hl)
 ld a,(current_song)
 cp b
 jr z,pick_distractor
 ld e,b
 ld d,0
 ld hl,used_wrong
 add hl,de
 ld a,(hl)
 or a
 jr nz,pick_distractor
 ld (hl),1
 ld a,(pick_index)
 ld e,a
 ld d,0
 ld hl,options
 add hl,de
 ld (hl),b
 inc a
 ld (pick_index),a
 cp 4
 jr nz,pick_distractor
 ld hl,options
 ld b,4
 call shuffle
 call draw_question
 jp start_music

next_question:
 ld a,(question_index)
 inc a
 ld (question_index),a
 ld b,a
 ld a,(round_length)
 cp b
 jp z,results
 jp prepare_question

answer:
 ld (chosen_option),a
 ld e,a
 ld d,0
 ld hl,options
 add hl,de
 ld b,(hl)
 ld a,(current_song)
 cp b
 ld a,0
 jr nz,answer_flag
 inc a
answer_flag:
 ld (was_correct),a
 xor a
 ld (playing),a
 call silence
 ld a,2
 ld (mode),a
 ld hl,msg_wrong
 ld a,(was_correct)
 or a
 jr z,answer_message
 ld hl,(score)
 ld de,10
 add hl,de
 ld (score),hl
 ld a,(correct_count)
 inc a
 ld (correct_count),a
 ld hl,msg_correct
answer_message:
 ld de,0x0602
 call print_at
 ; Highlight the correct option green; chosen wrong option red.
 ld hl,options
 ld c,0
answer_highlight:
 ld a,(current_song)
 cp (hl)
 jr nz,check_chosen
 ld a,0x44
 jr paint_answer
check_chosen:
 ld a,(chosen_option)
 cp c
 jr nz,next_highlight
 ld a,(was_correct)
 or a
 jr nz,next_highlight
 ld a,0x42
paint_answer:
 push hl
 push bc
 ld b,a
 ld a,c
 add a,a
 add a,c
 add a,9
 ld d,a
 ld e,1
 ld a,b
 ld b,30
 call color_row
 inc d
 call color_row
 pop bc
 pop hl
next_highlight:
 inc hl
 inc c
 ld a,c
 cp 4
 jr nz,answer_highlight
 ld hl,msg_next
 ld de,0x1501
 call print_at
 ld hl,msg_back
 ld de,0x1601
 call print_at
 call draw_score
 ret

results:
 ld a,3
 ld (mode),a
 call silence
 call clear_screen
 ld hl,results_layout
 call draw_layout
 ld hl,(score)
 ld de,0x0b0e
 call print_word
 ld a,(correct_count)
 ld de,0x0e0a
 call print_number
 ld hl,msg_of
 ld de,0x0e0e
 call print_at
 ld a,(round_length)
 ld de,0x0e12
 call print_number
 ld d,2
 ld e,1
 ld b,30
 ld a,0x45
 call color_row
 ld d,11
 ld a,0x46
 call color_row
 ld a,(correct_count)
 ld b,a
 ld a,(round_length)
 cp b
 jr z,result_perfect
 ld hl,msg_nice
 ld d,17
 call print_center
 ld hl,msg_try_mix
 ld d,18
 jp print_center
result_perfect:
 ld hl,msg_perfect
 ld d,17
 call print_center
 ld hl,msg_know_tunes
 ld d,18
 jp print_center

; Fisher-Yates shuffle. HL buffer, B length; preserves no registers.
shuffle:
 ld (shuffle_base),hl
 ld a,b
 dec a
 ld (shuffle_index),a
shuffle_loop:
 ld a,(shuffle_index)
 inc a
 ld b,a
 call random_mod
 ld e,a
 ld d,0
 ld hl,(shuffle_base)
 add hl,de
 push hl
 ld a,(shuffle_index)
 ld e,a
 ld hl,(shuffle_base)
 add hl,de
 ld a,(hl)
 pop de
 ld c,a
 ld a,(de)
 ld (hl),a
 ld a,c
 ld (de),a
 ld a,(shuffle_index)
 dec a
 ld (shuffle_index),a
 jr nz,shuffle_loop
 ret
random:
 ; 16-bit maximal LFSR, advanced every menu frame for human timing entropy.
 ld hl,(seed)
 srl h
 rr l
 jr nc,random_done
 ld a,h
 xor 0xb4
 ld h,a
random_done:
 ld (seed),hl
 ld a,l
 ret
random_mod:
 call random
random_reduce:
 cp b
 ret c
 sub b
 jr random_reduce

; Set up a stream, preserving the approved AY register bytes exactly.
start_music:
 call silence
 ld a,(current_song)
 ld l,a
 ld h,0
 add hl,hl
 add hl,hl
 add hl,hl
 ld e,a
 ld d,0
 or a
 sbc hl,de
 ld de,song_table
 add hl,de
 ld a,(hl)
 inc hl
 ld bc,0x7ffd
 out (c),a
 ld e,(hl)
 inc hl
 ld d,(hl)
 inc hl
 ld (stream_ptr),de
 ld e,(hl)
 inc hl
 ld d,(hl)
 inc hl
 ld (frames_left),de
 ld c,(hl)
 inc hl
 ld b,(hl)
 ld hl,0x6000
 add hl,bc
 ld (packed_end),hl
 ld hl,(stream_ptr)
 ld de,0x6000
 ldir
 ; The temporary packed input is in fixed bank 5 outside the screen.
 ld a,23
 ld bc,0x7ffd
 out (c),a
 ld hl,0x6000
 ld de,49152
lz_loop:
 ld bc,(packed_end)
 or a
 sbc hl,bc
 add hl,bc
 jr z,lz_done
 ld a,(hl)
 inc hl
 bit 7,a
 jr nz,lz_reference
 inc a
 ld c,a
 ld b,0
 ldir
 jr lz_loop
lz_reference:
 and 127
 add a,3
 ld (lz_length),a
 ld c,(hl)
 inc hl
 ld b,(hl)
 inc hl
 push hl
 push de
 ex de,hl
 or a
 sbc hl,bc
 pop de
 ld a,(lz_length)
 ld c,a
 ld b,0
 ldir
 pop hl
 jr lz_loop
lz_done:
 ld hl,49152
 ld (stream_ptr),hl
 xor a
 ld (repeat_left),a
 ld hl,ay_frame
 ld (hl),a
 ld de,ay_frame+1
 ld bc,13
 ldir
 ld a,1
 ld (playing),a
 ld hl,msg_playing
 jp music_status

music_tick:
 ld a,(playing)
 or a
 ret z
 ld hl,(frames_left)
 ld a,h
 or l
 jr z,music_finished
 dec hl
 ld (frames_left),hl
 ld a,(repeat_left)
 or a
 jr z,decode_event
 dec a
 ld (repeat_left),a
 jp output_frame
decode_event:
 ld hl,(stream_ptr)
 ld a,(hl)
 inc hl
 bit 7,a
 jr z,decode_mask
 and 127
 dec a
 ld (repeat_left),a
 ld (stream_ptr),hl
 jp output_frame
decode_mask:
 ld d,a
 ld e,(hl)
 inc hl
 ld ix,ay_frame
 ld b,14
decode_register:
 srl d
 rr e
 jr nc,keep_register
 ld a,(hl)
 inc hl
 ld (ix+0),a
keep_register:
 inc ix
 djnz decode_register
 ld (stream_ptr),hl
output_frame:
 ld hl,ay_frame
 ld e,0
output_register:
 ld bc,0xfffd
 ld a,e
 out (c),a
 ld b,0xbf
 ld a,(hl)
 out (c),a
 inc hl
 inc e
 ld a,e
 cp 14
 jr nz,output_register
 ret
music_finished:
 xor a
 ld (playing),a
 call silence
 ld hl,msg_finished
 jp music_status
silence:
 ld bc,0xfffd
 ld a,7
 out (c),a
 ld b,0xbf
 ld a,63
 out (c),a
 ld a,8
silence_loop:
 ld bc,0xfffd
 out (c),a
 ld b,0xbf
 push af
 xor a
 out (c),a
 pop af
 inc a
 cp 11
 jr nz,silence_loop
 ret

music_status:
 ld a,(mode)
 cp 1
 ret nz
 ld de,0x0702
 jp print_at

; Keyboard matrix: 1..5, Q, R, SPACE. No ROM keyboard state is required.
read_key:
 ld bc,0xf7fe
 in a,(c)
 bit 0,a
 ld e,49
 jr z,key_found
 bit 1,a
 ld e,50
 jr z,key_found
 bit 2,a
 ld e,51
 jr z,key_found
 bit 3,a
 ld e,52
 jr z,key_found
 bit 4,a
 ld e,53
 jr z,key_found
 ld b,0xfb
 in a,(c)
 bit 0,a
 ld e,81
 jr z,key_found
 bit 3,a
 ld e,82
 jr z,key_found
 ld b,0x7f
 in a,(c)
 bit 0,a
 ld e,32
 jr z,key_found
 xor a
 ret
key_found:
 ld a,e
 ret

; Character rendering uses a bundled font and actual Spectrum screen layout.
clear_screen:
 xor a
 ld hl,16384
 ld de,16385
 ld bc,6143
 ld (hl),a
 ldir
 ld hl,22528
 ld de,22529
 ld bc,767
 ld (hl),0x47
 ldir
 ret

; Layout is a list of row,column,pointer records, ending with row=255.
draw_layout:
 ld a,(hl)
 cp 255
 ret z
 ld d,a
 inc hl
 ld e,(hl)
 inc hl
 ld c,(hl)
 inc hl
 ld b,(hl)
 inc hl
 push hl
 ld h,b
 ld l,c
 ld a,e
 cp 255
 jr z,layout_center
 call print_at
 jr layout_next
layout_center:
 call print_center
layout_next:
 pop hl
 jr draw_layout

 ; Pixel-centred single line: the font ink occupies x=2..6 in each cell.
 ; Odd text lengths require a four-pixel shift after character rendering.
print_center:
 push hl
 ld b,0
center_count:
 ld a,(hl)
 inc hl
 or a
 jr z,center_ready
 inc b
 jr center_count
center_ready:
 pop hl
 ld a,32
 sub b
 srl a
 ld e,a
 push af
 push de
 call print_at
 pop de
 pop af
 ret nc
 ; Move this entire character row four pixels right, across cell boundaries.
 push hl
 push bc
 ld a,d
 and 0x18
 or 0x40
 ld h,a
 ld a,d
 and 7
 rrca
 rrca
 rrca
 ld l,a
 ld b,8
center_scanline:
 push hl
 ld c,32
 ld e,0
center_shift_byte:
 ld a,(hl)
 ld d,a
 and 240
 rrca
 rrca
 rrca
 rrca
 or e
 ld (hl),a
 ld a,d
 and 15
 rlca
 rlca
 rlca
 rlca
 ld e,a
 inc hl
 dec c
 jr nz,center_shift_byte
 pop hl
 inc h
 djnz center_scanline
 pop bc
 pop hl
 ret

; HL text, D row, E column. LF returns to the original column.
print_at:
 ld a,e
 ld (print_left),a
print_loop:
 ld a,(hl)
 inc hl
 or a
 ret z
 cp 10
 jr z,print_newline
 call putchar
 inc e
 jr print_loop
print_newline:
 inc d
 ld a,(print_left)
 ld e,a
 jr print_loop
putchar:
 push af
 push bc
 push de
 push hl
 sub 32
 ld l,a
 ld h,0
 add hl,hl
 add hl,hl
 add hl,hl
 ld bc,font
 add hl,bc
 push hl
 ld a,d
 and 0x18
 or 0x40
 ld h,a
 ld a,d
 and 7
 rrca
 rrca
 rrca
 add a,e
 ld l,a
 pop de
 ld b,8
glyph_loop:
 ld a,(de)
 ld (hl),a
 inc de
 inc h
 djnz glyph_loop
 pop hl
 pop de
 pop bc
 pop af
 ret

; Attribute run, A colour, D row, E column, B count; preserves input registers.
color_row:
 push af
 push bc
 push de
 push hl
 ld c,a
 ld h,0
 ld l,d
 add hl,hl
 add hl,hl
 add hl,hl
 add hl,hl
 add hl,hl
 ld d,0
 add hl,de
 ld de,22528
 add hl,de
color_loop:
 ld (hl),c
 inc hl
 djnz color_loop
 pop hl
 pop de
 pop bc
 pop af
 ret

 ; Three digits, supporting scores through 500. DE is print position.
print_number:
 ld l,a
 ld h,0
print_word:
 ld bc,100
 ld a,48
number_hundreds:
 or a
 sbc hl,bc
 jr c,number_tens_start
 inc a
 jr number_hundreds
number_tens_start:
 add hl,bc
 call putchar
 inc e
 ld a,l
 ld b,48
number_tens:
 cp 10
 jr c,number_units
 sub 10
 inc b
 jr number_tens
number_units:
 ld c,a
 ld a,b
 call putchar
 inc e
 ld a,c
 add a,48
 call putchar
 ret

draw_question:
 call clear_screen
 call draw_answer_window
 ld hl,question_layout
 call draw_layout
 ld a,(song_category)
 add a,a
 ld e,a
 ld d,0
 ld hl,category_table
 add hl,de
 ld e,(hl)
 inc hl
 ld d,(hl)
 ex de,hl
 ld de,0x0202
 call print_at
 ld a,(question_index)
 inc a
 ld de,0x040b
 call print_number
 ld a,(round_length)
 ld de,0x040f
 call print_number
 call draw_score
 xor a
 ld (draw_index),a
draw_option:
 ld a,(draw_index)
 ld c,a
 add a,a
 add a,c
 add a,9
 ld d,a
 ld e,2
 ld a,c
 add a,49
 call putchar
 inc e
 inc e
 ld a,(draw_index)
 ld c,a
 ld b,0
 ld hl,options
 add hl,bc
 ld a,(hl)
 ld l,a
 ld h,0
 add hl,hl
 ld bc,title_table
 add hl,bc
 ld c,(hl)
 inc hl
 ld b,(hl)
 ld h,b
 ld l,c
 call print_at
 ld a,(draw_index)
 inc a
 ld (draw_index),a
 cp 4
 jr nz,draw_option
 ld d,0
 ld e,0
 ld b,32
 ld a,0x68
 call color_row
 ld d,2
 ld e,1
 ld b,30
 ld a,0x45
 call color_row
 ld d,6
 ld a,0x46
 call color_row
 ld d,7
 ld a,0x43
 call color_row
 ld d,9
 ld a,0x45
 call color_row
 inc d
 call color_row
 ld d,12
 ld a,0x46
 call color_row
 inc d
 call color_row
 ld d,15
 ld a,0x45
 call color_row
 inc d
 call color_row
 ld d,18
 ld a,0x46
 call color_row
 inc d
 call color_row
 ret

 ; Single answer panel, drawn in Spectrum bitmap memory with eight custom
 ; full-width border glyphs. Its sides stay cyan during answer highlighting.
draw_answer_window:
 ld d,8
 ld e,0
 ld a,96
 call putchar
 ld a,97
 ld e,1
 ld b,30
window_top:
 call putchar
 inc e
 djnz window_top
 ld a,98
 call putchar
 ld d,9
window_sides:
 ld e,0
 ld a,99
 call putchar
 ld e,31
 ld a,100
 call putchar
 ld e,0
 ld b,1
 ld a,0x45
 call color_row
 ld e,31
 call color_row
 inc d
 ld a,d
 cp 20
 jr nz,window_sides
 ld e,0
 ld a,101
 call putchar
 ld a,102
 ld e,1
 ld b,30
window_bottom:
 call putchar
 inc e
 djnz window_bottom
 ld a,103
 call putchar
 ld d,8
 ld e,0
 ld b,32
 ld a,0x45
 call color_row
 ld d,20
 call color_row
 ret

draw_score:
 ld hl,(score)
 ld de,0x041a
 jp print_word

mode: db 0
category: db 0
seed: dw 29533
lastkey: db 0
playing: db 0
question_index: db 0
round_length: db 0
current_song: db 0
song_category: db 0
score: dw 0
correct_count: db 0
option_pool: dw 0
pick_index: db 0
used_wrong: ds 250
chosen_option: db 0
was_correct: db 0
shuffle_base: dw 0
shuffle_index: db 0
draw_index: db 0
print_left: db 0
stream_ptr: dw 0
frames_left: dw 0
repeat_left: db 0
packed_end: dw 0
lz_length: db 0
ay_frame: ds 14
order: ds 50
options: ds 4

menu_layout:
 db 1,255
 dw msg_rewind
 db 2,255
 dw msg_subtitle
 db 4,255
 dw msg_tagline
 db 7,255
 dw msg_choose
 db 10,3
 dw msg_normal
 db 13,3
 dw msg_full
 db 16,255
 dw msg_random_order
 db 21,3
 dw msg_menu_rules
 db 22,3
 dw msg_menu_rules2
 db 255
question_layout:
 db 0,255
 dw msg_header
 db 4,2
 dw msg_question
 db 4,14
 dw msg_slash
 db 4,20
 dw msg_score
 db 6,2
 dw msg_name
 db 21,1
 dw msg_controls
 db 22,1
 dw msg_controls2
 db 255
results_layout:
 db 2,255
 dw msg_rewind
 db 5,9
 dw msg_round_complete
 db 9,11
 dw msg_final_score
 db 14,2
 dw msg_correct_label
 db 20,3
 dw msg_play_again
 db 22,3
 dw msg_return_menu
 db 255
category_table:
 dw cat_0,cat_1,cat_2,cat_3,cat_4,cat_5,cat_6,cat_7,cat_8,cat_9
cat_0: db 77,79,86,73,69,83,0
cat_1: db 80,79,80,32,38,32,82,79,67,75,0
cat_2: db 67,65,82,84,79,79,78,83,0
cat_3: db 84,86,32,83,69,82,73,69,83,0
cat_4: db 69,76,69,67,84,82,79,78,73,67,0
cat_5: db 71,79,84,72,73,67,0
cat_6: db 77,69,84,65,76,0
cat_7: db 86,73,68,69,79,32,71,65,77,69,83,0
cat_8: db 83,89,78,84,72,45,80,79,80,0
cat_9: db 68,65,78,67,69,0
msg_rewind: db 82,32,69,32,87,32,73,32,78,32,68,0
msg_subtitle: db 84,72,69,32,77,85,83,73,67,32,77,69,77,79,82,89,32,81,85,73,90,0
msg_tagline: db 53,48,32,84,85,78,69,83,46,32,84,69,83,84,32,89,79,85,82,32,77,69,77,79,82,89,46,0
msg_choose: db 67,72,79,79,83,69,32,89,79,85,82,32,77,73,88,0
msg_movies: db 49,32,32,32,77,79,86,73,69,83,0
msg_pop: db 50,32,32,32,80,79,80,32,38,32,82,79,67,75,0
msg_cartoons: db 51,32,32,32,67,65,82,84,79,79,78,83,0
msg_tv: db 52,32,32,32,84,86,32,83,69,82,73,69,83,0
msg_all: db 53,32,32,32,84,72,69,32,70,85,76,76,32,77,73,88,32,45,32,50,48,32,84,85,78,69,83,0
msg_menu_rules: db 76,73,83,84,69,78,46,32,80,73,67,75,32,49,45,52,46,32,83,67,79,82,69,32,43,49,48,46,0
msg_menu_rules2: db 82,32,82,69,80,76,65,89,83,46,32,78,79,32,84,73,77,69,32,76,73,77,73,84,46,0
msg_header: db 82,69,87,73,78,68,32,32,47,32,32,78,65,77,69,32,84,72,65,84,32,84,85,78,69,0
msg_question: db 81,85,69,83,84,73,79,78,0
msg_slash: db 47,0
msg_score: db 83,67,79,82,69,0
msg_name: db 78,65,77,69,32,84,72,65,84,32,84,85,78,69,33,32,32,32,32,32,32,32,32,32,32,32,32,32,32,0
msg_playing: db 80,76,65,89,73,78,71,46,46,46,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,0
msg_paused: db 80,65,85,83,69,68,32,45,32,83,80,65,67,69,32,84,79,32,82,69,83,85,77,69,32,32,32,32,32,0
msg_finished: db 70,73,78,73,83,72,69,68,32,45,32,82,32,84,79,32,72,69,65,82,32,65,71,65,73,78,32,32,32,0
msg_controls: db 49,45,52,32,65,78,83,87,69,82,32,32,32,82,32,82,69,80,76,65,89,32,32,32,32,32,32,32,32,32,32,0
msg_controls2: db 83,80,65,67,69,32,80,65,85,83,69,47,80,76,65,89,32,32,32,81,32,77,69,78,85,32,32,32,32,32,32,0
msg_correct: db 67,79,82,82,69,67,84,33,32,43,49,48,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,0
msg_wrong: db 87,82,79,78,71,32,45,32,71,82,69,69,78,32,73,83,32,84,72,69,32,65,78,83,87,69,82,32,32,0
msg_next: db 83,80,65,67,69,32,78,69,88,84,32,81,85,69,83,84,73,79,78,32,32,32,32,32,32,32,32,32,32,32,0
msg_back: db 81,32,66,65,67,75,32,84,79,32,77,69,78,85,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,0
msg_round_complete: db 82,79,85,78,68,32,67,79,77,80,76,69,84,69,33,0
msg_final_score: db 89,79,85,82,32,83,67,79,82,69,0
msg_correct_label: db 67,79,82,82,69,67,84,0
msg_of: db 79,70,0
msg_perfect: db 80,69,82,70,69,67,84,33,0
msg_nice: db 78,73,67,69,32,80,76,65,89,73,78,71,46,0
msg_play_again: db 83,80,65,67,69,32,80,76,65,89,32,84,72,73,83,32,82,79,85,78,68,32,65,71,65,73,78,0
msg_return_menu: db 81,32,32,66,65,67,75,32,84,79,32,77,69,78,85,0
msg_intro: db 80,82,69,83,83,32,83,80,65,67,69,32,84,79,32,83,84,65,82,84,0
msg_normal: db 49,32,32,32,78,79,82,77,65,76,32,45,32,50,53,32,82,65,78,68,79,77,32,84,85,78,69,83,0
msg_full: db 50,32,32,32,70,85,76,76,32,32,32,45,32,65,76,76,32,53,48,32,84,85,78,69,83,0
msg_random_order: db 65,32,68,73,70,70,69,82,69,78,84,32,77,73,88,32,69,86,69,82,89,32,84,73,77,69,0
font:
 mdat "font.bin"
 include "songs.inc"
end_code:
 assert $ < 0xbc00

msg_try_mix: db 84,82,89,32,65,78,79,84,72,69,82,32,77,73,88,33,0
msg_know_tunes: db 89,79,85,32,75,78,79,87,32,89,79,85,82,32,84,85,78,69,83,46,0
