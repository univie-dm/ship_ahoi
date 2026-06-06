"""
ToyDatasetService: Comprehensive sample dataset generation for clustering analysis.

This service provides a wide variety of synthetic and real-world datasets for testing
clustering algorithms, dimensionality reduction techniques, and educational purposes.
"""

import numpy as np
import time
from typing import Dict, Any, List, Tuple, Optional
from sklearn.datasets import (
    make_blobs, make_moons, make_circles, make_s_curve, make_swiss_roll,
    make_classification, load_iris, load_wine, load_breast_cancer, load_digits,
    fetch_olivetti_faces, fetch_california_housing, fetch_lfw_people
)
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from enum import Enum
import urllib.request
import os
import tempfile
import gzip
import struct
import zipfile
import shutil
import pickle
from PIL import Image
import threading
import hashlib


class DatasetCategory(str, Enum):
    """Dataset categories for organization and UI display."""
    SYNTHETIC_2D = "synthetic_2d"
    SYNTHETIC_ND = "synthetic_nd" 
    REAL_WORLD = "real_world"


class DatasetInfo:
    """Metadata for a dataset."""
    def __init__(self, name: str, category: DatasetCategory, description: str, 
                 typical_dims: int, typical_samples: int, difficulty: str = "medium",
                 supports_custom_dims: bool = False, max_dims: int = None):
        self.name = name
        self.category = category
        self.description = description
        self.typical_dims = typical_dims
        self.typical_samples = typical_samples
        self.difficulty = difficulty  # "easy", "medium", "hard"
        self.supports_custom_dims = supports_custom_dims
        self.max_dims = max_dims or typical_dims


