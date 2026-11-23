"""L9 tamper-evident audit: hash = SHA256(prev_hash || canonical record). Editing, deleting or reordering a past row breaks the chain (P6)."""

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

GENESIS_HASH = "0" * 64


def _utc_naive(ts: datetime) -> str:
    # SQLite hands back naive UTC and Postgres aware datetimes; hash the same text for both.
    return (ts.astimezone(timezone.utc) if ts.tzinfo else ts).replace(tzinfo=None).isoformat()


def record_hash(
    *, seq: int, prev_hash: str, incident_id: str | None, actor: str, action: str, details: dict, timestamp: datetime
) -> str:
    record = {
        "seq": seq,
        "incident_id": incident_id,
        "actor": actor,
        "action": action,
        "details": details,
        "timestamp": _utc_naive(timestamp),
    }
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(prev_hash.encode() + payload.encode()).hexdigest()


def verify_chain(rows: Iterable[Any]) -> dict:
    """rows: objects with seq, prev_hash, hash, incident_id, actor, action, details, timestamp, ordered by seq.

    shortcut: deleting the newest rows (tail truncation) is not detectable from the chain alone;
    anchor the head hash externally (e.g. signed daily checkpoint) if that threat matters.
    """
    prev, checked = GENESIS_HASH, 0
    for expected_seq, row in enumerate(rows, start=1):
        if row.seq != expected_seq:
            return {"ok": False, "checked": checked, "broken_at_seq": expected_seq, "reason": "missing or reordered row"}
        if row.prev_hash != prev:
            return {"ok": False, "checked": checked, "broken_at_seq": row.seq, "reason": "prev_hash mismatch"}
        try:
            recomputed = record_hash(
                seq=row.seq, prev_hash=row.prev_hash, incident_id=row.incident_id, actor=row.actor,
                action=row.action, details=row.details, timestamp=row.timestamp,
            )
        except (TypeError, ValueError, AttributeError):
            recomputed = None
        if recomputed != row.hash:
            return {"ok": False, "checked": checked, "broken_at_seq": row.seq, "reason": "record modified"}
        prev, checked = row.hash, checked + 1
    return {"ok": True, "checked": checked, "broken_at_seq": None, "reason": None}
