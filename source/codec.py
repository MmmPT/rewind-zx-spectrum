from collections import defaultdict,deque

def compress(data):
 positions=defaultdict(lambda:deque(maxlen=128));out=bytearray();literals=bytearray();i=0
 def flush():
  if literals:out.append(len(literals)-1);out.extend(literals);literals.clear()
 while i<len(data):
  key=data[i:i+3];best=0;offset=0
  if len(key)==3:
   for p in reversed(positions[key]):
    n=3
    while n<130 and i+n<len(data) and data[p+n]==data[i+n]:n+=1
    if n>best:best=n;offset=i-p
    if n==130:break
  if best>=4:
   flush();out.append(128+best-3);out+=offset.to_bytes(2,'little');advance=best
  else:
   literals.append(data[i]);advance=1
   if len(literals)==128:flush()
  for p in range(i,i+advance):positions[data[p:p+3]].append(p)
  i+=advance
 flush();return bytes(out)

def decompress(data):
 out=bytearray();i=0
 while i<len(data):
  token=data[i];i+=1
  if token<128:
   n=token+1;out+=data[i:i+n];i+=n
  else:
   n=(token&127)+3;offset=int.from_bytes(data[i:i+2],'little');i+=2
   assert 0<offset<=len(out)
   for _ in range(n):out.append(out[-offset])
 return bytes(out)

def delta_encode(raw):
 last=bytes(14);out=bytearray();run=0
 for i in range(0,len(raw),14):
  row=raw[i:i+14]
  if row==last:
   run+=1
   if run==127:out.append(0x80|run);run=0
  else:
   if run:out.append(0x80|run);run=0
   mask=sum(1<<j for j in range(14) if row[j]!=last[j]);out+=mask.to_bytes(2,'big');out+=bytes(row[j] for j in range(14) if mask>>j&1);last=row
 if run:out.append(0x80|run)
 return bytes(out)
