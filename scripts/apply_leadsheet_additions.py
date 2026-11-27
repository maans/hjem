"""Merge reviewed leadsheets without replacing the wiki's other tiddlers."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'research/helles'

QUALITIES={'diminished-seventh':'dim7','minor-sixth':'m6','major-sixth':'6','minor-ninth':'m9','major-ninth':'maj9','dominant-ninth':'9'}
def compact_chords(source):
    return re.sub(r'"([A-G](?:b|#)?)(diminished-seventh|minor-sixth|major-sixth|minor-ninth|major-ninth|dominant-ninth)(/[^"\n]*)?"',lambda m:'"'+m[1]+QUALITIES[m[2]]+(m[3] or '')+'"',source)

def normalize(rows):
    for row in rows:
        for field in ('abc-source','abc_source'):
            if isinstance(row.get(field),str):row[field]=compact_chords(row[field])
        if row.get('abc-source') and (row.get('repertoire-work-title')=='Bluesette' or re.search(r'^T:\s*Bluesette\s*$',row['abc-source'],re.M|re.I)):
            row['abc-genre']='Jazz waltz'
            try: config=json.loads(row.get('abc-accompaniment','{}'))
            except ValueError: config={}
            if config.get('style')=='swing':
                config['style']='auto'
                row['abc-accompaniment']=json.dumps(config,ensure_ascii=False)
    return rows

def merge(rows):
    index={r['title']:r for r in rows}
    additions=json.loads((DATA/'leadsheet-additions.json').read_text())
    for source in additions:
        assert source.get('abc-source','').startswith('X:')
        index[source['title']]=source
        title=source['repertoire-work-title']
        work=index[title]
        work.update({'repertoire-leadsheet-source':source['title'],'repertoire-source-role':'leadsheet','repertoire-has-leadsheet':'yes'})
    material=DATA/'material-additions.json'
    for addition in json.loads(material.read_text()) if material.exists() else []:
        title=addition['title']
        work=index.setdefault(title,{'title':title,'type':'text/vnd.tiddlywiki'})
        work.update(addition)
        if work.get('repertoire-pdf') or work.get('repertoire-chord-stabs-source'):
            work['text']=work.get('text','').replace('Nodefil til dette nummer er endnu ikke fundet i arkivet.\n\n','')
    # Keep the arranged key sequence on both the work and its orchestra entry.
    # A transposing instrument is a display choice, not a replacement for modulation.
    if index.get('Those Who Were · Leadsheet',{}).get('huwiki-import-source')=='Those Who Were.mscz':
        for row in index.values():
            if row.get('title')=='Those Who Were' or row.get('music-title')=='Those Who Were':
                row['repertoire-key']='G + Bb'
    if 'Materialestatus' in index:
        count=sum(bool(index.get(r.get('repertoire-leadsheet-source',''),{}).get('abc-source')) for r in index.values() if r.get('repertoire-kind')=='piece')
        status=index['Materialestatus']
        status['text']=re.sub(r'\d+ transponérbare ABC-leadsheets',str(count)+' transponérbare ABC-leadsheets',status.get('text',''))
        pdf_count=sum(bool(r.get('repertoire-score-pdf')) for r in index.values() if r.get('repertoire-kind')=='piece')
        status['text']=re.sub(r'\d+ leadsheets som PDF',str(pdf_count)+' leadsheets som PDF',status['text'])
        for title in ('The Guaracha','Altid et Goodbye'):
            work=index.get(title,{})
            if work.get('repertoire-pdf') or work.get('repertoire-chord-stabs-source'):
                status['text']=status['text'].replace('* [['+title+']]\n','')
    return normalize(list(index.values()))

def apply_data():
    path=DATA/'tiddlers.json'
    if path.exists():path.write_text(json.dumps(merge(json.loads(path.read_text())),ensure_ascii=False)+'\n')

def apply_html(path):
    path=Path(path)
    html=path.read_text();updated=0
    def replace(m):
        nonlocal updated
        rows=json.loads(m[2])
        if not isinstance(rows,list):return m[0]
        before=json.dumps(rows,ensure_ascii=False)
        rows=merge(rows) if path==ROOT/'wiki/helles/index.html' and any(r.get('title')=='Libertango' for r in rows) else normalize(rows)
        after=json.dumps(rows,ensure_ascii=False)
        if before==after:return m[0]
        updated+=1
        return m[1]+after.replace('<','\\u003c')+m[3]
    result=re.sub(r'(<script\b[^>]*class=["\'][^"\']*\btiddlywiki-tiddler-store\b[^"\']*["\'][^>]*>)([\s\S]*?)(</script>)',replace,html)
    if updated:path.write_text(result)

if __name__=='__main__':
    apply_data()
    if '--data-only' not in sys.argv:
        for path in (ROOT/'wiki').rglob('index.html'):apply_html(path)
    print('Reviewed ABC leadsheets merged; original PDFs and other tiddlers preserved')

