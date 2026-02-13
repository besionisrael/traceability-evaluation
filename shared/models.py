"""
Shared data models for distributed traceability simulation.
"""
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Set, Optional


@dataclass
class Interaction:
    agent: str
    resource: str
    action: str   # 'acquire' or 'release'
    timestamp: int

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class ResourceState:
    """State of a single resource, as held by a resource node."""
    resource_id: str
    locks: Set[str] = field(default_factory=set)       # agents currently holding lock
    permissions: Dict[str, bool] = field(default_factory=dict)  # agent -> valid

    def to_dict(self):
        return {
            'resource_id': self.resource_id,
            'locks': list(self.locks),
            'permissions': self.permissions
        }

    @classmethod
    def from_dict(cls, d):
        obj = cls(resource_id=d['resource_id'])
        obj.locks = set(d['locks'])
        obj.permissions = d['permissions']
        return obj


# ─── TCP message protocol ────────────────────────────────────────────────────
# All messages are newline-delimited JSON objects.
#
# Request types:
#   GET_STATE              → returns ResourceState
#   PROCESS_MP             → record without validation (M_P)
#   PROCESS_ML             → local validation + record (M_L)
#   COMMIT                 → unconditional state update (used by M_D coordinator)
#
# Response:
#   { "ok": true/false, "state": {...}, "latency_us": float }

def encode_msg(msg: dict) -> bytes:
    return (json.dumps(msg) + '\n').encode('utf-8')

def decode_msg(data: bytes) -> dict:
    return json.loads(data.decode('utf-8').strip())
