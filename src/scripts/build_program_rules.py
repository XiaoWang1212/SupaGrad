from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pdfplumber
import pandas as pd


PDF_DIR = Path("pdfs")
PARSED_DIR = Path("parsed")
OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)


COURSE_ID_RE = re.compile(r"[A-Z]{1,4}\d{3,4}[A-Z]?(?:\s*/\s*[A-Z]{1,4}\d{3,4}[A-Z]?)*")
NUMBER_RE = re.compile(r"(\d+)")
MIN_GRAD_RE = re.compile(r"最低畢業學分[：:\s]*([0-9]+)")
REQUIRED_TOTAL_RE = re.compile(r"必修科目計[：:\s]*([0-9]+)")
ELECTIVE_MIN_RE = re.compile(r"選修至少\s*([0-9]+)\s*學分")
STAR_MIN_RE = re.compile(r"\*\s*課程至少選\s*([0-9]+)\s*門")


@dataclass
class ProgramSummary:
    program_name: str
    source_file: str
    minimum_graduation_credits: int | None = None
    required_credits: int | None = None
    elective_min_credits: int | None = None
    star_courses_min_count: int | None = None
    raw_notes: list[str] | None = None


@dataclass
class ProgramRule:
    program_name: str
    source_file: str
    category: str
    course_name: str
    course_ids: list[str]
    credits: int | None
    note: str = ""
    year1_fall: float | None = None
    year1_spring: float | None = None
    year2_fall: float | None = None
    year2_spring: float | None = None
    year3_fall: float | None = None
    year3_spring: float | None = None
    year4_fall: float | None = None
    year4_spring: float | None = None


def normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_text_from_pdf(pdf_path: Path) -> str:
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text:
                parts.append(text)
    return "\n".join(parts)


def extract_summary(program_name: str, pdf_path: Path) -> ProgramSummary:
    text = extract_text_from_pdf(pdf_path)
    lines = [normalize(line) for line in text.splitlines() if normalize(line)]

    def find_int(pattern: re.Pattern[str]) -> int | None:
        m = pattern.search(text)
        return int(m.group(1)) if m else None

    return ProgramSummary(
        program_name=program_name,
        source_file=pdf_path.name,
        minimum_graduation_credits=find_int(MIN_GRAD_RE),
        required_credits=find_int(REQUIRED_TOTAL_RE),
        elective_min_credits=find_int(ELECTIVE_MIN_RE),
        star_courses_min_count=find_int(STAR_MIN_RE),
        raw_notes=lines,
    )


def split_course_ids(value: str) -> list[str]:
    if not value:
        return []
    ids = COURSE_ID_RE.findall(value)
    if ids:
        return [item.strip() for item in re.split(r"\s*/\s*", ids[0]) if item.strip()]
    return []


def extract_course_name_and_ids(cell: str) -> tuple[str, list[str]]:
    cell = normalize(cell)
    if not cell:
        return "", []
    ids = split_course_ids(cell)
    if ids:
        name = normalize(COURSE_ID_RE.sub("", cell))
        name = re.sub(r"[／/()（）【】\[\]、,]+$", "", name).strip()
        return name, ids
    return cell, []


def parse_credits(row: list[str]) -> int | None:
    for idx in (2, 3, 4, 5):
        if idx < len(row):
            cell = normalize(row[idx])
            if cell.isdigit():
                return int(cell)
            m = NUMBER_RE.search(cell)
            if m:
                return int(m.group(1))
    return None


def is_header_row(row: list[str]) -> bool:
    joined = " ".join(normalize(c) for c in row)
    return "課名及課號" in joined or "學分數" in joined or "第一學年" in joined


def _to_num(cell: str) -> float | None:
    cell = normalize(cell)
    if not cell:
        return None
    try:
        return float(cell)
    except ValueError:
        m = NUMBER_RE.search(cell)
        return float(m.group(1)) if m else None


def parse_semester_credits(row: list[str]) -> dict[str, float | None]:
    # 對應 CSV: [2..9] = 大一上, 大一下, 大二上, 大二下, 大三上, 大三下, 大四上, 大四下
    vals = [row[i] if i < len(row) else "" for i in range(2, 10)]
    nums = [_to_num(v) for v in vals]
    return {
        "year1_fall": nums[0],
        "year1_spring": nums[1],
        "year2_fall": nums[2],
        "year2_spring": nums[3],
        "year3_fall": nums[4],
        "year3_spring": nums[5],
        "year4_fall": nums[6],
        "year4_spring": nums[7],
    }


def parse_rules_from_csv(program_name: str, csv_path: Path) -> list[ProgramRule]:
    rules: list[ProgramRule] = []
    current_category = ""

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    for row in rows:
        row = [normalize(cell) for cell in row]
        if not any(row):
            continue
        if is_header_row(row):
            continue

        first = row[0] if len(row) > 0 else ""
        second = row[1] if len(row) > 1 else ""
        third = row[2] if len(row) > 2 else ""

        # 類別欄
        if first and not second and not third:
            current_category = first
            continue

        if first in {
            "共同 必修",
            "院訂 必修",
            "系訂 必修",
            "系訂 選修",
            "共同選修",
            "院訂選修",
        }:
            current_category = first

        # 盡量抓課程資料
        course_name, course_ids = extract_course_name_and_ids(second or first)
        credits = parse_credits(row)

        if not course_name:
            continue

        # 避免把標題/分類當作課程
        if course_name in {"共同", "院訂", "系訂", "必修", "選修"}:
            continue

        note = ""
        if first and first != current_category and second:
            note = first

        sem = parse_semester_credits(row)

        rules.append(
            ProgramRule(
                program_name=program_name,
                source_file=csv_path.name,
                category=current_category or first or "",
                course_name=course_name,
                course_ids=course_ids,
                credits=credits,
                note=note,
                **sem,
            )
        )

    return rules


def load_program_name_from_filename(path: Path) -> str:
    return path.stem.replace("_table_1", "").replace("_table_2", "").strip()


def main() -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    csvs = sorted(PARSED_DIR.glob("*_table_*.csv"))

    if not csvs:
        print(f"找不到 CSV：{PARSED_DIR.resolve()}")
        return

    all_summaries: list[dict[str, Any]] = []
    all_rules: list[dict[str, Any]] = []

    for csv_path in csvs:
        program_name = load_program_name_from_filename(csv_path)
        pdf_path = PDF_DIR / f"{program_name}.pdf"
        if not pdf_path.exists():
            # 允許 PDF 檔名和 CSV stem 不完全一致時手動改
            matches = list(PDF_DIR.glob(f"{program_name}*.pdf"))
            pdf_path = matches[0] if matches else pdf_path

        if pdf_path.exists():
            summary = extract_summary(program_name, pdf_path)
            all_summaries.append(asdict(summary))

        rules = parse_rules_from_csv(program_name, csv_path)
        all_rules.extend(asdict(r) for r in rules)

        print(f"[OK] {program_name}: rules={len(rules)}")

    (OUT_DIR / "program_summaries.json").write_text(
        json.dumps(all_summaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "program_rules.json").write_text(
        json.dumps(all_rules, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pd.DataFrame(all_rules).to_csv(
        OUT_DIR / "program_rules.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\n輸出完成：")
    print(f"- {OUT_DIR / 'program_summaries.json'}")
    print(f"- {OUT_DIR / 'program_rules.json'}")
    print(f"- {OUT_DIR / 'program_rules.csv'}")


if __name__ == "__main__":
    main()
