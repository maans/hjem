#!/usr/bin/env python3
"""Prepare reviewed PDF excerpts and consistent two-page Birdland readers.

All sources/ranges and wiki patches are validated in staging before publication.
Original Drive links and all unrelated tiddlers/score fields are preserved.
"""
from __future__ import annotations

import argparse
import base64
from html import escape, unescape
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import parse_qs, quote, urljoin, urlsplit

from fix_guitar_pdf_previews import atomic_write, attrs, download_public, validate_source
from update_abc_plugin import SCRIPT, ATTRIBUTE, array_items

IFRAME = re.compile(r'<iframe\b[^>]*>[\s\S]*?</iframe\s*>', re.I)
ANCHOR = re.compile(r'<a\b[^>]*>[\s\S]*?</a\s*>', re.I)
KICK = re.compile(r'PDF-side\s*<\$select\b[\s\S]*?</\$select>\s*(?:<\$reveal\b[\s\S]*?</\$reveal>\s*)+', re.I)
CONFIG = '$:/config/maans/repertoire/pdf-viewer'
WIKIS = ('wiki/birdland/index.html', 'wiki/birdland/guitar/index.html')
ORIGIN = 'https://xn--mns-ula.dk/'


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def relative_pdf(wiki: str, output: str) -> str:
    return str(PurePosixPath(output).relative_to(PurePosixPath(wiki).parent))


def checked_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not str(path).startswith('wiki/birdland/'):
        raise ValueError('Manifest path must stay under wiki/birdland')
    return str(path)


def read_manifest(path: Path):
    manifest = json.loads(path.read_text(encoding='utf-8'))
    viewer = manifest.get('viewer', '')
    if viewer != ORIGIN + 'wiki/birdland/pdf-viewer/':
        raise ValueError('Unexpected viewer origin/path')
    sources, targets = manifest.get('sources', []), manifest.get('targets', [])
    by_id = {}
    for source in sources:
        source_id = source.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', source_id) or source_id in by_id:
            raise ValueError('Invalid or duplicate source')
        if type(source.get('size')) is not int or source['size'] < 1:
            raise ValueError('Every source needs its reviewed exact byte size')
        by_id[source_id] = source
    seen, outputs = set(), set()
    for target in targets:
        wiki, output = checked_path(target['wiki']), checked_path(target['output'])
        key = (wiki, target['title'])
        if wiki not in WIKIS or key in seen or output in outputs or not output.endswith('.pdf'):
            raise ValueError('Invalid or duplicate target')
        if not target.get('segments'):
            raise ValueError('A target has no page segments')
        for segment in target['segments']:
            if segment.get('id') not in by_id or type(segment.get('start')) is not int or type(segment.get('end')) is not int or not 1 <= segment['start'] <= segment['end']:
                raise ValueError('Invalid reviewed page segment')
        relative_pdf(wiki, output)
        seen.add(key)
        outputs.add(output)
    if not by_id or not seen:
        raise ValueError('Empty source/target manifest')
    return manifest


def viewer_url(viewer: str, absolute_pdf: str) -> str:
    return viewer + '?file=' + quote(absolute_pdf, safe='') + '&spread=2'


def iframe(viewer: str, pdf: str, title: str) -> str:
    return '<iframe class="bird-pdf" title="' + escape(title, quote=True) + '" src="' + escape(viewer_url(viewer, pdf), quote=True) + '" loading="lazy" allow="fullscreen" allowfullscreen="true"></iframe>'


