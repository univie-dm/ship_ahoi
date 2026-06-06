from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class SHiPObjectBase(BaseModel):
    data_hash: str
    tree_type: str
    config: Dict[str, Any]
    data_shape: List[int]

class SHiPObjectCreate(SHiPObjectBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ship_object_binary: Optional[bytes] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0

class SHiPObjectUpdate(BaseModel):
    data_hash: Optional[str] = None
    tree_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    data_shape: Optional[List[int]] = None
    ship_object_binary: Optional[bytes] = None
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    access_count: Optional[int] = None

class SHiPObject(SHiPObjectBase):
    id: str
    ship_object_binary: Optional[bytes] = None
    created_at: datetime
    last_accessed: datetime
    access_count: int

    class Config:
        from_attributes = True