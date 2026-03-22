"""Authentifizierung: Passwort-Hashing, Session-Cookies, Admin-Check."""

import os
import secrets
import bcrypt
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

SESSION_COOKIE = "essenplaner_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 Tage

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def hash_password(password: str) -> str:
    """Hasht ein Passwort mit bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Prüft ein Passwort gegen einen Hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_session_token(user_id: int) -> str:
    """Erstellt einen signierten Session-Token."""
    return _serializer.dumps({"user_id": user_id})


def verify_session_token(token: str) -> dict | None:
    """Prüft einen Session-Token und gibt die Daten zurück."""
    try:
        return _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def generate_password(length: int = 12) -> str:
    """Generiert ein zufälliges Einmal-Passwort."""
    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def is_admin_email(email: str) -> bool:
    """Prüft ob die E-Mail die Admin-E-Mail ist."""
    return email.lower() == ADMIN_EMAIL.lower() and ADMIN_EMAIL != ""


def verify_admin(username: str, password: str) -> bool:
    """Prüft Admin-Zugangsdaten aus der .env."""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD and ADMIN_PASSWORD != ""