def frame_pdf(text: str, wiki: str, viewer: str):
    """Return one existing same-wiki PDF preview (native or our viewer)."""
    found = []
    wiki_url = urljoin(ORIGIN, wiki)
    for match in IFRAME.finditer(text):
        source = attrs(match.group()).get('src')
        if not source:
            continue
        value = unescape(source['value'])
        if value.startswith(viewer):
            values = parse_qs(urlsplit(value).query).get('file', [])
            value = values[0] if len(values) == 1 else ''
        absolute = urljoin(wiki_url, value).split('#', 1)[0]
        expected = urljoin(wiki_url, 'pdf/')
        if absolute.startswith(expected) and urlsplit(absolute).path.endswith('.pdf'):
            found.append((match, absolute, absolute.removeprefix(urljoin(wiki_url, './'))))
    if len(found) > 1:
        raise ValueError('A song has multiple local PDF previews')
    return found[0] if found else None


def patch_score(item: dict, wiki: str, viewer: str, target: dict | None):
    text = item.get('text', '')
    if not isinstance(text, str):
        return item, False
    local = frame_pdf(text, wiki, viewer)
    if target:
        relative = relative_pdf(wiki, target['output'])
        absolute = urljoin(ORIGIN, target['output'])
        if local:
            if local[1] != absolute:
                raise ValueError('Existing preview conflicts with reviewed target')
            begin, end = local[0].span()
        elif len(target['segments']) > 1:
            blocks = list(KICK.finditer(text))
            if len(blocks) != 1 or any('/' + segment['id'] + '/preview' not in blocks[0].group() for segment in target['segments']):
                raise ValueError('Expected one reviewed multi-file page selector')
            begin, end = blocks[0].span()
        else:
            source_id = target['segments'][0]['id']
            frames = [match for match in IFRAME.finditer(text) if '/file/d/' + source_id + '/preview' in match.group()]
            if len(frames) != 1:
                raise ValueError('Expected one reviewed Drive preview')
            begin, end = frames[0].span()
        text = text[:begin] + iframe(viewer, absolute, item['title']) + text[end:]
    elif local:
        match, absolute, relative = local
        text = text[:match.start()] + iframe(viewer, absolute, item['title']) + text[match.end():]
    else:
        return item, False
    direct = viewer_url(viewer, absolute)
    # Change only our established score-opening anchor, retaining all Drive links.
    replacements = []
    has_open, has_download = False, False
    for anchor in ANCHOR.finditer(text):
        href = attrs(anchor.group()).get('href')
        if not href:
            continue
        if '>Åbn noderne som PDF</a>' in anchor.group():
            replacements.append((anchor.start() + href.start('value'), anchor.start() + href.end('value'), escape(direct, quote=True)))
            has_open = True
        if '>Hent PDF</a>' in anchor.group() and urljoin(urljoin(ORIGIN, wiki), unescape(href['value'])) == absolute:
            has_download = True
    for begin, end, replacement in reversed(replacements):
        text = text[:begin] + replacement + text[end:]
    links = []
    if not has_open:
        links.append('<a href="' + escape(direct, quote=True) + '" target="_blank" rel="noopener">Åbn noderne som PDF</a>')
    if not has_download:
        links.append('<a href="' + escape(relative, quote=True) + '" target="_blank" rel="noopener" download>Hent PDF</a>')
    if links:
        frame = frame_pdf(text, wiki, viewer)[0]
        text = text[:frame.end()] + '\n<p class="bird-pdf-links">' + ' · '.join(links) + '</p>\n' + text[frame.end():]
    result = dict(item, text=text)
    # Existing ABC, selected representation, mixer and musical settings win.
    result['repertoire-pdf'] = relative
    result.setdefault('repertoire-sheet-format', 'pdf')
    return result, result != item


