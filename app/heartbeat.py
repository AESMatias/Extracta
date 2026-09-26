"""Keep the database active: a periodic task rewrites one row, so the database always shows a
recent write even on days when nobody signs in or uploads anything."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Heartbeat


def beat(db: Session, now: datetime) -> int:
    """Record one beat and return how many there have been."""
    row = db.get(Heartbeat, 1)
    if row is None:
        row = Heartbeat(id=1, beat_at=now, beats=0)
        db.add(row)
    row.beat_at = now
    row.beats += 1
    db.flush()
    return row.beats
