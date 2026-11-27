#!/usr/bin/env python3
"""Build Helles' own repertoire wiki from documented sources."""
import json,re,zipfile,shutil,os
from pathlib import Path
from pypdf import PdfReader,PdfWriter
ROOT=Path(__file__).resolve().parents[1]
FORGE=Path(os.environ.get('FORGE_SOURCE',ROOT/'.forge-source'))
DATA=ROOT/'research/helles';OUT=ROOT/'wiki/helles';OUT.mkdir(parents=True,exist_ok=True)
def load(name):return json.loads((DATA/name).read_text())
def slug(s):
 import unicodedata
 return re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()).strip('-')
def listed(a):return ' '.join('[['+s+']]' for s in a)
def tid(title,text='',**fields):return {'title':title,'text':text,'type':'text/vnd.tiddlywiki',**fields}
ORCH='Repertoire/Orkestre/Helles'
def item(title):return 'Helles/Repertoire/'+slug(title)
def setid(key):return 'Helles/Sætlister/'+key
rows=load('arrangements.json');assets=load('asset-manifest.json');conversions={r['title']:r for r in load('conversions.json') if r.get('publish')}
original=PdfReader(OUT/'pdf/helles-saet-1-og-2-original.pdf')
pages=[[2],[3,4,5],[6,7],[8],[9],[10],[11,12],[13],[14],[16],[17,18],[19],[20],[21],[22],[23],[25],[24]]
for row,p in zip(rows,pages):
 target=slug(row['title'])+'-leadsheet.pdf';writer=PdfWriter()
 for i in p:writer.add_page(original.pages[i-1])
 writer.write(OUT/'pdf'/target);row['pdf']=target
for title in ['Har du visor, min vän','Bluesette','I din hand','The Guaracha','Altid et Goodbye','Oy como va','Visan från Utanmyra']:
 rows.append({'title':title,'key':'','tempo':'','form':'','cues':'','pdf':assets.get(title,{}).get('pdf','')})
assert len({r['title'] for r in rows})==25
if (DATA/'assets.zip').exists():
 with zipfile.ZipFile(DATA/'assets.zip') as z:
  for name in z.namelist():
   assert name.startswith('pdf/') and '..' not in Path(name).parts
   (OUT/name).parent.mkdir(exist_ok=True,parents=True);(OUT/name).write_bytes(z.read(name))
# Remove superseded generated charts whose identification was not confirmed.
for old in ['brevet','libertango','this-masquerade','those-who-were']:
 (OUT/'pdf'/(old+'-chord-stabs.pdf')).unlink(missing_ok=True)
tiddlers=[]
for p in ['themes/modern/dist/theme.json','languages/da-DK/plugin.json']+[f'plugins/{n}/dist/plugin.json' for n in ['abc','music','musescore-import','repertoire','site-publisher','print-article']]:
 tiddlers.append(json.loads((FORGE/p).read_text()))