def patch_wiki(html: str, wiki: str, manifest: dict):
    targets = {target['title']: target for target in manifest['targets'] if target['wiki'] == wiki}
    viewer = manifest['viewer']
    seen, existing, edits, stores = set(), set(), [], []
    changed_scores = 0
    for store in SCRIPT.finditer(html):
        attributes = {match['name'].lower(): match['value'] for match in ATTRIBUTE.finditer(store['attrs'])}
        if 'tiddlywiki-tiddler-store' not in attributes.get('class', '').split() or attributes.get('type', '').lower() != 'application/json':
            continue
        stores.append(store)
        for item, start, end in array_items(store['body']):
            if not isinstance(item, dict):
                continue
            title = item.get('title')
            if title in existing:
                raise ValueError('Duplicate tiddler title')
            existing.add(title)
            changed = item
            if title in targets:
                seen.add(title)
            if title == CONFIG:
                changed = dict(item, text=viewer)
            elif not str(title).startswith('$:/'):
                changed, score_changed = patch_score(item, wiki, viewer, targets.get(title))
                changed_scores += int(score_changed)
                if title in ('Birdland · Guitar', 'Birdlands orkesterwiki') and '[[Leadsheets]]' not in changed.get('text', ''):
                    changed = dict(changed, text=changed.get('text', '').rstrip() + '\n\n[[Leadsheets]] · Melodi og becifringer i Birdlands tonearter og tempi.\n')
            if changed != item:
                edits.append((store.start('body') + start, store.start('body') + end, safe_json(changed)))
    if set(targets) != seen:
        raise ValueError('Missing reviewed PDF tiddlers: ' + ', '.join(sorted(set(targets) - seen)))
    if not stores:
        raise ValueError('No writable tiddler store')
    additions = []
    if CONFIG not in existing:
        additions.append({'title': CONFIG, 'text': viewer})
    if 'Leadsheets' not in existing:
        additions.append({'title': 'Leadsheets', 'type': 'text/vnd.tiddlywiki', 'tags': 'Birdland Oversigt', 'text':
            '! Leadsheets\n\nMelodi og becifringer til repertoirets numre. Importerede leadsheets tilpasses Birdlands klingende toneart og tempo; kilden og eventuelle uafklarede oplysninger bevares.\n\n'
            '<$list filter="[field:repertoire-has-leadsheet[yes]sort[title]]" emptyMessage="Der er endnu ingen færdigkontrollerede leadsheets i denne wiki."><div><$link to=<<currentTiddler>>><$view field="title"/></$link></div></$list>\n'})
    if additions:
        store = stores[-1]
        body = store['body']
        close = body.rfind(']')
        if close < 0:
            raise ValueError('Invalid tiddler store')
        comma = ',' if list(array_items(body)) else ''
        edits.append((store.start('body') + close, store.start('body') + close, comma + '\n' + ',\n'.join(map(safe_json, additions)) + '\n'))
    for begin, end, replacement in sorted(edits, reverse=True):
        html = html[:begin] + replacement + html[end:]
    return html, {'scores': changed_scores, 'added_tiddlers': len(additions)}


