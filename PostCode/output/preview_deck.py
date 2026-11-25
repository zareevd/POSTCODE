from pathlib import Path
import html
s=Path('output/make_deck.py').read_text(encoding='utf-8')
exec(s[:s.index('with zipfile.ZipFile(out')])
body=''
for bg,els in slides:
 body+=f'<section style="background:#{bg}">'
 for x,y,w,h,size,c,t in els:
  body+=f'<div style="left:{x/13.333*100}%;top:{y/7.5*100}%;width:{w/13.333*100}%;font-size:{size/13.333}cqw;color:#{c}">'+html.escape(t).replace('\n','<br>')+'</div>'
 body+='</section>'
Path('output/preview.html').write_text('<!doctype html><meta charset="utf-8"><title>Почта Премиум</title><style>body{margin:0;background:#151a29;font-family:Arial}section{container-type:inline-size;position:relative;width:96vw;aspect-ratio:16/9;margin:2vw auto;box-shadow:0 8px 40px #0005}div{position:absolute;line-height:1.25}</style>'+body,encoding='utf-8')