for name,value in {
 '$:/SiteTitle':'Helles','$:/SiteSubtitle':'Repertoire · leadsheets · chord stabs · sangtekster',
 '$:/theme':'$:/themes/huwiki/modern','$:/language':'$:/languages/da-DK',
 '$:/DefaultTiddlers':'[[Helles]]','$:/config/maans/repertoire/default-source-role':'',
 '$:/GitHub/Branch':'main','$:/GitHub/Filename':'index.html','$:/GitHub/Path':'wiki/helles/',
 '$:/GitHub/Repo':'maans/hjem','$:/GitHub/Username':'maans',
 '$:/config/huwiki/abc/tab-default':'off',
 '$:/config/maans/repertoire/pdf-viewer':'/wiki/birdland/pdf-viewer/',
}.items():tiddlers.append(tid(name,value))
tiddlers.append(tid(ORCH,name='Helles',**{'repertoire-kind':'orchestra'}))
for r in rows:
 title=r['title'];extra=assets.get(title,{})
 fields={'repertoire-kind':'piece','tags':'RepertoireMelodi HellesNummer','music-template':'off','repertoire-key':r['key'],'repertoire-tempo':('1/4='+str(r['tempo'])) if r['tempo'] else '', 'repertoire-category':'leadsheet'}
 links=[]
 if r.get('pdf'):
  fields['repertoire-score-pdf']='pdf/'+r['pdf'];fields['repertoire-pdf']='pdf/'+r['pdf'];fields['repertoire-source-role']='score'
 if extra.get('stabs'):fields['repertoire-guitar-pdf']='pdf/'+extra['stabs']
 if title in conversions:
  c=conversions[title];sid=title+' · Leadsheet';fields.update({'repertoire-leadsheet-source':sid,'repertoire-has-leadsheet':'yes','repertoire-source-role':'leadsheet'})
  tiddlers.append(tid(sid,'<$huwiki-repertoire-piece tiddler=<<currentTiddler>>/>',**{'caption':title,'music-template':'off','repertoire-work-title':title,'repertoire-abc-label':'Leadsheet (ABC)','abc-source':c['abc_source'],'abc-accompaniment':json.dumps({'enabled':True,'style':'bossa' if title in ['Wave','Desafinado'] else 'swing'}),'abc-bars-per-line':'4','helles-source-file':c['original']}))
  fields['repertoire-key']=r['key'] if '+' in r.get('key','') else c['target']
 if extra.get('lyrics'):fields['helles-lyrics-pdf']='pdf/'+extra['lyrics']
 text='<$huwiki-repertoire-piece tiddler=<<currentTiddler>>/>\n\n'
 if not r.get('pdf') and title not in conversions:text+='Nodefil til dette nummer er endnu ikke fundet i arkivet.\n\n'
 text+='[[Sangtekst og noter|'+title+' · Sangtekst]]\n'
 tiddlers.append(tid(title,text,**fields))
 if title=='Dejlighedssang':tiddlers.append(tid('Dejlighedsvise','Se [[Dejlighedssang]].',tags='HellesAlias'))
 tiddlers.append(tid(item(title),'',**{'repertoire-kind':'orchestra-item','orchestra-title':ORCH,'music-title':title,'repertoire-key':fields['repertoire-key'],'repertoire-tempo':fields['repertoire-tempo'],'repertoire-form':r['form'],'repertoire-cues':r['cues']}))
 lyrictext='! '+title+' · Sangtekst\n\n[[Åbn noder|'+title+']]\n\n'
 if extra.get('lyrics'):lyrictext+='[[Original tekstside (PDF)|pdf/'+extra['lyrics']+']]\n\n<iframe src="pdf/'+extra['lyrics']+'" title="Sangtekst" style="width:100%;height:75vh;border:0;"></iframe>\n\n'
 else:lyrictext+='Sangtekst mangler i det fundne materiale. Tilføj den her, når den er klar.\n\n'
 lyrictext+='<$edit-text tiddler="'+title+'" field="helles-lyrics" tag="textarea" rows="18" class="helles-lyrics-editor" placeholder="Sangtekst og egne noter…"/>\n'
 tiddlers.append(tid(title+' · Sangtekst',lyrictext,tags='HellesSangtekst'))
latest=['Sakta vi gå genom stan','Desafinado','Dansevise','Brevet','Wave',"'Round Midnight",'Deidres Samba','This Masquerade','Quiet Night of Quiet Stars','The Guaracha']
sets=[('2026-11-28','28.11.2026 · Måns’ musikfest',latest,'Helles repertoiremail 9. november 2026. Rækkefølgen følger mailen; den endelige koncertorden er ikke særskilt bekræftet.'),('2026-01-25-saet-1','Jazzeftermiddag · Sæt 1',[r['title'] for r in rows[:9]],'Sæt 1 fra den samlede nodebog, sendt 18. januar 2026.'),('2026-01-25-saet-2','Jazzeftermiddag · Sæt 2',[r['title'] for r in rows[9:18]],'Sæt 2 fra den samlede nodebog, sendt 18. januar 2026.'),('2026-05-16','16.05.2026 · Allans fødselsdag',['Sakta vi gå genom stan','Desafinado','Dansevise','Hvorfor er lykken så lunefuld','Nature Boy'],'Mail 21. april med Helles rettelse 26. april: Hvorfor er lykken så lunefuld erstatter Round Midnight.'),('2026-06-01','01.06.2026 · Nye numre',['Har du visor, min vän','Bluesette','I din hand','The Guaracha','Altid et Goodbye','Oy como va'],'Øverepertoire fra Helles mail 22. maj 2026.')]
for key,name,titles,description in sets:
 assert all(t in [r['title'] for r in rows] for t in titles)
 tiddlers.append(tid(setid(key),'',name=name,list=listed([item(t) for t in titles]),description=description,**{'repertoire-kind':'setlist','orchestra-title':ORCH,'repertoire-overrides':'{}','repertoire-event-date':key[:10],'repertoire-order-status':'mail-order' if key=='2026-11-28' else 'source-order'}))
 tiddlers.append(tid(name,description+'\n\n<$huwiki-repertoire-book setlist="'+setid(key)+'"/>'))