class ToyDatasetService:
    """
    Comprehensive toy dataset generation service.
    
    Provides a wide variety of datasets including:
    - Enhanced 2D synthetic datasets
    - High-dimensional synthetic datasets (5-20D)
    - Real-world datasets from sklearn
    - Educational datasets with varying complexity
    """
    
    # Use Redis-only caching for consistency and persistence
    _cache_lock = threading.RLock()
    _lfw_cache: Optional[Tuple[np.ndarray, np.ndarray]] = None
    _fashion_mnist_cache: Optional[Tuple[np.ndarray, np.ndarray]] = None
    _sign_language_cache: Optional[Tuple[np.ndarray, np.ndarray]] = None
    _download_dataset_cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
    _DOWNLOAD_REDIS_PREFIX = "downloaded_dataset"
    _DOWNLOAD_CACHE_TTL_SECONDS = 3600 * 24  # 24 hours
    _MAX_REDIS_DOWNLOAD_MB = 200
    _dataset_2_cache: Optional[Tuple[np.ndarray, np.ndarray]] = None

    # Dataset metadata registry
    DATASETS = {
        # === 2D SYNTHETIC DATASETS ===
        'blobs': DatasetInfo(
            'blobs', DatasetCategory.SYNTHETIC_2D,
            'Gaussian clusters with clear separation - ideal for basic clustering',
            2, 200, 'easy'
        ),
        'moons': DatasetInfo(
            'moons', DatasetCategory.SYNTHETIC_2D,
            'Two interleaving half-circles - tests non-linear clustering',
            2, 200, 'medium'
        ),
        'circles': DatasetInfo(
            'circles', DatasetCategory.SYNTHETIC_2D,
            'Concentric circles pattern - challenges density-based clustering',
            2, 200, 'medium'
        ),
        'aniso': DatasetInfo(
            'aniso', DatasetCategory.SYNTHETIC_2D,
            'Elongated clusters at different angles - tests shape sensitivity',
            2, 200, 'medium'
        ),
        'varied': DatasetInfo(
            'varied', DatasetCategory.SYNTHETIC_2D,
            'Clusters with different sizes and densities',
            2, 200, 'medium'
        ),
        'spiral': DatasetInfo(
            'spiral', DatasetCategory.SYNTHETIC_2D,
            'Two interleaving spiral patterns - very challenging',
            2, 200, 'hard'
        ),
        
        # === HIGH-DIMENSIONAL SYNTHETIC DATASETS ===
        'blobs_nd': DatasetInfo(
            'blobs_nd', DatasetCategory.SYNTHETIC_ND,
            'Multi-dimensional galaxy clusters in cosmic web (5-20D) - simulates dark matter halos',
            10, 500, 'medium', True, 20
        ),
        'classification_nd': DatasetInfo(
            'classification_nd', DatasetCategory.SYNTHETIC_ND,
            'High-dimensional gene regulation patterns with noise - models cellular pathways',
            15, 1000, 'hard', True, 50
        ),
        'sparse_clusters': DatasetInfo(
            'sparse_clusters', DatasetCategory.SYNTHETIC_ND,
            'Sparse clusters in quantum Hilbert space - tests curse of dimensionality',
            20, 800, 'hard', True, 100
        ),
        'hypercube': DatasetInfo(
            'hypercube', DatasetCategory.SYNTHETIC_ND,
            'Atomic positions in crystal structures - clusters on hypercube vertices',
            8, 512, 'hard', True, 15
        ),
        'swiss_roll_3d': DatasetInfo(
            'swiss_roll_3d', DatasetCategory.SYNTHETIC_ND,
            'Protein conformational space manifold - models amino acid interactions',
            3, 1000, 'hard'
        ),
        'neural_embedding': DatasetInfo(
            'neural_embedding', DatasetCategory.SYNTHETIC_ND,
            'High-dimensional word embeddings with semantic clusters - NLP-inspired',
            25, 1200, 'hard', True, 50
        ),
        
        # === REAL-WORLD DATASETS ===
        'iris': DatasetInfo(
            'iris', DatasetCategory.REAL_WORLD,
            'Classic iris flower dataset - 4 features, 3 species, 150 samples',
            4, 150, 'easy'
        ),
        'wine': DatasetInfo(
            'wine', DatasetCategory.REAL_WORLD,
            'Wine quality dataset - 13 chemical features, 3 classes, 178 samples',
            13, 178, 'medium'
        ),
        'breast_cancer': DatasetInfo(
            'breast_cancer', DatasetCategory.REAL_WORLD,
            'Breast cancer diagnosis - 30 features, 2 classes, 569 samples',
            30, 569, 'medium'
        ),
        'digits_small': DatasetInfo(
            'Digits (Small)', DatasetCategory.REAL_WORLD,
            'Handwritten digits - 64 pixels (8x8), 10 classes, 1797 samples',
            64, 1797, 'hard'
        ),
        'coil20': DatasetInfo(
            'coil20', DatasetCategory.REAL_WORLD,
            'COIL20 object recognition - 20 objects, 72 angles each, 1440 grayscale images',
            1024, 1440, 'hard'
        ),
        'olivetti_faces': DatasetInfo(
            'olivetti_faces', DatasetCategory.REAL_WORLD,
            'Olivetti faces - 40 people, 10 images each, 400 grayscale face images',
            4096, 400, 'hard'
        ),
        'lfw_faces': DatasetInfo(
            'lfw_faces', DatasetCategory.REAL_WORLD,
            'Labeled Faces in the Wild - aligned face images (grayscale)',
            2914, 4000, 'hard'
        ),
        'digits_full': DatasetInfo(
            'Digits (Big)', DatasetCategory.REAL_WORLD,
            'Full handwritten digits - 64 pixels (8x8), 10 classes, 5620 samples',
            64, 5620, 'medium'
        ),
        'california_housing': DatasetInfo(
            'california_housing', DatasetCategory.REAL_WORLD,
            'California housing prices - 8 features, 20640 samples',
            8, 20640, 'medium'
        ),
        
        # === NEW REAL-WORLD DATASETS (10K samples, <50 dimensions) ===
        'customer_segments': DatasetInfo(
            'customer_segments', DatasetCategory.REAL_WORLD,
            'E-commerce customer behavior - 12 features, 8000 samples',
            12, 8000, 'easy'
        ),
        'network_intrusion': DatasetInfo(
            'network_intrusion', DatasetCategory.REAL_WORLD,
            'Network security intrusion detection - 41 features, 10000 samples',
            41, 10000, 'hard'
        ),
        'gene_expression': DatasetInfo(
            'gene_expression', DatasetCategory.REAL_WORLD,
            'Gene expression cancer data - 30 features, 9000 samples',
            30, 9000, 'medium'
        ),
        'financial_fraud': DatasetInfo(
            'financial_fraud', DatasetCategory.REAL_WORLD,
            'Credit card fraud detection - 28 features, 12000 samples',
            28, 12000, 'medium'
        ),
        'sensor_readings': DatasetInfo(
            'sensor_readings', DatasetCategory.REAL_WORLD,
            'IoT sensor environmental data - 15 features, 15000 samples',
            15, 15000, 'easy'
        ),
        'social_media': DatasetInfo(
            'social_media', DatasetCategory.REAL_WORLD,
            'Social media user engagement - 22 features, 11000 samples',
            22, 11000, 'medium'
        ),
        'medical_diagnosis': DatasetInfo(
            'medical_diagnosis', DatasetCategory.REAL_WORLD,
            'Medical diagnostic features - 35 features, 8500 samples',
            35, 8500, 'hard'
        ),
        'retail_analytics': DatasetInfo(
            'retail_analytics', DatasetCategory.REAL_WORLD,
            'Retail sales and inventory - 18 features, 13000 samples',
            18, 13000, 'easy'
        ),
        'diabetes': DatasetInfo(
            'diabetes', DatasetCategory.REAL_WORLD,
            'Diabetes dataset - 10 features, 442 samples',
            10, 442, 'medium'
        ),
        'palmer_penguins': DatasetInfo(
            'palmer_penguins', DatasetCategory.REAL_WORLD,
            'Palmer Penguins - Antarctic penguin species with bill and body measurements, 3 species, 344 samples',
            6, 344, 'easy'
        ),
        'fashion_mnist': DatasetInfo(
            'fashion_mnist', DatasetCategory.REAL_WORLD,
            'Fashion-MNIST apparel images - 28x28 grayscale, 10 classes',
            784, 10000, 'medium'
        ),
        'sign_language_digits': DatasetInfo(
            'sign_language_digits', DatasetCategory.REAL_WORLD,
            'American Sign Language digit gestures - 64x64 grayscale images',
            4096, 2000, 'medium'
        ),
        'dataset_1': DatasetInfo(
            'dataset_1', DatasetCategory.REAL_WORLD,
            'Dataset 1 - 13 features, 178 samples',
            13, 178, 'easy'
        ),
        'dataset_2': DatasetInfo(
            'dataset_2', DatasetCategory.REAL_WORLD,
            'Dataset 2 - 784 features, 5000 samples',
            784, 5000, 'medium'
        ),
        'wheats': DatasetInfo(
            'wheats', DatasetCategory.REAL_WORLD,
            'Wheat Seeds dataset - 7 geometric features, 3 varieties, 210 samples',
            7, 210, 'easy'
        ),
        'olive_oil': DatasetInfo(
            'olive_oil', DatasetCategory.REAL_WORLD,
            'Italian Olive Oil - 8 fatty acid features, 3 regions (9 areas), 572 samples',
            8, 572, 'easy'
        ),
        'zoo': DatasetInfo(
            'zoo', DatasetCategory.REAL_WORLD,
            'Zoo Animals - 16 boolean features, 7 animal classes, 101 samples',
            16, 101, 'easy'
        ),
    }

    @classmethod
    def get_dataset_info(cls, dataset_name: str) -> Optional[DatasetInfo]:
        """Get metadata information for a dataset."""
        return cls.DATASETS.get(dataset_name)

    @classmethod
    def list_datasets_by_category(cls) -> Dict[str, List[str]]:
        """Get datasets organized by category."""
        categories = {}
        for name, info in cls.DATASETS.items():
            category = info.category.value
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        return categories

    @classmethod
    def _download_cache_key(cls, dataset_name: str) -> str:
        return f"{cls._DOWNLOAD_REDIS_PREFIX}:{dataset_name}"

    @classmethod
    def _get_cached_downloaded_dataset(cls, dataset_name: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Return previously downloaded dataset from in-memory or Redis cache if available."""
        with cls._cache_lock:
            cached = cls._download_dataset_cache.get(dataset_name)
        if cached is not None:
            return cached

        try:
            from .redis_service import redis_service
            if redis_service.client is None:
                redis_service.connect()
            if redis_service.client is None:
                return None

            redis_key = cls._download_cache_key(dataset_name)
            cached_blob = redis_service.client.get(redis_key)
            if cached_blob:
                payload = pickle.loads(cached_blob)
                X = payload.get('X')
                y = payload.get('y')
                if X is not None and y is not None:
                    with cls._cache_lock:
                        cls._download_dataset_cache[dataset_name] = (X, y)
                    print(f"[ToyDatasetService] Loaded downloaded dataset '{dataset_name}' from Redis cache")
                    return X, y
        except Exception as e:
            print(f"[ToyDatasetService] Failed to load downloaded dataset '{dataset_name}' from Redis: {e}")

        return None

    @classmethod
    def _store_downloaded_dataset(cls, dataset_name: str, X: np.ndarray, y: np.ndarray) -> None:
        """Persist downloaded datasets in-memory and in Redis for faster reuse."""
        with cls._cache_lock:
            cls._download_dataset_cache[dataset_name] = (X, y)

        dataset_size_mb = (X.nbytes + y.nbytes) / (1024 * 1024)
        if dataset_size_mb > cls._MAX_REDIS_DOWNLOAD_MB:
            print(f"[ToyDatasetService] Skipping Redis cache for '{dataset_name}': {dataset_size_mb:.1f}MB exceeds {cls._MAX_REDIS_DOWNLOAD_MB}MB limit")
            return

        try:
            from .redis_service import redis_service
            if redis_service.client is None:
                redis_service.connect()
            if redis_service.client is None:
                return

            payload = pickle.dumps({
                'X': X.copy(),
                'y': y.copy(),
                'shape': X.shape,
                'dtype': str(X.dtype),
                'timestamp': time.time(),
            })
            redis_key = cls._download_cache_key(dataset_name)
            redis_service.client.setex(redis_key, cls._DOWNLOAD_CACHE_TTL_SECONDS, payload)
            print(f"[ToyDatasetService] Cached downloaded dataset '{dataset_name}' in Redis ({dataset_size_mb:.2f}MB)")
        except Exception as e:
            print(f"[ToyDatasetService] Failed to cache downloaded dataset '{dataset_name}' in Redis: {e}")

    @classmethod
    def _create_cache_key(cls, dataset_name: str, n_samples: int, n_clusters: int, 
                         n_features: int, random_state: int, **kwargs) -> str:
        """Create a deterministic cache key for dataset parameters."""
        # Create a hash of all parameters to ensure uniqueness
        params_str = f"{dataset_name}_{n_samples}_{n_clusters}_{n_features}_{random_state}"
        if kwargs:
            # Sort kwargs for consistent ordering
            kwargs_str = "_".join(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            params_str += f"_{kwargs_str}"
        
        # Use hash to keep key length manageable
        return hashlib.md5(params_str.encode()).hexdigest()
    
    @classmethod
    def clear_cache(cls):
        """Clear the dataset cache from Redis."""
        with cls._cache_lock:
            try:
                from .redis_service import redis_service
                if redis_service.client is not None:
                    redis_keys = list(redis_service.client.scan_iter(match="toy_dataset:*"))
                    download_keys = list(redis_service.client.scan_iter(match=f"{cls._DOWNLOAD_REDIS_PREFIX}:*"))

                    total_removed = 0
                    if redis_keys:
                        redis_service.client.delete(*redis_keys)
                        total_removed += len(redis_keys)
                    if download_keys:
                        redis_service.client.delete(*download_keys)
                        total_removed += len(download_keys)

                    if total_removed:
                        print(f"[ToyDatasetService] Dataset cache cleared: {total_removed} Redis entries removed")
                    else:
                        print("[ToyDatasetService] Dataset cache cleared: no entries found in Redis")
                else:
                    print("[ToyDatasetService] Dataset cache clear failed: Redis not available")
            except Exception as e:
                print(f"[ToyDatasetService] Dataset cache clear failed: {e}")
            finally:
                cls._download_dataset_cache.clear()
                cls._lfw_cache = None
                cls._fashion_mnist_cache = None
                cls._sign_language_cache = None
                cls._dataset_2_cache = None

    @classmethod
    def get_dataset_by_data_hash(cls, data_hash: str) -> Optional[Tuple[str, str]]:
        """
        Get dataset name and cache key by data hash for SHiP caching coordination.
        
        Returns:
            Tuple of (dataset_name, cache_key) if found, None otherwise
        """
        with cls._cache_lock:
            try:
                from .redis_service import redis_service
                if redis_service.client is not None:
                    # Scan all toy dataset keys
                    redis_keys = list(redis_service.client.scan_iter(match="toy_dataset:*"))
                    for redis_key in redis_keys:
                        try:
                            cached_data = redis_service.client.get(redis_key)
                            if cached_data:
                                import pickle
                                cached_result = pickle.loads(cached_data)
                                if cached_result.get('data_hash') == data_hash:
                                    key_str = redis_key.decode() if isinstance(redis_key, bytes) else redis_key
                                    cache_key = key_str.replace('toy_dataset:', '')
                                    return cached_result['dataset_name'], cache_key
                        except Exception:
                            continue
                return None
            except Exception as e:
                print(f"[ToyDatasetService] Error looking up dataset by hash: {e}")
                return None

    @classmethod
    def generate_dataset(cls, dataset_name: str, n_samples: int = 200, 
                        n_clusters: int = 3, n_features: int = None,
                        random_state: int = 42, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a specified dataset with caching for consistency.
        
        Args:
            dataset_name: Name of the dataset to generate
            n_samples: Number of samples to generate
            n_clusters: Number of clusters (for applicable datasets)
            n_features: Number of features (for high-dimensional datasets)
            random_state: Random seed for reproducibility
            **kwargs: Additional dataset-specific parameters
            
        Returns:
            Tuple of (X, y) where X is the data and y are the true labels
        """
        if dataset_name not in cls.DATASETS:
            raise ValueError(f"Unknown dataset: {dataset_name}. Available: {list(cls.DATASETS.keys())}")

        info = cls.DATASETS[dataset_name]
        
        # Set default n_features based on dataset
        if n_features is None:
            n_features = info.typical_dims

        # Validate parameters
        if info.supports_custom_dims and info.max_dims and n_features > info.max_dims:
            raise ValueError(f"Dataset {dataset_name} supports maximum {info.max_dims} features")

        # Create cache key for this specific dataset configuration
        cache_key = cls._create_cache_key(dataset_name, n_samples, n_clusters, n_features, random_state, **kwargs)
        
        # Check Redis cache first
        with cls._cache_lock:
            try:
                from .redis_service import redis_service
                if redis_service.client is not None:
                    redis_key = f"toy_dataset:{cache_key}"
                    cached_data = redis_service.client.get(redis_key)
                    if cached_data:
                        import pickle
                        cached_result = pickle.loads(cached_data)
                        X_cached = cached_result['X']
                        y_cached = cached_result['y']
                        
                        # Validate data integrity and ensure consistency
                        expected_shape = tuple(cached_result.get('data_shape', X_cached.shape))
                        expected_dtype = cached_result.get('data_dtype', str(X_cached.dtype))
                        
                        if X_cached.shape != expected_shape:
                            print(f"[ToyDatasetService] Warning: Cached data shape mismatch ({X_cached.shape} vs {expected_shape}), regenerating")
                        elif str(X_cached.dtype) != expected_dtype:
                            print(f"[ToyDatasetService] Warning: Cached data dtype mismatch ({X_cached.dtype} vs {expected_dtype}), regenerating")
                        else:
                            # Ensure data maintains exact characteristics for consistent SHiP hashing
                            X_cached = X_cached.astype(expected_dtype)
                            print(f"[ToyDatasetService] Using cached dataset from Redis: {dataset_name} (key: {cache_key[:8]}..., hash: {cached_result.get('data_hash', 'unknown')[:8]}...)")
                            return X_cached, y_cached
            except Exception as e:
                print(f"[ToyDatasetService] Redis cache lookup failed: {e}")
        
        print(f"[ToyDatasetService] Generating new dataset: {dataset_name} (n_samples={n_samples}, n_clusters={n_clusters}, n_features={n_features}, random_state={random_state})")
        
        # Generate the dataset
        if info.category == DatasetCategory.SYNTHETIC_2D:
            X, y = cls._generate_2d_synthetic(dataset_name, n_samples, n_clusters, random_state, **kwargs)
        elif info.category == DatasetCategory.SYNTHETIC_ND:
            X, y = cls._generate_nd_synthetic(dataset_name, n_samples, n_clusters, n_features, random_state, **kwargs)
        elif info.category == DatasetCategory.REAL_WORLD:
            X, y = cls._generate_real_world(dataset_name, n_samples, random_state, **kwargs)
        else:
            raise ValueError(f"Unknown dataset category: {info.category}")
        
        # Cache the result in Redis for future use
        with cls._cache_lock:
            try:
                from .redis_service import redis_service
                if redis_service.client is not None:
                    import pickle
                    # Compute the data hash that SHiPCacheService would use for consistency
                    from .ship_cache_service import SHiPCacheService
                    data_hash = SHiPCacheService._create_data_hash(X)
                    
                    cache_data = {
                        'X': X.copy(),
                        'y': y.copy(),
                        'dataset_name': dataset_name,
                        'timestamp': time.time(),
                        'data_shape': X.shape,
                        'data_dtype': str(X.dtype),
                        'data_hash': data_hash,  # Store SHiP-compatible hash
                        'cache_key': cache_key  # Store the dataset cache key
                    }
                    redis_key = f"toy_dataset:{cache_key}"
                    serialized_data = pickle.dumps(cache_data)
                    # Cache for 24 hours
                    redis_service.client.setex(redis_key, 3600 * 24, serialized_data)
                    print(f"[ToyDatasetService] Cached dataset in Redis: {dataset_name} (shape: {X.shape}, key: {cache_key[:8]}..., hash: {data_hash[:8]}...)")
            except Exception as e:
                print(f"[ToyDatasetService] Failed to cache dataset in Redis: {e}")
        
        return X, y

    @classmethod
    def _generate_2d_synthetic(cls, dataset_name: str, n_samples: int, n_clusters: int, 
                             random_state: int, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
        """Generate 2D synthetic datasets."""
        
        if dataset_name == 'blobs':
            return make_blobs(n_samples=n_samples, centers=n_clusters, 
                            random_state=random_state, cluster_std=1.0)
        
        elif dataset_name == 'moons':
            X, y = make_moons(n_samples=n_samples, noise=0.05, random_state=random_state)
            return X, y
        
        elif dataset_name == 'circles':
            X, y = make_circles(n_samples=n_samples, noise=0.05, random_state=random_state)
            return X, y
        
        elif dataset_name == 'aniso':
            # Anisotropically distributed data
            transformation = np.array([[0.6, -0.6], [-0.4, 0.8]])
            X, y = make_blobs(n_samples=n_samples, centers=n_clusters, random_state=random_state)
            X = np.dot(X, transformation)
            return X, y
        
        elif dataset_name == 'varied':
            # Varied variances
            stds = [1.0, 2.5, 0.5, 1.5, 0.8]
            stds = (stds * ((n_clusters // len(stds)) + 1))[:n_clusters]
            return make_blobs(n_samples=n_samples, centers=n_clusters, 
                            cluster_std=stds, random_state=random_state)
        
        elif dataset_name == 'spiral':
            # Two interleaving spirals
            n_points = n_samples // 2
            t = np.linspace(0, 3 * np.pi, n_points)
            
            # First spiral
            x1 = t * np.cos(t)
            y1 = t * np.sin(t)
            
            # Second spiral (offset by pi)
            x2 = t * np.cos(t + np.pi)
            y2 = t * np.sin(t + np.pi)
            
            # Combine and add noise
            X = np.vstack([np.column_stack([x1, y1]), np.column_stack([x2, y2])])
            X += np.random.RandomState(random_state).normal(0, 0.15, X.shape)
            y = np.hstack([np.zeros(n_points), np.ones(n_points)])
            return X, y
        
        else:
            raise ValueError(f"Unknown 2D synthetic dataset: {dataset_name}")

    @classmethod
    def _generate_nd_synthetic(cls, dataset_name: str, n_samples: int, n_clusters: int,
                             n_features: int, random_state: int, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
        """Generate high-dimensional synthetic datasets."""
        
        if dataset_name == 'blobs_nd':
            return make_blobs(n_samples=n_samples, centers=n_clusters, n_features=n_features,
                            cluster_std=1.0, random_state=random_state)
        
        elif dataset_name == 'classification_nd':
            # High-dimensional classification with noise features
            n_informative = max(2, n_features // 3)
            n_redundant = max(0, n_features // 4)
            n_clusters_per_class = max(1, n_clusters // 3)
            
            return make_classification(
                n_samples=n_samples, n_features=n_features, n_informative=n_informative,
                n_redundant=n_redundant, n_clusters_per_class=n_clusters_per_class,
                n_classes=n_clusters, class_sep=0.8, random_state=random_state
            )
        
        elif dataset_name == 'sparse_clusters':
            # High-dimensional sparse clustering
            # Generate clusters in a subspace, add noise in other dimensions
            subspace_dims = max(3, n_features // 4)
            
            # Generate clusters in subspace
            X_sub, y = make_blobs(n_samples=n_samples, centers=n_clusters, 
                                n_features=subspace_dims, cluster_std=1.5, random_state=random_state)
            
            # Add noise dimensions
            noise_dims = n_features - subspace_dims
            if noise_dims > 0:
                noise = np.random.RandomState(random_state).normal(0, 0.5, (n_samples, noise_dims))
                X = np.hstack([X_sub, noise])
            else:
                X = X_sub
            
            return X, y
        
        elif dataset_name == 'hypercube':
            # Clusters on hypercube vertices
            n_vertices = min(n_clusters, 2**n_features)
            
            # Generate hypercube vertices
            vertices = []
            for i in range(n_vertices):
                vertex = []
                for j in range(n_features):
                    vertex.append(1 if (i >> j) & 1 else -1)
                vertices.append(vertex)
            
            vertices = np.array(vertices) * 3  # Scale up
            
            # Generate samples around each vertex
            samples_per_cluster = n_samples // n_vertices
            X_list = []
            y_list = []
            
            for i, vertex in enumerate(vertices):
                if i == n_vertices - 1:  # Last cluster gets remaining samples
                    cluster_samples = n_samples - len(X_list)
                else:
                    cluster_samples = samples_per_cluster
                
                # Add noise around vertex
                noise = np.random.RandomState(random_state + i).normal(0, 0.3, (cluster_samples, n_features))
                cluster_data = vertex + noise
                
                X_list.append(cluster_data)
                y_list.append(np.full(cluster_samples, i))
            
            X = np.vstack(X_list)
            y = np.hstack(y_list)
            
            return X, y
        
        elif dataset_name == 'swiss_roll_3d':
            # Swiss roll in 3D
            X, color = make_swiss_roll(n_samples=n_samples, noise=0.1, random_state=random_state)
            # Create labels based on color
            y = (color - color.min()) / (color.max() - color.min())
            y = (y * (n_clusters - 1)).astype(int)
            return X, y
        
        elif dataset_name == 'neural_embedding':
            # High-dimensional word embeddings with semantic clusters
            # Simulate word embeddings by creating semantic clusters in high-D space
            rng = np.random.RandomState(random_state)
            
            # Create semantic clusters (like word categories)
            cluster_centers = rng.randn(n_clusters, n_features) * 2
            
            # Generate samples around each semantic cluster
            samples_per_cluster = n_samples // n_clusters
            X_list = []
            y_list = []
            
            for i, center in enumerate(cluster_centers):
                if i == n_clusters - 1:  # Last cluster gets remaining samples
                    cluster_samples = n_samples - len(X_list)
                else:
                    cluster_samples = samples_per_cluster
                
                # Add semantic noise with different patterns for each cluster
                if i % 3 == 0:  # Dense semantic cluster
                    cluster_data = center + rng.normal(0, 0.5, (cluster_samples, n_features))
                elif i % 3 == 1:  # Sparse semantic cluster
                    cluster_data = center + rng.normal(0, 1.2, (cluster_samples, n_features))
                else:  # Mixed semantic cluster
                    cluster_data = center + rng.normal(0, 0.8, (cluster_samples, n_features))
                
                # Add word embedding-like correlations
                for j in range(min(5, n_features // 3)):
                    cluster_data[:, j] = cluster_data[:, j] + 0.3 * cluster_data[:, (j + 1) % n_features]
                
                X_list.append(cluster_data)
                y_list.append(np.full(cluster_samples, i))
            
            X = np.vstack(X_list)
            y = np.hstack(y_list)
            
            return X, y
        
        else:
            raise ValueError(f"Unknown high-dimensional synthetic dataset: {dataset_name}")

    @classmethod
    def _load_coil20(cls) -> Tuple[np.ndarray, np.ndarray]:
        """Load COIL20 dataset from Columbia University."""
        import urllib.request
        import zipfile
        import os
        import tempfile
        from PIL import Image
        import shutil

        cached = cls._get_cached_downloaded_dataset('coil20')
        if cached is not None:
            return cached

        # Create temp directory for COIL20 data
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, 'coil-20-proc.zip')

        try:
            # Download COIL20 dataset
            url = 'http://www.cs.columbia.edu/CAVE/databases/SLAM_coil-20_coil-100/coil-20/coil-20-proc.zip'
            print(f"Downloading COIL20 dataset from {url}...")
            urllib.request.urlretrieve(url, zip_path)
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Load images
            images = []
            labels = []
            
            # Check what files are available
            coil_dir = os.path.join(temp_dir, 'coil-20-proc')
            if not os.path.exists(coil_dir):
                coil_dir = temp_dir
            
            # Get all PNG files
            png_files = []
            for root, dirs, files in os.walk(coil_dir):
                for file in files:
                    if file.endswith('.png') and file.startswith('obj'):
                        png_files.append(os.path.join(root, file))
            
            print(f"Found {len(png_files)} PNG files")
            
            # Load all images
            for img_path in png_files:
                filename = os.path.basename(img_path)
                # Extract object ID from filename (e.g., obj1__0.png -> 1)
                obj_id = int(filename.split('__')[0][3:])  # Extract number after 'obj'
                
                # Load and process image
                img = Image.open(img_path).convert('L')  # Convert to grayscale
                img_array = np.array(img).flatten()  # Flatten to 1D
                images.append(img_array)
                labels.append(obj_id - 1)  # Convert to 0-based indexing
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            if len(images) == 0:
                raise ValueError("No images found in COIL20 dataset")

            X = np.array(images)
            y = np.array(labels)

            print(f"Successfully loaded COIL20 dataset: {X.shape[0]} samples, {X.shape[1]} features")
            cls._store_downloaded_dataset('coil20', X, y)
            return X, y
            
        except Exception as e:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise RuntimeError(f"Failed to load COIL20 dataset: {e}")

    @classmethod
    def _load_digits_full(cls) -> Tuple[np.ndarray, np.ndarray]:
        """Load full UCI digits dataset (5620 samples) by downloading from UCI repository."""
        import urllib.request
        import tempfile
        import os
        import shutil

        cached = cls._get_cached_downloaded_dataset('digits_full')
        if cached is not None:
            return cached

        # Create temp directory for UCI digits data
        temp_dir = tempfile.mkdtemp()

        try:
            # Download training and test files from UCI repository
            train_url = "https://archive.ics.uci.edu/ml/machine-learning-databases/optdigits/optdigits.tra"
            test_url = "https://archive.ics.uci.edu/ml/machine-learning-databases/optdigits/optdigits.tes"
            
            train_path = os.path.join(temp_dir, 'optdigits.tra')
            test_path = os.path.join(temp_dir, 'optdigits.tes')
            
            print(f"Downloading UCI digits training data from {train_url}...")
            urllib.request.urlretrieve(train_url, train_path)
            
            print(f"Downloading UCI digits test data from {test_url}...")
            urllib.request.urlretrieve(test_url, test_path)
            
            # Parse the files (65 comma-separated values: 64 features + 1 label)
            X_list = []
            y_list = []
            
            # Process both training and test files
            for file_path in [train_path, test_path]:
                with open(file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:  # Skip empty lines
                            values = [int(x) for x in line.split(',')]
                            if len(values) == 65:  # Ensure correct format
                                X_list.append(values[:64])  # First 64 are pixel features
                                y_list.append(values[64])   # Last value is the digit label
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            if len(X_list) == 0:
                raise ValueError("No valid data found in UCI digits files")
            
            X = np.array(X_list, dtype=np.float32)
            y = np.array(y_list, dtype=np.int32)
            
            print(f"Successfully loaded UCI digits dataset: {X.shape[0]} samples, {X.shape[1]} features")
            cls._store_downloaded_dataset('digits_full', X, y)
            return X, y
            
        except Exception as e:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise RuntimeError(f"Failed to load UCI digits dataset: {e}")

    @classmethod
    def _load_palmer_penguins(cls) -> Tuple[np.ndarray, np.ndarray]:
        """Load Palmer Penguins dataset from GitHub."""
        import urllib.request
        import tempfile
        import os
        import pandas as pd

        cached = cls._get_cached_downloaded_dataset('palmer_penguins')
        if cached is not None:
            return cached

        # Create temp directory for Palmer Penguins data
        temp_dir = tempfile.mkdtemp()
        csv_path = os.path.join(temp_dir, 'penguins.csv')

        try:
            # Download Palmer Penguins dataset from seaborn-data repository
            url = 'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv'
            print(f"Downloading Palmer Penguins dataset from {url}...")
            urllib.request.urlretrieve(url, csv_path)
            
            # Load CSV with pandas
            df = pd.read_csv(csv_path)
            
            # Remove rows with missing values
            df = df.dropna()
            
            # Prepare features (numerical columns)
            feature_columns = ['bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g']
            
            # Encode categorical features
            # Add sex as binary feature (0=FEMALE, 1=MALE)
            sex_encoded = df['sex'].map({'FEMALE': 0, 'MALE': 1}).fillna(0.5)  # Use 0.5 for any missing
            
            # Add island as one-hot encoded features
            island_dummies = pd.get_dummies(df['island'], prefix='island')
            
            # Combine all features
            X_df = df[feature_columns].copy()
            X_df['sex'] = sex_encoded
            X_df = pd.concat([X_df, island_dummies], axis=1)
            
            X = X_df.values.astype(np.float32)
            
            # Encode species as labels (0=Adelie, 1=Chinstrap, 2=Gentoo)
            species_map = {'Adelie': 0, 'Chinstrap': 1, 'Gentoo': 2}
            y = df['species'].map(species_map).values.astype(np.int32)
            
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir)
            
            print(f"Successfully loaded Palmer Penguins dataset: {X.shape[0]} samples, {X.shape[1]} features")
            print(f"Features: {list(X_df.columns)}")
            print(f"Species distribution: {np.bincount(y)}")

            cls._store_downloaded_dataset('palmer_penguins', X, y)
            return X, y
            
        except Exception as e:
            # Clean up temp directory
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
            raise RuntimeError(f"Failed to load Palmer Penguins dataset: {e}")

    @classmethod
    def _load_lfw_faces(cls) -> Tuple[np.ndarray, np.ndarray]:
        """Load Labeled Faces in the Wild dataset (grayscale)."""
        if cls._lfw_cache is not None:
            return cls._lfw_cache

        cached = cls._get_cached_downloaded_dataset('lfw_faces')
        if cached is not None:
            cls._lfw_cache = cached
            return cached

        data = fetch_lfw_people(min_faces_per_person=10, resize=1.0, color=False)
        images = data.images  # (n_samples, 62, 47)
        X = images.reshape(images.shape[0], -1).astype(np.float32)
        y = data.target.astype(np.int32)

        cls._lfw_cache = (X, y)
        cls._store_downloaded_dataset('lfw_faces', X, y)
        return X, y

    @classmethod
    def _read_idx_file(cls, path: str, expected_header: int) -> np.ndarray:
        """Read IDX formatted file (used for MNIST datasets)."""
        with gzip.open(path, 'rb') as f:
            header = f.read(4)
            if len(header) != 4:
                raise ValueError("Invalid IDX file header")
            magic = struct.unpack('>I', header)[0]
            if magic >> 8 != expected_header:
                raise ValueError(f"Unexpected IDX magic number: {magic}")
            dimensions = magic & 0xFF
            shape = [struct.unpack('>I', f.read(4))[0] for _ in range(dimensions)]
            data = np.frombuffer(f.read(), dtype=np.uint8)
            return data.reshape(shape)

    @classmethod
    def _load_fashion_mnist(cls) -> Tuple[np.ndarray, np.ndarray]:
        """Download and load Fashion-MNIST dataset (train split)."""
        if cls._fashion_mnist_cache is not None:
            return cls._fashion_mnist_cache

        cached = cls._get_cached_downloaded_dataset('fashion_mnist')
        if cached is not None:
            cls._fashion_mnist_cache = cached
            return cached

        base_url = "https://storage.googleapis.com/tensorflow/tf-keras-datasets/"
        files = {
            'images': 'train-images-idx3-ubyte.gz',
            'labels': 'train-labels-idx1-ubyte.gz',
        }

        temp_dir = tempfile.mkdtemp()
        try:
            local_paths = {}
            for key, filename in files.items():
                url = base_url + filename
                local_path = os.path.join(temp_dir, filename)
                urllib.request.urlretrieve(url, local_path)
                local_paths[key] = local_path

            images = cls._read_idx_file(local_paths['images'], expected_header=0x000008)
            labels = cls._read_idx_file(local_paths['labels'], expected_header=0x000008)

            # Ensure we only use up to 10000 samples to keep dataset lightweight
            limit = min(10000, images.shape[0])
            images = images[:limit]
            labels = labels[:limit]

            X = images.reshape(limit, -1).astype(np.float32)
            y = labels.astype(np.int32)

            cls._fashion_mnist_cache = (X, y)
            cls._store_downloaded_dataset('fashion_mnist', X, y)
            return X, y
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _load_sign_language_digits(cls) -> Tuple[np.ndarray, np.ndarray]:
        """Load American Sign Language digit dataset from GitHub."""
        if cls._sign_language_cache is not None:
            return cls._sign_language_cache

        cached = cls._get_cached_downloaded_dataset('sign_language_digits')
        if cached is not None:
            cls._sign_language_cache = cached
            return cached

        url = "https://github.com/ardamavi/Sign-Language-Digits-Dataset/archive/refs/heads/master.zip"
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "sign-language-digits.zip")

        try:
            urllib.request.urlretrieve(url, zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            dataset_root = None
            for candidate in os.listdir(temp_dir):
                if candidate.lower().startswith('sign-language-digits-dataset'):
                    dataset_root = os.path.join(temp_dir, candidate, 'Dataset')
                    break

            if dataset_root is None or not os.path.isdir(dataset_root):
                raise RuntimeError("Unexpected archive structure for sign language dataset")

            images = []
            labels = []

            digit_folders = sorted([d for d in os.listdir(dataset_root) if d.isdigit()])
            for digit in digit_folders:
                digit_dir = os.path.join(dataset_root, digit)
                file_paths = sorted(
                    os.path.join(digit_dir, f)
                    for f in os.listdir(digit_dir)
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))
                )

                for img_path in file_paths:
                    img = Image.open(img_path).convert('L').resize((64, 64))
                    images.append(np.array(img, dtype=np.uint8).flatten())
                    labels.append(int(digit))

            if not images:
                raise RuntimeError("No images found in sign language dataset")

            X = np.array(images, dtype=np.float32)
            y = np.array(labels, dtype=np.int32)

            cls._sign_language_cache = (X, y)
            cls._store_downloaded_dataset('sign_language_digits', X, y)
            return X, y
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _generate_real_world(cls, dataset_name: str, n_samples: int, 
                           random_state: int, **kwargs) -> Tuple[np.ndarray, np.ndarray]:
        """Generate real-world datasets from sklearn."""
        
        if dataset_name == 'iris':
            data = load_iris()
            X, y = data.data, data.target
            
        elif dataset_name == 'wine':
            data = load_wine()
            X, y = data.data, data.target
            
        elif dataset_name == 'breast_cancer':
            data = load_breast_cancer()
            X, y = data.data, data.target
            
        elif dataset_name == 'digits_small':
            data = load_digits()
            X, y = data.data, data.target
            
        elif dataset_name == 'coil20':
            X, y = cls._load_coil20()
            
        elif dataset_name == 'olivetti_faces':
            data = fetch_olivetti_faces()
            X, y = data.data, data.target
            
        elif dataset_name == 'digits_full':
            # Load full UCI digits dataset (5620 samples)
            X, y = cls._load_digits_full()
            
        elif dataset_name == 'california_housing':
            data = fetch_california_housing()
            X, y = data.data, data.target
            
        elif dataset_name == 'diabetes':
            from sklearn.datasets import load_diabetes
            data = load_diabetes()
            X, y = data.data, data.target
            
        elif dataset_name == 'palmer_penguins':
            X, y = cls._load_palmer_penguins()

        elif dataset_name == 'lfw_faces':
            X, y = cls._load_lfw_faces()

        elif dataset_name == 'fashion_mnist':
            X, y = cls._load_fashion_mnist()

        elif dataset_name == 'sign_language_digits':
            X, y = cls._load_sign_language_digits()
        
        elif dataset_name == 'dataset_2':
            X, y = cls._load_fashion_mnist()
            # dataset_2 is a subset of fashion_mnist: only first 5000 samples
            X, y = X[:5000], y[:5000]

        elif dataset_name == 'dataset_1':
            data = load_wine()
            X, y = data.data, data.target

        elif dataset_name == 'wheats':
            from clustpy.data import load_wheat
            X, y = load_wheat(return_X_y=True)

        elif dataset_name == 'olive_oil':
            import pandas as pd
            url = 'https://raw.githubusercontent.com/rafalab/dslabs/master/inst/extdata/olive.csv'
            df = pd.read_csv(url)
            feature_cols = ['palmitic', 'palmitoleic', 'stearic', 'oleic', 'linoleic', 'linolenic', 'arachidic', 'eicosenoic']
            X = df[feature_cols].values.astype(np.float64)
            y = df['Region'].values  # 3 regions (use Region as ground truth)

        elif dataset_name == 'zoo':
            from sklearn.datasets import fetch_openml
            import pandas as pd
            zoo = fetch_openml(name='zoo', version=1, as_frame=True, parser='auto')
            df = zoo.data.copy()
            # Convert categorical boolean columns to numeric (true/false -> 1/0)
            for col in df.columns:
                if df[col].dtype.name == 'category':
                    df[col] = df[col].astype(str).map({'true': 1, 'false': 0, 'True': 1, 'False': 0}).fillna(
                        pd.to_numeric(df[col].astype(str), errors='coerce')
                    )
            X = df.values.astype(np.float64)
            # Convert categorical target to numeric labels
            target_map = {name: i for i, name in enumerate(sorted(zoo.target.unique()))}
            y = np.array([target_map[t] for t in zoo.target])

        else:
            raise ValueError(f"Unknown real-world dataset: {dataset_name}")
        
        # Standardize real-world datasets, but skip datasets that are already on a
        # meaningful scale: raw image pixels.
        no_standardize = {'lfw_faces', 'fashion_mnist', 'sign_language_digits', 'dataset_2'}
        if dataset_name not in no_standardize:
            scaler = StandardScaler()
            X = scaler.fit_transform(X)
        else:
            X = X.astype(np.float32)
        
        # Subsample if requested
        if n_samples < len(X):
            rng = np.random.RandomState(random_state)
            indices = rng.choice(len(X), n_samples, replace=False)
            X = X[indices]
            y = y[indices]
        
        return X, y

    @classmethod
    def get_recommended_params(cls, dataset_name: str) -> Dict[str, Any]:
        """Get recommended parameters for a dataset."""
        info = cls.get_dataset_info(dataset_name)
        if not info:
            return {}
        
        recommendations = {
            'n_samples': info.typical_samples,
            'description': info.description,
            'difficulty': info.difficulty,
            'category': info.category.value
        }
        
        # Category-specific recommendations
        if info.category == DatasetCategory.REAL_WORLD:
            recommendations.update({
                'min_points': 5,
                'min_cluster_size': 10,
                'tree_type': 'DCTree',
                'partition_method': 'Elbow'
            })
        elif info.difficulty == 'hard':
            recommendations.update({
                'min_points': 3,
                'min_cluster_size': 5,
                'tree_type': 'SLTree',
                'partition_method': 'Manual'
            })
        else:
            recommendations.update({
                'min_points': 5,
                'min_cluster_size': 8,
                'tree_type': 'DCTree',
                'partition_method': 'Elbow'
            })
            
        # Special handling for diabetes dataset
        if dataset_name == 'diabetes':
            recommendations.update({
                'difficulty': 'medium',
                'min_points': 5,
                'min_cluster_size': 8,
                'tree_type': 'DCTree',
                'partition_method': 'Elbow'
            })
        
        return recommendations
