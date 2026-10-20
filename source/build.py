from pathlib import Path
import json,struct,subprocess,shutil
P=Path(__file__).resolve().parent
# Approved AY streams are copied here; subsequent builds are self contained.
from codec import compress, decompress, delta_encode
SONGS=json.loads((P/'songs_manifest.json').read_text())
CATEGORIES=list(dict.fromkeys(x['category'] for x in SONGS))
FONT={
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],
'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],
'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['11111','00100','00100','00100','00100','00100','11111'],
'J':['00111','00010','00010','00010','10010','10010','01100'],
'K':['10001','10010','10100','11000','10100','10010','10001'],
'L':['10000','10000','10000','10000','10000','10000','11111'],
'M':['10001','11011','10101','10101','10001','10001','10001'],
'N':['10001','11001','11001','10101','10011','10011','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],
'P':['11110','10001','10001','11110','10000','10000','10000'],
'Q':['01110','10001','10001','10001','10101','10010','01101'],
'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],
'V':['10001','10001','10001','10001','10001','01010','00100'],
'W':['10001','10001','10001','10101','10101','11011','10001'],
'X':['10001','10001','01010','00100','01010','10001','10001'],
'Y':['10001','10001','01010','00100','00100','00100','00100'],
'Z':['11111','00001','00010','00100','01000','10000','11111'],
'0':['01110','10011','10101','10101','11001','10001','01110'],
'1':['00100','01100','00100','00100','00100','00100','01110'],
'2':['01110','10001','00001','00010','00100','01000','11111'],
'3':['11110','00001','00001','01110','00001','00001','11110'],
'4':['00010','00110','01010','10010','11111','00010','00010'],
'5':['11111','10000','10000','11110','00001','00001','11110'],
'6':['01110','10000','10000','11110','10001','10001','01110'],
'7':['11111','00001','00010','00100','01000','01000','01000'],
'8':['01110','10001','10001','01110','10001','10001','01110'],
'9':['01110','10001','10001','01111','00001','00001','01110'],
' ':['00000']*7,'-':['00000','00000','00000','11111','00000','00000','00000'],
'.':['00000']*5+['00100','00100'],':':['00000','00100','00100','00000','00100','00100','00000'],
'/':['00001','00001','00010','00100','01000','10000','10000'],
'&':['01100','10010','10100','01000','10101','10010','01101'],
'!':['00100']*5+['00000','00100'],'?':['01110','10001','00001','00010','00100','00000','00100'],
'+':['00000','00100','00100','11111','00100','00100','00000'],
'>':['10000','01000','00100','00010','00100','01000','10000'],
'[':['01110','01000','01000','01000','01000','01000','01110'],
']':['01110','00010','00010','00010','00010','00010','01110'],
}
FONT[chr(39)]=['00100','00100','01000','00000','00000','00000','00000']
FONT[chr(44)]=['00000','00000','00000','00000','00100','00100','01000']
font=bytes(v for c in range(32,96) for v in [*(int(r,2)<<2 for r in FONT.get(chr(c),FONT['?'])),0])
# Rounded answer-window border glyphs, codes 96..103, at full cell width.
font+=bytes([
 0,0,15,16,32,32,32,32,
 0,0,255,0,0,0,0,0,
 0,0,240,8,4,4,4,4,
 32,32,32,32,32,32,32,32,
 4,4,4,4,4,4,4,4,
 32,32,32,32,16,15,0,0,
 0,0,0,0,0,255,0,0,
 4,4,4,4,8,240,0,0])
