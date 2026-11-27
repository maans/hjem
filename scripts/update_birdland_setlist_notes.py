"""Update setlist descriptions without rebuilding scores, lists or plugins."""
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STORE=re.compile(r'(<script\b[^>]*class=["\'][^"\']*\btiddlywiki-tiddler-store\b[^"\']*["\'][^>]*>)([\s\S]*?)(</script>)')

def update(path,events):
    changed=0
    def replace(match):
        nonlocal changed
        rows=json.loads(match[2]);before=json.loads(json.dumps(rows));index={r['title']:r for r in rows}
        allowed=set()
        for event in events:
            sid='Birdland/Nodemapper/'+event['id']
            if sid not in index:continue
            title='Nodemappe · '+event['date']+' · '+event['event']
            note=event.get('notes','')
            previous=index[sid].get('description','')
            if note==previous:continue
            index[sid]['description']=note
            allowed.add((sid,'description'))
            if title in index:
                page=index[title];body=page.get('text','')
                marker='<$huwiki-repertoire-book setlist="'+sid+'"/>'
                if marker not in body:raise ValueError('Unexpected setlist page: '+title)
                if previous and previous in body:
                    page['text']=body.replace(previous+'\n\n',note+'\n\n' if note else '',1)
                else:
                    raise ValueError('Setlist note differs from the reviewed source: '+title)
                allowed.add((title,'text'))
        for old,new in zip(before,rows):
            assert old['title']==new['title']
            for field in set(old)|set(new):
                if (old['title'],field) not in allowed:assert old.get(field)==new.get(field),(old['title'],field)
        if rows==before:return match[0]
        changed+=1
        return match[1]+json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')+match[3]
    original=path.read_text();result=STORE.sub(replace,original)
    if changed:path.write_text(result)
    return changed

if __name__=='__main__':
    events=json.loads((ROOT/'scripts/birdland-setlists.json').read_text())['events']
    for relative in ('wiki/birdland/index.html','wiki/birdland/guitar/index.html'):
        path=ROOT/relative
        print(relative,update(path,events),'stores updated')
        assert update(path,events)==0,'Setlist descriptions must be idempotent'