tiddlers.append(tid('Hele repertoiret','<$huwiki-repertoire-book setlist="'+ORCH+'"/>'))
home='''<div class="helles-home"><p class="helles-eyebrow">HELLES · REPERTOIRE</p><h1>Musikken, samlet.</h1><p>Leadsheets, chord stabs, spilleaftaler og sangtekster — fra øvning til koncert.</p>
<div class="helles-links">[[Åbn musikfestens nodemappe|28.11.2026 · Måns’ musikfest]] [[Hele repertoiret]] [[Nodemapper og numre|HUWiki Repertoire – Start]] [[Redigér sætlister|Repertoire – Sætlister]] [[Spilleaftaler]] [[Sangtekster]]</div></div>

!! Musikfesten · 28. november

De ti numre fra Helles seneste repertoiremail. Åbn nodemappen for at bladre gennem dem.

''Saxofon:'' Vælg instrumentnoder i ABC-visningen: B♭ sopransax, B♭ tenor eller E♭ alto. Afspilningen beholder den klingende toneart. Originale PDF’er vises i deres egen toneart.

''Guitar:'' Vælg Chord stabs (PDF), hvor den originale guitarudgave findes. Capo og håndskrevne noter i PDF’en bevares. Akkordarkene stammer fra Per Aspera-arkivet; sammenhold toneart og aftaler med Helles’ leadsheet.

!! Nodemapper

'''
home+='\n'.join('* [['+s[1]+']]' for s in sets)
home+='\n\n!! Alle numre\n\n<div class="helles-catalog"><$list filter="[tag[HellesNummer]sort[title]]"><div><$link><$view field="title"/></$link></div></$list></div>\n\n[[Materialestatus]] · [[Kilder og historik]]\n'
tiddlers.append(tid('Helles',home))
agreement='Aftalerne er overført fra den eksisterende Helles-sætliste. Ret dem under [[Redigér sætlister|Repertoire – Sætlister]].\n\n'
for r in rows:
 if r['form']:agreement+='!! [['+r['title']+']]\n\n'+r['key']+' · '+str(r['tempo'])+'\n\n'+r['form']+'\n\n'
