from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path
from typing import Any
import os

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from supabase import create_client
from src.config import BaseConfig


CSV_PATH = Path("data/program_rules.csv")
BATCH_SIZE = 500


def parse_course_ids(value: str) -> list[str]:
    value = (value or "").strip()
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass

    value = value.strip("[]")
    return [
        part.strip().strip("'").strip('"') for part in value.split(",") if part.strip()
    ]


def parse_credits(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_float(value: str) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_rows(csv_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "program_name": (row.get("program_name") or "").strip(),
                    "source_file": (row.get("source_file") or "").strip(),
                    "category": (row.get("category") or "").strip() or None,
                    "course_name": (row.get("course_name") or "").strip(),
                    "course_ids": parse_course_ids(row.get("course_ids") or ""),
                    "credits": parse_credits(row.get("credits") or ""),
                    "note": (row.get("note") or "").strip() or None,
                    "raw": None,
                    "row_type": "course",
                    "year1_fall": parse_float(row.get("year1_fall") or ""),
                    "year1_spring": parse_float(row.get("year1_spring") or ""),
                    "year2_fall": parse_float(row.get("year2_fall") or ""),
                    "year2_spring": parse_float(row.get("year2_spring") or ""),
                    "year3_fall": parse_float(row.get("year3_fall") or ""),
                    "year3_spring": parse_float(row.get("year3_spring") or ""),
                    "year4_fall": parse_float(row.get("year4_fall") or ""),
                    "year4_spring": parse_float(row.get("year4_spring") or ""),
                }
            )

    return rows


def chunked(items: list[dict[str, Any]], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _get_env(*names: str) -> str:
    for n in names:
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


def main() -> None:
    url = _get_env("SUPABASE_URL")
    key = _get_env("SUPABASE_KEY", "SUPABASE_SECRET_KEY")

    if not url or not key:
        raise RuntimeError("缺少 SUPABASE_URL 或 SUPABASE_SECRET_KEY")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"找不到檔案：{CSV_PATH.resolve()}")

    client = create_client(url, key)
    rows = load_rows(CSV_PATH)

    if not rows:
        print("沒有可匯入的資料")
        return

    total = 0
    for batch in chunked(rows, BATCH_SIZE):
        res = client.table("program_rules").insert(batch).execute()
        total += len(res.data or [])
        print(f"已匯入 {len(res.data or [])} 筆")

    print(f"完成，共匯入 {total} 筆")


if __name__ == "__main__":
    main()
