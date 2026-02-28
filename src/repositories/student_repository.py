from src.clients.supabase_client import get_supabase_client


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
