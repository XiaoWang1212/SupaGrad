from __future__ import annotations

import re

from flask import Blueprint, jsonify, request, render_template
from supabase import create_client

from src.config import BaseConfig

curriculum_bp = Blueprint("curriculum", __name__, url_prefix="/api/curriculum")


def _get_supabase():
    url = BaseConfig.SUPABASE_URL
    key = BaseConfig.SUPABASE_KEY
    return create_client(url, key)


@curriculum_bp.route("/view", methods=["GET"])
def view_curriculum_page():
    """顯示課程表 HTML 頁面"""
    return render_template("curriculum.html")


def _normalize_program_name(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    normalized = re.sub(r"\s*/\s*", " / ", normalized)
    return normalized


def _program_name_search_candidates(value: str) -> list[str]:
    normalized = _normalize_program_name(value)
    candidates: list[str] = []

    def add_candidate(candidate: str):
        candidate = candidate.strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add_candidate(normalized)
    add_candidate(value.strip())

    if "/" in normalized:
        before_slash = normalized.split("/", 1)[0].strip()
        add_candidate(before_slash)
        add_candidate(normalized.replace(" / ", " "))

    tokens = re.split(r"\s+", normalized)
    for i in range(len(tokens) - 1, 0, -1):
        add_candidate(" ".join(tokens[:i]))

    trimmed = normalized
    while len(trimmed) > 4:
        trimmed = trimmed[:-1].rstrip()
        add_candidate(trimmed)

    return candidates


def _find_matching_program_name(client, raw_name: str) -> str | None:
    candidates = _program_name_search_candidates(raw_name)
    res = client.table("program_rules").select("program_name").execute()
    rows = res.data or []
    program_names = sorted(
        {row.get("program_name", "").strip() for row in rows if row.get("program_name")}
    )

    # Exact normalized match against real database names
    for candidate in candidates:
        normalized_candidate = _normalize_program_name(candidate)
        for name in program_names:
            if _normalize_program_name(name) == normalized_candidate:
                return name

    # Partial containment match
    for candidate in candidates:
        lower_candidate = candidate.lower()
        for name in program_names:
            lower_name = name.lower()
            if lower_candidate in lower_name or lower_name in lower_candidate:
                return name

    # Fallback to database ilike search if no local name matches
    for candidate in candidates:
        res = (
            client.table("program_rules")
            .select("program_name")
            .ilike("program_name", f"%{candidate}%")
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0].get("program_name")

    return None


@curriculum_bp.route("/", methods=["GET"])
def get_curriculum_by_program():
    """依據使用者科系取得課程表

    Query params:
    - program_name: 科系名稱 (必須)

    Returns:
        {
            "program_name": "...",
            "courses": [
                {
                    "course_name": "...",
                    "course_ids": [...],
                    "credits": 3,
                    "category": "共同必修",
                    "schedule": {
                        "year1_fall": 3,
                        "year1_spring": null,
                        ...
                    }
                },
                ...
            ],
            "summary": {
                "total_courses": 50,
                "total_credits": 128,
                "by_category": {
                    "共同必修": {...},
                    "系訂必修": {...},
                    ...
                }
            }
        }
    """
    program_name = request.args.get("program_name", "").strip()

    if not program_name:
        return jsonify({"error": "缺少 program_name 參數"}), 400

    try:
        client = _get_supabase()
        matched_program_name = _find_matching_program_name(client, program_name)

        if matched_program_name:
            program_name = matched_program_name
        else:
            return (
                jsonify(
                    {
                        "program_name": program_name,
                        "courses": [],
                        "summary": {"error": "找不到對應的科系資料"},
                    }
                ),
                404,
            )

        rows = (
            client.table("program_rules")
            .select(
                "course_name, course_ids, credits, category, "
                "year1_fall, year1_spring, year2_fall, year2_spring, "
                "year3_fall, year3_spring, year4_fall, year4_spring"
            )
            .eq("program_name", program_name)
            .execute()
        )
        rows = rows.data or []

        if not rows:
            return (
                jsonify(
                    {
                        "program_name": program_name,
                        "courses": [],
                        "summary": {"error": "找不到該科系"},
                    }
                ),
                404,
            )

        # 整理課程資料
        courses = []
        category_stats = {}
        total_credits = 0

        for row in rows:
            schedule = {
                "year1_fall": row.get("year1_fall"),
                "year1_spring": row.get("year1_spring"),
                "year2_fall": row.get("year2_fall"),
                "year2_spring": row.get("year2_spring"),
                "year3_fall": row.get("year3_fall"),
                "year3_spring": row.get("year3_spring"),
                "year4_fall": row.get("year4_fall"),
                "year4_spring": row.get("year4_spring"),
            }

            course = {
                "course_name": row.get("course_name"),
                "course_ids": row.get("course_ids") or [],
                "credits": row.get("credits"),
                "category": row.get("category") or "未分類",
                "schedule": schedule,
            }
            courses.append(course)

            # 統計
            cat = course["category"]
            if cat not in category_stats:
                category_stats[cat] = {
                    "count": 0,
                    "total_credits": 0,
                }
            category_stats[cat]["count"] += 1
            if course["credits"]:
                category_stats[cat]["total_credits"] += course["credits"]
                total_credits += course["credits"]

        return (
            jsonify(
                {
                    "program_name": program_name,
                    "courses": courses,
                    "summary": {
                        "total_courses": len(courses),
                        "total_credits": total_credits,
                        "by_category": category_stats,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@curriculum_bp.route("/programs", methods=["GET"])
def list_all_programs():
    """列出所有科系清單"""
    try:
        client = _get_supabase()

        res = client.table("program_rules").select("program_name").execute()
        rows = res.data or []

        # 去重
        programs = sorted(
            set(row["program_name"] for row in rows if row.get("program_name"))
        )

        return (
            jsonify(
                {
                    "programs": programs,
                    "total": len(programs),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
