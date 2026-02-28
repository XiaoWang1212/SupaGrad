from datetime import datetime, timezone

from src.clients.supabase_client import SupabaseConfigError
from src.repositories.student_repository import fetch_student_credit_snapshot


def audit_student(student_id: str, payload: dict) -> dict:
    source = "payload"
    completed_credits = payload.get("completed_credits")
    required_credits = payload.get("required_credits")

    if completed_credits is None or required_credits is None:
        try:
            snapshot = fetch_student_credit_snapshot(student_id)
            completed_credits = snapshot["completed_credits"]
            required_credits = snapshot["required_credits"]
            source = "supabase"
        except SupabaseConfigError:
            completed_credits = int(payload.get("completed_credits", 0))
            required_credits = int(payload.get("required_credits", 128))
            source = "payload_fallback"

    completed_credits = int(completed_credits)
    required_credits = int(required_credits)

    missing = max(required_credits - completed_credits, 0)
    passed = missing == 0

    return {
        "student_id": student_id,
        "passed": passed,
        "summary": {
            "completed_credits": completed_credits,
            "required_credits": required_credits,
            "missing_credits": missing,
        },
        "source": source,
        "next_actions": [] if passed else ["補足學分", "檢查學程必修課號是否完成"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
