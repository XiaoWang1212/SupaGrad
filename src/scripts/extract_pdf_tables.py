from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber
import pandas as pd


PDF_DIR = Path("pdfs")
OUT_DIR = Path("parsed")
OUT_DIR.mkdir(exist_ok=True)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_tables_from_pdf(pdf_path: Path) -> list[list[list[str]]]:
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                page_tables = page.extract_tables()
            except Exception:
                page_tables = []

            for table in page_tables or []:
                cleaned = []
                for row in table:
                    cleaned.append([normalize_text(cell) for cell in (row or [])])
                if cleaned:
                    tables.append(cleaned)
    return tables


def save_tables(pdf_path: Path, tables: list[list[list[str]]]) -> None:
    stem = pdf_path.stem
    json_path = OUT_DIR / f"{stem}.json"
    csv_paths = []

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=2)

    for i, table in enumerate(tables, start=1):
        max_cols = max(len(r) for r in table) if table else 0
        rows = [r + [""] * (max_cols - len(r)) for r in table]
        df = pd.DataFrame(rows)
        csv_path = OUT_DIR / f"{stem}_table_{i}.csv"
        df.to_csv(csv_path, index=False, header=False, encoding="utf-8-sig")
        csv_paths.append(csv_path)

    print(f"[OK] {pdf_path.name}: {len(tables)} tables -> {json_path.name}, {len(csv_paths)} csv")


def main() -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"找不到 PDF：{PDF_DIR.resolve()}")
        return

    for pdf_path in pdfs:
        tables = extract_tables_from_pdf(pdf_path)
        if not tables:
            print(f"[WARN] {pdf_path.name}: 沒抓到表格")
            continue
        save_tables(pdf_path, tables)


if __name__ == "__main__":
    main()