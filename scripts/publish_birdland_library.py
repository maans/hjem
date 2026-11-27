#!/usr/bin/env python3
"""Publish reviewed sources and dated folders without replacing original ABC."""
import json,re
from pathlib import Path
from urllib.parse import urljoin,quote
from update_abc_plugin import SCRIPT,ATTRIBUTE,array_items
from publish_birdland_pdf_spreads import safe_json
ROOT=Path(__file__).resolve().parents[1]
WIKIS=['wiki/birdland/index.html','wiki/birdland/guitar/index.html']
ORIGIN='https://xn--mns-ula.dk/'
def read(html):
 out={}
 for store in SCRIPT.finditer(html):
  a={m['name'].lower():m['value'] for m in ATTRIBUTE.finditer(store['attrs'])}
  if 'tiddlywiki-tiddler-store' not in a.get('class','').split():continue
  for item,_,_ in array_items(store['body']):
   if isinstance(item,dict):out[item['title']]=item
 return out
def patch(html,changes):
 edits=[];seen=set();stores=[]
 for store in SCRIPT.finditer(html):
  a={m['name'].lower():m['value'] for m in ATTRIBUTE.finditer(store['attrs'])}
  if 'tiddlywiki-tiddler-store' not in a.get('class','').split():continue
  stores.append(store)
  for item,start,end in array_items(store['body']):
   title=item.get('title')
   if title in changes:
    seen.add(title)
    if item!=changes[title]:edits.append((store.start('body')+start,store.start('body')+end,safe_json(changes[title])))
 additions=[changes[k] for k in changes if k not in seen]
 if additions:
  store=stores[-1];close=store.start('body')+store['body'].rfind(']')
  edits.append((close,close,',\n'+',\n'.join(map(safe_json,additions))))
 for start,end,text in sorted(edits,reverse=True):html=html[:start]+text+html[end:]
 return html
