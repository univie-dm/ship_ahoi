from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum

# Enums for validation
class MissingValueStrategy(str, Enum):
    keep = "keep"
    remove = "remove"
    fill_mean = "fill_mean"
    fill_median = "fill_median"
    fill_zero = "fill_zero"
    fill_mode = "fill_mode"

class NormalizationMethod(str, Enum):
    none = "none"
    standard = "standard"
    minmax = "minmax"
    robust = "robust"

class CategoricalEncoding(str, Enum):
    none = "none"
    label = "label"
    onehot = "onehot"

class DataType(str, Enum):
    numeric = "numeric"
    integer = "integer"
    categorical = "categorical"
    text = "text"
    mixed = "mixed"
    empty = "empty"

class ColumnUsage(str, Enum):
    feature = "feature"
    label = "label"
    ignore = "ignore"

# File Upload Models
class ColumnInfo(BaseModel):
    name: str
    data_type: DataType
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: List[str]
    is_categorical: bool
    is_numeric: bool
    unique_ratio: float = 0.0

class FileInfo(BaseModel):
    filename: str
    size: int
    extension: str
    mime_type: Optional[str] = None

class FileParseResponse(BaseModel):
    data: List[List[Any]]
    headers: List[str]
    has_headers: bool
    row_count: int
    column_count: int
    column_info: List[ColumnInfo]
    file_info: FileInfo
    missing_value_count: int
    data_types: Dict[str, str]
    # Additional metadata for different file types
    encoding: Optional[str] = None
    encoding_confidence: Optional[float] = None
    separator: Optional[str] = None

class ColumnConfig(BaseModel):
    name: str
    index: int
    data_type: DataType
    usage: ColumnUsage = ColumnUsage.feature
    normalize: bool = True
    is_categorical: bool = False

class DataProcessingConfig(BaseModel):
    missing_value_strategy: MissingValueStrategy = MissingValueStrategy.keep
    normalization: NormalizationMethod = NormalizationMethod.none
    categorical_encoding: CategoricalEncoding = CategoricalEncoding.label
    feature_columns: List[int] = []
    label_columns: List[int] = []
    ignored_columns: List[int] = []
    columns: List[ColumnConfig] = []

class DataProcessRequest(BaseModel):
    file_id: str  # Identifier for the uploaded file
    processing_config: DataProcessingConfig

class ProcessingInfo(BaseModel):
    missing_strategy: str
    normalization: str
    categorical_encoding: str
    original_shape: List[int]
    processed_shape: List[int]
    removed_rows: int
    categorical_info: Dict[str, Any] = {}
    normalization_info: Dict[str, Any] = {}

class DataProcessResponse(BaseModel):
    data: List[List[float]]
    headers: List[str]
    row_count: int
    column_count: int
    processing_info: ProcessingInfo
    feature_columns: List[int]
    ignored_columns: List[int]

class DataPreviewRequest(BaseModel):
    file_id: str
    num_rows: int = 10

class DataPreviewResponse(BaseModel):
    headers: List[str]
    data: List[List[Any]]
    total_rows: int
    preview_rows: int
    column_info: List[ColumnInfo]
    has_headers: bool

class DataAnalysisResponse(BaseModel):
    row_count: int
    column_count: int
    missing_value_count: int
    missing_value_percentage: float
    column_analysis: List[Dict[str, Any]]
    recommendations: Dict[str, Any]

# Error Response Model
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Progress Response Model
class ProgressResponse(BaseModel):
    stage: str
    progress: float
    message: str
    completed: bool = False

# Original ClusterParams model (extended for backward compatibility)
class ClusterParams(BaseModel):
    n_samples: int = 200
    n_clusters: int = 3
    random_state: int = 42
    sample: str = 'blobs'  # Sample dataset type - see ToyDatasetService for available options
    data: list | None = None  # Optional custom data (preprocessed)
    treeType: str = 'DCTree'
    partitioningMethod: str = 'Elbow'
    power: int = 2  # Power parameter for hierarchy similarity
    hierarchyLevel: int | None = None  # Added to fix AttributeError
    # Enhanced dataset parameters
    n_features: int | None = None  # Number of features for high-dimensional datasets (auto-detected if None)
    # Enhanced data processing fields
    isPreprocessed: bool = False  # Indicates if data is already preprocessed
    hasHeaders: bool = False  # Indicates if first row contains headers that need to be stripped
    featureHeaders: list[str] | None = None  # Headers for feature columns
    dataConfig: dict | None = None  # Configuration used for preprocessing
    # Label/Target support for ARI calculation
    labelColumns: list[int] | None = None  # Indices of label columns
    labelData: list | None = None  # Ground truth labels for ARI calculation
    # File upload integration
    fileId: str | None = None  # Reference to uploaded file data
    # Dimensionality reduction control for performance optimization
    skip_umap: bool = False  # Skip UMAP computation for faster response
    skip_tsne: bool = False  # Skip t-SNE computation for faster response
    groundTruthColumn: int | None = None # Column to be used as ground truth
    # Tree visualization options
    realTreeDepth: int = 100  # Depth limit for real trees (1-500)
    # Settings override parameters
    umap_params: Optional[Dict[str, Any]] = None  # Custom UMAP parameters from settings
    fast_mode: bool = False  # Fast mode toggle from settings


# Settings Models
class UMAPMetric(str, Enum):
    euclidean = "euclidean"
    manhattan = "manhattan"
    chebyshev = "chebyshev"
    minkowski = "minkowski"
    cosine = "cosine"
    correlation = "correlation"


class UMAPSettings(BaseModel):
    n_neighbors: int = Field(default=15, ge=5, le=100, description="Number of neighbors for UMAP")
    min_dist: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum distance for UMAP")
    n_epochs: int = Field(default=200, ge=50, le=500, description="Number of optimization epochs")
    metric: UMAPMetric = Field(default=UMAPMetric.euclidean, description="Distance metric for UMAP")
    spread: float = Field(default=1.0, ge=0.1, le=3.0, description="Scale of embedded points")
    negative_sample_rate: int = Field(default=5, ge=1, le=20, description="Negative samples per positive sample")
    fast_mode: bool = Field(default=False, description="Enable fast mode with reduced quality")


class PerformanceSettings(BaseModel):
    skip_umap: bool = Field(default=False, description="Skip UMAP computation for faster processing")
    skip_tsne: bool = Field(default=False, description="Skip t-SNE computation for faster processing")


class AppSettings(BaseModel):
    umap_settings: UMAPSettings = Field(default_factory=UMAPSettings, description="UMAP configuration")
    performance_settings: PerformanceSettings = Field(default_factory=PerformanceSettings, description="Performance optimization settings")


class SettingsRequest(BaseModel):
    umap_settings: UMAPSettings
    performance_settings: PerformanceSettings


class SettingsResponse(BaseModel):
    settings: AppSettings
    message: str = "Settings retrieved successfully"


class SettingsUpdateResponse(BaseModel):
    success: bool
    message: str
    settings: AppSettings



