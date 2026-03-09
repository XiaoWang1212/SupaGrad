from flask import Flask, jsonify

from src.config import get_config
from src.routes.audit import audit_bp
from src.routes.health import health_bp
from src.routes.html_upload import html_upload_bp
from src.routes.manual import manual_bp

def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    app.register_blueprint(health_bp)
    app.register_blueprint(manual_bp)
    app.register_blueprint(html_upload_bp)
    app.register_blueprint(audit_bp, url_prefix="/api/v1")

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not Found"}), 404

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"error": "Internal Server Error"}), 500

    return app
