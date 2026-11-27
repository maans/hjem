#!/usr/bin/env python3
"""Extract reviewed guitar-book pages and replace only their wiki preview URLs.

Source books are never published. --download-public uses no saved cookies or
credentials; all books must be anonymously retrievable PDFs of the exact
reviewed sizes before any public file is written. For local fixtures,
--source-dir accepts book-N.pdf or the original book name.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

from update_abc_plugin import SCRIPT, ATTRIBUTE, array_items

IFRAME = re.compile(r"<iframe\b[^>]*>(?:[\s\S]*?</iframe\s*>)?", re.I)
ANCHOR = re.compile(r"<a\b[^>]*>[\s\S]*?</a\s*>", re.I)
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
DIRECT_LABEL = "Åbn noderne som PDF"


class SourceUnavailable(ValueError):
    pass


def read_manifest(path: Path) -> tuple[list[dict], list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    books, entries = data.get("books", []), data.get("entries", [])
    if not 1 <= len(books) <= 3 or not entries:
        raise ValueError("Expected one to three reviewed books and song entries")
    by_number, ids = {}, set()
    for book in books:
        number, source_id, size = book.get("number"), book.get("id"), book.get("size")
        if type(number) is not int or number < 1 or number in by_number:
            raise ValueError("Invalid or duplicate book number")
        if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", source_id) or source_id in ids:
            raise ValueError("Invalid or duplicate reviewed source")
        if type(size) is not int or size <= 0:
            raise ValueError("Every reviewed source needs its exact positive byte size")
        by_number[number] = book
        ids.add(source_id)
    titles, slugs = set(), set()
    for entry in entries:
        title, slug = entry.get("title"), entry.get("slug")
        book = by_number.get(entry.get("book"))
        start, end = entry.get("start"), entry.get("end")
        if not title or title in titles or not isinstance(slug, str) or not SLUG.fullmatch(slug) or slug in slugs:
            raise ValueError("Song titles and safe PDF slugs must be unique")
        if not book or entry.get("drive_id") != book["id"]:
            raise ValueError(f"Song {title!r} does not match its reviewed source book")
        if type(start) is not int or type(end) is not int or not 1 <= start <= end:
            raise ValueError(f"Invalid inclusive page range for {title!r}")
        titles.add(title)
        slugs.add(slug)
    return books, entries


def validate_source(path: Path, book: dict) -> None:
    if not path.is_file() or path.stat().st_size != book["size"]:
        raise SourceUnavailable(f"Book {book['number']}: PDF byte size does not match the reviewed source")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise SourceUnavailable(f"Book {book['number']}: source is not a PDF")


def download_public(book: dict, target: Path, temporary_home: Path) -> None:
    # gdown explicitly disables persisted cookies. NETRC points at a nonexistent
    # file so requests cannot silently obtain user credentials from ~/.netrc.
    old_netrc = os.environ.get("NETRC")
    os.environ["NETRC"] = str(temporary_home / "no-credentials.netrc")
    try:
        # A fresh process also bounds stalled network requests without leaving
        # a downloader running after the temporary source files are discarded.
        code = ("import gdown,sys; result=gdown.download(id=sys.argv[1],output=sys.argv[2],"
                "quiet=True,use_cookies=False,verify=True,resume=False); sys.exit(0 if result else 1)")
        subprocess.run([sys.executable, "-c", code, book["id"], str(target)],
                       check=True, timeout=150, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        validate_source(target, book)
    except Exception:
        raise SourceUnavailable(f"Book {book['number']}: anonymous PDF download failed; no public outputs were changed") from None
    finally:
        if old_netrc is None:
            os.environ.pop("NETRC", None)
        else:
            os.environ["NETRC"] = old_netrc


def source_path(directory: Path, book: dict) -> Path:
    candidates = [directory / f"book-{book['number']}.pdf"]
    name = book.get("name")
    if name and Path(name).name == name:
        candidates.append(directory / name)
    candidates.append(directory / f"{book['id']}.pdf")
    found = next((path for path in candidates if path.is_file()), candidates[0])
    validate_source(found, book)
    return found


def attrs(tag: str) -> dict[str, re.Match]:
    return {match["name"].lower(): match for match in ATTRIBUTE.finditer(tag)}


def is_expected_drive_url(value: str, source_id: str) -> bool:
    parsed = urlsplit(value.replace("&amp;", "&"))
    return parsed.scheme == "https" and parsed.hostname == "drive.google.com" and bool(
        re.fullmatch(r"/file/d/" + re.escape(source_id) + r"/(?:preview|view)/?", parsed.path))


def text_edits(text: str, entry: dict) -> list[tuple[int, int, str]]:
    """Return only iframe-src and adjacent link edits in decoded tiddler text."""
    relative = f"pdf/{entry['slug']}.pdf"
    matches = []
    for match in IFRAME.finditer(text):
        source = attrs(match.group()).get("src")
        if not source:
            continue
        value = source["value"]
        local = value.removeprefix("./").split("#", 1)[0] == relative
        if local or is_expected_drive_url(value, entry["drive_id"]):
            matches.append((match, source, local))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one matching score iframe in {entry['title']!r}")
    iframe, source, local = matches[0]
    edits = []
    if not local:
        edits.append((iframe.start() + source.start("value"), iframe.start() + source.end("value"), relative + "#view=FitH"))
    linked = False
    for anchor in ANCHOR.finditer(text):
        href = attrs(anchor.group()).get("href")
        if href and href["value"].removeprefix("./").split("#", 1)[0] == relative and DIRECT_LABEL in anchor.group():
            linked = True
        if href and is_expected_drive_url(href["value"], entry["drive_id"]):
            label = "Åbn originalen i Drev"
            index = anchor.group().find(">" + label + "</a>")
            if index >= 0:
                begin = anchor.start() + index + 1
                edits.append((begin, begin + len(label), "Åbn hele guitarmappen i Drev"))
    if not linked:
        link = f'\n<p><a href="{relative}" target="_blank" rel="noopener">{DIRECT_LABEL}</a></p>'
        edits.append((iframe.end(), iframe.end(), link))
    return edits


def object_text_span(raw: str) -> tuple[str, int, int]:
    """Find the text value's JSON string while retaining every other raw byte."""
    decoder = json.JSONDecoder()
    at = 0
    while at < len(raw) and raw[at].isspace():
        at += 1
    if raw[at:at + 1] != "{":
        raise ValueError("Expected a tiddler object")
    at += 1
    found = None
    keys = set()
    while True:
        while at < len(raw) and raw[at].isspace():
            at += 1
        if raw[at:at + 1] == "}":
            break
        key, at = decoder.raw_decode(raw, at)
        if key in keys:
            raise ValueError("Duplicate tiddler field")
        keys.add(key)
        while at < len(raw) and raw[at].isspace():
            at += 1
        if raw[at:at + 1] != ":":
            raise ValueError("Invalid tiddler field separator")
        at += 1
        while at < len(raw) and raw[at].isspace():
            at += 1
        start = at
        value, at = decoder.raw_decode(raw, at)
        if key == "text":
            if not isinstance(value, str):
                raise ValueError("The score text must be a JSON string")
            found = (value, start, at)
        while at < len(raw) and raw[at].isspace():
            at += 1
        if raw[at:at + 1] == "}":
            break
        if raw[at:at + 1] != ",":
            raise ValueError("Invalid tiddler field separator")
        at += 1
    if found is None:
        raise ValueError("The score tiddler has no text")
    return found


