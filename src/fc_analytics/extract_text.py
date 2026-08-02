"""
Extract text from regular-issue Fine Cooking PDFs.

For each "FC_NNN ....pdf" under data/raw/, extract per-page text
and write it to data/processed/text_raw/FC_NNN.txt.

For each page, PyMuPDF's embedded text layer is used if present; pages with
little or no embedded text (i.e. scanned images) fall back to Tesseract OCR.

Some issues' embedded fonts encode fraction glyphs (1/2, 1/4, etc.) as
nonstandard character codes with broken/missing ToUnicode mappings, which
extract as garbage (e.g. "'Iz" instead of "1/2"). This can't be reliably
auto-corrected: the corrupted glyphs also misreport their own bounding
boxes, which defeats crop-and-re-OCR, and Tesseract misreads them even when
manually isolated. Instead, lines containing likely-broken fraction glyphs
are flagged in a companion data/processed/review/FC_NNN.txt file for manual
correction; hand-corrected text belongs in data/processed/text_clean/.

By default, issues that already have an output .txt file are skipped;
pass --force to reprocess everything.
"""

import argparse
import io
import re
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from fc_analytics.paths import RAW_DIR, REVIEW_DIR, TEXT_RAW_DIR

ISSUE_DIR_RE = re.compile(r"^FC_\d+-\d+$")
ISSUE_NUMBER_RE = re.compile(r"FC_(\d+)")

MIN_TEXT_CHARS = 20
OCR_DPI = 300

# A character whose reported glyph width is ~0 is a side effect of the
# broken ligature encoding used for fraction glyphs in some issues' fonts.
# The literal Unicode replacement character shows up where a font's
# ToUnicode mapping is missing entirely.
MIN_GLYPH_WIDTH = 0.3
REPLACEMENT_CHAR = "�"

# Restricts flagged lines to ones that look like ingredient quantities, since
# the raw glyph-width signal alone fires on all kinds of unrelated kerning
# artifacts throughout the body text (not just fractions), which would make
# the review file too noisy to be useful.
UNIT_RE = re.compile(
    r"\b(cups?|tsp\.?|tbsp?\.?|teaspoons?|tablespoons?|oz\.?|ounces?|lbs?\.?|pounds?|"
    r"pt\.?|pints?|qt\.?|quarts?|gal\.?|gallons?|pinch(es)?|cloves?|sticks?|in\.|inch(es)?)\b",
    re.IGNORECASE,
)


def find_regular_issue_pdfs(input_dir: Path) -> list[Path]:
    pdfs = [
        pdf
        for issue_dir in sorted(input_dir.iterdir())
        if issue_dir.is_dir() and ISSUE_DIR_RE.match(issue_dir.name)
        for pdf in sorted(issue_dir.glob("*.pdf"))
    ]
    return pdfs


def issue_output_path(pdf_path: Path, output_dir: Path) -> Path:
    match = ISSUE_NUMBER_RE.search(pdf_path.stem)
    if not match:
        raise ValueError(f"Could not find issue number in filename: {pdf_path.name}")
    issue_number = int(match.group(1))
    return output_dir / f"FC_{issue_number:03d}.txt"


def _line_words(line: dict) -> list[list[dict]]:
    """Group a rawdict line's chars into whitespace-separated words."""
    words: list[list[dict]] = []
    current: list[dict] = []
    for span in line["spans"]:
        for ch in span["chars"]:
            if ch["c"].isspace():
                if current:
                    words.append(current)
                    current = []
            else:
                current.append(ch)
    if current:
        words.append(current)
    return words


def _is_suspect_word(word_chars: list[dict]) -> bool:
    text = "".join(ch["c"] for ch in word_chars)
    if REPLACEMENT_CHAR in text:
        return True
    return any((ch["bbox"][2] - ch["bbox"][0]) < MIN_GLYPH_WIDTH for ch in word_chars)


def find_suspect_lines(page: fitz.Page) -> list[str]:
    """Return the text of lines that likely contain a broken fraction glyph."""
    suspect_lines = []
    raw = page.get_text("rawdict")
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            words = _line_words(line)
            if any(_is_suspect_word(w) for w in words):
                line_text = "".join(ch["c"] for span in line["spans"] for ch in span["chars"]).strip()
                if UNIT_RE.search(line_text):
                    suspect_lines.append(line_text)
    return suspect_lines


def extract_page_text(page: fitz.Page) -> tuple[str, bool, list[str]]:
    """Return (text, was_ocr, suspect_fraction_lines) for a single page."""
    text = page.get_text().strip()
    if len(text) >= MIN_TEXT_CHARS:
        return text, False, find_suspect_lines(page)

    pixmap = page.get_pixmap(dpi=OCR_DPI)
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    ocr_text = pytesseract.image_to_string(image).strip()
    return ocr_text, True, []


def extract_pdf_text(pdf_path: Path) -> tuple[str, int, list[tuple[int, str]]]:
    """Return (full_text, ocr_page_count, suspect_fraction_lines) for a PDF.

    suspect_fraction_lines is a list of (page_number, line_text).
    """
    parts = []
    ocr_page_count = 0
    suspect_lines: list[tuple[int, str]] = []
    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            text, was_ocr, page_suspect_lines = extract_page_text(page)
            if was_ocr:
                ocr_page_count += 1
            suspect_lines.extend((page_number, line) for line in page_suspect_lines)
            parts.append(f"--- Page {page_number} ---\n{text}")
    return "\n\n".join(parts), ocr_page_count, suspect_lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output-dir", type=Path, default=TEXT_RAW_DIR)
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    parser.add_argument(
        "--force", action="store_true", help="Reprocess issues that already have output text files."
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.review_dir.mkdir(parents=True, exist_ok=True)

    pdfs = find_regular_issue_pdfs(args.input_dir)
    processed = skipped = failed = 0
    total_ocr_pages = 0
    total_suspect_lines = 0

    for pdf_path in pdfs:
        try:
            output_path = issue_output_path(pdf_path, args.output_dir)
        except ValueError as exc:
            print(f"SKIP (bad filename): {pdf_path.name}: {exc}")
            failed += 1
            continue

        if output_path.exists() and not args.force:
            skipped += 1
            continue

        print(f"Processing {pdf_path.name} -> {output_path.name}")
        try:
            text, ocr_page_count, suspect_lines = extract_pdf_text(pdf_path)
        except Exception as exc:
            print(f"FAILED: {pdf_path.name}: {exc}")
            failed += 1
            continue

        output_path.write_text(text, encoding="utf-8")

        review_path = args.review_dir / output_path.name
        if suspect_lines:
            review_text = "\n".join(f"Page {page_number}: {line}" for page_number, line in suspect_lines)
            review_path.write_text(review_text, encoding="utf-8")
        elif review_path.exists():
            review_path.unlink()

        total_ocr_pages += ocr_page_count
        total_suspect_lines += len(suspect_lines)
        processed += 1
        if ocr_page_count:
            print(f"  {ocr_page_count} page(s) required OCR")
        if suspect_lines:
            print(f"  {len(suspect_lines)} line(s) flagged for fraction review -> {review_path.name}")

    print(
        f"\nDone. Processed {processed}, skipped {skipped}, failed {failed} "
        f"(of {len(pdfs)} total). OCR used on {total_ocr_pages} page(s). "
        f"{total_suspect_lines} line(s) flagged for fraction review."
    )


if __name__ == "__main__":
    main()
