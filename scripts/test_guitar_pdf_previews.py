"""Focused extraction, safe wiki editing and all-or-nothing source checks."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fitz
from pypdf import PdfReader

from fix_guitar_pdf_previews import SourceUnavailable, patch_wiki, run
from update_abc_plugin import SCRIPT, array_items


def stored(html):
    return {item['title']: item for match in SCRIPT.finditer(html)
            if 'tiddlywiki-tiddler-store' in match['attrs']
            for item, _start, _end in array_items(match['body'])}


class GuitarPDFPreviews(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        sources = root / 'sources'
        sources.mkdir()
        books = []
        for number in range(1, 4):
            document = fitz.open()
            for page in range(1, 4):
                sheet = document.new_page(width=300 + page, height=400 + number)
                sheet.insert_text((30, 60), f'BOOK {number} PAGE {page}', fontsize=18)
                sheet.draw_rect(fitz.Rect(30, 90, 40 + page * 20, 160), color=(number / 3, 0, page / 3))
            path = sources / f'book-{number}.pdf'
            document.save(path)
            document.close()
            books.append({'number': number, 'id': f'public-book-{number}', 'size': path.stat().st_size})
        entries = [
            {'title': 'One page', 'slug': 'one-page', 'book': 1, 'start': 1, 'end': 1},
            {'title': 'Four Brothers', 'slug': 'four-brothers', 'book': 1, 'start': 2, 'end': 3},
            {'title': 'ABC wrapper', 'slug': 'abc-wrapper', 'book': 2, 'start': 2, 'end': 2},
            {'title': 'Last book', 'slug': 'last-book', 'book': 3, 'start': 3, 'end': 3},
        ]
        records = []
        for entry in entries:
            entry['drive_id'] = books[entry['book'] - 1]['id']
            href = f'https://drive.google.com/file/d/{entry["drive_id"]}'
            record = {'title': entry['title'], 'text': (
                'Original note æøå 🎸\\ literal / line\n'
                + ('<details><summary>Original score</summary>\n' if entry['title'] == 'ABC wrapper' else '')
                + f'Guitarmappe {entry["book"]}, side {entry["start"]}–{entry["end"]} · '
                + f'<a href="{href}/view" target="_blank">Åbn originalen i Drev</a>\n'
                + f'<iframe class="bird-pdf" src="{href}/preview" loading="lazy"></iframe>\n'
                + ('</details>' if entry['title'] == 'ABC wrapper' else '')
                + '\nOriginal ending note'), 'tags': 'BirdlandGuitarPDF'}
            if entry['title'] == 'ABC wrapper':
                record.update({'abc-source': 'X:1\nT:ABC wrapper\nK:C\nCDEF|',
                               'abc-accompaniment': '{"style":"swing","reverb":42}',
                               'abc-bars-per-line': '4', 'custom-setting': 'keep \\ " æ 🎸'})
            records.append(record)
        unrelated = ' { "title" : "A Foggy Day", "text": "separate Drive source untouched", "abc-accompaniment": "custom" } '
        settings = '{"title":"$:/config/audio","text":"keep settings"}'
        # ASCII escapes and deliberately irregular whitespace must survive edits.
        body = ',\n'.join(json.dumps(record, ensure_ascii=True, separators=(', ', ' : ')) for record in records)
        html = '<!doctype html>\n<script>var preserve="unrelated script";</script>\n<script type="application/json" class="tiddlywiki-tiddler-store">[\n' + body + ',\n' + unrelated + ',\n' + settings + '\n]</script>\nTAIL\n'
        wiki = root / 'wiki/birdland/guitar/index.html'
        wiki.parent.mkdir(parents=True)
        wiki.write_text(html, encoding='utf-8')
        manifest = root / 'manifest.json'
        manifest.write_text(json.dumps({'books': books, 'entries': entries}), encoding='utf-8')
        return sources, manifest, wiki, entries, html, unrelated, settings

    def test_inclusive_pages_render_identically_and_second_run_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            sources, manifest, wiki, entries, original, unrelated, settings = self.fixture(directory)
            result = run(manifest, wiki, source_dir=sources)
            self.assertEqual((result['books'], result['pdfs'], result['pages']), (3, 4, 5))
            self.assertGreaterEqual(result['raster_checks'], 5)
            changed = wiki.read_text(encoding='utf-8')
            before, after = stored(original), stored(changed)
            self.assertIn(unrelated, changed)
            self.assertIn(settings, changed)
            self.assertIn('<script>var preserve="unrelated script";</script>', changed)
            self.assertTrue(changed.endswith('\nTAIL\n'))
            for entry in entries:
                title, slug = entry['title'], entry['slug']
                self.assertEqual({k: v for k, v in before[title].items() if k != 'text'},
                                 {k: v for k, v in after[title].items() if k != 'text'})
                text = after[title]['text']
                self.assertIn(f'src="pdf/{slug}.pdf#view=FitH"', text)
                self.assertIn('Åbn noderne som PDF', text)
                self.assertIn('Åbn hele guitarmappen i Drev', text)
                self.assertIn(f'https://drive.google.com/file/d/{entry["drive_id"]}/view', text)
                self.assertIn('Original note æøå 🎸\\ literal / line\n', text)
                self.assertIn('Original ending note', text)
                pdf = PdfReader(wiki.parent / 'pdf' / f'{slug}.pdf')
                self.assertEqual(len(pdf.pages), entry['end'] - entry['start'] + 1)
                self.assertEqual(pdf.metadata.title, title)
                for index, page in enumerate(pdf.pages, entry['start']):
                    self.assertIn(f'BOOK {entry["book"]} PAGE {index}', page.extract_text())
            # Fields outside text retain their original raw JSON bytes too.
            raw_abc = json.dumps(before['ABC wrapper']['abc-source'], ensure_ascii=True)
            self.assertIn('"abc-source" : ' + raw_abc, changed)
            files_before = {path.name: path.read_bytes() for path in (wiki.parent / 'pdf').glob('*.pdf')}
            rerun = run(manifest, wiki, source_dir=sources)
            self.assertFalse(rerun['wiki_changed'])
            self.assertEqual(rerun['text_edits'], 0)
            self.assertEqual(rerun['written_pdfs'], 0)
            self.assertEqual(wiki.read_text(encoding='utf-8'), changed)
            self.assertEqual({path.name: path.read_bytes() for path in (wiki.parent / 'pdf').glob('*.pdf')}, files_before)

    def test_bad_or_unavailable_source_never_changes_any_public_output(self):
        with tempfile.TemporaryDirectory() as directory:
            sources, manifest, wiki, _entries, original, *_rest = self.fixture(directory)
            (sources / 'book-3.pdf').write_bytes(b'<html>Sign in</html>')
            with self.assertRaises(SourceUnavailable):
                run(manifest, wiki, source_dir=sources)
            self.assertEqual(wiki.read_text(encoding='utf-8'), original)
            self.assertFalse((wiki.parent / 'pdf').exists())
            with patch('fix_guitar_pdf_previews.download_public', side_effect=SourceUnavailable('anonymous download unavailable')):
                with self.assertRaises(SourceUnavailable):
                    run(manifest, wiki, download=True)
            self.assertEqual(wiki.read_text(encoding='utf-8'), original)
            self.assertFalse((wiki.parent / 'pdf').exists())

    def test_missing_or_wrong_iframe_cannot_patch_other_material(self):
        with tempfile.TemporaryDirectory() as directory:
            _sources, _manifest, _wiki, entries, original, *_rest = self.fixture(directory)
            broken = original.replace('/preview', '/unexpected')
            with self.assertRaisesRegex(ValueError, 'matching score iframe'):
                patch_wiki(broken, entries)
            with self.assertRaisesRegex(ValueError, 'Missing'):
                patch_wiki(original, [dict(entries[0], title='Missing song')])


if __name__ == '__main__':
    unittest.main()
