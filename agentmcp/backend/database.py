"""SQLite storage layer for SwaraOS — replaces Walrus."""
import sqlite3
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent / "storage" / "voicevault.db"


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS voice_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voice_id TEXT UNIQUE NOT NULL,
                owner_address TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                audio_hash TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                preview_path TEXT NOT NULL,
                price_per_use INTEGER DEFAULT 0,
                on_chain_id INTEGER DEFAULT NULL,
                on_chain_tx TEXT DEFAULT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_address TEXT NOT NULL,
                voice_id TEXT NOT NULL,
                tx_hash TEXT NOT NULL,
                expires_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payment_proofs (
                tx_hash TEXT PRIMARY KEY,
                buyer_address TEXT NOT NULL,
                verified INTEGER NOT NULL DEFAULT 1
            );
        """)

        # Safe migrations — ignored if column already exists
        for migration in [
            "ALTER TABLE voice_assets ADD COLUMN on_chain_id INTEGER DEFAULT NULL",
            "ALTER TABLE voice_assets ADD COLUMN on_chain_tx TEXT DEFAULT NULL",
        ]:
            try:
                conn.execute(migration)
            except Exception:
                pass


# ---- voice_assets ----

def insert_voice(voice_id: str, owner_address: str, name: str, description: str,
                 audio_hash: str, audio_path: str, preview_path: str, price_per_use: int = 0) -> dict:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO voice_assets
               (voice_id, owner_address, name, description, audio_hash, audio_path, preview_path, price_per_use, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (voice_id, owner_address.lower(), name, description, audio_hash, audio_path, preview_path, price_per_use, time.time())
        )
    return get_voice(voice_id)


def get_voice(voice_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM voice_assets WHERE voice_id = ?", (voice_id,)).fetchone()
        return dict(row) if row else None


def list_voices() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM voice_assets ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def set_on_chain_id(voice_id: str, on_chain_id: int, tx_hash: str) -> dict | None:
    with _conn() as conn:
        conn.execute(
            "UPDATE voice_assets SET on_chain_id = ?, on_chain_tx = ? WHERE voice_id = ?",
            (on_chain_id, tx_hash, voice_id)
        )
    return get_voice(voice_id)


def get_voice_by_on_chain_id(on_chain_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM voice_assets WHERE on_chain_id = ?", (on_chain_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_voice(voice_id: str) -> bool:
    with _conn() as conn:
        result = conn.execute("DELETE FROM voice_assets WHERE voice_id = ?", (voice_id,))
        return result.rowcount > 0


# ---- licenses ----

def insert_license(buyer_address: str, voice_id: str, tx_hash: str, expires_in_hours: int = 8760) -> dict:
    expires_at = time.time() + expires_in_hours * 3600
    with _conn() as conn:
        conn.execute(
            "INSERT INTO licenses (buyer_address, voice_id, tx_hash, expires_at) VALUES (?,?,?,?)",
            (buyer_address.lower(), voice_id, tx_hash, expires_at)
        )
    return {"buyer_address": buyer_address, "voice_id": voice_id, "tx_hash": tx_hash, "expires_at": expires_at}


def get_licenses_for_buyer(buyer_address: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            """SELECT va.*, l.tx_hash as license_tx, l.expires_at
               FROM licenses l
               JOIN voice_assets va ON va.voice_id = l.voice_id
               WHERE l.buyer_address = ? AND l.expires_at > ?
               ORDER BY l.expires_at DESC""",
            (buyer_address.lower(), time.time())
        ).fetchall()
        return [dict(r) for r in rows]


def has_license(buyer_address: str, voice_id: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM licenses WHERE buyer_address = ? AND voice_id = ? AND expires_at > ?",
            (buyer_address.lower(), voice_id, time.time())
        ).fetchone()
        return row is not None


# ---- payment_proofs (replay protection) ----

def has_payment_proof(tx_hash: str) -> bool:
    with _conn() as conn:
        row = conn.execute("SELECT 1 FROM payment_proofs WHERE tx_hash = ?", (tx_hash,)).fetchone()
        return row is not None


def record_payment_proof(tx_hash: str, buyer_address: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO payment_proofs (tx_hash, buyer_address, verified) VALUES (?,?,1)",
            (tx_hash, buyer_address.lower())
        )
