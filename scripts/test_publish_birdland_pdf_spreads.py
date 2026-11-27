"""Focused mixed-preview migration, preservation, join and range checks."""
import json
from pathlib import Path
import tempfile
import unittest

from publish_birdland_pdf_spreads import ORIGIN, CONFIG, patch_wiki, read_manifest, run
from update_abc_plugin import SCRIPT, array_items


def records(html):
    return {item['title']: item for store in SCRIPT.finditer(html)
            if 'tiddlywiki-tiddler-store' in store['attrs']
            for item, _start, _end in array_items(store['body'])}


def store(items):
    return '<!doctype html>KEEP\n<script class="tiddlywiki-tiddler-store" type="application/json">' + json.dumps(items, ensure_ascii=True) + '</script>\nTAIL'


class BirdlandPDFSpreads(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        viewer = ORIGIN + 'wiki/birdland/pdf-viewer/'
        targets = [
            {'wiki': 'wiki/birdland/index.html', 'title': 'Broadway',
             'output': 'wiki/birdland/pdf/broadway.pdf',
             'segments': [{'id': 'source-one', 'start': 2, 'end': 3}]},
            {'wiki': 'wiki/birdland/guitar/index.html', 'title': 'I Get a Kick Out of You',
             'output': 'wiki/birdland/guitar/pdf/i-get-a-kick-out-of-you.pdf',
             'segments': [{'id': 'source-one', 'start': 1, 'end': 1}, {'id': 'source-two', 'start': 1, 'end': 1}]},
        ]
        orchestra = [
            {'title': 'Broadway', 'text': 'PRELUDE\nPartitur · PDF-side 2–3 · <a href="https://drive.google.com/file/d/source-one/view">Åbn originalen i Drev</a>\n<iframe class="bird-pdf" title="Broadway" src="https://drive.google.com/file/d/source-one/preview"></iframe>\nENDING',
             'repertoire-kind': 'piece', 'custom-setting': 'preserve æ " \\ 🎸'},
            {'title': 'Birdlands orkesterwiki', 'text': 'Original homepage'},
            {'title': '$:/config/custom', 'text': 'preserve settings'},
        ]
        guitar = [
            {'title': 'I Get a Kick Out of You', 'abc-source': 'X:1\nT:Kick\nK:F\n"F"CDEF|', 'abc-accompaniment': '{"style":"swing","reverb":0}',
             'text': 'KEEP ORIGINAL INSTRUCTIONS\nGuitar · <a href="https://drive.google.com/file/d/source-one/view">Side 1</a> · <a href="https://drive.google.com/file/d/source-two/view">Side 2</a>\n\nPDF-side <$select tiddler="$:/temp/birdland/pdf/g-kick" default="1"><option value="1">1</option><option value="2">2</option></$select>\n\n<$reveal type="match" state="$:/temp/birdland/pdf/g-kick" default="1" text="1"><iframe class="bird-pdf" src="https://drive.google.com/file/d/source-one/preview"></iframe></$reveal>\n<$reveal type="match" state="$:/temp/birdland/pdf/g-kick" default="1" text="2"><iframe class="bird-pdf" src="https://drive.google.com/file/d/source-two/preview"></iframe></$reveal>\n\n[[Guitarwikiens forside|Birdland · Guitar]]'},
            {'title': 'Four Brothers', 'text': '<iframe class="bird-pdf" src="pdf/four-brothers.pdf#view=FitH"></iframe>\n<p><a href="pdf/four-brothers.pdf" target="_blank" rel="noopener">Åbn noderne som PDF</a></p>\nORIGINAL FOOTER',
             'repertoire-sheet-format': 'abc', 'abc-source': 'X:1\nK:Ab\nABcd|', 'abc-volume': '65'},
            {'title': 'Birdland · Guitar', 'text': 'Original guitar homepage'},
            {'title': 'Unrelated', 'text': 'keep original raw object'},
        ]
        for wiki, items in [('wiki/birdland/index.html', orchestra), ('wiki/birdland/guitar/index.html', guitar)]:
            path = root / wiki
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(store(items), encoding='utf-8')
        manifest = {'viewer': viewer, 'sources': [{'number': 1, 'id': 'source-one', 'size': 1}, {'number': 2, 'id': 'source-two', 'size': 1}], 'targets': targets}
        return root, manifest, orchestra, guitar

    def test_mixed_sources_keep_abc_and_prose_and_patch_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root, manifest, orchestra, guitar = self.fixture(directory)
            for wiki in ('wiki/birdland/index.html', 'wiki/birdland/guitar/index.html'):
                original = (root / wiki).read_text(encoding='utf-8')
                changed, info = patch_wiki(original, wiki, manifest)
                before, after = records(original), records(changed)
                for title, old in before.items():
                    if 'abc-source' in old:
                        for field in ('abc-source', 'abc-accompaniment', 'abc-volume'):
                            self.assertEqual(old.get(field), after[title].get(field))
                self.assertIn('Leadsheets', after)
                self.assertEqual(after[CONFIG]['text'], manifest['viewer'])
                self.assertTrue(changed.startswith('<!doctype html>KEEP'))
                self.assertTrue(changed.endswith('TAIL'))
                repeated, second = patch_wiki(changed, wiki, manifest)
                self.assertEqual(repeated, changed)
                self.assertEqual(second, {'scores': 0, 'added_tiddlers': 0})
                if 'guitar' in wiki:
                    kick = after['I Get a Kick Out of You']
                    self.assertEqual(kick['text'].count('<iframe'), 1)
                    self.assertNotIn('<$select', kick['text'])
                    self.assertNotIn('<$reveal', kick['text'])
                    self.assertIn('KEEP ORIGINAL INSTRUCTIONS', kick['text'])
                    self.assertIn('https://drive.google.com/file/d/source-two/view', kick['text'])
                    self.assertIn('[[Guitarwikiens forside|Birdland · Guitar]]', kick['text'])
                    self.assertEqual(kick['repertoire-pdf'], 'pdf/i-get-a-kick-out-of-you.pdf')
                    four = after['Four Brothers']
                    self.assertEqual(four['repertoire-sheet-format'], 'abc')
                    self.assertEqual(four['text'].count('>Hent PDF</a>'), 1)
                    self.assertEqual(four['text'].count('>Åbn noderne som PDF</a>'), 1)
                    self.assertIn('&amp;spread=2', four['text'])
                    self.assertEqual(after['Unrelated'], before['Unrelated'])

    def test_wrong_source_or_missing_song_cannot_patch_another_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root, manifest, _orchestra, _guitar = self.fixture(directory)
            original = (root / 'wiki/birdland/index.html').read_text(encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'reviewed Drive preview'):
                patch_wiki(original.replace('/source-one/preview', '/wrong/preview'), 'wiki/birdland/index.html', manifest)
            missing = dict(manifest, targets=[dict(manifest['targets'][0], title='Missing song')])
            with self.assertRaisesRegex(ValueError, 'Missing reviewed'):
                patch_wiki(original, 'wiki/birdland/index.html', missing)

    def test_inclusive_extraction_join_bounds_and_no_partial_publication(self):
        try:
            import fitz
            from pypdf import PdfReader
        except ImportError:
            self.skipTest('PDF dependencies installed in publication CI')
        with tempfile.TemporaryDirectory() as directory:
            root, manifest, _orchestra, _guitar = self.fixture(directory)
            sources = root / 'sources'
            sources.mkdir()
            for number, source in enumerate(manifest['sources'], 1):
                document = fitz.open()
                for page in range(1, 4):
                    sheet = document.new_page(width=300, height=400)
                    sheet.insert_text((30, 60), f'SOURCE {number} PAGE {page}', fontsize=18)
                path = sources / (source['id'] + '.pdf')
                document.save(path)
                document.close()
                source['size'] = path.stat().st_size
            manifest_path = root / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            result = run(root, manifest_path, source_dir=sources)
            self.assertEqual((result['pdfs'], result['pages'], result['raster_checks']), (2, 4, 4))
            broadway = PdfReader(root / manifest['targets'][0]['output'])
            self.assertEqual(len(broadway.pages), 2)
            self.assertIn('SOURCE 1 PAGE 2', broadway.pages[0].extract_text())
            self.assertIn('SOURCE 1 PAGE 3', broadway.pages[1].extract_text())
            kick = PdfReader(root / manifest['targets'][1]['output'])
            self.assertIn('SOURCE 1 PAGE 1', kick.pages[0].extract_text())
            self.assertIn('SOURCE 2 PAGE 1', kick.pages[1].extract_text())
            self.assertEqual(kick.page_layout, '/TwoPageLeft')
            repeated = run(root, manifest_path, source_dir=sources)
            self.assertEqual((repeated['written_pdfs'], repeated['written_wikis']), (0, 0))
            original_wiki = (root / 'wiki/birdland/index.html').read_bytes()
            original_pdf = (root / manifest['targets'][0]['output']).read_bytes()
            manifest['targets'][1]['segments'][1]['end'] = 99
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'range exceeds'):
                run(root, manifest_path, source_dir=sources)
            self.assertEqual((root / 'wiki/birdland/index.html').read_bytes(), original_wiki)
            self.assertEqual((root / manifest['targets'][0]['output']).read_bytes(), original_pdf)


if __name__ == '__main__':
    unittest.main()
