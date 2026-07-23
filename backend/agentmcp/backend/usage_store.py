"""SQLite-backed x402 UsagePass store."""
import time
import uuid
import database


def create_pass(user: str, voice_id: str, uses: int = 2, expires_in_hours: int = 24, tx_digest: str = "") -> dict:
    import sqlite3
    from pathlib import Path
    expires_at = time.time() + expires_in_hours * 3600
    pass_id = str(uuid.uuid4())
    with database._conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS usage_passes (
                id TEXT PRIMARY KEY,
                user TEXT NOT NULL,
                voice_id TEXT NOT NULL,
                uses_remaining INTEGER NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL,
                tx_digest TEXT DEFAULT ''
            )"""
        )
        conn.execute(
            "INSERT INTO usage_passes (id, user, voice_id, uses_remaining, expires_at, created_at, tx_digest) VALUES (?,?,?,?,?,?,?)",
            (pass_id, user.lower(), voice_id.lower(), uses, expires_at, time.time(), tx_digest)
        )
    return {"id": pass_id, "user": user, "voice_id": voice_id, "uses_remaining": uses, "expires_at": expires_at}


def has_access(user: str, voice_id: str) -> tuple:
    try:
        with database._conn() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS usage_passes (
                id TEXT PRIMARY KEY, user TEXT NOT NULL, voice_id TEXT NOT NULL,
                uses_remaining INTEGER NOT NULL, expires_at REAL NOT NULL,
                created_at REAL NOT NULL, tx_digest TEXT DEFAULT '')""")
            row = conn.execute(
                "SELECT * FROM usage_passes WHERE user=? AND voice_id=? AND uses_remaining>0 AND expires_at>?",
                (user.lower(), voice_id.lower(), time.time())
            ).fetchone()
            if row:
                return True, dict(row)
            return False, None
    except Exception:
        return False, None


def consume_pass(pass_id: str) -> dict | None:
    try:
        with database._conn() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS usage_passes (
                id TEXT PRIMARY KEY, user TEXT NOT NULL, voice_id TEXT NOT NULL,
                uses_remaining INTEGER NOT NULL, expires_at REAL NOT NULL,
                created_at REAL NOT NULL, tx_digest TEXT DEFAULT '')""")
            row = conn.execute("SELECT * FROM usage_passes WHERE id=?", (pass_id,)).fetchone()
            if not row or row["uses_remaining"] <= 0:
                return None
            conn.execute("UPDATE usage_passes SET uses_remaining=uses_remaining-1 WHERE id=?", (pass_id,))
            updated = conn.execute("SELECT * FROM usage_passes WHERE id=?", (pass_id,)).fetchone()
            return dict(updated)
    except Exception:
        return None


def list_passes_for_user(user: str) -> list:
    try:
        with database._conn() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS usage_passes (
                id TEXT PRIMARY KEY, user TEXT NOT NULL, voice_id TEXT NOT NULL,
                uses_remaining INTEGER NOT NULL, expires_at REAL NOT NULL,
                created_at REAL NOT NULL, tx_digest TEXT DEFAULT '')""")
            rows = conn.execute("SELECT * FROM usage_passes WHERE user=?", (user.lower(),)).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []
