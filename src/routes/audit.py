from flask import Blueprint, jsonify, request

from src.services.audit_service import audit_student

audit_bp = Blueprint("audit", __name__)


@audit_bp.post("/audit/<student_id>")
def run_audit(student_id: str):
    payload = request.get_json(silent=True) or {}

    result = audit_student(student_id=student_id, payload=payload)
    return jsonify(result), 200