def json_string_offsets(raw: str) -> list[int]:
    """Map decoded character boundaries to original JSON-encoded boundaries."""
    if not raw.startswith('"') or not raw.endswith('"'):
        raise ValueError("Expected a JSON string")
    offsets, at = [1], 1
    while at < len(raw) - 1:
        if raw[at] != "\\":
            at += 1
        elif raw[at + 1] != "u":
            at += 2
        else:
            point = int(raw[at + 2:at + 6], 16)
            at += 6
            if 0xD800 <= point <= 0xDBFF and raw[at:at + 2] == "\\u" and 0xDC00 <= int(raw[at + 2:at + 6], 16) <= 0xDFFF:
                at += 6
        offsets.append(at)
    return offsets


def encoded_fragment(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)[1:-1].replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def patch_wiki(html: str, entries: list[dict]) -> tuple[str, int]:
    by_title = {entry["title"]: entry for entry in entries}
    found, replacements = set(), []
    for store in SCRIPT.finditer(html):
        attributes = {match["name"].lower(): match["value"] for match in ATTRIBUTE.finditer(store["attrs"])}
        if "tiddlywiki-tiddler-store" not in attributes.get("class", "").split() or attributes.get("type", "").lower() != "application/json":
            continue
        for item, start, end in array_items(store["body"]):
            title = item.get("title") if isinstance(item, dict) else None
            if title not in by_title:
                continue
            if title in found:
                raise ValueError(f"Duplicate target tiddler: {title!r}")
            found.add(title)
            base = store.start("body") + start
            raw = html[base:store.start("body") + end]
            text, value_start, value_end = object_text_span(raw)
            offsets = json_string_offsets(raw[value_start:value_end])
            if len(offsets) != len(text) + 1:
                raise ValueError("JSON string character mapping failed")
            for begin, finish, value in text_edits(text, by_title[title]):
                replacements.append((base + value_start + offsets[begin], base + value_start + offsets[finish], encoded_fragment(value)))
    missing = set(by_title) - found
    if missing:
        raise ValueError(f"Missing {len(missing)} reviewed score tiddlers")
    for start, end, value in sorted(replacements, reverse=True):
        html = html[:start] + value + html[end:]
    return html, len(replacements)


