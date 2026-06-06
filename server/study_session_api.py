from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from .study_session_service import save_parameter_log, get_session_log, clear_session

router = APIRouter(prefix="/study-session", tags=["study-session"])
logger = logging.getLogger(__name__)

class StudyLogEntry(BaseModel):
    source: str
    params: Dict[str, Any]
    metrics: Dict[str, Any]
    elapsedSeconds: int
    timestamp: str

@router.post("/{session_id}/log")
async def log_parameter_set(session_id: str, entry: StudyLogEntry):
    success = save_parameter_log(session_id, entry.model_dump())
    if not success:
        logger.warning(f"Failed to log session entry for {session_id}")
    return {"status": "success", "saved": success}

@router.get("/{session_id}", response_model=List[Dict[str, Any]])
async def get_session(session_id: str):
    return get_session_log(session_id)

@router.delete("/{session_id}")
async def clear_session_endpoint(session_id: str):
    success = clear_session(session_id)
    return {"status": "success", "cleared": success}
