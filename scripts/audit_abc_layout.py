#!/usr/bin/env python3
"""Inventory existing ABC layout settings without changing musical sources."""
import collections, importlib.util, json, pathlib, re
spec=importlib.util.spec_from_file_location('updater','scripts/update_abc_plugin.py')
updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(updater)
rows=[]
for path in sorted(pathlib.Path('wiki').rglob('index.html')):
 for match in updater.SCRIPT.finditer(path.read_text()):
  attrs={m['name'].lower():m['value'] for m in updater.ATTRIBUTE.finditer(match['attrs'])}
  if 'tiddlywiki-tiddler-store' not in attrs.get('class','').split() or attrs.get('type')!='application/json':continue
  for f,_,_ in updater.array_items(match['body']):
   source=f.get('abc-source') or (f.get('text','') if f.get('type')=='text/vnd.abc' else '')
   if not source:continue
   lines=[s.strip() for s in source.splitlines() if s.strip() and not re.match(r'^(%|[A-Za-z]:)',s.strip())]
   counts=[len(re.findall(r'[|]',s)) for s in lines]
   rows.append({'wiki':str(path),'title':f['title'],'mode':f.get('abc-bars-per-line','auto'),'parts':f.get('abc-parts-new-line','default'),'origin':f.get('abc-origin-url',f.get('abc-importer','')),'directives':re.findall(r'^%%(?:barsperstaff|staffbreak|continueall|linebreak).*$',source,re.M),'sourceBars':counts,'fields':f})
print('ABC layout inventory:',len(rows),'scores')
print('Modes:',dict(collections.Counter(r['mode'] for r in rows)))
print('Per wiki:',dict(collections.Counter(r['wiki'] for r in rows)))
for r in rows: print(json.dumps(r,ensure_ascii=False))
pathlib.Path('abc-layout-inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
