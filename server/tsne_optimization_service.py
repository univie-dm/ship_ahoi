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
    from sklearn.manifold import TSNE
    TSNE_AVAILABLE = True
except ImportError:
    TSNE_AVAILABLE = False
    print("Warning: t-SNE not available. Please install scikit-learn to use t-SNE dimensionality reduction.")


class TSNEOptimizationService:
    """
    High-performance t-SNE service with intelligent caching, adaptive parameters,
    and optimized computation strategies for different dataset sizes.
    Uses Redis-only caching for consistency and persistence.
    """
    
    _lock = threading.RLock()
    
    @classmethod
    def _create_tsne_hash(cls, data: np.ndarray, tsne_params: Dict[str, Any]) -> str:
        """
        Create a deterministic hash for t-SNE computation based on data and parameters.
        Uses efficient sampling for large datasets.
        """
        try:
            # For large datasets, use strategic sampling to create hash
            if len(data) > 100000:
                # Sample beginning, middle, and end of the array
                sample_size = min(1000, len(data) // 10)
                indices = np.concatenate([
                    np.arange(sample_size),  # Beginning
                    np.arange(len(data) // 2 - sample_size // 2, len(data) // 2 + sample_size // 2),  # Middle
                    np.arange(len(data) - sample_size, len(data))  # End
                ])
                sample_data = data[indices]
                print(f"[TSNEService] Using strategic sampling for hash: {len(sample_data)}/{len(data)} samples")
            else:
                sample_data = data
            
            # Create hash from data sample and parameters
            data_bytes = sample_data.tobytes()
            params_str = str(sorted(tsne_params.items()))
            combined = data_bytes + params_str.encode()
            
            return hashlib.sha256(combined).hexdigest()[:16]
            
        except Exception as e:
            print(f"[TSNEService] Hash creation failed: {e}")
            # Fallback: use timestamp-based hash
            return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    
    @classmethod
    def _get_optimal_tsne_params(cls, n_samples: int, n_features: int, fast_mode: bool = True) -> Dict[str, Any]:
        """
        Get optimal t-SNE parameters based on dataset characteristics.
        """
        # Base parameters
        params = {
            'n_components': 2,
            'random_state': 42,
            'n_jobs': min(4, multiprocessing.cpu_count()),  # Limit to 4 cores for better performance
        }
        
        # Improved perplexity selection using sqrt(n_samples) as baseline
        # More principled approach based on dataset size
        base_perplexity = max(5, min(50, int(np.sqrt(n_samples))))
        
        if n_samples <= 30:
            params['perplexity'] = max(5, min(n_samples // 3, base_perplexity))
        elif n_samples <= 100:
            params['perplexity'] = max(5, min(15, base_perplexity))
        elif n_samples <= 1000:
            params['perplexity'] = max(15, min(30, base_perplexity))
        else:
            params['perplexity'] = max(20, min(50, base_perplexity))
        
        # Adaptive learning rate based on perplexity and dataset size
        base_lr = max(50.0, min(1000.0, params['perplexity'] * 4.0))
        
        # Performance optimization based on dataset size with improved quality
        if fast_mode:
            if n_samples <= 500:
                # Small dataset: high quality settings
                params['learning_rate'] = base_lr
                params['max_iter'] = 1000
                params['early_exaggeration'] = 12.0
            elif n_samples <= 2000:
                # Medium dataset: balanced settings with better quality
                params['learning_rate'] = base_lr * 1.1
                params['max_iter'] = 800  # Increased from 750
                params['early_exaggeration'] = 10.0  # Increased from 8.0
            elif n_samples <= 10000:
                # Large dataset: improved settings
                params['learning_rate'] = base_lr * 1.2
                params['max_iter'] = 600  # Increased from 500
                params['early_exaggeration'] = 8.0   # Increased from 6.0
            else:
                # Very large dataset: better minimum quality
                params['learning_rate'] = base_lr * 1.3
                params['max_iter'] = 400  # Increased from 250
                params['early_exaggeration'] = 6.0   # Increased from 4.0
        else:
            # High quality mode (slower but better results)
            params['learning_rate'] = base_lr
            params['max_iter'] = 1500
            params['early_exaggeration'] = 12.0
        
        return params
    
    @classmethod
    def _validate_data(cls, data: np.ndarray) -> Tuple[bool, str]:
        """
        Validate input data for t-SNE computation.
        """
        if data is None:
            return False, "Data is None"
        
        if not isinstance(data, np.ndarray):
            return False, "Data must be a numpy array"
        
        if len(data.shape) != 2:
            return False, f"Data must be 2D, got shape {data.shape}"
        
        if data.shape[0] < 4:
            return False, f"Need at least 4 samples for t-SNE, got {data.shape[0]}"
        
        if data.shape[1] < 1:
            return False, f"Need at least 1 feature for t-SNE, got {data.shape[1]}"
        
        # Check for invalid values
        if not np.isfinite(data).all():
            return False, "Data contains NaN or infinite values"
        
        return True, "Data is valid"
    
    @classmethod
    def compute_tsne_optimized(cls, data: np.ndarray, fast_mode: bool = True, use_cache: bool = True) -> Optional[List[List[float]]]:
        """
        Compute t-SNE with intelligent optimization and caching.
        
        Args:
            data: Input data array (n_samples, n_features)
            fast_mode: Use faster parameters for large datasets
            use_cache: Whether to use caching system
            
        Returns:
            t-SNE coordinates as list of [x, y] pairs, or None if computation fails
        """
        if not TSNE_AVAILABLE:
            print("[TSNEService] t-SNE not available - skipping computation")
            return None
        
        try:
            # Validate input data
            is_valid, error_msg = cls._validate_data(data)
            if not is_valid:
                print(f"[TSNEService] Data validation failed: {error_msg}")
                return None
            
            n_samples, n_features = data.shape
            print(f"[TSNEService] Computing t-SNE for {n_samples} samples, {n_features} features (fast_mode={fast_mode})")
            
            # Get optimal parameters
            tsne_params = cls._get_optimal_tsne_params(n_samples, n_features, fast_mode)
            
            # Check Redis cache if enabled
            tsne_hash = None
            if use_cache:
                tsne_hash = cls._create_tsne_hash(data, tsne_params)
                
                # Check Redis cache only
                with cls._lock:
                    try:
                        if redis_service.client is not None:
                            redis_key = f"tsne:{tsne_hash}"
                            cached_data = redis_service.client.get(redis_key)
                            if cached_data:
                                cached_result = pickle.loads(cached_data)
                                cache_age = time.time() - cached_result['timestamp']
                                
                                # Cache for 1 hour for large datasets, 30 minutes for smaller ones
                                max_age = 3600 if n_samples > 5000 else 1800
                                
                                if cache_age < max_age:
                                    print(f"[TSNEService] Using Redis cached t-SNE result (age: {cache_age:.1f}s)")
                                    return cached_result['coordinates']
                                else:
                                    # Cache expired, delete from Redis
                                    redis_service.client.delete(redis_key)
                    except Exception as e:
                        print(f"[TSNEService] Redis cache lookup failed: {e}")
            
            # Compute t-SNE
            start_time = time.time()
            
            print(f"[TSNEService] t-SNE parameters: perplexity={tsne_params['perplexity']}, "
                  f"learning_rate={tsne_params['learning_rate']}, max_iter={tsne_params['max_iter']}")
            
            tsne = TSNE(**tsne_params)
            coordinates = tsne.fit_transform(data)
            
            end_time = time.time()
            print(f"[TSNEService] t-SNE computation completed in {end_time - start_time:.4f} seconds")
            
            # Convert to list format
            result = coordinates.tolist()
            
            # Cache the result in Redis only if enabled
            if use_cache and tsne_hash:
                cache_data = {
                    'coordinates': result,
                    'timestamp': time.time(),
                    'data_shape': data.shape,
                    'parameters': tsne_params
                }
                
                # Store in Redis cache only
                try:
                    if redis_service.client is not None:
                        redis_key = f"tsne:{tsne_hash}"
                        serialized_data = pickle.dumps(cache_data)
                        # Set expiration based on dataset size
                        ttl = 3600 if n_samples > 5000 else 1800
                        redis_service.client.setex(redis_key, ttl, serialized_data)
                        print(f"[TSNEService] Cached t-SNE result in Redis: {redis_key}")
                except Exception as e:
                    print(f"[TSNEService] Failed to cache in Redis: {e}")
                
                print(f"[TSNEService] Cached t-SNE result with hash {tsne_hash}")
            
            return result
            
        except Exception as e:
            print(f"[TSNEService] t-SNE computation failed: {e}")
            return None
    
    @classmethod
    def clear_cache(cls):
        """Clear the t-SNE computation cache from Redis."""
        total_cleared = 0
        
        # Clear Redis cache only
        try:
            if redis_service.client is not None:
                redis_keys = list(redis_service.client.scan_iter(match="tsne:*"))
                if redis_keys:
                    redis_service.client.delete(*redis_keys)
                    total_cleared = len(redis_keys)
                    print(f"[TSNEService] Cleared {len(redis_keys)} Redis cache entries")
                else:
                    print(f"[TSNEService] No Redis cache entries found to clear")
        except Exception as e:
            print(f"[TSNEService] Error clearing Redis cache: {e}")
        
        print(f"[TSNEService] Total cleared {total_cleared} cache entries")
        return total_cleared
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, Any]:
        """Get information about the current cache state from Redis only."""
        # Get Redis cache info
        redis_cache_size = 0
        redis_cached_datasets = []
        memory_estimate = 0
        
        try:
            if redis_service.client is not None:
                redis_keys = list(redis_service.client.scan_iter(match="tsne:*"))
                redis_cache_size = len(redis_keys)
                
                # Get sample of Redis cached datasets
                for redis_key in redis_keys[:10]:  # Limit to first 10 for performance
                    try:
                        cached_data = redis_service.client.get(redis_key)
                        if cached_data:
                            cache_info = pickle.loads(cached_data)
                            coords = cache_info['coordinates']
                            if coords:
                                # Estimate size: 8 bytes per float * 2 coordinates * n_samples
                                estimated_size = len(coords) * 2 * 8
                                memory_estimate += estimated_size
                            
                            redis_cached_datasets.append({
                                'key': redis_key.decode()[-8:] + '...',
                                'data_shape': cache_info['data_shape'],
                                'age_minutes': (time.time() - cache_info['timestamp']) / 60
                            })
                    except Exception as e:
                        print(f"[TSNEService] Error reading Redis cache entry: {e}")
        except Exception as e:
            print(f"[TSNEService] Error getting Redis cache info: {e}")
        
        return {
            'redis_cache_size': redis_cache_size,
            'total_cache_size': redis_cache_size,
            'estimated_memory_mb': memory_estimate / (1024 * 1024),
            'redis_cached_datasets': redis_cached_datasets
        }
    
    @classmethod
    def compute_tsne_with_fallback(cls, data: np.ndarray, fast_mode: bool = True) -> Optional[List[List[float]]]:
        """
        Compute t-SNE with automatic fallback strategies for edge cases.
        """
        try:
            # First attempt: standard t-SNE
            result = cls.compute_tsne_optimized(data, fast_mode=fast_mode)
            if result is not None:
                return result
            
            # Fallback 1: Try with more robust parameters
            print("[TSNEService] Standard t-SNE failed, trying fallback parameters...")
            n_samples = data.shape[0]
            # More conservative fallback with better quality
            fallback_perplexity = max(5, min(30, int(np.sqrt(n_samples))))
            fallback_params = {
                'n_components': 2,
                'perplexity': fallback_perplexity,
                'learning_rate': max(50.0, fallback_perplexity * 3.0),
                'max_iter': 500,  # Increased from 250
                'random_state': 42,
                'early_exaggeration': 8.0  # Increased from 4.0
            }
            
            tsne = TSNE(**fallback_params)
            coordinates = tsne.fit_transform(data)
            result = coordinates.tolist()
            print("[TSNEService] Fallback t-SNE computation successful")
            return result
            
        except Exception as e:
            print(f"[TSNEService] All t-SNE computation attempts failed: {e}")
            return None