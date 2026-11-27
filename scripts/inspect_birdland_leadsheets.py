#!/usr/bin/env python3
"""Prepare review crops from existing Birdland PDFs and extract free MSCZ sources."""
import base64,json,sys,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import fitz

root=Path(__file__).resolve().parents[1]
source_root=Path(sys.argv[1]).resolve()
bulk=source_root/'research/birdland/bulk'
catalogue=json.loads((bulk/'catalogue.json').read_text())
rows=json.loads((root/'scripts/birdland-research-titles.json').read_text())
if isinstance(rows,dict):rows=rows.get('titles',rows.get('entries',[]))
from publish_birdland_library import read
wiki=read((root/'wiki/birdland/guitar/index.html').read_text())
previews=[];native=[]
for entry in catalogue['entries']:
 if not entry['sources']:continue
 title=entry['title'];piece=wiki.get(title,{})
 relative=piece.get('repertoire-pdf','')
 pdf=(root/'wiki/birdland/guitar'/relative).resolve()
 if relative and pdf.is_relative_to(root/'wiki/birdland/guitar') and pdf.is_file():
  with fitz.open(pdf) as doc:
   page=doc[0];clip=fitz.Rect(0,0,page.rect.width,page.rect.height*.44)
   pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),clip=clip,alpha=False)
   previews.append({'title':title,'source_pdf':relative,'image_jpeg_base64':base64.b64encode(pix.tobytes('jpeg',jpg_quality=75)).decode()})
 for source in entry['sources']:
  if source['format']!='mscz':continue
  archive=bulk/source['path']
  with zipfile.ZipFile(archive) as z:
   names=[n for n in z.namelist() if n.lower().endswith('.mscx') and not n.startswith('__MACOSX/')]
   if len(names)!=1:raise ValueError('Ambiguous MuseScore root: '+title)
   raw=z.read(names[0]);tree=ET.fromstring(raw)
   target=archive.with_suffix('.mscx');target.write_bytes(raw)
   native.append({'title':title,'path':str(target.relative_to(bulk)),'source':source['url'],'notes':len(tree.findall('.//Note')),'parts':len(tree.findall('.//Score/Part')),'staves':len(tree.findall('.//Score/Staff'))})
output={'previews':previews,'native':native}
(bulk/'inspection.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({'review_crops':len(previews),'native_scores':len(native),'inspection_bytes':(bulk/'inspection.json').stat().st_size}))
