from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

class ClusteringStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ClusteringResultBase(BaseModel):
    operation_id: str
    cluster_id: Optional[str] = None
    dataset_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    status: ClusteringStatus = ClusteringStatus.PENDING

class ClusteringResultCreate(ClusteringResultBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClusteringResultUpdate(BaseModel):
    operation_id: Optional[str] = None
    cluster_id: Optional[str] = None
    dataset_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    status: Optional[ClusteringStatus] = None

class ClusteringResult(ClusteringResultBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True