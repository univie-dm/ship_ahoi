import hashlib
import json
import sys
import numpy as np
from typing import Optional, Dict, Any
import threading
import time
from collections import OrderedDict
from .redis_service import redis_service
from .models import SHiPObjectCreate, SHiPObjectUpdate
from .ship_exceptions import SHiPTreeGenerationError, SHIP_TREE_INVALID, SHIP_TREE_FILEPATH_INVALID

from contextlib import contextmanager


def _safe_json_loads(json_str: str) -> Any:
    """
    Safely parse JSON string, handling deep nesting that would cause RecursionError.
    Uses increased recursion limit with fallback to iterative parser.
    """
    if not json_str:
        return None
    
    original_limit = sys.getrecursionlimit()
    try:
        # Try standard JSON parsing with increased recursion limit
        sys.setrecursionlimit(max(10000, original_limit))
        return json.loads(json_str)
    except RecursionError:
        print(f"[SHiPCacheService] Standard JSON parsing hit recursion limit, using iterative parser")
        try:
            # Import from clustering_service only when needed to avoid circular import at load time
            from .clustering_service import ClusteringService
            return ClusteringService._iterative_json_parse(json_str)
        except Exception as e:
            print(f"[SHiPCacheService] Iterative JSON parsing failed: {e}")
            raise
    except json.JSONDecodeError as e:
        print(f"[SHiPCacheService] JSON decode error: {e}")
        raise
    finally:
        sys.setrecursionlimit(original_limit)


def _safe_json_dumps(obj: Any) -> str:
    """
    Safely serialize object to JSON, handling deep nesting that would cause RecursionError.
    Uses increased recursion limit with fallback to iterative serializer.
    """
    original_limit = sys.getrecursionlimit()
    try:
        # Try standard JSON serialization with increased recursion limit
        sys.setrecursionlimit(max(10000, original_limit))
        return json.dumps(obj)
    except (RecursionError, MemoryError) as e:
        print(f"[SHiPCacheService] Standard JSON serialization failed: {e}")
        try:
            # Import from clustering_service only when needed to avoid circular import at load time
            from .clustering_service import ClusteringService
            return ClusteringService._iterative_json_serialize(obj)
        except Exception as e2:
            print(f"[SHiPCacheService] Iterative JSON serialization failed: {e2}")
            raise
    finally:
        sys.setrecursionlimit(original_limit)

try:
    from SHiP_framework import SHiP
    from SHiP_framework.logger import LogLevel, setLogLevel
    from SHiP_framework.ultrametric_tree import UltrametricTreeType as UTreeType
    from SHiP_framework.partitioning import PartitioningMethod as PMethod
except ImportError:
    try:
        from SHiP import SHiP
        from SHiP.logger import LogLevel, setLogLevel
        from SHiP.ultrametric_tree import UltrametricTreeType as UTreeType
        from SHiP.partitioning import PartitioningMethod as PMethod
    except ImportError:
        SHiP = None
        print("Warning: SHiP framework not available.")
    try:
        from SHiP import SHiP
        from SHiP.logger import LogLevel, setLogLevel
        from SHiP.ultrametric_tree import UltrametricTreeType as UTreeType
        from SHiP.partitioning import PartitioningMethod as PMethod
    except ImportError:
        SHiP = None
        print("Warning: SHiP framework not available.")


