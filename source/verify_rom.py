"""Load the actual TAP through a 128K ROM and validate bank payloads."""
from pathlib import Path
import json,pickle,subprocess,shutil
from skoolkit.snapshot import Snapshot
P=Path(__file__).resolve().parent
S=pickle.loads((P/'symbols.pkl').read_bytes())
exe=shutil.which('tap2sna.py') or str(Path.home()/'.local/bin/tap2sna.py')
out=P/'rom_boot_test.z80'
r=subprocess.run([exe,'-c','machine=128','-c','finish-tape=1','--start',str(S['main_loop']),str(P/'Rewind_Quiz_128K.tap'),str(out)],capture_output=True,text=True,check=True)
assert 'Tape finished' in r.stdout and 'PC='+str(S['main_loop']) in r.stdout
s=Snapshot.get(str(out));assert s.pc==S['main_loop'] and s.im==2 and s.sp==0xbc00
for k in [0,1,3,4]:assert bytes(s.memory.banks[k])==(P/f'bank{k}.bin').read_bytes()
# The loader must preserve the illustration; the last row changes to SPACE.
scr=(P/'Rewind_Loading.scr').read_bytes()
for y in range(184):
 off=((y&192)<<5)|((y&7)<<8)|((y&56)<<2)
 assert bytes(s.memory.banks[5][off:off+32])==scr[off:off+32]
assert bytes(s.memory.banks[5][6144:6144+23*32])==scr[6144:6144+23*32]
# Parse the independently packaged SNA and check its entry point and bank order.
sna=Snapshot.get(str(P/'Rewind_Quiz_128K.sna'));assert sna.pc==32768 and sna.out7ffd==16
assert bytes(sna.memory.banks[5][:6912])==scr
for k in [0,1,3,4]:assert bytes(sna.memory.banks[k])==(P/f'bank{k}.bin').read_bytes()
code=(P/'game.bin').read_bytes();assert bytes(sna.memory.banks[2][:len(code)])==code
result={'128K_ROM_TAP_boot_reaches_intro':True,'all_four_music_banks_match':True,'IM2_and_stack_initialized':True,'128K_SNA_parses_and_bank_order_matches':True,'tape_mode':'ROM calls with SkoolKit fast loading; no physical tape or hardware test'}
(P/'rom_verification.json').write_text(json.dumps(result,indent=2));(P/'rom_boot_log.txt').write_text(r.stdout)
print(json.dumps(result,indent=2))
