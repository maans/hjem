"""Add the reviewed birthday set while preserving score sources and other sets."""
import json, re
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'research/silba/birthday-set.json').read_text())
SCRIPT=re.compile(r'(<script\b[^>]*class=["\'][^"\']*\btiddlywiki-tiddler-store\b[^"\']*["\'][^>]*>)([\s\S]*?)(</script\s*>)',re.I)

def apply(path):
    html=path.read_text();found=False
    def patch(match):
        nonlocal found
        rows=json.loads(match[2]);index={r.get('title'):r for r in rows}
        orchestra=next((r for r in rows if r.get('repertoire-kind')=='orchestra' and r.get('name') in ('SilbaÄtno','Silba Ätno')),None)
        if not orchestra:return match[0]
        found=True;orch=orchestra['title']
        set_title='Repertoire/Saetlister/'+quote(orch,safe="~()*!.'-")+'/'+quote(DATA['name'],safe="~()*!.'-")
        entries=[];overrides={}
        for song in DATA['songs']:
            title=song['title'];assert index.get(title,{}).get('abc-source'),f'Missing ABC: {title}'
            item=next((r for r in rows if r.get('repertoire-kind')=='orchestra-item' and r.get('orchestra-title')==orch and r.get('music-title')==title),None)
            assert item,f'Missing orchestra item: {title}'
            entries.append(item['title']);overrides[item['title']]={k:song[k] for k in ('key','form','cues','instrumentation') if k in song}
        assert len(entries)==len(set(entries))==12
        existing=index.get(set_title,{})
        old_overrides=json.loads(existing.get('repertoire-overrides','{}'))
        for title,values in overrides.items():old_overrides[title]={**old_overrides.get(title,{}),**values}
        index[set_title]={**existing,'title':set_title,'type':'text/vnd.tiddlywiki','repertoire-kind':'setlist','orchestra-title':orch,'name':DATA['name'],'list':' '.join('[['+t+']]' for t in entries),'repertoire-overrides':json.dumps(old_overrides,ensure_ascii=False),'text':DATA['note'],'repertoire-source-role':'abc'}
        index[DATA['name']]={'title':DATA['name'],'type':'text/vnd.tiddlywiki','tags':'[[SilbaÄtno]] [[Sætliste]]','text':'<$huwiki-repertoire-book setlist="'+set_title+'"/>\n\n!! Om sættet\n\n'+DATA['note']+'\n\nKilde: '+DATA['source']+'.\n'}
        home=index.get('SilbaÄtno Repertoire – Oversigt')
        if home and 'Åbn fødselsdagssættet' not in home.get('text',''):
            home['text']=home['text'].replace('to="Repertoire – Nodebog" class="silba-primary','to="'+DATA['name']+'" class="silba-primary',1).replace('tooltip="Åbn nodebogen"','tooltip="Åbn fødselsdagssættet"',1).replace('>Åbn nodebogen</span>','>Åbn fødselsdagssættet</span>',1)
            section='<section class="silba-intro"><h2>Fødselsdagssættet · 28. november</h2><p><$link to="'+DATA['name']+'">Åbn fødselsdagssættet</$link> · Henriks seneste rækkefølge og spilleaftaler fra 27. november. Gadjo Cocek og Syv sind er markeret som mulige tilvalg; Cocek Srece er ekstranummer.</p></section>\n'
            home['text']=home['text'].replace('<div class="silba-metrics"',section+'<div class="silba-metrics"',1)
        index['$:/temp/huwiki/repertoire/active-setlist']={'title':'$:/temp/huwiki/repertoire/active-setlist','text':set_title}
        updated=[index.pop(r['title']) for r in rows];updated.extend(index.values())
        # Escape HTML-significant tokens inside the JSON script element.
        data=json.dumps(updated,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
        return match[1]+data+match[3]
    revised=SCRIPT.sub(patch,html)
    assert found,'Silba orchestra store was not found'
    if revised!=html:path.write_text(revised)
    print('Silba birthday set: 12 entries, including 2 optional and 1 encore')

if __name__=='__main__':apply(ROOT/'wiki/silba/index.html')
