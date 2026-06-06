import numpy as np
import math
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.datasets import make_blobs, make_moons, make_circles
from sklearn.decomposition import PCA
from scipy.spatial.distance import cdist
import time
# UMAP availability is handled by UMAPOptimizationService
UMAP_AVAILABLE = True

from .clustering_service import ClusteringService
from .cluster_color_helper import ClusterColorHelper
from .cluster_params import ClusterParams
from .ship_cache_service import SHiPCacheService
from .toy_dataset_service import ToyDatasetService
from .umap_optimization_service import UMAPOptimizationService
from .tsne_optimization_service import TSNEOptimizationService
import sys, os
from typing import List, Dict, Any, Optional, Callable
import importlib.util
# --- Begin DISCO integration (v2) ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DISCO_PARENT_PATH = os.path.join(PROJECT_ROOT, 'DISCO-main')
DISCO_SRC_PATH = os.path.join(DISCO_PARENT_PATH, 'src')
for _p in [DISCO_PARENT_PATH, DISCO_SRC_PATH]:
    if _p not in sys.path:
        sys.path.append(_p)

disco_import_error = None

def _load_disco_score() -> Optional[Callable]:
    disco_file = os.path.join(DISCO_SRC_PATH, 'Evaluation', 'disco.py')
    if not os.path.isfile(disco_file):
        return None
    try:
        spec = importlib.util.spec_from_file_location('_disco', disco_file)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            return getattr(mod, 'disco_score', None)
    except Exception as ex:
        print(f"[KSelectionService] Direct disco import failed: {ex}")
    return None

try:
    from Evaluation.disco import disco_score  # type: ignore
    print('[KSelectionService] disco_score imported via Evaluation package')
except Exception as e:
    print(f"[KSelectionService] Standard import failed: {e}; trying direct file load")
    disco_score = _load_disco_score()  # type: ignore
    if disco_score is None:
        disco_import_error = e
        print(f"[KSelectionService] Could not load disco_score; DISCO metric disabled. {e}")
# --- End DISCO integration (v2) ---

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
        try:
            import SHiP
        except ImportError:
            print("Warning: SHiP framework not available. Using KMeans as fallback.")
            SHiP = None


