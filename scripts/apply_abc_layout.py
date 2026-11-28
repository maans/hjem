#!/usr/bin/env python3
"""Apply only layout changes accepted by the measured all-score audit."""
import importlib.util,json,pathlib
spec=importlib.util.spec_from_file_location('updater','scripts/update_abc_plugin.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
targets=json.loads(pathlib.Path('scripts/abc-layout-fixes.json').read_text())
report=json.loads(pathlib.Path('abc-layout-measured.json').read_text())
checked={(r['wiki'],r['title']):r for r in report}
sources={}
for target in targets:
 r=checked[(target['wiki'],target['title'])]
 modes=[m for m in r['modes'] if m['strategy']=='noParts']
 assert len(modes)==3 and all(m['audioUnchanged'] for m in modes)
 assert len({str(m['systems']) for m in modes})==1
 path=pathlib.Path(target['wiki']);html=path.read_text();edits=[];matches=0
 for match in u.SCRIPT.finditer(html):
  if 'tiddlywiki-tiddler-store' not in match['attrs']:continue
  for item,a,b in u.array_items(match['body']):
   if item.get('title')!=target['title'] or not item.get('abc-source'):continue
   matches+=1
   source=item['abc-source'];sources[(item['title'],source)]=True
   updated=dict(item,**{'abc-parts-new-line':'no'})
   assert updated['abc-source']==source
   replacement=json.dumps(updated,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace(chr(0x2028),'\\u2028').replace(chr(0x2029),'\\u2029')
   if updated!=item:edits.append((match.start('body')+a,match.start('body')+b,replacement))
 assert matches==1,(target,matches)
 for a,b,s in reversed(edits):html=html[:a]+s+html[b:]
 path.write_text(html);print('LAYOUT_FIXED',path,target['title'])
# Match authoritative source records by exact title and ABC, so later rebuilds retain the correction.
def visit(value):
 changed=False
 if isinstance(value,list):
  for child in value:changed=visit(child) or changed
 elif isinstance(value,dict):
  if isinstance(value.get('title'),str) and isinstance(value.get('abc-source'),str) and (value.get('title'),value.get('abc-source')) in sources and value.get('abc-parts-new-line')!='no':
   value['abc-parts-new-line']='no';changed=True
  for child in value.values():
   if isinstance(child,(dict,list)):changed=visit(child) or changed
 return changed
for path in pathlib.Path('research').rglob('*.json'):
 try:value=json.loads(path.read_text())
 except (ValueError,UnicodeError):continue
 if visit(value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print('LAYOUT_SOURCE_FIXED',path)
print('Verified layout-only changes in',len(targets),'scores')
