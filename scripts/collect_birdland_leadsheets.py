#!/usr/bin/env python3
"""Collect free editable lead-sheet sources; never change active wiki scores."""
import hashlib,json,re,zipfile,io
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import xml.etree.ElementTree as ET
from research_birdland_sources import normalized,public_download,failure_code
class Page(HTMLParser):
 def __init__(self,html):
  super().__init__();self.links=[];self.anchor=None;self.captures=[];self.active=[];self.feed(html)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a':self.anchor=[a.get('href',''),'']
  if tag in ['pre','code','textarea'] or 'abc' in (a.get('id','')+' '+a.get('class','')).lower():self.active.append([tag,''])
  elif self.active:self.active[-1][1]+='\n' if tag=='br' else ''
 def handle_data(self,text):
  if self.anchor:self.anchor[1]+=text
  for c in self.active:c[1]+=text
 def handle_endtag(self,tag):
  if tag=='a' and self.anchor:self.links.append(tuple(self.anchor));self.anchor=None
  if self.active and self.active[-1][0]==tag:self.captures.append(self.active.pop()[1])
def norm(s):
 n=normalized(s)
 return {'donothingtillyouhearfromme':'donothintillyouhearfromme','imbeginingtoseethelight':'imbeginningtoseethelight','itdontmeanathing':'itdontmeanathingifitaintgotthatswing'}.get(n,n)
def fetch(url,limit=2000000):return public_download(url,limit)
def page(url):return Page(fetch(url).decode('utf-8'))
def allowed(url,domain):return urlsplit(url).scheme=='https' and urlsplit(url).hostname==domain
def run(root):
 titles=json.loads((root/'scripts/birdland-research-titles.json').read_text());wanted={norm(t):t for t in titles}
 out=root/'research/birdland/bulk';out.mkdir(parents=True,exist_ok=True)
 entries={t:{'title':t,'sources':[],'status':'not_found_in_reviewed_catalogues'} for t in titles};failures=[];seen=set()
 for index,domain,kind in [('https://freedjazz.org/','freedjazz.org','mscz'),('https://jazzleadsheet.com/leadsheets/','jazzleadsheet.com','abc')]:
  try: links=page(index).links
  except Exception as e:failures.append({'url':index,'failure':failure_code(e)});continue
  for href,label in links:
   title=wanted.get(norm(label))
   url=urljoin(index,href)
   if not title or not allowed(url,domain) or (title,kind) in seen:continue
   try:
    p=page(url)
    if kind=='mscz':
     urls=[urljoin(url,h) for h,l in p.links if h.lower().endswith('.mscz') and allowed(urljoin(url,h),domain)]
     if not urls:raise ValueError('no_public_musescore_link')
     source_url=urls[0];data=fetch(source_url,5000000)
     with zipfile.ZipFile(io.BytesIO(data)) as z:
      names=[n for n in z.namelist() if n.lower().endswith('.mscx') and '/' not in n]
      if len(names)!=1 or z.getinfo(names[0]).file_size>10000000:raise ValueError('invalid_score_archive')
      raw=z.read(names[0])
      if b'<!ENTITY' in raw.upper():raise ValueError('xml_entities')
      xml=ET.fromstring(raw)
      if xml.tag!='museScore' or not list(xml.iter('Note')):raise ValueError('empty_score')
      details={'parts':len(xml.findall('Score/Part')),'notes':len(list(xml.iter('Note'))),'harmonies':len(list(xml.iter('Harmony')))}
    else:
     abc=next((c.strip() for c in p.captures if re.search(r'(^|\n)T:',c) and re.search(r'(^|\n)K:',c)),None)
     if not abc:raise ValueError('no_public_abc_block')
     if len(abc)>300000:raise ValueError('abc_size_limit')
     if not re.search(r'(^|\n)X:',abc):abc='X:1\n'+abc
     chords=re.findall(r'"[^"\n]+"',abc)
     if not chords:raise ValueError('missing_chord_symbols')
     data=(abc+'\n').encode();source_url=url;details={'chord_symbols':len(chords),'source_key':re.search(r'^K:\s*(.+)',abc,re.M).group(1)}
    digest=hashlib.sha256(data).hexdigest();relative='sources/'+digest+'.'+kind
    target=out/relative;target.parent.mkdir(exist_ok=True);target.write_bytes(data)
    record={'format':kind,'url':source_url,'page':url,'path':relative,'sha256':digest,'bytes':len(data),'access':'free_public_source','arrangement':'alternative_leadsheet','birdland_key_tempo_verified':False,**details}
    entries[title]['sources'].append(record);entries[title]['status']='downloaded_needs_musical_review';seen.add((title,kind))
    print(json.dumps({'title':title,'format':kind,'bytes':len(data)}),flush=True)
   except Exception as e:failures.append({'title':title,'url':url,'failure':failure_code(e)})
 report={'scope':'Two reviewed free primary catalogues, matched against the complete Birdland title list. Sources remain unmodified and are not automatically imported into active wikis. Birdland key, tempo and musical content must be checked.','entries':list(entries.values()),'failures':failures}
 (out/'catalogue.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'downloaded_titles':sum(bool(e['sources']) for e in entries.values()),'files':sum(len(e['sources']) for e in entries.values()),'failures':len(failures)}))
 return report
if __name__=='__main__':run(Path(__file__).resolve().parents[1])
