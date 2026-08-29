from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import config_by_name
from .extensions import db, migrate, jwt, cors, bcrypt


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure a Flask application instance."""
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # Optional per-config initialization (e.g. production assertions)
    cfg = config_by_name[config_name]
    if hasattr(cfg, "init_app"):
        cfg.init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": [app.config["FRONTEND_URL"]]}},
        supports_credentials=True,
    )

    # Register models so Flask-Migrate can detect them
    from . import models  # noqa: F401

    # Register API blueprints
    from .api.auth import auth_bp
    from .api.accounts import accounts_bp
    from .api.categories import categories_bp
    from .api.transactions import transactions_bp
    from .api.budgets import budgets_bp
    from .api.goals import goals_bp
    from .api.reports import reports_bp
    from .api.imports import imports_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(accounts_bp, url_prefix="/api/accounts")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(budgets_bp, url_prefix="/api/budgets")
    app.register_blueprint(goals_bp, url_prefix="/api/goals")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(imports_bp, url_prefix="/api/imports")

    # Health endpoint
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "version": "1.0.0"})

    # Uniform error handler -> JSON
    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        return jsonify({
            "error": err.name,
            "message": err.description,
            "status": err.code,
        }), err.code

    @app.errorhandler(Exception)
    def handle_generic_exception(err):
        app.logger.exception("Unhandled exception")
        return jsonify({
            "error": "Internal Server Error",
            "message": str(err) if app.debug else "An unexpected error occurred.",
            "status": 500,
        }), 500

    # JWT error responses
    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return jsonify({"error": "Unauthorized", "message": reason, "status": 401}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token expired", "status": 401}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({"error": "Invalid token", "message": reason, "status": 401}), 401

    return app
