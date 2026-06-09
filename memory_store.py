import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from ..database.init_db import DB_PATH

class MemoryStore:
    def __init__(self, capacity: int = 20):
        self.capacity = capacity

    def _get_conn(self):
        return sqlite3.connect(DB_PATH)

    def query(self, subject: str, predicate: str) -> Optional[dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE subject=? AND predicate=?", (subject.lower(), predicate.lower()))
        row = cursor.fetchone()
        if not row:
            return None
            
        columns = [col[0] for col in cursor.description]
        mem = dict(zip(columns, row))
        mem['sources'] = json.loads(mem['sources'])
        
        # Load provenance
        cursor.execute("SELECT * FROM provenance WHERE memory_id=? ORDER BY id ASC", (mem['id'],))
        prov_rows = cursor.fetchall()
        prov_cols = [col[0] for col in cursor.description]
        mem['provenance_history'] = [dict(zip(prov_cols, pr)) for pr in prov_rows]
        
        conn.close()
        return mem

    def get_all_active(self) -> List[dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE status='active'")
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        
        results = []
        for row in rows:
            mem = dict(zip(columns, row))
            mem['sources'] = json.loads(mem['sources'])
            results.append(mem)
        conn.close()
        return results

    def store(self, subject: str, predicate: str, obj: str, confidence: float, status: str, sources: List[str], timestamp: str, claim_id: str, reason: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Check if exists to avoid UNIQUE constraint failure if we are 'storing' over an existing (should use revise instead, but just in case)
        cursor.execute("SELECT id FROM memories WHERE subject=? AND predicate=?", (subject.lower(), predicate.lower()))
        existing = cursor.fetchone()
        
        if existing:
            # Update instead
            mem_id = existing[0]
            cursor.execute('''
                UPDATE memories SET object=?, confidence=?, status=?, sources=?, last_updated=?
                WHERE id=?
            ''', (obj, confidence, status, json.dumps(sources), timestamp, mem_id))
        else:
            cursor.execute('''
                INSERT INTO memories (subject, predicate, object, confidence, status, sources, first_seen, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (subject.lower(), predicate.lower(), obj, confidence, status, json.dumps(sources), timestamp, timestamp))
            mem_id = cursor.lastrowid
            
        self._add_provenance(cursor, mem_id, timestamp, "ACCEPTED", claim_id, 0.0, confidence, reason)
        conn.commit()
        conn.close()
        self.evict_if_needed()

    def revise(self, subject: str, predicate: str, new_obj: str, new_conf: float, new_source: str, claim_id: str, timestamp: str, reason: str):
        mem = self.query(subject, predicate)
        if not mem:
            return
            
        sources = mem['sources']
        if new_source not in sources:
            sources.append(new_source)
            
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE memories SET object=?, confidence=?, status=?, sources=?, last_updated=?, revision_count=revision_count+1
            WHERE id=?
        ''', (new_obj, new_conf, "active", json.dumps(sources), timestamp, mem['id']))
        
        self._add_provenance(cursor, mem['id'], timestamp, "REVISED", claim_id, mem['confidence'], new_conf, reason)
        conn.commit()
        conn.close()

    def downgrade(self, subject: str, predicate: str, new_conf: float, claim_id: str, timestamp: str, reason: str):
        mem = self.query(subject, predicate)
        if not mem: return
        
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE memories SET confidence=?, status=?, last_updated=?
            WHERE id=?
        ''', (new_conf, "low_confidence", timestamp, mem['id']))
        self._add_provenance(cursor, mem['id'], timestamp, "DOWNGRADED", claim_id, mem['confidence'], new_conf, reason)
        conn.commit()
        conn.close()

    def forget(self, subject: str, predicate: str, claim_id: str, timestamp: str, reason: str):
        mem = self.query(subject, predicate)
        if not mem: return
        
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE memories SET confidence=0.0, status=?, last_updated=?
            WHERE id=?
        ''', ("forgotten", timestamp, mem['id']))
        self._add_provenance(cursor, mem['id'], timestamp, "FORGOTTEN", claim_id, mem['confidence'], 0.0, reason)
        conn.commit()
        conn.close()

    def merge(self, subject: str, predicate: str, new_source: str, new_conf: float, claim_id: str, timestamp: str, reason: str):
        mem = self.query(subject, predicate)
        if not mem: return
        
        sources = mem['sources']
        if new_source not in sources:
            sources.append(new_source)
            
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE memories SET confidence=?, sources=?, last_updated=?, corroboration_count=corroboration_count+1
            WHERE id=?
        ''', (new_conf, json.dumps(sources), timestamp, mem['id']))
        self._add_provenance(cursor, mem['id'], timestamp, "MERGED", claim_id, mem['confidence'], new_conf, reason)
        conn.commit()
        conn.close()

    def _add_provenance(self, cursor, mem_id, timestamp, action, claim_id, conf_before, conf_after, explanation):
        cursor.execute('''
            INSERT INTO provenance (memory_id, timestamp, action, triggering_claim_id, confidence_before, confidence_after, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (mem_id, timestamp, action, claim_id, conf_before, conf_after, explanation))

    def evict_if_needed(self):
        active = self.get_all_active()
        if len(active) > self.capacity:
            active.sort(key=lambda x: x['confidence'])
            to_evict = active[0]
            from datetime import datetime
            ts = datetime.utcnow().isoformat() + "Z"
            self.forget(to_evict['subject'], to_evict['predicate'], "SYSTEM_EVICTION", ts, "Memory overflow: Evicted lowest confidence entry.")
