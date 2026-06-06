"""
History API endpoints for clustering run persistence
Provides REST API for managing clustering run history with Redis backend
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field

from .history_service import history_service

logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class ClusteringRunCreate(BaseModel):
    """Model for creating a new clustering run"""
    id: str = Field(..., description="Unique identifier for the clustering run")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the run was created")
    dataset: str = Field(..., description="Name of the dataset used")
    treeType: str = Field(..., description="Type of clustering algorithm used")
    partitionMethod: str = Field(..., description="Partition method used")
    selectedK: int = Field(..., description="Number of clusters selected")
    selectedPower: float = Field(..., description="Power parameter used")
    actualClusterCount: Optional[int] = Field(None, description="Actual number of clusters found")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Algorithm parameters")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Clustering metrics")
    clusterData: Optional[Dict[str, Any]] = Field(None, description="Cluster data and results")
    treeData: Optional[Dict[str, Any]] = Field(None, description="Tree structure data")

class ClusteringRunResponse(BaseModel):
    """Model for clustering run response"""
    id: str
    timestamp: datetime
    dataset: str
    treeType: str
    partitionMethod: str
    selectedK: int
    selectedPower: float
    actualClusterCount: Optional[int] = None
    parameters: Dict[str, Any]
    metrics: Dict[str, Any]
    clusterData: Optional[Dict[str, Any]] = None
    treeData: Optional[Dict[str, Any]] = None

class ClusteringRunList(BaseModel):
    """Model for listing clustering runs"""
    runs: List[ClusteringRunResponse]
    total: int
    page: int
    limit: int
    hasMore: bool


class OperationResult(BaseModel):
    """Model for generic operation results"""
    success: bool
    message: str

def restore_run_cache(run_data: Dict[str, Any]):
    """
    Background task to restore SHiP cache from run data.
    Loads the dataset and populates the cache.
    """
    try:
        from .ship_cache_service import SHiPCacheService
        from .dataset_access import get_dataset_data
        
        dataset_name = run_data.get('dataset')
        tree_data = run_data.get('treeData')
        
        if not dataset_name or not tree_data:
            return
            
        # We need to find the file_id from the dataset name
        # This is a heuristic since we don't store file_id in history yet
        # In a real app, we should store file_id
        # For now, we'll try to use the dataset name as file_id if it looks like one,
        # or search for it.
        
        # Try to load data
        # Note: get_dataset_data might need to be async, but here we run in a thread pool via BackgroundTasks?
        # FastAPI BackgroundTasks run in the same loop if async, or thread if sync.
        # Since get_dataset_data is likely sync or we can use a sync wrapper.
        
        # Assuming we can get the data. For now, let's try to find the dataset in the cache/storage
        # This part depends on how dataset_access works.
        
        # If we can't easily get the data, we can't compute the hash, so we can't restore the cache key correctly.
        # However, if the frontend re-uploads the data or it's already cached, we might be fine.
        
        # Let's assume we can get the data if it's a toy dataset or recently uploaded
        from .toy_dataset_service import ToyDatasetService
        data = ToyDatasetService.get_dataset(dataset_name)
        
        if data is None:
            # Try to get from file storage if available globally
            # This is tricky without a proper DB mapping
            pass
            
        if data is not None:
            config = run_data.get('parameters', {})
            tree_type = run_data.get('treeType')
            
            # Restore to cache
            SHiPCacheService.restore_from_json(data, tree_type, config, tree_data)
            logger.info(f"[HistoryAPI] Restored cache for run {run_data.get('id')}")
            
    except Exception as e:
        logger.error(f"[HistoryAPI] Error in background cache restoration: {e}")

# Create router
router = APIRouter(prefix="/api/history", tags=["history"])

@router.post("/runs", response_model=ClusteringRunResponse)
async def create_clustering_run(run: ClusteringRunCreate):
    """
    Create a new clustering run in history
    
    Args:
        run: Clustering run data
        
    Returns:
        Created clustering run
    """
    try:
        logger.info(f"[HistoryAPI] Creating clustering run: {run.id}")
        
        # Convert to dict for service
        run_dict = run.dict()
        
        # Save to Redis
        success = history_service.save_run(run_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save clustering run")
        
        logger.info(f"[HistoryAPI] Successfully created clustering run: {run.id}")
        return ClusteringRunResponse(**run_dict)
        
    except Exception as e:
        logger.error(f"[HistoryAPI] Error creating clustering run: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create clustering run: {str(e)}")

@router.get("/runs", response_model=ClusteringRunList)
async def list_clustering_runs(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(50, ge=1, le=1000, description="Number of runs per page"),
):
    """
    List clustering runs with pagination
    
    Args:
        page: Page number (1-based)
        limit: Number of runs per page
        
    Returns:
        List of clustering runs with pagination info
    """
    try:
        logger.info(f"[HistoryAPI] Listing clustering runs: page={page}, limit={limit}")
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get runs from service
        runs = history_service.list_runs(limit=limit + 1, offset=offset)  # Get one extra to check if there are more
        
        # Check if there are more runs
        has_more = len(runs) > limit
        if has_more:
            runs = runs[:limit]  # Remove the extra run
        
        # Get total count
        total = history_service.get_run_count()
        
        # Convert to response models
        run_responses = [ClusteringRunResponse(**run) for run in runs]
        
        response = ClusteringRunList(
            runs=run_responses,
            total=total,
            page=page,
            limit=limit,
            hasMore=has_more
        )
        
        logger.info(f"[HistoryAPI] Listed {len(runs)} clustering runs")
        return response
        
    except Exception as e:
        logger.error(f"[HistoryAPI] Error listing clustering runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list clustering runs: {str(e)}")

@router.get("/runs/{run_id}", response_model=ClusteringRunResponse)
async def get_clustering_run(run_id: str, background_tasks: BackgroundTasks = None):
    """
    Get a specific clustering run by ID
    
    Args:
        run_id: Unique identifier for the clustering run
        
    Returns:
        Clustering run data
    """
    try:
        logger.info(f"[HistoryAPI] Getting clustering run: {run_id}")
        
        # Get run from service
        run_data = history_service.get_run(run_id)
        
        if not run_data:
            raise HTTPException(status_code=404, detail=f"Clustering run {run_id} not found")
            
        # Restore cache in background for immediate re-clustering capability
        if background_tasks and run_data.get('treeData'):
            background_tasks.add_task(restore_run_cache, run_data)
        
        logger.info(f"[HistoryAPI] Successfully retrieved clustering run: {run_id}")
        return ClusteringRunResponse(**run_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HistoryAPI] Error getting clustering run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get clustering run: {str(e)}")

@router.delete("/runs/{run_id}", response_model=OperationResult)
async def delete_clustering_run(run_id: str):
    """
    Delete a specific clustering run by ID
    
    Args:
        run_id: Unique identifier for the clustering run
        
    Returns:
        Operation result
    """
    try:
        logger.info(f"[HistoryAPI] Deleting clustering run: {run_id}")
        
        # Delete from service
        success = history_service.delete_run(run_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Clustering run {run_id} not found")
        
        logger.info(f"[HistoryAPI] Successfully deleted clustering run: {run_id}")
        return OperationResult(success=True, message=f"Clustering run {run_id} deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HistoryAPI] Error deleting clustering run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete clustering run: {str(e)}")

@router.delete("/runs", response_model=OperationResult)
async def clear_all_clustering_runs():
    """
    Clear all clustering runs from history
    
    Returns:
        Operation result
    """
    try:
        logger.info("[HistoryAPI] Clearing all clustering runs")
        
        # Clear from service
        success = history_service.clear_all_runs()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear clustering runs")
        
        logger.info("[HistoryAPI] Successfully cleared all clustering runs")
        return OperationResult(success=True, message="All clustering runs cleared successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HistoryAPI] Error clearing clustering runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear clustering runs: {str(e)}")



@router.get("/stats")
async def get_history_stats():
    """
    Get clustering history statistics
    
    Returns:
        Statistics about clustering runs
    """
    try:
        logger.info("[HistoryAPI] Getting history statistics")
        
        # Get count from service
        total_runs = history_service.get_run_count()
        
        # Get recent runs to analyze
        recent_runs = history_service.list_runs(limit=100)
        
        # Calculate statistics
        stats = {
            'totalRuns': total_runs,
            'recentRuns': len(recent_runs),
            'algorithms': {},
            'datasets': {},
            'avgClusterCount': 0
        }
        
        if recent_runs:
            # Count by algorithm
            for run in recent_runs:
                tree_type = run.get('treeType', 'unknown')
                stats['algorithms'][tree_type] = stats['algorithms'].get(tree_type, 0) + 1
                
                # Count by dataset
                dataset = run.get('dataset', 'unknown')
                stats['datasets'][dataset] = stats['datasets'].get(dataset, 0) + 1
            
            # Calculate average cluster count
            cluster_counts = [run.get('selectedK', 0) for run in recent_runs if run.get('selectedK')]
            if cluster_counts:
                stats['avgClusterCount'] = sum(cluster_counts) / len(cluster_counts)
        
        logger.info("[HistoryAPI] Successfully retrieved history statistics")
        return stats
        
    except Exception as e:
        logger.error(f"[HistoryAPI] Error getting history statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history statistics: {str(e)}")

@router.get("/health")
async def health_check():
    """
    Health check for history service
    
    Returns:
        Health status
    """
    try:
        # Check Redis connection
        redis_health = history_service.redis_svc.health_check() if history_service.redis_svc else {"status": "disabled"}
        
        # Get basic stats
        run_count = history_service.get_run_count()
        
        return {
            "status": "healthy",
            "redis": redis_health,
            "runCount": run_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[HistoryAPI] Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }