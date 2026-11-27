# Birdland PDF score viewer

Same-origin, locally hosted PDF rendering with two-page spreads by default:

`/wiki/birdland/pdf-viewer/index.html?file=%2Fwiki%2Fbirdland%2Fguitar%2Fpdf%2Ffour-brothers.pdf&title=Four%20Brothers&spread=2`

Pages are grouped as 1+2, 3+4, and so on. The last odd page remains visible on its own. A narrow screen stacks both selected pages vertically without changing the two-page stepping. Single-page view is available. Arrow keys, Page Up/Down, Home and End work when focus is not in a field.

The viewer accepts only HTTP(S) PDF URLs on its own origin. Optional `page` is a one-based target, aligned to the current spread. `embedded=1` hides the duplicate spread selector when the repertoire nodebook controls it.

Copy this exact matching pair from Forge's `plugins/instantwiki/vendor/` into `vendor/`:

- `pdf.js`: PDF.js 6.4.299, SHA-256 `4c16d74f623721a3558c5f58cecbda395639b2d4009bca57a120d197127808da`.
- `pdf-worker.js`: SHA-256 `dbf93a537161174993a4549944ed83f61064412c75ecc3a82983e434936ca324`.
- `PDFJS-LICENSE.txt`: upstream Apache 2.0 license.

The vendor files are unchanged CommonJS bundles. `viewer.js` and `pdf-worker.mjs` adapt them to browser modules; the matching worker can run in a real worker or PDF.js's fallback. PDF evaluation and XFA are disabled. No CDN or external conversion service is used.

For the same-origin parent nodebook, the child sends `birdland-pdf:ready` after its first completed render and `birdland-pdf:state` thereafter. Both include `{pages,page,spread}`. Parent commands use `{type:'birdland-pdf:command',command:'next'|'previous'|'go'|'spread',page,spread}`. At a boundary, the child emits `{type:'birdland-pdf:boundary',direction:'next'|'previous',delta:1|-1}`. Both directions verify the message origin and source window. The standalone viewer simply stops at document boundaries.

Rendering is cancelled on newer navigation requests; stale asynchronous pages cannot replace the current spread. Canvas memory is bounded per rendered page, and only the visible one/two pages are rendered.

Run pure pagination and URL tests with:

```sh
node --test scripts/test_birdland_pdf_viewer.mjs
```
