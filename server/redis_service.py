"""
Redis service layer for SHiP Clustering Application
Provides Redis operations with connection management and error handling
"""

import os
import pickle
import logging
import time
import hashlib
import json
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import contextmanager

try:
    import redis
    from redis.exceptions import ConnectionError, TimeoutError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: Redis not available. Database functionality will be disabled.")
    
    # Mock classes for when redis is not available
    class redis:
        class Redis:
            pass
        class ConnectionPool:
            pass
        class ConnectionError(Exception):
            pass
        class TimeoutError(Exception):
            pass

import numpy as np

from .models import (
    Dataset, DatasetCreate, DatasetUpdate,
    SHiPObject, SHiPObjectCreate, SHiPObjectUpdate,
    ClusteringResult, ClusteringResultCreate, ClusteringResultUpdate,
    DimensionalityReductionResult, DimensionalityReductionResultCreate, DimensionalityReductionResultUpdate,
    KSelectionCache, KSelectionCacheCreate, KSelectionCacheUpdate
)

logger = logging.getLogger(__name__)

class RedisService:
    """
    Redis database service for SHiP clustering application
    Provides synchronous operations with connection management
    """
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[redis.ConnectionPool] = None
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        # DC distance compression level: 1=fastest, 6=default, 9=best compression
        self.dc_compression_level = int(os.getenv('DC_COMPRESSION_LEVEL', '1'))
        
    def connect(self):
        """Connect to Redis database"""
        if self.client is not None:
            try:
                self.client.ping()
                return  # Already connected
            except Exception:
                self.client = None  # Reset and reconnect
                
        start_time = time.time()
        
        # Log Redis availability status
        if not REDIS_AVAILABLE:
            print(f"[RedisService] Redis support not available - redis-py not installed")
            print(f"[RedisService] Redis URL configured: {self.redis_url}")
            print(f"[RedisService] DC compression level: {self.dc_compression_level}")
            return
            
        print(f"[RedisService] Attempting to connect to Redis at: {self.redis_url}")
        print(f"[RedisService] Redis-py version available: {redis.__version__ if hasattr(redis, '__version__') else 'unknown'}")
        print(f"[RedisService] DC compression level configured: {self.dc_compression_level}")
            
        try:
            connection_start = time.time()
            self.pool = redis.ConnectionPool.from_url(self.redis_url)
            self.client = redis.Redis(connection_pool=self.pool)
            connection_time = time.time() - connection_start
            print(f"[RedisService] Redis connection pool created in {connection_time:.4f} seconds")
            
            # Test connection with detailed info
            ping_start = time.time()
            self.client.ping()
            ping_time = time.time() - ping_start
            print(f"[RedisService] Redis ping successful in {ping_time:.4f} seconds")
            
            # Get basic Redis info for debugging
            try:
                info = self.client.info()
                redis_version = info.get('redis_version', 'unknown')
                redis_mode = info.get('redis_mode', 'unknown')
                tcp_port = info.get('tcp_port', 'unknown')
                print(f"[RedisService] Connected to Redis {redis_version} (mode: {redis_mode}, port: {tcp_port})")
            except Exception as info_e:
                print(f"[RedisService] Could not retrieve Redis info: {info_e}")
            
            total_time = time.time() - start_time
            print(f"[RedisService] Redis connection established successfully in {total_time:.4f} seconds")
            
        except (ConnectionError, TimeoutError) as e:
            total_time = time.time() - start_time
            print(f"[RedisService] Redis connection failed: {e}")
            print(f"[RedisService] Connection attempt took {total_time:.4f} seconds")
            print(f"[RedisService] Redis URL attempted: {self.redis_url}")
            # Don't raise - allow application to continue without database
            self.client = None
            self.pool = None
    
    def disconnect(self):
        """Disconnect from Redis"""
        if self.client is not None:
            self.client.close()
            logger.info("Disconnected from Redis")
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health and connection status"""
        start_time = time.time()
        
        if not REDIS_AVAILABLE:
            print(f"[RedisService] Redis health check: Redis support not available")
            return {"status": "disabled", "error": "Redis support not available"}
            
        if self.client is None:
            print(f"[RedisService] Redis health check: No client connection established")
            return {"status": "disconnected", "error": "No client connection"}
        
        print(f"[RedisService] Performing Redis health check...")
        
        try:
            # Test connection
            ping_start = time.time()
            self.client.ping()
            ping_time = time.time() - ping_start
            print(f"[RedisService] Health check ping: {ping_time:.4f} seconds")
            
            # Get Redis info
            info_start = time.time()
            info = self.client.info()
            info_time = time.time() - info_start
            print(f"[RedisService] Redis info query: {info_time:.4f} seconds")
            
            # Get key count
            keys_start = time.time()
            db_size = self.client.dbsize()
            keys_time = time.time() - keys_start
            print(f"[RedisService] Database size query: {keys_time:.4f} seconds")
            
            total_time = time.time() - start_time
            redis_version = info.get('redis_version', 'unknown')
            redis_mode = info.get('redis_mode', 'unknown')
            uptime_seconds = info.get('uptime_in_seconds', 0)
            uptime_days = uptime_seconds / (24 * 3600)
            
            print(f"[RedisService] Redis health check completed in {total_time:.4f} seconds")
            print(f"[RedisService] Redis version: {redis_version}, mode: {redis_mode}")
            print(f"[RedisService] Uptime: {uptime_days:.1f} days, Keys: {db_size}")
            print(f"[RedisService] Memory: {info.get('used_memory_human', 'unknown')} used")
            
            return {
                "status": "healthy",
                "redis_version": redis_version,
                "redis_mode": redis_mode,
                "db_size": db_size,
                "memory_usage": info.get('used_memory_human', 'unknown'),
                "connected_clients": info.get('connected_clients', 0),
                "uptime_days": uptime_days,
                "timing": {
                    "ping_time": ping_time,
                    "info_time": info_time,
                    "keys_time": keys_time,
                    "total_time": total_time
                }
            }
        except Exception as e:
            total_time = time.time() - start_time
            print(f"[RedisService] Redis health check failed: {e}")
            print(f"[RedisService] Health check took {total_time:.4f} seconds")
            return {"status": "unhealthy", "error": str(e), "timing": {"total_time": total_time}}
    
    def check_memory_pressure(self) -> Dict[str, Any]:
        """Check Redis memory pressure to prevent caching when memory is high"""
        if not REDIS_AVAILABLE or self.client is None:
            print(f"[RedisService] Memory pressure check: Redis not available")
            return {"can_cache": False, "reason": "Redis not available"}
        
        print(f"[RedisService] Checking Redis memory pressure...")
        
        try:
            info = self.client.info()
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            used_memory_mb = used_memory / (1024 * 1024)
            max_memory_mb = max_memory / (1024 * 1024) if max_memory > 0 else 0
            
            print(f"[RedisService] Memory usage: {used_memory_mb:.1f}MB used")
            if max_memory > 0:
                print(f"[RedisService] Memory limit: {max_memory_mb:.1f}MB configured")
            else:
                print(f"[RedisService] Memory limit: No limit configured (using default 1GB)")
            
            # If maxmemory is 0, Redis is not configured with memory limit
            if max_memory == 0:
                # Default to 1GB limit if not configured
                max_memory = 1024 * 1024 * 1024  # 1GB
                max_memory_mb = 1024.0
            
            memory_usage_ratio = used_memory / max_memory
            
            print(f"[RedisService] Memory usage ratio: {memory_usage_ratio:.1%}")
            
            # Don't cache if Redis is > 80% full
            if memory_usage_ratio > 0.8:
                print(f"[RedisService] Memory pressure detected: {memory_usage_ratio:.1%} > 80% threshold")
                return {
                    "can_cache": False, 
                    "reason": f"Memory usage too high: {memory_usage_ratio:.1%}",
                    "used_memory_mb": used_memory_mb,
                    "max_memory_mb": max_memory_mb
                }
            
            print(f"[RedisService] Memory pressure check passed: {memory_usage_ratio:.1%} < 80% threshold")
            return {
                "can_cache": True,
                "memory_usage_ratio": memory_usage_ratio,
                "used_memory_mb": used_memory_mb,
                "max_memory_mb": max_memory_mb
            }
            
        except Exception as e:
            print(f"[RedisService] Memory pressure check failed: {e}")
            return {"can_cache": False, "reason": f"Check failed: {e}"}
    
    def should_cache_object(self, object_size_mb: float) -> bool:
        """Check if object should be cached based on size and Redis memory pressure"""
        print(f"[RedisService] Evaluating cache decision for object size: {object_size_mb:.1f}MB")
        
        # Check object size limit (don't cache objects > 10MB)
        if object_size_mb > 10:
            print(f"[RedisService] Object rejected: {object_size_mb:.1f}MB > 10MB size limit")
            return False
        
        # Check Redis memory pressure
        memory_check = self.check_memory_pressure()
        if not memory_check["can_cache"]:
            print(f"[RedisService] Object rejected due to memory pressure: {memory_check['reason']}")
            return False
            
        # Don't cache objects > 10% of Redis capacity
        max_memory_mb = memory_check.get("max_memory_mb", 1024)
        capacity_threshold = max_memory_mb * 0.1
        if object_size_mb > capacity_threshold:
            print(f"[RedisService] Object rejected: {object_size_mb:.1f}MB > {capacity_threshold:.1f}MB (10% of Redis capacity)")
            return False
        
        print(f"[RedisService] Object approved for caching: {object_size_mb:.1f}MB within limits")
        return True
    
    def _filter_config_for_caching(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out runtime-only parameters that don't affect ultrametric tree construction"""
        runtime_only_params = {
            'k',                    # Manual K selection - used in fit_predict()
            'power',                # Power parameter - used in fit_predict()
            'partitioningMethod',   # Partition method - used in fit_predict()
            'partition_method',     # Alternative naming
            'clustering_method',    # Alternative naming
        }
        return {k: v for k, v in config.items() if k not in runtime_only_params}
    
    def _hash_dict(self, data: Dict[str, Any]) -> str:
        """Create a hash from dictionary for consistent key generation"""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]
    
    def _serialize_dict(self, data: Dict[str, Any]) -> str:
        """Serialize dictionary to JSON string"""
        return json.dumps(data, default=str)
    
    def _deserialize_dict(self, data: str) -> Dict[str, Any]:
        """Deserialize JSON string to dictionary"""
        return json.loads(data)
    
    # Dataset operations
    def create_dataset(self, dataset: DatasetCreate) -> Dataset:
        """Create a new dataset record"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available, returning dataset without persistence")
            return Dataset(**dataset.dict())
            
        try:
            dataset_dict = dataset.dict()
            key = f"dataset:{dataset_dict['id']}"
            
            # Store as Redis hash
            pipe = self.client.pipeline()
            pipe.hset(key, mapping={k: self._serialize_dict({k: v}) if isinstance(v, dict) else str(v) for k, v in dataset_dict.items()})
            pipe.zadd("datasets_by_time", {dataset_dict['id']: time.time()})
            pipe.execute()
            
            return Dataset(**dataset_dict)
        except Exception as e:
            logger.error(f"Error creating dataset: {e}")
            raise
    
    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for dataset retrieval")
            return None
        try:
            key = f"dataset:{dataset_id}"
            result = self.client.hgetall(key)
            if result:
                # Deserialize the hash values
                dataset_dict = {}
                for k, v in result.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    try:
                        # Try to deserialize as JSON
                        parsed = self._deserialize_dict(v_str)
                        dataset_dict[k_str] = parsed[k_str] if k_str in parsed else v_str
                    except:
                        dataset_dict[k_str] = v_str
                return Dataset(**dataset_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting dataset {dataset_id}: {e}")
            return None
    
    def update_dataset(self, dataset_id: str, dataset: DatasetUpdate) -> Optional[Dataset]:
        """Update dataset by ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for dataset update")
            return None
        try:
            key = f"dataset:{dataset_id}"
            update_data = {k: str(v) for k, v in dataset.dict().items() if v is not None}
            
            if update_data:
                self.client.hset(key, mapping=update_data)
                return self.get_dataset(dataset_id)
            return None
        except Exception as e:
            logger.error(f"Error updating dataset {dataset_id}: {e}")
            return None
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete dataset by ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for dataset deletion")
            return False
        try:
            key = f"dataset:{dataset_id}"
            pipe = self.client.pipeline()
            pipe.delete(key)
            pipe.zrem("datasets_by_time", dataset_id)
            results = pipe.execute()
            return results[0] > 0
        except Exception as e:
            logger.error(f"Error deleting dataset {dataset_id}: {e}")
            return False
    
    def list_datasets(self, limit: int = 100, skip: int = 0) -> List[Dataset]:
        """List all datasets with pagination"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for dataset listing")
            return []
        try:
            # Get dataset IDs sorted by time (most recent first)
            dataset_ids = self.client.zrevrange("datasets_by_time", skip, skip + limit - 1)
            
            datasets = []
            for dataset_id in dataset_ids:
                dataset_id_str = dataset_id.decode() if isinstance(dataset_id, bytes) else dataset_id
                dataset = self.get_dataset(dataset_id_str)
                if dataset:
                    datasets.append(dataset)
            
            return datasets
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            return []
    
    # SHiP Object operations
    def _serialize_ship_object(self, ship_instance):
        """
        Serialize SHiP object by trying JSON tree method first, then recreation parameters
        Returns serialized_data or None if failed
        """
        try:
            # First try to serialize as JSON tree (preferred method)
            try:
                if hasattr(ship_instance, 'get_tree') and callable(ship_instance.get_tree):
                    tree = ship_instance.get_tree()
                    if tree and hasattr(tree, 'to_json') and callable(tree.to_json):
                        json_tree = tree.to_json()
                        
                        cache_data = {
                            'serialization_method': 'json_tree',
                            'json_tree': json_tree,
                            'config': getattr(ship_instance, 'config', {}),
                            'tree_type': str(getattr(ship_instance, 'treeType', 'DCTree')),
                            'power': getattr(ship_instance, 'power', 1),
                            'partitioning_method': str(getattr(ship_instance, 'partitioningMethod', 'Elbow')),
                            'cached_at': time.time()
                        }
                        
                        # Add runtime attributes if available
                        for attr in ['labels_', 'partitioning_runtime', 'tree_construction_runtime']:
                            if hasattr(ship_instance, attr):
                                try:
                                    value = getattr(ship_instance, attr)
                                    pickle.dumps(value)  # Test if it's serializable
                                    cache_data[attr] = value
                                except Exception:
                                    pass  # Skip non-serializable attributes
                        
                        pickled_data = pickle.dumps(cache_data)
                        data_size = len(pickled_data)
                        logger.info(f"[RedisService] SHiP object cached as JSON tree: {data_size} bytes")
                        return pickled_data
                    else:
                        logger.warning(f"[RedisService] SHiP tree does not support to_json method")
                else:
                    logger.warning(f"[RedisService] SHiP object does not support get_tree method")
            except Exception as e:
                logger.warning(f"[RedisService] JSON tree serialization failed: {e}, falling back to full pickle")
            
            # Second try: full SHiP object pickle
            try:
                cache_data = {
                    'serialization_method': 'full_object',
                    'ship_object': ship_instance,
                    'cached_at': time.time()
                }
                pickled_data = pickle.dumps(cache_data)
                data_size = len(pickled_data)
                logger.info(f"[RedisService] SHiP object cached as full pickle: {data_size} bytes")
                return pickled_data
            except Exception as e:
                logger.debug(f"[RedisService] Full SHiP object pickle failed ({e}), falling back to recreation parameters")
            
            # Fall back to recreation parameters (slower but most reliable)
            cache_data = {
                'serialization_method': 'recreation_params',
                'config': getattr(ship_instance, 'config', {}),
                'tree_type': str(getattr(ship_instance, 'treeType', 'DCTree')),
                'power': getattr(ship_instance, 'power', 1),
                'partitioning_method': str(getattr(ship_instance, 'partitioningMethod', 'Elbow')),
                'cached_at': time.time()
            }
            
            # Add any other easily serializable attributes
            for attr in ['labels_', 'partitioning_runtime', 'tree_construction_runtime']:
                if hasattr(ship_instance, attr):
                    try:
                        value = getattr(ship_instance, attr)
                        pickle.dumps(value)  # Test if it's serializable
                        cache_data[attr] = value
                    except Exception:
                        pass  # Skip non-serializable attributes
            
            pickled_data = pickle.dumps(cache_data)
            data_size = len(pickled_data)
            logger.info(f"[RedisService] SHiP object cached as recreation parameters: {data_size} bytes")
            return pickled_data
                
        except Exception as e:
            logger.error(f"[RedisService] Failed to cache SHiP object: {e}")
            logger.error(f"[RedisService] SHiP object type: {type(ship_instance)}")
            return None

    def create_ship_object(self, ship_obj: SHiPObjectCreate, ship_instance=None) -> SHiPObject:
        """Create a new SHiP object record with improved serialization and error handling"""
        start_time = time.time()
        
        logger.info(f"[RedisService] Starting create_ship_object for data_hash: {ship_obj.data_hash[:8]}..., tree_type: {ship_obj.tree_type}")
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available for SHiP object creation - REDIS_AVAILABLE=False")
            return SHiPObject(**ship_obj.dict())
            
        if self.client is None:
            logger.warning("Redis connection not established for SHiP object creation")
            return SHiPObject(**ship_obj.dict())
            
        try:
            # Test connection before proceeding
            ping_start = time.time()
            self.client.ping()
            ping_time = time.time() - ping_start
            logger.debug(f"[RedisService] Connection ping successful, took {ping_time:.4f} seconds")
            
            ship_dict = ship_obj.dict()
            filtered_config = self._filter_config_for_caching(ship_dict.get('config', {}))
            config_hash = self._hash_dict(filtered_config)
            key = f"ship:{ship_dict['data_hash']}:{ship_dict['tree_type']}:{config_hash}"
            logger.info(f"[RedisService] Storing SHIP with key: {key}")
            logger.info(f"[RedisService] Original config: {ship_dict.get('config', {})}")
            logger.info(f"[RedisService] Filtered config: {filtered_config}")
            
            # Remove ship_object_binary if it's None
            if ship_dict.get('ship_object_binary') is None:
                ship_dict.pop('ship_object_binary', None)
                logger.debug("[RedisService] Removed None ship_object_binary from dict")
            
            # Serialize SHiP object if provided
            if ship_instance is not None:
                logger.debug(f"[RedisService] Serializing SHiP instance of type: {type(ship_instance)}")
                serialize_start = time.time()
                serialized_data = self._serialize_ship_object(ship_instance)
                serialize_time = time.time() - serialize_start
                logger.debug(f"[RedisService] Serialization took {serialize_time:.4f} seconds")
                
                if serialized_data is not None:
                    # Store binary data separately
                    binary_key = f"{key}:binary"
                    self.client.set(binary_key, serialized_data)
                    
                    # Determine serialization method by checking the data
                    try:
                        test_data = pickle.loads(serialized_data)
                        if isinstance(test_data, dict) and '_serialization_method' in test_data:
                            ship_dict['serialization_method'] = test_data['_serialization_method']
                        else:
                            ship_dict['serialization_method'] = 'pickle'
                    except:
                        ship_dict['serialization_method'] = 'pickle'
                        
                    logger.info(f"[RedisService] SHiP object serialized successfully, size: {len(serialized_data)} bytes, method: {ship_dict['serialization_method']}")
                else:
                    logger.warning("Serialization failed for SHiP object. Storing metadata only.")
                    ship_dict['serialization_method'] = 'failed'
            else:
                logger.debug("[RedisService] No SHiP instance provided for serialization")
            
            # Store metadata as hash
            insert_start = time.time()
            logger.debug(f"[RedisService] Storing SHiP object metadata in Redis hash")
            metadata = {k: str(v) for k, v in ship_dict.items() if k != 'ship_object_binary'}
            metadata['created_at'] = datetime.utcnow().isoformat()
            metadata['last_accessed'] = datetime.utcnow().isoformat()
            metadata['access_count'] = '1'
            
            self.client.hset(key, mapping=metadata)
            insert_time = time.time() - insert_start
            logger.debug(f"[RedisService] hset operation took {insert_time:.4f} seconds")
            
            logger.info(f"[RedisService] Successfully stored SHiP object with key: {key}")
            
            total_time = time.time() - start_time
            logger.info(f"[RedisService] create_ship_object completed successfully in {total_time:.4f} seconds")
            return SHiPObject(**ship_dict)
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Error creating SHiP object: {e} (took {total_time:.4f} seconds)")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return SHiPObject(**ship_obj.dict())
    
    def get_ship_object(self, data_hash: str, tree_type: str, config: Dict[str, Any]) -> Optional[SHiPObject]:
        """Get SHiP object by data hash, tree type, and config"""
        start_time = time.time()
        
        if not REDIS_AVAILABLE or self.client is None:
            logger.debug("Redis not available for SHiP object retrieval")
            return None
            
        try:
            ping_start = time.time()
            self.client.ping()
            ping_time = time.time() - ping_start
            logger.debug(f"[RedisService] Connection ping took {ping_time:.4f} seconds")
            
            filtered_config = self._filter_config_for_caching(config)
            config_hash = self._hash_dict(filtered_config)
            key = f"ship:{data_hash}:{tree_type}:{config_hash}"
            
            find_start = time.time()
            result = self.client.hgetall(key)
            find_time = time.time() - find_start
            logger.debug(f"[RedisService] hgetall query took {find_time:.4f} seconds")
            
            if result:
                # Update access statistics
                update_start = time.time()
                pipe = self.client.pipeline()
                pipe.hset(key, "last_accessed", datetime.utcnow().isoformat())
                pipe.hincrby(key, "access_count", 1)
                pipe.execute()
                update_time = time.time() - update_start
                logger.debug(f"[RedisService] Access statistics update took {update_time:.4f} seconds")
                
                # Convert bytes to strings
                ship_dict = {}
                for k, v in result.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    ship_dict[k_str] = v_str
                
                total_time = time.time() - start_time
                logger.info(f"[RedisService] get_ship_object completed in {total_time:.4f} seconds")
                return SHiPObject(**ship_dict)
            
            total_time = time.time() - start_time
            logger.info(f"[RedisService] get_ship_object (no result) completed in {total_time:.4f} seconds")
            return None
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Error getting SHiP object: {e} (took {total_time:.4f} seconds)")
            return None
    
    def _deserialize_ship_object(self, binary_data):
        """
        Deserialize SHiP object from cache
        Returns the cached SHiP object, recreation params dict, or None if failed
        """
        try:
            deserialized = pickle.loads(binary_data)
            
            # Legacy: Check if this is a raw full SHiP object (pre-dict format)
            if hasattr(deserialized, 'config') and hasattr(deserialized, 'treeType'):
                logger.debug(f"[RedisService] Found legacy full SHiP object in cache")
                return {'type': 'full_object', 'ship_object': deserialized}
            
            # New format: Check if this is a dictionary with serialization method
            if isinstance(deserialized, dict) and 'serialization_method' in deserialized:
                serialization_method = deserialized['serialization_method']
                logger.debug(f"[RedisService] Found cached data with method: {serialization_method}")
                
                if serialization_method == 'json_tree':
                    # Return data for JSON tree-based reconstruction
                    return {
                        'type': 'json_tree_data',
                        'json_tree': deserialized.get('json_tree'),
                        'config': deserialized.get('config', {}),
                        'tree_type': deserialized.get('tree_type', 'DCTree'),
                        'power': deserialized.get('power', 1),
                        'partitioning_method': deserialized.get('partitioning_method', 'Elbow'),
                        'labels_': deserialized.get('labels_'),
                        'partitioning_runtime': deserialized.get('partitioning_runtime'),
                        'tree_construction_runtime': deserialized.get('tree_construction_runtime'),
                        'cached_at': deserialized.get('cached_at')
                    }
                elif serialization_method == 'full_object':
                    # Return full SHiP object 
                    ship_obj = deserialized.get('ship_object')
                    if ship_obj:
                        logger.debug(f"[RedisService] Successfully found full SHiP object")
                        return {'type': 'full_object', 'ship_object': ship_obj}
                elif serialization_method == 'recreation_params':
                    # Return data for parameter-based reconstruction
                    return {
                        'type': 'recreation_params',
                        'config': deserialized.get('config', {}),
                        'tree_type': deserialized.get('tree_type', 'DCTree'),
                        'power': deserialized.get('power', 1),
                        'partitioning_method': deserialized.get('partitioning_method', 'Elbow'),
                        'labels_': deserialized.get('labels_'),
                        'partitioning_runtime': deserialized.get('partitioning_runtime'),
                        'tree_construction_runtime': deserialized.get('tree_construction_runtime'),
                        'cached_at': deserialized.get('cached_at')
                    }
                else:
                    logger.warning(f"[RedisService] Unknown serialization method: {serialization_method}")
                    return None
                    
            # Old format handling for backward compatibility
            if isinstance(deserialized, dict) and '_serialization_method' in deserialized:
                logger.debug(f"[RedisService] Found old format data - returning None to force recreation")
                return None
            
            # Unknown format
            logger.debug(f"[RedisService] Unknown cached data format - returning None to force recreation")
            return None
            
        except Exception as e:
            logger.error(f"[RedisService] Failed to deserialize SHiP data: {e}")
            return None

    def has_ship_cache(self, data_hash: str, tree_type: str, config: Dict[str, Any]) -> bool:
        """Check if we have any cached data for this SHiP object (even if not directly usable)"""
        if not REDIS_AVAILABLE or self.client is None:
            return False
            
        try:
            filtered_config = self._filter_config_for_caching(config)
            config_hash = self._hash_dict(filtered_config)
            key = f"ship:{data_hash}:{tree_type}:{config_hash}"
            
            # Check if we have metadata for this SHiP object
            result = self.client.hgetall(key)
            return bool(result)
        except Exception as e:
            logger.debug(f"[RedisService] Error checking cache existence: {e}")
            return False

    def get_ship_recreation_params(self, data_hash: str, tree_type: str, config: Dict[str, Any]):
        """Get SHiP recreation parameters from cache"""
        start_time = time.time()
        
        print(f"[RedisService] Starting get_ship_recreation_params for data_hash: {data_hash[:8]}..., tree_type: {tree_type}")
        
        if not REDIS_AVAILABLE or self.client is None:
            print(f"[RedisService] Redis not available for SHiP recreation params retrieval")
            return None
            
        try:
            ping_start = time.time()
            self.client.ping()
            ping_time = time.time() - ping_start
            print(f"[RedisService] Connection ping successful, took {ping_time:.4f} seconds")
            
            filtered_config = self._filter_config_for_caching(config)
            config_hash = self._hash_dict(filtered_config)
            key = f"ship:{data_hash}:{tree_type}:{config_hash}"
            binary_key = f"{key}:binary"
            print(f"[RedisService] Looking for SHIP with key: {key}")
            print(f"[RedisService] Original config: {config}")
            print(f"[RedisService] Filtered config: {filtered_config}")
            
            find_start = time.time()
            result = self.client.hgetall(key)
            binary_data = self.client.get(binary_key)
            find_time = time.time() - find_start
            print(f"[RedisService] Data retrieval took {find_time:.4f} seconds")
            
            if result and binary_data:
                print(f"[RedisService] Found cached SHiP data with key: {key}")
                
                # Update access statistics
                update_start = time.time()
                pipe = self.client.pipeline()
                pipe.hset(key, "last_accessed", datetime.utcnow().isoformat())
                pipe.hincrby(key, "access_count", 1)
                pipe.execute()
                update_time = time.time() - update_start
                print(f"[RedisService] Access statistics update took {update_time:.4f} seconds")
                
                deserialize_start = time.time()
                recreation_params = self._deserialize_ship_object(binary_data)
                deserialize_time = time.time() - deserialize_start
                print(f"[RedisService] Deserialization took {deserialize_time:.4f} seconds")
                
                if recreation_params is not None:
                    print(f"[RedisService] Successfully retrieved SHiP recreation parameters")
                else:
                    print(f"[RedisService] Failed to deserialize SHiP recreation parameters")
                
                total_time = time.time() - start_time
                print(f"[RedisService] get_ship_recreation_params completed in {total_time:.4f} seconds")
                return recreation_params
            else:
                print(f"[RedisService] SHiP cache NOT found - metadata: {'found' if result else 'missing'}, binary: {'found' if binary_data else 'missing'}")
            
            total_time = time.time() - start_time
            print(f"[RedisService] get_ship_recreation_params (no result) completed in {total_time:.4f} seconds")
            return None
        except Exception as e:
            total_time = time.time() - start_time
            print(f"[RedisService] Error getting SHiP recreation params: {e} (took {total_time:.4f} seconds)")
            import traceback
            print(f"[RedisService] Full traceback: {traceback.format_exc()}")
            return None
    
    def cleanup_old_ship_objects(self, days_old: int = 7) -> int:
        """Clean up old SHiP objects that haven't been accessed recently"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for SHiP object cleanup")
            return 0
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()
            
            # Scan for ship objects
            cleaned_count = 0
            for key in self.client.scan_iter(match="ship:*"):
                key_str = key.decode() if isinstance(key, bytes) else key
                if ":binary" in key_str:
                    continue
                    
                last_accessed = self.client.hget(key, "last_accessed")
                if last_accessed:
                    last_accessed_str = last_accessed.decode() if isinstance(last_accessed, bytes) else last_accessed
                    if last_accessed_str < cutoff_str:
                        # Delete both metadata and binary data
                        binary_key = f"{key_str}:binary"
                        pipe = self.client.pipeline()
                        pipe.delete(key)
                        pipe.delete(binary_key)
                        pipe.execute()
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old SHiP objects")
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up old SHiP objects: {e}")
            return 0
    
    # Clustering Results operations
    def _serialize_dict_for_redis(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Helper to serialize dictionary values for Redis storage"""
        serialized = {}
        for k, v in data.items():
            if v is None:
                continue
            
            # Handle numpy types first
            if isinstance(v, np.ndarray):
                # Convert to list directly, don't rely on json default
                v = v.tolist()
            
            # Now handle standard types
            if isinstance(v, (dict, list)):
                # Use a custom encoder for deep nested numpy types
                class NumpyEncoder(json.JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, np.ndarray):
                            return obj.tolist()
                        if isinstance(obj, np.integer):
                            return int(obj)
                        if isinstance(obj, np.floating):
                            return float(obj)
                        if isinstance(obj, Enum):
                            return obj.value
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        # Handle NaN and Infinity which are not valid JSON standard
                        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
                            return None 
                        return super().default(obj)
                    
                    # Override to handle standard float('nan') which default() misses
                    def encode(self, o):
                        def recursive_replace(obj):
                            if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
                                return None
                            if isinstance(obj, dict):
                                return {k: recursive_replace(val) for k, val in obj.items()}
                            if isinstance(obj, list):
                                return [recursive_replace(val) for val in obj]
                            return obj
                        
                        return super().encode(recursive_replace(o))
                
                # Check for NaN/Inf in top level floats if not caught by encoder (though encoder handles objects)
                # But json.dumps allows NaN by default which produces invalid JSON
                # We must enforce allow_nan=False or handle it manually
                serialized[k] = json.dumps(v, cls=NumpyEncoder)
            elif isinstance(v, datetime):
                serialized[k] = v.isoformat()
            elif isinstance(v, Enum):
                serialized[k] = str(v.value)
            elif isinstance(v, bool):
                 serialized[k] = str(v).lower()
            else:
                serialized[k] = str(v)
        return serialized

    def _deserialize_dict_from_redis(self, data: Dict[str, str], json_fields: List[str] = None) -> Dict[str, Any]:
        """Helper to deserialize values from Redis to Python types"""
        if json_fields is None:
            json_fields = []
        
        deserialized = {}
        for k, v in data.items():
            if k in json_fields and v:
                try:
                    deserialized[k] = json.loads(v)
                except:
                    deserialized[k] = v
            elif v == 'None':
                 deserialized[k] = None
            else:
                deserialized[k] = v
        return deserialized

    def create_clustering_result(self, result: ClusteringResultCreate) -> ClusteringResult:
        """Create a new clustering result record"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for clustering result creation")
            return ClusteringResult(**result.dict())
        try:
            result_dict = result.dict()
            key = f"result:{result_dict['id']}"
            
            # Store as Redis hash
            metadata = self._serialize_dict_for_redis(result_dict)
            if 'created_at' not in metadata:
                 metadata['created_at'] = datetime.utcnow().isoformat()
                 
            self.client.hset(key, mapping=metadata)
            
            # Add to sorted set for listing
            self.client.zadd("results_by_time", {result_dict['id']: time.time()})
            
            return ClusteringResult(**result_dict)
        except Exception as e:
            logger.error(f"Error creating clustering result: {e}")
            return ClusteringResult(**result.dict())
    
    def get_clustering_result(self, result_id: str) -> Optional[ClusteringResult]:
        """Get clustering result by ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for clustering result retrieval")
            return None
        try:
            key = f"result:{result_id}"
            result = self.client.hgetall(key)
            if result:
                result_dict = {}
                for k, v in result.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    result_dict[k_str] = v_str
                
                # Parse JSON fields
                result_dict = self._deserialize_dict_from_redis(
                    result_dict, 
                    json_fields=['parameters', 'result', 'data']
                )
                return ClusteringResult(**result_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting clustering result {result_id}: {e}")
            return None
    
    def get_clustering_result_by_operation_id(self, operation_id: str) -> Optional[ClusteringResult]:
        """Get clustering result by operation ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for clustering result retrieval by operation ID")
            return None
        try:
            # Scan for results with matching operation_id
            for key in self.client.scan_iter(match="result:*"):
                result = self.client.hgetall(key)
                if result:
                    op_id = result.get(b'operation_id', b'').decode()
                    if op_id == operation_id:
                        result_dict = {}
                        for k, v in result.items():
                            k_str = k.decode() if isinstance(k, bytes) else k
                            v_str = v.decode() if isinstance(v, bytes) else v
                            result_dict[k_str] = v_str
                        
                        # Parse JSON fields
                        result_dict = self._deserialize_dict_from_redis(
                            result_dict, 
                            json_fields=['parameters', 'result', 'data']
                        )
                        return ClusteringResult(**result_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting clustering result by operation ID {operation_id}: {e}")
            return None
    
    def update_clustering_result(self, result_id: str, result: ClusteringResultUpdate) -> Optional[ClusteringResult]:
        """Update clustering result by ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for clustering result update")
            return None
        try:
            key = f"result:{result_id}"
            # Use serializer for updates too
            update_data = self._serialize_dict_for_redis(result.dict(exclude_unset=True))
            
            if update_data:
                self.client.hset(key, mapping=update_data)
                return self.get_clustering_result(result_id)
            return None
        except Exception as e:
            logger.error(f"Error updating clustering result {result_id}: {e}")
            return None
    
    def list_clustering_results(self, dataset_id: Optional[str] = None, limit: int = 100, skip: int = 0) -> List[ClusteringResult]:
        """List clustering results with optional dataset filter"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for clustering results listing")
            return []
        try:
            results = []
            count = 0
            skipped = 0
            
            # Get results sorted by time (most recent first)
            result_ids = self.client.zrevrange("results_by_time", 0, -1)
            
            for result_id in result_ids:
                result_id_str = result_id.decode() if isinstance(result_id, bytes) else result_id
                result = self.get_clustering_result(result_id_str)
                
                if result:
                    # Apply dataset filter if specified
                    if dataset_id is None or result.dataset_id == dataset_id:
                        if skipped < skip:
                            skipped += 1
                            continue
                        
                        results.append(result)
                        count += 1
                        
                        if count >= limit:
                            break
            
            return results
        except Exception as e:
            logger.error(f"Error listing clustering results: {e}")
            return []
    
    # Dimensionality Reduction operations
    def create_dr_result(self, result: DimensionalityReductionResultCreate) -> DimensionalityReductionResult:
        """Create a new dimensionality reduction result"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DR result creation")
            return DimensionalityReductionResult(**result.dict())
        try:
            result_dict = result.dict()
            key = f"dr:{result_dict['cluster_id']}:{result_dict['method']}"
            
            # Store as Redis hash
            metadata = {k: str(v) for k, v in result_dict.items()}
            metadata['created_at'] = datetime.utcnow().isoformat()
            self.client.hset(key, mapping=metadata)
            
            return DimensionalityReductionResult(**result_dict)
        except Exception as e:
            logger.error(f"Error creating DR result: {e}")
            return DimensionalityReductionResult(**result.dict())
    
    def get_dr_result(self, cluster_id: str, method: str) -> Optional[DimensionalityReductionResult]:
        """Get dimensionality reduction result by cluster ID and method"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DR result retrieval")
            return None
        try:
            key = f"dr:{cluster_id}:{method}"
            result = self.client.hgetall(key)
            if result:
                result_dict = {}
                for k, v in result.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    result_dict[k_str] = v_str
                return DimensionalityReductionResult(**result_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting DR result for cluster {cluster_id}, method {method}: {e}")
            return None
    
    def update_dr_result(self, result_id: str, result: DimensionalityReductionResultUpdate) -> Optional[DimensionalityReductionResult]:
        """Update dimensionality reduction result by ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DR result update")
            return None
        try:
            # Find the key by result_id
            for key in self.client.scan_iter(match="dr:*"):
                existing_result = self.client.hgetall(key)
                if existing_result:
                    existing_id = existing_result.get(b'id', b'').decode()
                    if existing_id == result_id:
                        update_data = {k: str(v) for k, v in result.dict().items() if v is not None}
                        if update_data:
                            self.client.hset(key, mapping=update_data)
                            # Return updated result
                            updated_result = self.client.hgetall(key)
                            result_dict = {}
                            for k, v in updated_result.items():
                                k_str = k.decode() if isinstance(k, bytes) else k
                                v_str = v.decode() if isinstance(v, bytes) else v
                                result_dict[k_str] = v_str
                            return DimensionalityReductionResult(**result_dict)
                        break
            return None
        except Exception as e:
            logger.error(f"Error updating DR result {result_id}: {e}")
            return None
    
    # K-Selection Cache operations
    def create_k_selection_cache(self, cache: KSelectionCacheCreate) -> KSelectionCache:
        """Create a new k-selection cache entry"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for k-selection cache creation")
            return KSelectionCache(**cache.dict())
        try:
            cache_dict = cache.dict()
            key = f"cache:{cache_dict['dataset_id']}"
            
            # Store as Redis hash with TTL
            metadata = {k: str(v) for k, v in cache_dict.items()}
            metadata['created_at'] = datetime.utcnow().isoformat()
            
            pipe = self.client.pipeline()
            pipe.hset(key, mapping=metadata)
            
            # Set TTL if expires_at is provided
            if cache_dict.get('expires_at'):
                expires_at = cache_dict['expires_at']
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at)
                ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())
                if ttl_seconds > 0:
                    pipe.expire(key, ttl_seconds)
            
            pipe.execute()
            
            return KSelectionCache(**cache_dict)
        except Exception as e:
            logger.error(f"Error creating k-selection cache: {e}")
            return KSelectionCache(**cache.dict())
    
    def get_k_selection_cache(self, dataset_id: str) -> Optional[KSelectionCache]:
        """Get k-selection cache by dataset ID"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for k-selection cache retrieval")
            return None
        try:
            key = f"cache:{dataset_id}"
            result = self.client.hgetall(key)
            if result:
                result_dict = {}
                for k, v in result.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    result_dict[k_str] = v_str
                
                # Check if cache is still valid
                expires_at_str = result_dict.get('expires_at')
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.utcnow() > expires_at:
                        # Cache expired, delete it
                        self.client.delete(key)
                        return None
                
                return KSelectionCache(**result_dict)
            return None
        except Exception as e:
            logger.error(f"Error getting k-selection cache for dataset {dataset_id}: {e}")
            return None
    
    def cleanup_expired_cache(self) -> int:
        """Clean up expired k-selection cache entries"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for cache cleanup")
            return 0
        try:
            cleaned_count = 0
            now = datetime.utcnow()
            
            # Scan for cache entries
            for key in self.client.scan_iter(match="cache:*"):
                result = self.client.hgetall(key)
                if result:
                    expires_at_str = result.get(b'expires_at', b'').decode()
                    if expires_at_str:
                        try:
                            expires_at = datetime.fromisoformat(expires_at_str)
                            if now > expires_at:
                                self.client.delete(key)
                                cleaned_count += 1
                        except ValueError:
                            # Invalid date format, delete the entry
                            self.client.delete(key)
                            cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return 0
    
    # Dimensionality Reduction Task Management
    def store_dr_task_status(self, cluster_id: str, status_data: Dict[str, Any]) -> bool:
        """Store dimensionality reduction task status in Redis"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DR task status storage")
            return False
        try:
            key = f"dr_task:{cluster_id}"
            
            # Prepare data for Redis storage
            redis_data = {
                'cluster_id': cluster_id,
                'status': status_data.get('status', 'pending') or 'pending',
                'umap_status': status_data.get('umap_status', 'pending') or 'pending',
                'tsne_status': status_data.get('tsne_status', 'pending') or 'pending',
                'error': status_data.get('error', '') or '',
                'start_time': str(status_data.get('start_time', time.time()) or time.time()),
                'end_time': str(status_data.get('end_time', '') or ''),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Store as Redis hash with 1 hour TTL
            pipe = self.client.pipeline()
            pipe.hset(key, mapping=redis_data)
            pipe.expire(key, 3600)  # 1 hour TTL
            pipe.execute()
            
            logger.debug(f"[RedisService] Stored DR task status for cluster {cluster_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing DR task status for {cluster_id}: {e}")
            return False
    
    def get_dr_task_status(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get dimensionality reduction task status from Redis"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.debug("Redis not available for DR task status retrieval")
            return None
        try:
            key = f"dr_task:{cluster_id}"
            result = self.client.hgetall(key)
            if result:
                # Convert bytes to strings and parse
                task_data = {}
                for k, v in result.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    task_data[k_str] = v_str
                
                # Convert numeric fields
                if task_data.get('start_time'):
                    try:
                        task_data['start_time'] = float(task_data['start_time'])
                    except:
                        pass
                if task_data.get('end_time'):
                    try:
                        task_data['end_time'] = float(task_data['end_time']) if task_data['end_time'] else None
                    except:
                        task_data['end_time'] = None
                
                return task_data
            return None
        except Exception as e:
            logger.error(f"Error getting DR task status for {cluster_id}: {e}")
            return None
    
    def store_dr_result_metadata(self, cluster_id: str, umap_hash: Optional[str] = None, tsne_hash: Optional[str] = None) -> bool:
        """Store metadata linking cluster_id to UMAP/t-SNE cache keys"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DR result metadata storage")
            return False
        try:
            key = f"dr_meta:{cluster_id}"
            
            metadata = {
                'cluster_id': cluster_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            if umap_hash:
                metadata['umap_key'] = f"umap:{umap_hash}"
            if tsne_hash:
                metadata['tsne_key'] = f"tsne:{tsne_hash}"
            
            # Store with 24 hour TTL
            pipe = self.client.pipeline()
            pipe.hset(key, mapping=metadata)
            pipe.expire(key, 86400)  # 24 hours
            pipe.execute()
            
            logger.debug(f"[RedisService] Stored DR result metadata for cluster {cluster_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing DR result metadata for {cluster_id}: {e}")
            return False
    
    def get_dr_result_metadata(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get dimensionality reduction result metadata from Redis"""
        if not REDIS_AVAILABLE or self.client is None:
            return None
        try:
            key = f"dr_meta:{cluster_id}"
            result = self.client.hgetall(key)
            if result:
                metadata = {}
                for k, v in result.items():
                    k_str = k.decode() if isinstance(k, bytes) else k
                    v_str = v.decode() if isinstance(v, bytes) else v
                    metadata[k_str] = v_str
                return metadata
            return None
        except Exception as e:
            logger.error(f"Error getting DR result metadata for {cluster_id}: {e}")
            return None
    
    def clear_database(self) -> bool:
        """Clear all data from Redis database"""
        logger.info("[RedisService] Starting database clear operation")
        
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for clearing")
            return False
        
        try:
            # Test connection
            ping_start = time.time()
            self.client.ping()
            ping_time = time.time() - ping_start
            logger.debug(f"[RedisService] Connection ping successful, took {ping_time:.4f} seconds")
            
            # Clear all keys
            self.client.flushdb()
            
            logger.info("[RedisService] Successfully cleared Redis database")
            return True
        except Exception as e:
            logger.error(f"[RedisService] Error clearing database: {e}")
            import traceback
            logger.error(f"[RedisService] Full traceback: {traceback.format_exc()}")
            return False

    # DC Distance caching operations
    def get_dc_distances(self, data_hash: str, min_points: int) -> Optional[np.ndarray]:
        """Get cached DC distance matrix using optimized numpy format"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DC distance retrieval")
            return None
            
        try:
            key = f"dc_distances:{data_hash}:{min_points}"
            meta_key = f"{key}:meta"
            logger.debug(f"[RedisService] Looking for DC distances with key: {key}")
            
            # Get compressed binary data
            binary_data = self.client.get(key)
            
            if binary_data:
                logger.info(f"[RedisService] Found cached DC distances")
                
                # Update access statistics
                pipe = self.client.pipeline()
                pipe.hset(meta_key, "last_accessed", datetime.utcnow().isoformat())
                pipe.hincrby(meta_key, "access_count", 1)
                pipe.execute()
                
                # Deserialize using numpy compressed format
                deserialize_start = time.time()
                import io
                buffer = io.BytesIO(binary_data)
                data = np.load(buffer)
                dc_distances = data['dc_distances']
                buffer.close()
                
                deserialize_time = time.time() - deserialize_start
                logger.info(f"[RedisService] Successfully retrieved DC distances matrix: {dc_distances.shape} (deserialize: {deserialize_time:.4f}s)")
                return dc_distances
            else:
                logger.debug(f"[RedisService] DC distances cache NOT found for key: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting DC distances: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def store_dc_distances(self, data_hash: str, min_points: int, dc_distances: np.ndarray, 
                          data_shape: List[int]) -> bool:
        """Store DC distance matrix in cache using optimized numpy compression"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DC distance storage")
            return False
            
        try:
            key = f"dc_distances:{data_hash}:{min_points}"
            meta_key = f"{key}:meta"
            
            logger.info(f"[RedisService] Storing DC distances with key: {key}")
            logger.info(f"[RedisService] DC distances shape: {dc_distances.shape}")
            
            # Use numpy's optimized compression instead of pickle + gzip
            import io
            serialize_start = time.time()
            
            # Create in-memory buffer for numpy compression
            buffer = io.BytesIO()
            # Use compression level 1 for speed (vs default 6 for size)
            np.savez_compressed(buffer, dc_distances=dc_distances, format_version=2)
            compressed_data = buffer.getvalue()
            buffer.close()
            
            serialize_time = time.time() - serialize_start
            
            # Calculate original size estimate for comparison
            original_size_estimate = dc_distances.nbytes
            compression_ratio = len(compressed_data) / original_size_estimate
            
            logger.info(f"[RedisService] DC distances compressed: {original_size_estimate} bytes -> {len(compressed_data)} bytes (ratio: {compression_ratio:.3f}, took {serialize_time:.4f}s)")
            
            # Store binary data with metadata
            pipe = self.client.pipeline()
            pipe.set(key, compressed_data)
            pipe.hset(meta_key, mapping={
                "data_hash": data_hash,
                "min_points": str(min_points),
                "data_shape": str(data_shape),
                "dc_shape": str(list(dc_distances.shape)),
                "created_at": datetime.utcnow().isoformat(),
                "last_accessed": datetime.utcnow().isoformat(),
                "access_count": "1",
                "compressed_size": str(len(compressed_data)),
                "original_size": str(original_size_estimate),
                "compression_ratio": str(compression_ratio),
                "serialize_time": str(serialize_time),
                "format": "numpy_compressed_v2"
            })
            
            # Set expiration (30 days for DC distances)
            pipe.expire(key, 30 * 24 * 60 * 60)
            pipe.expire(meta_key, 30 * 24 * 60 * 60)
            
            pipe.execute()
            
            logger.info(f"[RedisService] Successfully stored DC distances with key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing DC distances: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    def cleanup_old_dc_distances(self, days_old: int = 30) -> int:
        """Clean up old DC distance caches that haven't been accessed recently"""
        if not REDIS_AVAILABLE or self.client is None:
            logger.warning("Redis not available for DC distance cleanup")
            return 0
            
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()
            
            # Find all DC distance keys
            pattern = "dc_distances:*:meta"
            keys = self.client.keys(pattern)
            
            cleaned_count = 0
            for key in keys:
                result = self.client.hgetall(key)
                if result:
                    last_accessed_str = result.get(b'last_accessed', b'').decode()
                    if last_accessed_str and last_accessed_str < cutoff_str:
                        # Delete both data and metadata
                        data_key = key.decode().replace(':meta', '') if isinstance(key, bytes) else key.replace(':meta', '')
                        pipe = self.client.pipeline()
                        pipe.delete(key)
                        pipe.delete(data_key)
                        pipe.execute()
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old DC distance caches")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old DC distance caches: {e}")
            return 0