class KSelectionService:

    @staticmethod
    def _sanitize_value(value):
        """Sanitize numeric values to ensure JSON serialization compatibility"""
        if math.isinf(value):
            return None  # Use None for infinite values, will be handled in frontend
        if math.isnan(value):
            return None  # Use None for NaN values
        return float(value)

    @staticmethod
    def analyze_k_range_sync(data, k_range, tree_type="DCTree", power=2.0, random_state=42):
        """Synchronous wrapper for analyze_k_range for use in process workers"""
        import asyncio
        return asyncio.run(KSelectionService.analyze_k_range(data, k_range, tree_type, power, random_state))
    
    @staticmethod
    async def analyze_k_range(data, k_range, tree_type="DCTree", power=2.0, random_state=42):
        """
        Analyze multiple k values and compute various metrics to determine optimal k.
        
        Args:
            data: Input data points (numpy array or list)
            k_range: Range of k values to test (list of integers)
            tree_type: Tree type for SHiP clustering
            power: Power parameter for SHiP clustering
            random_state: Random state for reproducibility
            
        Returns:
            Dictionary with analysis results including metrics and optimal k suggestions
        """
        start_time_total = time.time()
        X = np.array(data)
        
        print(f"[KSelectionService] Starting k-selection analysis for k_range={k_range}")
        print(f"[KSelectionService] Data shape: {X.shape}")
        
        # Pre-compute DC-Tree distances once for DISCO optimization
        dc_dists = None
        if not disco_import_error and len(X) > 0:
            try:
                print(f"[KSelectionService] Pre-computing DC-Tree distances for DISCO optimization...")
                print(f"[KSelectionService] Dataset info: {X.shape[0]} samples, {X.shape[1]} features")
                start_time_dctree = time.time()
                # Import DCTree directly from the DISCO module
                from Evaluation.dcdistances.dctree import DCTree
                dc_dists = DCTree(X, min_points=5, no_fastindex=False).dc_distances()
                end_time_dctree = time.time()
                dctree_time = end_time_dctree - start_time_dctree
                print(f"[KSelectionService] ✅ DC-Tree pre-computation completed in {dctree_time:.4f}s")
                print(f"[KSelectionService] 🚀 DISCO optimization active - will save ~{dctree_time * (len(k_range)-1):.4f}s per analysis")
            except Exception as e:
                print(f"[KSelectionService] DC-Tree pre-computation failed: {e}")
                dc_dists = None
        elif len(X) == 0:
            print(f"[KSelectionService] ⚠️  Cannot pre-compute DC-Tree for empty dataset")
        
        # Initialize result storage
        metrics = {
            'wcss': [],
            'silhouette': [],
            'davies_bouldin': [],
            'calinski_harabasz': [],
            'elbow_scores': [],
            'disco': []
        }
        
        cluster_results = []
        all_labels_for_disco = {}  # Store all clustering results for batch DISCO processing
        
        # Create SHiP object once for all k-values (major performance optimization)
        ship = None
        if SHiP is not None:
            try:
                print(f"[KSelectionService] Creating single SHiP object for all k-values...")
                start_time_ship_creation = time.time()
                
                # Get optimized config for dataset size (without k in construction)
                config = SHiPCacheService._get_optimized_config_for_dataset_size(len(X))
                config["optimize_tree"] = True  # Enable tree optimization
                
                # Create SHiP instance using cache service (reuse same SHiP object for all k-values)
                ship = SHiPCacheService.get_ship(data=X, tree_type=tree_type, config=config)
                end_time_ship_creation = time.time()
                print(f"[KSelectionService] SHiP object creation took {end_time_ship_creation - start_time_ship_creation:.4f} seconds")
                print(f"[KSelectionService] 🚀 SHiP object reuse optimization active - will save ~{(end_time_ship_creation - start_time_ship_creation) * (len(k_range)-1):.4f}s per analysis")
            except Exception as e:
                print(f"[KSelectionService] SHiP object creation failed: {e}")
                ship = None
        
        # Analyze each k value
        for k in k_range:
            start_time_k_loop = time.time()
            print(f"[KSelectionService] Analyzing k={k}")
            
            try:
                # Cluster with fixed k using the shared SHiP object (performance optimization)
                start_time_clustering = time.time()
                labels = await KSelectionService._cluster_with_fixed_k_using_ship(X, k, tree_type, power, random_state, ship)
                end_time_clustering = time.time()
                clustering_time = end_time_clustering - start_time_clustering
                actual_clusters = len(np.unique(labels))
                
                print(f"[KSelectionService] k={k}: Got {actual_clusters} clusters (clustering took {clustering_time:.4f}s)")
                
                # Store cluster result
                cluster_results.append({
                    'k': k,
                    'labels': labels.tolist() if hasattr(labels, 'tolist') else list(labels),
                    'n_clusters': actual_clusters
                })
                
                # Store labels for batch DISCO processing
                if not disco_import_error:
                    all_labels_for_disco[k] = labels
                
                # Calculate WCSS (Within-Cluster Sum of Squares)
                start_time_wcss = time.time()
                wcss = KSelectionService._calculate_wcss(X, labels)
                end_time_wcss = time.time()
                wcss_time = end_time_wcss - start_time_wcss
                metrics['wcss'].append(wcss)
                print(f"[KSelectionService] k={k}: WCSS computed in {wcss_time:.4f}s")
                
                # Calculate metrics only if we have more than 1 cluster and enough samples
                if actual_clusters > 1 and len(X) > actual_clusters:
                    try:
                        start_time_metrics = time.time()
                        
                        # Silhouette Score
                        start_time_sil = time.time()
                        sil_score = silhouette_score(X, labels)
                        end_time_sil = time.time()
                        metrics['silhouette'].append(sil_score)
                        
                        # Davies-Bouldin Index
                        start_time_db = time.time()
                        db_score = davies_bouldin_score(X, labels)
                        end_time_db = time.time()
                        metrics['davies_bouldin'].append(db_score)
                        
                        # Calinski-Harabasz Index
                        start_time_ch = time.time()
                        ch_score = calinski_harabasz_score(X, labels)
                        end_time_ch = time.time()
                        metrics['calinski_harabasz'].append(ch_score)
                        
                        end_time_metrics = time.time()
                        sil_time = end_time_sil - start_time_sil
                        db_time = end_time_db - start_time_db
                        ch_time = end_time_ch - start_time_ch
                        total_metrics_time = end_time_metrics - start_time_metrics
                        
                        print(f"[KSelectionService] k={k}: sil={sil_score:.3f} ({sil_time:.4f}s), db={db_score:.3f} ({db_time:.4f}s), ch={ch_score:.3f} ({ch_time:.4f}s)")
                        print(f"[KSelectionService] k={k}: All standard metrics computed in {total_metrics_time:.4f}s")
                        
                    except Exception as e:
                        print(f"[KSelectionService] Error calculating metrics for k={k}: {e}")
                        metrics['silhouette'].append(None)
                        metrics['davies_bouldin'].append(None)
                        metrics['calinski_harabasz'].append(None)
                else:
                    # Single cluster or insufficient samples
                    print(f"[KSelectionService] k={k}: Single cluster or insufficient samples, using None values")
                    metrics['silhouette'].append(None)
                    metrics['davies_bouldin'].append(None)
                    metrics['calinski_harabasz'].append(None)
                    
            except Exception as e:
                print(f"[KSelectionService] Error analyzing k={k}: {e}")
                # Add None values for failed clustering
                metrics['wcss'].append(None)
                metrics['silhouette'].append(None)
                metrics['davies_bouldin'].append(None)
                metrics['calinski_harabasz'].append(None)
                
                cluster_results.append({
                    'k': k,
                    'labels': [0] * len(X),
                    'n_clusters': 1
                })
                
            end_time_k_loop = time.time()
            print(f"[KSelectionService] k={k} analysis took {end_time_k_loop - start_time_k_loop:.4f} seconds")
        
        # Batch process DISCO scores for all k values (major performance optimization)
        if not disco_import_error and dc_dists is not None and all_labels_for_disco:
            print(f"[KSelectionService] 🚀 Starting batch DISCO processing for {len(all_labels_for_disco)} k-values...")
            start_time_batch_disco = time.time()
            
            disco_results = KSelectionService._calculate_disco_batch(X, all_labels_for_disco, dc_dists)
            
            # Add results to metrics in k_range order
            for k in k_range:
                if k in disco_results:
                    metrics['disco'].append(disco_results[k])
                else:
                    metrics['disco'].append(None)
            
            end_time_batch_disco = time.time()
            batch_disco_time = end_time_batch_disco - start_time_batch_disco
            valid_disco_count = len([x for x in metrics['disco'] if x is not None])
            print(f"[KSelectionService] ✅ Batch DISCO processing completed in {batch_disco_time:.4f}s")
            print(f"[KSelectionService] 📊 DISCO optimization results: {valid_disco_count}/{len(k_range)} valid scores computed")
        else:
            # Fill with None if batch processing not available
            reason = "import error" if disco_import_error else "no DC-Tree cache" if dc_dists is None else "no clustering results"
            print(f"[KSelectionService] ⚠️  Batch DISCO processing not available ({reason}), filling with None values")
            for k in k_range:
                metrics['disco'].append(None)
        
        # Calculate elbow scores
        elbow_scores = KSelectionService._calculate_elbow_scores(metrics['wcss'])
        metrics['elbow_scores'] = elbow_scores
        
        # Determine optimal k values using different methods
        optimal_k_suggestions = KSelectionService._suggest_optimal_k(k_range, metrics)
        
        end_time_total = time.time()
        print(f"[KSelectionService] Total analyze_k_range execution took {end_time_total - start_time_total:.4f} seconds")
        print(f"[KSelectionService] Optimal k suggestions: {optimal_k_suggestions}")

        # For datasets with 50+ features, skip the full feature data to reduce JSON size
        is_high_dimensional = X.shape[1] > 50
        if is_high_dimensional:
            print(f"[KSelectionService] Skipping full feature data for {X.shape[1]}-feature dataset to reduce JSON size")
            data_points = []
        else:
            data_points = X.tolist()
            
        # Compute PCA directly during analysis (not lazy loaded) with robust error handling
        pca_components = None
        if X.shape[1] >= 2 and X.shape[0] >= 2:
            try:
                print(f"[KSelectionService] Computing PCA for analysis: {X.shape[0]} samples, {X.shape[1]} features")
                
                # Validate data before PCA computation
                if np.any(np.isnan(X)) or np.any(np.isinf(X)):
                    print(f"[KSelectionService] Data contains NaN/Inf values, cleaning before PCA")
                    X_clean = np.copy(X)
                    X_clean = np.nan_to_num(X_clean, nan=0.0, posinf=1e10, neginf=-1e10)
                else:
                    X_clean = X
                
                # Check for sufficient variance
                variances = np.var(X_clean, axis=0)
                non_zero_var_features = np.sum(variances > 1e-10)
                
                if non_zero_var_features < 2:
                    print(f"[KSelectionService] Insufficient variance in features ({non_zero_var_features} features with variance), creating synthetic PCA")
                    # Create synthetic 2D projection for visualization
                    n_samples = X_clean.shape[0]
                    pca_components = np.random.randn(n_samples, 2).tolist()
                    print(f"[KSelectionService] Created synthetic 2D projection for visualization")
                else:
                    # Compute PCA with appropriate number of components
                    n_components = min(2, X_clean.shape[1], non_zero_var_features)
                    pca = PCA(n_components=n_components)
                    pca_result = pca.fit_transform(X_clean)
                    
                    # Ensure we always have 2D output for visualization
                    if pca_result.shape[1] == 1:
                        # If only 1 component, duplicate it with small noise for 2D visualization
                        pca_components = np.column_stack([
                            pca_result[:, 0], 
                            pca_result[:, 0] + np.random.normal(0, 0.01, len(pca_result))
                        ]).tolist()
                        print(f"[KSelectionService] Extended 1D PCA to 2D for visualization")
                    else:
                        pca_components = pca_result.tolist()
                    
                    explained_variance = np.sum(pca.explained_variance_ratio_)
                    print(f"[KSelectionService] PCA analysis completed successfully, explained variance: {explained_variance:.3f}")
                    
            except Exception as e:
                print(f"[KSelectionService] PCA computation failed with error: {e}")
                import traceback
                traceback.print_exc()
                print(f"[KSelectionService] Creating fallback 2D projection for visualization")
                try:
                    # Fallback: create a simple 2D projection using first two features or random projection
                    if X.shape[1] >= 2:
                        # Use first two features as fallback
                        pca_components = X[:, :2].tolist()
                        print(f"[KSelectionService] Using first two features as PCA fallback")
                    else:
                        # Single feature: duplicate with noise
                        feature_data = X[:, 0]
                        pca_components = np.column_stack([
                            feature_data,
                            feature_data + np.random.normal(0, np.std(feature_data) * 0.1, len(feature_data))
                        ]).tolist()
                        print(f"[KSelectionService] Created 2D projection from single feature")
                except Exception as fallback_error:
                    print(f"[KSelectionService] Fallback PCA also failed: {fallback_error}")
                    import traceback
                    traceback.print_exc()
                    # Last resort: create random 2D data for visualization
                    n_samples = X.shape[0]
                    pca_components = np.random.randn(n_samples, 2).tolist()
                    print(f"[KSelectionService] Created random 2D data as final fallback")
        elif X.shape[1] < 2:
            print(f"[KSelectionService] Single feature dataset, creating 2D projection")
            try:
                feature_data = X[:, 0]
                pca_components = np.column_stack([
                    feature_data,
                    np.random.normal(0, np.std(feature_data) * 0.1, len(feature_data))
                ]).tolist()
                print(f"[KSelectionService] Created 2D projection from single feature")
            except Exception as e:
                print(f"[KSelectionService] Single feature projection failed: {e}")
                n_samples = X.shape[0]
                pca_components = np.random.randn(n_samples, 2).tolist()
        elif X.shape[0] < 2:
            print(f"[KSelectionService] Insufficient samples for PCA ({X.shape[0]} samples)")
            pca_components = None
        
        # Ensure PCA components exist for visualization (critical for UX)
        if pca_components is None and X.shape[0] >= 2:
            print(f"[KSelectionService] PCA components still None, creating minimal fallback")
            pca_components = np.random.randn(X.shape[0], 2).tolist()
        
        # Skip UMAP/t-SNE computation during analysis for faster page load
        # They will be computed in background after analysis is complete (like clustering page)
        umap_components = None
        tsne_components = None
        
        if X.shape[1] > 2 and X.shape[0] >= 10:  # Any dataset > 2D with sufficient samples
            print(f"[KSelectionService] Deferring UMAP/t-SNE computation for {X.shape[1]}D dataset ({X.shape[0]} samples) - will be computed in background")
            print(f"[KSelectionService] Background UMAP/t-SNE will be available via polling after analysis completes")
        else:
            if X.shape[1] <= 2:
                print(f"[KSelectionService] Skipping UMAP/t-SNE for 2D dataset ({X.shape[1]}D)")
            else:
                print(f"[KSelectionService] Skipping UMAP/t-SNE due to insufficient samples ({X.shape[0]} samples)")
            print(f"[KSelectionService] Only PCA will be available for visualization")
        
        return {
            'k_values': k_range,
            'metrics': metrics,
            'optimal_k_suggestions': optimal_k_suggestions,
            'cluster_results': cluster_results,
            'data_points': data_points,
            'high_dimensional_dataset': X.shape[1] > 50,
            'original_feature_count': X.shape[1],
            'show_only_dr_methods': X.shape[1] > 50,
            'pca_components': pca_components,
            'umap_components': umap_components,
            'tsne_components': tsne_components
        }
    
    @staticmethod
    def reset_ship_cache():
        """Reset the cached SHiP objects (e.g., when a new dataset is loaded)."""
        SHiPCacheService.clear_cache()

    @staticmethod
    def _calculate_disco_optimized(X, labels, precomputed_dc_dists):
        """
        Calculate DISCO score using pre-computed DC-Tree distances for performance optimization.
        
        This method replicates the disco_samples logic but uses pre-computed DC-Tree distances
        to avoid the expensive DCTree computation for each k-value.
        
        Args:
            X: Input data points
            labels: Cluster labels
            precomputed_dc_dists: Pre-computed DC-Tree distance matrix
            
        Returns:
            Mean DISCO score (float)
        """
        try:
            # Import required functions from DISCO module
            from Evaluation.disco import p_cluster, p_noise
            
            labels = np.array(labels)
            if len(X) == 0:
                raise ValueError("Can't calculate DISCO score for empty dataset.")
            if len(X) != len(labels):
                raise ValueError("Dataset size differs from label size.")

            # Labels needs to be a one dimensional vector
            labels = np.reshape(labels, -1)
            label_set = set(labels)

            # Only noise
            if label_set == {-1}:
                return -1.0

            # One cluster without noise
            if len(label_set) == 1 and label_set != {-1}:
                return 0.0

            # One cluster with noise
            if len(label_set) == 2 and -1 in label_set:
                l_ = labels.copy()
                l_[l_ == -1] = np.arange(-1, -len(l_[l_ == -1]) - 1, -1)
                disco_values = np.empty(len(X))
                disco_values[labels != -1] = p_cluster(precomputed_dc_dists, l_, precomputed_dc_dists=True)[labels != -1]
                disco_values[labels == -1] = np.minimum(*p_noise(X, labels, min_points=5, dc_dists=precomputed_dc_dists))
                return float(np.mean(disco_values))

            # More than one cluster with optional noise
            else:
                disco_values = np.empty(len(X))
                non_noise_dc_dists = precomputed_dc_dists[np.ix_(labels != -1, labels != -1)]
                non_noise_labels = labels[labels != -1]
                disco_values[labels != -1] = p_cluster(non_noise_dc_dists, non_noise_labels, precomputed_dc_dists=True)
                
                if np.any(labels == -1):
                    disco_values[labels == -1] = np.minimum(*p_noise(X, labels, min_points=5, dc_dists=precomputed_dc_dists))
                
                return float(np.mean(disco_values))
                
        except Exception as e:
            print(f"[KSelectionService] Optimized DISCO calculation failed: {e}")
            # Fallback to standard disco_score if optimization fails
            return float(disco_score(X, labels))

    @staticmethod
    def _calculate_disco_batch(X, all_labels_dict, precomputed_dc_dists):
        """
        Calculate DISCO scores for multiple k-values in batch for maximum performance.
        
        This method processes all clustering results at once using the shared DC-Tree distances,
        providing significant performance improvements over sequential processing.
        
        Args:
            X: Input data points
            all_labels_dict: Dictionary mapping k -> cluster labels
            precomputed_dc_dists: Pre-computed DC-Tree distance matrix
            
        Returns:
            Dictionary mapping k -> DISCO score
        """
        results = {}
        
        try:
            print(f"[KSelectionService] Processing DISCO for k-values: {list(all_labels_dict.keys())}")
            
            # Process each k-value using the shared DC-Tree distances
            for k, labels in all_labels_dict.items():
                try:
                    start_time_k_disco = time.time()
                    disco_val = KSelectionService._calculate_disco_optimized(X, labels, precomputed_dc_dists)
                    end_time_k_disco = time.time()
                    k_disco_time = end_time_k_disco - start_time_k_disco
                    
                    results[k] = disco_val
                    print(f"[KSelectionService] Batch k={k}: DISCO={disco_val} (computed in {k_disco_time:.4f}s)")
                except Exception as e:
                    print(f"[KSelectionService] Batch DISCO error for k={k}: {e}")
                    results[k] = None
            
            return results
            
        except Exception as e:
            print(f"[KSelectionService] Batch DISCO processing failed: {e}")
            # Return empty dict to trigger fallback
            return {}

    @staticmethod
    def _cluster_with_fixed_k_sync(X, k, tree_type="DCTree", power=2.0, random_state=42):
        """Synchronous wrapper for _cluster_with_fixed_k for use in process workers"""
        import asyncio
        return asyncio.run(KSelectionService._cluster_with_fixed_k(X, k, tree_type, power, random_state))
    
    @staticmethod
    async def _cluster_with_fixed_k_using_ship(X, k, tree_type="DCTree", power=2.0, random_state=42, ship=None):
        """
        Cluster data with a fixed number of clusters k using provided SHiP object (optimized)
        """
        if k == 1:
            return np.zeros(len(X))
        
        # Try using the provided SHiP object first (major performance optimization)
        if ship is not None:
            try:
                print(f"[KSelectionService] Using shared SHiP object for k={k}")
                
                # Use PMethod.K with runtime k parameter
                runtime_config = {"k": k}
                ship.k = k
                labels = ship.fit_predict(int(power), PMethod.K, config=runtime_config)
                
                # Verify we got the right number of clusters
                actual_k = len(np.unique(labels))
                if actual_k == k:
                    print(f"[KSelectionService] Shared SHiP successfully clustered into k={k} clusters")
                    return labels
                else:
                    print(f"[KSelectionService] Shared SHiP returned {actual_k} clusters instead of {k}, falling back to individual SHiP")
                    
            except Exception as e:
                print(f"[KSelectionService] Shared SHiP clustering failed for k={k}: {e}")
        
        # Fallback to original method if shared SHiP fails
        return await KSelectionService._cluster_with_fixed_k(X, k, tree_type, power, random_state)

    @staticmethod
    async def _cluster_with_fixed_k(X, k, tree_type="DCTree", power=2.0, random_state=42):
        """
        Cluster data with a fixed number of clusters k using SHiP with PMethod.K
        """
        if k == 1:
            return np.zeros(len(X))
        
        # Try SHiP first with proper K-method configuration
        if SHiP is not None:
            try:
                print(f"[KSelectionService] Trying SHiP clustering with k={k}")
                start_time_ship_creation = time.time()
                
                # Get optimized config for dataset size (without k in construction)
                config = SHiPCacheService._get_optimized_config_for_dataset_size(len(X))
                config["optimize_tree"] = True  # Enable tree optimization

                print(f"[KSelectionService] Using config for k={k}: {config}")
                
                # Create SHiP instance using cache service (reuse same SHiP object for all k-values)
                ship = SHiPCacheService.get_ship(data=X, tree_type=tree_type, config=config)
                end_time_ship_creation = time.time()
                print(f"[KSelectionService] SHiP object creation for k={k} took {end_time_ship_creation - start_time_ship_creation:.4f} seconds")
                
                if ship is not None:
                    # Use PMethod.K with runtime k parameter
                    runtime_config = {"k": k}
                    ship.k = k  # Set k in SHiP object
                    labels = ship.fit_predict(int(power), PMethod.K, config=runtime_config)
                    
                    # Verify we got the right number of clusters
                    actual_k = len(np.unique(labels))
                    if actual_k == k:
                        print(f"[KSelectionService] SHiP successfully clustered into k={k} clusters")
                        return labels
                    else:
                        print(f"[KSelectionService] SHiP returned {actual_k} clusters instead of {k}, falling back to KMeans")
                        
            except Exception as e:
                print(f"[KSelectionService] SHiP clustering failed for k={k}: {e}")
        
        # Fallback to KMeans which guarantees exactly k clusters
        print(f"[KSelectionService] Using KMeans fallback for k={k}")
        kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(X)
        return labels
    
    @staticmethod
    def _calculate_wcss(X, labels):
        """Calculate Within-Cluster Sum of Squares"""
        wcss = 0
        unique_labels = np.unique(labels)
        
        for label in unique_labels:
            if label == -1:  # Skip noise points if any
                continue
                
            cluster_points = X[labels == label]
            if len(cluster_points) > 0:
                centroid = np.mean(cluster_points, axis=0)
                wcss += np.sum((cluster_points - centroid) ** 2)
        
        return float(wcss)
    
    @staticmethod
    def _calculate_elbow_scores(wcss_values):
        """Calculate elbow scores for elbow method"""
        # Filter out None values
        valid_wcss = [(i, wcss) for i, wcss in enumerate(wcss_values) if wcss is not None]
        
        if len(valid_wcss) < 3:
            return [0] * len(wcss_values)
        
        elbow_scores = [0] * len(wcss_values)
        
        # Calculate second derivative approximation only for valid values
        for i in range(1, len(valid_wcss) - 1):
            prev_idx, prev_wcss = valid_wcss[i-1]
            curr_idx, curr_wcss = valid_wcss[i]
            next_idx, next_wcss = valid_wcss[i+1]
            
            # Calculate second derivative approximation
            second_derivative = prev_wcss - 2*curr_wcss + next_wcss
            elbow_scores[curr_idx] = abs(second_derivative)
        
        return elbow_scores
    
    @staticmethod
    def _suggest_optimal_k(k_range, metrics):
        """Suggest optimal k values using different methods"""
        suggestions = {}
        
        # Elbow method - find the k with maximum elbow score
        if metrics['elbow_scores']:
            valid_elbow = [(i, score) for i, score in enumerate(metrics['elbow_scores']) if score > 0]
            if valid_elbow:
                max_elbow_idx = max(valid_elbow, key=lambda x: x[1])[0]
                suggestions['elbow'] = k_range[max_elbow_idx]
        
        # Silhouette method - find k with maximum silhouette score
        valid_silhouette = [(i, score) for i, score in enumerate(metrics['silhouette']) if score is not None]
        if valid_silhouette:
            best_sil_idx = max(valid_silhouette, key=lambda x: x[1])[0]
            suggestions['silhouette'] = k_range[best_sil_idx]
        
        # Davies-Bouldin method - find k with minimum Davies-Bouldin index
        valid_db = [(i, score) for i, score in enumerate(metrics['davies_bouldin']) if score is not None]
        if valid_db:
            best_db_idx = min(valid_db, key=lambda x: x[1])[0]
            suggestions['davies_bouldin'] = k_range[best_db_idx]
        
        # Calinski-Harabasz method - find k with maximum Calinski-Harabasz index
        valid_ch = [(i, score) for i, score in enumerate(metrics['calinski_harabasz']) if score is not None]
        if valid_ch:
            max_ch_idx = max(valid_ch, key=lambda x: x[1])[0]
            suggestions['calinski_harabasz'] = k_range[max_ch_idx]
        
        # DISCO method - find k with maximum DISCO score
        valid_disco = [(i, score) for i, score in enumerate(metrics['disco']) if score is not None]
        if valid_disco:
            max_disco_idx = max(valid_disco, key=lambda x: x[1])[0]
            suggestions['disco'] = k_range[max_disco_idx]
        
        return suggestions
    
    @staticmethod
    def generate_sample_data(sample_type='blobs', n_samples=200, random_state=42):
        """Generate sample data for k-selection analysis using ToyDatasetService"""
        print(f"[KSelectionService] Generating {sample_type} sample data with {n_samples} samples")

        # Use ToyDatasetService for comprehensive dataset support
        try:
            # Set appropriate defaults for different dataset types
            n_clusters = 3
            n_features = None

            # For high-dimensional datasets, set appropriate feature count
            if sample_type in ['hypercube', 'sparse_clusters', 'blobs_nd', 'classification_nd']:
                if sample_type == 'hypercube':
                    n_features = 8  # Default for hypercube
                elif sample_type == 'sparse_clusters':
                    n_features = 20
                elif sample_type in ['blobs_nd', 'classification_nd']:
                    n_features = 10

            X, X_true_labels = ToyDatasetService.generate_dataset(
                dataset_name=sample_type,
                n_samples=n_samples,
                n_clusters=n_clusters,
                n_features=n_features,
                random_state=random_state
            )
            print(f"[KSelectionService] Generated data shape: {X.shape}")
            # Return the actual numpy array for processing, not the serialized version
            return X
        except Exception as e:
            print(f"[KSelectionService] Failed to generate {sample_type} data: {e}, falling back to blobs")
            # Fallback to blobs if generation fails
            X, y = make_blobs(n_samples=n_samples, centers=4, random_state=random_state)
            print(f"[KSelectionService] Generated fallback data shape: {X.shape}")
            # Return the actual numpy array for processing
            return X
    
    @staticmethod
    def cluster_for_visualization_sync(data, n_clusters, tree_type="DCTree", power=2.0, random_state=42, skip_umap=False, skip_tsne=False, data_cache_id=None, cached_pca=None):
        """Synchronous wrapper for cluster_for_visualization for use in process workers"""
        import asyncio
        return asyncio.run(KSelectionService.cluster_for_visualization(data, n_clusters, tree_type, power, random_state, skip_umap, skip_tsne, data_cache_id, cached_pca))
    
    @staticmethod
    async def cluster_for_visualization(data, n_clusters, tree_type="DCTree", power=2.0, random_state=42, skip_umap=False, skip_tsne=False, data_cache_id=None, cached_pca=None):
        """
        Cluster data for visualization purposes with exact k clusters.
        This should use the SAME data and parameters as the k-selection analysis.
        
        Args:
            data: Input data points (should be the same as used in analyze_k_range)
            n_clusters: Number of clusters (will be exactly this many)
            tree_type: Tree type for clustering
            power: Power parameter
            random_state: Random state
            skip_umap: Skip UMAP computation for faster response (default: False)
            skip_tsne: Skip t-SNE computation for faster response (default: False)
            
        Returns:
            Dictionary with clustering results and dimensionality reduction
        """
        X = np.array(data)
        print(f"[KSelectionService] Clustering for visualization: k={n_clusters}, data_shape={X.shape}")
        
        # Use the same clustering method as in k-selection analysis
        labels = await KSelectionService._cluster_with_fixed_k(X, n_clusters, tree_type, power, random_state)
        actual_clusters = len(np.unique(labels))
        
        print(f"[KSelectionService] Visualization clustering resulted in {actual_clusters} clusters")
        
        # Calculate evaluation metrics
        evaluation_metrics = {}
        
        if actual_clusters > 1 and len(X) > actual_clusters:
            try:
                evaluation_metrics['silhouette_score'] = float(silhouette_score(X, labels))
                evaluation_metrics['db_index'] = float(davies_bouldin_score(X, labels))
                evaluation_metrics['calinski_harabasz'] = float(calinski_harabasz_score(X, labels))
                # Visualization metrics
                try:
                    if disco_import_error:
                        evaluation_metrics['disco_score'] = None
                        print(f"[KSelectionService] Visualization DISCO disabled (import error)")
                    else:
                        start_time_vis_disco = time.time()
                        evaluation_metrics['disco_score'] = float(disco_score(X, labels))
                        end_time_vis_disco = time.time()
                        vis_disco_time = end_time_vis_disco - start_time_vis_disco
                        print(f"[KSelectionService] Visualization DISCO={evaluation_metrics['disco_score']} (computed in {vis_disco_time:.4f}s)")
                except Exception as e:
                    print(f"[KSelectionService] Error calculating visualization DISCO: {e}")
                    import traceback; traceback.print_exc()
                    evaluation_metrics['disco_score'] = None
                print(f"[KSelectionService] Visualization metrics: sil={evaluation_metrics['silhouette_score']:.3f}")
            except Exception as e:
                print(f"[KSelectionService] Error calculating visualization metrics: {e}")
        
        # Create result
        # For datasets with 50+ features, skip the full feature data to reduce JSON size
        is_high_dimensional = X.shape[1] > 50
        if is_high_dimensional:
            print(f"[KSelectionService] Skipping full feature data for {X.shape[1]}-feature dataset to reduce JSON size")
            points_data = []
        else:
            points_data = X.tolist()
            
        result = {
            'points': points_data,
            'labels': labels.tolist() if hasattr(labels, 'tolist') else list(labels),
            'centers': [],
            'evaluation_metrics': evaluation_metrics,
            'high_dimensional_dataset': X.shape[1] > 50,
            'original_feature_count': X.shape[1],
            'show_only_dr_methods': X.shape[1] > 50
        }
        
        # Add dimensionality reduction
        pca_components = None
        umap_components = None
        tsne_components = None
        
        if X.shape[1] <= 2:
            # For 2D data, use raw coordinates (consistent with clustering_service)
            print(f"[KSelectionService] Using raw {X.shape[1]}D data as PCA components (no transformation needed)")
            pca_components = X.tolist()
        elif X.shape[1] > 2:
            # PCA - use cached results if available, otherwise compute (always fast)
            if cached_pca is not None:
                print(f"[KSelectionService] Using cached PCA results from k-selection analysis")
                pca_components = cached_pca
            else:
                try:
                    print(f"[KSelectionService] Computing PCA for {X.shape[0]} samples, {X.shape[1]} features")
                    
                    # Clean data for PCA computation
                    X_clean = X.copy()
                    if np.any(np.isnan(X_clean)) or np.any(np.isinf(X_clean)):
                        print(f"[KSelectionService] Cleaning data for PCA computation")
                        X_clean = np.nan_to_num(X_clean, nan=0.0, posinf=1e10, neginf=-1e10)
                    
                    # Check for sufficient variance
                    variances = np.var(X_clean, axis=0)
                    non_zero_var_features = np.sum(variances > 1e-10)
                    
                    if non_zero_var_features < 2:
                        print(f"[KSelectionService] Insufficient variance in features ({non_zero_var_features} features with variance), using first two features")
                        pca_components = X_clean[:, :2].tolist()
                    else:
                        n_components = min(2, X_clean.shape[1], non_zero_var_features)
                        pca = PCA(n_components=n_components)
                        pca_result = pca.fit_transform(X_clean)
                        
                        # Ensure we always have 2D output for visualization
                        if pca_result.shape[1] == 1:
                            # If only 1 component, duplicate it with small noise for 2D visualization
                            pca_components = np.column_stack([
                                pca_result[:, 0], 
                                pca_result[:, 0] + np.random.normal(0, 0.01, len(pca_result))
                            ]).tolist()
                            print(f"[KSelectionService] Extended 1D PCA to 2D for visualization")
                        else:
                            pca_components = pca_result.tolist()
                        
                        explained_variance = np.sum(pca.explained_variance_ratio_)
                        print(f"[KSelectionService] PCA completed successfully, explained variance: {explained_variance:.3f}")
                        
                except Exception as e:
                    print(f"[KSelectionService] PCA computation failed: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Fallback: use first two features or create synthetic data
                    try:
                        if X.shape[1] >= 2:
                            pca_components = X[:, :2].tolist()
                            print(f"[KSelectionService] Using first two features as PCA fallback")
                        else:
                            # Single feature: duplicate with noise
                            feature_data = X[:, 0]
                            pca_components = np.column_stack([
                                feature_data,
                                feature_data + np.random.normal(0, np.std(feature_data) * 0.1, len(feature_data))
                            ]).tolist()
                            print(f"[KSelectionService] Created 2D projection from single feature")
                    except Exception as fallback_error:
                        print(f"[KSelectionService] PCA fallback also failed: {fallback_error}")
                        # Last resort: create random 2D data
                        pca_components = np.random.randn(X.shape[0], 2).tolist()
                        print(f"[KSelectionService] Created random 2D data as final fallback")
                
            # UMAP - always skip in cluster_for_visualization, will be computed in background
            if not skip_umap and UMAP_AVAILABLE and X.shape[0] >= 10 and X.shape[1] >= 2:
                print(f"[KSelectionService] Skipping UMAP computation - will be computed in background for better performance")
            elif skip_umap:
                print(f"[KSelectionService] Skipping UMAP computation (skip_umap=True) for performance")
            else:
                print(f"Skipping UMAP: data conditions not met (samples={X.shape[0]}, features={X.shape[1]})")
            
            umap_components = None  # Always null, background will provide UMAP
                
            # t-SNE - always skip in cluster_for_visualization, will be computed in background
            if not skip_tsne and X.shape[0] >= 10 and X.shape[1] >= 2:
                print(f"[KSelectionService] Skipping t-SNE computation - will be computed in background for better performance")
            elif skip_tsne:
                print(f"[KSelectionService] Skipping t-SNE computation (skip_tsne=True) for performance")
            else:
                print(f"Skipping t-SNE: data conditions not met (samples={X.shape[0]}, features={X.shape[1]})")
            
            tsne_components = None  # Always null, background will provide t-SNE
        
        result['dimensionality_reduction'] = {
            "pca": pca_components,
            "umap": umap_components,
            "tsne": tsne_components
        }
        
        # Add colors for visualization using the same helper as regular clustering
        try:
            color_helper = ClusterColorHelper(labels=labels, tree=None)
            color_map = getattr(color_helper, 'label_to_color', {}) or {}
            scatter_colors = color_helper.get_color_list_for_labels(labels)
            result['color_map'] = color_map
            result['scatter_colors'] = scatter_colors
        except Exception as color_error:
            print(f"[KSelectionService] Failed to assign colors via ClusterColorHelper: {color_error}")
            # Fallback simple mapping to ensure result contains fields
            unique_labels = np.unique(labels)
            fallback_map = {str(l): '#cccccc' for l in unique_labels}
            result['color_map'] = fallback_map
            result['scatter_colors'] = [fallback_map.get(str(l), '#cccccc') for l in labels]

        return result


__all__ = ["KSelectionService"]
