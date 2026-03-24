from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path


DEFAULT_TARGET_DIR = Path.home() / "Desktop" / "Desktop_Triage" / "AI_Staging_Ground" / "Documents"


def build_pdf_metadata_header(pdf_path: Path) -> str:
    import fitz  # PyMuPDF

    file_stat = os.stat(pdf_path)
    mac_date = datetime.fromtimestamp(file_stat.st_birthtime).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with fitz.open(pdf_path) as doc:
        internal_meta = doc.metadata.get("creationDate", "Unknown Internal Date")

    header = "--- DOCUMENT METADATA ---\n"
    header += f"Original File: {pdf_path.name}\n"
    header += f"Internal PDF Date: {internal_meta}\n"
    header += f"Mac File Saved Date: {mac_date}\n"
    header += "--- END METADATA ---\n\n"
    return header


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        import fitz  # PyMuPDF

        with fitz.open(pdf_path) as doc:
            return "\n".join(page.get_text("text") for page in doc)
    except ImportError:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        chunks: list[str] = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)


def extract_docx_text(docx_path: Path) -> str:
    try:
        import docx2txt

        return docx2txt.process(str(docx_path)) or ""
    except ImportError:
        from docx import Document

        doc = Document(str(docx_path))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def convert_to_txt(source_path: Path) -> Path:
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        text = build_pdf_metadata_header(source_path) + extract_pdf_text(source_path)
    elif suffix == ".docx":
        text = extract_docx_text(source_path)
    else:
        raise ValueError(f"Unsupported file type: {source_path}")

    out_path = source_path.with_suffix(".txt")
    out_path.write_text(text, encoding="utf-8", errors="ignore")
    return out_path


def run(target_dir: Path, no_overwrite: bool = False) -> int:
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Target directory does not exist: {target_dir}")

    candidates = [
        path
        for path in target_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".pdf", ".docx"}
    ]

    converted = 0
    skipped = 0
    failed = 0

    for source in candidates:
        try:
            out_path = source.with_suffix(".txt")
            if no_overwrite and out_path.exists():
                print(f"Skipped (exists): {out_path}")
                skipped += 1
                continue

            out_path = convert_to_txt(source)
            print(f"Converted: {source.name} -> {out_path.name}")
            converted += 1
        except Exception as exc:
            print(f"Failed: {source} ({exc})")
            failed += 1

    print(
        f"\nDone. Converted {converted} file(s); skipped {skipped} file(s); {failed} failure(s)."
    )
    return 0 if failed == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract text from .pdf and .docx files into .txt files in-place."
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET_DIR,
        help=f"Folder to scan (default: {DEFAULT_TARGET_DIR})",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Skip files where same-name .txt already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raise SystemExit(
        run(args.target.expanduser().resolve(), no_overwrite=args.no_overwrite)
    )


if __name__ == "__main__":
    main()