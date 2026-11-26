#!/usr/bin/env python3
"""Apply the checked instrument and percussion repair to Bjarke's score."""
import hashlib
import json
from pathlib import Path
from update_abc_plugin import SCRIPT, ATTRIBUTE, array_items, atomic_write


def repair(html, source):
    changes = []
    found = 0
    expected = '290859bbd17c350b59d2651acc413ac9c1528bc8131211b04e29d21ff07be4f3'
    for store in SCRIPT.finditer(html):
        attrs = {m['name'].lower(): m['value'] for m in ATTRIBUTE.finditer(store['attrs'])}
        if 'tiddlywiki-tiddler-store' not in attrs.get('class', '').split() or attrs.get('type', '').lower() != 'application/json':
            continue
        for item, start, end in array_items(store['body']):
            if not isinstance(item, dict):
                continue
            changed = False
            if item.get('title') == 'Alone Together':
                found += 1
                old = item.get('abc-source', '')
                if old != source:
                    if hashlib.sha256(old.encode()).hexdigest() != expected:
                        raise ValueError('Alone Together has changed since review; refusing to overwrite it')
                    item['abc-source'] = source
                    changed = True
            if item.get('title') == 'Bjarkes nodepult':
                old = item.get('text', '')
                new = old.replace('Brug originalen som reference for trommerne, hvor importen forenkler notationen.', 'Instrumenterne følger stemmerne. Trommerne vises samlet på ét femlinjet system.')
                if new != old:
                    item['text'] = new
                    changed = True
            if changed:
                encoded = json.dumps(item, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
                changes.append((store.start('body') + start, store.start('body') + end, encoded))
    if found != 1:
        raise ValueError('Expected exactly one Alone Together score')
    for start, end, encoded in sorted(changes, reverse=True):
        html = html[:start] + encoded + html[end:]
    return html, len(changes)


if __name__ == '__main__':
    path = Path('wiki/bjarke/index.html')
    source = Path('scripts/scores/alone-together.abc').read_text()
    html, count = repair(path.read_text(), source)
    if count:
        atomic_write(path, html.encode())
    print(f'Bjarke: {count} checked tiddlers updated')
