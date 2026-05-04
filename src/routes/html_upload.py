from flask import Blueprint, jsonify, render_template, request

from src.clients.supabase_client import SupabaseConfigError
from src.repositories.student_repository import persist_student_and_enrollments
from src.services.html_upload_service import analyze_html_document
from src.services.llm_service import generate_llm_analysis

html_upload_bp = Blueprint("html_upload", __name__)


@html_upload_bp.get("/")
def html_upload_page():
    return render_template("html_upload.html")


@html_upload_bp.post("/api/v1/html/analyze")
def analyze_html_file():
    html_file = request.files.get("html_file")
    if not html_file:
        return jsonify({"error": "html_file is required"}), 400

    try:
        result = analyze_html_document(html_file)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    student_id_override = (request.form.get("student_id") or "").strip()
    required_credits_raw = (request.form.get("required_credits") or "128").strip()

    try:
        required_credits = int(required_credits_raw)
    except ValueError:
        return jsonify({"error": "required_credits must be integer"}), 400

    if required_credits <= 0:
        return jsonify({"error": "required_credits must be > 0"}), 400

    student_id_from_html = (result.get("student") or {}).get("student_id")
    student_id = student_id_override or student_id_from_html
    if not student_id:
        return jsonify({"error": "無法從 HTML 解析學號，請手動輸入 student_id"}), 400

    def _build_analysis(result_data: dict, required_credits_value: int) -> dict:
        completed = result_data.get("credit_summary", {}).get(
            "completed_credits_calculated", 0
        )
        missing = max(required_credits_value - completed, 0)
        suggestions = []

        if missing > 0:
            suggestions.append(
                f"目前還缺 {missing} 學分，建議優先補修系所必修、主修核心課程，或選修能快速累積學分的課程。"
            )
        else:
            suggestions.append(
                "目前已達填寫的畢業學分，請再確認是否還有必修、系規定或通識未完成。"
            )

        department = (result_data.get("student") or {}).get("department")
        if department:
            suggestions.append(
                f"此成績單屬於 {department}，建議比對該系的課程表與必修規定。"
            )

        emi_credits = result_data.get("credit_summary", {}).get(
            "emi_earned_credits_calculated"
        )
        if emi_credits is not None:
            if emi_credits < 12:
                suggestions.append(
                    f"EMI 學分目前為 {emi_credits}，若系所或畢業條件需要 EMI，建議補修至少一門 EMI 課程。"
                )
            else:
                suggestions.append(
                    f"EMI 學分目前為 {emi_credits}，可以再確認是否符合你系所的 EMI 最低要求。"
                )

        credits_by_type = result_data.get("credit_summary", {}).get(
            "credits_by_course_type", {}
        )
        if credits_by_type:
            top_type = max(credits_by_type.items(), key=lambda item: item[1])
            suggestions.append(
                f"已修最多的課程類別為「{top_type[0]}」，可檢查該類別是否還有補修空間。"
            )

        return {
            "missing_credits": missing,
            "suggestions": suggestions,
        }

    result["analysis"] = _build_analysis(result, required_credits)

    result["analysis"] = generate_llm_analysis(result, required_credits)

    try:
        db_result = persist_student_and_enrollments(
            student_id=student_id,
            required_credits=required_credits,
            courses=result.get("courses", []),
        )
        result["database"] = {
            "saved": True,
            "target": "supabase",
            **db_result,
        }
    except SupabaseConfigError as err:
        result["database"] = {
            "saved": False,
            "target": "supabase",
            "error": str(err),
        }
    except Exception as err:
        result["database"] = {
            "saved": False,
            "target": "supabase",
            "error": str(err),
        }

    return jsonify(result), 200
