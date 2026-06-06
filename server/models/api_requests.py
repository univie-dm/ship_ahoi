from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class ClusterRequest(BaseModel):
    n_samples: int = 200
    n_clusters: int = 3
    random_state: int = 42


class KSelectionRequest(BaseModel):
    sample: Optional[str] = 'blobs'
    n_samples: Optional[int] = 200
    data: Optional[List[List[float]]] = None  # type: ignore[name-defined]
    treeType: str = 'DCTree'
    power: float = 2.0
    k_range: List[int] = [2, 3, 4, 5, 6, 7, 8, 9, 10]
    random_state: int = 42
    fileId: Optional[str] = None


class ClusterVisualizationRequest(BaseModel):
    data: Optional[List[List[float]]] = None  # type: ignore[name-defined]
    data_cache_id: Optional[str] = None
    fileId: Optional[str] = None
    n_clusters: int
    treeType: str = 'DCTree'
    power: float = 2.0
    random_state: int = 42
    skip_umap: bool = False
    skip_tsne: bool = False
    # Add fields to align with clustering page
    partitioningMethod: Optional[str] = 'K'
    sample: Optional[str] = None
    # Tree visualization options
    realTreeDepth: int = 100  # depth for real tree (1-500)


class ClusteringAnalysisRequest(BaseModel):
    """Request model for advanced clustering analysis"""
    run_id: str
    cluster_data: Any
    tree_data: Optional[Any] = None
    selected_features: List[int]
    feature_names: List[str]
    analysis_options: Dict[str, bool]


class DatasetInsightsRequest(BaseModel):
    """Request model for dataset insights analysis"""
    dataset: str
    data: Optional[List[List[float]]] = None  # type: ignore[name-defined]
    selected_features: List[int]
    feature_names: List[str]
    analysis_type: str = 'dataset_insights'
    options: Dict[str, Any] = {}


class ClusterSummaryRequest(BaseModel):
    """Request model for cluster summary analysis"""
    cluster_data: Any
    selected_features: List[int]
    feature_names: List[str]
    options: Dict[str, Any] = {}


class FeatureImportanceRequest(BaseModel):
    """Request model for feature importance analysis"""
    cluster_data: Any
    selected_features: List[int]
    feature_names: List[str]
    options: Dict[str, Any] = {}


class FeatureImportanceDatasetRequest(BaseModel):
    """Request model for dataset-based feature importance analysis"""
    dataset_id: str
    cluster_labels: List[int]
    selected_features: List[int] = []
    feature_names: List[str] = []
    options: Dict[str, Any] = {}


class FeatureStatisticsRequest(BaseModel):
    """Request model for feature statistics analysis"""
    data: List[List[float]]  # type: ignore[name-defined]
    selected_features: List[int]
    feature_names: List[str]
    options: Dict[str, Any] = {}


class CorrelationMatrixRequest(BaseModel):
    """Request model for correlation matrix analysis"""
    data: List[List[float]]  # type: ignore[name-defined]
    selected_features: List[int]
    feature_names: List[str]
    options: Dict[str, Any] = {}


class DatasetAnalysisRequest(BaseModel):
    """Request model for dataset-based analysis (optimized for large datasets)"""
    dataset_id: str  # Can be cluster_id, file_id, or sample dataset name
    selected_features: List[int]
    feature_names: List[str]
    options: Dict[str, Any] = {}
    sample_size: Optional[int] = None  # Optional sampling for very large datasets


class FeatureDistributionRequest(BaseModel):
    """Request model for feature distribution analysis"""
    dataset_id: str
    selected_features: List[int]
    feature_names: List[str]
    feature_index: int  # Index within the selected features array
    options: Dict[str, Any] = {}
    sample_size: Optional[int] = None

