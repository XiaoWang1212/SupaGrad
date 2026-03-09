from flask import Blueprint, jsonify, render_template, request

from src.services.manual_audit_service import audit_manual_upload

manual_bp = Blueprint("manual", __name__)


@manual_bp.get("/")
def index_page():
    return render_template("index.html")


@manual_bp.post("/api/v1/manual/audit")
def manual_audit():
    transcript_file = request.files.get("transcript_file")
    transfer_file = request.files.get("transfer_file")

    if not transcript_file:
        return jsonify({"error": "transcript_file is required"}), 400

    student_id = (request.form.get("student_id") or "self").strip() or "self"
    required_courses = request.form.get("required_courses")

    try:
        required_credits = int(request.form.get("required_credits", 128))
    except ValueError:
        return jsonify({"error": "required_credits must be integer"}), 400

    try:
        result = audit_manual_upload(
            student_id=student_id,
            required_credits=required_credits,
            required_courses_raw=required_courses,
            transcript_file=transcript_file,
            transfer_file=transfer_file,
        )
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    return jsonify(result), 200
