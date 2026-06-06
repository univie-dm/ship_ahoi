from fastapi import FastAPI, Response, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response as PlainResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import math
import gzip
import io
from .clustering_service import (
    ClusterParams,
    ClusteringService,
    ClusteringAnalysisService,
)
from .cluster_color_helper import ClusterColorHelper
from .k_selection_service import KSelectionService
from .ship_cache_service import SHiPCacheService
from .ship_exceptions import SHiPTreeGenerationError
from .file_upload_service import FileUploadService
from .data_processing_service import DataProcessingService
from .umap_optimization_service import UMAPOptimizationService
from .tsne_optimization_service import TSNEOptimizationService
from .cluster_params import (
    FileParseResponse, DataProcessingConfig, DataProcessRequest, 
    DataProcessResponse, DataPreviewRequest, DataPreviewResponse,
    DataAnalysisResponse, ErrorResponse, ProgressResponse
)
from .redis_service import redis_service, initialize_database, shutdown_database
from .history_api import router as history_router
from .image_api import router as image_router
from .study_session_api import router as study_session_router
from .models import (
    DatasetCreate, DatasetUpdate, 
    ClusteringResultCreate, ClusteringResultUpdate, ClusteringStatus,
    DimensionalityReductionResultCreate, DimensionalityReductionResultUpdate, DRMethod, DRStatus,
    KSelectionCacheCreate
)
from fastapi.encoders import jsonable_encoder
import json
import copy
import time
import uuid
import logging
import numpy as np
import threading
import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import multiprocessing
import psutil
import signal
import os
import queue
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from .k_selection_cache import (
    k_selection_data_cache,
    cleanup_k_selection_cache,
    get_cached_data_with_fallback,
)
from .models.api_requests import (
    ClusterRequest,
    KSelectionRequest,
    ClusterVisualizationRequest,
    ClusteringAnalysisRequest,
    DatasetInsightsRequest,
    ClusterSummaryRequest,
    FeatureImportanceRequest,
    FeatureImportanceDatasetRequest,
    FeatureStatisticsRequest,
    CorrelationMatrixRequest,
    DatasetAnalysisRequest,
    FeatureDistributionRequest,
)
from .dataset_access import get_dataset_data as _get_dataset_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder for FastAPI to handle numpy types and NaN/Inf
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            float_val = float(obj)
            # Replace NaN and Inf with None
            if math.isnan(float_val) or math.isinf(float_val):
                return None
            return float_val
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)

app = FastAPI()

