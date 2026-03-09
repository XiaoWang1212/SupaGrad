from src.clients.supabase_client import get_supabase_client
from src.models.transcript import ParsedCourse


DEFAULT_REQUIRED_CREDITS = 128


def fetch_student_credit_snapshot(student_id: str) -> dict:
    client = get_supabase_client()

    student_response = (
        client.table("students")
        .select("id,required_credits")
        .eq("id", student_id)
        .limit(1)
        .execute()
    )

    student = student_response.data[0] if student_response.data else {}
    required_credits = int(student.get("required_credits") or DEFAULT_REQUIRED_CREDITS)

    enrollment_response = (
        client.table("enrollments")
        .select("course_id,passed,credits")
        .eq("student_id", student_id)
        .eq("passed", True)
        .execute()
    )

    completed_credits = 0
    for row in enrollment_response.data or []:
        completed_credits += int(row.get("credits") or 0)

    return {
        "student_id": student_id,
        "required_credits": required_credits,
        "completed_credits": completed_credits,
    }


def persist_student_and_enrollments(
    student_id: str, required_credits: int, courses: list[dict] | list[ParsedCourse]
) -> dict:
    client = get_supabase_client()

    client.table("students").upsert(
        {"id": student_id, "required_credits": required_credits}, on_conflict="id"
    ).execute()

    client.table("enrollments").delete().eq("student_id", student_id).execute()

    rows = []
    for course in courses:
        if isinstance(course, ParsedCourse):
            course_id = course.course_id
            credits = int(course.credits)
            passed = bool(course.passed)
        else:
            course_id = course["course_id"]
            credits = int(course["credits"])
            passed = bool(course["passed"])

        rows.append(
            {
                "student_id": student_id,
                "course_id": course_id,
                "credits": credits,
                "passed": passed,
            }
        )

    if rows:
        client.table("enrollments").insert(rows).execute()

    return {
        "student_id": student_id,
        "required_credits": required_credits,
        "saved_course_count": len(rows),
    }
