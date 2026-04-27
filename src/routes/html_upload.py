from flask import Blueprint, jsonify, render_template, request

from src.clients.supabase_client import SupabaseConfigError
from src.repositories.student_repository import persist_student_and_enrollments
from src.services.html_upload_service import analyze_html_document

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
