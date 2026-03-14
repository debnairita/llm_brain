#!/usr/bin/env python3
"""
Anvaya file ingestion helper.

Extracts text and metadata from a file so Claude Code can classify
and store it. Prints a JSON blob to stdout.

Usage:
    python scripts/ingest.py <file_path>
"""

import json
import sys
from pathlib import Path


def extract_pdf(path: Path) -> str:
    import PyPDF2
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text.strip())
    return "\n\n".join(text_parts)


def extract_image(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception as e:
        return f"[Image — OCR unavailable: {e}]"


def extract_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


SUFFIX_MAP = {
    ".pdf": ("pdf", extract_pdf),
    ".txt": ("text", extract_text),
    ".md": ("text", extract_text),
    ".csv": ("text", extract_text),
    ".json": ("text", extract_text),
    ".yaml": ("text", extract_text),
    ".yml": ("text", extract_text),
    ".png": ("image", extract_image),
    ".jpg": ("image", extract_image),
    ".jpeg": ("image", extract_image),
    ".gif": ("image", extract_image),
    ".bmp": ("image", extract_image),
    ".tiff": ("image", extract_image),
    ".webp": ("image", extract_image),
}


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/ingest.py <file_path>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists():
        print(json.dumps({"error": f"File not found: {path}"}))
        sys.exit(1)

    suffix = path.suffix.lower()
    file_type, extractor = SUFFIX_MAP.get(suffix, ("unknown", None))

    if extractor is None:
        # Try reading as plain text anyway
        try:
            content = extract_text(path)
            file_type = "text"
        except Exception as e:
            content = f"[Could not read file: {e}]"
    else:
        try:
            content = extractor(path)
        except Exception as e:
            content = f"[Extraction failed: {e}]"

    result = {
        "file_name": path.name,
        "file_type": file_type,
        "size_bytes": path.stat().st_size,
        "content": content,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
