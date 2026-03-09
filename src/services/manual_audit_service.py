import csv
import io
from datetime import datetime, timezone


def _parse_passed(value: str | None) -> bool:
    if value is None:
        return True
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "t", "yes", "y", "pass", "passed"}


def _parse_required_courses(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []

    chunks = raw_value.replace("\n", ",").split(",")
    return [course.strip().upper() for course in chunks if course.strip()]


def _read_csv_rows(file_storage) -> list[dict]:
    if not file_storage:
        return []

    content = file_storage.read()
    file_storage.stream.seek(0)

    if not content:
        return []

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _extract_credit_snapshot(rows: list[dict], source_name: str) -> tuple[int, set[str], int]:
    total_credits = 0
    passed_courses: set[str] = set()
    skipped_rows = 0

    for row in rows:
        course_id = str(row.get("course_id", "")).strip().upper()
        credits_raw = row.get("credits")

        if credits_raw in (None, ""):
            skipped_rows += 1
            continue

        try:
            credits = int(float(str(credits_raw).strip()))
        except ValueError as exc:
            raise ValueError(f"{source_name} 有無法解析的 credits: {credits_raw}") from exc

        if _parse_passed(row.get("passed")):
            total_credits += credits
            if course_id:
                passed_courses.add(course_id)

    return total_credits, passed_courses, skipped_rows


def audit_manual_upload(
    student_id: str,
    required_credits: int,
    required_courses_raw: str | None,
    transcript_file,
    transfer_file=None,
) -> dict:
    if required_credits <= 0:
        raise ValueError("required_credits 必須大於 0")

    transcript_rows = _read_csv_rows(transcript_file)
    if not transcript_rows:
        raise ValueError("transcript_file 內容為空或格式錯誤")

    transfer_rows = _read_csv_rows(transfer_file) if transfer_file else []

    transcript_credits, transcript_courses, transcript_skipped = _extract_credit_snapshot(
        transcript_rows, "transcript_file"
    )
    transfer_credits, transfer_courses, transfer_skipped = _extract_credit_snapshot(
        transfer_rows, "transfer_file"
    )

    completed_credits = transcript_credits + transfer_credits
    completed_courses = transcript_courses.union(transfer_courses)

    required_courses = _parse_required_courses(required_courses_raw)
    missing_required_courses = [
        course_id for course_id in required_courses if course_id not in completed_courses
    ]

    missing_credits = max(required_credits - completed_credits, 0)
    passed = missing_credits == 0 and len(missing_required_courses) == 0

    return {
        "student_id": student_id,
        "passed": passed,
        "summary": {
            "completed_credits": completed_credits,
            "required_credits": required_credits,
            "missing_credits": missing_credits,
            "required_course_count": len(required_courses),
            "missing_required_course_count": len(missing_required_courses),
        },
        "missing_required_courses": missing_required_courses,
        "data_stats": {
            "transcript_rows": len(transcript_rows),
            "transfer_rows": len(transfer_rows),
            "transcript_skipped_rows": transcript_skipped,
            "transfer_skipped_rows": transfer_skipped,
        },
        "source": "manual_upload",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
