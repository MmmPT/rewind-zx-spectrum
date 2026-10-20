from pathlib import Path
import pickle,json,struct
import z80
from PIL import Image
P=Path(__file__).resolve().parent
S=pickle.loads((P/'symbols.pkl').read_bytes())
class Harness:
 def __init__(self):
  self.m=z80.Z80Machine();self.m.set_memory_block(32768,(P/'game.bin').read_bytes());self.m.pc=32768;self.m.set_memory_block(16384,(P/'Rewind_Loading.scr').read_bytes())
  self.banks={k:(P/f'bank{k}.bin').read_bytes() for k in [0,1,3,4]};self.keys=set();self.writes=[];self.frames=[];self.regs=[0]*14;self.reg=0
  self.m.set_output_callback(self.out);self.m.set_input_callback(self.inp)
 def out(self,port,v):
  if port==0x7ffd:
   bank=v&7;self.m.set_memory_block(49152,self.banks.get(bank,bytes(16384)))
  elif port==0xfffd:self.reg=v
  elif port==0xbffd:
   self.writes.append((self.reg,v))
   if self.reg<14:self.regs[self.reg]=v
   if self.reg==13:self.frames.append(bytes(self.regs))
 def inp(self,port):
  rows={49:(0xf7,0),50:(0xf7,1),51:(0xf7,2),52:(0xf7,3),53:(0xf7,4),81:(0xfb,0),82:(0xfb,3),32:(0x7f,0)}
  v=255
  if port&255==254:
   for key in self.keys:
    r,b=rows[key]
    if not ((port>>8)&(~r&255)):v&=~(1<<b)
  return v
 def get(self,name):return self.m.memory[S[name]]
 def word(self,name):return int.from_bytes(self.m.memory[S[name]:S[name]+2],'little')
 def run_to(self,addr,limit=500):
  self.m.set_breakpoint(addr)
  for _ in range(limit):
   self.m.ticks_to_stop=100000;self.m.run()
   if self.m.pc==addr:break
  else:raise AssertionError(('timeout',hex(self.m.pc),hex(addr)))
  self.m.clear_breakpoint(addr)
 def boot(self,intro=False):
  self.run_to(S['main_loop'])
  assert self.get('mode')==4
  if not intro:
   self.action(32)
   self.m.pc=S['main_loop'];self.m.iff1=True;self.m.iff2=True

 def call(self,label,a=None):
  self.m.iff1=False;self.m.iff2=False;self.m.halted=False
  self.m.sp=0xbbfe;self.m.set_memory_block(0xbbfe,struct.pack('<H',0x7000))
  self.m.pc=S[label]
  if a is not None:self.m.a=a
  self.run_to(0x7000)
  assert self.m.sp==0xbc00
 def action(self,key):self.call('dispatch',key)
 def image(self):
  mem=self.m.memory;im=Image.new('RGB',(256,192));pix=im.load()
  pal=[(0,0,0),(0,0,205),(205,0,0),(205,0,205),(0,205,0),(0,205,205),(205,205,0),(205,205,205)]
  bright=[(0,0,0),(0,0,255),(255,0,0),(255,0,255),(0,255,0),(0,255,255),(255,255,0),(255,255,255)]
  for y in range(192):
   offset=((y&192)<<5)|((y&7)<<8)|((y&56)<<2)
   for xb in range(32):
    b=mem[16384+offset+xb];a=mem[22528+(y//8)*32+xb];p=bright if a&64 else pal
    for bit in range(8):pix[xb*8+bit,y]=p[(a&7) if b&(128>>bit) else ((a>>3)&7)]
  return im

def check_attributes(h):
 for row,colour in [(9,0x45),(12,0x46),(15,0x45),(18,0x46)]:
  for y in [row,row+1]:
   assert bytes(h.m.memory[22528+y*32+1:22528+y*32+31])==bytes([colour])*30,('continuation colour',row,y)

def glyph(h,row,col):
 return bytes(h.m.memory[16384+(((row*8+y)&192)<<5)+(((row*8+y)&7)<<8)+(((row*8+y)&56)<<2)+col] for y in range(8))

def expected_glyph(char):
 return (P/'font.bin').read_bytes()[(ord(char)-32)*8:(ord(char)-31)*8]

def test():
 cat=json.loads((P/'answers_catalogue.json').read_text());assert len(cat)==250
 assert len(set(x['title'].upper() for x in cat))==250
 for name in {x['category'] for x in cat}:assert sum(x['category']==name for x in cat)==25
 h=Harness();h.boot();assert h.get('mode')==0 and h.get('playing')==0
 h.image().resize((768,576),Image.Resampling.NEAREST).save(P/'Rewind_Menu.png')
 # Menu has two selectable modes and remains silent for at least a minute.
 for key in [51,52,53]:h.action(key);assert h.get('mode')==0
 h.frames.clear();before=len(h.writes)
 for _ in range(3000):h.call('music_tick')
 assert not h.frames and len(h.writes)==before and not h.get('playing')
 assert all(h.regs[r]==0 for r in (8,9,10))
 # Actual matrix and HALT/IM2 execution, including held-key debounce.
 for key in [49,50,51,52,53,81,82,32]:
  h.keys={key};h.call('read_key');assert h.m.a==key
 h.keys=set();h.call('read_key');assert h.m.a==0
 h.action(81);h.m.pc=S['main_loop'];h.m.iff1=True;h.m.iff2=True
 for key,mode,playing in [(49,1,1),(None,1,1),(32,1,0),(None,1,0),(32,1,1),(None,1,1),(81,0,0),(None,0,0),(50,1,1)]:
  h.keys=set() if key is None else {key};h.m.ticks_to_stop=4;h.m.run();assert h.m.halted
  h.m.on_handle_active_int();h.run_to(S['main_loop']);assert h.get('mode')==mode and h.get('playing')==playing
 h.keys={32}
 for _ in range(4):
  h.m.ticks_to_stop=4;h.m.run();h.m.on_handle_active_int();h.run_to(S['main_loop']);assert not h.get('playing')
 # Ensure 25-of-50 sampling varies, without repetition or fixed category order.
 orders=set();subsets=set();coverage=set()
 for seed in range(1,41):
  h.m.set_memory_block(S['seed'],struct.pack('<H',seed*997));h.action(81);h.action(49)
  order=tuple(h.m.memory[S['order']:S['order']+25]);assert len(set(order))==25 and max(order)<50
  orders.add(order);subsets.add(tuple(sorted(order)));coverage.update(order)
 assert len(orders)==40 and len(subsets)>35 and coverage==set(range(50))
 # Both modes through to results, full exact AY decode and 500-point scoring.
 seen50=[]
 for mode,length in [(0,25),(1,50)]:
  h.action(81);h.action(49+mode);assert h.get('round_length')==length
  seen=[];used=set();score=0
  for q in range(length):
   assert h.get('mode')==1 and h.get('question_index')==q
   song=h.get('current_song');seen.append(song);options=list(h.m.memory[S['options']:S['options']+4])
   assert len(set(options))==4 and options.count(song)==1
   assert all(cat[x]['category']==cat[song]['category'] for x in options)
   wrong=set(options)-{song};assert not used.intersection(wrong);used.update(wrong)
   check_attributes(h)
   if mode==0 and q==0:
    h.image().resize((768,576),Image.Resampling.NEAREST).save(P/'Rewind_Question.png')
    h.call('music_tick');left=h.word('frames_left');h.action(32)
    for _ in range(3):h.call('music_tick')
    assert h.word('frames_left')==left and not h.get('playing')
    h.action(32);h.call('music_tick');assert h.word('frames_left')==left-1
   if mode==1:
    h.action(82);h.frames.clear();raw=(P/'music'/f'{song:02d}.bin').read_bytes()
    for _ in range(len(raw)//14):h.call('music_tick')
    assert b''.join(h.frames)==raw,('approved AY mismatch',song)
    h.call('music_tick');assert h.get('playing')==0
    seen50.append(song)
   right=mode==1 or q%2==0;choice=options.index(song) if right else next(i for i,x in enumerate(options) if x!=song)
   h.action(49+choice);score+=10 if right else 0;assert h.word('score')==score and h.get('mode')==2
   h.action(32)
  assert len(set(seen))==length and h.get('mode')==3
  if mode==1:
   assert score==500 and h.word('score')==500
   for col,char in zip([14,15,16],'500'):assert glyph(h,11,col)==expected_glyph(char)
   h.image().resize((768,576),Image.Resampling.NEAREST).save(P/'Rewind_Results.png')
  h.action(32);assert h.get('mode')==1 and h.word('score')==0
 assert sorted(seen50)==list(range(50))
 # Explicit high-ID (>127) pointer and two-line text regression.
 long=[a for a in cat if len(a['title'])>25];assert len(long)>=4
 chosen=[long[0],long[1],next(a for a in long if a['id']>=128),next(a for a in reversed(long) if a['id']!=next(x['id'] for x in long if x['id']>=128))]
 h.m.set_memory_block(S['options'],bytes(a['id'] for a in chosen));h.call('draw_question');check_attributes(h)
 for row,a in zip([9,12,15,18],chosen):assert glyph(h,row,4)==expected_glyph(a['title'][0].upper())
 # Capture a real question with coherent, unique cartoon answers and wrapped text.
 for seed in range(1,100):
  h.m.set_memory_block(S['seed'],struct.pack('<H',seed*61));h.action(81);h.action(49)
  options=list(h.m.memory[S['options']:S['options']+4])
  if sum(len(cat[x]['title'])>25 for x in options)>=1:
   h.image().resize((768,576),Image.Resampling.NEAREST).save(P/'Rewind_Wrapped_Answers.png');break
 else:raise AssertionError('no wrapped real question found')
 # Tape payload ordering and parity.
 tap=(P/'Rewind_Quiz_128K.tap').read_bytes();pos=0;blocks=[]
 while pos<len(tap):
  n=int.from_bytes(tap[pos:pos+2],'little');pos+=2;b=tap[pos:pos+n];pos+=n
  chk=0
  for v in b:chk^=v
  assert len(b)==n and chk==0;blocks.append(b)
 assert len(blocks)==9
 assert blocks[3][1:-1]==(P/'game.bin').read_bytes()
 assert blocks[4][1:-1]==(P/'Rewind_Loading.scr').read_bytes()
 for b,k in zip(blocks[5:],[0,1,3,4]):assert b[1:-1]==(P/f'bank{k}.bin').read_bytes()
 result={'50_approved_AY_streams_byte_identical':True,'menu_silent_for_3000_ticks':True,'two_menu_modes_only':True,'normal_25_random_unique_from_50':True,'full_50_shuffled_unique':True,'40_distinct_tested_orders_and_all_50_reached':True,'250_unique_answer_labels_25_per_category':True,'no_repeated_wrong_alternative_in_each_round':True,'same_category_options_and_one_correct':True,'two_line_answers_keep_colour':True,'high_answer_ID_pointers':True,'500_point_scoring_and_display':True,'pause_resume_replay_menu_restart':True,'keyboard_IM2_HALT_debounce':True,'TAP_payloads_checksums':True,'scope':'Z80 CPU with simulated paging and keyboard; full ROM boot verified separately.'}
 (P/'verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':test()