def custom_jsonable_encoder(obj, _depth=0, _max_depth=1000):
    """Custom encoder that handles numpy types and NaN/Inf properly with recursion depth limit"""
    # Prevent infinite recursion
    if _depth > _max_depth:
        logger.warning(f"[Encoder] Max depth {_max_depth} reached, truncating")
        return None
    
    if obj is None:
        return None
    elif isinstance(obj, str):
        # Ensure strings are properly handled (FastAPI will escape them)
        return obj
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, np.ndarray):
        return custom_jsonable_encoder(obj.tolist(), _depth + 1, _max_depth)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        float_val = float(obj)
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        return float_val
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, dict):
        return {k: custom_jsonable_encoder(v, _depth + 1, _max_depth) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [custom_jsonable_encoder(item, _depth + 1, _max_depth) for item in obj]
    else:
        # For unknown types, convert to string safely
        try:
            return str(obj)
        except:
            return None

# Include routers
app.include_router(history_router)
app.include_router(image_router, prefix="/api")
app.include_router(study_session_router, prefix="/api")

# CORS configuration - Restrictive since backend is now proxied through Nuxt server
# Only allow requests from the frontend server (not direct client access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://frontend:3000",    # Docker container
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database and process pools during application startup"""
    initialize_database()
    
    # Initialize and warm up process pools on startup instead of lazily
    logger.info("Initializing process pools on startup...")
    initialize_clustering_pool()
    initialize_dr_pool()
    
    # Start memory monitoring
    start_memory_monitoring()
    
    # Clear database on startup
    redis_service.clear_database()

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown database connection during application shutdown"""
    global clustering_pool_executor, dr_pool_executor
    
    # Shutdown clustering process pool
    if clustering_pool_executor:
        logger.info("[MemoryOpt] Shutting down clustering process pool...")
        clustering_pool_executor.shutdown(wait=True)
        clustering_pool_executor = None
    
    # Shutdown dimensionality reduction process pool
    if dr_pool_executor:
        logger.info("[MemoryOpt] Shutting down DR process pool...")
        dr_pool_executor.shutdown(wait=True)
        dr_pool_executor = None
    
    # Clear all caches
    try:
        SHiPCacheService.clear_cache()
        UMAPOptimizationService.clear_cache()
        TSNEOptimizationService.clear_cache()
    except:
        pass
    
    shutdown_database()

# Global storage for uploaded files (in production, use a proper database)
file_storage: Dict[str, Any] = {}

# Global storage for clustering results and background dimensionality reduction tasks
cluster_results: Dict[str, Any] = {}
dimensionality_reduction_tasks: Dict[str, Any] = {}

# Database-backed storage helper

class DatasetRepository:
    """Thin orchestrator for dataset and clustering result persistence."""

    def __init__(self, redis_client, file_cache: Dict[str, Any], result_cache: Dict[str, Any]):
        self._redis = redis_client
        self._file_cache = file_cache
        self._result_cache = result_cache

    async def get_dataset_data(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset data from database with fallback to in-memory storage."""
        dataset = self._redis.get_dataset(file_id)
        if dataset and dataset.processed_data:
            return dataset.processed_data

        if file_id in self._file_cache:
            stored = self._file_cache[file_id]
            return stored.get("processed_data") or stored.get("parsed_data")

        return None

    async def store_clustering_result(
        self,
        operation_id: str,
        cluster_id: str,
        result: Dict[str, Any],
        data: Dict[str, Any],
    ) -> None:
        """Persist clustering results with in-memory fallback on Redis failure."""
        try:
            clustering_result = ClusteringResultCreate(
                operation_id=operation_id,
                cluster_id=cluster_id,
                result=result,
                data=data,
                status=ClusteringStatus.COMPLETED,
            )
            self._redis.create_clustering_result(clustering_result)
        except Exception as exc:
            logger.error(f"Failed to store clustering result in database: {exc}")
            self._result_cache[cluster_id] = {
                "result": result,
                "data": data,
                "operation_id": operation_id,
                "timestamp": time.time(),
            }

    async def get_clustering_result(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Fetch clustering result from Redis with in-memory fallback."""
        result = self._redis.get_clustering_result(cluster_id)
        if result:
            return {
                "result": result.result,
                "data": result.data,
                "operation_id": result.operation_id,
                "timestamp": result.created_at.timestamp(),
            }

        if cluster_id in self._result_cache:
            return self._result_cache[cluster_id]

        return None


dataset_repository = DatasetRepository(redis_service, file_storage, cluster_results)

# Global storage for active processes (for abort functionality)
active_processes: Dict[str, multiprocessing.Process] = {}

def clustering_worker(params_dict: dict, operation_id: str, settings_dict: dict = None):
    """Worker function to run clustering in a separate process"""
    data = None
    ship = None
    result = None
    
    try:
        import numpy as np
        import gc
        from .cluster_params import ClusterParams, AppSettings
        req = ClusterParams(**params_dict)
        
        # Reconstruct settings from dict if provided
        app_settings = None
        if settings_dict:
            app_settings = AppSettings(**settings_dict)
        
        try:
            result = ClusteringService.cluster_data_sync(req, app_settings)
        except SHiPTreeGenerationError as ship_error:
            # Return structured error response for SHiP tree generation failures  
            return {
                "success": False,
                "error": ship_error.to_dict()
            }
            
        cluster_id = str(uuid.uuid4())
        result['cluster_id'] = cluster_id
        result['operation_id'] = operation_id
        
        # Note: Don't store toy dataset data here as this runs in a separate process
        # The file_storage modified here won't be visible to the main process
        dataset_id = params_dict.get('fileId') or req.sample
        
        return_value = {
            "success": True,
            "result": result,
            "cluster_id": cluster_id,
            "should_start_background": True,
            "params": {
                'treeType': req.treeType,
                'partitioningMethod': req.partitioningMethod,
                'n_clusters': req.n_clusters,
                'power': req.power,
                'sample': req.sample,
                'dataset_id': dataset_id
            }
        }
        
        # Explicit cleanup before return to prevent memory leaks
        if 'data' in locals():
            del data
        if 'ship' in locals():
            del ship
        # Don't delete result as we need to return it
        
        gc.collect()
        return return_value
        
    except Exception as e:
        logger.error(f"Clustering process {operation_id} failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Force cleanup of large objects
        try:
            if data is not None:
                del data
            if ship is not None:
                del ship
            # Keep result for return value
            import gc
            gc.collect()
        except:
            pass  # Ignore cleanup errors

def k_selection_worker(params_dict: dict, operation_id: str):
    """Worker function to run k-selection analysis in a separate process"""
    data = None
    result = None
    
    try:
        import gc
        result = KSelectionService.analyze_k_values(params_dict)
        
        return_value = {"success": True, "result": result}
        
        # Explicit cleanup before return to prevent memory leaks
        if 'data' in locals():
            del data
        gc.collect()
        
        return return_value
        
    except Exception as e:
        logger.error(f"K-Selection process {operation_id} failed: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Force cleanup
        try:
            if data is not None:
                del data
            # Keep result for return value
            import gc
            gc.collect()
        except:
            pass  # Ignore cleanup errors

    # k-selection cache utilities are imported from server.k_selection_cache

# Global cache for dataset-level dimensionality reduction (UMAP/t-SNE computed once per dataset)
dataset_dr_cache: Dict[str, Any] = {}

def cleanup_dataset_dr_cache():
    """Remove dataset DR cache entries older than 1 hour to prevent memory leaks"""
    current_time = time.time()
    expired_keys = [
        key for key, entry in dataset_dr_cache.items()
        if current_time - entry['created_at'] > 3600  # 1 hour
    ]
    for key in expired_keys:
        del dataset_dr_cache[key]
    if expired_keys:
        print(f"[Cache] Cleaned up {len(expired_keys)} expired dataset DR cache entries")

# Process pool for CPU-bound tasks
# Memory-optimized multiprocessing settings
def get_optimal_worker_count() -> int:
    """Calculate optimal number of workers based on available memory and CPU"""
    try:
        available_memory_gb = psutil.virtual_memory().available / (1024**3)
        cpu_count = multiprocessing.cpu_count()
        
        # Estimate 0.8GB per worker process for safety (more conservative)
        memory_based_limit = max(1, int(available_memory_gb / 0.8))
        
        # Use the minimum of CPU count and memory-based limit, cap at 4 for better performance
        optimal_count = min(cpu_count, memory_based_limit, 4)
        
        logger.info(f"[MemoryOpt] Available memory: {available_memory_gb:.1f}GB, "
                    f"CPU cores: {cpu_count}, optimal workers: {optimal_count}")
        
        return optimal_count
    except Exception as e:
        logger.warning(f"[MemoryOpt] Error calculating optimal workers: {e}, using 4")
        return 4

# Use memory-optimized worker count
num_cores = get_optimal_worker_count()

# Memory monitoring utilities
class MemoryMonitor:
    @staticmethod
    def get_memory_usage():
        try:
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # MB
        except:
            return 0
    
    @staticmethod
    def force_cleanup():
        """Force garbage collection and memory cleanup"""
        import gc
        before = MemoryMonitor.get_memory_usage()
        collected = gc.collect()
        after = MemoryMonitor.get_memory_usage()
        freed = before - after
        if freed > 10:  # Only log if significant memory was freed
            logger.info(f"[MemoryOpt] GC freed {freed:.1f}MB, collected {collected} objects")
        return freed

memory_monitor = MemoryMonitor()


def _psutil_process(pid: int):
    try:
        return psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _format_process_memory(ps_proc: psutil.Process, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        rss_mb = ps_proc.memory_info().rss / (1024 * 1024)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {}

    payload = {
        "pid": ps_proc.pid,
        "rss_mb": round(rss_mb, 2),
    }

    try:
        payload["name"] = ps_proc.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    try:
        payload["status"] = ps_proc.status()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    if extra:
        payload.update(extra)

    return payload


def _gather_pool_memory(executor, label: str) -> Dict[str, Any]:
    details: List[Dict[str, Any]] = []
    total_mb = 0.0

    if executor and hasattr(executor, "_processes"):
        for proc_obj in list(executor._processes.values()):
            pid = getattr(proc_obj, "pid", None)
            if not pid:
                continue
            ps_proc = _psutil_process(pid)
            if not ps_proc:
                continue
            info = _format_process_memory(ps_proc)
            if not info:
                continue
            total_mb += info["rss_mb"]
            details.append(info)

    return {
        "label": label,
        "total_mb": round(total_mb, 2),
        "processes": details,
    }


def _gather_legacy_process_memory() -> Dict[str, Any]:
    details: List[Dict[str, Any]] = []
    total_mb = 0.0

    for operation_id, proc in list(active_processes.items()):
        pid = getattr(proc, "pid", None)
        if not pid:
            continue
        ps_proc = _psutil_process(pid)
        if not ps_proc:
            continue
        info = _format_process_memory(ps_proc, {"operation_id": operation_id})
        if not info:
            continue
        total_mb += info["rss_mb"]
        details.append(info)

    return {
        "label": "legacy_processes",
        "total_mb": round(total_mb, 2),
        "processes": details,
    }

# Enhanced memory management
def periodic_memory_cleanup():
    """Periodic cleanup to prevent memory accumulation"""
    try:
        current_usage = memory_monitor.get_memory_usage()
        if current_usage > 1500:  # 1.5GB threshold
            logger.info(f"[MemoryOpt] High memory usage detected: {current_usage:.1f}MB, triggering cleanup")
            
            # Clear various caches
            try:
                SHiPCacheService.clear_cache()
            except:
                pass
            
            try:
                UMAPOptimizationService.clear_cache()
            except:
                pass
            
            try:
                TSNEOptimizationService.clear_cache()
            except:
                pass
            
            # Force garbage collection
            freed = memory_monitor.force_cleanup()
            logger.info(f"[MemoryOpt] Cleanup completed, freed {freed:.1f}MB")
            
    except Exception as e:
        logger.warning(f"[MemoryOpt] Error in periodic cleanup: {e}")

# Schedule periodic cleanup
import threading
def start_memory_monitoring():
    def cleanup_loop():
        while True:
            try:
                time.sleep(600*6)  # Every 10 minutes - less frequent cleanup
                periodic_memory_cleanup()
            except Exception as e:
                logger.error(f"[MemoryOpt] Error in cleanup loop: {e}")
                time.sleep(600)  # Wait longer on error
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    logger.info("[MemoryOpt] Started memory monitoring thread")

# Global process pool variables - separate pools for different task types
clustering_pool_executor = None  # High priority pool for clustering operations
dr_pool_executor = None         # Background pool for dimensionality reduction

# Worker management and status tracking
import threading
from dataclasses import dataclass
from typing import Set
import weakref

@dataclass
class WorkerStatus:
    """Status tracking for worker processes"""
    worker_id: str
    last_activity: float
    is_busy: bool = False
    active_operations: Set[str] = None
    
    def __post_init__(self):
        if self.active_operations is None:
            self.active_operations = set()

# Global worker tracking - separate tracking for each pool
worker_status_lock = threading.RLock()
clustering_worker_statuses = {}
dr_worker_statuses = {}
worker_cleanup_thread = None
WORKER_IDLE_TIMEOUT = 6000  # 10 minutes
pool_reset_lock = threading.RLock()


def reset_clustering_pool(reason: str = "unknown") -> None:
    """Safely dispose of the clustering pool so a fresh one can be created."""
    global clustering_pool_executor

    with pool_reset_lock:
        if clustering_pool_executor is not None:
            try:
                clustering_pool_executor.shutdown(wait=False, cancel_futures=True)  # type: ignore[arg-type]
            except TypeError:
                # `cancel_futures` not available on older Python versions
                clustering_pool_executor.shutdown(wait=False)
            except Exception as exc:
                logger.warning(f"[PoolReset] Error shutting down clustering pool: {exc}")
            finally:
                clustering_pool_executor = None

        with worker_status_lock:
            clustering_worker_statuses.clear()

        logger.info(f"[PoolReset] Clustering pool reset (reason: {reason})")


def reset_dr_pool(reason: str = "unknown") -> None:
    """Safely dispose of the DR pool so a fresh one can be created."""
    global dr_pool_executor

    with pool_reset_lock:
        if dr_pool_executor is not None:
            try:
                dr_pool_executor.shutdown(wait=False, cancel_futures=True)  # type: ignore[arg-type]
            except TypeError:
                dr_pool_executor.shutdown(wait=False)
            except Exception as exc:
                logger.warning(f"[PoolReset] Error shutting down DR pool: {exc}")
            finally:
                dr_pool_executor = None

        with worker_status_lock:
            dr_worker_statuses.clear()

        with active_dr_lock:
            active_dr_operations.clear()

        logger.info(f"[PoolReset] DR pool reset (reason: {reason})")

# Active DR tracking for cancellation
active_dr_operations = {}  # cluster_id -> future
active_dr_lock = threading.RLock()

def cancel_dr_for_cluster(cluster_id: str):
    """Cancel any ongoing DR operation for a specific cluster"""
    with active_dr_lock:
        if cluster_id in active_dr_operations:
            future = active_dr_operations[cluster_id]
            if not future.done():
                logger.info(f"[DR Cancel] Cancelling DR operation for cluster {cluster_id}")
                if future.cancel():
                    logger.info(f"[DR Cancel] Successfully cancelled DR for cluster {cluster_id}")
                else:
                    logger.warning(f"[DR Cancel] Could not cancel DR for cluster {cluster_id} (already running)")
            del active_dr_operations[cluster_id]

def cancel_old_dr_operations(keep_recent_count: int = 2):
    """Cancel DR operations for old clusters, keeping only the most recent ones"""
    with active_dr_lock:
        if len(active_dr_operations) <= keep_recent_count:
            return
        
        # Sort by cluster_id (assuming timestamp-based IDs) to identify oldest
        cluster_ids = sorted(active_dr_operations.keys())
        old_cluster_ids = cluster_ids[:-keep_recent_count]
        
        cancelled_count = 0
        for cluster_id in old_cluster_ids:
            future = active_dr_operations.get(cluster_id)
            if future and not future.done():
                if future.cancel():
                    cancelled_count += 1
                    logger.info(f"[DR Cancel] Cancelled old DR operation for cluster {cluster_id}")
            active_dr_operations.pop(cluster_id, None)
        
        if cancelled_count > 0:
            logger.info(f"[DR Cancel] Cancelled {cancelled_count} old DR operations to free workers")

def _prewarm_dummy_task():
    """Comprehensive dummy task that imports all heavy dependencies to warm up worker process"""
    import time
    start_time = time.time()
    
    # Import all heavy dependencies to warm up the worker process
    try:
        # Import clustering services which trigger heavy dependency loading
        from .clustering_service import ClusteringService
        from .k_selection_service import KSelectionService
        from .ship_cache_service import SHiPCacheService
        
        # Trigger DISCO import path setup
        import sys, os
        PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        DISCO_SRC_PATH = os.path.join(PROJECT_ROOT, 'DISCO-main', 'src')
        if DISCO_SRC_PATH not in sys.path:
            sys.path.append(DISCO_SRC_PATH)
        
        # Try to import DISCO to trigger the heavy loading
        try:
            from Evaluation.disco import disco_score
            disco_available = True
        except:
            disco_available = False
        
        end_time = time.time()
        import_time = end_time - start_time
        
        return f"worker_ready_imports_{import_time:.3f}s_disco_{disco_available}"
        
    except Exception as e:
        end_time = time.time()
        import_time = end_time - start_time
        return f"worker_ready_partial_{import_time:.3f}s_error_{str(e)[:50]}"

def track_worker_activity(operation_id: str, future: concurrent.futures.Future, pool_type: str = "clustering"):
    """Track worker activity for idle detection"""
    global clustering_worker_statuses, dr_worker_statuses
    
    worker_statuses = clustering_worker_statuses if pool_type == "clustering" else dr_worker_statuses
    
    with worker_status_lock:
        # Find which worker is handling this operation
        worker_id = id(future)  # Use future ID as worker identifier
        current_time = time.time()
        
        if worker_id not in worker_statuses:
            worker_statuses[worker_id] = WorkerStatus(
                worker_id=str(worker_id),
                last_activity=current_time,
                is_busy=True
            )
        
        worker_status = worker_statuses[worker_id]
        worker_status.last_activity = current_time
        worker_status.is_busy = True
        worker_status.active_operations.add(operation_id)
        
        logger.debug(f"[WorkerTracker] {pool_type} worker {worker_id} started operation {operation_id}")

def mark_worker_idle(operation_id: str, future: concurrent.futures.Future, pool_type: str = "clustering"):
    """Mark worker as idle when operation completes"""
    global clustering_worker_statuses, dr_worker_statuses
    
    worker_statuses = clustering_worker_statuses if pool_type == "clustering" else dr_worker_statuses
    
    with worker_status_lock:
        worker_id = id(future)
        current_time = time.time()
        
        if worker_id in worker_statuses:
            worker_status = worker_statuses[worker_id]
            worker_status.active_operations.discard(operation_id)
            worker_status.last_activity = current_time
            
            # Mark as idle if no active operations
            if not worker_status.active_operations:
                worker_status.is_busy = False
                logger.debug(f"[WorkerTracker] {pool_type} worker {worker_id} completed operation {operation_id}, now idle")

def cleanup_idle_workers():
    """Clean up idle workers that haven't been used recently"""
    global clustering_pool_executor, dr_pool_executor, clustering_worker_statuses, dr_worker_statuses
    
    current_time = time.time()
    
    # Clean up clustering workers
    if clustering_pool_executor is not None:
        workers_to_remove = []
        
        with worker_status_lock:
            for worker_id, status in clustering_worker_statuses.items():
                if (not status.is_busy and 
                    not status.active_operations and 
                    current_time - status.last_activity > WORKER_IDLE_TIMEOUT):
                    workers_to_remove.append(worker_id)
            
            for worker_id in workers_to_remove:
                del clustering_worker_statuses[worker_id]
        
        if workers_to_remove:
            logger.info(f"[WorkerTracker] Found {len(workers_to_remove)} idle clustering workers to clean up")
            try:
                old_executor = clustering_pool_executor
                clustering_pool_executor = None
                old_executor.shutdown(wait=False)
                logger.info(f"[WorkerTracker] Cleaned up {len(workers_to_remove)} clustering workers")
            except Exception as e:
                logger.error(f"[WorkerTracker] Error during clustering worker cleanup: {e}")
    
    # Clean up DR workers
    if dr_pool_executor is not None:
        workers_to_remove = []
        
        with worker_status_lock:
            for worker_id, status in dr_worker_statuses.items():
                if (not status.is_busy and 
                    not status.active_operations and 
                    current_time - status.last_activity > WORKER_IDLE_TIMEOUT):
                    workers_to_remove.append(worker_id)
            
            for worker_id in workers_to_remove:
                del dr_worker_statuses[worker_id]
        
        if workers_to_remove:
            logger.info(f"[WorkerTracker] Found {len(workers_to_remove)} idle DR workers to clean up")
            try:
                old_executor = dr_pool_executor
                dr_pool_executor = None
                old_executor.shutdown(wait=False)
                logger.info(f"[WorkerTracker] Cleaned up {len(workers_to_remove)} DR workers")
            except Exception as e:
                logger.error(f"[WorkerTracker] Error during DR worker cleanup: {e}")

def start_worker_cleanup_monitoring():
    """Start the worker cleanup monitoring thread"""
    global worker_cleanup_thread
    
    def cleanup_loop():
        while True:
            try:
                time.sleep(600*6)  # Check every 60 minutes
                cleanup_idle_workers()
            except Exception as e:
                logger.error(f"[WorkerTracker] Error in cleanup loop: {e}")
                time.sleep(600*6)
    
    if worker_cleanup_thread is None:
        worker_cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        worker_cleanup_thread.start()
        logger.info("[WorkerTracker] Started worker cleanup monitoring thread")

def initialize_clustering_pool():
    """Initialize the clustering process pool lazily when first needed"""
    global clustering_pool_executor
    
    try:
        # Use 4 workers for clustering operations (high priority, immediate response)
        clustering_workers = 4
        logger.info(f"Initializing clustering process pool with {clustering_workers} workers")
        
        clustering_pool_executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=clustering_workers,
            mp_context=multiprocessing.get_context('spawn')
        )
        
        # Warm up all workers by submitting dummy tasks
        logger.info("Warming up clustering workers...")
        warmup_futures = []
        for i in range(clustering_workers):
            future = clustering_pool_executor.submit(_prewarm_dummy_task)
            warmup_futures.append(future)
        
        # Wait for all warmup tasks to complete
        for i, future in enumerate(warmup_futures):
            try:
                result = future.result(timeout=30)  # 30 second timeout per worker
                logger.info(f"Clustering worker {i+1} warmed up: {result}")
            except Exception as e:
                logger.warning(f"Clustering worker {i+1} warmup failed: {e}")
        
        logger.info("Clustering process pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize clustering process pool: {e}")
        clustering_pool_executor = None

def initialize_dr_pool():
    """Initialize the DR process pool lazily when first needed"""
    global dr_pool_executor
    
    try:
        # Use 2 workers for DR operations (background processing)
        dr_workers = 2
        logger.info(f"Initializing DR process pool with {dr_workers} workers")
        
        dr_pool_executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=dr_workers,
            mp_context=multiprocessing.get_context('spawn')
        )
        
        # Start worker cleanup monitoring (only once)
        start_worker_cleanup_monitoring()
        
        logger.info("DR process pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DR process pool: {e}")
        dr_pool_executor = None

def ensure_clustering_pool():
    """Ensure the clustering process pool is available, initialize if needed"""
    global clustering_pool_executor
    if clustering_pool_executor is None:
        logger.info("Clustering pool not initialized, initializing now...")
        initialize_clustering_pool()
        if clustering_pool_executor is None:
            raise RuntimeError("Cannot initialize clustering process pool")

def ensure_dr_pool():
    """Ensure the DR process pool is available, initialize if needed"""
    global dr_pool_executor
    if dr_pool_executor is None:
        logger.info("DR pool not initialized, initializing now...")
        initialize_dr_pool()
        if dr_pool_executor is None:
            raise RuntimeError("Cannot initialize DR process pool")

def submit_clustering_task(operation_id: str, func, *args, **kwargs):
    """Submit a clustering task to the high-priority clustering pool"""
    ensure_clustering_pool()

    try:
        future = clustering_pool_executor.submit(func, *args, **kwargs)
    except BrokenProcessPool as exc:
        logger.warning(
            f"[PoolReset] Clustering pool broken when submitting {operation_id}: {exc}. Restarting pool."
        )
        reset_clustering_pool(f"broken during submit ({operation_id})")
        ensure_clustering_pool()
        future = clustering_pool_executor.submit(func, *args, **kwargs)

    # Track worker activity
    track_worker_activity(operation_id, future, pool_type="clustering")
    
    # Add completion callback to mark worker as idle
    def completion_callback(completed_future):
        try:
            mark_worker_idle(operation_id, completed_future, pool_type="clustering")
        except Exception as e:
            logger.warning(f"[WorkerTracker] Error in clustering completion callback: {e}")
    
    future.add_done_callback(completion_callback)
    
    return future

def submit_dr_task(cluster_id: str, func, *args, **kwargs):
    """Submit a DR task to the background DR pool with smart cancellation"""
    ensure_dr_pool()
    
    # Cancel old DR operations to free workers for new requests
    cancel_old_dr_operations(keep_recent_count=2)
    
    # Cancel any existing DR for this cluster
    cancel_dr_for_cluster(cluster_id)
    
    try:
        future = dr_pool_executor.submit(func, *args, **kwargs)
    except BrokenProcessPool as exc:
        logger.warning(
            f"[PoolReset] DR pool broken when submitting {cluster_id}: {exc}. Restarting pool."
        )
        reset_dr_pool(f"broken during submit ({cluster_id})")
        ensure_dr_pool()
        future = dr_pool_executor.submit(func, *args, **kwargs)
    
    # Track this DR operation
    with active_dr_lock:
        active_dr_operations[cluster_id] = future
    
    # Track worker activity
    operation_id = f"dr_{cluster_id}"
    track_worker_activity(operation_id, future, pool_type="dr")
    
    # Add completion callback to mark worker as idle and clean up tracking
    def completion_callback(completed_future):
        try:
            mark_worker_idle(operation_id, completed_future, pool_type="dr")
            # Clean up from active operations tracking
            with active_dr_lock:
                active_dr_operations.pop(cluster_id, None)
        except Exception as e:
            logger.warning(f"[WorkerTracker] Error in DR completion callback: {e}")
    
    future.add_done_callback(completion_callback)
    
    return future

# Global storage for active futures (for abort functionality)
active_futures: Dict[str, concurrent.futures.Future] = {}
# Global storage for operation start times
operation_start_times: Dict[str, float] = {}

def cleanup_expired_operations():
    """Remove only completed operations older than 30 minutes, keep running ones longer"""
    current_time = time.time()
    expired_operations = []
    
    for operation_id, start_time in list(operation_start_times.items()):
        operation_age = current_time - start_time
        
        if operation_id in active_futures:
            future = active_futures[operation_id]
            
            # Only clean up completed operations that are old enough
            if future.done() and operation_age > 1800:  # 30 minutes for completed
                expired_operations.append(operation_id)
                logger.info(f"[MemoryOpt] Cleaning up completed operation {operation_id} (age: {operation_age/60:.1f}min)")
            elif not future.done() and operation_age > 7200:  # 2 hours for running operations
                logger.warning(f"[MemoryOpt] Operation {operation_id} running for {operation_age/60:.1f}min - keeping alive")
                # Don't cancel running operations, just warn
        else:
            # Clean up orphaned start times
            if operation_age > 1800:
                expired_operations.append(operation_id)
    
    for operation_id in expired_operations:
        if operation_id in active_futures:
            future = active_futures[operation_id]
            # Only delete if actually done
            if future.done():
                del active_futures[operation_id]
        operation_start_times.pop(operation_id, None)
        cluster_results.pop(operation_id, None)  # Clean up results too
    
    if expired_operations:
        logger.info(f"[MemoryOpt] Cleaned up {len(expired_operations)} completed operations")

def get_legacy_clustering_status(operation_id: str):
    """Legacy function for backward compatibility with older clustering operations"""
    if operation_id not in active_processes:
        return {"status": "not_found", "message": "Legacy operation not found"}
    
    process = active_processes[operation_id]
    
    if process.is_alive():
        return {"status": "processing", "message": "Clustering operation is still running"}
    else:
        # Process finished, check if we have results
        if operation_id in cluster_results:
            result = cluster_results[operation_id]['result']
            return {
                "status": "completed",
                "operation_id": operation_id,
                "result": result
            }
        else:
            return {"status": "failed", "message": "Process completed but no results found"}

# Request models moved to server/models/api_requests.py

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker containers"""
    db_health = redis_service.health_check()
    main_process = psutil.Process(os.getpid())
    main_info = _format_process_memory(main_process, {"role": "main"})
    process_memory_mb = main_info.get("rss_mb", 0.0)

    clustering_pool_info = _gather_pool_memory(clustering_pool_executor, "clustering_pool")
    dr_pool_info = _gather_pool_memory(dr_pool_executor, "dr_pool")
    legacy_process_info = _gather_legacy_process_memory()

    application_total_mb = process_memory_mb
    for section in (clustering_pool_info, dr_pool_info, legacy_process_info):
        application_total_mb += section.get("total_mb", 0.0)

    system_memory = psutil.virtual_memory()
    system_total_mb = round(system_memory.total / (1024 * 1024), 2)
    system_available_mb = round(system_memory.available / (1024 * 1024), 2)
    system_percent = round(system_memory.percent, 2)
    memory_status = "warning" if application_total_mb > 2048 else "healthy"
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "timestamp": time.time(),
        "database": db_health,
        "memory": {
            "status": memory_status,
            "application": {
                "total_mb": round(application_total_mb, 2),
                "main_process": main_info,
                "clustering_pool": clustering_pool_info,
                "dr_pool": dr_pool_info,
                "legacy_processes": legacy_process_info,
            },
            "system": {
                "total_mb": system_total_mb,
                "available_mb": system_available_mb,
                "percent_used": system_percent
            }
        }
    }

@app.post("/api/cluster/regular")
async def cluster_data_regular(req: ClusterParams, background_tasks: BackgroundTasks):
    # Regular clustering, return tree without color properties in nodes
    try:
        start_time = time.time()
        
        # Handle file upload integration
        if req.fileId and req.fileId in file_storage:
            logger.info(f"Using fileId: {req.fileId}")
            stored_data = file_storage[req.fileId]
            logger.info(f"Stored data keys: {list(stored_data.keys())}")
            if "processed_data" in stored_data:
                # Use processed data from file upload
                processed_data = stored_data["processed_data"]
                logger.info(f"Using processed data with shape: {processed_data.get('processing_info', {}).get('processed_shape', 'unknown')}")
                logger.info(f"Processed data headers: {processed_data['headers']}")
                req.data = processed_data["data"]
                req.featureHeaders = processed_data["headers"]
                req.isPreprocessed = True
                # Get hasHeaders from original parsed data
                req.hasHeaders = stored_data["parsed_data"].get("has_headers", False)
                
                # Extract ground truth labels if available
                if processed_data.get("ground_truth_labels"):
                    req.labelData = processed_data["ground_truth_labels"]
                    logger.info(f"Using ground truth labels with {len(req.labelData)} labels")
                
                logger.info(f"Set req.data to processed data with {len(req.data)} rows")
            else:
                logger.warning(f"No processed_data found for fileId: {req.fileId}")
        
        # Enable fast mode by default - skip UMAP/t-SNE for immediate response
        req.skip_umap = True
        req.skip_tsne = True
        
        try:
            result = await ClusteringService.cluster_data(req, None)
        except SHiPTreeGenerationError as ship_error:
            # Return structured error response for SHiP tree generation failures
            logger.error(f"SHiP tree generation failed: {ship_error.message}")
            raise HTTPException(
                status_code=400,
                detail=ship_error.to_dict()
            )
        
        # Generate unique cluster ID for this result
        cluster_id = str(uuid.uuid4())
        
        # Store the clustering result and data for background processing
        cluster_results[cluster_id] = {
            'result': result,
            'params': req,
            'timestamp': time.time(),
            'data': np.array(req.data) if req.data else None
        }
        
        # Add cluster_id to the result
        result['cluster_id'] = cluster_id
        
        # Start background dimensionality reduction if data is suitable (non-blocking)
        if req.data and len(req.data) > 10:
            try:
                # Initialize task status in main process and Redis
                start_time = time.time()
                status_data = {
                    'status': 'processing',
                    'umap_status': 'pending',
                    'tsne_status': 'pending',
                    'umap_result': None,
                    'tsne_result': None,
                    'start_time': start_time,
                    'error': None
                }
                dimensionality_reduction_tasks[cluster_id] = status_data
                redis_service.store_dr_task_status(cluster_id, status_data)
                
                # Callback to handle worker results
                def handle_dr_results(future):
                    try:
                        worker_result = future.result()
                        sync_dr_worker_results(cluster_id, worker_result)
                        
                        if worker_result and worker_result.get('cluster_id') in dimensionality_reduction_tasks:
                            cid = worker_result['cluster_id']
                            start_time = dimensionality_reduction_tasks[cid].get('start_time', time.time())
                            end_time = dimensionality_reduction_tasks[cid].get('end_time', time.time())
                            duration = end_time - start_time
                            logger.info(f"DR completed for cluster {cid} in {duration:.2f}s")
                    except BrokenProcessPool as exc:
                        logger.error(f"[PoolReset] DR pool became unusable for cluster {cluster_id}: {exc}")
                        reset_dr_pool(f"dr result retrieval ({cluster_id})")
                        error_status = {'status': 'failed', 'error': 'Dimensionality reduction worker crashed. Pool restarted.', 'end_time': time.time()}
                        if cluster_id in dimensionality_reduction_tasks:
                            dimensionality_reduction_tasks[cluster_id].update(error_status)
                        redis_service.store_dr_task_status(cluster_id, error_status)
                    except Exception as e:
                        logger.error(f"Error handling DR results for cluster {cluster_id}: {e}")
                        # Update both memory and Redis with error status
                        error_status = {'status': 'failed', 'error': str(e), 'end_time': time.time()}
                        if cluster_id in dimensionality_reduction_tasks:
                            dimensionality_reduction_tasks[cluster_id].update(error_status)
                        redis_service.store_dr_task_status(cluster_id, error_status)
                
                # Submit worker with data directly to DR pool
                data_array = np.array(req.data)
                future = submit_dr_task(cluster_id, compute_dimensionality_reduction_worker, cluster_id, data_array)
                future.add_done_callback(handle_dr_results)
                logger.info(f"Successfully submitted background DR task for cluster {cluster_id}")
            except Exception as e:
                logger.warning(f"Failed to start background dimensionality reduction: {e}")
                if cluster_id in dimensionality_reduction_tasks:
                    dimensionality_reduction_tasks[cluster_id]['status'] = 'failed'
                    dimensionality_reduction_tasks[cluster_id]['error'] = str(e)
        end_time = time.time()
        print(f"ClusteringService.cluster_data (regular) took {end_time - start_time:.4f} seconds")

        start_time = time.time()
        # Remove color properties from tree nodes if present
        def remove_colors(node):
            node.pop('color', None)
            for child in node.get('children', []):
                remove_colors(child)
        tree = copy.deepcopy(result['tree'])
        if 'root' in tree:
            remove_colors(tree['root'])
        result['tree'] = tree
        # Remove color_map if present
        result.pop('color_map', None)
        end_time = time.time()
        print(f"Post-processing (regular) took {end_time - start_time:.4f} seconds")
        
        # Sanitize and return - let FastAPI's default encoder handle it
        sanitized_result = custom_jsonable_encoder(result)
        return sanitized_result
    except ValueError as e:
        print(f"Data validation error in cluster_data_regular: {e}")
        return {"error": str(e), "message": "Invalid data format or content"}
    except Exception as e:
        print(f"Unexpected error in cluster_data_regular: {e}")
        return {"error": str(e), "message": "Failed to perform clustering analysis"}

@app.post("/api/cluster/colored")
async def cluster_data_colored(req: ClusterParams, background_tasks: BackgroundTasks):
    # Clustering with color properties in each tree node - now runs in separate process
    
    # Generate operation ID for abort functionality
    operation_id = str(uuid.uuid4())
    logger.info(f"Starting clustering operation {operation_id}")
    
    try:
        # Handle file upload integration
        if req.fileId and req.fileId in file_storage:
            stored_data = file_storage[req.fileId]
            
            # Check if this is actually an uploaded file (not a toy dataset)
            if stored_data.get('dataset_type') == 'toy_dataset':
                # This is a toy dataset stored in file_storage, skip file processing
                logger.info(f"Skipping file processing for toy dataset: {req.fileId}")
            elif "processed_data" in stored_data and stored_data["processed_data"] is not None:
                # Use processed data from file upload
                processed_data = stored_data["processed_data"]
                req.data = processed_data["data"]
                req.featureHeaders = processed_data["headers"]
                req.isPreprocessed = True
                # Get hasHeaders from original parsed data
                req.hasHeaders = stored_data["parsed_data"].get("has_headers", False)
                
                # Extract ground truth labels if available
                if processed_data.get("ground_truth_labels"):
                    req.labelData = processed_data["ground_truth_labels"]
            else:
                # Auto-process data if it contains non-numeric values
                # Check if parsed_data exists (for uploaded files and imported runs)
                if "parsed_data" in stored_data and stored_data["parsed_data"] is not None:
                    parsed_data = stored_data["parsed_data"]
                    raw_data = parsed_data["data"]
                    headers = parsed_data["headers"]
                else:
                    # Fallback for datasets without parsed_data structure
                    logger.info(f"No parsed_data found for {req.fileId}, using direct data access")
                    raw_data = stored_data.get("data", [])
                    headers = stored_data.get("headers", stored_data.get("feature_names", []))
                    # Create a minimal parsed_data structure for consistency
                    parsed_data = {
                        "data": raw_data,
                        "headers": headers,
                        "has_headers": stored_data.get("has_headers", True)
                    }
                
                logger.info(f"Auto-processing check for file {req.fileId}: data shape {len(raw_data)}x{len(headers)}")
                logger.info(f"Sample raw data: {raw_data[0][:3] if raw_data else 'No data'}")
                
                # Check if data contains non-numeric values
                needs_processing = False
                try:
                    # Try to convert full dataset to float to check if processing is needed
                    import pandas as pd
                    df_full = pd.DataFrame(raw_data, columns=headers)
                    
                    # Check all columns for non-numeric values
                    for col in df_full.columns:
                        try:
                            pd.to_numeric(df_full[col], errors='raise')
                        except (ValueError, TypeError):
                            needs_processing = True
                            logger.info(f"Auto-processing data for file {req.fileId} due to non-numeric values in column '{col}'")
                            break
                    
                    # Additional check: try converting to float array
                    if not needs_processing:
                        try:
                            df_full.astype(float)
                        except (ValueError, TypeError):
                            needs_processing = True
                            logger.info(f"Auto-processing data for file {req.fileId} due to non-numeric values during float conversion")
                
                except Exception as e:
                    logger.warning(f"Error during auto-processing check: {e}")
                    needs_processing = True
                
                if needs_processing:
                    try:
                        # Create default processing config for categorical data
                        from server.cluster_params import DataProcessingConfig, CategoricalEncoding, DataType
                        from server.data_processing_service import DataProcessingService
                        
                        # Detect categorical columns more robustly
                        df = pd.DataFrame(raw_data, columns=headers)
                        column_configs = []
                        for i, col in enumerate(headers):
                            is_categorical = False
                            
                            # Check if column is object type or has any non-numeric values
                            if df[col].dtype == 'object':
                                is_categorical = True
                            else:
                                # Check for mixed types or non-numeric values
                                try:
                                    pd.to_numeric(df[col], errors='raise')
                                except (ValueError, TypeError):
                                    is_categorical = True
                            
                            if is_categorical:
                                column_configs.append({
                                    'index': i,
                                    'name': col,
                                    'data_type': DataType.categorical,
                                    'is_categorical': True,
                                    'usage': 'feature'
                                })
                        
                        if not column_configs:
                            logger.warning("No categorical columns detected for auto-processing")
                            # Fall back to using raw data
                            req.data = raw_data
                            req.featureHeaders = headers
                            req.isPreprocessed = False
                            req.hasHeaders = parsed_data.get("has_headers", False)
                        else:
                            processing_config = DataProcessingConfig(
                                categorical_encoding=CategoricalEncoding.label,
                                feature_columns=list(range(len(headers))),
                                columns=column_configs
                            )
                            
                            # Process the data automatically
                            processed_result = DataProcessingService.process_data(
                                raw_data=raw_data,
                                headers=headers,
                                processing_config=processing_config
                            )
                            
                            # Validate that processing was successful
                            if processed_result and processed_result.get("data"):
                                # Test if processed data is numeric
                                try:
                                    test_array = np.array(processed_result["data"])
                                    test_array.astype(float)
                                    
                                    # Processing was successful
                                    stored_data["processed_data"] = processed_result
                                    
                                    # Use processed data
                                    req.data = processed_result["data"]
                                    req.featureHeaders = processed_result["headers"]
                                    req.isPreprocessed = True
                                    req.hasHeaders = parsed_data.get("has_headers", False)
                                    
                                    # Extract ground truth labels if available
                                    if processed_result.get("ground_truth_labels"):
                                        req.labelData = processed_result["ground_truth_labels"]
                                    
                                    logger.info(f"Auto-processed data shape: {processed_result.get('processing_info', {}).get('processed_shape', 'unknown')}")
                                    logger.info(f"Categorical columns processed: {list(processed_result.get('processing_info', {}).get('categorical_info', {}).keys())}")
                                    logger.info(f"Final processed data sample: {req.data[0][:3] if req.data else 'No data'}")
                                except Exception as validation_error:
                                    logger.error(f"Auto-processing validation failed: {validation_error}")
                                    # Fall back to using raw data - let clustering service handle the error
                                    req.data = raw_data
                                    req.featureHeaders = headers
                                    req.isPreprocessed = False
                                    req.hasHeaders = parsed_data.get("has_headers", False)
                            else:
                                logger.error("Auto-processing returned no data")
                                # Fall back to using raw data
                                req.data = raw_data
                                req.featureHeaders = headers
                                req.isPreprocessed = False
                                req.hasHeaders = parsed_data.get("has_headers", False)
                    
                    except Exception as processing_error:
                        logger.error(f"Auto-processing failed: {processing_error}")
                        # Fall back to using raw data - let clustering service handle the error
                        req.data = raw_data
                        req.featureHeaders = headers
                        req.isPreprocessed = False
                        req.hasHeaders = parsed_data.get("has_headers", False)
                else:
                    # No processing needed - use raw data
                    req.data = raw_data
                    req.featureHeaders = headers
                    req.isPreprocessed = False
                    req.hasHeaders = parsed_data.get("has_headers", False)
        
        # Store toy dataset data in file_storage BEFORE sending to worker
        # This ensures the main process has access to the original data for export
        if not req.fileId and req.sample and req.sample != 'uploaded':
            # This is a toy dataset - store its original data for export
            try:
                import numpy as np
                from .toy_dataset_service import ToyDatasetService
                X, X_true_labels = ToyDatasetService.generate_dataset(
                    dataset_name=req.sample,
                    n_samples=req.n_samples,
                    n_clusters=req.n_clusters,
                    n_features=req.n_features,
                    random_state=req.random_state
                )
                
                # Store in file_storage for export functionality
                dataset_id = req.sample
                file_storage[dataset_id] = {
                    'data': X.tolist(),
                    'labels': X_true_labels.tolist() if X_true_labels is not None else [],
                    'filename': req.sample.upper(),
                    'feature_names': [f"Feature_{i+1}" for i in range(X.shape[1])],
                    'headers': [f"Feature_{i+1}" for i in range(X.shape[1])],
                    'processed_data': X.tolist(),
                    'dataset_type': 'toy_dataset',
                    'n_samples': X.shape[0],
                    'n_features': X.shape[1],
                    'n_clusters': len(np.unique(X_true_labels)) if X_true_labels is not None else req.n_clusters
                }
                
                logger.info(f"[MainProcess] Stored toy dataset {req.sample} in file_storage: {X.shape[0]}x{X.shape[1]}")
                
            except Exception as e:
                logger.warning(f"[MainProcess] Could not store toy dataset in file_storage: {e}")
        
        # Enable fast mode by default - skip UMAP/t-SNE for immediate response
        req.skip_umap = True
        req.skip_tsne = True
        
        # Submit clustering task to high-priority clustering pool
        future = submit_clustering_task(
            operation_id,
            clustering_worker,
            req.model_dump(),
            operation_id,
            {}
        )
        
        # Store future for abort functionality and record start time
        active_futures[operation_id] = future
        operation_start_times[operation_id] = time.time()
        
        # Return operation ID immediately
        return {
            "operation_id": operation_id,
            "status": "started",
            "message": "Clustering operation started. Use /api/cluster/status/{operation_id} to check progress."
        }
        
    except Exception as e:
        logger.error(f"Failed to start clustering operation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start clustering: {str(e)}")

@app.get("/api/cluster/status/{operation_id}")
def get_clustering_status(operation_id: str):
    """Check the status of a clustering operation"""
    logger.info(f"[DEBUG] Status check requested for operation {operation_id}")
    
    # Clean up expired operations periodically
    cleanup_expired_operations()
    
    if operation_id not in active_futures:
        # Check if the result is in the legacy active_processes dict for backward compatibility
        if operation_id in active_processes:
            logger.info(f"[DEBUG] Found operation {operation_id} in legacy processes")
            return get_legacy_clustering_status(operation_id)
            
        # Check Redis persistence for completed operations
        if redis_service:
            try:
                redis_result = redis_service.get_clustering_result_by_operation_id(operation_id)
                if redis_result:
                    logger.info(f"[DEBUG] Redis result found. Status: {redis_result.status}")
                    if redis_result.status == ClusteringStatus.COMPLETED:
                        logger.info(f"[DEBUG] Found completed operation {operation_id} in Redis persistence")
                        
                        # Use the same error handling as the main path
                        response_data = {
                            "status": "completed",
                            "operation_id": operation_id,
                            "result": redis_result.result,
                            "warnings": []
                        }
                        
                        # Sanitize and test serialization
                        try:
                            sanitized_data = custom_jsonable_encoder(response_data)
                            
                            # Test if this can be serialized to JSON
                            test_json = json.dumps(sanitized_data)
                            logger.info(f"[DEBUG] Redis result serializes OK ({len(test_json)} bytes)")
                            
                            return JSONResponse(content=sanitized_data)
                            
                        except (TypeError, ValueError, OverflowError) as e:
                            logger.error(f"[DEBUG] Failed to serialize Redis result: {e}")
                            
                            # Try removing the tree
                            logger.info(f"[DEBUG] Attempting Redis response without tree...")
                            try:
                                if 'result' in sanitized_data and 'tree' in sanitized_data['result']:
                                    result_without_tree = sanitized_data['result'].copy()
                                    result_without_tree['tree'] = {"error": "Tree too complex for serialization"}
                                    
                                    fallback_response = {
                                        "status": "completed",
                                        "operation_id": operation_id,
                                        "result": result_without_tree,
                                        "warning": "Tree structure omitted due to serialization complexity"
                                    }
                                    
                                    test_json2 = json.dumps(fallback_response)
                                    logger.info(f"[DEBUG] Fallback Redis response serializes OK ({len(test_json2)} bytes)")
                                    return JSONResponse(content=fallback_response)
                            except Exception as e2:
                                logger.error(f"[DEBUG] Fallback also failed: {e2}")
                            
                            # Last resort
                            return {
                                "status": "failed",
                                "operation_id": operation_id,
                                "error": f"Redis result too complex to serialize"
                            }
            except Exception as e:
                logger.error(f"[DEBUG] Error checking Redis persistence: {e}")
        
        logger.warning(f"[DEBUG] Operation {operation_id} not found in active_futures or legacy processes")
        logger.info(f"[DEBUG] Current active operations: {list(active_futures.keys())}")
        return {"status": "not_found", "message": "Operation not found"}

    future = active_futures[operation_id]

    if future.done():
        try:
            logger.info(f"[DEBUG] Operation {operation_id} completed, retrieving result...")
            start_time = time.time()
            worker_result = future.result()
            result_retrieval_time = time.time() - start_time
            logger.info(f"[DEBUG] Result retrieval took {result_retrieval_time:.3f}s for operation {operation_id}")
            
            # Safely remove from tracking dicts
            if operation_id in active_futures:
                del active_futures[operation_id]
            operation_start_times.pop(operation_id, None)

            if worker_result["success"]:
                result = worker_result["result"]
                cluster_id = worker_result.get("cluster_id")
                should_start_background = worker_result.get("should_start_background", False)
                
                # Log result size before any processing
                result_json = json.dumps(custom_jsonable_encoder(result))
                result_size_mb = len(result_json.encode('utf-8')) / (1024 * 1024)
                logger.info(f"[DEBUG] Raw clustering result size: {result_size_mb:.2f} MB for operation {operation_id}")
                
                # Check if we need PCA replacement for large datasets
                if result.get('points') and len(result['points']) > 0:
                    points_count = len(result['points'])
                    features_count = len(result['points'][0]) if result['points'] else 0
                    logger.info(f"[DEBUG] Result contains {points_count} points with {features_count} features")
                    
                    # If dataset is large (>10k points or >50 features), consider PCA replacement
                    if points_count > 10000 or features_count > 50:
                        logger.info(f"[DEBUG] Large dataset detected ({points_count} points, {features_count} features) - checking PCA availability")
                        
                        if result.get('dimensionality_reduction', {}).get('pca'):
                            logger.info(f"[DEBUG] PCA available, replacing raw points with PCA components for transfer")
                            # Create a copy with PCA-replaced points for transfer
                            transfer_result = copy.deepcopy(result)
                            pca_components = result['dimensionality_reduction']['pca']
                            if len(pca_components) >= 2:
                                # Replace points with first 2 PCA components for transfer
                                transfer_result['points'] = [[row[0], row[1]] for row in pca_components]
                                transfer_result['_pca_replaced'] = True
                                transfer_result['_original_features'] = features_count
                                
                                # Log size after PCA replacement
                                transfer_json = json.dumps(custom_jsonable_encoder(transfer_result))
                                transfer_size_mb = len(transfer_json.encode('utf-8')) / (1024 * 1024)
                                logger.info(f"[DEBUG] PCA-replaced result size: {transfer_size_mb:.2f} MB (reduced by {result_size_mb - transfer_size_mb:.2f} MB)")
                                result = transfer_result

                data_for_storage = None
                if result.get('points'):
                    data_for_storage = np.array(result['points'])

                cluster_results[cluster_id] = {
                    'result': result,
                    'params': worker_result.get('params', {}),
                    'timestamp': time.time(),
                    'data': data_for_storage
                }

                if should_start_background and data_for_storage is not None and data_for_storage.shape[0] > 10:
                    logger.info(f"Starting background dimensionality reduction for cluster {cluster_id}")
                    # Start background DR immediately since we're in the main process
                    # and have confirmed the cluster results are stored
                    try:
                        # Use a small delay to ensure the response is sent first
                        import threading
                        def start_background_dr():
                            try:
                                # Initialize task status in main process and Redis
                                start_time = time.time()
                                status_data = {
                                    'status': 'processing',
                                    'umap_status': 'pending',
                                    'tsne_status': 'pending',
                                    'umap_result': None,
                                    'tsne_result': None,
                                    'start_time': start_time,
                                    'error': None
                                }
                                dimensionality_reduction_tasks[cluster_id] = status_data
                                redis_service.store_dr_task_status(cluster_id, status_data)
                                logger.info(f"Initialized DR task status for cluster {cluster_id}")
                                
                                # Callback to handle worker results
                                def handle_dr_results(future):
                                    try:
                                        worker_result = future.result()
                                        sync_dr_worker_results(cluster_id, worker_result)
                                        
                                        if worker_result and worker_result.get('cluster_id') in dimensionality_reduction_tasks:
                                            cid = worker_result['cluster_id']
                                            start_time = dimensionality_reduction_tasks[cid].get('start_time', time.time())
                                            end_time = dimensionality_reduction_tasks[cid].get('end_time', time.time())
                                            duration = end_time - start_time
                                            logger.info(f"DR completed for cluster {cid} in {duration:.2f}s")
                                    except BrokenProcessPool as exc:
                                        logger.error(f"[PoolReset] DR pool became unusable for cluster {cluster_id}: {exc}")
                                        reset_dr_pool(f"dr result retrieval ({cluster_id})")
                                        error_status = {'status': 'failed', 'error': 'Dimensionality reduction worker crashed. Pool restarted.', 'end_time': time.time()}
                                        if cluster_id in dimensionality_reduction_tasks:
                                            dimensionality_reduction_tasks[cluster_id].update(error_status)
                                        redis_service.store_dr_task_status(cluster_id, error_status)
                                    except Exception as e:
                                        logger.error(f"Error handling DR results for cluster {cluster_id}: {e}")
                                        # Update both memory and Redis with error status
                                        error_status = {'status': 'failed', 'error': str(e), 'end_time': time.time()}
                                        if cluster_id in dimensionality_reduction_tasks:
                                            dimensionality_reduction_tasks[cluster_id].update(error_status)
                                        redis_service.store_dr_task_status(cluster_id, error_status)
                                
                                # Pass the data directly to avoid process isolation issues
                                future = submit_dr_task(cluster_id, compute_dimensionality_reduction_worker, cluster_id, data_for_storage)
                                future.add_done_callback(handle_dr_results)
                                logger.info(f"Successfully submitted background DR task for cluster {cluster_id}")
                            except Exception as e:
                                logger.error(f"Failed to submit background DR task for cluster {cluster_id}: {e}")
                                if cluster_id in dimensionality_reduction_tasks:
                                    dimensionality_reduction_tasks[cluster_id]['status'] = 'failed'
                                    dimensionality_reduction_tasks[cluster_id]['error'] = str(e)
                        
                        # Start in a separate thread with small delay to avoid blocking the response
                        threading.Timer(0.1, start_background_dr).start()
                    except Exception as e:
                        logger.warning(f"Failed to setup background dimensionality reduction: {e}")

                logger.info(f"[ProcessManager] Marked clustering process {operation_id} as completed")
                
                # Persist result to Redis for resilience against restarts and polling race conditions
                if redis_service:
                    try:
                        c_res = ClusteringResultCreate(
                            operation_id=operation_id,
                            cluster_id=cluster_id,
                            result=result,
                            data=None, 
                            status=ClusteringStatus.COMPLETED
                        )
                        redis_service.create_clustering_result(c_res)
                        logger.info(f"[DEBUG] Persisted result for operation {operation_id} to Redis")
                    except Exception as e:
                        logger.warning(f"[DEBUG] Failed to persist result for {operation_id} to Redis: {e}")
                
                # Create a lightweight copy of result for status response
                lightweight_result = copy.deepcopy(result)
                
                # Debug: Check size of individual components
                if lightweight_result:
                    for key, value in lightweight_result.items():
                        try:
                            component_json = json.dumps(custom_jsonable_encoder(value))
                            component_size_mb = len(component_json.encode('utf-8')) / (1024 * 1024)
                            if component_size_mb > 1:  # Only log components larger than 1MB
                                logger.info(f"[DEBUG] Component '{key}' size: {component_size_mb:.2f} MB")
                                
                                # If it's a list, check the first few items
                                if isinstance(value, list) and len(value) > 0:
                                    first_item_json = json.dumps(custom_jsonable_encoder(value[0]))
                                    first_item_size = len(first_item_json.encode('utf-8'))
                                    logger.info(f"[DEBUG] Component '{key}' has {len(value)} items, first item size: {first_item_size} bytes")
                        except Exception as e:
                            logger.warning(f"[DEBUG] Could not measure size of component '{key}': {e}")
                
                # Log final response size before sending
                response_data = {
                    "status": "completed",
                    "operation_id": operation_id,
                    "result": lightweight_result
                }
                
                # Sanitize the data to remove NaN/Inf and handle numpy types
                try:
                    sanitized_data = custom_jsonable_encoder(response_data)
                    
                    # Test if this can be serialized to JSON
                    test_json = json.dumps(sanitized_data)
                    logger.info(f"[DEBUG] Sanitized response serializes OK ({len(test_json)} bytes)")
                    
                    # Return using FastAPI's JSONResponse
                    return JSONResponse(content=sanitized_data)
                    
                except (TypeError, ValueError, OverflowError) as e:
                    logger.error(f"[DEBUG] Failed to serialize full response: {e}")
                    
                    # Try removing the tree which is often the problematic part
                    logger.info(f"[DEBUG] Attempting response without tree...")
                    try:
                        if 'result' in sanitized_data and 'tree' in sanitized_data['result']:
                            # Create response without tree
                            result_without_tree = sanitized_data['result'].copy()
                            result_without_tree['tree'] = {"error": "Tree too complex for serialization"}
                            
                            fallback_response = {
                                "status": "completed",
                                "operation_id": operation_id,
                                "result": result_without_tree,
                                "warning": "Tree structure omitted due to serialization complexity"
                            }
                            
                            # Test this version
                            test_json2 = json.dumps(fallback_response)
                            logger.info(f"[DEBUG] Fallback response (without tree) serializes OK ({len(test_json2)} bytes)")
                            return JSONResponse(content=fallback_response)
                    except Exception as e2:
                        logger.error(f"[DEBUG] Fallback also failed: {e2}")
                    
                    # Last resort: minimal response
                    return {
                        "status": "failed",
                        "operation_id": operation_id,
                        "error": f"Result too complex to serialize. Try with fewer data points or simpler configuration."
                    }
            else:
                logger.info(f"[ProcessManager] Marked clustering process {operation_id} as failed")
                return {
                    "status": "failed",
                    "operation_id": operation_id,
                    "error": worker_result["error"]
                }
        except BrokenProcessPool as exc:
            if operation_id in active_futures:
                del active_futures[operation_id]
            operation_start_times.pop(operation_id, None)
            logger.error(
                f"[PoolReset] Clustering pool became unusable while retrieving {operation_id}: {exc}"
            )
            reset_clustering_pool(f"result retrieval ({operation_id})")
            return {
                "status": "failed",
                "operation_id": operation_id,
                "error": "Clustering worker crashed and the pool was restarted. Please retry the operation."
            }
        except Exception as e:
            if operation_id in active_futures:
                del active_futures[operation_id]
            operation_start_times.pop(operation_id, None)
            logger.info(f"[ProcessManager] Marked clustering process {operation_id} as failed due to exception")
            return {
                "status": "failed",
                "operation_id": operation_id,
                "error": f"Failed to retrieve result: {str(e)}"
            }
    else:
        # Calculate elapsed time
        elapsed_time = 0.0
        if operation_id in operation_start_times:
            elapsed_time = time.time() - operation_start_times[operation_id]
        
        return {
            "status": "running",
            "operation_id": operation_id,
            "elapsed_time": elapsed_time
        }

@app.post("/api/cluster/abort/{operation_id}")
def abort_clustering_operation(operation_id: str):
    """Abort a running clustering operation"""
    if operation_id in active_futures:
        future = active_futures[operation_id]
        if future.cancel():
            del active_futures[operation_id]
            operation_start_times.pop(operation_id, None)
            return {"status": "aborted", "message": "Clustering operation aborted successfully."}
        else:
            return {"status": "failed_to_abort", "message": "Operation could not be aborted. It may have already completed."}
    
    # Legacy abort for old process-based approach
    if operation_id in active_processes:
        process_info = active_processes[operation_id]
        process = process_info['process']
        if process.is_alive():
            process.terminate()
            process.join()  # Wait for termination
            del active_processes[operation_id]
            return {"status": "aborted", "message": "Clustering operation aborted successfully."}

    return {"status": "not_found", "message": "Operation not found."}
        
        
    

# ============ DATA UPLOAD AND PROCESSING ENDPOINTS ============

@app.post("/api/data/upload")
async def upload_data_file(file: UploadFile = File(...)):
    """
    Upload and parse a data file (CSV, Excel, JSON).
    Returns parsed data with metadata and assigns a unique file ID.
    """
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Parse the uploaded file
        parsed_data = await FileUploadService.parse_file(file)
        
        # Generate data hash from parsed data
        data_hash = None
        if parsed_data.get("data"):
            try:
                import numpy as np
                data_array = np.array(parsed_data["data"])
                data_hash = SHiPCacheService._create_data_hash(data_array)
            except Exception as e:
                logger.warning(f"Could not generate data hash: {e}")
                # Provide fallback hash instead of None to satisfy MongoDB schema
                import hashlib
                fallback_content = f"{file.filename}_{len(parsed_data['data'])}_{time.time()}"
                data_hash = hashlib.md5(fallback_content.encode()).hexdigest()
                logger.info(f"Generated fallback data hash: {data_hash}")
        
        # Ensure data_hash is never None for MongoDB schema compliance
        if data_hash is None:
            import hashlib
            fallback_content = f"{file.filename}_{file.size}_{time.time()}"
            data_hash = hashlib.md5(fallback_content.encode()).hexdigest()
            logger.info(f"Generated final fallback data hash: {data_hash}")
        
        # Create dataset record in database
        dataset = DatasetCreate(
            id=file_id,
            filename=file.filename,
            original_filename=file.filename,
            content_type=file.content_type,
            file_size=file.size if hasattr(file, 'size') else None,
            data_hash=data_hash,
            processed_data=parsed_data
        )
        
        # Store in database
        redis_service.create_dataset(dataset)
        
        # Also store in file_storage for export functionality
        file_storage[file_id] = {
            'data': parsed_data.get('data', []),
            'labels': [],  # Will be populated if ground truth is available
            'filename': file.filename,
            'feature_names': parsed_data.get('headers', []),
            'headers': parsed_data.get('headers', []),
            'parsed_data': parsed_data,
            'processed_data': None,  # Will be set after processing
            'dataset_type': 'uploaded_file',
            'has_headers': parsed_data.get('has_headers', False),
            'content_type': file.content_type
        }
        
        # Add file_id to response
        response_data = {**parsed_data, "file_id": file_id}
        
        logger.info(f"File uploaded successfully: {file.filename} -> {file_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@app.post("/api/data/process")
async def process_data(request: DataProcessRequest):
    """
    Process uploaded data according to configuration.
    Applies missing value handling, normalization, feature selection, etc.
    """
    try:
        file_id = request.file_id
        logger.info(f"Processing data for file_id: {file_id}")
        
        # Try to get from in-memory storage first
        if file_id in file_storage:
            stored_data = file_storage[file_id]
            # Check if parsed_data exists, otherwise create it from stored data
            if "parsed_data" in stored_data and stored_data["parsed_data"] is not None:
                parsed_data = stored_data["parsed_data"]
            else:
                # Create parsed_data structure from stored data (for imported runs or toy datasets)
                parsed_data = {
                    "data": stored_data.get("data", []),
                    "headers": stored_data.get("headers", stored_data.get("feature_names", [])),
                    "has_headers": stored_data.get("has_headers", True),
                    "filename": stored_data.get("filename", "unknown"),
                    "num_rows": len(stored_data.get("data", [])),
                    "num_columns": len(stored_data.get("headers", stored_data.get("feature_names", [])))
                }
                logger.info(f"Created parsed_data structure for file_id: {file_id}")
        else:
            # Fallback to database storage
            logger.info(f"File not found in memory storage, trying database: {file_id}")
            dataset_data = await dataset_repository.get_dataset_data(file_id)
            if not dataset_data:
                logger.error(f"File not found in database: {file_id}")
                raise HTTPException(status_code=404, detail="File not found. Please upload the file again.")
            
            parsed_data = dataset_data
            logger.info(f"Loaded data from database for file: {file_id}")
        
        logger.info(f"Processing config: categorical_encoding={request.processing_config.categorical_encoding}")
        logger.info(f"Feature columns: {request.processing_config.feature_columns}")
        logger.info(f"Column configs: {[(c.name, c.is_categorical, c.usage) if hasattr(c, 'name') else c for c in request.processing_config.columns]}")
        
        # Extract ground truth column if specified
        ground_truth_column = None
        if request.processing_config.label_columns:
            # Use the first label column as ground truth
            ground_truth_column = request.processing_config.label_columns[0]
        
        # Process the data
        processed_result = DataProcessingService.process_data(
            raw_data=parsed_data["data"],
            headers=parsed_data["headers"],
            processing_config=request.processing_config,
            ground_truth_column=ground_truth_column
        )
        
        logger.info(f"Processing result: categorical_info keys = {list(processed_result.get('processing_info', {}).get('categorical_info', {}).keys())}")
        logger.info(f"Processed data shape: {processed_result.get('processing_info', {}).get('processed_shape', 'unknown')}")
        
        # Store processed data
        if file_id in file_storage:
            file_storage[file_id]["processed_data"] = processed_result
            # Ensure original data is preserved for export
            if not file_storage[file_id].get('data'):
                file_storage[file_id]['data'] = parsed_data.get('data', [])
            # Store ground truth labels if extracted
            if processed_result.get('ground_truth_labels'):
                file_storage[file_id]['labels'] = processed_result['ground_truth_labels']
        else:
            # If not in memory, create entry and try to update database
            try:
                dataset = redis_service.get_dataset(file_id)
                if dataset:
                    # Store in file_storage for export functionality
                    file_storage[file_id] = {
                        'data': parsed_data.get('data', []),
                        'labels': processed_result.get('ground_truth_labels', []),
                        'filename': dataset.filename,
                        'feature_names': parsed_data.get('headers', []),
                        'headers': parsed_data.get('headers', []),
                        'parsed_data': parsed_data,
                        'processed_data': processed_result,
                        'dataset_type': 'uploaded_file',
                        'has_headers': parsed_data.get('has_headers', False),
                        'content_type': dataset.content_type
                    }
                    
                    redis_service.update_dataset(file_id, {"processed_data": processed_result})
                    logger.info(f"Updated processed data in database and file_storage for file: {file_id}")
            except Exception as e:
                logger.warning(f"Failed to update processed data in database: {e}")
        
        logger.info(f"Data processed successfully for file: {file_id}")
        return processed_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data processing failed: {str(e)}")

@app.post("/api/data/preview")
async def get_data_preview(request: DataPreviewRequest):
    """
    Get a preview of uploaded data.
    """
    try:
        file_id = request.file_id
        
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found")
        
        stored_data = file_storage[file_id]
        parsed_data = stored_data["parsed_data"]
        
        # Get preview
        preview = await FileUploadService.get_preview(parsed_data, request.num_rows)
        
        return preview
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get data preview: {str(e)}")

@app.post("/api/data/preview-processed")
async def get_processed_data_preview(request: DataProcessRequest):
    """
    Get a preview of how data will look after processing with given configuration.
    This provides an accurate preview of backend processing without storing the result.
    """
    try:
        file_id = request.file_id
        
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found")
        
        stored_data = file_storage[file_id]
        parsed_data = stored_data["parsed_data"]
        
        # Extract ground truth column if specified
        ground_truth_column = None
        if request.processing_config.label_columns:
            # Use the first label column as ground truth
            ground_truth_column = request.processing_config.label_columns[0]
        
        # Process the data with the configuration
        processed_result = DataProcessingService.process_data(
            raw_data=parsed_data["data"],
            headers=parsed_data["headers"],
            processing_config=request.processing_config,
            ground_truth_column=ground_truth_column
        )
        
        # Return preview with limited rows for performance
        preview_rows = 10
        preview_data = processed_result["data"][:preview_rows] if len(processed_result["data"]) > preview_rows else processed_result["data"]
        
        return {
            "headers": processed_result["headers"],
            "data": preview_data,
            "total_rows": processed_result["row_count"],
            "preview_rows": len(preview_data),
            "processing_info": processed_result["processing_info"],
            "feature_columns": processed_result["feature_columns"],
            "ignored_columns": processed_result["ignored_columns"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processed data preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get processed data preview: {str(e)}")

@app.get("/api/data/analyze/{file_id}")
async def analyze_data(file_id: str):
    """
    Analyze data characteristics and provide processing recommendations.
    """
    try:
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found")
        
        stored_data = file_storage[file_id]
        parsed_data = stored_data["parsed_data"]
        
        # Analyze data
        analysis = DataProcessingService.analyze_data_characteristics(
            data=parsed_data["data"],
            headers=parsed_data["headers"]
        )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data analysis failed: {str(e)}")

@app.get("/api/data/raw/{file_id}")
async def get_raw_data(file_id: str):
    """
    Get raw data for a file ID.
    """
    try:
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found")
        
        stored_data = file_storage[file_id]
        parsed_data = stored_data["parsed_data"]
        
        return {
            "data": parsed_data["data"],
            "headers": parsed_data["headers"],
            "has_headers": parsed_data["has_headers"],
            "row_count": parsed_data["row_count"],
            "column_count": parsed_data["column_count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Raw data retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve raw data: {str(e)}")

@app.delete("/api/data/{file_id}")
async def delete_data_file(file_id: str):
    """
    Delete uploaded data file from storage.
    """
    try:
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found")
        
        original_filename = file_storage[file_id].get("original_filename", "unknown")
        del file_storage[file_id]
        
        logger.info(f"File deleted: {original_filename} ({file_id})")
        return {"message": "File deleted successfully", "file_id": file_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.get("/api/data/formats")
async def get_supported_formats():
    """
    Get list of supported file formats.
    """
    return {
        "supported_extensions": [".csv", ".xlsx", ".xls", ".json"],
        "max_file_size_mb": 100,
        "features": [
            "Automatic encoding detection",
            "Header detection",
            "Data type inference",
            "Missing value handling",
            "Normalization options",
            "Feature selection",
            "Categorical encoding"
        ]
    }

@app.get("/api/data/files")
async def list_uploaded_files():
    """
    List all uploaded files (for debugging/admin purposes).
    """
    files_info = []
    for file_id, data in file_storage.items():
        files_info.append({
            "file_id": file_id,
            "filename": data.get("original_filename", "unknown"),
            "upload_time": data.get("upload_time", 0),
            "has_processed_data": "processed_data" in data,
            "row_count": data["parsed_data"].get("row_count", 0),
            "column_count": data["parsed_data"].get("column_count", 0)
        })
    
    return {"files": files_info, "total": len(files_info)}


@app.get("/api/cluster/options")
def get_cluster_options():
    from .clustering_service import AVAILABLE_ULTRAMETRIC_TREE_TYPES, AVAILABLE_PARTITIONING_METHODS
    
    # Add 'K' as a manual partition method option if not already present
    partition_methods = list(AVAILABLE_PARTITIONING_METHODS)
    if 'K' not in partition_methods:
        partition_methods.append('K')
    
    # Filter out LoadTree since it requires external tree files
    tree_types = [tree_type for tree_type in AVAILABLE_ULTRAMETRIC_TREE_TYPES if tree_type != 'LoadTree']
    
    return {
        "treeTypes": tree_types,
        "partitionMethods": partition_methods
    }

def run_k_selection_analysis(params_dict: dict, operation_id: str):
    """Run k-selection analysis in a separate process"""
    try:
        # Perform k-selection analysis
        start_time = time.time()
        results = KSelectionService.analyze_k_range_sync(
            data=params_dict['data'],
            k_range=params_dict['k_range'],
            tree_type=params_dict['treeType'],
            power=params_dict['power'],
            random_state=params_dict['random_state']
        )
        end_time = time.time()
        print(f"[K-Selection Process] KSelectionService.analyze_k_range took {end_time - start_time:.4f} seconds")
        
        # Add data caching logic
        data_array = np.array(params_dict['data']) if not isinstance(params_dict['data'], np.ndarray) else params_dict['data']
        should_cache = (
            data_array.shape[1] > 50 or  # High-dimensional datasets
            len(results.get('data_points', [])) == 0 or  # When data_points is empty
            data_array.shape[0] * data_array.shape[1] > 10000  # Large datasets
        )
        
        if should_cache:
            try:
                # Clean up old cache entries before adding new ones
                cleanup_k_selection_cache()
                
                # Create a more robust hash that works for large datasets
                sample_size = min(100, data_array.size)
                data_sample = data_array.flatten()[:sample_size]
                
                # Include dataset characteristics in hash for better uniqueness
                hash_input = (
                    tuple(data_sample),
                    data_array.shape[0],  # number of samples
                    data_array.shape[1],  # number of features
                    params_dict['treeType'],
                    params_dict['power']
                )
                data_hash = str(abs(hash(hash_input)))  # Use abs to avoid negative hashes
                
                # Ensure PCA components are available for caching
                pca_components = results.get('pca_components')
                if pca_components is None and data_array.shape[1] > 2:
                    print(f"[K-Selection Process] PCA components missing for high-dimensional dataset, computing now...")
                    try:
                        from sklearn.decomposition import PCA
                        pca = PCA(n_components=min(2, data_array.shape[1]))
                        pca_components = pca.fit_transform(data_array).tolist()
                        results['pca_components'] = pca_components
                        print(f"[K-Selection Process] Successfully computed PCA components for caching")
                    except Exception as pca_error:
                        print(f"[K-Selection Process] Failed to compute PCA for caching: {pca_error}")
                        pca_components = None
                
                k_selection_data_cache[data_hash] = {
                    'data': data_array,  # Always store as numpy array
                    'pca_components': pca_components,
                    'created_at': time.time(),
                    'dataset_info': {
                        'shape': data_array.shape,
                        'tree_type': params_dict['treeType'],
                        'power': params_dict['power'],
                        'original_feature_count': data_array.shape[1],
                        'high_dimensional_dataset': data_array.shape[1] > 50
                    }
                }
                
                # Add data identifier to results for frontend reference
                results['data_cache_id'] = data_hash
                print(f"[K-Selection Process] Cached dataset with ID: {data_hash} (shape: {data_array.shape})")
                
                # Add high-dimensional dataset flag
                if data_array.shape[1] > 50:
                    results['high_dimensional_dataset'] = True
                    results['original_feature_count'] = data_array.shape[1]
                    results['show_only_dr_methods'] = True
                    print(f"[K-Selection Process] Successfully cached and validated data for high-dimensional dataset")
                
            except Exception as cache_error:
                print(f"[K-Selection Process] Failed to cache data: {cache_error}")
        
        # Start background dimensionality reduction computation if suitable
        dr_cluster_id = None
        if data_array.shape[1] > 2 and data_array.shape[0] > 10:
            try:
                # Generate unique cluster ID for DR computation
                dr_cluster_id = str(uuid.uuid4())
                
                # Initialize DR task status
                start_time = time.time()
                status_data = {
                    'status': 'processing',
                    'umap_status': 'pending',
                    'tsne_status': 'pending',
                    'umap_result': None,
                    'tsne_result': None,
                    'start_time': start_time,
                    'error': None
                }
                dimensionality_reduction_tasks[dr_cluster_id] = status_data
                
                # Store DR task status in Redis immediately in worker process
                try:
                    from .redis_service import RedisService
                    redis_service = RedisService()
                    redis_service.store_dr_task_status(dr_cluster_id, status_data)
                    print(f"[K-Selection Process] Stored DR task status in Redis for cluster {dr_cluster_id}")
                except Exception as redis_error:
                    print(f"[K-Selection Process] Failed to store DR task in Redis: {redis_error}")
                
                print(f"[K-Selection Process] Starting DR computation for cluster {dr_cluster_id}")
                
                # Add DR cluster_id to results for frontend polling
                results['dr_cluster_id'] = dr_cluster_id
                results['dr_status'] = 'started'
                
                print(f"[K-Selection Process] DR computation initialized for cluster {dr_cluster_id}")
                
            except Exception as dr_error:
                print(f"[K-Selection Process] Failed to initialize DR computation: {dr_error}")
                results['dr_status'] = 'failed'
                results['dr_error'] = str(dr_error)

        return {
            'status': 'completed', 
            'result': results, 
            'dr_cluster_id': dr_cluster_id,
            'data_for_dr': data_array.tolist() if dr_cluster_id and data_array.shape[1] > 2 else None
        }
        
    except Exception as e:
        error_msg = f"K-selection analysis failed: {str(e)}"
        print(f"[K-Selection Process] Error: {error_msg}")
        return {'status': 'failed', 'error': error_msg}

@app.post("/api/k-selection/analyze")
def analyze_k_selection(req: KSelectionRequest):
    """
    Start K-selection analysis to determine optimal number of clusters (async with abort support)
    """
    try:
        # Get data
        if req.fileId and req.fileId in file_storage:
            stored_data = file_storage[req.fileId]
            if "processed_data" in stored_data and stored_data["processed_data"].get("data"):
                logger.info(f"[K-Selection API] Using processed data from file_storage for fileId: {req.fileId}")
                data = stored_data["processed_data"]["data"]
            elif req.data is not None:
                data = req.data
            else:
                # Fallback to checking parsed_data or erroring if no data found
                logger.warning(f"[K-Selection API] fileId provided but no processed data found. Checking parsed data.")
                if "parsed_data" in stored_data and stored_data["parsed_data"].get("data"):
                     data = stored_data["parsed_data"]["data"]
                else: 
                     raise HTTPException(status_code=400, detail="No data found for the provided fileId")

        elif req.data is not None:
            data = req.data
        else:
            # Generate sample data
            start_time = time.time()
            generated_data = KSelectionService.generate_sample_data(
                sample_type=req.sample,
                n_samples=req.n_samples or 200,
                random_state=req.random_state
            )
            end_time = time.time()
            print(f"KSelectionService.generate_sample_data took {end_time - start_time:.4f} seconds")
            
            # Convert numpy array to list only if not high-dimensional
            if isinstance(generated_data, np.ndarray):
                if generated_data.shape[1] > 50:
                    print(f"[K-Selection API] High-dimensional dataset ({generated_data.shape[1]} features), using numpy array directly")
                    data = generated_data  # Keep as numpy array for processing
                else:
                    data = generated_data.tolist()  # Convert to list for JSON serialization
            else:
                data = generated_data
        
        # Generate unique operation ID
        operation_id = str(uuid.uuid4())
        logger.info(f"Starting k-selection analysis with operation ID: {operation_id}")
        
        # Prepare parameters for multiprocessing
        params_dict = {
            'data': data,
            'k_range': req.k_range,
            'treeType': req.treeType,
            'power': req.power,
            'random_state': req.random_state
        }
        
        # Submit k-selection task to clustering pool (high priority)
        future = submit_clustering_task(
            operation_id,
            run_k_selection_analysis,
            params_dict,
            operation_id
        )
        
        # Store future for abort functionality and record start time
        active_futures[operation_id] = future
        operation_start_times[operation_id] = time.time()
        
        # Return operation ID immediately
        return {
            "operation_id": operation_id,
            "status": "started",
            "message": "K-selection analysis started. Use /api/k-selection/status/{operation_id} to check progress."
        }
        
    except Exception as e:
        logger.error(f"Failed to start k-selection analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start k-selection analysis: {str(e)}")

@app.get("/api/k-selection/status/{operation_id}")
def get_k_selection_status(operation_id: str):
    """Check the status of a k-selection analysis operation"""
    # Clean up expired operations periodically
    cleanup_expired_operations()
    
    if operation_id not in active_futures:
        return {"status": "not_found", "message": "Operation not found"}

    future = active_futures[operation_id]

    if future.done():
        try:
            result = future.result()
            
            # Store result for later retrieval but don't immediately clean up
            cluster_results[operation_id] = {
                'result': result,
                'timestamp': time.time(),
                'status': 'completed'
            }
            
            logger.info(f"[MemoryOpt] Operation {operation_id} completed, result stored")

            if result['status'] == 'completed':
                response = {
                    "status": "completed",
                    "operation_id": operation_id,
                    "result": result['result']
                }
                
                # Start DR computation if it was initialized during analysis
                dr_cluster_id = result.get('dr_cluster_id')
                if dr_cluster_id:
                    try:
                        # Get the data array - first try from worker result, then fallback to cache
                        data_array = None
                        
                        # First, try to get data passed back from worker process
                        if result.get('data_for_dr'):
                            data_array = np.array(result['data_for_dr'])
                            print(f"[K-Selection API] Using data from worker process (shape: {data_array.shape})")
                        else:
                            # Fallback: try data_points from result
                            data_array = np.array(result['result'].get('data_points', []))
                            data_cache_id = result['result'].get('data_cache_id')
                            
                            print(f"[K-Selection API] DR data analysis - data_points length: {len(data_array)}, data_cache_id: {data_cache_id}")
                            
                            if len(data_array) == 0 or data_array.size == 0:
                                # For high-dimensional datasets, try to get data from cache
                                if data_cache_id and data_cache_id in k_selection_data_cache:
                                    data_array = k_selection_data_cache[data_cache_id]['data']
                                    print(f"[K-Selection API] Using cached data for DR computation (cache_id: {data_cache_id}, shape: {data_array.shape})")
                                else:
                                    print(f"[K-Selection API] No cached data found for data_cache_id: {data_cache_id}")
                                    print(f"[K-Selection API] Available cache keys: {list(k_selection_data_cache.keys())}")
                        
                        if data_array is not None and len(data_array) > 0 and data_array.ndim > 1 and data_array.shape[1] > 2:
                            # Store cluster results for DR computation
                            cluster_results[dr_cluster_id] = {
                                'result': result['result'],
                                'data': data_array,
                                'timestamp': time.time()
                            }
                            
                            # Initialize DR task status in main process (since worker process state doesn't transfer)
                            start_time = time.time()
                            status_data = {
                                'status': 'processing',
                                'umap_status': 'pending',
                                'tsne_status': 'pending',
                                'umap_result': None,
                                'tsne_result': None,
                                'start_time': start_time,
                                'error': None
                            }
                            dimensionality_reduction_tasks[dr_cluster_id] = status_data
                            
                            # Store DR task status in Redis immediately
                            try:
                                redis_service.store_dr_task_status(dr_cluster_id, status_data)
                                print(f"[K-Selection API] Stored DR task status in Redis for cluster {dr_cluster_id}")
                            except Exception as redis_error:
                                print(f"[K-Selection API] Failed to store DR task in Redis: {redis_error}")
                                # Continue anyway - the in-memory storage should work
                            
                            # Submit DR task
                            def handle_k_selection_dr_results(future):
                                try:
                                    worker_result = future.result()
                                    sync_dr_worker_results(dr_cluster_id, worker_result)
                                    print(f"[K-Selection API] DR completed for cluster {dr_cluster_id}")
                                except BrokenProcessPool as exc:
                                    print(f"[PoolReset] DR pool unusable during k-selection DR for {dr_cluster_id}: {exc}")
                                    reset_dr_pool(f"k-selection dr result retrieval ({dr_cluster_id})")
                                    error_status = {'status': 'failed', 'error': 'Dimensionality reduction worker crashed. Pool restarted.', 'end_time': time.time()}
                                    if dr_cluster_id in dimensionality_reduction_tasks:
                                        dimensionality_reduction_tasks[dr_cluster_id].update(error_status)
                                    redis_service.store_dr_task_status(dr_cluster_id, error_status)
                                except Exception as e:
                                    print(f"[K-Selection API] Error handling DR results for cluster {dr_cluster_id}: {e}")
                                    error_status = {'status': 'failed', 'error': str(e), 'end_time': time.time()}
                                    if dr_cluster_id in dimensionality_reduction_tasks:
                                        dimensionality_reduction_tasks[dr_cluster_id].update(error_status)
                                    redis_service.store_dr_task_status(dr_cluster_id, error_status)
                            
                            future = submit_dr_task(dr_cluster_id, compute_dimensionality_reduction_worker, dr_cluster_id, data_array)
                            future.add_done_callback(handle_k_selection_dr_results)
                            print(f"[K-Selection API] Started background DR computation for cluster {dr_cluster_id}")
                            
                        else:
                            data_shape = data_array.shape if data_array is not None and hasattr(data_array, 'shape') else 'None'
                            data_len = len(data_array) if data_array is not None else 0
                            data_dims = data_array.shape[1] if data_array is not None and hasattr(data_array, 'shape') and len(data_array.shape) > 1 else 'unknown'
                            print(f"[K-Selection API] Skipping DR computation - data shape: {data_shape}, dimensions: {data_dims}")
                            print(f"[K-Selection API] DR requirements: data not None, length > 0, dimensions > 2. Current: data={data_array is not None}, length={data_len}")
                            
                    except Exception as dr_error:
                        print(f"[K-Selection API] Failed to start DR computation: {dr_error}")
                        if dr_cluster_id in dimensionality_reduction_tasks:
                            dimensionality_reduction_tasks[dr_cluster_id]['status'] = 'failed'
                            dimensionality_reduction_tasks[dr_cluster_id]['error'] = str(dr_error)
                
                return response
            else:
                return {
                    "status": "failed",
                    "operation_id": operation_id,
                    "error": result.get('error', 'Unknown error')
                }
        except BrokenProcessPool as exc:
            if operation_id in active_futures:
                del active_futures[operation_id]
            operation_start_times.pop(operation_id, None)
            logger.error(
                f"[PoolReset] Clustering pool became unusable while retrieving k-selection {operation_id}: {exc}"
            )
            reset_clustering_pool(f"k-selection result retrieval ({operation_id})")
            return {
                "status": "failed",
                "operation_id": operation_id,
                "error": "K-selection worker crashed and the pool was restarted. Please retry the analysis."
            }
        except Exception as e:
            # Only clean up on error
            if operation_id in active_futures:
                del active_futures[operation_id]
            operation_start_times.pop(operation_id, None)
            logger.error(f"[MemoryOpt] Error retrieving result for {operation_id}: {str(e)}")
            return {
                "status": "failed",
                "operation_id": operation_id,
                "error": f"Error retrieving result: {str(e)}"
            }
    else:
        return {
            "status": "running",
            "operation_id": operation_id,
            "message": "K-selection analysis in progress"
        }

@app.post("/api/k-selection/cluster-visualization")
def get_cluster_visualization(req: ClusterVisualizationRequest):
    """
    Get clustering visualization for a specific k value
    """
    try:
        # Allow request parameters to control UMAP/t-SNE skipping behavior
        # Default behavior will be determined by the frontend request
        
        # Determine data source: either from request or from cache
        data_to_use = req.data
        cached_pca = None
        
        if req.data is None or (isinstance(req.data, list) and len(req.data) == 0):
            # Try to get data from cache using data_cache_id
            if req.data_cache_id:
                data_to_use, cached_pca, found_exact_match = get_cached_data_with_fallback(req.data_cache_id, req.treeType, req.power)
                if data_to_use is not None:
                    if found_exact_match:
                        print(f"[K-Selection] Using exact cached data for dataset (cache_id: {req.data_cache_id})")
                    else:
                        print(f"[K-Selection] Using fallback cached data for dataset (cache_id: {req.data_cache_id})")
                    print(f"[K-Selection] Cached data shape: {data_to_use.shape}")
                    if cached_pca is not None:
                        print(f"[K-Selection] Found cached PCA results - will reuse for efficiency")
                else:
                    # No valid cache data found - provide helpful error message
                    error_msg = (
                        f"Data cache_id '{req.data_cache_id}' not found and no fallback data available. "
                        f"The analysis data may have expired (cache entries are kept for 2 hours). "
                        f"Please re-run the k-selection analysis to generate fresh data."
                    )
                    raise ValueError(error_msg)
            else:
                raise ValueError("No data provided and no data_cache_id specified. Either provide data directly or include a valid cache_id.")
        elif req.data_cache_id and req.data_cache_id in k_selection_data_cache:
            # Even if we have data, check for cached PCA results to avoid recomputation
            cached_entry = k_selection_data_cache[req.data_cache_id]
            cached_pca = cached_entry.get('pca_components')
        
        start_time = time.time()
        result = KSelectionService.cluster_for_visualization_sync(
            data=data_to_use,
            n_clusters=req.n_clusters,
            tree_type=req.treeType,
            power=req.power,
            random_state=req.random_state,
            skip_umap=req.skip_umap,  # UMAP will be computed in background
            skip_tsne=req.skip_tsne,  # t-SNE will be computed in background
            data_cache_id=req.data_cache_id,
            cached_pca=cached_pca
        )
        
        # Generate unique cluster ID for this result
        cluster_id = str(uuid.uuid4())
        
        # Store the clustering result and data for background processing
        data_for_storage = np.array(data_to_use) if data_to_use is not None else None
        
        cluster_results[cluster_id] = {
            'result': result,
            'params': {
                'treeType': req.treeType,
                'n_clusters': req.n_clusters,
                'power': req.power,
                'random_state': req.random_state,
                'fileId': req.fileId,
                'sample': req.sample or 'uploaded'
            },
            'data': data_for_storage,
            'timestamp': time.time()
        }
        
        # Add cluster_id to the result for frontend polling
        result['cluster_id'] = cluster_id
        
        # Note: DR computation is now handled during K-selection analysis
        # This endpoint only handles clustering for specific K values
        print(f"[K-Selection] Cluster visualization endpoint took {time.time() - start_time:.4f} seconds")
        print(f"[K-Selection] DR results will be available via analysis DR cluster_id")
        return result
        
    except ValueError as ve:
        print(f"[K-Selection] Validation error: {ve}")
        return {"error": str(ve), "message": "Invalid request parameters"}
    except RuntimeError as re:
        print(f"[K-Selection] Runtime error: {re}")
        return {"error": str(re), "message": "Background task initialization failed"}
    except Exception as e:
        print(f"[K-Selection] Unexpected error: {e}")
        return {"error": str(e), "message": "Failed to generate cluster visualization"}

@app.get("/api/cache/info")
def get_cache_info():
    """
    Get information about current cache state (both SHIP and UMAP caches)
    """
    try:
        cache_info = SHiPCacheService.get_combined_cache_info()
        return {
            "success": True,
            "cache_info": cache_info
        }
    except Exception as e:
        return {"error": str(e), "message": "Failed to retrieve cache information"}

@app.post("/api/cache/clear")
def clear_cache():
    """
    Clear all cached objects (both SHIP and UMAP) to free memory
    """
    try:
        clear_result = SHiPCacheService.clear_all_caches()
        return {
            "success": True,
            "message": "All caches cleared successfully",
            "details": clear_result
        }
    except Exception as e:
        return {"error": str(e), "message": "Failed to clear cache"}

@app.post("/api/cache/reset")
def reset_cache():
    """
    Legacy endpoint for backwards compatibility - same as clear_cache
    """
    return clear_cache()

@app.get("/api/cache/umap-info")
def get_umap_cache_info():
    """
    Get detailed information about UMAP optimization cache
    """
    try:
        from .umap_optimization_service import UMAPOptimizationService
        umap_info = UMAPOptimizationService.get_cache_info()
        return {
            "success": True,
            "umap_cache_info": umap_info
        }
    except ImportError:
        return {
            "success": False,
            "error": "UMAP optimization service not available"
        }
    except Exception as e:
        return {"error": str(e), "message": "Failed to retrieve UMAP cache information"}

@app.post("/api/cache/clear-umap")
def clear_umap_cache():
    """
    Clear only the UMAP cache while preserving SHIP cache
    """
    try:
        from .umap_optimization_service import UMAPOptimizationService
        cleared_count = UMAPOptimizationService.clear_cache()
        return {
            "success": True,
            "message": f"UMAP cache cleared successfully",
            "entries_cleared": cleared_count
        }
    except ImportError:
        return {
            "success": False,
            "error": "UMAP optimization service not available"
        }
    except Exception as e:
        return {"error": str(e), "message": "Failed to clear UMAP cache"}

@app.get("/api/optimization/recommendations")
def get_optimization_recommendations():
    """
    Get optimization recommendations for different dataset sizes
    """
    try:
        recommendations = {}
        
        # Sample different dataset sizes
        sizes = [100, 1000, 5000, 10000, 50000, 100000, 500000]
        
        for size in sizes:
            # Get SHIP config recommendations
            ship_config = SHiPCacheService._get_optimized_config_for_dataset_size(size)
            
            recommendations[str(size)] = {
                "ship_config": ship_config,
                "sampling_recommendations": None # Removed sampling
            }
            
        return {"success": True, "recommendations": recommendations}
    except Exception as e:
        return {"error": str(e), "message": "Failed to get optimization recommendations"}

@app.get("/api/optimization/status")
def get_optimization_status():
    """
    Get current optimization status
    """
    try:
        # In a real app, this would check system resources, cache status etc.
        return {
            "success": True,
            "message": "Optimization status check not fully implemented in this demo.",
            "status": "N/A"
        }
    except Exception as e:
        return {"error": str(e), "message": "Failed to get optimization status"}

@app.post("/api/data/upload-duplicate-remove")
async def upload_file_duplicate_to_remove(file: UploadFile = File(...)):
    """
    Upload and parse a file (CSV, Excel, JSON).
    Returns parsed data with metadata for further processing.
    """
    try:
        start_time = time.time()
        logger.info(f"Starting file upload: {file.filename}")
        
        # Parse the file
        parsed_data = await FileUploadService.parse_file(file)
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Store parsed data in memory (in production, use proper storage)
        file_storage[file_id] = {
            "parsed_data": parsed_data,
            "upload_time": time.time(),
            "filename": file.filename
        }
        
        end_time = time.time()
        logger.info(f"File upload completed in {end_time - start_time:.2f}s: {file.filename}")
        
        # Convert to response format
        response_data = {
            "file_id": file_id,
            "data": parsed_data["data"],
            "headers": parsed_data["headers"],
            "has_headers": parsed_data["has_headers"],
            "row_count": parsed_data["row_count"],
            "column_count": parsed_data["column_count"],
            "column_info": parsed_data["column_info"],
            "file_info": parsed_data["file_info"],
            "missing_value_count": parsed_data["missing_value_count"],
            "data_types": parsed_data["data_types"]
        }
        
        # Add format-specific metadata
        if "encoding" in parsed_data:
            response_data["encoding"] = parsed_data["encoding"]
            response_data["encoding_confidence"] = parsed_data["encoding_confidence"]
        if "separator" in parsed_data:
            response_data["separator"] = parsed_data["separator"]
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@app.post("/api/data/preview")
async def get_data_preview(request: DataPreviewRequest):
    """
    Get a preview of uploaded file data.
    """
    try:
        # Get stored file data
        if request.file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found. Please upload file first.")
        
        stored_data = file_storage[request.file_id]
        parsed_data = stored_data["parsed_data"]
        
        # Get preview
        preview_data = await FileUploadService.get_preview(parsed_data, request.num_rows)
        
        return DataPreviewResponse(**preview_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get data preview: {str(e)}")

@app.get("/api/data/analyze/{file_id}")
async def analyze_data(file_id: str):
    """
    Analyze uploaded data and provide processing recommendations.
    """
    try:
        # Get stored file data
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found. Please upload file first.")
        
        stored_data = file_storage[file_id]
        parsed_data = stored_data["parsed_data"]
        
        # Analyze data
        analysis = DataProcessingService.analyze_data_characteristics(
            data=parsed_data["data"],
            headers=parsed_data["headers"]
        )
        
        return DataAnalysisResponse(**analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Data analysis failed: {str(e)}")

@app.delete("/api/data/{file_id}")
async def delete_uploaded_file(file_id: str):
    """
    Delete uploaded file data from storage.
    """
    try:
        if file_id not in file_storage:
            raise HTTPException(status_code=404, detail="File not found")
        
        filename = file_storage[file_id].get("filename", "unknown")
        del file_storage[file_id]
        
        logger.info(f"Deleted file data: {filename}")
        
        return {"message": f"File {filename} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")

@app.get("/api/data/files")
async def list_uploaded_files():
    """
    List all uploaded files in storage.
    """
    try:
        files_info = []
        for file_id, data in file_storage.items():
            files_info.append({
                "file_id": file_id,
                "filename": data.get("filename", "unknown"),
                "upload_time": data.get("upload_time", 0),
                "has_processed_data": "processed_data" in data
            })
        
        return {"files": files_info}
        
    except Exception as e:
        logger.error(f"File listing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/api/data/formats")
async def get_supported_formats():
    """
    Get information about supported file formats.
    """
    return {
        "supported_extensions": list(FileUploadService.SUPPORTED_EXTENSIONS),
        "max_file_size_mb": FileUploadService.MAX_FILE_SIZE / (1024 * 1024),
        "formats": {
            ".csv": {
                "description": "Comma-separated values",
                "features": ["encoding_detection", "separator_detection", "header_detection"]
            },
            ".xlsx": {
                "description": "Excel spreadsheet (modern)",
                "features": ["multi_sheet_support", "header_detection"]
            },
            ".xls": {
                "description": "Excel spreadsheet (legacy)",
                "features": ["header_detection"]
            },
            ".json": {
                "description": "JSON data format",
                "features": ["array_of_arrays", "array_of_objects"]
            }
        }
    }

@app.post("/api/analyze/clustering-insights")
def analyze_clustering_insights(req: ClusteringAnalysisRequest):
    """
    Analyze clustering insights for a specific dataset
    """
    try:
        start_time = time.time()
        result = ClusteringAnalysisService.analyze_clustering_insights(
            cluster_data=req.cluster_data,
            tree_data=req.tree_data,
            selected_features=req.selected_features,
            feature_names=req.feature_names,
            analysis_options=req.analysis_options
        )
        end_time = time.time()
        print(f"ClusteringAnalysisService.analyze_clustering_insights took {end_time - start_time:.4f} seconds")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Failed to analyze clustering insights"}

@app.post("/api/analyze/dataset-insights")
def analyze_dataset_insights(req: DatasetInsightsRequest):
    """
    Analyze dataset insights for a specific dataset
    """
    try:
        start_time = time.time()
        result = ClusteringAnalysisService.analyze_dataset_insights(
            dataset=req.dataset,
            data=req.data,
            selected_features=req.selected_features,
            feature_names=req.feature_names,
            analysis_type=req.analysis_type,
            options=req.options
        )
        end_time = time.time()
        print(f"ClusteringAnalysisService.analyze_dataset_insights took {end_time - start_time:.4f} seconds")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Failed to analyze dataset insights"}

@app.post("/api/analyze/cluster-summary")
def analyze_cluster_summary(req: ClusterSummaryRequest):
    """
    Generate comprehensive cluster summary statistics
    """
    try:
        start_time = time.time()
        result = ClusteringAnalysisService.analyze_cluster_summary(
            cluster_data=req.cluster_data,
            selected_features=req.selected_features,
            feature_names=req.feature_names,
            options=req.options
        )
        end_time = time.time()
        print(f"ClusteringAnalysisService.analyze_cluster_summary took {end_time - start_time:.4f} seconds")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Failed to analyze cluster summary"}

@app.post("/api/analyze/feature-importance")
def analyze_feature_importance(req: FeatureImportanceRequest):
    """
    Calculate feature importance for clustering analysis
    """
    try:
        start_time = time.time()
        result = ClusteringAnalysisService.analyze_feature_importance(
            cluster_data=req.cluster_data,
            selected_features=req.selected_features,
            feature_names=req.feature_names,
            options=req.options
        )
        end_time = time.time()
        print(f"ClusteringAnalysisService.analyze_feature_importance took {end_time - start_time:.4f} seconds")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Failed to analyze feature importance"}

@app.post("/api/analyze/feature-importance-dataset")
def analyze_feature_importance_dataset(req: FeatureImportanceDatasetRequest):
    """
    Calculate feature importance by loading dataset directly (optimized for big datasets)
    """
    try:
        start_time = time.time()
        result = ClusteringAnalysisService.analyze_feature_importance_dataset(
            dataset_id=req.dataset_id,
            cluster_labels=req.cluster_labels,
            selected_features=req.selected_features,
            feature_names=req.feature_names,
            options=req.options
        )
        end_time = time.time()
        print(f"ClusteringAnalysisService.analyze_feature_importance_dataset took {end_time - start_time:.4f} seconds")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Failed to analyze feature importance from dataset"}

@app.post("/api/analyze/feature-statistics")
def analyze_feature_statistics(req: FeatureStatisticsRequest):
    """
    Calculate comprehensive feature statistics
    """
    try:
        # Validate request size to prevent 422 errors
        data_size = len(req.data) * len(req.data[0]) if req.data and len(req.data) > 0 else 0
        max_data_points = 100000  # 100k data points limit
        
        if data_size > max_data_points:
            return {
                "error": f"Dataset too large for direct analysis ({data_size:,} data points > {max_data_points:,} limit)",
                "message": "Please use dataset-reference-based analysis for large datasets with 50+ features",
                "suggestion": "Consider using sampling or the optimized dataset-based API endpoints"
            }
        
        start_time = time.time()
        result = ClusteringAnalysisService.analyze_feature_statistics(
            data=req.data,
            selected_features=req.selected_features,
            feature_names=req.feature_names,
            options=req.options
        )
        end_time = time.time()
        print(f"ClusteringAnalysisService.analyze_feature_statistics took {end_time - start_time:.4f} seconds")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Failed to analyze feature statistics"}

@app.post("/api/analyze/correlation-matrix")
def analyze_correlation_matrix(req: CorrelationMatrixRequest):
    """
    Calculate correlation matrix for selected features
    """
    try:
        # Validate request size to prevent 422 errors
        data_size = len(req.data) * len(req.data[0]) if req.data and len(req.data) > 0 else 0
        max_data_points = 100000  # 100k data points limit
        
        if data_size > max_data_points:
            return {
                "error": f"Dataset too large for direct analysis ({data_size:,} data points > {max_data_points:,} limit)",
                "message": "Please use dataset-reference-based analysis for large datasets with 50+ features",
                "suggestion": "Consider using sampling or the optimized dataset-based API endpoints"
            }
        
        start_time = time.time()
        result = ClusteringAnalysisService.analyze_correlation_matrix(
            data=req.data,
            selected_features=req.selected_features,
            feature_names=req.feature_names,
            options=req.options
        )
        end_time = time.time()
        print(f"ClusteringAnalysisService.analyze_correlation_matrix took {end_time - start_time:.4f} seconds")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "message": "Failed to analyze correlation matrix"}

# ============ OPTIMIZED DATASET-BASED ANALYSIS ENDPOINTS ============

@app.post("/api/analyze/dataset/feature-statistics")
def analyze_dataset_feature_statistics(req: DatasetAnalysisRequest):
    """
    Calculate feature statistics using dataset reference (optimized for large datasets)
    """
    try:
        start_time = time.time()
        
        # Get data from backend storage instead of request payload
        data_array = _get_dataset_data(req.dataset_id)
        if data_array is None:
            return {
                "error": f"Dataset not found: {req.dataset_id}",
                "message": "Dataset could not be retrieved from backend storage",
                "suggestion": "For uploaded CSV files, ensure the data has been processed and contains only numeric values. Use the data processing page to handle categorical data with proper encoding."
            }
        
        # Apply sampling for very large datasets if requested
        if req.sample_size and len(data_array) > req.sample_size:
            import numpy as np
            indices = np.random.choice(len(data_array), req.sample_size, replace=False)
            data_array = data_array[indices]
            print(f"[DatasetAnalysis] Sampled {req.sample_size} rows from {len(data_array)} total")
        
        # Filter by selected features
        if req.selected_features and len(req.selected_features) > 0:
            if data_array.shape[1] > max(req.selected_features):
                data_array = data_array[:, req.selected_features]
        
        # Convert to list format for the existing analysis function
        data_list = data_array.tolist()
        
        result = ClusteringAnalysisService.analyze_feature_statistics(
            data=data_list,
            selected_features=list(range(len(req.selected_features))),  # Re-index after filtering
            feature_names=req.feature_names,
            options=req.options
        )
        
        end_time = time.time()
        print(f"Dataset-based feature statistics took {end_time - start_time:.4f} seconds")
        
        # Add metadata about the analysis
        result['analysis_metadata'] = {
            'dataset_id': req.dataset_id,
            'original_shape': f"{len(data_list)}x{len(data_list[0]) if data_list else 0}",
            'sampled': req.sample_size is not None,
            'sample_size': len(data_list) if req.sample_size else None
        }
        
        return result
        
    except Exception as e:
        print(f"Error in dataset-based feature statistics: {e}")
        return {"error": str(e), "message": "Failed to analyze dataset feature statistics"}

@app.post("/api/analyze/dataset/correlation-matrix")
def analyze_dataset_correlation_matrix(req: DatasetAnalysisRequest):
    """
    Calculate correlation matrix using dataset reference (optimized for large datasets)
    """
    try:
        start_time = time.time()
        
        # Get data from backend storage instead of request payload
        data_array = _get_dataset_data(req.dataset_id)
        if data_array is None:
            return {
                "error": f"Dataset not found: {req.dataset_id}",
                "message": "Dataset could not be retrieved from backend storage",
                "suggestion": "For uploaded CSV files, ensure the data has been processed and contains only numeric values. Use the data processing page to handle categorical data with proper encoding."
            }
        
        # Apply sampling for very large datasets if requested
        if req.sample_size and len(data_array) > req.sample_size:
            import numpy as np
            indices = np.random.choice(len(data_array), req.sample_size, replace=False)
            data_array = data_array[indices]
            print(f"[DatasetAnalysis] Sampled {req.sample_size} rows from {len(data_array)} total")
        
        # Filter by selected features
        if req.selected_features and len(req.selected_features) > 0:
            if data_array.shape[1] > max(req.selected_features):
                data_array = data_array[:, req.selected_features]
        
        # Convert to list format for the existing analysis function
        data_list = data_array.tolist()
        
        result = ClusteringAnalysisService.analyze_correlation_matrix(
            data=data_list,
            selected_features=list(range(len(req.selected_features))),  # Re-index after filtering
            feature_names=req.feature_names,
            options=req.options
        )
        
        end_time = time.time()
        print(f"Dataset-based correlation matrix took {end_time - start_time:.4f} seconds")
        
        # Add metadata about the analysis
        if isinstance(result, dict):
            result['analysis_metadata'] = {
                'dataset_id': req.dataset_id,
                'original_shape': f"{len(data_list)}x{len(data_list[0]) if data_list else 0}",
                'sampled': req.sample_size is not None,
                'sample_size': len(data_list) if req.sample_size else None
            }
        
        return result
        
    except Exception as e:
        print(f"Error in dataset-based correlation matrix: {e}")
        return {"error": str(e), "message": "Failed to analyze dataset correlation matrix"}

@app.post("/api/analyze/dataset/data-sample")
def analyze_dataset_data_sample(req: DatasetAnalysisRequest):
    """
    Generate data sample using dataset reference (optimized for large datasets)
    """
    try:
        start_time = time.time()
        print(f"[DataSample] Processing data sample request for dataset: {req.dataset_id}")
        
        # Get data from backend storage instead of request payload
        data_array = _get_dataset_data(req.dataset_id)
        if data_array is None:
            return {
                "error": f"Dataset not found: {req.dataset_id}",
                "message": "Dataset could not be retrieved from backend storage",
                "suggestion": "For uploaded CSV files, ensure the data has been processed and contains only numeric values. Use the data processing page to handle categorical data with proper encoding."
            }
        
        print(f"[DataSample] Retrieved dataset: {data_array.shape[0]}x{data_array.shape[1]} shape")
        
        # Filter by selected features if specified
        if req.selected_features and len(req.selected_features) > 0:
            max_feature_index = max(req.selected_features)
            if data_array.shape[1] > max_feature_index:
                data_array = data_array[:, req.selected_features]
                print(f"[DataSample] Filtered to selected features: {data_array.shape[1]} features")
            else:
                print(f"[DataSample] Warning: Feature index {max_feature_index} exceeds dataset dimensions {data_array.shape[1]}")
        
        # Apply sampling for very large datasets if requested
        sample_size = req.sample_size or 10  # Default to 10 rows for data sample
        if len(data_array) > sample_size:
            sampled_data = data_array[:sample_size]  # Take first N rows for consistent preview
            print(f"[DataSample] Sampled {sample_size} rows from {len(data_array)} total")
        else:
            sampled_data = data_array
            print(f"[DataSample] Using all {len(data_array)} rows (dataset smaller than sample size)")
        
        # Convert to list format for frontend
        sample_list = sampled_data.tolist()
        
        end_time = time.time()
        print(f"[DataSample] Data sample generated in {end_time - start_time:.4f} seconds: {len(sample_list)}x{len(sample_list[0]) if sample_list else 0}")
        
        return {
            "success": True,
            "data_sample": sample_list,
            "feature_names": req.feature_names[:len(sample_list[0])] if sample_list and req.feature_names else [],
            "metadata": {
                "total_rows": data_array.shape[0],
                "total_features": data_array.shape[1],
                "sample_size": len(sample_list),
                "selected_features_count": len(req.selected_features) if req.selected_features else data_array.shape[1]
            }
        }
        
    except Exception as e:
        print(f"Error in dataset-based data sample: {e}")
        return {"error": str(e), "message": "Failed to generate dataset data sample"}

# FeatureDistributionRequest moved to server/models/api_requests.py

@app.post("/api/analyze/dataset/feature-distribution")
def analyze_dataset_feature_distribution(req: FeatureDistributionRequest):
    """
    Calculate feature distribution using dataset reference (optimized for large datasets)
    """
    try:
        start_time = time.time()
        print(f"[FeatureDistribution] Processing distribution request for dataset: {req.dataset_id}, feature_index: {req.feature_index}")
        
        # Get data from backend storage instead of request payload
        data_array = _get_dataset_data(req.dataset_id)
        if data_array is None:
            return {
                "error": f"Dataset not found: {req.dataset_id}",
                "message": "Dataset could not be retrieved from backend storage",
                "suggestion": "For uploaded CSV files, ensure the data has been processed and contains only numeric values. Use the data processing page to handle categorical data with proper encoding."
            }
        
        print(f"[FeatureDistribution] Retrieved dataset: {data_array.shape[0]}x{data_array.shape[1]} shape")
        
        # Validate feature index
        if req.feature_index < 0 or req.feature_index >= len(req.selected_features):
            return {
                "error": f"Invalid feature index: {req.feature_index}",
                "message": f"Feature index must be between 0 and {len(req.selected_features)-1}",
                "suggestion": "Check that the feature index corresponds to a valid selected feature"
            }
        
        # Get actual feature column index from selected features
        actual_feature_index = req.selected_features[req.feature_index]
        if actual_feature_index >= data_array.shape[1]:
            return {
                "error": f"Feature index {actual_feature_index} exceeds dataset dimensions {data_array.shape[1]}",
                "message": "Selected feature index is out of bounds for this dataset",
                "suggestion": "Ensure selected features are valid for this dataset"
            }
        
        # Extract feature values
        feature_values = data_array[:, actual_feature_index]
        print(f"[FeatureDistribution] Extracted {len(feature_values)} values for feature {actual_feature_index}")
        
        # Apply sampling for very large datasets if requested
        if req.sample_size and len(feature_values) > req.sample_size:
            import numpy as np
            indices = np.random.choice(len(feature_values), req.sample_size, replace=False)
            feature_values = feature_values[indices]
            print(f"[FeatureDistribution] Sampled {req.sample_size} values from {len(data_array)} total")
        
        # Convert to list and remove any NaN values
        import numpy as np
        feature_list = feature_values.tolist()
        feature_list = [val for val in feature_list if not np.isnan(val)]
        
        if not feature_list:
            return {
                "error": "No valid values found for this feature",
                "message": "All values are NaN or invalid",
                "suggestion": "Try a different feature or check data preprocessing"
            }
        
        end_time = time.time()
        feature_name = req.feature_names[req.feature_index] if req.feature_index < len(req.feature_names) else f"Feature {actual_feature_index}"
        print(f"[FeatureDistribution] Feature distribution calculated for '{feature_name}' in {end_time - start_time:.4f} seconds: {len(feature_list)} data points")
        
        return {
            "success": True,
            "feature_values": feature_list,
            "feature_name": feature_name,
            "metadata": {
                "feature_index": req.feature_index,
                "actual_feature_index": actual_feature_index,
                "total_values": len(feature_values),
                "valid_values": len(feature_list),
                "min_value": min(feature_list),
                "max_value": max(feature_list)
            }
        }
        
    except Exception as e:
        print(f"Error in dataset-based feature distribution: {e}")
        return {"error": str(e), "message": "Failed to calculate dataset feature distribution"}

def _get_dataset_data(dataset_id: str):
    """
    Helper function to retrieve dataset data from various sources
    """
    import numpy as np
    
    try:
        # Try to get from toy dataset service first (most common case)
        from .toy_dataset_service import ToyDatasetService
        
        # Map common dataset aliases to their toy dataset names
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
        
        # Note: Toy datasets are stored in file_storage by the clustering endpoint
        # so we can use the same unified data retrieval path for both toy datasets and uploaded CSV files
        
        # Try to get from cluster result cache (if SHiP cache has the method)
        try:
            if hasattr(SHiPCacheService, 'get_cluster_result'):
                cluster_result = SHiPCacheService.get_cluster_result(dataset_id)
                if cluster_result and 'points' in cluster_result:
                    points = cluster_result['points']
                    if points and len(points) > 0:
                        # Extract feature data from points (exclude cluster labels)
                        data_array = np.array([[p.get(f'feature_{i}', p.get(f'f{i}', 0)) 
                                              for i in range(len(points[0]) - 1)]  # Exclude last column (labels)
                                             for p in points])
                        print(f"[DatasetAnalysis] Retrieved data from cluster cache: {data_array.shape}")
                        return data_array
        except Exception as cache_error:
            print(f"[DatasetAnalysis] Failed to get from cluster cache: {cache_error}")
        
        # Try to get from file storage (uploaded CSV files)
        if dataset_id in file_storage:
            stored_data = file_storage[dataset_id]
            print(f"[DatasetAnalysis] Found file in storage: {stored_data.keys()}")
            
            # Priority 1: Use processed data if available (after data processing)
            if 'processed_data' in stored_data and stored_data['processed_data'] is not None:
                processed_data = stored_data['processed_data']
                if 'data' in processed_data:
                    try:
                        data_array = np.array(processed_data['data'], dtype=float)
                        print(f"[DatasetAnalysis] Retrieved processed data from file storage: {data_array.shape}")
                        return data_array
                    except (ValueError, TypeError) as e:
                        print(f"[DatasetAnalysis] Failed to convert processed data to float array: {e}")
                        # Continue to try other data sources
            
            # Priority 2: Use parsed data (raw uploaded data)
            if 'parsed_data' in stored_data and stored_data['parsed_data'] is not None:
                parsed_data = stored_data['parsed_data']
                if 'data' in parsed_data:
                    try:
                        data_array = np.array(parsed_data['data'], dtype=float)
                        print(f"[DatasetAnalysis] Retrieved parsed data from file storage: {data_array.shape}")
                        return data_array
                    except (ValueError, TypeError) as e:
                        print(f"[DatasetAnalysis] Failed to convert parsed data to float array: {e}")
                        # Continue to try other data sources
            
            # Priority 3: Direct data access (fallback)
            if 'data' in stored_data:
                try:
                    data_array = np.array(stored_data['data'], dtype=float)
                    print(f"[DatasetAnalysis] Retrieved direct data from file storage: {data_array.shape}")
                    return data_array
                except (ValueError, TypeError) as e:
                    print(f"[DatasetAnalysis] Failed to convert direct data to float array: {e}")
                    # Continue to try database access
        
        # Try to get from Redis database (persistent storage)
        try:
            dataset = redis_service.get_dataset(dataset_id)
            if dataset and dataset.processed_data:
                if 'data' in dataset.processed_data:
                    try:
                        data_array = np.array(dataset.processed_data['data'], dtype=float)
                        print(f"[DatasetAnalysis] Retrieved data from Redis database: {data_array.shape}")
                        return data_array
                    except (ValueError, TypeError) as e:
                        print(f"[DatasetAnalysis] Failed to convert Redis processed data to float array: {e}")
                elif hasattr(dataset.processed_data, 'data'):
                    try:
                        data_array = np.array(dataset.processed_data.data, dtype=float)
                        print(f"[DatasetAnalysis] Retrieved data from Redis database (attribute access): {data_array.shape}")
                        return data_array
                    except (ValueError, TypeError) as e:
                        print(f"[DatasetAnalysis] Failed to convert Redis processed data (attribute) to float array: {e}")
            elif dataset and hasattr(dataset, 'data') and dataset.data:
                try:
                    data_array = np.array(dataset.data, dtype=float)
                    print(f"[DatasetAnalysis] Retrieved raw data from Redis database: {data_array.shape}")
                    return data_array
                except (ValueError, TypeError) as e:
                    print(f"[DatasetAnalysis] Failed to convert Redis raw data to float array: {e}")
        except Exception as db_error:
            print(f"[DatasetAnalysis] Failed to get from Redis database: {db_error}")
        
        print(f"[DatasetAnalysis] Dataset {dataset_id} not found in any storage")
        return None
        
    except Exception as e:
        print(f"[DatasetAnalysis] Error retrieving dataset {dataset_id}: {e}")
        return None


# ============ BACKGROUND DIMENSIONALITY REDUCTION ENDPOINTS ============

# Helper function to sync worker results to both memory and Redis
def sync_dr_worker_results(cluster_id: str, worker_result: Dict[str, Any]) -> None:
    """Sync dimensionality reduction worker results to both in-memory storage and Redis"""
    try:
        if not worker_result or 'cluster_id' not in worker_result:
            return
        
        cid = worker_result['cluster_id']
        end_time = time.time()
        
        # Update in-memory storage (for backward compatibility)
        if cid in dimensionality_reduction_tasks:
            dimensionality_reduction_tasks[cid]['status'] = worker_result['status']
            dimensionality_reduction_tasks[cid]['umap_status'] = worker_result['umap_status']
            dimensionality_reduction_tasks[cid]['tsne_status'] = worker_result['tsne_status']
            dimensionality_reduction_tasks[cid]['umap_result'] = worker_result['umap_result']
            dimensionality_reduction_tasks[cid]['tsne_result'] = worker_result['tsne_result']
            dimensionality_reduction_tasks[cid]['end_time'] = end_time
            
            if worker_result.get('error'):
                dimensionality_reduction_tasks[cid]['error'] = worker_result['error']
        
        # Update Redis storage (primary storage)
        redis_status = {
            'cluster_id': cid,
            'status': worker_result['status'],
            'umap_status': worker_result['umap_status'],
            'tsne_status': worker_result['tsne_status'],
            'end_time': end_time,
            'error': worker_result.get('error', '')
        }
        
        # Get start time from existing Redis data if available
        existing_data = redis_service.get_dr_task_status(cid)
        if existing_data and existing_data.get('start_time'):
            redis_status['start_time'] = existing_data['start_time']
        
        redis_service.store_dr_task_status(cid, redis_status)
        
    except Exception as e:
        print(f"[DR-Sync] Error syncing worker results for cluster {cluster_id}: {e}")

# Old thread-based functions removed - now using process-based compute_dimensionality_reduction_worker

def compute_dimensionality_reduction_worker(cluster_id: str, data_array: np.ndarray):
    """
    Process worker function to compute UMAP and t-SNE for a clustering result.
    This function runs in a separate process and stores results in Redis.
    """
    try:
        print(f"[DR-Worker] Starting dimensionality reduction for cluster {cluster_id} with {data_array.shape[0]} samples")
        
        # Import heavy dependencies inside worker to avoid startup overhead
        import numpy as np
        from .umap_optimization_service import UMAPOptimizationService  
        from .tsne_optimization_service import TSNEOptimizationService
        from .redis_service import redis_service
        import time
        
        start_time = time.time()
        
        # Initialize status in Redis
        status_data = {
            'cluster_id': cluster_id,
            'status': 'processing',
            'umap_status': 'pending',
            'tsne_status': 'pending',
            'start_time': start_time,
            'error': None
        }
        
        # Connect to Redis if not already connected
        if redis_service.client is None:
            redis_service.connect()
        
        # Store initial status in Redis
        redis_service.store_dr_task_status(cluster_id, status_data)
        
        results = {
            'cluster_id': cluster_id,
            'status': 'processing',
            'umap_result': None,
            'tsne_result': None,
            'umap_status': 'pending',
            'tsne_status': 'pending',
            'error': None
        }
        
        # Validate data
        if data_array.shape[0] < 10:
            error_msg = f'Insufficient samples: {data_array.shape[0]}'
            results['status'] = 'failed'
            results['error'] = error_msg
            status_data.update({'status': 'failed', 'error': error_msg, 'end_time': time.time()})
            redis_service.store_dr_task_status(cluster_id, status_data)
            return results
            
        if data_array.shape[1] < 2:
            error_msg = f'Insufficient features: {data_array.shape[1]}'
            results['status'] = 'failed'
            results['error'] = error_msg
            status_data.update({'status': 'failed', 'error': error_msg, 'end_time': time.time()})
            redis_service.store_dr_task_status(cluster_id, status_data)
            return results
        
        umap_hash = None
        tsne_hash = None
        
        # Compute UMAP
        try:
            print(f"[DR-Worker] Computing UMAP for cluster {cluster_id}")
            status_data['umap_status'] = 'processing'
            redis_service.store_dr_task_status(cluster_id, status_data)
            results['umap_status'] = 'processing'
            
            # Get the cache key that will be used for this computation
            umap_hash = UMAPOptimizationService.get_cache_key_for_computation(data_array, fast_mode=True)
            
            # Compute UMAP - this will use the same cache key we just calculated
            umap_result = UMAPOptimizationService.compute_umap_optimized(data_array, fast_mode=True)
            if umap_result is not None and len(umap_result) > 0:
                # Result is cached in Redis by the optimization service
                results['umap_result'] = umap_result if isinstance(umap_result, list) else umap_result.tolist()
                results['umap_status'] = 'completed'
                status_data['umap_status'] = 'completed'
                print(f"[DR-Worker] UMAP completed for cluster {cluster_id}, cached with hash {umap_hash}")
            else:
                results['umap_status'] = 'failed'
                status_data['umap_status'] = 'failed'
                umap_hash = None
                print(f"[DR-Worker] UMAP failed for cluster {cluster_id}")
        except Exception as e:
            results['umap_status'] = 'failed'
            status_data['umap_status'] = 'failed'
            umap_hash = None
            print(f"[DR-Worker] UMAP error for cluster {cluster_id}: {e}")
        
        # Update status after UMAP
        redis_service.store_dr_task_status(cluster_id, status_data)
        
        # Compute t-SNE
        try:
            print(f"[DR-Worker] Computing t-SNE for cluster {cluster_id}")
            status_data['tsne_status'] = 'processing'
            redis_service.store_dr_task_status(cluster_id, status_data)
            results['tsne_status'] = 'processing'
            
            # Get optimal parameters to generate hash
            tsne_params = TSNEOptimizationService._get_optimal_tsne_params(data_array.shape[0], data_array.shape[1], fast_mode=True)
            tsne_hash = TSNEOptimizationService._create_tsne_hash(data_array, tsne_params)
            
            tsne_result = TSNEOptimizationService.compute_tsne_optimized(data_array, fast_mode=True)
            if tsne_result is not None and len(tsne_result) > 0:
                # Result is cached in Redis by the optimization service
                results['tsne_result'] = tsne_result if isinstance(tsne_result, list) else tsne_result.tolist()
                results['tsne_status'] = 'completed'
                status_data['tsne_status'] = 'completed'
                print(f"[DR-Worker] t-SNE completed for cluster {cluster_id}, cached with hash {tsne_hash}")
            else:
                results['tsne_status'] = 'failed'
                status_data['tsne_status'] = 'failed'
                tsne_hash = None
                print(f"[DR-Worker] t-SNE failed for cluster {cluster_id}")
        except Exception as e:
            results['tsne_status'] = 'failed'
            status_data['tsne_status'] = 'failed'
            tsne_hash = None
            print(f"[DR-Worker] t-SNE error for cluster {cluster_id}: {e}")
        
        # Set final status
        end_time = time.time()
        results['status'] = 'completed'
        status_data.update({
            'status': 'completed',
            'end_time': end_time
        })
        
        # Store final status and metadata linking to cache keys
        redis_service.store_dr_task_status(cluster_id, status_data)
        redis_service.store_dr_result_metadata(cluster_id, umap_hash, tsne_hash)
        
        duration = end_time - start_time
        print(f"[DR-Worker] Completed DR processing for cluster {cluster_id} in {duration:.2f}s")
        
        return results
        
    except Exception as e:
        print(f"[DR-Worker] Overall error for cluster {cluster_id}: {e}")
        error_result = {
            'cluster_id': cluster_id,
            'status': 'failed',
            'error': str(e),
            'umap_status': 'failed',
            'tsne_status': 'failed'
        }
        
        # Store error status in Redis
        try:
            if 'redis_service' in locals():
                error_status = {
                    'cluster_id': cluster_id,
                    'status': 'failed',
                    'umap_status': 'failed',
                    'tsne_status': 'failed',
                    'error': str(e),
                    'end_time': time.time()
                }
                redis_service.store_dr_task_status(cluster_id, error_status)
        except:
            pass  # Don't fail if Redis update fails
        
        return error_result

# Old compute_dimensionality_reduction_background function removed - now using direct worker calls with data passing


@app.get("/api/cluster/{cluster_id}/result")
async def get_cluster_result(cluster_id: str):
    """
    Get complete clustering result including colors for a cluster ID
    
    Args:
        cluster_id: The cluster identifier
        
    Returns:
        Complete clustering result with colors
    """
    try:
        result = await dataset_repository.get_clustering_result(cluster_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Cluster result not found for ID: {cluster_id}")
        
        # Return the result section which contains all the clustering data
        return result.get('result', result)
        
    except Exception as e:
        logger.error(f"Error fetching cluster result {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cluster result: {str(e)}")

@app.get("/api/cluster/{cluster_id}/dimensionality-reduction/status")
def get_dimensionality_reduction_status(cluster_id: str):
    """
    Get the status of background dimensionality reduction computation.
    Uses Redis-first approach with fallback to in-memory storage.
    """
    print(f"[API] Status check for cluster {cluster_id}")
    
    # Try Redis first
    redis_task = redis_service.get_dr_task_status(cluster_id)
    if redis_task:
        print(f"[API] Found Redis task status for cluster {cluster_id}")
        response = {
            "status": redis_task.get('status', 'unknown'),
            "umap_status": redis_task.get('umap_status', 'unknown'),
            "tsne_status": redis_task.get('tsne_status', 'unknown'),
            "start_time": redis_task.get('start_time'),
            "end_time": redis_task.get('end_time'),
            "error": redis_task.get('error', ''),
            "cluster_exists": True,
            "source": "redis"
        }
        
        # Add progress information
        if redis_task.get('status') == 'processing':
            start_time = redis_task.get('start_time')
            if start_time:
                elapsed = time.time() - start_time
                response['elapsed_seconds'] = round(elapsed, 1)
            
            # Estimate progress based on completion status
            progress = 0
            if redis_task.get('umap_status') == 'completed':
                progress += 50
            elif redis_task.get('umap_status') == 'processing':
                progress += 25
                
            if redis_task.get('tsne_status') == 'completed':
                progress += 50
            elif redis_task.get('tsne_status') == 'processing':
                progress += 25
                
            response['progress_percent'] = progress
        
        return response
    
    # Fallback to in-memory storage (legacy support)
    print(f"[API] No Redis task found, checking in-memory storage for cluster {cluster_id}")
    print(f"[API] Available clusters in dimensionality_reduction_tasks: {list(dimensionality_reduction_tasks.keys())}")
    print(f"[API] Available clusters in cluster_results: {list(cluster_results.keys())}")
    
    # Check if task exists in memory
    if cluster_id not in dimensionality_reduction_tasks:
        # Check if cluster exists but no DR task started
        if cluster_id in cluster_results:
            return {
                "status": "not_started", 
                "message": "Dimensionality reduction not started for this cluster",
                "cluster_exists": True,
                "source": "memory"
            }
        else:
            return {
                "status": "not_found", 
                "message": "Cluster not found",
                "cluster_exists": False,
                "source": "memory"
            }
    
    task = dimensionality_reduction_tasks[cluster_id]
    
    # Provide detailed status information
    response = {
        "status": task['status'],
        "umap_status": task['umap_status'],
        "tsne_status": task['tsne_status'],
        "start_time": task.get('start_time'),
        "end_time": task.get('end_time'),
        "error": task.get('error'),
        "cluster_exists": True,
        "source": "memory"
    }
    
    # Add progress information
    if task['status'] == 'processing':
        start_time = task.get('start_time', time.time())
        elapsed = time.time() - start_time
        response['elapsed_seconds'] = round(elapsed, 1)
        
        # Estimate progress based on individual task status
        progress = 0
        if task['umap_status'] == 'completed':
            progress += 50
        elif task['umap_status'] == 'processing':
            progress += 25
            
        if task['tsne_status'] == 'completed':
            progress += 50
        elif task['tsne_status'] == 'processing':
            progress += 25
            
        response['progress_percent'] = progress
    
    return response


@app.get("/api/cluster/{cluster_id}/dimensionality-reduction/result")
def get_dimensionality_reduction_result(cluster_id: str):
    """
    Get the completed dimensionality reduction results from Redis cache.
    Returns partial results if available (e.g., UMAP completed but t-SNE still processing).
    """
    print(f"[API] Fetching DR results for cluster {cluster_id}")
    
    # Try Redis first
    redis_task = redis_service.get_dr_task_status(cluster_id)
    redis_metadata = redis_service.get_dr_result_metadata(cluster_id)
    
    umap_result = None
    tsne_result = None
    umap_status = 'unknown'
    tsne_status = 'unknown'
    overall_status = 'unknown'
    error = None
    source = 'redis'
    
    if redis_task:
        print(f"[API] Found Redis task status for cluster {cluster_id}")
        umap_status = redis_task.get('umap_status', 'unknown')
        tsne_status = redis_task.get('tsne_status', 'unknown')
        overall_status = redis_task.get('status', 'unknown')
        error = redis_task.get('error')
        
        # Fetch actual results from optimization service caches if completed
        if redis_metadata:
            if umap_status == 'completed' and redis_metadata.get('umap_key'):
                try:
                    import pickle
                    umap_key = redis_metadata['umap_key']
                    cached_data = redis_service.client.get(umap_key)
                    if cached_data:
                        cache_info = pickle.loads(cached_data)
                        umap_result = cache_info.get('embedding')
                        print(f"[API] Retrieved UMAP result from Redis cache: {umap_key}")
                    else:
                        print(f"[API] UMAP cache key {umap_key} not found in Redis")
                except Exception as e:
                    print(f"[API] Error retrieving UMAP from Redis: {e}")
            
            if tsne_status == 'completed' and redis_metadata.get('tsne_key'):
                try:
                    import pickle
                    tsne_key = redis_metadata['tsne_key']
                    cached_data = redis_service.client.get(tsne_key)
                    if cached_data:
                        cache_info = pickle.loads(cached_data)
                        tsne_result = cache_info.get('coordinates')
                        print(f"[API] Retrieved t-SNE result from Redis cache: {tsne_key}")
                    else:
                        print(f"[API] t-SNE cache key {tsne_key} not found in Redis")
                except Exception as e:
                    print(f"[API] Error retrieving t-SNE from Redis: {e}")
    
    # Fallback to in-memory storage if Redis doesn't have the data
    if not redis_task and cluster_id in dimensionality_reduction_tasks:
        print(f"[API] Falling back to in-memory storage for cluster {cluster_id}")
        task = dimensionality_reduction_tasks[cluster_id]
        umap_result = task['umap_result'] if task['umap_status'] == 'completed' else None
        tsne_result = task['tsne_result'] if task['tsne_status'] == 'completed' else None
        umap_status = task['umap_status']
        tsne_status = task['tsne_status']
        overall_status = task['status']
        error = task.get('error')
        source = 'memory'
    elif not redis_task:
        return {"error": "No dimensionality reduction task found for this cluster"}
    
    # Return available results, even if not all components are completed
    result = {
        "umap": umap_result,
        "tsne": tsne_result,
        "umap_status": umap_status,
        "tsne_status": tsne_status,
        "overall_status": overall_status,
        "source": source
    }
    
    # Add error information if available
    if error:
        result['error'] = error
    
    # Add data size information for frontend memory management
    if umap_result:
        result['umap_size'] = len(umap_result)
    if tsne_result:
        result['tsne_size'] = len(tsne_result)
    
    print(f"[API] Returning DR results for cluster {cluster_id}: UMAP={umap_status}, t-SNE={tsne_status}, source={source}")
    
    return result


@app.post("/api/cluster/{cluster_id}/dimensionality-reduction/compute")
def trigger_dimensionality_reduction(cluster_id: str):
    """
    Manually trigger dimensionality reduction computation for a cluster.
    """
    if cluster_id not in cluster_results:
        return {"error": "Cluster ID not found"}
    
    # Start background computation (non-blocking)
    try:
        # Get cluster data
        cluster_data = cluster_results[cluster_id]['data']
        if cluster_data is None:
            return {"error": "No data available for this cluster"}
        
        # Initialize task status in main process and Redis 
        start_time = time.time()
        status_data = {
            'status': 'processing',
            'umap_status': 'pending',
            'tsne_status': 'pending',
            'umap_result': None,
            'tsne_result': None,
            'start_time': start_time,
            'error': None
        }
        dimensionality_reduction_tasks[cluster_id] = status_data
        redis_service.store_dr_task_status(cluster_id, status_data)
        
        # Callback to handle worker results
        def handle_dr_results(future):
            try:
                worker_result = future.result()
                sync_dr_worker_results(cluster_id, worker_result)
                
                if worker_result and worker_result.get('cluster_id') in dimensionality_reduction_tasks:
                    cid = worker_result['cluster_id']
                    start_time = dimensionality_reduction_tasks[cid].get('start_time', time.time())
                    end_time = dimensionality_reduction_tasks[cid].get('end_time', time.time())
                    duration = end_time - start_time
                    logger.info(f"Manual DR completed for cluster {cid} in {duration:.2f}s")
            except BrokenProcessPool as exc:
                logger.error(f"[PoolReset] DR pool became unusable during manual DR for {cluster_id}: {exc}")
                reset_dr_pool(f"manual dr result retrieval ({cluster_id})")
                error_status = {'status': 'failed', 'error': 'Dimensionality reduction worker crashed. Pool restarted.', 'end_time': time.time()}
                if cluster_id in dimensionality_reduction_tasks:
                    dimensionality_reduction_tasks[cluster_id].update(error_status)
                redis_service.store_dr_task_status(cluster_id, error_status)
            except Exception as e:
                logger.error(f"Error handling manual DR results for cluster {cluster_id}: {e}")
                # Update both memory and Redis with error status
                error_status = {'status': 'failed', 'error': str(e), 'end_time': time.time()}
                if cluster_id in dimensionality_reduction_tasks:
                    dimensionality_reduction_tasks[cluster_id].update(error_status)
                redis_service.store_dr_task_status(cluster_id, error_status)
        
        # Submit worker with data directly to DR pool
        future = submit_dr_task(cluster_id, compute_dimensionality_reduction_worker, cluster_id, cluster_data)
        future.add_done_callback(handle_dr_results)
        logger.info(f"Successfully submitted manual DR task for cluster {cluster_id}")
    except Exception as e:
        logger.warning(f"Failed to start background dimensionality reduction: {e}")
        if cluster_id in dimensionality_reduction_tasks:
            dimensionality_reduction_tasks[cluster_id]['status'] = 'failed'
            dimensionality_reduction_tasks[cluster_id]['error'] = str(e)
        return {"error": f"Failed to start dimensionality reduction: {str(e)}"}
    
    return {"message": "Dimensionality reduction computation started", "cluster_id": cluster_id}


@app.delete("/api/cluster/{cluster_id}")
def delete_cluster_result(cluster_id: str):
    """
    Delete stored cluster result and associated dimensionality reduction tasks.
    """
    deleted_items = []
    
    if cluster_id in cluster_results:
        del cluster_results[cluster_id]
        deleted_items.append("cluster_result")
    
    if cluster_id in dimensionality_reduction_tasks:
        del dimensionality_reduction_tasks[cluster_id]
        deleted_items.append("dimensionality_reduction_task")
    
    if not deleted_items:
        return {"error": "Cluster ID not found"}
    
    return {"message": f"Deleted {', '.join(deleted_items)} for cluster {cluster_id}"}








@app.post("/api/abort/{operation_id}")
async def abort_operation(operation_id: str):
    """Immediately terminate a running operation by killing its process"""
    logger.info(f"Abort requested for operation: {operation_id}")
    
    if operation_id in active_processes:
        process_info = active_processes[operation_id]
        process = process_info['process']
        if process.is_alive():
            logger.info(f"Terminating process for operation: {operation_id}")
            process.terminate()
            process.join(timeout=2)  # Wait up to 2 seconds
            
            # Force kill if still alive
            if process.is_alive():
                logger.warning(f"Process {operation_id} didn't terminate gracefully, force killing")
                process.kill()
                process.join()
            
            # Clean up
            del active_processes[operation_id]
            logger.info(f"Process {operation_id} terminated successfully")
            return {"status": "aborted", "operation_id": operation_id}
        else:
            # Process already finished
            del active_processes[operation_id]
            return {"status": "already_finished", "operation_id": operation_id}
    else:
        logger.warning(f"Operation {operation_id} not found in active processes")
        return {"status": "not_found", "operation_id": operation_id}


# Global settings storage (in production, this would be a database)
