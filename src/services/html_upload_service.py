import re

from bs4 import BeautifulSoup

from src.models.transcript import (
    CreditSummary,
    ParsedCourse,
    ParsedHtmlTranscript,
    ParsedStudent,
)


ALLOWED_EXTENSIONS = {".html", ".htm", ".webarchive"}


def _decode_html_bytes(raw_bytes: bytes) -> str:
    try:
        return raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw_bytes.decode("big5", errors="ignore")


def _extract_number(value: str | None) -> float | None:
    if not value:
        return None
    matched = re.search(r"-?\d+(?:\.\d+)?", value)
    if not matched:
        return None
    return float(matched.group(0))


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _is_course_passed(score_text: str) -> bool:
    score_text = _normalize_text(score_text)
    if not score_text:
        return False

    fail_keywords = {"停修", "退選", "不通過", "未通過", "fail", "failed"}
    pass_keywords = {"通過", "一般課程通過", "勞動服務通過", "pass", "passed"}

    lowered = score_text.lower()
    if any(keyword in score_text for keyword in fail_keywords) or any(
        keyword in lowered for keyword in fail_keywords
    ):
        return False
    if any(keyword in score_text for keyword in pass_keywords) or any(
        keyword in lowered for keyword in pass_keywords
    ):
        return True

    score_number = _extract_number(score_text)
    if score_number is None:
        return False
    return score_number >= 60


def _extract_student_field(soup: BeautifulSoup, label: str) -> str | None:
    labels = soup.select("div.fmlabel")
    for item in labels:
        if _normalize_text(item.get_text()) != label:
            continue
        sibling = item.find_next_sibling("div")
        if not sibling:
            return None
        target = sibling.select_one("span.fmreadonly") or sibling
        return _normalize_text(target.get_text(" ", strip=True))
    return None


def _extract_courses(soup: BeautifulSoup) -> list[ParsedCourse]:
    courses: list[ParsedCourse] = []

    tables = soup.select("table.table.table-bordered.table-hover")
    for table in tables:
        rows = table.select("tr")
        if len(rows) <= 2:
            continue

        header_text = _normalize_text(rows[0].get_text(" ", strip=True))
        term_match = re.search(r"第\d{3}學年度第\d學期", header_text)
        term = term_match.group(0) if term_match else None

        for row in rows[2:]:
            cells = row.select("td")
            if len(cells) < 7:
                continue

            course_id = _normalize_text(cells[0].get_text(" ", strip=True)).upper()
            course_type = _normalize_text(cells[3].get_text(" ", strip=True))
            credits_text = _normalize_text(cells[5].get_text(" ", strip=True))
            score_text = _normalize_text(cells[6].get_text(" ", strip=True))
            note_text = _normalize_text(cells[7].get_text(" ", strip=True)) if len(cells) > 7 else ""

            if not course_id:
                continue

            credits_number = _extract_number(credits_text)
            if credits_number is None:
                continue

            credits = int(credits_number)
            passed = _is_course_passed(score_text)

            courses.append(
                ParsedCourse(
                    term=term,
                    course_id=course_id,
                    course_type=course_type,
                    credits=credits,
                    score_text=score_text,
                    note=note_text,
                    passed=passed,
                )
            )

    return courses


def _summarize_credits(
    courses: list[ParsedCourse], html_accumulated_credits: float | None
) -> CreditSummary:
    completed_credits = 0
    emi_earned_credits = 0
    credits_by_type: dict[str, int] = {}
    credits_by_prefix: dict[str, int] = {}

    for course in courses:
        if not course.passed:
            continue

        credits = int(course.credits)
        completed_credits += credits

        course_type = course.course_type or "未分類"
        credits_by_type[course_type] = credits_by_type.get(course_type, 0) + credits

        prefix = course.course_id[:2]
        credits_by_prefix[prefix] = credits_by_prefix.get(prefix, 0) + credits

        if "EMI" in (course.note or ""):
            emi_earned_credits += credits

    return CreditSummary(
        completed_credits_calculated=completed_credits,
        completed_credits_from_html=(
            int(html_accumulated_credits) if html_accumulated_credits is not None else None
        ),
        emi_earned_credits_calculated=emi_earned_credits,
        credits_by_course_type=credits_by_type,
        credits_by_prefix=credits_by_prefix,
    )


def validate_html_filename(filename: str | None) -> None:
    if not filename:
        raise ValueError("請選擇要上傳的檔案")

    lower_name = filename.lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError("僅支援 .html / .htm / .webarchive")


def analyze_html_document(file_storage) -> dict:
    validate_html_filename(file_storage.filename)

    raw_bytes = file_storage.read()
    file_storage.stream.seek(0)

    if not raw_bytes:
        raise ValueError("上傳檔案是空的")

    html_text = _decode_html_bytes(raw_bytes)
    soup = BeautifulSoup(html_text, "html.parser")

    student_id = _extract_student_field(soup, "學號")
    student_name = _extract_student_field(soup, "姓名")
    dept_name = _extract_student_field(soup, "系所")
    html_accumulated_credits = _extract_number(_extract_student_field(soup, "累計學分"))
    html_emi_credits = _extract_number(_extract_student_field(soup, "EMI課程學分"))

    courses = _extract_courses(soup)
    credit_summary = _summarize_credits(courses, html_accumulated_credits)

    preview_chunks = [
        _normalize_text(node.get_text(" ", strip=True))
        for node in soup.select("h1, h4, nav, div.alert")[:10]
    ]
    preview = "\n".join([item for item in preview_chunks if item])

    transcript = ParsedHtmlTranscript(
        filename=file_storage.filename,
        byte_size=len(raw_bytes),
        char_size=len(html_text),
        table_count=len(soup.select("table")),
        row_count=len(soup.select("tr")),
        cell_count=len(soup.select("td, th")),
        student=ParsedStudent(
            student_id=student_id,
            student_name=student_name,
            department=dept_name,
            accumulated_credits_from_html=(
                int(html_accumulated_credits) if html_accumulated_credits is not None else None
            ),
            emi_credits_from_html=(int(html_emi_credits) if html_emi_credits is not None else None),
        ),
        credit_summary=credit_summary,
        courses=courses,
        passed_course_count=len([course for course in courses if course.passed]),
        text_preview=preview,
    )
    return transcript.to_dict()
