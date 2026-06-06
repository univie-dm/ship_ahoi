from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

class KSelectionCacheBase(BaseModel):
    dataset_id: str
    cache_data: Dict[str, Any]

class KSelectionCacheCreate(KSelectionCacheBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(hours=2))

class KSelectionCacheUpdate(BaseModel):
    dataset_id: Optional[str] = None
    cache_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

class KSelectionCache(KSelectionCacheBase):
    id: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True