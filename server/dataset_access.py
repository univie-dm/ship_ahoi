from typing import Any, Dict, Optional
import numpy as np

from .ship_cache_service import SHiPCacheService
from .redis_service import redis_service


def get_dataset_data(dataset_id: str):
    """Retrieve dataset data from toy datasets, in-memory storage, SHiP cache, or Redis.

    Returns a NumPy array or None if not found/convertible.
    """
    try:
        # Try toy dataset service mapping
        from .toy_dataset_service import ToyDatasetService
        dataset_aliases = {
            'digits_full': 'digits_full',
            'digits': 'digits',
            'iris': 'iris',
            'wine': 'wine',
            'breast_cancer': 'breast_cancer',
            'blobs': 'blobs',
            'circles': 'circles',
            'moons': 'moons',
            'wheats': 'wheats',
            'olive_oil': 'olive_oil',
            'zoo': 'zoo'
        }
        toy_dataset_name = dataset_aliases.get(dataset_id, dataset_id)

        # 1) SHiP cache: clustering result (if available)
        try:
            if hasattr(SHiPCacheService, 'get_cluster_result'):
                cluster_result = SHiPCacheService.get_cluster_result(dataset_id)
                if cluster_result and isinstance(cluster_result, dict):
                    data = cluster_result.get('data') or cluster_result.get('points')
                    if data is not None:
                        try:
                            return np.array(data, dtype=float)
                        except (ValueError, TypeError):
                            pass
        except Exception:
            pass

        # 2) Toy dataset service
        try:
            toy_data = ToyDatasetService.get_dataset(toy_dataset_name)
            if toy_data and isinstance(toy_data, dict) and 'data' in toy_data:
                return np.array(toy_data['data'], dtype=float)
        except Exception:
            pass

        # 3) Redis database storage
        try:
            dataset = redis_service.get_dataset(dataset_id)
            if dataset and hasattr(dataset, 'processed_data') and dataset.processed_data:
                try:
                    pd = dataset.processed_data
                    if isinstance(pd, dict) and 'data' in pd:
                        return np.array(pd['data'], dtype=float)
                    if hasattr(pd, 'data'):
                        return np.array(pd.data, dtype=float)
                except (ValueError, TypeError):
                    pass
            if dataset and hasattr(dataset, 'data') and dataset.data:
                try:
                    return np.array(dataset.data, dtype=float)
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass

        return None
    except Exception:
        return None