def main():
 originals={p:(ROOT/p).read_text() for p in WIKIS};rows={p:read(h) for p,h in originals.items()}
 refs=json.loads((ROOT/'scripts/birdland-arrangement-settings.json').read_text())
 leads=json.loads((ROOT/'research/birdland/leadsheet-patches.json').read_text())
 history=json.loads((ROOT/'scripts/birdland-setlists.json').read_text())
 guitar=rows[WIKIS[1]];score=rows[WIKIS[0]]
 titles=[t for t in score if score[t].get('repertoire-kind')=='piece']
 updates={}
 for p,current in rows.items():
  changes={}; role='guitar' if '/guitar/' in p else 'score'
  for title in titles:
   t=dict(current.get(title,{'title':title,'type':'text/vnd.tiddlywiki','text':'','repertoire-kind':'piece','tags':'RepertoireMelodi BirdlandKatalog'}))
   for source,field,path in [(guitar,'repertoire-guitar-pdf',WIKIS[1]),(score,'repertoire-score-pdf',WIKIS[0])]:
    if source.get(title,{}).get('repertoire-pdf'):t[field]=urljoin(urljoin(ORIGIN,path),source[title]['repertoire-pdf'])
   ref=refs.get(title,{})
   if ref.get('key'):t['repertoire-key']=ref['key']
   if ref.get('bpm'):t['repertoire-tempo']=ref['beat']+'='+str(ref['bpm'])
   if guitar.get(title,{}).get('abc-source'):
    sid=title+' · Guitar-ABC'
    changes[sid]={'title':sid,'type':'text/vnd.tiddlywiki','text':'','caption':title,'repertoire-work-title':title,**{k:v for k,v in guitar[title].items() if k.startswith('abc-')}}
    t['repertoire-chord-stabs-source']=sid
   changes[title]=t
  for lead in leads:
   title=lead['title'];sid=title+' · Leadsheet'
   assert re.search(r'^K:\s*'+re.escape(lead['abc_key'])+r'\s*$',lead['abc_source'],re.M)
   assert re.search(r'^Q:\s*'+re.escape(lead['abc_tempo'])+r'\s*$',lead['abc_source'],re.M)
   assert lead['abc_chord_count']>0
   changes[sid]={'title':sid,'caption':title,'type':'text/vnd.tiddlywiki','text':'<$huwiki-abc tiddler=<<currentTiddler>> view="full" embedded="yes" audio="all" show-title="no"/>','music-template':'off','repertoire-work-title':title,'repertoire-abc-label':'Leadsheet (ABC)','abc-source':lead['abc_source'],'source-url':lead['source'],'repertoire-source-reference':lead['birdland_reference']['reference']}
   changes[title]['repertoire-leadsheet-source']=sid
   changes[title]['repertoire-has-leadsheet']='yes'
   view='<$huwiki-repertoire-piece tiddler="'+title+'"/>'
   body=changes[title].get('text','')
   if '<$huwiki-repertoire-piece' not in body:
    body,n=re.subn(r'<iframe\b[^>]*>[\s\S]*?</iframe\s*>',lambda _:view,body,count=1,flags=re.I)
    if not n:body=view+'\n\n'+body
   body=body.replace('Partitur mangler i det delte materiale.','Fuldt partitur mangler i det delte materiale. Leadsheetet vises ovenfor.')
   changes[title]['text']=body
  for title,original in guitar.items():
   if not original.get('abc-source') or title not in changes:continue
   piece=changes[title]; pdf=piece.get('repertoire-guitar-pdf')
   if not pdf:continue
   url=ORIGIN+'wiki/birdland/pdf-viewer/?file='+quote(pdf,safe='')+'&spread=2'
   link='<p class="bird-original-chart"><a href="'+url+'" target="_blank" rel="noopener">Originale chord stabs (PDF) · to sider</a></p>'
   if 'class="bird-original-chart"' not in piece.get('text',''):piece['text']=link+'\n'+piece.get('text','')
   if not piece.get('abc-source') and '<$huwiki-repertoire-piece' not in piece.get('text',''):
    view='<$huwiki-repertoire-piece tiddler="'+title+'"/>'
    piece['text'],n=re.subn(r'<iframe\b[^>]*>[\s\S]*?</iframe\s*>',lambda _:view,piece['text'],count=1,flags=re.I)
    if not n:piece['text']=view+'\n'+piece['text']
   piece['text']=piece['text'].replace('Partitur mangler i det delte materiale.','Fuldt orkesterpartitur mangler. De originale guitar-chordstabs findes som PDF og ABC.')
  orchestra=next(t['title'] for t in current.values() if t.get('repertoire-kind')=='orchestra')
  items={t.get('music-title'):t['title'] for t in current.values() if t.get('repertoire-kind')=='orchestra-item' and t.get('orchestra-title')==orchestra}
  links=[]
  for event in history['events']:
   name=event['date']+' · '+event['event'];sid='Birdland/Nodemapper/'+event['id']
   ordered=[title for section in event['sets'] for title in section['items']]
   assert all(title in items for title in ordered),event['id']
   old=current.get(sid,{})
   record={'title':sid,'type':'text/vnd.tiddlywiki','text':'','repertoire-kind':'setlist','orchestra-title':orchestra,'name':name,'repertoire-event-date':event['date'],'repertoire-event':event['event'],'repertoire-programme-status':event['programme_status'],'repertoire-order-status':event['order_status'],'repertoire-sections':json.dumps(event['sets'],ensure_ascii=False),'description':event['notes'],'list':' '.join('[['+items[x]+']]' for x in ordered),'repertoire-source-role':role,'repertoire-sheet-format':'pdf'}
   for k in ['repertoire-overrides','repertoire-source-role','repertoire-sheet-format']:
    if k in old:record[k]=old[k]
   if event['date']=='2026-11-28' and not old.get('repertoire-view-corrected'):
    record['repertoire-source-role']='guitar';record['repertoire-sheet-format']='pdf'
   if event['date']=='2026-11-28':record['repertoire-view-corrected']='yes'
   changes[sid]=record
   page='Nodemappe · '+name
   changes[page]={'title':page,'type':'text/vnd.tiddlywiki','tags':'BirdlandNodemappe','text':'! '+name+'\n\n'+event['notes']+'\n\n<$huwiki-repertoire-book setlist="'+sid+'"/>\n'}
   links.append('* [['+name+'|'+page+']]')
  changes['Leadsheets']={'title':'Leadsheets','type':'text/vnd.tiddlywiki','tags':'Birdland Oversigt','text':'Afspillelige ABC-noder med melodi og becifringer, tilpasset Birdlands klingende toneart og tempo.\n\n<$list filter="[field:repertoire-has-leadsheet[yes]has[repertoire-leadsheet-source]sort[title]]" emptyMessage="Der er endnu ingen færdigkontrollerede leadsheets i denne wiki."><div><$link to={{!!repertoire-leadsheet-source}}><$view field="title"/></$link></div></$list>\n'}
  changes['Nodemapper']={'title':'Nodemapper','type':'text/vnd.tiddlywiki','tags':'Birdland Oversigt','text':'! Daterede nodemapper\n\nÉn fælles rækkefølge med valgfri visning for hele mappen og for hvert nummer.\n\n'+'\n'.join(links)+'\n\nNordjysk Bigband Dag 23.11.2025 afventer dokumenteret rækkefølge.\n'}
  changes['$:/config/maans/repertoire/default-source-role']={'title':'$:/config/maans/repertoire/default-source-role','text':role}
  for home in ['Birdland · Guitar','Birdlands orkesterwiki']:
   if home in current:
    changes[home]=dict(current[home])
    if '[[Nodemapper]]' not in changes[home].get('text',''):changes[home]['text']=changes[home].get('text','')+'\n\n[[Nodemapper]] · Sætlister med dato og begivenhed.\n'
  result=patch(originals[p],changes);after=read(result)
  for title,t in current.items():
   if 'abc-source' in t:assert after[title].get('abc-source')==t['abc-source'],title
  assert len([t for t in after.values() if t.get('repertoire-has-leadsheet')=='yes'])==len(leads)
  for lead in leads:
   source=after[after[lead['title']]['repertoire-leadsheet-source']]
   assert source['abc-source']==lead['abc_source']
   assert '<$huwiki-abc ' in source['text'] and 'audio="all"' in source['text']
   assert source['music-template']=='off'
  assert 'to={{!!repertoire-leadsheet-source}}' in after['Leadsheets']['text']
  updates[p]=result
 for p,text in updates.items():(ROOT/p).write_text(text)
 print(json.dumps({'wikis':2,'leadsheets':len(leads),'event_folders':len(history['events']),'original_abc_preserved':True}))
if __name__=='__main__':main()
