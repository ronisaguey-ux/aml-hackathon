import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class SQLiteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Idempotency Tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
            """)

            # Main Memories storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    msg_index INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp_ms INTEGER,
                    created_at_iso TEXT NOT NULL,
                    is_procedural INTEGER DEFAULT 0,
                    embedding BLOB,
                    created_at_epoch REAL NOT NULL
                );
            """)

            # Fast lookup indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(user_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_session ON memories(user_id, session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_request ON memories(request_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mem_timestamp ON memories(user_id, timestamp_ms);")

            # FTS5 full-text search table for sub-millisecond BM25 keyword matching
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    id UNINDEXED,
                    user_id UNINDEXED,
                    session_id UNINDEXED,
                    tokenize = 'porter unicode61'
                );
            """)
            conn.commit()

    def is_request_seen(self, request_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM requests WHERE request_id = ? LIMIT 1;", (request_id,))
            return cur.fetchone() is not None

    def record_request(self, request_id: str, user_id: str, session_id: str):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT OR IGNORE INTO requests (request_id, user_id, session_id, created_at) VALUES (?, ?, ?, ?);",
                (request_id, user_id, session_id, time.time())
            )
            conn.commit()

    def insert_memories(self, items: List[Dict[str, Any]]):
        if not items:
            return

        with self._get_connection() as conn:
            cur = conn.cursor()
            now_epoch = time.time()
            
            for item in items:
                cur.execute("""
                    INSERT OR REPLACE INTO memories (
                        id, user_id, session_id, request_id, msg_index, role,
                        content, timestamp_ms, created_at_iso, is_procedural,
                        embedding, created_at_epoch
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    item["id"],
                    item["user_id"],
                    item["session_id"],
                    item["request_id"],
                    item["msg_index"],
                    item["role"],
                    item["content"],
                    item.get("timestamp_ms"),
                    item["created_at_iso"],
                    item.get("is_procedural", 0),
                    item.get("embedding"),
                    now_epoch
                ))

                # Insert into FTS5
                # Delete existing row if replaced
                cur.execute("DELETE FROM memories_fts WHERE id = ?;", (item["id"],))
                cur.execute("""
                    INSERT INTO memories_fts (content, id, user_id, session_id)
                    VALUES (?, ?, ?, ?);
                """, (
                    item["content"],
                    item["id"],
                    item["user_id"],
                    item["session_id"]
                ))
            conn.commit()

    def search_bm25(self, user_id: str, query: str, limit: int = 200) -> List[Tuple[str, float]]:
        """
        Execute BM25 search via SQLite FTS5.
        Returns list of (memory_id, bm25_rank_score).
        FTS5 bm25() returns negative values where more negative is better match.
        We negate it so higher is better.
        """
        # Clean query tokens for FTS5 syntax
        ENGLISH_STOPWORDS = {
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "what", "which", "this", "that",
            "these", "those", "then", "just", "so", "than", "such", "both", "through", "about", "for",
            "is", "of", "while", "during", "to", "from", "in", "out", "on", "off", "again", "further",
            "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
            "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
            "too", "very", "can", "will", "should", "now", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "my", "your", "his", "her", "its", "our", "their",
            "i", "me", "we", "us", "you", "he", "him", "she", "it", "they", "them", "with", "at", "by"
        }
        raw_tokens = re.findall(r'[a-zA-Z0-9_\-\.]+', query)
        filtered = [
            t.replace('"', '""').replace("'", "''") 
            for t in raw_tokens 
            if t.lower() not in ENGLISH_STOPWORDS and len(t) > 1
        ]
        clean_tokens = filtered if filtered else [
            t.replace('"', '""').replace("'", "''") 
            for t in raw_tokens
        ]
        if not clean_tokens:
            return []

        # Form FTS query with OR logic for broad recall
        fts_query = " OR ".join(f'"{t}"' for t in clean_tokens[:30])

        with self._get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT id, bm25(memories_fts) as score
                    FROM memories_fts
                    WHERE memories_fts MATCH ? AND user_id = ?
                    ORDER BY score ASC
                    LIMIT ?;
                """, (fts_query, user_id, limit))
                results = []
                for row in cur.fetchall():
                    # Negate so higher is more relevant
                    results.append((row["id"], -float(row["score"])))
                return results
            except sqlite3.OperationalError:
                # If syntax error in MATCH, fallback to individual token matching
                return []

    def get_memories_by_ids(self, user_id: str, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        query = f"SELECT * FROM memories WHERE user_id = ? AND id IN ({placeholders});"
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [user_id] + ids)
            rows = cur.fetchall()
            return {row["id"]: dict(row) for row in rows}

    def get_user_embeddings(self, user_id: str, limit: int = 500) -> List[Tuple[str, bytes]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, embedding FROM memories
                WHERE user_id = ? AND embedding IS NOT NULL
                ORDER BY timestamp_ms DESC, created_at_epoch DESC
                LIMIT ?;
            """, (user_id, limit))
            return [(row["id"], row["embedding"]) for row in cur.fetchall()]

    def get_all_memories_for_user(self, user_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM memories
                WHERE user_id = ?
                ORDER BY timestamp_ms DESC, created_at_epoch DESC
                LIMIT ?;
            """, (user_id, limit))
            return [dict(row) for row in cur.fetchall()]

    def get_adjacent_session_memories(self, user_id: str, session_id: str, min_idx: int, max_idx: int) -> List[Dict[str, Any]]:
        """Retrieve contiguous sequence within a session for procedural execution context."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM memories
                WHERE user_id = ? AND session_id = ? AND msg_index >= ? AND msg_index <= ?
                ORDER BY msg_index ASC;
            """, (user_id, session_id, min_idx, max_idx))
            return [dict(row) for row in cur.fetchall()]

    def get_session_procedure_block(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all procedural and operational steps for a session in strict chronological execution order."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM memories
                WHERE user_id = ? AND session_id = ?
                ORDER BY msg_index ASC, timestamp_ms ASC, created_at_epoch ASC;
            """, (user_id, session_id))
            return [dict(row) for row in cur.fetchall()]

    def get_latest_user_timestamp(self, user_id: str) -> Optional[int]:
        """Fetch highest explicit timestamp recorded for this user."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT MAX(timestamp_ms) FROM memories
                WHERE user_id = ? AND timestamp_ms IS NOT NULL;
            """, (user_id,))
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None

    def count_memories(self, user_id: Optional[str] = None) -> int:
        with self._get_connection() as conn:
            cur = conn.cursor()
            if user_id:
                cur.execute("SELECT COUNT(*) FROM memories WHERE user_id = ?;", (user_id,))
            else:
                cur.execute("SELECT COUNT(*) FROM memories;")
            return cur.fetchone()[0]

    def purge_older_than(self, days: int = 30) -> int:
        """Data hygiene policy: purge memories older than specified days."""
        cutoff_epoch = time.time() - (days * 86400)
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM memories WHERE created_at_epoch < ?;", (cutoff_epoch,))
            deleted = cur.rowcount
            # Rebuild FTS
            cur.execute("DELETE FROM memories_fts WHERE id NOT IN (SELECT id FROM memories);")
            conn.commit()
            return deleted
