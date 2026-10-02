import os
import secrets


def database_url():
    url = os.getenv("DATABASE_URL", "sqlite:///skillswap.db")
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("FLASK_ENV") == "production"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    MATCHING_USE_EMBEDDINGS = os.getenv("MATCHING_USE_EMBEDDINGS", "true").lower() == "true"