def run(root: Path, manifest_path: Path, source_dir: Path | None = None, download: bool = False):
    from pypdf import PdfReader, PdfWriter
    import fitz
    manifest = read_manifest(manifest_path)
    if (source_dir is None) == (not download):
        raise ValueError('Choose exactly one source mode')
    planned_wikis, wiki_stats = [], {}
    for wiki in WIKIS:
        path = root / wiki
        original = path.read_bytes()
        patched, info = patch_wiki(original.decode('utf-8'), wiki, manifest)
        planned_wikis.append((path, patched.encode('utf-8')))
        wiki_stats[wiki] = info
    with tempfile.TemporaryDirectory(prefix='birdland-pdf-spreads-') as folder:
        stage = Path(folder)
        readers, documents = {}, {}
        try:
            for source in manifest['sources']:
                path = stage / (source['id'] + '.pdf') if download else source_dir / (source['id'] + '.pdf')
                if download:
                    download_public(source, path, stage)
                validate_source(path, source)
                reader = PdfReader(path, strict=True)
                if reader.is_encrypted:
                    raise ValueError('Encrypted PDF source')
                readers[source['id']] = reader
                documents[source['id']] = fitz.open(path)
            generated, checks, pages = [], 0, 0
            for index, target in enumerate(manifest['targets']):
                writer, originals = PdfWriter(), []
                for segment in target['segments']:
                    source = readers[segment['id']]
                    if segment['end'] > len(source.pages):
                        raise ValueError('Page range exceeds reviewed source: ' + target['title'])
                    for page in range(segment['start'] - 1, segment['end']):
                        writer.add_page(source.pages[page])
                        originals.append((segment['id'], page))
                writer.add_metadata({'/Title': target['title']})
                writer.page_layout = '/TwoPageLeft'
                output = stage / f'excerpt-{index}.pdf'
                with output.open('wb') as stream:
                    writer.write(stream)
                result = PdfReader(output, strict=True)
                if len(result.pages) != len(originals) or result.metadata.title != target['title']:
                    raise ValueError('Extracted PDF failed structural validation')
                with fitz.open(output) as extracted:
                    for page in sorted({0, len(originals) - 1}):
                        source_id, source_page = originals[page]
                        left = documents[source_id][source_page].get_pixmap(matrix=fitz.Matrix(.5, .5), alpha=False)
                        right = extracted[page].get_pixmap(matrix=fitz.Matrix(.5, .5), alpha=False)
                        if (left.width, left.height) != (right.width, right.height) or hashlib.sha256(left.samples).digest() != hashlib.sha256(right.samples).digest():
                            raise ValueError('Extracted page rendering changed')
                        checks += 1
                generated.append((root / target['output'], output.read_bytes()))
                pages += len(originals)
            written = sum(atomic_write(path, data) for path, data in generated)
            wikis_written = sum(atomic_write(path, data) for path, data in planned_wikis)
            return {'pdfs': len(generated), 'pages': pages, 'raster_checks': checks,
                    'written_pdfs': written, 'written_wikis': wikis_written, 'wikis': wiki_stats}
        finally:
            for document in documents.values():
                document.close()


def reference_previews(root: Path):
    """Small review-only crops of Birdland's actual opening key/tempo markings."""
    import fitz
    sources = [
        ('All of Me', 'wiki/birdland/guitar/pdf/all-of-me.pdf'),
        ('Desafinado', 'wiki/birdland/guitar/pdf/desafinado.pdf'),
        ('Fly Me to the Moon', 'wiki/birdland/guitar/pdf/fly-me-to-the-moon.pdf'),
        ('It Could Happen to You', 'wiki/birdland/guitar/pdf/it-could-happen-to-you.pdf'),
        ('On the Sunny Side of the Street', 'wiki/birdland/guitar/pdf/on-the-sunny-side-of-the-street.pdf'),
        ('Summertime', 'wiki/birdland/guitar/pdf/summertime.pdf'),
        ('Take the A Train', 'wiki/birdland/guitar/pdf/take-the-a-train.pdf'),
        ('Stolen Moments', 'wiki/birdland/pdf/stolen-moments.pdf'),
    ]
    previews = []
    for title, relative in sources:
        with fitz.open(root / relative) as document:
            page = document[0]
            clip = fitz.Rect(0, 0, page.rect.width, page.rect.height * .4)
            image = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), clip=clip, alpha=False)
            encoded = base64.b64encode(image.tobytes('jpeg', jpg_quality=75)).decode('ascii')
        previews.append({'title': title, 'source_pdf': relative, 'image_jpeg_base64': encoded})
    data = json.dumps(previews, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(data) > 3_000_000:
        raise ValueError('Reference preview review artifact exceeds 3 MB')
    atomic_write(root / 'research/birdland/reference-previews.json', data)
    return {'count': len(previews), 'bytes': len(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source-dir', type=Path)
    mode.add_argument('--download-public', action='store_true')
    parser.add_argument('--reference-previews', action='store_true', help='Save small first-page key/tempo review crops for the eight initial leadsheet matches')
    args = parser.parse_args()
    result = run(args.root, args.manifest or args.root / 'scripts/birdland-pdf-sources.json', args.source_dir, args.download_public)
    if args.reference_previews:
        result['reference_previews'] = reference_previews(args.root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
