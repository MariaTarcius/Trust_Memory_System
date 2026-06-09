import json
import os
from typing import Dict, Tuple, List, Optional
from datetime import datetime
from .models import MemoryEntry, ChangeLogEntry, MemoryStatus, ActionType

class MemoryStore:
    def __init__(self, capacity: int = 20):
        self.capacity = capacity
        # Key: (subject, predicate) -> MemoryEntry
        self.memories: Dict[Tuple[str, str], MemoryEntry] = {}
        self.change_log: List[ChangeLogEntry] = []

    def _get_key(self, subject: str, predicate: str) -> Tuple[str, str]:
        return (subject.strip().lower(), predicate.strip().lower())

    def query(self, subject: str, predicate: str) -> Optional[MemoryEntry]:
        key = self._get_key(subject, predicate)
        return self.memories.get(key)

    def get_all_active(self) -> List[MemoryEntry]:
        """Return memories still retained in the store (not forgotten or rejected)."""
        retained = {
            MemoryStatus.ACTIVE,
            MemoryStatus.LOW_CONFIDENCE,
            MemoryStatus.OUTDATED,
        }
        return [m for m in self.memories.values() if m.status in retained]

    def store(self, entry: MemoryEntry, claim_id: str, reason: str):
        key = self._get_key(entry.subject, entry.predicate)
        existing = self.memories.get(key)
        if existing and existing.status != MemoryStatus.FORGOTTEN:
            entry.provenance_history = existing.provenance_history + entry.provenance_history
            entry.corroboration_count = existing.corroboration_count
            entry.revision_count = existing.revision_count
        self.memories[key] = entry

        self.evict_if_needed()
        
        self._log_change(
            claim_id=claim_id,
            action=ActionType.ACCEPTED,
            reason=reason,
            old_value=None,
            new_value=entry.object,
            confidence_delta=entry.confidence
        )

    def revise(self, subject: str, predicate: str, new_object: str, new_confidence: float, new_source: str, claim_id: str, reason: str):
        key = self._get_key(subject, predicate)
        if key in self.memories:
            entry = self.memories[key]
            old_val = entry.object
            old_conf = entry.confidence
            
            entry.object = new_object
            entry.confidence = new_confidence
            entry.revision_count += 1
            entry.last_updated = datetime.utcnow().isoformat() + "Z"
            if new_source not in entry.sources:
                entry.sources.append(new_source)
            entry.status = MemoryStatus.ACTIVE
            
            entry.provenance_history.append({
                "timestamp": entry.last_updated,
                "action": "REVISED",
                "triggering_claim_id": claim_id,
                "confidence_before": old_conf,
                "confidence_after": new_confidence,
                "explanation": reason
            })
            
            self._log_change(claim_id, ActionType.REVISED, reason, old_val, new_object, new_confidence - old_conf)

    def downgrade(self, subject: str, predicate: str, new_confidence: float, claim_id: str, reason: str):
        key = self._get_key(subject, predicate)
        if key in self.memories:
            entry = self.memories[key]
            old_conf = entry.confidence
            entry.confidence = new_confidence
            entry.status = MemoryStatus.LOW_CONFIDENCE
            entry.last_updated = datetime.utcnow().isoformat() + "Z"
            
            entry.provenance_history.append({
                "timestamp": entry.last_updated,
                "action": "DOWNGRADED",
                "triggering_claim_id": claim_id,
                "confidence_before": old_conf,
                "confidence_after": new_confidence,
                "explanation": reason
            })
            
            self._log_change(claim_id, ActionType.DOWNGRADED, reason, entry.object, entry.object, new_confidence - old_conf)

    def reject(self, claim_id: str, reason: str):
        self._log_change(claim_id, ActionType.REJECTED, reason, None, None, 0.0)

    def forget(self, subject: str, predicate: str, claim_id: str, reason: str):
        key = self._get_key(subject, predicate)
        if key in self.memories:
            entry = self.memories[key]
            old_conf = entry.confidence
            entry.status = MemoryStatus.FORGOTTEN
            entry.confidence = 0.0
            entry.last_updated = datetime.utcnow().isoformat() + "Z"
            
            entry.provenance_history.append({
                "timestamp": entry.last_updated,
                "action": "FORGOTTEN",
                "triggering_claim_id": claim_id,
                "confidence_before": old_conf,
                "confidence_after": 0.0,
                "explanation": reason
            })
            
            self._log_change(claim_id, ActionType.FORGOTTEN, reason, entry.object, None, -old_conf)

    def merge(self, subject: str, predicate: str, new_source: str, new_confidence: float, claim_id: str, reason: str):
        key = self._get_key(subject, predicate)
        if key in self.memories:
            entry = self.memories[key]
            old_conf = entry.confidence
            entry.confidence = new_confidence
            entry.corroboration_count += 1
            if new_source not in entry.sources:
                entry.sources.append(new_source)
            entry.last_updated = datetime.utcnow().isoformat() + "Z"
            
            entry.provenance_history.append({
                "timestamp": entry.last_updated,
                "action": "MERGED",
                "triggering_claim_id": claim_id,
                "confidence_before": old_conf,
                "confidence_after": new_confidence,
                "explanation": reason
            })
            
            self._log_change(claim_id, ActionType.MERGED, reason, entry.object, entry.object, new_confidence - old_conf)

    def evict_if_needed(self):
        active_entries = self.get_all_active()
        if len(active_entries) > self.capacity:
            # Sort by confidence to evict lowest
            active_entries.sort(key=lambda x: x.confidence)
            to_evict = active_entries[0]
            self.forget(to_evict.subject, to_evict.predicate, "SYSTEM_EVICTION", "Memory overflow: Evicted lowest confidence entry to make room.")

    def explain(self, subject: str, predicate: str) -> str:
        entry = self.query(subject, predicate)
        if not entry:
            return "No memory found."
        
        explanation = f"Memory: {entry.subject} {entry.predicate} {entry.object}\n"
        explanation += f"Current Confidence: {entry.confidence:.2f} ({entry.status})\n"
        explanation += f"Sources: {', '.join(entry.sources)}\n"
        explanation += "Provenance History:\n"
        for hist in entry.provenance_history:
            explanation += f"  - [{hist['timestamp']}] {hist['action']} (Claim {hist['triggering_claim_id']}): {hist['explanation']} (Conf: {hist['confidence_before']:.2f} -> {hist['confidence_after']:.2f})\n"
        return explanation

    def _log_change(self, claim_id: str, action: str, reason: str, old_value: Optional[str], new_value: Optional[str], confidence_delta: float):
        entry = ChangeLogEntry(
            claim_id=claim_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            action=action,
            reason=reason,
            old_value=old_value,
            new_value=new_value,
            confidence_delta=confidence_delta
        )
        self.change_log.append(entry)

    def save(self, filepath: str, log_filepath: str):
        # Convert to dict
        mem_data = []
        for entry in self.memories.values():
            mem_data.append(entry.__dict__)
            
        with open(filepath, 'w') as f:
            json.dump(mem_data, f, indent=2)
            
        log_data = [l.__dict__ for l in self.change_log]
        with open(log_filepath, 'w') as f:
            json.dump(log_data, f, indent=2)

    def load(self, filepath: str, log_filepath: str):
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                mem_data = json.load(f)
                for d in mem_data:
                    entry = MemoryEntry(**d)
                    key = self._get_key(entry.subject, entry.predicate)
                    self.memories[key] = entry
                    
        if os.path.exists(log_filepath):
            with open(log_filepath, 'r') as f:
                log_data = json.load(f)
                for d in log_data:
                    self.change_log.append(ChangeLogEntry(**d))