class SHiPCacheService:
    """
    Centralized caching service for SHIP objects to optimize performance with large datasets.
    Uses Redis JSON tree caching for consistency and persistence.
    """
    
    _local_lock = threading.RLock()
    
    @classmethod
    @contextmanager
    def _get_lock(cls, timeout: int = 30):
        """
        Get a distributed lock using Redis, falling back to local lock if Redis is unavailable.
        """
        lock_acquired = False
        local_lock_acquired = False
        redis_lock = None
        
        try:
            if redis_service.client is not None:
                try:
                    # Use Redis lock for cross-process synchronization
                    redis_lock = redis_service.client.lock("ship_cache_global_lock", timeout=timeout)
                    # Note: redis-py arguments vary by version. 
                    # 'timeout' in lock() is the lock validity.
                    # 'blocking_timeout' in acquire() is how long to wait.
                    lock_acquired = redis_lock.acquire(blocking=True, blocking_timeout=timeout)
                except Exception as e:
                    print(f"[SHiPCacheService] Redis lock acquisition failed: {e}")
                    lock_acquired = False
            
            if not lock_acquired:
                # Fallback to local lock if Redis lock fails or Redis is unavailable
                # This at least protects threads within the same process
                cls._local_lock.acquire()
                local_lock_acquired = True
                
            yield
            
        finally:
            if lock_acquired and redis_lock:
                try:
                    redis_lock.release()
                except Exception:
                    pass
            elif local_lock_acquired:
                cls._local_lock.release()
    
    @classmethod
    def _create_data_hash(cls, data: np.ndarray) -> str:
        """
        Create a deterministic hash for the dataset that's efficient for large arrays.
        Uses sampling approach for very large datasets to balance uniqueness and performance.
        Ensures consistency across pickle/unpickle cycles.
        """
        start_time = time.time()
        try:
            # Ensure consistent dtype for hashing
            data_normalized = data.astype(np.float64)  # Normalize to float64 for consistency
            
            # For very large arrays, use strategic sampling
            if data_normalized.size > 100000:  # More than 100k elements
                # Sample from beginning, middle, end + shape info
                sample_size = min(1000, data_normalized.shape[0] // 10)
                indices = np.concatenate([
                    np.arange(min(sample_size // 3, data_normalized.shape[0])),  # Beginning
                    np.arange(data_normalized.shape[0] // 2 - sample_size // 6, 
                             min(data_normalized.shape[0] // 2 + sample_size // 6, data_normalized.shape[0])),  # Middle
                    np.arange(max(0, data_normalized.shape[0] - sample_size // 3), data_normalized.shape[0])  # End
                ])
                sample_data = data_normalized[indices].flatten()
            else:
                sample_data = data_normalized.flatten()
            
            # Create hash from sample + metadata (use normalized shape and dtype)
            hasher = hashlib.sha256()
            hasher.update(sample_data.tobytes())
            hasher.update(str(data_normalized.shape).encode())
            hasher.update(b'float64')  # Always use normalized dtype for consistency
            
            end_time = time.time()
            print(f"[SHiPCacheService] _create_data_hash took {end_time - start_time:.4f} seconds")
            return hasher.hexdigest()
        except Exception as e:
            print(f"Warning: Could not create data hash, using fallback: {e}")
            end_time = time.time()
            print(f"[SHiPCacheService] _create_data_hash (fallback) took {end_time - start_time:.4f} seconds")
            return f"fallback_{id(data)}_{data.shape}"
    
    @classmethod
    def _create_cache_key(cls, data_hash: str, tree_type: str, config: Dict[str, Any]) -> str:
        """Create a cache key from data hash, tree type, and configuration (excluding runtime parameters)."""
        # Runtime-only parameters that don't affect ultrametric tree construction
        # These are used only during fit_predict() calls, not during SHiP object creation
        runtime_only_params = {
            'k',                    # Manual K selection - used in fit_predict()
            'power',                # Power parameter - used in fit_predict()
            'partitioningMethod',   # Partition method - used in fit_predict()
            'partition_method',     # Alternative naming
            'clustering_method',    # Alternative naming
        }
        
        # Create a copy of config without runtime-only parameters for caching
        # Only tree construction parameters should affect the cache key
        config_for_cache = {k: v for k, v in config.items() if k not in runtime_only_params}
        config_str = "_".join(f"{k}:{v}" for k, v in sorted(config_for_cache.items()))
        return f"{data_hash}_{tree_type}_{config_str}"

    @classmethod
    def _store_ship_json_to_redis(cls, cache_key: str, ship) -> bool:
        """Store SHiP object as JSON tree in Redis."""
        try:
            if redis_service.client is None:
                redis_service.connect()
            
            if redis_service.client is None:
                print(f"[SHiPCacheService] Redis connection not available, skipping storage")
                return False
            
            # Get JSON tree from SHiP object
            print(f"[SHiPCacheService] Extracting JSON tree from SHiP object")
            
            try:
                tree_obj = ship.get_tree()
                print(f"[SHiPCacheService] Tree object type: {type(tree_obj)}")
                
                # Try to get JSON representation
                json_result = tree_obj.to_json(fast_index=True)
                print(f"[SHiPCacheService] JSON result type: {type(json_result)}")
                
                # Handle different possible return types
                if isinstance(json_result, str):
                    full_json_str = json_result
                elif hasattr(json_result, 'to_string'):
                    full_json_str = json_result.to_string()
                elif hasattr(json_result, '__str__'):
                    full_json_str = str(json_result)
                else:
                    # Fallback: try JSON serialization of the object
                    if hasattr(json_result, '__dict__'):
                        full_json_str = _safe_json_dumps(json_result.__dict__)
                    else:
                        raise ValueError(f"Cannot convert {type(json_result)} to JSON string")
                
                print(f"[SHiPCacheService] Full JSON string length: {len(full_json_str)} characters")
                
                # Extract only the root tree structure (LoadTree expects only the tree, not metadata)
                # Use safe JSON parsing to handle deep trees
                try:
                    full_json_data = _safe_json_loads(full_json_str)
                    root_tree_data = full_json_data['root']
                    json_tree_str = _safe_json_dumps(root_tree_data)
                    print(f"[SHiPCacheService] Extracted root tree JSON length: {len(json_tree_str)} characters")
                except (json.JSONDecodeError, KeyError, RecursionError) as parse_error:
                    print(f"[SHiPCacheService] Failed to parse JSON or extract root: {parse_error}")
                    print(f"[SHiPCacheService] Storing full JSON as fallback")
                    json_tree_str = full_json_str
                
                # Store root tree JSON string in Redis
                redis_key = f"ship_json:{cache_key}"
                redis_service.client.set(redis_key, json_tree_str)
                
            except Exception as json_error:
                print(f"[SHiPCacheService] Error during JSON extraction: {json_error}")
                print(f"[SHiPCacheService] Tree object attributes: {dir(tree_obj) if 'tree_obj' in locals() else 'N/A'}")
                raise json_error
            
            # Store metadata
            tree_type_value = getattr(ship, 'treeType', 'unknown')
            # Convert enum to string for Redis serialization
            if hasattr(tree_type_value, 'name'):
                tree_type_str = tree_type_value.name
            else:
                tree_type_str = str(tree_type_value)
            
            metadata = {
                'created_at': time.time(),
                'last_accessed': time.time(),
                'access_count': '1',
                'tree_type': tree_type_str,
                'data_shape': str(getattr(ship, 'data', np.array([])).shape) if hasattr(ship, 'data') else 'unknown'
            }
            metadata_key = f"ship_meta:{cache_key}"
            redis_service.client.hset(metadata_key, mapping=metadata)
            
            print(f"[SHiPCacheService] Successfully stored SHiP JSON tree in Redis with key: {redis_key}")
            return True
            
        except Exception as e:
            print(f"[SHiPCacheService] Failed to store SHiP JSON in Redis: {e}")
            return False
    
    @classmethod
    def _get_ship_json_from_redis(cls, cache_key: str) -> Optional[str]:
        """Retrieve SHiP JSON tree from Redis."""
        try:
            if redis_service.client is None:
                redis_service.connect()
            
            if redis_service.client is None:
                return None
            
            redis_key = f"ship_json:{cache_key}"
            json_tree = redis_service.client.get(redis_key)
            
            if json_tree:
                # Update access metadata
                metadata_key = f"ship_meta:{cache_key}"
                redis_service.client.hset(metadata_key, mapping={
                    'last_accessed': time.time(),
                    'access_count': str(int(redis_service.client.hget(metadata_key, 'access_count') or 0) + 1)
                })
                print(f"[SHiPCacheService] Retrieved SHiP JSON tree from Redis")
                return json_tree.decode() if isinstance(json_tree, bytes) else json_tree
            
            return None
            
        except Exception as e:
            print(f"[SHiPCacheService] Failed to retrieve SHiP JSON from Redis: {e}")
            return None
    
    @classmethod
    def get_ship(cls, data: np.ndarray, tree_type: str = "DCTree", 
                       config: Optional[Dict[str, Any]] = None) -> Optional["SHiP"]:
        """
        Get or create a cached SHIP object for the given data and parameters.
        Uses JSON tree caching for fast recreation.
        
        Args:
            data: Input data array
            tree_type: Tree type for SHIP clustering
            config: Configuration dictionary for SHIP
            
        Returns:
            SHIP object or None if SHIP is not available
        """
        start_time_total = time.time()
        if SHiP is None:
            print(f"[SHiPCacheService] SHiP framework not available. get_ship took {time.time() - start_time_total:.4f} seconds")
            return None

        if config is None:
            start_time_get_optimized_config = time.time()
            config = cls._get_optimized_config_for_dataset_size(len(data))
            end_time_get_optimized_config = time.time()
            print(f"[SHiPCacheService] _get_optimized_config_for_dataset_size in get_ship took {end_time_get_optimized_config - start_time_get_optimized_config:.4f} seconds")
        else:
            # Avoid mutating caller-provided configuration when we add optimizer flags
            config = dict(config)
        
        # Compute deterministic hash and cache key
        start_time_create_hash = time.time()
        data_hash = cls._create_data_hash(data)
        end_time_create_hash = time.time()
        print(f"[SHiPCacheService] _create_data_hash in get_ship took {end_time_create_hash - start_time_create_hash:.4f} seconds")
        cache_key = cls._create_cache_key(data_hash, tree_type, config)
        
        # Check if this data hash corresponds to a cached dataset
        try:
            from .toy_dataset_service import ToyDatasetService
            dataset_info = ToyDatasetService.get_dataset_by_data_hash(data_hash)
            if dataset_info:
                dataset_name, dataset_cache_key = dataset_info
                print(f"[SHiPCacheService] Data hash {data_hash[:8]}... matches cached dataset: {dataset_name} (key: {dataset_cache_key[:8]}...)")
        except Exception as e:
            print(f"[SHiPCacheService] Could not check dataset coordination: {e}")

        with cls._get_lock():
            # Try to get JSON tree from Redis cache
            try:
                start_time_cache_check = time.time()
                json_tree = cls._get_ship_json_from_redis(cache_key)
                end_time_cache_check = time.time()
                print(f"[SHiPCacheService] Redis JSON cache check took {end_time_cache_check - start_time_cache_check:.4f} seconds")
                
                # If we have cached JSON tree, try to recreate the SHiP object
                if json_tree is not None:
                    try:
                        print(f"[SHiPCacheService] Found cached JSON tree - attempting recreation")
                        start_time_recreation = time.time()
                        
                        import tempfile
                        import os
                        # Process the cached JSON to ensure it's in the correct format for LoadTree
                        # Use safe JSON parsing to handle deep trees
                        try:
                            # Try to parse as JSON to check if it's the full format or just root
                            parsed_json = _safe_json_loads(json_tree)
                            
                            # If it has a 'root' key, it's the full format - extract root
                            if isinstance(parsed_json, dict) and 'root' in parsed_json:
                                print(f"[SHiPCacheService] Detected full JSON format, extracting root tree")
                                tree_json_str = _safe_json_dumps(parsed_json['root'])
                            else:
                                # Assume it's already the root tree format
                                print(f"[SHiPCacheService] Using cached JSON as root tree (already processed format)")
                                tree_json_str = json_tree
                                
                        except (json.JSONDecodeError, TypeError, RecursionError):
                            # If parsing fails, assume it's already the correct format
                            print(f"[SHiPCacheService] Cached JSON not parseable, using as-is")
                            tree_json_str = json_tree
                        
                        # Create temporary file for JSON tree
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                            f.write(tree_json_str)
                            temp_json_path = f.name
                        
                        try:
                            # Set log level to reduce verbosity
                            setLogLevel(LogLevel.ERROR)
                            
                            # Create SHiP object with LoadTree and JSON file
                            load_config = {"json_tree_filepath": temp_json_path}
                            ship = SHiP(data=data, treeType="LoadTree", config=load_config)
                            
                            end_time_recreation = time.time()
                            print(f"[SHiPCacheService] SHiP object recreated from JSON tree in {end_time_recreation - start_time_recreation:.4f} seconds")
                            print(f"[SHiPCacheService] JSON cache hit! Total execution took {time.time() - start_time_total:.4f} seconds")
                            
                            # Log dataset coordination for successful cache hits
                            try:
                                from .toy_dataset_service import ToyDatasetService
                                dataset_info = ToyDatasetService.get_dataset_by_data_hash(data_hash)
                                if dataset_info:
                                    dataset_name, cache_key_info = dataset_info
                                    print(f"[SHiPCacheService] Cache hit linked to dataset: {dataset_name}")
                            except Exception as e:
                                print(f"[SHiPCacheService] Could not log dataset coordination: {e}")
                            
                            return ship
                            
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_json_path)
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"[SHiPCacheService] Failed to recreate SHiP from JSON tree: {e}")
                        print(f"[SHiPCacheService] Falling back to creating new SHiP object")
                        # Fall through to create new SHiP object
                
            except Exception as e:
                print(f"[SHiPCacheService] Redis JSON lookup failed: {e}")

            # Create new SHIP object (cache miss or recreation failed)
            start_time_ship_init = time.time()
            try:
                print(f"[SHiPCacheService] Creating new SHiP object")
                setLogLevel(LogLevel.ERROR)  # Reduce verbosity for large datasets
                tree_type_enum = getattr(UTreeType, tree_type, UTreeType.DCTree)
                config["optimize_tree"] = True  # Enable tree optimization

                ship = SHiP(data=data, treeType=tree_type_enum, config=config)
                end_time_ship_init = time.time()
                print(f"[SHiPCacheService] SHiP object initialization took {end_time_ship_init - start_time_ship_init:.4f} seconds")
                
                # Store JSON tree in Redis cache
                try:
                    cls._store_ship_json_to_redis(cache_key, ship)
                except Exception as e:
                    print(f"[SHiPCacheService] Failed to store SHiP JSON in Redis: {e}")
                
                print(f"[SHiPCacheService] Created and cached SHiP object for dataset shape {data.shape}")
                print(f"[SHiPCacheService] Total get_ship execution took {time.time() - start_time_total:.4f} seconds")
                return ship
                    
            except Exception as e:
                print(f"[SHiPCacheService] Failed to create SHIP object: {e}")
                print(f"[SHiPCacheService] Total get_ship execution (failed) took {time.time() - start_time_total:.4f} seconds")
                
                # Check for specific error patterns
                error_str = str(e)
                if "Tree is invalid" in error_str:
                    raise SHiPTreeGenerationError(
                        message="SHiP tree generation failed with the selected tree type",
                        error_code=SHIP_TREE_INVALID
                    )
                elif "json_tree_filepath" in error_str and ("Empty" in error_str or "Invalid" in error_str):
                    raise SHiPTreeGenerationError(
                        message="This tree type is not compatible with your dataset",
                        error_code=SHIP_TREE_FILEPATH_INVALID
                    )
                
                return None
    
    @classmethod
    def restore_from_json(cls, data: np.ndarray, tree_type: str, config: Dict[str, Any], json_tree: str) -> bool:
        """
        Explicitly populate the cache with a JSON tree, typically from history.
        This allows re-clustering to work immediately without re-computation.
        
        Args:
            data: Input data array
            tree_type: Tree type
            config: Configuration dictionary
            json_tree: The JSON tree string to cache
            
        Returns:
            bool: True if successful
        """
        if not json_tree:
            return False
            
        try:
            # Generate cache key
            data_hash = cls._create_data_hash(data)
            cache_key = cls._create_cache_key(data_hash, tree_type, config)
            
            with cls._get_lock():
                if redis_service.client is None:
                    redis_service.connect()
                
                if redis_service.client is None:
                    return False
                
                # Store JSON tree
                redis_key = f"ship_json:{cache_key}"
                redis_service.client.set(redis_key, json_tree)
                
                # Store metadata
                metadata = {
                    'created_at': time.time(),
                    'last_accessed': time.time(),
                    'access_count': '1',
                    'tree_type': tree_type,
                    'data_shape': str(data.shape),
                    'restored_from_history': 'true'
                }
                metadata_key = f"ship_meta:{cache_key}"
                redis_service.client.hset(metadata_key, mapping=metadata)
                
                print(f"[SHiPCacheService] Restored cache from history for key: {cache_key}")
                return True
                
        except Exception as e:
            print(f"[SHiPCacheService] Failed to restore cache from JSON: {e}")
            return False
    
    @classmethod
    def clear_cache(cls):
        """Clear all cached SHIP objects from Redis."""
        start_time = time.time()
        try:
            if redis_service.client is not None:
                # Clear JSON trees and metadata
                json_keys = list(redis_service.client.scan_iter(match="ship_json:*"))
                meta_keys = list(redis_service.client.scan_iter(match="ship_meta:*"))
                # Also clear old format keys for backward compatibility
                old_keys = list(redis_service.client.scan_iter(match="ship:*"))
                
                all_keys = json_keys + meta_keys + old_keys
                if all_keys:
                    redis_service.client.delete(*all_keys)
                    print(f"SHIP cache cleared: {len(all_keys)} entries removed from Redis (JSON: {len(json_keys)}, Meta: {len(meta_keys)}, Old: {len(old_keys)})")
                else:
                    print("SHIP cache cleared: no entries found in Redis")
            else:
                print("SHIP cache clear failed: Redis not available")
        except Exception as e:
            print(f"SHIP cache clear failed: {e}")
        end_time = time.time()
        print(f"[SHiPCacheService] clear_cache took {end_time - start_time:.4f} seconds")
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, Any]:
        """
        Get information about current cache state from Redis.
        """
        start_time = time.time()
        cache_info = {
            'num_cached_objects': 0,
            'cached_datasets': []
        }
        
        try:
            if redis_service.client is not None:
                # Get JSON and metadata keys from Redis
                json_keys = list(redis_service.client.scan_iter(match="ship_json:*"))
                meta_keys = list(redis_service.client.scan_iter(match="ship_meta:*"))
                
                cache_info['num_cached_objects'] = len(json_keys)
                
                # Get sample of cached datasets info
                for json_key in json_keys[:10]:  # Limit to first 10 for performance
                    try:
                        json_key_str = json_key.decode() if isinstance(json_key, bytes) else json_key
                        cache_key = json_key_str.replace('ship_json:', '')
                        meta_key = f"ship_meta:{cache_key}"
                        
                        # Get metadata
                        metadata = redis_service.client.hgetall(meta_key)
                        if metadata:
                            # Parse cache key to extract info (data_hash_tree_type_config)
                            key_parts = cache_key.split('_', 2)  # Split into 3 parts maximum
                            if len(key_parts) >= 2:
                                data_hash = key_parts[0]
                                tree_type = key_parts[1]
                                
                                cache_info['cached_datasets'].append({
                                    'key': cache_key[:32] + "..." if len(cache_key) > 32 else cache_key,
                                    'data_hash': data_hash[:8] + "...",
                                    'tree_type': tree_type,
                                    'last_accessed': metadata.get(b'last_accessed', b'unknown').decode(),
                                    'access_count': metadata.get(b'access_count', b'0').decode(),
                                    'data_shape': metadata.get(b'data_shape', b'unknown').decode()
                                })
                    except Exception as e:
                        print(f"[SHiPCacheService] Error reading cache entry: {e}")
        except Exception as e:
            print(f"[SHiPCacheService] Error getting Redis cache info: {e}")
        
        end_time = time.time()
        print(f"[SHiPCacheService] get_cache_info took {end_time - start_time:.4f} seconds")
        return cache_info
    
    @classmethod
    def remove_cache_entry(cls, data: np.ndarray, tree_type: str = "DCTree", 
                          config: Optional[Dict[str, Any]] = None):
        """
        Remove a specific cache entry from Redis.
        """
        start_time = time.time()
        if config is None:
            config = cls._get_optimized_config_for_dataset_size(len(data))
        
        data_hash = cls._create_data_hash(data)
        cache_key = cls._create_cache_key(data_hash, tree_type, config)
        
        try:
            if redis_service.client is not None:
                json_key = f"ship_json:{cache_key}"
                meta_key = f"ship_meta:{cache_key}"
                
                # Delete both JSON data and metadata
                pipe = redis_service.client.pipeline()
                pipe.delete(json_key)
                pipe.delete(meta_key)
                results = pipe.execute()
                
                if results[0] > 0 or results[1] > 0:
                    print(f"Removed cache entry for dataset (hash: {data_hash[:8]}...)")
                    end_time = time.time()
                    print(f"[SHiPCacheService] remove_cache_entry took {end_time - start_time:.4f} seconds")
                    return True
            
            end_time = time.time()
            print(f"[SHiPCacheService] remove_cache_entry (no entry found) took {end_time - start_time:.4f} seconds")
            return False
        except Exception as e:
            print(f"[SHiPCacheService] Error removing cache entry: {e}")
            end_time = time.time()
            print(f"[SHiPCacheService] remove_cache_entry (error) took {end_time - start_time:.4f} seconds")
            return False
    
    @classmethod
    def _get_optimized_config_for_dataset_size(cls, data_size: int) -> Dict[str, Any]:
        """
        Get optimized SHIP configuration based on dataset size.
        Dynamically adjusts parameters to handle large datasets efficiently.
        """
        if data_size <= 1000:
            # Small datasets - use minimal constraints
            return {
                "min_points": 2,
                "min_cluster_size": max(1, data_size // 50),
                "optimize_tree": True,
            }
        elif data_size <= 10000:
            # Medium datasets - balanced approach
            return {
                "min_points": max(3, data_size // 2000),
                "min_cluster_size": max(5, data_size // 100),
                "optimize_tree": True,
            }
        elif data_size <= 100000:
            # Large datasets - more conservative
            return {
                "min_points": max(5, data_size // 5000),
                "min_cluster_size": max(20, data_size // 200),
                "optimize_tree": True,
            }
        else:
            # Very large datasets - highly conservative
            return {
                "min_points": max(10, data_size // 10000),
                "min_cluster_size": max(50, data_size // 500),
                "optimize_tree": True,
            }
    
    @classmethod
    def get_combined_cache_info(cls) -> Dict[str, Any]:
        """
        Get comprehensive cache information including SHiP, UMAP, t-SNE, and toy dataset caches.
        """
        start_time = time.time()
        
        # Get SHiP cache info
        ship_info = cls.get_cache_info()
        
        # Get UMAP cache info
        try:
            from .umap_optimization_service import UMAPOptimizationService
            umap_info = UMAPOptimizationService.get_cache_info()
        except ImportError:
            umap_info = {
                'total_cache_size': 0,
                'estimated_memory_mb': 0,
                'redis_cached_datasets': [],
                'error': 'UMAP optimization service not available'
            }
        
        # Get t-SNE cache info
        try:
            from .tsne_optimization_service import TSNEOptimizationService
            tsne_info = TSNEOptimizationService.get_cache_info()
        except ImportError:
            tsne_info = {
                'total_cache_size': 0,
                'estimated_memory_mb': 0,
                'redis_cached_datasets': [],
                'error': 't-SNE optimization service not available'
            }
        
        # Get toy dataset cache info
        try:
            from .toy_dataset_service import ToyDatasetService
            toy_dataset_info = ToyDatasetService.get_cache_info()
        except ImportError:
            toy_dataset_info = {
                'cached_datasets': 0,
                'cache_keys': [],
                'error': 'Toy dataset service not available'
            }
        
        combined_info = {
            'ship_cache': ship_info,
            'umap_cache': umap_info,
            'tsne_cache': tsne_info,
            'toy_dataset_cache': toy_dataset_info,
            'total_cached_items': (
                ship_info['num_cached_objects'] + 
                umap_info.get('total_cache_size', 0) + 
                tsne_info.get('total_cache_size', 0) + 
                toy_dataset_info.get('cached_datasets', 0)
            ),
            'estimated_total_memory_mb': (
                umap_info.get('estimated_memory_mb', 0) + 
                tsne_info.get('estimated_memory_mb', 0)
            ),
            'cache_check_time': time.time() - start_time
        }
        
        return combined_info
    
    @classmethod
    def clear_all_caches(cls) -> Dict[str, int]:
        """
        Clear all caches including SHiP, UMAP, t-SNE, and toy datasets.
        Returns dict with counts of cleared entries.
        """
        start_time = time.time()
        
        # Clear SHiP cache
        ship_count = 0
        try:
            if redis_service.client is not None:
                json_keys = list(redis_service.client.scan_iter(match="ship_json:*"))
                meta_keys = list(redis_service.client.scan_iter(match="ship_meta:*"))
                old_keys = list(redis_service.client.scan_iter(match="ship:*"))
                ship_count = len(json_keys) + len(meta_keys) + len(old_keys)
        except Exception:
            pass
        cls.clear_cache()
        
        # Clear UMAP cache
        umap_count = 0
        try:
            from .umap_optimization_service import UMAPOptimizationService
            umap_count = UMAPOptimizationService.clear_cache()
        except ImportError:
            print("UMAP optimization service not available for cache clearing")
        
        # Clear t-SNE cache
        tsne_count = 0
        try:
            from .tsne_optimization_service import TSNEOptimizationService
            tsne_count = TSNEOptimizationService.clear_cache()
        except ImportError:
            print("t-SNE optimization service not available for cache clearing")
        
        # Clear toy dataset cache
        toy_dataset_count = 0
        try:
            from .toy_dataset_service import ToyDatasetService
            toy_dataset_info = ToyDatasetService.get_cache_info()
            toy_dataset_count = toy_dataset_info.get('cached_datasets', 0)
            ToyDatasetService.clear_cache()
        except ImportError:
            print("Toy dataset service not available for cache clearing")
        
        result = {
            'ship_entries_cleared': ship_count,
            'umap_entries_cleared': umap_count,
            'tsne_entries_cleared': tsne_count,
            'toy_dataset_entries_cleared': toy_dataset_count,
            'total_cleared': ship_count + umap_count + tsne_count + toy_dataset_count,
            'clear_time': time.time() - start_time
        }
        
        print(f"[SHiPCacheService] Cleared all caches: {result}")
        return result
    
    @classmethod
    def get_or_create_dc_distances(cls, data: np.ndarray, min_points: int = 5) -> Optional[np.ndarray]:
        """
        Get or create cached DC distance matrix for the given data and min_points.
        
        Args:
            data: Input data array
            min_points: Min points parameter for DC distance calculation
            
        Returns:
            DC distance matrix (numpy array) or None if failed
        """
        start_time = time.time()
        
        # Create data hash for cache key
        data_hash = cls._create_data_hash(data)
        print(f"[SHiPCacheService] DC distances cache lookup for data_hash: {data_hash[:8]}..., min_points: {min_points}")
        
        # Try to get from Redis cache first
        try:
            if redis_service.client is not None:
                # Check if DC distance methods are available
                if hasattr(redis_service, 'get_dc_distances') and hasattr(redis_service, 'store_dc_distances'):
                    cached_dc_distances = redis_service.get_dc_distances(data_hash, min_points)
                    if cached_dc_distances is not None:
                        cache_time = time.time() - start_time
                        print(f"[SHiPCacheService] DC distances cache HIT! Retrieved in {cache_time:.4f} seconds")
                        return cached_dc_distances
                    else:
                        print(f"[SHiPCacheService] DC distances cache MISS")
                else:
                    print(f"[SHiPCacheService] DC distance methods not available - server restart required for caching")
        except Exception as e:
            print(f"[SHiPCacheService] Error accessing DC distances cache: {e}")
        
        # Cache miss - compute DC distances
        try:
            print(f"[SHiPCacheService] Computing DC distances for {data.shape[0]} samples with min_points={min_points}")
            
            # Import DCTree from DISCO framework
            import sys
            disco_path = "/home/uni/ship.ahoi/DISCO-main/src"
            if disco_path not in sys.path:
                sys.path.insert(0, disco_path)
            
            from Evaluation.dcdistances.dctree import DCTree
            
            # Create DCTree and compute DC distances
            compute_start = time.time()
            dc_tree = DCTree(data, min_points=min_points, no_fastindex=False)
            dc_distances = dc_tree.dc_distances()
            compute_time = time.time() - compute_start
            print(f"[SHiPCacheService] DC distances computed in {compute_time:.4f} seconds, shape: {dc_distances.shape}")
            
            # Store in Redis cache
            try:
                if redis_service.client is not None and hasattr(redis_service, 'store_dc_distances'):
                    store_success = redis_service.store_dc_distances(
                        data_hash, min_points, dc_distances, list(data.shape)
                    )
                    if store_success:
                        print(f"[SHiPCacheService] DC distances cached successfully")
                    else:
                        print(f"[SHiPCacheService] Failed to cache DC distances")
                else:
                    print(f"[SHiPCacheService] Redis service or store_dc_distances method not available, skipping cache storage")
            except Exception as e:
                print(f"[SHiPCacheService] Error caching DC distances: {e}")
            
            total_time = time.time() - start_time
            print(f"[SHiPCacheService] Total DC distances retrieval took {total_time:.4f} seconds")
            return dc_distances
            
        except Exception as e:
            print(f"[SHiPCacheService] Failed to compute DC distances: {e}")
            import traceback
            traceback.print_exc()
            return None

 
