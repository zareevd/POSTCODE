from pathlib import Path
import struct
s=Path('output/make_deck.py').read_text(encoding='utf-8'); exec(s[:s.index('with zipfile.ZipFile(out')])
f=Path('C:/Windows/Fonts/arial.ttf').read_bytes()
u16=lambda p:struct.unpack_from('>H',f,p)[0]
u32=lambda p:struct.unpack_from('>I',f,p)[0]
tables={f[p:p+4].decode():u32(p+8) for p in range(12,12+16*u16(4),16)}
c=tables['cmap']; off=None
for p in range(c+4,c+4+8*u16(c+2),8):
 t=c+u32(p+4)
 if u16(t)==4: off=t
n=u16(off+6)//2; end=off+14; start=end+2*n+2; delta=start+2*n; ranges=delta+2*n
mapping={}
for ch in set(''.join(a[-1] for bg,els in slides for a in els)):
 code=ord(ch); gid=0
 for i in range(n):
  if u16(start+2*i)<=code<=u16(end+2*i):
   d=u16(delta+2*i); rr=u16(ranges+2*i)
   gid=(code+d)&65535 if rr==0 else u16(ranges+2*i+rr+2*(code-u16(start+2*i)))
   if rr and gid: gid=(gid+d)&65535
   break
 mapping[code]=gid
objs=[]
def obj(b):
 objs.append(b.encode() if isinstance(b,str) else b); return len(objs)
def stream(b,extra=''):
 return obj(f'<< /Length {len(b)} {extra} >>\nstream\n'.encode()+b+b'\nendstream')
fontfile=stream(f,f'/Length1 {len(f)}')
fd=obj(f'<< /Type /FontDescriptor /FontName /Arial /Flags 32 /FontBBox [-1000 -1000 2500 2500] /ItalicAngle 0 /Ascent 905 /Descent -212 /CapHeight 720 /StemV 80 /FontFile2 {fontfile} 0 R >>')
cm=bytearray(131072)
for code,gid in mapping.items(): struct.pack_into('>H',cm,code*2,gid)
cidmap=stream(bytes(cm))
cid=obj(f'<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Arial /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor {fd} 0 R /DW 550 /CIDToGIDMap {cidmap} 0 R >>')
font=obj(f'<< /Type /Font /Subtype /Type0 /BaseFont /Arial /Encoding /Identity-H /DescendantFonts [{cid} 0 R] >>')
pages=obj(''); pageids=[]
for bg,els in slides:
 def rgb(c): return ' '.join(str(int(c[i:i+2],16)/255) for i in (0,2,4))
 cmds=[rgb(bg)+' rg 0 0 960 540 re f']
 for x,y,w,h,size,c,t in els:
  for j,line in enumerate(t.split('\n')):
   cmds.append(f'BT /F1 {size} Tf {rgb(c)} rg 1 0 0 1 {x*72} {540-y*72-size-j*size*1.35} Tm <{line.encode("utf-16-be").hex()}> Tj ET')
 cont=stream('\n'.join(cmds).encode()); pageids.append(obj(f'<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 960 540] /Resources << /Font << /F1 {font} 0 R >> >> /Contents {cont} 0 R >>'))
objs[pages-1]=('<< /Type /Pages /Count 3 /Kids ['+' '.join(f'{i} 0 R' for i in pageids)+'] >>').encode()
root=obj(f'<< /Type /Catalog /Pages {pages} 0 R >>'); data=bytearray(b'%PDF-1.7\n'); offsets=[0]
for i,b in enumerate(objs,1): offsets.append(len(data)); data+=f'{i} 0 obj\n'.encode()+b+b'\nendobj\n'
x=len(data); data+=f'xref\n0 {len(objs)+1}\n0000000000 65535 f \n'.encode()
for o in offsets[1:]: data+=f'{o:010} 00000 n \n'.encode()
data+=f'trailer << /Size {len(objs)+1} /Root {root} 0 R >>\nstartxref\n{x}\n%%EOF'.encode()
Path('output/pochtatech_subscription.pdf').write_bytes(data)
print(len(data))
