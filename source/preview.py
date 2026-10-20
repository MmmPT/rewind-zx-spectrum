"""Record the native game loop and synthesise its captured AY output."""
from pathlib import Path
import subprocess,wave,json
import numpy as np
from scipy import signal
from verify import Harness,S,P

def render_audio(frames,path):
 sr=88200;count=sr//50;clock=1773400
 vol=np.array([0,.009994,.01445,.02106,.03070,.04555,.06450,.10736,.12659,.20499,.29221,.37284,.49253,.63532,.80558,1.0])
 phase=np.zeros(3);noise_phase=0.;lfsr=0x1ffff;parts=[]
 for r in frames:
  noise=np.empty(count);noiseperiod=max(1,r[6]);step=clock/(16*noiseperiod*sr)
  for j in range(count):
   noise_phase+=step
   while noise_phase>=1:
    feedback=(lfsr^(lfsr>>3))&1;lfsr=(lfsr>>1)|(feedback<<16);noise_phase-=1
   noise[j]=lfsr&1
  out=np.zeros(count)
  for c in range(3):
   per=max(1,r[2*c]+256*r[2*c+1]);step_t=clock/(16*per*sr)
   ph=phase[c]+np.arange(count)*step_t
   tone=(np.mod(ph,1)<.5).astype(float);phase[c]=(phase[c]+count*step_t)%1
   gate=(np.ones(count) if r[7]&(1<<c) else tone)*(np.ones(count) if r[7]&(1<<(c+3)) else noise)
   out+=gate*vol[r[8+c]&15]
  parts.append(out)
 x=np.concatenate(parts);x=signal.sosfilt(signal.butter(2,35,fs=sr,btype='highpass',output='sos'),x)
 x=signal.resample_poly(x,1,2);x*=.86/max(abs(x).max(),1e-6)
 with wave.open(str(path),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes((x*32767).astype('<i2').tobytes())

def main():
 h=Harness();h.boot(intro=True);last=None;imagebytes=None;audio=[]
 movie=P/'preview_silent.mp4'
 ff=subprocess.Popen(['ffmpeg','-nostdin','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','768x576','-r','25','-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(movie)],stdin=subprocess.PIPE)
 for f in range(1250):
  key={50:32,250:49,310:32,360:32,450:82,650:81,750:50,1150:81}.get(f)
  if f==550:
   options=list(h.m.memory[S['options']:S['options']+4]);key=49+options.index(h.get('current_song'))
  if f==1050:
   options=list(h.m.memory[S['options']:S['options']+4]);key=49+next(i for i,x in enumerate(options) if x!=h.get('current_song'))
  h.keys=set() if key is None else {key}
  h.m.ticks_to_stop=4;h.m.run();assert h.m.halted
  h.m.on_handle_active_int();h.run_to(S['main_loop'])
  audio.append(h.regs.copy())
  if f%2==0:
   screen=bytes(h.m.memory[16384:23296])
   if screen!=last:
    imagebytes=h.image().resize((768,576),0).tobytes();last=screen
   ff.stdin.write(imagebytes)
 ff.stdin.close();assert ff.wait()==0
 render_audio(audio,P/'preview_audio.wav')
 subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-i',str(movie),'-i',str(P/'preview_audio.wav'),'-c:v','copy','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(P/'Rewind_Gameplay.mp4')],check=True)
 movie.unlink();(P/'preview_audio.wav').unlink()
 print('preview seconds',len(audio)/50)
if __name__=='__main__':main()
