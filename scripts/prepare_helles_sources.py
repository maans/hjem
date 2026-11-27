#!/usr/bin/env python3
import os,json,subprocess,xml.etree.ElementTree as E
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'research/helles'
def tree(n):return {'name':n.tag,'attrs':n.attrib,'text':n.text or '', 'tail':n.tail or '', 'children':[tree(c) for c in n]}
for row in json.loads((root/'source-manifest.json').read_text()):
 p=root/'sources'/row['original'];raw=root/'sources'/row['xml']
 if p.suffix=='.mscz':
  raw=root/'sources'/(p.stem+'-modern.musicxml')
  subprocess.run(['mscore3','-o',str(raw),str(p)],env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},check=True,timeout=120)
  row['xml']=raw.name
 (root/'sources'/(row['xml']+'.json')).write_text(json.dumps(tree(E.fromstring(raw.read_bytes())),ensure_ascii=False))
 (root/'sources'/(p.stem+'.manifest.json')).write_text(json.dumps(row,ensure_ascii=False))
