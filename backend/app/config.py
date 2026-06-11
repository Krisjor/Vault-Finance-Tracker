"""
Application configuration loaded from environment variables.

Defines three configurations: Development, Testing, Production.
Selected at runtime via the FLASK_ENV environment variable.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """Shared configuration values."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "1"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    )
    JWT_TOKEN_LOCATION = ["headers"]

    # CORS
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # App defaults
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "ALL")
    SUPPORTED_CURRENCIES = ["ALL", "EUR", "USD", "GBP", "CHF"]

    # Pagination
    PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200


# Pool tuning belongs only on network-backed configs (Dev / Production use
# PostgreSQL; Testing uses an in-process SQLite connection that doesn't pool).
_POSTGRES_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/finance_tracker",
    )
    SQLALCHEMY_ENGINE_OPTIONS = _POSTGRES_ENGINE_OPTIONS


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL_TEST",
        "sqlite:///:memory:",
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = _POSTGRES_ENGINE_OPTIONS

    @classmethod
    def init_app(cls, app):
        # In production, hard-fail if secrets weren't set
        assert app.config["SECRET_KEY"] != "dev-secret-change-me", \
            "SECRET_KEY must be set in production"
        assert app.config["JWT_SECRET_KEY"] != "jwt-dev-secret", \
            "JWT_SECRET_KEY must be set in production"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