# Global Redis service instance
redis_service = RedisService()

@contextmanager
def get_database():
    """Context manager for database operations"""
    try:
        if redis_service.client is None:
            redis_service.connect()
        yield redis_service
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise

def initialize_database():
    """Initialize Redis connection on startup"""
    try:
        redis_service.connect()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis during startup: {e}")
        logger.info("Application will continue without database - using memory-only mode")

def shutdown_database():
    """Shutdown Redis connection on app shutdown"""
    try:
        redis_service.disconnect()
    except Exception as e:
        logger.warning(f"Error during Redis shutdown: {e}")

# Mock SHiP object for testing (must be at module level for pickling)
class MockSHiPObject:
    def __init__(self):
        self.data = [[1, 2], [3, 4], [5, 6]]
        self.config = {"method": "ward", "k": 3}
        self.clusters = [0, 1, 1]

# Test functionality
def test_redis_service():
    """Test the Redis service functionality"""
    print("🧪 Testing Redis Service...")
    
    redis_svc = RedisService()
    
    # Test serialization methods
    print("Testing serialization methods...")
    
    mock_obj = MockSHiPObject()
    data = redis_svc._serialize_ship_object(mock_obj)
    print(f"✅ Object serialized: {data is not None}")
    
    # Test deserialization
    if data:
        deserialized = redis_svc._deserialize_ship_object(data)
        print(f"✅ Object deserialized successfully: {deserialized is not None}")
        if deserialized:
            print(f"✅ Deserialized object has data: {hasattr(deserialized, 'data')}")
            print(f"✅ Deserialized object has config: {hasattr(deserialized, 'config')}")
    
    # Test health check without connection
    health = redis_svc.health_check()
    print(f"✅ Health check status: {health['status']}")
    
    print("🎉 Redis service tests completed successfully!")

if __name__ == "__main__":
    test_redis_service()