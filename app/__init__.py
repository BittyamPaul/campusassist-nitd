"""
CampusAssist Flask Application Factory.
Initializes the Flask app, registers blueprints, database hooks, and error handlers.
"""

from flask import Flask
from config import Config
from app.models.db import close_db
from app.routes import main_bp, api_bp, admin_bp


def create_app(config_class=Config):
    """Factory to create and configure the Flask application instance."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register database teardown hook
    app.teardown_appcontext(close_db)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Ensure database tables and column migrations are applied
    with app.app_context():
        from app.models.db import init_db
        try:
            init_db()
        except Exception as e:
            app.logger.warning(f"Database init warning: {e}")

    # Inject CSRF token into template context
    from app.services.csrf import get_csrf_token
    @app.context_processor
    def inject_csrf():
        return dict(csrf_token=get_csrf_token)

    # Security Response Headers
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'self';"
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Centralized Sanitized Error Handlers (Zero Stack Trace Disclosure)
    from flask import request, jsonify

    def is_api_or_json_request():
        return (
            request.path.startswith("/api/")
            or request.is_json
            or (request.accept_mimetypes.best == "application/json" and request.accept_mimetypes.best != "text/html")
        )

    @app.errorhandler(400)
    def handle_bad_request(e):
        if is_api_or_json_request():
            return jsonify({"error": "Bad Request", "message": getattr(e, "description", "Invalid request parameters.")}), 400
        return "<h1>400 Bad Request</h1><p>Invalid request parameters.</p>", 400

    @app.errorhandler(401)
    def handle_unauthorized(e):
        if is_api_or_json_request():
            return jsonify({"error": "Unauthorized", "message": getattr(e, "description", "Authentication required.")}), 401
        return "<h1>401 Unauthorized</h1><p>Authentication required.</p>", 401

    @app.errorhandler(403)
    def handle_forbidden(e):
        if is_api_or_json_request():
            return jsonify({"error": "Forbidden", "message": getattr(e, "description", "Access denied.")}), 403
        return "<h1>403 Forbidden</h1><p>Access denied.</p>", 403

    @app.errorhandler(404)
    def handle_not_found(e):
        if is_api_or_json_request():
            return jsonify({"error": "Not Found", "message": "The requested resource was not found on this server."}), 404
        return "<h1>404 Not Found</h1><p>The requested page was not found.</p>", 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        if is_api_or_json_request():
            return jsonify({"error": "Method Not Allowed", "message": "The HTTP method is not allowed for this endpoint."}), 405
        return "<h1>405 Method Not Allowed</h1><p>Method not allowed.</p>", 405

    @app.errorhandler(413)
    def handle_payload_too_large(e):
        if is_api_or_json_request():
            return jsonify({"error": "Payload Too Large", "message": "Request entity exceeds maximum permitted size."}), 413
        return "<h1>413 Payload Too Large</h1><p>Request payload is too large.</p>", 413

    @app.errorhandler(429)
    def handle_rate_limit(e):
        if is_api_or_json_request():
            return jsonify({"error": "Too Many Requests", "message": getattr(e, "description", "Rate limit exceeded.")}), 429
        return "<h1>429 Too Many Requests</h1><p>Rate limit exceeded. Please try again later.</p>", 429

    @app.errorhandler(500)
    def handle_internal_error(e):
        app.logger.error(f"Internal server error: {e}")
        if is_api_or_json_request():
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred while processing your request."
            }), 500
        return "<h1>500 Internal Server Error</h1><p>An unexpected error occurred. Please try again later.</p>", 500

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        # Don't intercept Werkzeug HTTPExceptions (they have their own handlers)
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return e
        app.logger.error(f"Uncaught exception: {e}", exc_info=True)
        if is_api_or_json_request():
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred. Please try again later."
            }), 500
        return "<h1>500 Internal Server Error</h1><p>An unexpected error occurred. Please try again later.</p>", 500

    # Health check route
    @app.route("/api/health")
    def health_check():
        return {
            "status": "healthy",
            "app": "CampusAssist",
            "institution": "National Institute of Technology Durgapur",
            "department": "Computer Science & Engineering",
            "owner": "Bittyam Paul",
            "version": "1.0.0"
        }

    return app
