import hashlib
import numpy as np
import time
import multiprocessing
import json
import pickle
from typing import Optional, Dict, Any, List, Tuple
import threading
from .redis_service import redis_service

try:
    import umap.umap_ as umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    print("Warning: UMAP not available. Please install umap-learn to use UMAP dimensionality reduction.")


class UMAPOptimizationService:
    """
    High-performance UMAP service with intelligent caching, adaptive parameters,
    and optimized computation strategies for different dataset sizes.
    Uses Redis-only caching for consistency and persistence.
    """
    
    _lock = threading.RLock()
    
    @classmethod
    def _create_umap_hash(cls, data: np.ndarray, umap_params: Dict[str, Any]) -> str:
        """
        Create a deterministic hash for UMAP computation based on data and parameters.
        Uses efficient sampling for large datasets.
        """
        start_time = time.time()
        try:
            # Create data hash (similar to SHiPCacheService approach)
            if data.size > 100000:  # Large dataset sampling
                sample_size = min(1000, data.shape[0] // 10)
                indices = np.concatenate([
                    np.arange(min(sample_size // 3, data.shape[0])),  # Beginning
                    np.arange(data.shape[0] // 2 - sample_size // 6, 
                             min(data.shape[0] // 2 + sample_size // 6, data.shape[0])),  # Middle
                    np.arange(max(0, data.shape[0] - sample_size // 3), data.shape[0])  # End
                ])
                sample_data = data[indices].flatten()
                data_bytes = sample_data.tobytes()
            else:
                data_bytes = data.tobytes()
            
            # Add shape and basic stats for uniqueness
            shape_info = f"{data.shape}_{np.mean(data):.6f}_{np.std(data):.6f}"
            
            # Create parameter hash
            param_keys = ['n_components', 'n_neighbors', 'min_dist', 'metric', 'n_epochs', 'init']
            param_str = "_".join(f"{k}={umap_params.get(k, 'default')}" for k in param_keys)
            
            # Combine all elements
            combined = data_bytes + shape_info.encode() + param_str.encode()
            hash_obj = hashlib.sha256(combined)
            result = hash_obj.hexdigest()[:16]  # Use first 16 chars for efficiency
            
            elapsed = time.time() - start_time
            print(f"[UMAPOptimizationService] Hash creation took {elapsed:.4f} seconds")
            return result
            
        except Exception as e:
            print(f"[UMAPOptimizationService] Error creating hash: {e}")
            # Fallback to simple hash
            return hashlib.sha256(str(data.shape).encode() + str(time.time()).encode()).hexdigest()[:16]
    
    @classmethod
    def _get_optimal_parameters(cls, data: np.ndarray) -> Dict[str, Any]:
        """
        Determine optimal UMAP parameters based on dataset characteristics.
        Balances speed vs quality based on data size and dimensionality.
        """
        n_samples, n_features = data.shape
        
        # Adaptive n_neighbors
        if n_samples < 100:
            n_neighbors = min(n_samples - 1, 5)
        elif n_samples < 1000:
            n_neighbors = min(15, max(5, n_samples // 10))
        elif n_samples < 10000:
            n_neighbors = min(30, max(15, n_samples // 20))
        else:
            n_neighbors = min(50, max(30, n_samples // 50))
        
        # Adaptive epochs for better quality - increased epochs for better convergence
        if n_samples < 500:
            n_epochs = 75  # Increased for better quality on small datasets
        elif n_samples < 2000:
            n_epochs = 100  # Better convergence for medium datasets
        elif n_samples < 10000:
            n_epochs = 150  # Improved quality for larger datasets
        elif n_samples < 50000:
            n_epochs = 200  # Better convergence for large datasets
        else:
            n_epochs = 250  # Higher quality for very large datasets
        
        # Memory-aware adaptive threading
        cpu_count = multiprocessing.cpu_count()
        available_memory_gb = 8  # Conservative estimate
        try:
            import psutil
            available_memory_gb = psutil.virtual_memory().available / (1024**3)
        except:
            pass
        
        # Adaptive parameters based on dataset size and available memory
        if n_samples < 100:
            n_jobs = 1  # Single thread for very small datasets
        elif n_samples < 500:
            n_jobs = min(2, cpu_count, max(1, int(available_memory_gb / 2)))  # Memory-aware threading
        elif n_samples < 2000:
            n_jobs = min(3, cpu_count, max(1, int(available_memory_gb / 1.5)))  # Conservative for medium datasets
        else:
            n_jobs = min(4, cpu_count)  # Cap at 4 threads for large datasets with memory awareness
        
        # Memory optimization
        low_memory = n_samples > 50000 or n_features > 1000
        
        # For datasets where speed is critical and we can use parallelism,
        # disable random_state to allow n_jobs > 1
        # Only use random_state for very small datasets or single-threaded execution
        use_random_state = n_jobs == 1 or n_samples < 100
        
        # Adaptive min_dist for better local/global structure balance
        if n_samples < 1000:
            min_dist = 0.05  # Tighter clusters for small datasets
        elif n_samples < 10000:
            min_dist = 0.1   # Balanced for medium datasets
        else:
            min_dist = 0.15  # More spread for large datasets
        
        # Adaptive spread for better embedding distribution
        if n_samples < 500:
            spread = 0.8     # Slightly tighter for small datasets
        elif n_samples < 5000:
            spread = 1.0     # Standard spread
        else:
            spread = 1.2     # More spread for large datasets
        
        params = {
            'n_components': 2,
            'n_neighbors': n_neighbors,
            'min_dist': min_dist,
            'metric': 'euclidean',
            'n_epochs': n_epochs,
            'init': 'spectral',  # Faster than 'random'
            'verbose': False,
            'low_memory': low_memory,
            'n_jobs': n_jobs,
            'spread': spread,
            'set_op_mix_ratio': 1.0,
            'local_connectivity': 1.0,
            'repulsion_strength': 1.0,
            'negative_sample_rate': 8,  # Increased from 5 for better quality
            'transform_queue_size': 4.0,
            'a': None,
            'b': None,
        }
        
        # Only add random_state if we're not using parallelism
        if use_random_state:
            params['random_state'] = 42
        
        return params
    
    @classmethod
    def _validate_data_for_umap(cls, data: np.ndarray) -> Tuple[bool, str]:
        """
        Validate that data is suitable for UMAP computation.
        Returns (is_valid, error_message).
        """
        if not UMAP_AVAILABLE:
            return False, "UMAP not available. Please install umap-learn."
        
        if data.shape[0] < 4:
            return False, f"Dataset too small for UMAP ({data.shape[0]} samples, minimum 4)"
        
        if data.shape[1] == 0:
            return False, "No features available for UMAP"
        
        if data.shape[1] == 1:
            return False, "Single feature datasets not suitable for UMAP embedding"
        
        # Check for valid numeric data
        if not np.isfinite(data).all():
            return False, "Data contains NaN or infinite values"
        
        return True, ""
    
    @classmethod
    def _preprocess_data_for_umap(cls, data: np.ndarray) -> Tuple[np.ndarray, List[int]]:
        """
        Preprocess data for UMAP by removing constant features and handling edge cases.
        
        Args:
            data: Input data array (n_samples, n_features)
            
        Returns:
            Tuple of (processed_data, removed_feature_indices)
        """
        # Check for constant features (zero variance)
        feature_variances = np.var(data, axis=0)
        constant_features = feature_variances <= 1e-10  # Use small threshold for numerical stability
        
        if np.any(constant_features):
            # Remove constant features
            valid_features = ~constant_features
            processed_data = data[:, valid_features]
            removed_indices = np.where(constant_features)[0].tolist()
            
            print(f"[UMAPOptimizationService] Removed {len(removed_indices)} constant features (indices: {removed_indices[:5]}{'...' if len(removed_indices) > 5 else ''})")
            print(f"[UMAPOptimizationService] Data shape after preprocessing: {processed_data.shape}")
            
            # Check if we have enough features left
            if processed_data.shape[1] < 2:
                print(f"[UMAPOptimizationService] Warning: Only {processed_data.shape[1]} non-constant features remaining")
                # If we have only 1 feature, duplicate it with small noise for UMAP
                if processed_data.shape[1] == 1:
                    noise = np.random.normal(0, np.std(processed_data[:, 0]) * 0.01, (processed_data.shape[0], 1))
                    processed_data = np.hstack([processed_data, processed_data + noise])
                    print(f"[UMAPOptimizationService] Added noise column to create 2D data for UMAP")
            
            return processed_data, removed_indices
        else:
            return data, []
    
    @classmethod
    def compute_umap_optimized(cls, data: np.ndarray, custom_params: Optional[Dict[str, Any]] = None, fast_mode: bool = True, settings_override: Optional[Dict[str, Any]] = None) -> Optional[List[List[float]]]:
        """
        Compute UMAP embedding with intelligent caching and optimized parameters.
        
        Args:
            data: Input data array (n_samples, n_features)
            custom_params: Optional custom UMAP parameters to override defaults
            fast_mode: Enable fast mode optimizations
            settings_override: Settings from frontend to override defaults
            
        Returns:
            UMAP embedding as list of lists, or None if computation fails
        """
        start_time = time.time()
        
        # Validate input data
        is_valid, error_msg = cls._validate_data_for_umap(data)
        if not is_valid:
            print(f"[UMAPOptimizationService] Validation failed: {error_msg}")
            return None
        
        # Preprocess data to handle constant features
        processed_data, removed_features = cls._preprocess_data_for_umap(data)
        
        # Final validation after preprocessing
        if processed_data.shape[1] < 2:
            print(f"[UMAPOptimizationService] Insufficient features after preprocessing: {processed_data.shape[1]}")
            return None
        
        # Get optimal parameters based on processed data
        optimal_params = cls._get_optimal_parameters(processed_data)
        
        # Apply settings override first (from frontend settings)
        if settings_override:
            print(f"[UMAPOptimizationService] Applying settings override: {settings_override}")
            optimal_params.update(settings_override)
            # Use fast_mode from settings if provided
            if 'fast_mode' in settings_override:
                fast_mode = settings_override['fast_mode']
        
        # Apply fast mode optimizations - less aggressive for better quality
        if fast_mode:
            # More conservative optimizations to maintain quality
            optimal_params['n_epochs'] = max(50, int(optimal_params['n_epochs'] * 0.85))
            optimal_params['negative_sample_rate'] = 6  # Less reduction for better quality
        
        # Apply custom parameter overrides (highest priority)
        if custom_params:
            optimal_params.update(custom_params)
        
        # Create cache key based on processed data
        cache_key = cls._create_umap_hash(processed_data, optimal_params)
        
        # Check Redis cache only
        with cls._lock:
            try:
                if redis_service.client is not None:
                    redis_key = f"umap:{cache_key}"
                    cached_data = redis_service.client.get(redis_key)
                    if cached_data:
                        cached_result = pickle.loads(cached_data)
                        elapsed = time.time() - start_time
                        print(f"[UMAPOptimizationService] Redis cache hit! Returning cached UMAP result in {elapsed:.4f} seconds")
                        return cached_result['embedding']
            except Exception as e:
                print(f"[UMAPOptimizationService] Redis cache lookup failed: {e}")
        
        # Compute UMAP
        try:
            print(f"[UMAPOptimizationService] Computing UMAP for {processed_data.shape[0]} samples, {processed_data.shape[1]} features")
            if len(removed_features) > 0:
                print(f"[UMAPOptimizationService] Original data had {data.shape[1]} features, using {processed_data.shape[1]} after removing {len(removed_features)} constant features")
            print(f"[UMAPOptimizationService] Using parameters: n_neighbors={optimal_params['n_neighbors']}, "
                  f"n_epochs={optimal_params['n_epochs']}, n_jobs={optimal_params['n_jobs']}")
            
            computation_start = time.time()
            
            # Create UMAP reducer with optimized parameters
            reducer = umap.UMAP(**optimal_params)
            
            # Fit and transform using processed data
            embedding = reducer.fit_transform(processed_data)
            
            computation_time = time.time() - computation_start
            print(f"[UMAPOptimizationService] UMAP computation took {computation_time:.4f} seconds")
            
            # Convert to serializable format
            if hasattr(embedding, 'tolist'):
                embedding_list = embedding.tolist()
            else:
                embedding_list = [list(map(float, row)) for row in embedding]
            
            # Cache the result in Redis only
            cache_data = {
                'embedding': embedding_list,
                'parameters': optimal_params.copy(),
                'data_shape': data.shape,
                'processed_data_shape': processed_data.shape,
                'removed_features': removed_features,
                'computation_time': computation_time,
                'timestamp': time.time()
            }
            
            # Store in Redis cache
            try:
                if redis_service.client is not None:
                    redis_key = f"umap:{cache_key}"
                    serialized_data = pickle.dumps(cache_data)
                    redis_service.client.setex(redis_key, 3600 * 24, serialized_data)  # Cache for 24 hours
                    print(f"[UMAPOptimizationService] Cached UMAP result in Redis: {redis_key}")
            except Exception as e:
                print(f"[UMAPOptimizationService] Failed to cache in Redis: {e}")
            
            total_time = time.time() - start_time
            print(f"[UMAPOptimizationService] Total UMAP processing took {total_time:.4f} seconds")
            
            return embedding_list
            
        except Exception as e:
            print(f"[UMAPOptimizationService] UMAP computation failed: {e}")
            return None
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, Any]:
        """Get information about the current UMAP cache state from Redis only."""
        # Get Redis cache info
        redis_cache_size = 0
        redis_cached_datasets = []
        memory_estimate = 0
        
        try:
            if redis_service.client is not None:
                # Count Redis UMAP keys
                redis_keys = list(redis_service.client.scan_iter(match="umap:*"))
                redis_cache_size = len(redis_keys)
                
                # Get sample of Redis cached datasets
                for redis_key in redis_keys[:10]:  # Limit to first 10 for performance
                    try:
                        cached_data = redis_service.client.get(redis_key)
                        if cached_data:
                            cache_info = pickle.loads(cached_data)
                            # Estimate memory usage
                            embedding = cache_info['embedding']
                            memory_estimate += len(embedding) * len(embedding[0]) * 8  # 8 bytes per float
                            
                            redis_cached_datasets.append({
                                'key': redis_key.decode()[-8:] + '...',
                                'data_shape': cache_info['data_shape'],
                                'computation_time': cache_info['computation_time'],
                                'age_minutes': (time.time() - cache_info['timestamp']) / 60
                            })
                    except Exception as e:
                        print(f"[UMAPOptimizationService] Error reading Redis cache entry: {e}")
                        
        except Exception as e:
            print(f"[UMAPOptimizationService] Error getting Redis cache info: {e}")
        
        return {
            'redis_cache_size': redis_cache_size,
            'total_cache_size': redis_cache_size,
            'estimated_memory_mb': memory_estimate / (1024 * 1024),
            'redis_cached_datasets': redis_cached_datasets
        }
    
    @classmethod
    def clear_cache(cls) -> int:
        """Clear the UMAP cache from Redis and return number of entries removed."""
        total_cleared = 0
        
        # Clear Redis cache only
        try:
            if redis_service.client is not None:
                redis_keys = list(redis_service.client.scan_iter(match="umap:*"))
                if redis_keys:
                    redis_service.client.delete(*redis_keys)
                    total_cleared = len(redis_keys)
                    print(f"[UMAPOptimizationService] Cleared {len(redis_keys)} Redis cache entries")
                else:
                    print(f"[UMAPOptimizationService] No Redis cache entries found to clear")
        except Exception as e:
            print(f"[UMAPOptimizationService] Error clearing Redis cache: {e}")
        
        print(f"[UMAPOptimizationService] Total cleared {total_cleared} cache entries")
        return total_cleared
    
    @classmethod
    def get_cache_key_for_computation(cls, data: np.ndarray, custom_params: Optional[Dict[str, Any]] = None, 
                                    fast_mode: bool = True, settings_override: Optional[Dict[str, Any]] = None) -> str:
        """
        Get the cache key that would be used for a UMAP computation with the given parameters.
        This allows external code to know what cache key will be used without running the computation.
        """
        # Apply preprocessing to get the actual data that will be used
        processed_data, _ = cls._preprocess_data_for_umap(data)
        
        # Get optimal parameters
        optimal_params = cls._get_optimal_parameters(processed_data)
        
        # Apply settings override first (from frontend settings)
        if settings_override:
            optimal_params.update(settings_override)
            # Use fast_mode from settings if provided
            if 'fast_mode' in settings_override:
                fast_mode = settings_override['fast_mode']
        
        # Apply fast mode optimizations
        if fast_mode:
            optimal_params['n_epochs'] = max(50, int(optimal_params['n_epochs'] * 0.85))
            optimal_params['negative_sample_rate'] = 6
        
        # Apply custom parameter overrides (highest priority)
        if custom_params:
            optimal_params.update(custom_params)
        
        # Create cache key based on processed data
        return cls._create_umap_hash(processed_data, optimal_params)

    @classmethod
    def precompute_umap(cls, data: np.ndarray, custom_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Precompute UMAP for given data and cache the result.
        Returns cache key for the computation.
        """
        result = cls.compute_umap_optimized(data, custom_params)
        if result is not None:
            cache_key = cls.get_cache_key_for_computation(data, custom_params, fast_mode=False)
            print(f"[UMAPOptimizationService] Precomputed UMAP cached with key: {cache_key[:8]}...")
            return cache_key
        return ""