def raster_sample(entries: list[dict], limit: int = 8) -> set[str]:
    ordered = sorted(entries, key=lambda entry: (entry["book"], entry["start"], entry["slug"]))
    picked = {entry["slug"] for entry in ordered if entry["title"].casefold() == "four brothers"}
    for book in sorted({entry["book"] for entry in entries}):
        options = [entry for entry in ordered if entry["book"] == book]
        picked.update((options[0]["slug"], options[-1]["slug"]))
    for entry in ordered:
        if len(picked) >= limit:
            break
        picked.add(entry["slug"])
    return picked


def validate_output(path: Path, entry: dict, source_document, raster: bool) -> int:
    from pypdf import PdfReader
    reader = PdfReader(str(path), strict=True)
    expected = entry["end"] - entry["start"] + 1
    if len(reader.pages) != expected or reader.metadata.title != entry["title"]:
        raise ValueError(f"Extracted PDF validation failed for {entry['title']!r}")
    if not raster:
        return 0
    import fitz
    checks = 0
    with fitz.open(path) as output:
        for output_index in sorted({0, expected - 1}):
            original = source_document[entry["start"] - 1 + output_index].get_pixmap(matrix=fitz.Matrix(0.75, 0.75), alpha=False)
            extracted = output[output_index].get_pixmap(matrix=fitz.Matrix(0.75, 0.75), alpha=False)
            if (original.width, original.height, original.n) != (extracted.width, extracted.height, extracted.n) or hashlib.sha256(original.samples).digest() != hashlib.sha256(extracted.samples).digest():
                raise ValueError(f"Extracted page rendering changed for {entry['title']!r}")
            checks += 1
    return checks


def atomic_write(path: Path, data: bytes) -> bool:
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".guitar-preview-", dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        return True
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


def run(manifest: Path, wiki: Path, *, source_dir: Path | None = None, download: bool = False) -> dict:
    from pypdf import PdfReader, PdfWriter
    import fitz
    books, entries = read_manifest(manifest)
    if (source_dir is None) == (not download):
        raise ValueError("Choose exactly one of --source-dir or --download-public")
    original = wiki.read_bytes()
    patched, edits = patch_wiki(original.decode("utf-8"), entries)
    sample = raster_sample(entries)
    with tempfile.TemporaryDirectory(prefix="guitar-pdf-previews-") as temporary:
        staging = Path(temporary)
        sources, readers, documents = {}, {}, {}
        try:
            # Validate ALL anonymous downloads before extraction or public writes.
            for book in books:
                path = staging / f"book-{book['number']}.pdf" if download else source_path(source_dir, book)
                if download:
                    download_public(book, path, staging)
                validate_source(path, book)
                reader = PdfReader(str(path), strict=True)
                if reader.is_encrypted:
                    raise SourceUnavailable(f"Book {book['number']}: encrypted source is unsupported")
                readers[book["number"]] = reader
                documents[book["number"]] = fitz.open(path)
                sources[book["number"]] = path
            raster_checks, total_pages, generated = 0, 0, []
            for entry in entries:
                reader = readers[entry["book"]]
                if entry["end"] > len(reader.pages):
                    raise ValueError(f"Page range exceeds source book for {entry['title']!r}")
                writer = PdfWriter()
                for index in range(entry["start"] - 1, entry["end"]):
                    writer.add_page(reader.pages[index])
                writer.add_metadata({"/Title": entry["title"]})
                output = staging / f"{entry['slug']}.pdf"
                with output.open("wb") as stream:
                    writer.write(stream)
                raster_checks += validate_output(output, entry, documents[entry["book"]], entry["slug"] in sample)
                total_pages += entry["end"] - entry["start"] + 1
                generated.append((entry, output))
            # No file is published until all sources, ranges, PDFs, wiki edits
            # and bounded source/output raster comparisons have passed.
            written = 0
            for entry, output in generated:
                written += atomic_write(wiki.parent / "pdf" / output.name, output.read_bytes())
            wiki_changed = atomic_write(wiki, patched.encode("utf-8"))
            return {"books": len(books), "pdfs": len(entries), "pages": total_pages,
                    "raster_checks": raster_checks, "written_pdfs": written,
                    "wiki_changed": wiki_changed, "text_edits": edits}
        finally:
            for document in documents.values():
                document.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--manifest", type=Path, default=root / "scripts/guitar-pdf-pages.json")
    parser.add_argument("--wiki", type=Path, default=root / "wiki/birdland/guitar/index.html")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-dir", type=Path)
    source.add_argument("--download-public", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.manifest, args.wiki, source_dir=args.source_dir, download=args.download_public)
    except Exception as error:
        parser.exit(1, f"Guitar PDF previews: {type(error).__name__}: {error}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
