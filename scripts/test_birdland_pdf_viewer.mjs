import assert from 'node:assert/strict';
import test from 'node:test';
import { advance, normalizeSpread, resolvePdfUrl, spreadStart, visiblePages } from '../wiki/birdland/pdf-viewer/viewer-core.mjs';

test('two-page spreads advance by pairs, including an odd final page', () => {
  assert.deepEqual(visiblePages(1, 5), [1, 2]);
  assert.deepEqual(advance(1, 5, 2, 1), { page: 3, boundary: null });
  assert.deepEqual(visiblePages(3, 5), [3, 4]);
  assert.deepEqual(advance(3, 5, 2, 1), { page: 5, boundary: null });
  assert.deepEqual(visiblePages(5, 5), [5]);
  assert.deepEqual(advance(5, 5, 2, 1), { page: 5, boundary: 'next' });
  assert.deepEqual(advance(1, 5, 2, -1), { page: 1, boundary: 'previous' });
  assert.deepEqual(advance(5, 5, 2, -1), { page: 3, boundary: null });
  assert.deepEqual(visiblePages(1, 1), [1]);
});

test('direct page selection aligns to pairs and single-page navigation is exact', () => {
  assert.equal(spreadStart(4, 5, 2), 3);
  assert.equal(spreadStart(999, 5, 2), 5);
  assert.equal(spreadStart(-10, 5, 2), 1);
  assert.equal(spreadStart('garbage', 5, 2), 1);
  assert.equal(spreadStart(4, 5, 1), 4);
  assert.deepEqual(advance(2, 5, 1, 1), { page: 3, boundary: null });
  assert.equal(normalizeSpread(undefined), 2);
});

test('PDF sources are restricted to the viewer origin and safe PDF protocols', () => {
  const base = 'https://example.test/wiki/birdland/pdf-viewer/index.html';
  assert.equal(resolvePdfUrl('../guitar/pdf/four-brothers.pdf#page=2', base).href, 'https://example.test/wiki/birdland/guitar/pdf/four-brothers.pdf');
  assert.equal(resolvePdfUrl('/notes/a.PDF?revision=2', base).href, 'https://example.test/notes/a.PDF?revision=2');
  for (const url of ['', 'https://other.test/notes.pdf', '//other.test/notes.pdf', 'javascript:alert(1)', 'data:application/pdf;base64,AA==', 'https://name:password@example.test/notes.pdf', '/notes.html']) {
    assert.throws(() => resolvePdfUrl(url, base));
  }
});
