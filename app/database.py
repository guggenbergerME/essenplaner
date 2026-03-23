"""SQLite-Datenbank für Nutzer und Favoriten."""

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "essenplaner.db"


def get_db():
    """Gibt eine SQLite-Verbindung zurück."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Erstellt die Datenbanktabellen falls nicht vorhanden."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            confirmed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS favoriten (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            plan_data TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    # Migration: confirmed-Spalte für bestehende Datenbanken
    try:
        conn.execute("ALTER TABLE users ADD COLUMN confirmed INTEGER DEFAULT 0")
        conn.commit()
        print("[DB] Migration: Spalte 'confirmed' hinzugefügt.")
    except Exception:
        pass  # Spalte existiert bereits
    conn.commit()
    conn.close()


def ensure_admin_user(email: str, password_hash: str):
    """Erstellt den Admin-User aus .env, falls noch nicht vorhanden."""
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email.lower(),)).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (email, password_hash, is_active, confirmed) VALUES (?, ?, 1, 1)",
            (email.lower(), password_hash),
        )
        conn.commit()
        print(f"[DB] Admin-User '{email}' automatisch erstellt.")
    conn.close()


# ── User-Operationen ────────────────────────────────

def create_user(email, password_hash):
    """Erstellt einen neuen Nutzer."""
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_email(email):
    """Gibt einen Nutzer anhand der E-Mail zurück."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    """Gibt einen Nutzer anhand der ID zurück."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def confirm_user(user_id: int):
    """Markiert einen Nutzer als bestätigt (hat sich mindestens einmal angemeldet)."""
    conn = get_db()
    conn.execute("UPDATE users SET confirmed = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_users():
    """Gibt alle Nutzer zurück."""
    conn = get_db()
    users = conn.execute(
        "SELECT id, email, is_active, confirmed, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(u) for u in users]


def delete_user(user_id):
    """Löscht einen Nutzer."""
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_user_password(user_id, password_hash):
    """Aktualisiert das Passwort eines Nutzers."""
    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()


# ── Favoriten-Operationen ────────────────────────────

def save_favorit(user_id, name, plan_data):
    """Speichert einen Wochenplan als Favorit."""
    conn = get_db()
    conn.execute(
        "INSERT INTO favoriten (user_id, name, plan_data) VALUES (?, ?, ?)",
        (user_id, name, json.dumps(plan_data, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def get_favoriten(user_id):
    """Gibt alle Favoriten eines Nutzers zurück."""
    conn = get_db()
    favs = conn.execute(
        "SELECT id, name, created_at FROM favoriten WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(f) for f in favs]


def get_favorit(favorit_id, user_id):
    """Gibt einen einzelnen Favoriten zurück."""
    conn = get_db()
    fav = conn.execute(
        "SELECT * FROM favoriten WHERE id = ? AND user_id = ?",
        (favorit_id, user_id),
    ).fetchone()
    conn.close()
    if fav:
        result = dict(fav)
        result["plan_data"] = json.loads(result["plan_data"])
        return result
    return None


def delete_favorit(favorit_id, user_id):
    """Löscht einen Favoriten."""
    conn = get_db()
    conn.execute("DELETE FROM favoriten WHERE id = ? AND user_id = ?", (favorit_id, user_id))
    conn.commit()
    conn.close()
