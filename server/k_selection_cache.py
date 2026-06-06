import time
from typing import Any, Dict, Tuple, Optional


# Global storage for k-selection data cache (for high-dimensional datasets)
k_selection_data_cache: Dict[str, Any] = {}


def cleanup_k_selection_cache() -> None:
    """Remove k-selection data cache entries older than 2 hours and corrupted entries."""
    current_time = time.time()
    expired_keys = [
        key for key, entry in k_selection_data_cache.items()
        if not isinstance(entry, dict) or current_time - entry.get('created_at', 0) > 7200
    ]

    corrupted_keys = []
    for key, entry in k_selection_data_cache.items():
        if key in expired_keys:
            continue
        try:
            if not isinstance(entry, dict):
                corrupted_keys.append(key)
                continue
            required_fields = ['data', 'created_at', 'dataset_info']
            if not all(field in entry for field in required_fields):
                corrupted_keys.append(key)
                continue
            data = entry['data']
            if not hasattr(data, 'shape') or not hasattr(data, 'dtype'):
                corrupted_keys.append(key)
                continue
            if getattr(data, 'size', 0) == 0:
                corrupted_keys.append(key)
                continue
        except Exception:
            corrupted_keys.append(key)

    for key in expired_keys + corrupted_keys:
        try:
            del k_selection_data_cache[key]
        except KeyError:
            pass


def validate_cache_entry(cache_id: str) -> bool:
    """Validate that a cache entry exists and is accessible."""
    if not cache_id or cache_id not in k_selection_data_cache:
        return False
    try:
        entry = k_selection_data_cache[cache_id]
        if not isinstance(entry, dict):
            return False
        required_fields = ['data', 'created_at', 'dataset_info']
        if not all(field in entry for field in required_fields):
            return False
        data = entry['data']
        if not hasattr(data, 'shape') or not hasattr(data, 'dtype'):
            return False
        if getattr(data, 'size', 0) == 0:
            return False
        if len(getattr(data, 'shape', ())) != 2 or data.shape[0] == 0 or data.shape[1] == 0:
            return False
        dataset_info = entry.get('dataset_info')
        if not isinstance(dataset_info, dict) or 'shape' not in dataset_info:
            return False
        return True
    except Exception:
        return False


def get_cached_data_with_fallback(cache_id: str, tree_type: Optional[str] = None, power: Optional[float] = None) -> Tuple[Optional[Any], Optional[Any], bool]:
    """Get cached data with intelligent fallback mechanisms.

    Returns: (data, pca_components, found_exact_match)
    """
    if not cache_id:
        return None, None, False

    if cache_id in k_selection_data_cache and validate_cache_entry(cache_id):
        entry = k_selection_data_cache[cache_id]
        return entry['data'], entry.get('pca_components'), True

    if tree_type is not None and power is not None:
        for fallback_key, entry in k_selection_data_cache.items():
            if not validate_cache_entry(fallback_key):
                continue
            dataset_info = entry.get('dataset_info', {})
            if (dataset_info.get('tree_type') == tree_type and dataset_info.get('power') == power):
                return entry['data'], entry.get('pca_components'), False

    if len(k_selection_data_cache) > 0:
        valid_entries = [(key, entry) for key, entry in k_selection_data_cache.items() if validate_cache_entry(key)]
        if valid_entries:
            valid_entries.sort(key=lambda x: x[1]['created_at'], reverse=True)
            key, entry = valid_entries[0]
            return entry['data'], entry.get('pca_components'), False

    return None, None, False

