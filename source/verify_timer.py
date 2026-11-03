"""Timing/scoring regressions using both clock jumps and native IM2 frames."""
import struct,json
from verify import Harness,S,P,glyph,expected_glyph,check_attributes
from PIL import Image

def clock_advance(h,frames):
 now=(h.word('frame_clock')+frames)&65535
 h.m.set_memory_block(S['frame_clock'],struct.pack('<H',now));h.call('timer_tick')
def right(h):return 49+list(h.m.memory[S['options']:S['options']+4]).index(h.get('current_song'))
def start():
 h=Harness();h.boot();h.action(49);return h

def test():
 # Every second maps to exactly five fewer points, including the last second.
 for seconds in [0,1,5,9,19]:
  h=start();clock_advance(h,seconds*50)
  assert h.get('question_seconds')==20-seconds
  assert h.get('question_points')==100-5*seconds
  h.action(right(h));assert h.word('score')==100-5*seconds and h.get('correct_count')==1
  if seconds==5:h.image().resize((768,576),Image.Resampling.NEAREST).save(P/'Rewind_Fast_Answer.png')
 # Partial seconds and delayed iterations must not create or lose time.
 h=start();clock_advance(h,49);assert h.get('question_seconds')==20
 clock_advance(h,1);assert h.get('question_seconds')==19
 clock_advance(h,376);assert h.get('question_seconds')==12 and h.word('timer_frames')==26
 # Correct modular subtraction across the 16-bit PAL frame counter wrap.
 h=start();h.m.set_memory_block(S['frame_clock'],struct.pack('<H',65520));h.m.set_memory_block(S['timer_last_clock'],struct.pack('<H',65520))
 clock_advance(h,50);assert h.get('question_seconds')==19
 # Replay does not refresh the timer or points; pausing affects music only.
 h=start();clock_advance(h,250);h.action(82)
 assert (h.get('question_seconds'),h.get('question_points'))==(15,75)
 h.action(32);assert not h.get('playing');clock_advance(h,50)
 assert (h.get('question_seconds'),h.get('question_points'))==(14,70)
 h.action(32);assert h.get('playing')
 clock_advance(h,50);assert h.get('question_seconds')==13
 h.image().resize((768,576),Image.Resampling.NEAREST).save(P/'Rewind_Timer_Question.png')
 # Music finishing early must not freeze the deadline.
 h=start();h.m.memory[S['playing']]=0;clock_advance(h,1000)
 assert h.get('mode')==2 and h.get('question_seconds')==0 and h.get('question_points')==0
 assert h.word('score')==0 and h.get('correct_count')==0 and h.get('chosen_option')==255
 assert not h.get('playing') and all(h.regs[r]==0 for r in (8,9,10))
 correct=list(h.m.memory[S['options']:S['options']+4]).index(h.get('current_song'))
 for i,row in enumerate([9,12,15,18]):
  a=h.m.memory[22528+row*32+2]
  assert a==0x44 if i==correct else a in (0x45,0x46)
 for col in range(6,26):assert glyph(h,5,col)==bytes(8)
 h.image().resize((768,576),Image.Resampling.NEAREST).save(P/'Rewind_Time_Up.png')
 clock_advance(h,100);assert h.get('mode')==2 and h.word('score')==0
 h.action(32);assert h.get('mode')==1 and h.get('question_seconds')==20
 # A wrong answer and menu exit cannot earn points or consume the next timer.
 wrong=next(49+i for i,x in enumerate(h.m.memory[S['options']:S['options']+4]) if x!=h.get('current_song'))
 h.action(wrong);assert h.word('score')==0
 h.action(81);clock_advance(h,3000);assert h.get('mode')==0 and not h.get('playing')
 # Exercise the actual interrupt handler and main loop for the full deadline.
 h=start();h.m.pc=S['main_loop'];h.m.iff1=True;h.m.iff2=True
 before=h.word('frame_clock')
 for i in range(1000):
  h.keys=set();h.m.ticks_to_stop=4;h.m.run();assert h.m.halted
  assert h.m.on_handle_active_int()
  h.run_to(S['main_loop'])
  if i==48:assert h.get('question_seconds')==20
  if i==49:assert h.get('question_seconds')==19
  if i==998:assert h.get('mode')==1 and h.get('question_seconds')==1
 assert h.word('frame_clock')==(before+1000)&65535
 assert h.get('mode')==2 and h.get('question_seconds')==0
 # Four-digit 5000 score display at both the HUD and results, without overflow.
 h=start();h.m.set_memory_block(S['score'],struct.pack('<H',5000));h.call('draw_score')
 for col,c in zip(range(26,30),'5000'):assert glyph(h,4,col)==expected_glyph(c)
 h.call('results')
 for col,c in zip(range(14,18),'5000'):assert glyph(h,11,col)==expected_glyph(c)
 result={'native_IM2_timeout_after_1000_frames':True,'deadline_20_seconds_at_50_Hz':True,'points_100_to_5_in_five_point_steps':True,'timeout_zero_points_and_correct_answer_revealed':True,'replay_and_music_pause_do_not_reset_or_stop_clock':True,'timer_continues_after_excerpt_finishes':True,'frame_counter_wrap_and_delayed_updates':True,'5000_point_HUD_and_results':True,'new_question_resets_timer_and_feedback_stops_timer':True}
 (P/'timer_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':test()
