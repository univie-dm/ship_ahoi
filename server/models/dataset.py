from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class DatasetBase(BaseModel):
    filename: str
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    data_hash: Optional[str] = None

class DatasetCreate(DatasetBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    processed_data: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DatasetUpdate(BaseModel):
    filename: Optional[str] = None
    original_filename: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = None
    data_hash: Optional[str] = None
    processed_data: Optional[Dict[str, Any]] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Dataset(DatasetBase):
    id: str
    processed_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True