(P/'font.bin').write_bytes(font)
# Delta encode approved register bytes, then LZ-pack. Unpack one compact stream
# into bank 7 on song selection; the original real-time delta reader stays intact.
banks={k:bytearray() for k in [0,1,3,4]};manifest=[];asm=['song_table:']
entries=SONGS
for item in entries:
 i=item['id'];target=P/'music'/f'{i:02d}.bin'
 raw=target.read_bytes();assert len(raw)%14==0
 delta=delta_encode(raw);packed=compress(delta);assert decompress(packed)==delta
 assert len(packed)<=8192 and len(delta)<=16384
 k=min((k for k,v in banks.items() if len(v)+len(packed)<=16384),key=lambda k:len(banks[k]))
 address=49152+len(banks[k]);banks[k]+=packed
 asm += [f' db {k+16}',f' dw {address},{len(raw)//14},{len(packed)}']
 manifest.append(dict(item,frames=len(raw)//14,bank=k,address=address,packed_bytes=len(packed),delta_bytes=len(delta),raw_bytes=len(raw)))
for k,v in banks.items():(P/f'bank{k}.bin').write_bytes(v+bytes(16384-len(v)))
# 50 recorded answers + 200 text alternatives: all IDs fit one byte.
extra=json.loads((P/'extra_answers.json').read_text())
answers=[dict(id=x['id'],title=x['title'],category=x['category'],recorded=True) for x in SONGS]
pools=[]
for category,name in enumerate(CATEGORIES):
 pool=[x['id'] for x in SONGS if x['category']==name]
 for title in extra[name]:
  ix=len(answers);answers.append(dict(id=ix,title=title,category=name,recorded=False));pool.append(ix)
 assert len(pool)==25
 pools.append(pool)
assert len(answers)==250
assert len(set(a['title'].upper() for a in answers))==250
asm+=['answer_pool_table:']+[f' dw answer_pool_{i}' for i in range(10)]
for i,pool in enumerate(pools):asm+=[f'answer_pool_{i}: db '+','.join(map(str,pool))]
asm+=['title_table:']+[f' dw title_{i}' for i in range(len(answers))]
import textwrap
for item in answers:
 i,title=item['id'],item['title']
 lines=textwrap.wrap(title.upper(),25)
 assert len(lines)<=2,(title,lines)
 encoded=b'\n'.join(x.encode() for x in lines)+b'\0'
 asm+=[f'title_{i}: db '+','.join(str(x) for x in encoded)]
(P/'answers_catalogue.json').write_text(json.dumps(answers,indent=2))
(P/'songs.inc').write_text('\n'.join(asm)+'\n')
(P/'catalogue.json').write_text(json.dumps(manifest,indent=2))
subprocess.run([shutil.which('pyz80') or str(Path.home()/'.local/bin/pyz80'),'--obj='+str(P/'game.bin'),'--exportfile='+str(P/'symbols.pkl'),'--mapfile='+str(P/'game.map'),str(P/'game.asm')],check=True)
code=(P/'game.bin').read_bytes();assert len(code)<0x3c00
# Extended 128K SNA. PC is in the extension, not pushed onto the stack.
head=bytearray(27);head[0]=0xbe;struct.pack_into('<H',head,23,0xbc00);head[25]=1
scr=(P/'Rewind_Loading.scr').read_bytes();assert len(scr)==6912
ram={k:bytearray(16384) for k in range(8)};ram[2][:len(code)]=code;ram[5][:6912]=scr
for k in banks:ram[k][:]=(P/f'bank{k}.bin').read_bytes()
sna=head+ram[5]+ram[2]+ram[0]+struct.pack('<HBB',32768,16,0)
for k in [1,3,4,6,7]:sna+=ram[k]
assert len(sna)==131103;(P/'Rewind_Quiz_128K.sna').write_bytes(sna)
# A BASIC entry followed by resident code and three raw ROM-loader bank blocks.
def block(flag,data):
 b=bytes([flag])+data;v=0
 for x in b:v^=x
 b+=bytes([v]);return struct.pack('<H',len(b))+b
def header(t,n,size,p1,p2):return block(0,bytes([t])+n.encode().ljust(10,b' ')[:10]+struct.pack('<HHH',size,p1,p2))
def number(n):return str(n).encode()+bytes([14,0,0,n&255,n>>8,0])
def line(n,s):s+=b'\r';return struct.pack('>H',n)+struct.pack('<H',len(s))+s
# Tape-specific entry is at 32771 (the second JP in game.asm).
basic=line(10,b'\xfd '+number(32767))+line(20,b'\xef ""\xaf')+line(30,b'\xf9 \xc0 '+number(32771))
tap=header(0,'REWIND',len(basic),10,len(basic))+block(255,basic)+header(3,'REWIND128',len(code),32768,32768)+block(255,code)
tap+=block(255,scr)
for k in banks:tap+=block(255,(P/f'bank{k}.bin').read_bytes())
(P/'Rewind_Quiz_128K.tap').write_bytes(tap)
print(json.dumps({'core_bytes':len(code),'music_bytes':sum(len(x) for x in banks.values()),'bank_usage':{k:len(v) for k,v in banks.items()},'songs':50,'answer_labels':250,'menu_music':None,'codec':'LZ over delta AY','tap_bytes':len(tap)}))
