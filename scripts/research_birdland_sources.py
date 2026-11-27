#!/usr/bin/env python3
"""Reproducibly inspect two public score corpora; never edit active wikis.

Only the eight reviewed Effendi URLs and the documented Wikifonia archive are
requested. The catalogue describes these corpora, not an exhaustive web search.
No cookies, credentials, alternate download endpoints or access workarounds.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import socket
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler
import xml.etree.ElementTree as ET
import zipfile

MAX_XML = 5_000_000
MAX_ARCHIVE = 40_000_000
ARCHIVE_URL = 'https://www.synthzone.com/files/Wikifonia/Wikifonia.zip'
ARCHIVE_SIZE = 35_727_800
ARCHIVE_SHA256 = 'e7bce509462a73cee175308b6a3cdafa9effd6e8958b3ce03b4edb293cc6b691'
EFFENDI = [
 ('All of Me', 'https://effendi.me/jazz/repo/IV_Part-2/AllOfMe_C.musicxml'),
 ('Desafinado', 'https://effendi.me/jazz/repo/III/Desafinado.xml'),
 ('Fly Me to the Moon', 'https://effendi.me/jazz/repo/III/FlyMeToTheMoon.xml'),
 ('It Could Happen to You', 'https://effendi.me/jazz/repo/IV_Part-2/ItCouldHappenToYou.musicxml'),
 ('On the Sunny Side of the Street', 'https://effendi.me/jazz/repo/IV_Part-2/OnTheSunnySideOfTheStreet.musicxml'),
 ('Stolen Moments', 'https://effendi.me/jazz/repo/IV_Part-1/StolenMoments.xml'),
 ('Summertime', 'https://effendi.me/jazz/repo/I/Summertime.xml'),
 ('Take the A Train', 'https://effendi.me/jazz/repo/IV_Part-2/TakeTheATrain.musicxml'),
]


def normalized(title: str) -> str:
    text = str(title).strip().casefold().replace('ø', 'o').replace('æ', 'ae').replace('ß', 'ss')
    text = re.sub(r'\.(?:musicxml|mxl|xml|mscz|pdf)$', '', text)
    text = re.sub(r'\s*\((?:in\s+)?(?:c|bb|eb|b♭|e♭|bass clef)\)\s*$', '', text)
    text = re.sub(r'^the\s+', '', text)
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    value = re.sub(r'[^a-z0-9]', '', text)
    return {'flymetomoon': 'flymetothemoon', 'onthesunnyside': 'onthesunnysideofthestreet',
            'sunnysideofthestreet': 'onthesunnysideofthestreet', 'takeatrain': 'takeathetrain',
            'taketheatrain': 'takeathetrain'}.get(value, value)


def safe_text(value: str | None) -> str:
    value = ' '.join((value or '').split())
    # Account/contact details embedded in score metadata do not belong in the
    # public research catalogue. Original score bytes remain unchanged.
    return '' if '@' in value or re.search(r'https?://|www\.', value, re.I) else value[:300]


def musicxml_info(data: bytes) -> dict:
    if len(data) > MAX_XML or b'<!ENTITY' in data.upper():
        raise ValueError('xml_size_or_entity_limit')
    root = ET.fromstring(data)
    for element in root.iter():
        element.tag = element.tag.rsplit('}', 1)[-1]
    if root.tag not in ('score-partwise', 'score-timewise'):
        raise ValueError('not_musicxml_score')
    titles = []
    for path in ('work/work-title', 'movement-title'):
        value = safe_text(root.findtext(path))
        if value and value not in titles:
            titles.append(value)
    if not titles:
        raise ValueError('missing_musicxml_title')
    parts = len(root.findall('./part-list/score-part'))
    if root.tag == 'score-partwise':
        parts = parts or len(root.findall('./part'))
        measures = max((len(part.findall('./measure')) for part in root.findall('./part')), default=0)
    else:
        measures = len(root.findall('./measure'))
        parts = parts or len({part.get('id') for part in root.findall('./measure/part')})
    note_events = list(root.iter('note'))
    notes = sum(note.find('rest') is None and (note.find('pitch') is not None or note.find('unpitched') is not None) for note in note_events)
    if not parts or not measures or not notes:
        raise ValueError('empty_musicxml_score')
    composers = [safe_text(node.text) for node in root.findall('./identification/creator') if node.get('type') == 'composer']
    return {'musicxml_title': titles[0], 'title_aliases': titles[1:], 'composer': '; '.join(value for value in composers if value),
            'parts': parts, 'measures': measures, 'notes': notes, 'note_events': len(note_events),
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def public_download(url: str, limit: int) -> bytes:
    opener = build_opener(ProxyHandler({}))  # no proxy credentials or cookie/auth handlers
    request = Request(url, headers={'User-Agent': 'Birdland-source-research/1.0', 'Accept': '*/*'})
    with opener.open(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError('unexpected_http_status')
        declared = response.headers.get('Content-Length')
        if declared and int(declared) > limit:
            raise ValueError('download_size_limit')
        chunks, count = [], 0
        while True:
            chunk = response.read(min(65536, limit - count + 1))
            if not chunk:
                break
            count += len(chunk)
            if count > limit:
                raise ValueError('download_size_limit')
            chunks.append(chunk)
        return b''.join(chunks)


def failure_code(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f'http_{error.code}'
    if isinstance(error, (TimeoutError, socket.timeout)):
        return 'timeout'
    if isinstance(error, URLError):
        return 'network_error'
    if isinstance(error, (zipfile.BadZipFile, ET.ParseError)):
        return 'invalid_archive_or_xml'
    return str(error) if str(error) in {'download_size_limit', 'unexpected_http_status', 'archive_hash_or_size_mismatch',
        'not_musicxml_score', 'empty_musicxml_score', 'missing_musicxml_title', 'xml_size_or_entity_limit', 'mxl_score_missing'} else type(error).__name__


def mxl_musicxml(data: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        score = None
        if 'META-INF/container.xml' in names:
            if archive.getinfo('META-INF/container.xml').file_size > 100_000:
                raise ValueError('xml_size_or_entity_limit')
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            for node in container.iter():
                if node.tag.rsplit('}', 1)[-1] == 'rootfile':
                    candidate = node.get('full-path')
                    if candidate in names:
                        score = candidate
                        break
        if score is None:
            candidates = sorted(name for name in names if name.lower().endswith(('.xml', '.musicxml')) and not name.startswith('META-INF/'))
            if len(candidates) != 1:
                raise ValueError('mxl_score_missing')
            score = candidates[0]
        if archive.getinfo(score).file_size > MAX_XML:
            raise ValueError('xml_size_or_entity_limit')
        return archive.read(score)


def select_candidate(best: dict, requested: dict, data: bytes, source: dict) -> None:
    info = musicxml_info(data)
    matches = {normalized(title) for title in [info['musicxml_title'], *info['title_aliases']]}
    for key in matches & requested.keys():
        candidate = dict(info, **source)
        rank = (0 if source['corpus'] == 'effendi' else 1, info['parts'] != 1, -info['notes'], info['sha256'])
        if key not in best or rank < best[key][0]:
            best[key] = (rank, candidate, data)


def research(titles: list[str], output: Path, *, include_archive: bool = True) -> dict:
    if not isinstance(titles, list) or not titles or any(not isinstance(title, str) or not title.strip() for title in titles):
        raise ValueError('titles_must_be_nonempty_strings')
    if len(set(titles)) != len(titles):
        raise ValueError('duplicate_requested_titles')
    requested = {normalized(title): title for title in titles}
    best, downloads = {}, []
    for title, url in EFFENDI:
        record = {'corpus': 'effendi', 'title': title, 'url': url}
        try:
            data = public_download(url, MAX_XML)
            info = musicxml_info(data)
            record.update(status='verified_musicxml', sha256=info['sha256'], bytes=len(data))
            select_candidate(best, requested, data, {'corpus': 'effendi', 'url': url})
        except Exception as error:
            record.update(status='failed', failure=failure_code(error))
        downloads.append(record)
    archive_record = {'corpus': 'wikifonia', 'url': ARCHIVE_URL}
    if include_archive:
        try:
            data = public_download(ARCHIVE_URL, MAX_ARCHIVE)
            if len(data) != ARCHIVE_SIZE or hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
                raise ValueError('archive_hash_or_size_mismatch')
            inspected, invalid = 0, 0
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in sorted(archive.infolist(), key=lambda item: item.filename):
                    if member.is_dir() or not member.filename.lower().endswith(('.mxl', '.musicxml', '.xml')):
                        continue
                    if member.file_size > MAX_XML:
                        invalid += 1
                        continue
                    try:
                        raw = archive.read(member)
                        score = mxl_musicxml(raw) if member.filename.lower().endswith('.mxl') else raw
                        inspected += 1
                        select_candidate(best, requested, score, {'corpus': 'wikifonia', 'url': ARCHIVE_URL, 'archive_member': safe_text(member.filename)})
                    except (ValueError, ET.ParseError, zipfile.BadZipFile, KeyError):
                        invalid += 1
            archive_record.update(status='verified_archive', bytes=len(data), sha256=ARCHIVE_SHA256, scores_inspected=inspected, invalid_scores=invalid)
        except Exception as error:
            archive_record.update(status='failed', failure=failure_code(error))
    else:
        archive_record['status'] = 'not_requested'
    downloads.append(archive_record)
    entries, sources = [], {}
    for title in titles:
        found = best.get(normalized(title))
        entry = {'title': title, 'status': 'not_found_in_searched_corpora', 'arrangement_verified': False}
        if found:
            _rank, info, data = found
            relative = f"sources/{info['sha256']}.musicxml"
            entry.update(status='verified_musicxml_alternative', match_type='alternative_lead_sheet', source=dict(info, path=relative))
            sources[relative] = data
        entries.append(entry)
    result = {'schema_version': 1,
              'scope': 'Reviewed Effendi MusicXML links and optional Wikifonia corpus only; not an exhaustive internet search. Every match is an alternative lead sheet, never a verified Birdland arrangement.',
              'requested_titles': len(titles), 'matched_titles': sum('source' in entry for entry in entries),
              'downloads': downloads, 'entries': entries}
    output.mkdir(parents=True, exist_ok=True)
    for relative, data in sorted(sources.items()):
        path = output / relative
        path.parent.mkdir(exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    # Do not remove earlier source files or modify any wiki files.
    (output / 'catalogue.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return result


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--titles', type=Path, default=root / 'scripts/birdland-research-titles.json')
    parser.add_argument('--output', type=Path, default=root / 'research/birdland')
    parser.add_argument('--skip-archive', action='store_true')
    args = parser.parse_args()
    result = research(json.loads(args.titles.read_text(encoding='utf-8')), args.output, include_archive=not args.skip_archive)
    print(json.dumps({'requested_titles': result['requested_titles'], 'matched_titles': result['matched_titles'],
                      'download_failures': sum(row['status'] == 'failed' for row in result['downloads'])}, sort_keys=True))


if __name__ == '__main__':
    main()