tiddlers.append(tid('Spilleaftaler',agreement))
tiddlers.append(tid('Sangtekster','Sangtekster og egne noter pr. nummer. De tre fundne tekstark er bevaret som PDF.\n\n<$list filter="[tag[HellesNummer]sort[title]]"><div><$link to={{{ [<currentTiddler>addsuffix[ · Sangtekst]] }}}><$view field="title"/></$link></div></$list>'))
missing=[r['title'] for r in rows if not r.get('pdf') and r['title'] not in conversions]
status=f"{len(rows)} numre · {sum(bool(r.get('pdf')) for r in rows)} leadsheets som PDF · {sum(bool(a.get('stabs')) for a in assets.values())} originale chord-stabs-ark · {len(conversions)} transponérbare ABC-leadsheets · 3 tekstark.\n\n"
status+='!! Nodefil mangler\n\n'+'\n'.join('* [['+t+']]' for t in missing)+'\n\n!! Redigerbare kilder til kontrol\n\nDansevise, I din hand og Visan från Utanmyra er fundet som MusicXML, men indeholder ingen becifringer. De er bevaret i kildearkivet og afventer sammenhold med originalerne.\n\nØvrige numre med PDF kan endnu ikke transponeres automatisk.\n'
tiddlers.append(tid('Materialestatus',status))
tiddlers.append(tid('Kilder og historik','''Repertoiret bygger på Helles mail 24.06.2025 (18 numre), opdateringer i 2026 og repertoiremailen 09.11.2026 (musikfestens ti numre).

Spilleaftaler, tonearter og tempi er overført fra den eksisterende Helles Jazzeftermiddag-sætliste. De oprindelige guitarudgaver er fra dit Per Aspera-nodearkiv. Nyere mails går forud for ældre lister.

[[Samlet original nodebog|pdf/helles-saet-1-og-2-original.pdf]] · [[Den tidligere sætliste|https://maans.github.io/Helles2/]]

The Guaracha og La Guaracha samles under mailens seneste titel. Deidres Samba og Deirdres Samba er samme repertoirepost. Farvel, Goodbye er registreret som Altid et Goodbye (Troels Trier).
'''))
css='.helles-home{padding:32px;border-radius:18px;background:linear-gradient(125deg,#3c1928,#6b3640);color:#fff;margin-bottom:28px}.helles-home h1{font-size:2.8rem;color:#fff;margin:.2em 0}.helles-eyebrow{font-size:.8rem;letter-spacing:.14em;color:#ebc987}.helles-links{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}.helles-links a{display:block;background:#f4e8d4;color:#3c1928;padding:10px 14px;border-radius:7px;font-weight:600}.helles-catalog{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}.helles-catalog a{font-weight:600}.helles-lyrics-editor{width:100%;min-height:260px}.helles-reader-lyrics{padding:12px 18px;margin:8px;border:1px solid #c6b7a3;border-radius:8px}.helles-reader-lyrics pre{white-space:pre-wrap;font:inherit}'
tiddlers.append(tid('$:/helles/styles',css,tags='$:/tags/Stylesheet',type='text/css'))
addon='''exports.name='helles-reading';exports.platforms=['browser'];exports.after=['story'];exports.before=['render'];exports.synchronous=true;
exports.startup=function(){
var model=require('$:/plugins/huwiki/repertoire/model.js');model.viewLabels.score='Leadsheet (PDF)';model.viewLabels.guitar='Chord stabs (PDF)';
var Book=require('$:/plugins/huwiki/repertoire/book-widget.js')['huwiki-repertoire-book'],draw=Book.prototype.draw;
Book.prototype.draw=function(){draw.apply(this,arguments);if(!this.host||this._editReturn)return;var selected=this.wiki.getTiddler(this.activeItem),work=selected&&selected.fields['music-title']?this.wiki.getTiddler(selected.fields['music-title']):selected;if(!work)return;var d=this.document,box=d.createElement('details'),summary=d.createElement('summary');box.className='helles-reader-lyrics';summary.textContent='Sangtekst og noter';box.appendChild(summary);var body=d.createElement('div'),a=d.createElement('a');a.href='#'+encodeURIComponent(work.fields.title+' · Sangtekst');a.textContent='Åbn / redigér sangtekst';body.appendChild(a);if(work.fields['helles-lyrics']){var p=d.createElement('pre');p.textContent=work.fields['helles-lyrics'];body.appendChild(p);}if(work.fields['helles-lyrics-pdf']){var p=d.createElement('a');p.href=work.fields['helles-lyrics-pdf'];p.target='_blank';p.rel='noopener';p.textContent=' · Original tekstside (PDF)';body.appendChild(p);}box.appendChild(body);this.host.appendChild(box);};
};'''
tiddlers.append(tid('$:/helles/reading.js',addon,type='application/javascript',**{'module-type':'startup'}))
assert len({t['title'] for t in tiddlers})==len(tiddlers)
(DATA/'tiddlers.json').write_text(json.dumps(tiddlers,ensure_ascii=False))
(DATA/'build-summary.json').write_text(json.dumps({'pieces':25,'pdf_leadsheets':sum(bool(r.get('pdf')) for r in rows),'chord_stabs':sum(bool(a.get('stabs')) for a in assets.values()),'abc':len(conversions),'lyric_sheets':3,'missing':missing},ensure_ascii=False,indent=2))
print((DATA/'build-summary.json').read_text())

