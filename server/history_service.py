"""
Clustering History Service for SHiP Application
Handles persistent storage and retrieval of clustering run history using Redis
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict

from .redis_service import RedisService, redis_service

logger = logging.getLogger(__name__)

@dataclass
class ClusteringHistoryItem:
    """Data structure for clustering run history items"""
    id: str
    timestamp: datetime
    dataset: str
    treeType: str
    partitionMethod: str
    selectedK: int
    selectedPower: float
    actualClusterCount: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    
    # Serialized data for cluster and tree results
    clusterData: Optional[str] = None  # JSON serialized
    treeData: Optional[str] = None     # JSON serialized
    
    # Metadata
    created_at: Optional[str] = None
    last_accessed: Optional[str] = None
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime to ISO string
        if isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClusteringHistoryItem':
        """Create from dictionary"""
        # Convert ISO string back to datetime
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class ClusteringHistoryService:
    """Service for managing clustering run history with Redis persistence"""
    
    def __init__(self, redis_svc: RedisService = None):
        self.redis_svc = redis_svc or redis_service
        self.key_prefix = "clustering_history"
        self.index_key = "clustering_history_index"
        
    def _get_history_key(self, run_id: str) -> str:
        """Generate Redis key for a specific clustering run"""
        return f"{self.key_prefix}:{run_id}"
    
    def _serialize_run_data(self, data: Any) -> str:
        """Serialize run data to JSON string"""
        if data is None:
            return ""
        try:
            return json.dumps(data, default=str)
        except Exception as e:
            logger.warning(f"Failed to serialize run data: {e}")
            return ""
    
    def _deserialize_run_data(self, data: str) -> Any:
        """Deserialize run data from JSON string"""
        if not data:
            return None
        try:
            return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to deserialize run data: {e}")
            return None
    
    def save_run(self, run_data: Dict[str, Any]) -> bool:
        """
        Save a clustering run to Redis history
        
        Args:
            run_data: Dictionary containing run information
            
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        
        try:
            # Extract required fields
            run_id = run_data.get('id')
            if not run_id:
                logger.error("Run ID is required for saving history")
                return False
            
            logger.info(f"[HistoryService] Saving clustering run: {run_id}")
            
            # Convert to history item
            history_item = ClusteringHistoryItem(
                id=run_id,
                timestamp=run_data.get('timestamp', datetime.utcnow()),
                dataset=run_data.get('dataset', ''),
                treeType=run_data.get('treeType', ''),
                partitionMethod=run_data.get('partitionMethod', ''),
                selectedK=run_data.get('selectedK', 0),
                selectedPower=run_data.get('selectedPower', 1.0),
                actualClusterCount=run_data.get('actualClusterCount'),
                parameters=run_data.get('parameters', {}),
                metrics=run_data.get('metrics', {}),
                clusterData=self._serialize_run_data(run_data.get('clusterData')),
                treeData=self._serialize_run_data(run_data.get('treeData')),
                created_at=datetime.utcnow().isoformat(),
                last_accessed=datetime.utcnow().isoformat(),
                access_count=1
            )
            
            # Save to Redis if available
            if self.redis_svc and self.redis_svc.client:
                try:
                    key = self._get_history_key(run_id)
                    
                    # Store as Redis hash
                    history_dict = history_item.to_dict()
                    redis_data = {k: str(v) for k, v in history_dict.items()}
                    
                    # Use pipeline for atomic operation
                    pipe = self.redis_svc.client.pipeline()
                    pipe.hset(key, mapping=redis_data)
                    pipe.zadd(self.index_key, {run_id: time.time()})
                    pipe.execute()
                    
                    logger.info(f"[HistoryService] Successfully saved run {run_id} to Redis")
                    
                except Exception as e:
                    logger.error(f"[HistoryService] Failed to save run {run_id} to Redis: {e}")
                    return False
            else:
                logger.warning("[HistoryService] Redis not available, run not persisted")
                return False
            
            total_time = time.time() - start_time
            logger.info(f"[HistoryService] save_run completed in {total_time:.4f} seconds")
            return True
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[HistoryService] Error saving run: {e} (took {total_time:.4f} seconds)")
            return False
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a clustering run from Redis history
        
        Args:
            run_id: The run ID to retrieve
            
        Returns:
            Dict containing run data or None if not found
        """
        start_time = time.time()
        
        try:
            if not self.redis_svc or not self.redis_svc.client:
                logger.warning("[HistoryService] Redis not available for run retrieval")
                return None
            
            key = self._get_history_key(run_id)
            result = self.redis_svc.client.hgetall(key)
            
            if not result:
                logger.debug(f"[HistoryService] Run {run_id} not found in Redis")
                return None
            
            # Convert bytes to strings
            history_dict = {}
            for k, v in result.items():
                k_str = k.decode() if isinstance(k, bytes) else k
                v_str = v.decode() if isinstance(v, bytes) else v
                history_dict[k_str] = v_str
            
            # Update access statistics
            pipe = self.redis_svc.client.pipeline()
            pipe.hset(key, "last_accessed", datetime.utcnow().isoformat())
            pipe.hincrby(key, "access_count", 1)
            pipe.execute()
            
            # Convert back to original format
            run_data = {
                'id': history_dict.get('id'),
                'timestamp': datetime.fromisoformat(history_dict.get('timestamp')),
                'dataset': history_dict.get('dataset'),
                'treeType': history_dict.get('treeType'),
                'partitionMethod': history_dict.get('partitionMethod'),
                'selectedK': int(history_dict.get('selectedK', 0)),
                'selectedPower': float(history_dict.get('selectedPower', 1.0)),
                'actualClusterCount': int(history_dict.get('actualClusterCount')) if history_dict.get('actualClusterCount') else None,
                'parameters': json.loads(history_dict.get('parameters', '{}')),
                'metrics': json.loads(history_dict.get('metrics', '{}')),
                'clusterData': self._deserialize_run_data(history_dict.get('clusterData')),
                'treeData': self._deserialize_run_data(history_dict.get('treeData'))
            }
            
            total_time = time.time() - start_time
            logger.info(f"[HistoryService] Retrieved run {run_id} in {total_time:.4f} seconds")
            return run_data
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[HistoryService] Error retrieving run {run_id}: {e} (took {total_time:.4f} seconds)")
            return None
    
    def list_runs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List clustering runs with pagination
        
        Args:
            limit: Maximum number of runs to return
            offset: Number of runs to skip
            
        Returns:
            List of run dictionaries
        """
        start_time = time.time()
        
        try:
            if not self.redis_svc or not self.redis_svc.client:
                logger.warning("[HistoryService] Redis not available for run listing")
                return []
            
            # Get run IDs sorted by timestamp (most recent first)
            run_ids = self.redis_svc.client.zrevrange(
                self.index_key, 
                offset, 
                offset + limit - 1
            )
            
            runs = []
            for run_id in run_ids:
                run_id_str = run_id.decode() if isinstance(run_id, bytes) else run_id
                run_data = self.get_run(run_id_str)
                if run_data:
                    runs.append(run_data)
            
            total_time = time.time() - start_time
            logger.info(f"[HistoryService] Listed {len(runs)} runs in {total_time:.4f} seconds")
            return runs
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[HistoryService] Error listing runs: {e} (took {total_time:.4f} seconds)")
            return []
    
    def delete_run(self, run_id: str) -> bool:
        """
        Delete a clustering run from Redis history
        
        Args:
            run_id: The run ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        
        try:
            if not self.redis_svc or not self.redis_svc.client:
                logger.warning("[HistoryService] Redis not available for run deletion")
                return False
            
            key = self._get_history_key(run_id)
            
            # Use pipeline for atomic operation
            pipe = self.redis_svc.client.pipeline()
            pipe.delete(key)
            pipe.zrem(self.index_key, run_id)
            results = pipe.execute()
            
            success = results[0] > 0
            
            total_time = time.time() - start_time
            logger.info(f"[HistoryService] Deleted run {run_id} in {total_time:.4f} seconds, success: {success}")
            return success
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[HistoryService] Error deleting run {run_id}: {e} (took {total_time:.4f} seconds)")
            return False
    
    def clear_all_runs(self) -> bool:
        """
        Clear all clustering runs from Redis history
        
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        
        try:
            if not self.redis_svc or not self.redis_svc.client:
                logger.warning("[HistoryService] Redis not available for clearing runs")
                return False
            
            # Get all run IDs
            run_ids = self.redis_svc.client.zrange(self.index_key, 0, -1)
            
            if not run_ids:
                logger.info("[HistoryService] No runs to clear")
                return True
            
            # Delete all runs and index
            pipe = self.redis_svc.client.pipeline()
            for run_id in run_ids:
                run_id_str = run_id.decode() if isinstance(run_id, bytes) else run_id
                key = self._get_history_key(run_id_str)
                pipe.delete(key)
            
            pipe.delete(self.index_key)
            pipe.execute()
            
            total_time = time.time() - start_time
            logger.info(f"[HistoryService] Cleared {len(run_ids)} runs in {total_time:.4f} seconds")
            return True
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[HistoryService] Error clearing runs: {e} (took {total_time:.4f} seconds)")
            return False
    
    def get_run_count(self) -> int:
        """
        Get the total number of clustering runs in history
        
        Returns:
            int: Number of runs
        """
        try:
            if not self.redis_svc or not self.redis_svc.client:
                return 0
            
            return self.redis_svc.client.zcard(self.index_key)
            
        except Exception as e:
            logger.error(f"[HistoryService] Error getting run count: {e}")
            return 0
    

# Global history service instance
history_service = ClusteringHistoryService()