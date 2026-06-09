from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class VerifiableStatus(str, Enum):
    VERIFIABLE = "VERIFIABLE"
    NOT_VERIFIABLE = "NOT VERIFIABLE"

class ClaimLabel(str, Enum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NOT_ENOUGH_INFO = "NOT ENOUGH_INFO"

@dataclass
class Claim:
    id: str
    timestamp: Optional[str]
    source_id: str
    source_reliability: float
    verifiable: str
    label: str
    claim: str
    subject: str
    predicate: str
    object: Optional[str]
    notes: str = ""

class MemoryStatus(str, Enum):
    ACTIVE = "active"
    OUTDATED = "outdated"
    REJECTED = "rejected"
    LOW_CONFIDENCE = "low_confidence"
    FORGOTTEN = "forgotten"

class ActionType(str, Enum):
    ACCEPTED = "ACCEPTED"
    REVISED = "REVISED"
    UPDATED = "UPDATED"  # alias kept for backward compatibility
    DOWNGRADED = "DOWNGRADED"
    REJECTED = "REJECTED"
    FORGOTTEN = "FORGOTTEN"
    MERGED = "MERGED"

@dataclass
class ProvenanceRecord:
    timestamp: str
    action: str
    triggering_claim_id: str
    confidence_before: float
    confidence_after: float
    explanation: str

@dataclass
class MemoryEntry:
    subject: str
    predicate: str
    object: Optional[str]
    confidence: float
    status: str
    sources: List[str]
    first_seen: str
    last_updated: str
    corroboration_count: int = 1
    revision_count: int = 0
    provenance_history: List[dict] = field(default_factory=list)

@dataclass
class ChangeLogEntry:
    claim_id: str
    timestamp: str
    action: str
    reason: str
    old_value: Optional[str]
    new_value: Optional[str]
    confidence_delta: float
