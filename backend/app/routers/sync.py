from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SyncResult
from ..sync import sync_notes
from ..config import load_config

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("", response_model=SyncResult)
def trigger_sync(db: Session = Depends(get_db)):
    """Manually trigger a sync of Obsidian notes."""
    config = load_config()
    return sync_notes(db, config)
