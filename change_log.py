import sqlite3
from typing import List, Dict, Optional
from ..database.init_db import DB_PATH

class ChangeLog:
    def __init__(self):
        pass

    def _get_conn(self):
        return sqlite3.connect(DB_PATH)

    def log(self, claim_id: str, timestamp: str, action: str, reason: str, old_value: Optional[str], new_value: Optional[str], confidence_delta: float):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO changelog (claim_id, timestamp, action, reason, old_value, new_value, confidence_delta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (claim_id, timestamp, action, reason, old_value, new_value, confidence_delta))
        conn.commit()
        conn.close()

    def get_all(self) -> List[dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM changelog ORDER BY id ASC")
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        
        results = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return results
