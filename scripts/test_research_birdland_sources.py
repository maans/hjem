import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import research_birdland_sources as research


def score(title='All of Me', composer='Composer', count=1):
    return (f'<score-partwise version="4.0"><work><work-title>{title}</work-title></work>'
            f'<identification><creator type="composer">{composer}</creator></identification>'
            '<part-list><score-part id="P1"><part-name>Melody</part-name></score-part></part-list>'
            '<part id="P1"><measure number="1">'
            + '<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration></note>' * count
            + '</measure></part></score-partwise>').encode()


class ResearchSources(unittest.TestCase):
    def test_xml_validation_and_mxl_container_do_not_expose_contact_metadata(self):
        data = score(composer='name@example.com')
        info = research.musicxml_info(data)
        self.assertEqual((info['parts'], info['measures'], info['notes']), (1, 1, 1))
        self.assertEqual(info['composer'], '')
        with self.assertRaises(ValueError):
            research.musicxml_info(b'<html>Sign in</html>')
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('META-INF/container.xml', '<container><rootfiles><rootfile full-path="score.xml"/></rootfiles></container>')
            output.writestr('score.xml', data)
        self.assertEqual(research.mxl_musicxml(archive.getvalue()), data)

    def test_one_best_source_per_title_and_archive_failure_are_recorded(self):
        def download(url, _limit):
            if url == research.ARCHIVE_URL:
                raise research.HTTPError(url, 403, 'Forbidden', {}, None)
            return score()
        with tempfile.TemporaryDirectory() as directory, patch.object(research, 'public_download', side_effect=download):
            output = Path(directory) / 'research'
            result = research.research(['All of Me', 'The Legend'], output)
            self.assertEqual(result['requested_titles'], 2)
            self.assertEqual(result['matched_titles'], 1)
            self.assertEqual(len(list((output / 'sources').glob('*.musicxml'))), 1)
            self.assertEqual(result['entries'][0]['match_type'], 'alternative_lead_sheet')
            self.assertFalse(result['entries'][0]['arrangement_verified'])
            self.assertEqual(result['entries'][1]['status'], 'not_found_in_searched_corpora')
            self.assertEqual(result['downloads'][-1]['failure'], 'http_403')
            before = (output / 'catalogue.json').read_bytes()
            research.research(['All of Me', 'The Legend'], output)
            self.assertEqual((output / 'catalogue.json').read_bytes(), before)
            self.assertEqual(json.loads(before)['matched_titles'], 1)


if __name__ == '__main__':
    unittest.main()
