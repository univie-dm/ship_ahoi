from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

class DRMethod(str, Enum):
    UMAP = "umap"
    TSNE = "tsne"

class DRStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DimensionalityReductionResultBase(BaseModel):
    cluster_id: str
    method: DRMethod
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    status: DRStatus = DRStatus.PENDING

class DimensionalityReductionResultCreate(DimensionalityReductionResultBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DimensionalityReductionResultUpdate(BaseModel):
    cluster_id: Optional[str] = None
    method: Optional[DRMethod] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    status: Optional[DRStatus] = None

class DimensionalityReductionResult(DimensionalityReductionResultBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True