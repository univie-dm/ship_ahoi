from pydantic import BaseModel
import numpy as np
import json
import math
from sklearn.metrics import adjusted_rand_score, silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.datasets import make_blobs
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from scipy.stats import spearmanr
try:
    import umap.umap_ as umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    print("Warning: UMAP not available. Please install umap-learn to use UMAP dimensionality reduction.")
from .cluster_params import ClusterParams
from .cluster_color_helper import ClusterColorHelper
from .ship_cache_service import SHiPCacheService
from .ship_exceptions import SHiPTreeGenerationError

from .umap_optimization_service import UMAPOptimizationService
from .tsne_optimization_service import TSNEOptimizationService
from .toy_dataset_service import ToyDatasetService
import time
from typing import Dict, Any, List, Optional, Callable
import sys, os
import importlib.util
# --- Begin DISCO integration ---
# Ensure DISCO framework source path is on sys.path so we can import `disco_score`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DISCO_PARENT_PATH = os.path.join(PROJECT_ROOT, 'DISCO-main')
DISCO_SRC_PATH = os.path.join(DISCO_PARENT_PATH, 'src')
for _p in [DISCO_PARENT_PATH, DISCO_SRC_PATH]:
    if _p not in sys.path:
        sys.path.append(_p)

disco_import_error = None

def _load_disco_score() -> Optional[Callable]:
    """Attempt to load disco_score directly from file to avoid heavy imports."""
    disco_file = os.path.join(DISCO_SRC_PATH, 'Evaluation', 'disco.py')
    if not os.path.isfile(disco_file):
        return None
    try:
        spec = importlib.util.spec_from_file_location("_disco", disco_file)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            return getattr(mod, 'disco_score', None)
    except Exception as ex:
        print(f"[ClusteringService] Direct disco import failed: {ex}")
    return None

try:
    # First try normal package import (may fail if deps missing)
    from Evaluation.disco import disco_score  # type: ignore
    print('[ClusteringService] disco_score imported via Evaluation package')
except Exception as e:
    print(f"[ClusteringService] Standard import failed: {e}; trying direct file load")
    disco_score = _load_disco_score()  # type: ignore
    if disco_score is None:
        disco_import_error = e
        print(f"[ClusteringService] Could not load disco_score; DISCO metric disabled. {e}")
# --- End DISCO integration ---

try:
    from SHiP_framework import SHiP
    from SHiP_framework.logger import LogLevel, setLogLevel
    from SHiP_framework.ultrametric_tree import UltrametricTreeType as UTreeType, AVAILABLE_ULTRAMETRIC_TREE_TYPES
    from SHiP_framework.partitioning import PartitioningMethod as PMethod, AVAILABLE_PARTITIONING_METHODS
except ImportError:
    try:
        from SHiP import SHiP
        from SHiP.logger import LogLevel, setLogLevel
        from SHiP.ultrametric_tree import UltrametricTreeType as UTreeType, AVAILABLE_ULTRAMETRIC_TREE_TYPES
        from SHiP.partitioning import PartitioningMethod as PMethod, AVAILABLE_PARTITIONING_METHODS
    except ImportError:
        try:
            import SHiP
        except ImportError:
            raise ImportError("SHiP framework is not installed. Please install it using 'pip install SHiP'.")


class ClusteringService:
    @staticmethod
    def _sanitize_array_for_json(arr: np.ndarray) -> list:
        """
        Sanitize numpy array for JSON serialization by replacing NaN and Inf values with None.
        
        Args:
            arr: Numpy array to sanitize
            
        Returns:
            Python list with NaN/Inf replaced by None
        """
        if not isinstance(arr, np.ndarray):
            return arr
        
        # Replace NaN and Inf with finite values for conversion
        arr_clean = np.copy(arr)
        
        # Replace NaN with 0 or a sentinel value (we'll convert to None later)
        nan_mask = np.isnan(arr_clean)
        inf_mask = np.isinf(arr_clean)
        
        # Convert to list first
        result = arr_clean.tolist()
        
        # Replace NaN and Inf positions with None in the result list
        if arr.ndim == 1:
            for i in range(len(result)):
                if (nan_mask[i] if nan_mask.ndim > 0 else nan_mask) or \
                   (inf_mask[i] if inf_mask.ndim > 0 else inf_mask):
                    result[i] = None
        elif arr.ndim == 2:
            for i in range(len(result)):
                for j in range(len(result[i])):
                    if nan_mask[i, j] or inf_mask[i, j]:
                        result[i][j] = None
        # For higher dimensions, let the JSON encoder handle it
        
        return result
    
    @staticmethod
    def create_from_tree(tree_json: dict, data: np.ndarray, k: int = 3, power: float = 0.0, partition_method: str = "K", dataset_available: bool = True) -> dict:
        """
        Create a clustering result from a pure tree JSON structure using LoadTree.
        
        Args:
            tree_json: Pure tree JSON structure (as exported from SHiP)
            data: The dataset to cluster
            k: Number of clusters
            power: Power parameter
            partition_method: Partitioning method
            
        Returns:
            Clustering result dictionary
        """
        start_time_total = time.time()
        
        try:
            # If dataset is not available, create a minimal result for tree display only
            if not dataset_available:
                print(f"[ClusteringService] Dataset not available, creating minimal result for tree display")
                print(f"[ClusteringService] Tree JSON keys: {list(tree_json.keys()) if isinstance(tree_json, dict) else 'Not a dict'}")
                
                # Extract basic tree structure for display
                # Keep tree as object, no need to serialize it here
                
                # Ensure we return the tree structure properly
                tree_data_for_display = tree_json
                if isinstance(tree_json, dict) and 'root' in tree_json:
                    tree_data_for_display = tree_json
                    print(f"[ClusteringService] Tree has root node, returning full structure")
                else:
                    print(f"[ClusteringService] Warning: Tree structure may be incomplete")
                
                return {
                    "labels": [],  # Empty labels since no data
                    "points": [],  # Empty points since no data
                    "tree": tree_data_for_display,  # Keep as object
                    "node_to_data_mapping": {},
                    "silhouette_score": 0.0,
                    "davies_bouldin_score": 0.0,
                    "calinski_harabasz_score": 0.0,
                    "processing_time": time.time() - start_time_total,
                    "metadata": {
                        "tree_type": "LoadTree",
                        "config": {},
                        "dataset_available": False,
                        "display_only": True
                    },
                    "loaded_from_tree": True,
                    "actual_cluster_count": k
                }
            # Create temporary file for tree JSON
            import tempfile
            import os
            
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(tree_json, temp_file)
                    temp_file_path = temp_file.name
                
                # Validate that the temporary file was created and contains data
                if not temp_file_path or not os.path.exists(temp_file_path):
                    raise ValueError("Failed to create temporary JSON tree file")
                
                # Validate file content
                if os.path.getsize(temp_file_path) == 0:
                    raise ValueError("Temporary JSON tree file is empty")
                
                # Create SHiP object with LoadTree and pass parameters directly for faster creation
                print(f"[ClusteringService] Creating SHiP object with tree_type: LoadTree, k={k}, power={power}")
                
                # Extract config from tree_json and merge with LoadTree config
                tree_config = tree_json.get("config", {})
                ship_config = {
                    "json_tree_filepath": temp_file_path,
                    **tree_config  # Include original tree config for optimized creation
                }
                
                # Create SHiP object with all parameters for faster processing
                ship = SHiP(
                    data=data,
                    treeType="LoadTree",
                    config=ship_config,
                    power=power,  # Pass power parameter directly
                    partitioningMethod=partition_method  # Pass partition method directly
                )
                
                print(f"[ClusteringService] SHiP object created with optimized parameters: {list(ship_config.keys())}")
                
                # Perform clustering
                labels = ship.fit_predict(k=k)
                
                # Get the loaded tree
                loaded_tree = ship.get_tree().to_json(fast_index=True)
                json_tree = ClusteringService._safe_json_parse(loaded_tree)
                
                # Extract node mapping
                node_to_data_mapping = ClusteringService.extract_node_to_data_mapping(json_tree)
                
                # Color the tree
                color_helper = ClusterColorHelper()
                colored_tree = color_helper.color_tree_by_clusters(json_tree, labels, node_to_data_mapping)
                
                # Calculate metrics
                silhouette_avg = silhouette_score(data, labels) if len(set(labels)) > 1 else 0
                davies_bouldin_avg = davies_bouldin_score(data, labels) if len(set(labels)) > 1 else 0
                calinski_harabasz_avg = calinski_harabasz_score(data, labels) if len(set(labels)) > 1 else 0
                
                # Calculate disco score if available
                disco_avg = None
                try:
                    if disco_score and len(set(labels)) > 1:
                        disco_avg = disco_score(data, labels)
                        disco_avg = float(disco_avg) if disco_avg is not None else None
                except Exception as e:
                    print(f"[ClusteringService] Could not calculate DISCO Score in LoadTree: {e}")
                    disco_avg = None
                
                # Calculate ARI if ground truth labels are available (note: LoadTree typically doesn't have ground truth)
                ari_score = None
                # For LoadTree, we typically don't have ground truth labels, so ARI would be None
                
                # Process results
                end_time_total = time.time()
                processing_time = end_time_total - start_time_total
                
                # Save correct parameters in metadata
                result_metadata = {
                    "tree_type": tree_json.get("tree_type", "LoadTree"),
                    "config": tree_config,  # Original tree config without power parameter
                    "clustering_parameters": {
                        "k": k,
                        "power": power,
                        "partition_method": partition_method
                    },
                    "loaded_from_tree": True,
                    "optimized_creation": True,
                    "processing_time": processing_time
                }
                
                result = {
                    "labels": ClusteringService._sanitize_array_for_json(labels),
                    "points": ClusteringService._sanitize_array_for_json(data),
                    "tree": colored_tree,  # Keep as object, not string
                    "node_to_data_mapping": node_to_data_mapping,
                    "silhouette_score": silhouette_avg,
                    "davies_bouldin_score": davies_bouldin_avg,
                    "calinski_harabasz_score": calinski_harabasz_avg,
                    "disco_score": disco_avg,
                    "ari": ari_score,
                    "processing_time": processing_time,
                    "metadata": result_metadata
                }
                
                print(f"[ClusteringService] LoadTree clustering completed in {processing_time:.3f}s with optimized SHiP creation")
                
                return result
                
            except Exception as inner_error:
                # Clean up temporary file in case of inner exception
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_error:
                        print(f"[ClusteringService] Warning: Failed to cleanup temporary file {temp_file_path}: {cleanup_error}")
                raise inner_error
                
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_error:
                        print(f"[ClusteringService] Warning: Failed to cleanup temporary file {temp_file_path}: {cleanup_error}")
                
        except Exception as e:
            print(f"[ClusteringService] Error in create_from_tree: {e}")
            raise ValueError(f"Failed to create clustering from tree: {str(e)}")
    
    @staticmethod
    def get_pure_tree_json(run_data: dict) -> dict:
        """
        Extract pure tree JSON from run data without power parameter for clean export.
        
        Args:
            run_data: Run data containing tree information
            
        Returns:
            Pure tree JSON structure without power parameter
        """
        try:
            print(f"[ClusteringService] Processing run data with keys: {list(run_data.keys())}")
            
            # Initialize variables
            tree_data = None
            tree_type = "DCTree"
            config = {}
            
            # Handle different data structures
            if "result" in run_data:
                # Regular clustering result structure: {'result': {...}, 'timestamp': ..., 'data': ...}
                result = run_data["result"]
                print(f"[ClusteringService] Found result structure with keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                
                # Extract tree data from result
                if isinstance(result, dict):
                    if "tree" in result:
                        tree_str = result["tree"]
                        if isinstance(tree_str, str):
                            tree_data = ClusteringService._safe_json_parse(tree_str)
                        else:
                            tree_data = tree_str
                        print(f"[ClusteringService] Extracted tree from result.tree")
                    
                    # Extract metadata without power parameter
                    tree_type = result.get("tree_type", "DCTree")
                    original_config = result.get("config", {})
                    
                    # Clean config by removing power parameter for pure tree export
                    config = {k: v for k, v in original_config.items() if k != "power"}
                    
            elif "treeData" in run_data:
                # Tree import structure: direct keys like treeData, treeType, etc.
                tree_data = run_data["treeData"]
                tree_type = run_data.get("treeType", "DCTree")
                original_config = run_data.get("parameters", {})
                
                # Clean config by removing power parameter
                config = {k: v for k, v in original_config.items() if k != "power"}
                print(f"[ClusteringService] Found direct treeData structure")
                
            elif "tree" in run_data:
                # Direct tree structure
                tree_str = run_data["tree"]
                if isinstance(tree_str, str):
                    tree_data = ClusteringService._safe_json_parse(tree_str)
                else:
                    tree_data = tree_str
                tree_type = run_data.get("treeType", "DCTree")
                original_config = run_data.get("parameters", {})
                
                # Clean config by removing power parameter
                config = {k: v for k, v in original_config.items() if k != "power"}
                print(f"[ClusteringService] Found direct tree structure")
            
            if not tree_data:
                print(f"[ClusteringService] No tree data found in any expected location")
                raise ValueError("No tree data found in run")
            
            print(f"[ClusteringService] Tree data type: {type(tree_data)}")
            if isinstance(tree_data, dict):
                print(f"[ClusteringService] Tree data keys: {list(tree_data.keys())}")
            
            # Ensure tree_data has the required structure
            if not isinstance(tree_data, dict):
                raise ValueError("Tree data is not a dictionary")
                
            # Extract pure tree structure without power parameter
            # Generate index_order if missing - collect all point indices from tree
            index_order = tree_data.get("index_order", [])
            if not index_order:
                # Recursively collect all point indices from the tree
                def collect_point_indices(node):
                    indices = []
                    if "pointIndices" in node:
                        indices.extend(node["pointIndices"])
                    if "children" in node:
                        for child in node["children"]:
                            indices.extend(collect_point_indices(child))
                    return indices
                
                root_node = tree_data.get("root", {})
                if root_node:
                    all_indices = collect_point_indices(root_node)
                    # Remove duplicates and sort
                    index_order = sorted(list(set(all_indices)))
                    print(f"[ClusteringService] Generated index_order with {len(index_order)} indices")
            
            pure_tree = {
                "tree_type": tree_type,
                "config": config,  # Config already cleaned of power parameter
                "index_order": index_order,
                "root": tree_data.get("root", {})
            }
            
            # Validate that we have a root node
            if not pure_tree["root"]:
                raise ValueError("No root node found in tree data")
            
            print(f"[ClusteringService] Successfully extracted pure tree with tree_type: {tree_type}, config keys: {list(config.keys())}")
            return pure_tree
            
        except Exception as e:
            print(f"[ClusteringService] Error extracting pure tree: {e}")
            print(f"[ClusteringService] Run data keys: {list(run_data.keys())}")
            
            # Additional debugging information
            if "result" in run_data and isinstance(run_data["result"], dict):
                result_keys = list(run_data["result"].keys())
                print(f"[ClusteringService] Result keys: {result_keys}")
                
                # Look for any key that might contain tree data
                for key in result_keys:
                    if "tree" in key.lower():
                        tree_val = run_data["result"][key]
                        print(f"[ClusteringService] Found tree-like key '{key}' with type: {type(tree_val)}")
                        if isinstance(tree_val, str):
                            print(f"[ClusteringService] {key} length: {len(tree_val)} characters")
                
                if "tree" in run_data["result"]:
                    tree_val = run_data["result"]["tree"]
                    print(f"[ClusteringService] Result.tree type: {type(tree_val)}")
                    if isinstance(tree_val, str):
                        print(f"[ClusteringService] Result.tree length: {len(tree_val)} characters")
            
            if "treeData" in run_data:
                tree_data_val = run_data["treeData"]
                print(f"[ClusteringService] TreeData type: {type(tree_data_val)}")
                if isinstance(tree_data_val, dict):
                    print(f"[ClusteringService] TreeData keys: {list(tree_data_val.keys())}")
            
            raise ValueError(f"Failed to extract pure tree: {str(e)}")

    @staticmethod
    def cluster_data_sync(params: ClusterParams, app_settings=None):
        """Synchronous wrapper for cluster_data for use in process workers"""
        import asyncio
        return asyncio.run(ClusteringService.cluster_data(params, app_settings))
    
    @staticmethod
    async def cluster_data(params: ClusterParams, app_settings=None):
        # Load data based on user selection or upload
        start_time_total = time.time()
        X_true_labels = None # Initialize true labels
        start_time_data_load = time.time()
        if params.data is not None:
            try:
                raw_data = np.array(params.data)
                print(f"[ClusteringService] Raw uploaded data shape: {raw_data.shape}")
                
                if params.isPreprocessed:
                    # Data is already preprocessed by the frontend
                    print(f"[ClusteringService] Using preprocessed data with {len(params.featureHeaders or [])} features")
                    
                    # Strip header row if present
                    if params.hasHeaders:
                        print(f"[ClusteringService] Stripping header row from data (shape before: {raw_data.shape})")
                        raw_data = raw_data[1:]  # Remove first row (headers)
                        print(f"[ClusteringService] Data shape after header removal: {raw_data.shape}")
                    
                    # Validate data contains only numeric values
                    try:
                        X = raw_data.astype(float)
                    except (ValueError, TypeError) as e:
                        # Data marked as preprocessed but still contains non-numeric values
                        # Try automatic fallback processing
                        print(f"[ClusteringService] Preprocessed data validation failed, attempting fallback processing")
                        
                        try:
                            # Attempt automatic categorical encoding
                            import pandas as pd
                            from server.data_processing_service import DataProcessingService
                            from server.cluster_params import DataProcessingConfig, CategoricalEncoding, DataType
                            
                            # Create headers if not available
                            if params.featureHeaders:
                                headers = params.featureHeaders
                            else:
                                headers = [f"Feature_{i}" for i in range(raw_data.shape[1])]
                            
                            # Convert to DataFrame for processing
                            df = pd.DataFrame(raw_data, columns=headers)
                            
                            # Detect categorical columns
                            column_configs = []
                            for i, col in enumerate(headers):
                                if DataProcessingService._is_categorical_column(df[col]):
                                    column_configs.append({
                                        'index': i,
                                        'name': col,
                                        'data_type': DataType.categorical,
                                        'is_categorical': True,
                                        'usage': 'feature'
                                    })
                            
                            if column_configs:
                                print(f"[ClusteringService] Detected {len(column_configs)} categorical columns for fallback processing")
                                
                                # Create processing config
                                processing_config = DataProcessingConfig(
                                    categorical_encoding=CategoricalEncoding.label,
                                    feature_columns=list(range(len(headers))),
                                    columns=column_configs
                                )
                                
                                # Process the data
                                processed_result = DataProcessingService.process_data(
                                    raw_data=ClusteringService._sanitize_array_for_json(raw_data),
                                    headers=headers,
                                    processing_config=processing_config
                                )
                                
                                if processed_result and processed_result.get("data"):
                                    # Use processed data
                                    X = np.array(processed_result["data"]).astype(float)
                                    print(f"[ClusteringService] Fallback processing successful. New shape: {X.shape}")
                                else:
                                    raise ValueError("Fallback processing failed to produce data")
                            else:
                                raise ValueError("No categorical columns detected for fallback processing")
                        
                        except Exception as fallback_error:
                            print(f"[ClusteringService] Fallback processing failed: {fallback_error}")
                            
                            # Find and report non-numeric values
                            non_numeric_values = []
                            for i, row in enumerate(raw_data[:5]):  # Check first 5 rows
                                for j, value in enumerate(row[:5]):  # Check first 5 columns
                                    try:
                                        float(value)
                                    except (ValueError, TypeError):
                                        non_numeric_values.append(f"Row {i+1}, Col {j+1}: '{value}'")
                            
                            error_msg = f"Data contains non-numeric values that cannot be converted to float. "
                            if non_numeric_values:
                                error_msg += f"Examples: {', '.join(non_numeric_values[:3])}"
                                if params.hasHeaders:
                                    error_msg += " (Note: Header stripping was applied)"
                            else:
                                error_msg += f"Original error: {str(e)}"
                            
                            error_msg += "\n\nThis typically happens when your data contains categorical values (like text or categories) that need to be encoded as numbers before clustering."
                            error_msg += "\nPlease use the data upload page to properly process your categorical data with one-hot encoding or label encoding."
                            
                            print(f"[ClusteringService] {error_msg}")
                            raise ValueError(error_msg)
                    
                    # Extract ground truth labels if provided
                    # Prioritize labelData (pre-extracted discrete labels) over groundTruthColumn (normalized data)
                    if params.labelData is not None:
                        try:
                            X_true_labels = np.array(params.labelData)
                            print(f"[ClusteringService] Ground truth labels provided from labelData: shape {X_true_labels.shape}")
                        except (ValueError, TypeError) as e:
                            print(f"[ClusteringService] Warning: Could not parse label data for ARI calculation: {e}")
                            X_true_labels = None
                    elif params.groundTruthColumn is not None:
                        try:
                            X_true_labels = raw_data[:, params.groundTruthColumn]
                            print(f"[ClusteringService] Ground truth labels provided from column {params.groundTruthColumn}: shape {X_true_labels.shape}")
                        except (ValueError, TypeError, IndexError) as e:
                            print(f"[ClusteringService] Warning: Could not parse ground truth data from column {params.groundTruthColumn}: {e}")
                            X_true_labels = None
                    
                    # Log feature information if available
                    if params.featureHeaders:
                        print(f"[ClusteringService] Feature columns: {params.featureHeaders}")
                    if params.dataConfig:
                        print(f"[ClusteringService] Data configuration: {params.dataConfig}")
                else:
                    # Raw data processing - attempt automatic categorical encoding
                    print("[ClusteringService] Processing raw data - attempting categorical encoding")
                    
                    # First, try to use proper categorical encoding
                    try:
                        import pandas as pd
                        from server.data_processing_service import DataProcessingService
                        from server.cluster_params import DataProcessingConfig, CategoricalEncoding, DataType
                        
                        # Create headers if not available
                        if params.featureHeaders:
                            headers = params.featureHeaders
                        else:
                            headers = [f"Feature_{i}" for i in range(raw_data.shape[1])]
                        
                        # Convert to DataFrame for processing
                        df = pd.DataFrame(raw_data, columns=headers)
                        
                        # Detect categorical columns
                        column_configs = []
                        has_categorical = False
                        
                        for i, col in enumerate(headers):
                            if DataProcessingService._is_categorical_column(df[col]):
                                column_configs.append({
                                    'index': i,
                                    'name': col,
                                    'data_type': DataType.categorical,
                                    'is_categorical': True,
                                    'usage': 'feature'
                                })
                                has_categorical = True
                        
                        if has_categorical:
                            print(f"[ClusteringService] Detected {len(column_configs)} categorical columns, applying automatic encoding")
                            
                            # Create processing config
                            processing_config = DataProcessingConfig(
                                categorical_encoding=CategoricalEncoding.label,
                                feature_columns=list(range(len(headers))),
                                columns=column_configs
                            )
                            
                            # Process the data
                            processed_result = DataProcessingService.process_data(
                                raw_data=ClusteringService._sanitize_array_for_json(raw_data),
                                headers=headers,
                                processing_config=processing_config
                            )
                            
                            if processed_result and processed_result.get("data"):
                                # Use processed data
                                X = np.array(processed_result["data"]).astype(float)
                                print(f"[ClusteringService] Automatic categorical encoding successful. New shape: {X.shape}")
                            else:
                                raise ValueError("Automatic categorical encoding failed")
                        else:
                            # No categorical columns detected, use basic numeric conversion
                            print("[ClusteringService] No categorical columns detected, using basic numeric conversion")
                            X = raw_data.astype(float)
                    
                    except Exception as auto_encoding_error:
                        print(f"[ClusteringService] Automatic categorical encoding failed: {auto_encoding_error}")
                        print("[ClusteringService] Falling back to legacy processing")
                        
                        # Legacy data processing for backward compatibility
                        cleaned_data = []
                        for row in raw_data:
                            cleaned_row = []
                            for value in row:
                                try:
                                    # Handle various data types
                                    if isinstance(value, (int, float)):
                                        cleaned_row.append(float(value))
                                    elif isinstance(value, str):
                                        # Try to convert string to float
                                        if value.lower() in ['nan', 'null', '', 'none']:
                                            cleaned_row.append(0.0)  # Replace missing values with 0
                                        else:
                                            # Try to parse as number
                                            try:
                                                cleaned_row.append(float(value))
                                            except ValueError:
                                                # If string can't be converted, use hash as numeric value
                                                cleaned_row.append(float(hash(value) % 10000))
                                    else:
                                        # For other types, try conversion or use 0
                                        try:
                                            cleaned_row.append(float(value))
                                        except (ValueError, TypeError):
                                            cleaned_row.append(0.0)
                                except Exception as e:
                                    print(f"[ClusteringService] Error processing value {value}: {e}")
                                    cleaned_row.append(0.0)  # Fallback to 0
                            
                            if cleaned_row:  # Only add non-empty rows
                                cleaned_data.append(cleaned_row)
                        
                        if not cleaned_data:
                            raise ValueError("No valid numeric data found in uploaded file")
                        
                        X = np.array(cleaned_data, dtype=float)
                
                print(f"[ClusteringService] Final data shape: {X.shape}")
                
                # Validate data dimensions
                if X.shape[0] < 2:
                    raise ValueError("Dataset must have at least 2 samples")
                if X.shape[1] < 1:
                    raise ValueError("Dataset must have at least 1 feature")
                
                # Check for invalid values
                if np.isnan(X).any():
                    print("[ClusteringService] Warning: Data contains NaN values, replacing with 0")
                    X = np.nan_to_num(X, nan=0.0)
                
                if np.isinf(X).any():
                    print("[ClusteringService] Warning: Data contains infinite values, replacing with finite values")
                    X = np.nan_to_num(X, posinf=np.finfo(np.float64).max, neginf=np.finfo(np.float64).min)
                    
            except Exception as e:
                print(f"[ClusteringService] Error processing uploaded data: {e}")
                raise ValueError(f"Failed to process uploaded data: {str(e)}")
        else:
            # Use ToyDatasetService for all sample dataset generation
            try:
                print(f"[ClusteringService] Generating sample dataset: {params.sample}")
                print(f"[ClusteringService] Parameters: n_samples={params.n_samples}, n_clusters={params.n_clusters}, n_features={params.n_features}")
                
                X, X_true_labels = ToyDatasetService.generate_dataset(
                    dataset_name=params.sample,
                    n_samples=params.n_samples,
                    n_clusters=params.n_clusters,
                    n_features=params.n_features,
                    random_state=params.random_state
                )
                
                print(f"[ClusteringService] Generated dataset shape: {X.shape}")
                print(f"[ClusteringService] Unique labels: {len(np.unique(X_true_labels))}")
                
                # Get dataset recommendations for clustering parameters
                recommendations = ToyDatasetService.get_recommended_params(params.sample)
                print(f"[ClusteringService] Dataset recommendations: {recommendations}")
                
            except Exception as e:
                print(f"[ClusteringService] Error generating sample dataset '{params.sample}': {e}")
                print(f"[ClusteringService] Falling back to default blobs dataset")
                # Fallback to basic blobs if dataset generation fails
                X, X_true_labels = make_blobs(n_samples=params.n_samples, centers=params.n_clusters, random_state=params.random_state)
        end_time_data_load = time.time()
        print(f"[ClusteringService] Data loading/generation took {end_time_data_load - start_time_data_load:.4f} seconds")

        setLogLevel(LogLevel.INFO)

        k = params.n_clusters
        # Use selected treeType and partitioningMethod
        # Coerce power to int: SHiP.fit_predict's hierarchy/power arg is bound to a C++
        # int and raises a RuntimeError on a float (e.g. 2.0). ClusterParams.power is
        # already int, so this is a defensive guard for any caller that passes a float,
        # and keeps this path consistent with the k-selector (which also uses int(power)).
        power = int(params.power)

        # Handle manual K selection
        if params.partitioningMethod == 'K':
            # For manual K selection, we'll use None as partitioningMethod to bypass automatic selection
            partitioningMethod = None
            print(f"[ClusteringService] Using manual K selection with k={k}")
        else:
            partitioningMethod = getattr(PMethod, params.partitioningMethod, PMethod.Elbow)
            print(f"[ClusteringService] Using automatic partitioning method: {params.partitioningMethod}")
        
        # Use dynamically optimized configuration for dataset size
        config = SHiPCacheService._get_optimized_config_for_dataset_size(len(X))
        print(f"[ClusteringService] Optimized config: {config}")
        print(f"[ClusteringService] Final parameters - treeType: {params.treeType}, partitioningMethod: {params.partitioningMethod}, power: {power}, k: {k}")
        
        # Use cached SHiP instance for efficiency with large datasets
        start_time_ship_get = time.time()
        try:
            ship = SHiPCacheService.get_ship(data=X, tree_type=params.treeType, config=config)
        except SHiPTreeGenerationError:
            # Re-raise SHiP-specific errors to be handled by the API layer
            raise
        end_time_ship_get = time.time()
        print(f"[ClusteringService] SHiPCacheService.get_ship took {end_time_ship_get - start_time_ship_get:.4f} seconds")
        if ship is None:
            raise RuntimeError("Failed to create or retrieve SHiP instance")
        
        start_time_fit_predict = time.time()
        if partitioningMethod is None:
            # Manual K selection - use PMethod.K to force exactly k clusters
            print(f"[ClusteringService] Executing manual K clustering with k={k}")
            runtime_config = {"k": k}
            labels = ship.fit_predict(power, PMethod.K, config=runtime_config)
        else:
            # Automatic partition method selection
            print(f"[ClusteringService] Executing automatic partitioning with method: {partitioningMethod}")
            labels = ship.fit_predict(power, partitioningMethod)
        end_time_fit_predict = time.time()
        print(f"[ClusteringService] ship.fit_predict took {end_time_fit_predict - start_time_fit_predict:.4f} seconds")
        print(f"[ClusteringService] Resulting number of clusters: {len(np.unique(labels))}")
        
        # Calculate evaluation metrics
        start_time_metrics = time.time()
        metrics = {}
        if X_true_labels is not None:
            try:
                metrics["ari"] = adjusted_rand_score(X_true_labels, labels)
            except ValueError as e:
                print(f"Could not calculate ARI: {e}") # E.g. if all labels are the same
          # Silhouette Score can be calculated if there's more than 1 cluster and less than n_samples-1 clusters
        # and X has more than 1 sample.
        if len(np.unique(labels)) > 1 and len(np.unique(labels)) < len(X) - 1 and len(X) > 1:
            try:
                sil_score = silhouette_score(X, labels)
                if math.isnan(sil_score) or math.isinf(sil_score):
                    print(f"Silhouette Score returned invalid value: {sil_score}, skipping")
                else:
                    metrics["silhouette_score"] = sil_score
            except ValueError as e:
                print(f"Could not calculate Silhouette Score: {e}")
        else:
            print("Skipping Silhouette Score calculation due to insufficient number of clusters or samples.")

        # Davies-Bouldin Index - lower is better
        if len(np.unique(labels)) > 1 and len(X) > 1:
            try:
                db_score = davies_bouldin_score(X, labels)
                # Davies-Bouldin can return NaN for certain cluster configurations
                if math.isnan(db_score) or math.isinf(db_score):
                    print(f"Davies-Bouldin returned invalid value: {db_score}, skipping")
                else:
                    metrics["db_index"] = db_score
            except ValueError as e:
                print(f"Could not calculate Davies-Bouldin Index: {e}")
        else:
            print("Skipping Davies-Bouldin Index calculation due to insufficient number of clusters or samples.")

        # Calinski-Harabasz Index - higher is better
        if len(np.unique(labels)) > 1 and len(X) > 1:
            try:
                ch_score = calinski_harabasz_score(X, labels)
                if math.isnan(ch_score) or math.isinf(ch_score):
                    print(f"Calinski-Harabasz returned invalid value: {ch_score}, skipping")
                else:
                    metrics["calinski_harabasz"] = ch_score
            except ValueError as e:
                print(f"Could not calculate Calinski-Harabasz Index: {e}")
        else:
            print("Skipping Calinski-Harabasz Index calculation due to insufficient number of clusters or samples.")

        # --- DISCO metric ---
        try:
            if disco_import_error:
                print(f"[ClusteringService] Skipping DISCO calculation due to import error: {disco_import_error}")
                disco_val = None
            else:
                print(f"[ClusteringService] Calculating DISCO score: samples={len(X)}, unique_labels={np.unique(labels).size}")
                start_time_disco = time.time()
                
                # Calculate DISCO metric fresh each run (no caching)
                min_points = 5  # Default min_points for DISCO
                print(f"[ClusteringService] Calculating DISCO metric with min_points={min_points}")
                disco_val = disco_score(X, labels, min_points)
                
                end_time_disco = time.time()
                disco_time = end_time_disco - start_time_disco
                print(f"[ClusteringService] DISCO calculation took {disco_time:.4f} seconds")
                print(f"[ClusteringService] DISCO raw value: {disco_val}")
        except Exception as e:
            print(f"[ClusteringService] Could not calculate DISCO Score: {e}")
            import traceback; traceback.print_exc()
            disco_val = None

        if disco_val is not None and isinstance(disco_val, (float, np.floating)) and not (np.isnan(disco_val) or np.isinf(disco_val)):
            metrics["disco_score"] = float(disco_val)
        else:
            metrics["disco_score"] = None
        # --- End DISCO metric ---
        end_time_metrics = time.time()
        print(f"[ClusteringService] Evaluation metrics calculation took {end_time_metrics - start_time_metrics:.4f} seconds")

        # Get tree and ensure it's a Python dictionary, not a JSON string
        start_time_tree_processing = time.time()
        raw_tree = None  # Initialize raw_tree variable (will be set after colors are applied)
        try:
            json_tree_str = ship.get_tree(power).to_json(fast_index=True)
            
            # Handle JSON parsing with recursion depth protection
            import sys
            original_recursion_limit = sys.getrecursionlimit()
            json_tree = None
            try:
                # Temporarily increase recursion limit for deep trees.
                sys.setrecursionlimit(max(20000, original_recursion_limit))
                json_tree = json.loads(json_tree_str)
                print(f"[ClusteringService] Successfully parsed tree with {len(str(json_tree_str))} characters")

                # Apply tree depth limiting
                real_tree_depth = getattr(params, 'realTreeDepth', 100)
                
                # Apply depth limiting for the immediate response
                json_tree = ClusteringService._limit_tree_depth(json_tree, real_tree_depth)

            except (RecursionError, MemoryError) as e:
                print(f"[ClusteringService] Error during initial tree parsing or processing: {e}")
                print("[ClusteringService] Falling back to creating a representative tree structure.")
                # If even parsing fails, fall back to the old method.
                json_tree = ClusteringService._create_representative_tree(labels, k)
            finally:
                # Restore original recursion limit
                sys.setrecursionlimit(original_recursion_limit)
        
        except Exception as e:
            print(f"[ClusteringService] Error processing tree: {e}")
            # Fallback to representative tree structure if anything goes wrong
            json_tree = ClusteringService._create_representative_tree(labels, k)
        
        # Normalize all node IDs to strings to prevent mixed type comparison errors
        ClusteringService._normalize_tree_node_ids(json_tree)
        
        # Validate tree structure before extracting mappings
        if not ClusteringService._validate_tree_structure(json_tree):
            print("[ClusteringService] Tree validation failed, using fallback tree")
            json_tree = ClusteringService._create_representative_tree(labels, k)
        
        # Extract node-to-data mappings for interactivity
        node_mappings = ClusteringService.extract_node_to_data_mapping(json_tree)
        end_time_tree_processing = time.time()
        print(f"[ClusteringService] Tree processing (get, map) took {end_time_tree_processing - start_time_tree_processing:.4f} seconds")

        # Add color encoding - compute predicted cluster colors WITHOUT ground truth
        # so that scatter_colors match k-selection page colors for the same cluster labels.
        # Ground truth colors are provided separately in the response for the "color by ground truth" toggle.
        start_time_color_encoding = time.time()
        # Get outlier style from parameters
        outlier_style = getattr(params, 'outlier_style', 'prominent')
        color_helper = ClusterColorHelper(labels=labels, tree=json_tree, ground_truth_labels=X_true_labels, outlier_style=outlier_style)
        # Use a separate helper without ground truth for scatter_colors to avoid confusion matrix remapping
        plain_color_helper = ClusterColorHelper(labels=labels, tree=None, outlier_style=outlier_style)
        scatter_colors = plain_color_helper.get_color_list_for_labels(labels)
        print(f"Labels: {labels[:10]}{'...' if len(labels) > 10 else ''}")  # Limit log output for large datasets
        
        # Add ground truth coloring to tree if available
        if X_true_labels is not None:
            color_helper.add_ground_truth_coloring_to_tree(json_tree)
        
        # Store the raw tree (with colors applied) for on-demand processing
        # This is the tree before visualization processing but after color application
        raw_tree = json_tree.copy() if isinstance(json_tree, dict) else json_tree
        print(f"[ClusteringService] Stored raw tree with colors for on-demand processing")
        
        # Ensure raw_tree is set (fallback for edge cases)
        if raw_tree is None:
            raw_tree = json_tree.copy() if isinstance(json_tree, dict) else json_tree
            print(f"[ClusteringService] Set raw_tree as fallback (no colors applied)")
        
        # After color helper modifies the tree, keep it as object (don't pre-serialize)
        # The JSON encoder will handle serialization with proper NaN/Inf checks
        colored_tree_obj = json_tree
        end_time_color_encoding = time.time()
        print(f"[ClusteringService] Color encoding took {end_time_color_encoding - start_time_color_encoding:.4f} seconds")
        
        # Compute dimensionality reduction transformations
        start_time_dr = time.time()
        pca_components = None
        umap_components = None
        tsne_components = None
        
        # Skip dimensionality reduction for very small datasets or if already 2D
        if X.shape[0] < 10:
            print(f"Skipping dimensionality reduction: dataset too small ({X.shape[0]} samples)")
        elif X.shape[1] <= 2:
            print(f"Skipping dimensionality reduction: data already low-dimensional ({X.shape[1]}D)")
            # For 2D data, just use the original data as "PCA" components
            pca_components = ClusteringService._sanitize_array_for_json(X)
        elif X.shape[1] >= 2:
            # PCA - fast and always available
            try:
                print(f"[ClusteringService] Computing PCA for {X.shape[0]} samples, {X.shape[1]} features")
                pca = PCA(n_components=min(2, X.shape[1]))
                pca_components = ClusteringService._sanitize_array_for_json(pca.fit_transform(X))
                print(f"[ClusteringService] PCA completed")
            except Exception as e:
                print(f"PCA computation failed: {e}")
            
            # UMAP - using optimized service with intelligent caching and fast mode
            # Check for skip_umap from settings or params
            skip_umap = params.skip_umap
            if app_settings and hasattr(app_settings, 'performance_settings'):
                skip_umap = skip_umap or app_settings.performance_settings.skip_umap
            
            if not skip_umap and X.shape[1] > 2:  # Only compute for higher-dimensional data and if not skipped
                print(f"[ClusteringService] Computing UMAP for {X.shape[0]} samples, {X.shape[1]} features")
                
                # Prepare UMAP settings override
                umap_settings_override = None
                fast_mode = True  # Default
                if app_settings and hasattr(app_settings, 'umap_settings'):
                    umap_settings = app_settings.umap_settings
                    umap_settings_override = {
                        'n_neighbors': umap_settings.n_neighbors,
                        'min_dist': umap_settings.min_dist,
                        'n_epochs': umap_settings.n_epochs,
                        'metric': umap_settings.metric,
                        'spread': umap_settings.spread,
                        'negative_sample_rate': umap_settings.negative_sample_rate
                    }
                    fast_mode = umap_settings.fast_mode
                    print(f"[ClusteringService] Using UMAP settings override: {umap_settings_override}")
                
                umap_components = UMAPOptimizationService.compute_umap_optimized(
                    X, 
                    fast_mode=fast_mode, 
                    settings_override=umap_settings_override
                )
                
                if umap_components is None:
                    print(f"[ClusteringService] UMAP computation failed, skipping UMAP embedding")
                else:
                    print(f"[ClusteringService] UMAP completed successfully")
            elif skip_umap:
                print(f"[ClusteringService] Skipping UMAP computation (skip_umap=True) for performance")
            else:
                print(f"Skipping UMAP: data already low-dimensional ({X.shape[1]}D)")
            
            # t-SNE - using optimized service with intelligent caching and fast mode
            # Check for skip_tsne from settings or params
            skip_tsne = params.skip_tsne
            if app_settings and hasattr(app_settings, 'performance_settings'):
                skip_tsne = skip_tsne or app_settings.performance_settings.skip_tsne
            
            if not skip_tsne and X.shape[1] > 2:  # Only compute for higher-dimensional data and if not skipped
                print(f"[ClusteringService] Computing t-SNE for {X.shape[0]} samples, {X.shape[1]} features")
                tsne_components = TSNEOptimizationService.compute_tsne_optimized(X, fast_mode=True)
                
                if tsne_components is None:
                    print(f"[ClusteringService] t-SNE computation failed, skipping t-SNE embedding")
                else:
                    print(f"[ClusteringService] t-SNE completed successfully")
            elif skip_tsne:
                print(f"[ClusteringService] Skipping t-SNE computation (skip_tsne=True) for performance")
            else:
                print(f"Skipping t-SNE: data already low-dimensional ({X.shape[1]}D)")
        end_time_dr = time.time()
        print(f"[ClusteringService] Dimensionality reduction took {end_time_dr - start_time_dr:.4f} seconds")
        
        # Prepare the base clustering result
        # For datasets with many features, skip the full feature data to reduce JSON size
        # and only provide dimensionality reduction results for visualization
        if X.shape[1] > 10:
            print(f"[ClusteringService] Replacing high-dimensional data with PCA for {X.shape[1]}-feature dataset to reduce JSON size")
            points_data = pca_components if pca_components is not None else []
            skip_reason = f"Full feature data replaced with PCA for {X.shape[1]}-feature dataset"
        else:
            points_data = ClusteringService._sanitize_array_for_json(X)
            skip_reason = None
            
        # Create feature headers for visualization
        feature_headers = []
        if params.featureHeaders:
            feature_headers = params.featureHeaders
        else:
            # Check for known dataset feature names before using generic defaults
            known_feature_names = {
                'palmer_penguins': [
                    'bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g',
                    'sex', 'island_Biscoe', 'island_Dream', 'island_Torgersen'
                ],
                'wheats': [
                    'Area', 'Perimeter', 'Compactness', 'Kernel Length',
                    'Kernel Width', 'Asymmetry Coeff.', 'Groove Length'
                ],
                'olive_oil': [
                    'Palmitic', 'Palmitoleic', 'Stearic', 'Oleic',
                    'Linoleic', 'Linolenic', 'Arachidic', 'Eicosenoic'
                ],
                'zoo': [
                    'Hair', 'Feathers', 'Eggs', 'Milk', 'Airborne', 'Aquatic',
                    'Predator', 'Toothed', 'Backbone', 'Breathes', 'Venomous',
                    'Fins', 'Legs', 'Tail', 'Domestic', 'Catsize'
                ],
            }
            dataset_name = getattr(params, 'dataset', '') or getattr(params, 'sample', '') or ''
            if dataset_name in known_feature_names:
                feature_headers = known_feature_names[dataset_name][:X.shape[1]]
            else:
                # Create default headers
                feature_headers = [f"Feature_{i}" for i in range(X.shape[1])]
        
        # Ensure we have the correct number of headers
        if len(feature_headers) != X.shape[1]:
            print(f"[ClusteringService] Warning: Feature headers length ({len(feature_headers)}) doesn't match data columns ({X.shape[1]})")
            feature_headers = [f"Feature_{i}" for i in range(X.shape[1])]
        
        # Store the raw tree for future on-demand processing (also as object, not string)
        raw_tree_obj = raw_tree if raw_tree else colored_tree_obj

        base_result = {
            "points": points_data,
            "labels": labels,
            "centers": [],
            "tree": colored_tree_obj,  # Return tree as object, not pre-serialized string
            "raw_tree": raw_tree_obj,  # Store raw tree as object
            "scatter_colors": scatter_colors,
            "color_map": getattr(plain_color_helper, "label_to_color", {}),
            "evaluation_metrics": metrics,
            "dimensionality_reduction": {
                "pca": pca_components,
                "umap": umap_components,
                "tsne": tsne_components
            },
            "original_data_size": len(X),
            "original_feature_count": X.shape[1],
            # Don't include original_points in response to reduce size
            # Frontend can request it separately if needed for feature importance
            "original_points": None,
            "feature_names": feature_headers,  # Store feature names for export
            "node_mappings": node_mappings,
            "high_dimensional_dataset": X.shape[1] >= 100,
            "feature_headers": feature_headers
        }
        
        if skip_reason:
            base_result["points_skip_reason"] = skip_reason
        
        # Add ground truth information if available
        if X_true_labels is not None:
            base_result["ground_truth"] = {
                "labels": ClusteringService._sanitize_array_for_json(X_true_labels),
                "colors": color_helper.get_ground_truth_color_list(X_true_labels),
                "color_map": getattr(color_helper, "ground_truth_label_to_color", {}),
                "unique_labels": sorted(list(set(X_true_labels.astype(str))))
            }
            
            # Add confusion matrix quality metrics if available
            confusion_quality = color_helper.get_confusion_matrix_quality()
            if confusion_quality:
                base_result["confusion_matrix_mapping"] = confusion_quality
        
        print(f"[ClusteringService] Total cluster_data execution took {time.time() - start_time_total:.4f} seconds")
        return base_result

    @classmethod
    def _get_node_id(cls, node: Dict[str, Any]) -> str:
        """Get a unique identifier for a node."""
        if 'id' in node:
            return str(node['id'])
        elif 'label' in node:
            return f"label_{node['label']}"
        else:
            # Generate ID based on node properties
            height = node.get('height', node.get('distance', 0))
            children_count = len(node.get('children', []))
            return f"node_{hash(str(height))}_{children_count}"
    
    @classmethod
    def extract_node_to_data_mapping(cls, tree_data: Dict[str, Any]) -> Dict[str, List[int]]:
        """
        Extract mapping from tree nodes to data point indices for interactivity.
        This is an iterative implementation to avoid recursion depth errors on large datasets.
        
        Returns:
            Dictionary mapping node IDs to lists of data point indices
        """
        if not tree_data or 'root' not in tree_data:
            return {}
        
        # Additional validation before processing
        try:
            if not isinstance(tree_data['root'], dict):
                print("[ClusteringService] Invalid root node in tree data")
                return {}
        except Exception as e:
            print(f"[ClusteringService] Error accessing tree root: {e}")
            return {}
        
        node_mappings = {}
        # Stack for post-order traversal. Each item is (node, visited_children_flag)
        stack = [(tree_data['root'], False)]
        processed_nodes = 0
        max_nodes = 100000  # Safety limit
        
        try:
            while stack and processed_nodes < max_nodes:
                node, visited = stack[-1]
                processed_nodes += 1
                
                if not isinstance(node, dict):
                    print(f"[ClusteringService] Invalid node type encountered: {type(node)}")
                    stack.pop()
                    continue
                
                if visited:
                    # We have visited all children, now process the node
                    stack.pop()
                    node_id = cls._get_node_id(node)
                    
                    # After summarization, a node is either an internal node with children
                    # or a leaf node with a `pointIndices` or `data_indices` list.
                    if not node.get('children'):
                        # Leaf node: its data points are defined in `pointIndices` (preferred) or `data_indices`.
                        point_indices = node.get('pointIndices', node.get('data_indices', []))
                        
                        # Handle SHiP tree format: if no explicit indices, use low/high range
                        if not point_indices and 'low' in node and 'high' in node:
                            try:
                                low = int(node['low'])
                                high = int(node['high'])
                                if low >= 0 and high >= 0:
                                    # For SHiP trees, low and high define the range of data points
                                    # For leaf nodes, low == high (single point)
                                    point_indices = list(range(low, high + 1))
                            except (ValueError, TypeError):
                                point_indices = []
                        
                        # Validate point indices
                        if isinstance(point_indices, list):
                            valid_indices = []
                            for idx in point_indices:
                                if isinstance(idx, int) and idx >= 0:
                                    valid_indices.append(idx)
                                elif isinstance(idx, str):
                                    try:
                                        int_idx = int(idx)
                                        if int_idx >= 0:
                                            valid_indices.append(int_idx)
                                    except ValueError:
                                        pass  # Skip invalid string indices
                            node_mappings[node_id] = valid_indices
                        else:
                            node_mappings[node_id] = []
                    else:
                        # Internal node: its points are the union of its children's points.
                        descendant_indices = []
                        for child in node.get('children', []):
                            if isinstance(child, dict):
                                child_id = cls._get_node_id(child)
                                if child_id in node_mappings:
                                    descendant_indices.extend(node_mappings[child_id])
                        
                        node_mappings[node_id] = sorted(list(set(descendant_indices)))
                else:
                    # Mark current node as "visiting children now"
                    stack[-1] = (node, True)
                    # Push children to stack to be processed first
                    if 'children' in node and isinstance(node['children'], list):
                        # Iterate in reverse to maintain original order in processing
                        for child in reversed(node.get('children', [])):
                            if isinstance(child, dict):
                                stack.append((child, False))
            
            if processed_nodes >= max_nodes:
                print(f"[ClusteringService] Node mapping extraction stopped at limit: {max_nodes}")
                
        except Exception as e:
            print(f"[ClusteringService] Error during node mapping extraction: {e}")
            # Return partial results
            pass
                        
        return node_mappings

    @classmethod
    def _create_representative_tree(cls, labels: np.ndarray, k: int) -> Dict[str, Any]:
        """
        Create a representative tree structure based on clustering results.
        This creates a simple binary-like tree that can still be visualized.
        """
        unique_labels = np.unique(labels)
        n_clusters = len(unique_labels)
        
        # Create leaf nodes for each cluster
        leaves = []
        for i, label in enumerate(unique_labels):
            cluster_points = np.where(labels == label)[0]
            # Don't include pointIndices in tree nodes to reduce size
            # They can be reconstructed from labels if needed
            leaves.append({
                'id': f'cluster_{label}',
                'label': int(label),
                'height': 0.0,
                'color': f'hsl({(i * 360 / n_clusters) % 360}, 70%, 50%)',
                'children': [],
                'size': int(len(cluster_points))  # Just store count instead of full indices
            })
        
        # Build a simple hierarchical structure
        def build_hierarchy(nodes: List[Dict], level: int = 1) -> Dict[str, Any]:
            if len(nodes) == 1:
                return nodes[0]
            
            # Group nodes in pairs
            new_nodes = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    # Merge two nodes
                    left = nodes[i]
                    right = nodes[i + 1]
                    merged = {
                        'id': f'internal_{level}_{i//2}',
                        'height': float(level),
                        'color': '#888888',
                        'children': [left, right]
                    }
                    new_nodes.append(merged)
                else:
                    # Odd node out
                    new_nodes.append(nodes[i])
            
            if len(new_nodes) == 1:
                return new_nodes[0]
            else:
                return build_hierarchy(new_nodes, level + 1)
        
        if leaves:
            root = build_hierarchy(leaves)
            return {'root': root}
        else:
            return {
                'root': {
                    'id': 'empty_root',
                    'height': 1.0,
                    'children': [],
                    'color': '#888888'
                }
            }

    @classmethod
    def _iterative_json_serialize(cls, obj: Any) -> str:
        """
        True iterative JSON serialization using explicit stack to avoid recursion depth issues.
        Uses a state machine approach to handle nested structures without recursion.
        """
        import io
        
        # State constants
        STATE_VALUE = 'value'
        STATE_DICT_START = 'dict_start'
        STATE_DICT_KEY = 'dict_key'
        STATE_DICT_COLON = 'dict_colon'
        STATE_DICT_VALUE = 'dict_value'
        STATE_DICT_COMMA = 'dict_comma'
        STATE_DICT_END = 'dict_end'
        STATE_LIST_START = 'list_start'
        STATE_LIST_VALUE = 'list_value'
        STATE_LIST_COMMA = 'list_comma'
        STATE_LIST_END = 'list_end'
        
        output = io.StringIO()
        
        # Stack entries: (state, data, index, keys)
        # - state: current processing state
        # - data: the object being processed
        # - index: current position in list/dict iteration
        # - keys: list of keys for dict iteration
        stack = [(STATE_VALUE, obj, 0, None)]
        
        while stack:
            state, data, idx, keys = stack.pop()
            
            if state == STATE_VALUE:
                # Process a new value
                if data is None:
                    output.write('null')
                elif isinstance(data, bool):
                    output.write('true' if data else 'false')
                elif isinstance(data, (int, float, np.integer, np.floating)):
                    # Handle numpy numeric types as well as Python built-ins
                    if isinstance(data, (float, np.floating)):
                        # Convert numpy types to Python float for consistent handling
                        float_val = float(data)
                        # Check for NaN using math.isnan (more reliable)
                        try:
                            if math.isnan(float_val):
                                output.write('null')
                            # Check for infinity
                            elif math.isinf(float_val):
                                output.write('null')
                            else:
                                # Use str() instead of repr() to avoid 'nan'/'inf' string literals
                                output.write(str(float_val))
                        except (ValueError, OverflowError):
                            # Fallback for any edge cases
                            output.write('null')
                    else:
                        # Integer types (Python int or numpy integer)
                        output.write(str(int(data)))
                elif isinstance(data, str):
                    # Escape string properly
                    output.write('"')
                    for char in data:
                        if char == '"':
                            output.write('\\"')
                        elif char == '\\':
                            output.write('\\\\')
                        elif char == '\n':
                            output.write('\\n')
                        elif char == '\r':
                            output.write('\\r')
                        elif char == '\t':
                            output.write('\\t')
                        elif ord(char) < 32:
                            output.write(f'\\u{ord(char):04x}')
                        else:
                            output.write(char)
                    output.write('"')
                elif isinstance(data, np.ndarray):
                    # Convert numpy array to list and process
                    try:
                        data_list = data.tolist()
                        if not data_list:
                            output.write('[]')
                        else:
                            output.write('[')
                            stack.append((STATE_LIST_VALUE, data_list, 0, None))
                    except:
                        output.write('null')
                elif isinstance(data, dict):
                    if not data:
                        output.write('{}')
                    else:
                        output.write('{')
                        dict_keys = list(data.keys())
                        # Push dict processing state
                        stack.append((STATE_DICT_KEY, data, 0, dict_keys))
                elif isinstance(data, (list, tuple)):
                    if not data:
                        output.write('[]')
                    else:
                        output.write('[')
                        # Push list processing state
                        stack.append((STATE_LIST_VALUE, data, 0, None))
                else:
                    # Try to convert to string, fallback to null
                    try:
                        output.write('"')
                        output.write(str(data).replace('"', '\\"').replace('\\', '\\\\'))
                        output.write('"')
                    except:
                        output.write('null')
            
            elif state == STATE_DICT_KEY:
                if idx < len(keys):
                    key = keys[idx]
                    # Write key
                    output.write('"')
                    key_str = str(key)
                    for char in key_str:
                        if char == '"':
                            output.write('\\"')
                        elif char == '\\':
                            output.write('\\\\')
                        elif char == '\n':
                            output.write('\\n')
                        elif char == '\r':
                            output.write('\\r')
                        elif char == '\t':
                            output.write('\\t')
                        elif ord(char) < 32:
                            output.write(f'\\u{ord(char):04x}')
                        else:
                            output.write(char)
                    output.write('":')
                    # Push: after value, continue with next key or end
                    stack.append((STATE_DICT_COMMA, data, idx, keys))
                    # Push: process the value
                    stack.append((STATE_VALUE, data[key], 0, None))
                else:
                    output.write('}')
            
            elif state == STATE_DICT_COMMA:
                if idx + 1 < len(keys):
                    output.write(',')
                    # Continue with next key
                    stack.append((STATE_DICT_KEY, data, idx + 1, keys))
                else:
                    output.write('}')
            
            elif state == STATE_LIST_VALUE:
                if idx < len(data):
                    # Push: after value, continue with next item or end
                    stack.append((STATE_LIST_COMMA, data, idx, None))
                    # Push: process the value
                    stack.append((STATE_VALUE, data[idx], 0, None))
                else:
                    output.write(']')
            
            elif state == STATE_LIST_COMMA:
                if idx + 1 < len(data):
                    output.write(',')
                    # Continue with next item
                    stack.append((STATE_LIST_VALUE, data, idx + 1, None))
                else:
                    output.write(']')
        
        return output.getvalue()

    @classmethod
    def _iterative_json_parse(cls, json_str: str) -> Any:
        """
        Iterative JSON parser that handles deeply nested structures without recursion.
        Uses a state machine approach with explicit stack management.
        """
        if not json_str or not json_str.strip():
            return None
        
        json_str = json_str.strip()
        pos = 0
        length = len(json_str)
        
        def skip_whitespace():
            nonlocal pos
            while pos < length and json_str[pos] in ' \t\n\r':
                pos += 1
        
        def parse_string():
            nonlocal pos
            if json_str[pos] != '"':
                raise ValueError(f"Expected string at position {pos}")
            pos += 1
            result = []
            while pos < length:
                char = json_str[pos]
                if char == '"':
                    pos += 1
                    return ''.join(result)
                elif char == '\\':
                    pos += 1
                    if pos >= length:
                        raise ValueError("Unexpected end of string")
                    escape_char = json_str[pos]
                    if escape_char == 'n':
                        result.append('\n')
                    elif escape_char == 'r':
                        result.append('\r')
                    elif escape_char == 't':
                        result.append('\t')
                    elif escape_char == '"':
                        result.append('"')
                    elif escape_char == '\\':
                        result.append('\\')
                    elif escape_char == '/':
                        result.append('/')
                    elif escape_char == 'b':
                        result.append('\b')
                    elif escape_char == 'f':
                        result.append('\f')
                    elif escape_char == 'u':
                        # Unicode escape
                        if pos + 4 >= length:
                            raise ValueError("Invalid unicode escape")
                        hex_str = json_str[pos + 1:pos + 5]
                        try:
                            result.append(chr(int(hex_str, 16)))
                        except ValueError:
                            raise ValueError(f"Invalid unicode escape: \\u{hex_str}")
                        pos += 4
                    else:
                        result.append(escape_char)
                    pos += 1
                else:
                    result.append(char)
                    pos += 1
            raise ValueError("Unterminated string")
        
        def parse_number():
            nonlocal pos
            start = pos
            # Handle negative
            if pos < length and json_str[pos] == '-':
                pos += 1
            # Integer part
            while pos < length and json_str[pos].isdigit():
                pos += 1
            # Decimal part
            if pos < length and json_str[pos] == '.':
                pos += 1
                while pos < length and json_str[pos].isdigit():
                    pos += 1
            # Exponent
            if pos < length and json_str[pos] in 'eE':
                pos += 1
                if pos < length and json_str[pos] in '+-':
                    pos += 1
                while pos < length and json_str[pos].isdigit():
                    pos += 1
            num_str = json_str[start:pos]
            if '.' in num_str or 'e' in num_str or 'E' in num_str:
                return float(num_str)
            return int(num_str)
        
        def parse_keyword():
            nonlocal pos
            if json_str[pos:pos+4] == 'true':
                pos += 4
                return True
            elif json_str[pos:pos+5] == 'false':
                pos += 5
                return False
            elif json_str[pos:pos+4] == 'null':
                pos += 4
                return None
            raise ValueError(f"Unknown keyword at position {pos}")
        
        # Stack-based parsing
        # Stack entries: (container, key_or_none)
        # - container: the dict or list being built
        # - key_or_none: for dicts, the current key; for lists, None
        stack = []
        result = None
        current_container = None
        current_key = None
        expecting_value = True
        
        skip_whitespace()
        
        while pos < length:
            skip_whitespace()
            if pos >= length:
                break
            
            char = json_str[pos]
            
            if expecting_value:
                if char == '{':
                    pos += 1
                    new_dict = {}
                    if current_container is not None:
                        stack.append((current_container, current_key))
                        if isinstance(current_container, dict):
                            current_container[current_key] = new_dict
                        else:
                            current_container.append(new_dict)
                    else:
                        result = new_dict
                    current_container = new_dict
                    current_key = None
                    expecting_value = False
                    
                elif char == '[':
                    pos += 1
                    new_list = []
                    if current_container is not None:
                        stack.append((current_container, current_key))
                        if isinstance(current_container, dict):
                            current_container[current_key] = new_list
                        else:
                            current_container.append(new_list)
                    else:
                        result = new_list
                    current_container = new_list
                    current_key = None
                    expecting_value = True
                    
                elif char == '"':
                    value = parse_string()
                    if current_container is None:
                        result = value
                        break
                    elif isinstance(current_container, dict):
                        current_container[current_key] = value
                    else:
                        current_container.append(value)
                    expecting_value = False
                    
                elif char == '-' or char.isdigit():
                    value = parse_number()
                    if current_container is None:
                        result = value
                        break
                    elif isinstance(current_container, dict):
                        current_container[current_key] = value
                    else:
                        current_container.append(value)
                    expecting_value = False
                    
                elif char in 'tfn':  # true, false, null
                    value = parse_keyword()
                    if current_container is None:
                        result = value
                        break
                    elif isinstance(current_container, dict):
                        current_container[current_key] = value
                    else:
                        current_container.append(value)
                    expecting_value = False
                    
                elif char == ']':
                    # Empty list or end of list
                    pos += 1
                    if stack:
                        current_container, current_key = stack.pop()
                    else:
                        break
                    expecting_value = False
                    
                else:
                    raise ValueError(f"Unexpected character '{char}' at position {pos}")
            
            else:
                # Not expecting value - looking for structure tokens
                if isinstance(current_container, dict):
                    if char == '}':
                        pos += 1
                        if stack:
                            current_container, current_key = stack.pop()
                        else:
                            break
                    elif char == ',':
                        pos += 1
                        skip_whitespace()
                        # Expect key
                        if pos < length and json_str[pos] == '"':
                            current_key = parse_string()
                            skip_whitespace()
                            if pos < length and json_str[pos] == ':':
                                pos += 1
                                expecting_value = True
                            else:
                                raise ValueError(f"Expected ':' at position {pos}")
                        else:
                            raise ValueError(f"Expected string key at position {pos}")
                    elif char == '"':
                        # First key in object
                        current_key = parse_string()
                        skip_whitespace()
                        if pos < length and json_str[pos] == ':':
                            pos += 1
                            expecting_value = True
                        else:
                            raise ValueError(f"Expected ':' at position {pos}")
                    else:
                        raise ValueError(f"Unexpected character '{char}' in object at position {pos}")
                        
                elif isinstance(current_container, list):
                    if char == ']':
                        pos += 1
                        if stack:
                            current_container, current_key = stack.pop()
                        else:
                            break
                    elif char == ',':
                        pos += 1
                        expecting_value = True
                    else:
                        raise ValueError(f"Unexpected character '{char}' in array at position {pos}")
                else:
                    break
        
        return result

    @classmethod
    def _safe_json_parse(cls, json_str: str) -> Any:
        """
        Safely parse JSON string, using standard parser first then falling back to iterative.
        This handles deep nesting that would cause RecursionError with standard json.loads.
        """
        import sys
        
        if not json_str:
            return None
        
        # First try standard JSON parsing (faster for normal cases)
        original_limit = sys.getrecursionlimit()
        try:
            # Temporarily increase recursion limit for moderately deep trees
            sys.setrecursionlimit(max(10000, original_limit))
            return json.loads(json_str)
        except RecursionError:
            print(f"[ClusteringService] Standard JSON parsing hit recursion limit, using iterative parser")
            try:
                return cls._iterative_json_parse(json_str)
            except Exception as e:
                print(f"[ClusteringService] Iterative JSON parsing failed: {e}")
                raise
        except json.JSONDecodeError as e:
            print(f"[ClusteringService] JSON decode error: {e}")
            raise
        finally:
            sys.setrecursionlimit(original_limit)

    @classmethod
    def _safe_json_serialize(cls, tree: Dict[str, Any]) -> str:
        """
        Safely serialize a tree to JSON without recursion depth issues.
        Uses iterative approach for large/deep trees.
        Handles NaN and Infinity values properly.
        """
        import sys
        
        # Custom JSON encoder to handle NaN/Inf and numpy types
        class SafeJSONEncoder(json.JSONEncoder):
            def encode(self, o):
                if isinstance(o, float):
                    if math.isnan(o) or math.isinf(o):
                        return 'null'
                return super().encode(o)
            
            def iterencode(self, o, _one_shot=False):
                """Encode the given object and yield each string representation as available."""
                for chunk in super().iterencode(o, _one_shot):
                    yield chunk
            
            def default(self, obj):
                # Handle numpy types
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    float_val = float(obj)
                    if math.isnan(float_val) or math.isinf(float_val):
                        return None
                    return float_val
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)
        
        original_limit = sys.getrecursionlimit()
        try:
            # First attempt: normal JSON serialization with increased limit and safe encoder
            sys.setrecursionlimit(max(10000, original_limit))
            return json.dumps(tree, cls=SafeJSONEncoder, allow_nan=False)
        except (RecursionError, MemoryError, ValueError) as e:
            print(f"[ClusteringService] Normal JSON serialization failed: {e}")
            
            try:
                # Second attempt: iterative serialization
                return cls._iterative_json_serialize(tree)
            except Exception as e2:
                print(f"[ClusteringService] Iterative JSON serialization failed: {e2}")
                
                try:
                    # Final fallback: create simplified tree structure
                    simplified_tree = cls._flatten_tree_for_serialization(tree)
                    return json.dumps(simplified_tree, cls=SafeJSONEncoder, allow_nan=False)
                except Exception as e3:
                    print(f"[ClusteringService] All serialization methods failed: {e3}")
                    # Return minimal valid tree structure
                    return json.dumps({
                        'root': {
                            'id': 'fallback_root',
                            'color': '#cccccc',
                            'children': [],
                            '_error': 'Tree too large for serialization'
                        }
                    })
        finally:
            sys.setrecursionlimit(original_limit)

    @classmethod
    def _flatten_tree_for_serialization(cls, tree: Dict[str, Any], max_children: int = 10) -> Dict[str, Any]:
        """
        Create a flattened version of the tree that's safe for JSON serialization.
        Uses iterative approach to avoid recursion depth issues.
        """
        if not tree:
            return {}
        
        # Determine the starting node
        if 'root' in tree:
            start_node = tree['root']
            wrap_in_root = True
        else:
            start_node = tree
            wrap_in_root = False
        
        if not isinstance(start_node, dict):
            return tree
        
        # Create result structure using iterative approach
        # Stack: (original_node, parent_flattened_children_list_or_none, is_root)
        result_root = None
        stack = [(start_node, None, True)]
        
        while stack:
            node, parent_list, is_root = stack.pop()
            
            if not isinstance(node, dict):
                continue
            
            # Create flattened node without children
            flattened = {k: v for k, v in node.items() if k != 'children'}
            
            # Handle children
            children = node.get('children', [])
            if children:
                limited_children = children[:max_children]
                flattened['children'] = []
                
                # Add truncation marker if needed
                if len(children) > max_children:
                    flattened['children'].append({
                        'id': f"{node.get('id', 'unknown')}_truncated",
                        'height': node.get('height', 0) - 0.1,
                        'color': '#cccccc',
                        'children': [],
                        '_truncated': True,
                        '_original_count': len(children)
                    })
                
                # Add children to stack in reverse order (so first child is processed first)
                for child in reversed(limited_children):
                    stack.append((child, flattened['children'], False))
            
            # Add to parent or set as root
            if is_root:
                result_root = flattened
            elif parent_list is not None:
                # Insert at beginning since we process in reverse
                parent_list.insert(0, flattened)
        
        if wrap_in_root:
            return {'root': result_root}
        else:
            return result_root
    
    @classmethod
    def _normalize_tree_node_ids(cls, tree: Dict[str, Any]) -> None:
        """
        Convert all node IDs in the tree to strings to prevent
        mixed type comparison errors during sorting operations.
        Uses iterative approach to avoid recursion depth issues.
        """
        if not tree or not isinstance(tree, dict):
            return
        
        # Determine starting node
        if 'root' in tree:
            start_node = tree.get('root')
        else:
            start_node = tree
        
        if not isinstance(start_node, dict):
            return
        
        # Use stack-based iteration
        stack = [start_node]
        
        while stack:
            node = stack.pop()
            
            if not isinstance(node, dict):
                continue
            
            # Convert node ID to string if it exists
            if 'id' in node:
                node['id'] = str(node['id'])
            
            # Add children to stack
            children = node.get('children', [])
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        stack.append(child)

    @classmethod
    def _limit_tree_depth(cls, tree: Dict[str, Any], max_depth: int) -> Dict[str, Any]:
        """
        Limit the tree to a specified maximum depth by converting deep nodes to leaves.
        CORRECTLY collects points ONLY from leaf nodes to avoid double-counting.
        
        Args:
            tree: Tree data structure with 'root' key
            max_depth: Maximum depth to preserve (1-500)
            
        Returns:
            Tree with depth limited to max_depth, preserving ALL original leaf points
        """
        if not tree or 'root' not in tree:
            return tree
        
        # Track detailed statistics for validation
        original_leaf_count = 0
        original_point_count = 0
        cut_leaf_count = 0
        cut_point_count = 0
        nodes_cut = 0
        
        def get_leaf_point_indices(node: Dict[str, Any]) -> List[int]:
            """Extract point indices from a single leaf node using correct priority order."""
            if node.get('children'):
                return []  # Not a leaf node
            
            # Priority order for leaf nodes: pointIndices > data_indices > id
            if 'pointIndices' in node and isinstance(node['pointIndices'], list):
                indices = node['pointIndices']
            elif 'data_indices' in node and isinstance(node['data_indices'], list):
                indices = node['data_indices']
            elif 'id' in node:
                # Handle single-point leaf nodes where id represents the point
                try:
                    point_id = int(node['id'])
                    indices = [point_id]
                except (ValueError, TypeError):
                    indices = []
            else:
                indices = []
            
            # Validate and convert to integers
            valid_indices = []
            for idx in indices:
                try:
                    valid_idx = int(idx)
                    if valid_idx >= 0:
                        valid_indices.append(valid_idx)
                except (ValueError, TypeError):
                    continue
            
            return valid_indices
        
        def collect_leaf_points_only(node: Dict[str, Any]) -> List[int]:
            """Collect points ONLY from leaf nodes in subtree to avoid double-counting."""
            leaf_points = []
            leaf_count = 0
            stack = [node]
            
            while stack:
                current = stack.pop()
                
                # Check if this is a leaf node (no children)
                if not current.get('children'):
                    leaf_count += 1
                    points = get_leaf_point_indices(current)
                    leaf_points.extend(points)
                    if len(points) > 0:
                        print(f"[TreeDepthCut] Leaf node {current.get('id', 'unknown')} contributes {len(points)} points: {points[:5]}{'...' if len(points) > 5 else ''}")
                else:
                    # Continue to children for internal nodes
                    stack.extend(current.get('children', []))
            
            # Return unique, sorted indices
            unique_points = sorted(list(set(leaf_points)))
            print(f"[TreeDepthCut] Subtree has {leaf_count} leaf nodes contributing {len(unique_points)} unique points")
            return unique_points
        
        def count_original_leaf_stats(node: Dict[str, Any]) -> tuple:
            """Count original leaf nodes and their points."""
            leaf_count = 0
            total_points = set()
            stack = [node]
            
            while stack:
                current = stack.pop()
                
                if not current.get('children'):  # Leaf node
                    leaf_count += 1
                    points = get_leaf_point_indices(current)
                    total_points.update(points)
                else:
                    stack.extend(current.get('children', []))
            
            return leaf_count, len(total_points)
        
        def limit_node_depth(node: Dict[str, Any], current_depth: int) -> Dict[str, Any]:
            """Recursively limit node depth with CORRECT point preservation from leaves only."""
            nonlocal nodes_cut
            
            if current_depth >= max_depth:
                # Convert to leaf node - this is where we cut the tree
                nodes_cut += 1
                limited_node = {k: v for k, v in node.items() if k != 'children'}
                
                # Collect points ONLY from leaf nodes in this subtree
                subtree_leaf_points = collect_leaf_points_only(node)
                
                # Assign all subtree leaf points to this new leaf node
                limited_node['pointIndices'] = subtree_leaf_points
                limited_node['data_indices'] = subtree_leaf_points  # Keep both for compatibility
                
                # Mark as cut node with metadata
                limited_node['_subtree_size'] = len(subtree_leaf_points)
                limited_node['_was_cut'] = True
                limited_node['_original_depth'] = current_depth
                
                print(f"[TreeDepthCut] Cut node {node.get('id', 'unknown')} at depth {current_depth}: merged {len(subtree_leaf_points)} leaf points into new leaf")
                
                # CRITICAL: Remove children to make this a proper leaf node
                if 'children' in limited_node:
                    del limited_node['children']
                
                return limited_node
            else:
                # Continue processing children normally
                limited_node = {k: v for k, v in node.items() if k != 'children'}
                
                if 'children' in node and node['children']:
                    limited_children = []
                    for child in node['children']:
                        limited_child = limit_node_depth(child, current_depth + 1)
                        limited_children.append(limited_child)
                    limited_node['children'] = limited_children
                
                return limited_node
        
        # Count original tree statistics
        print(f"[ClusteringService] Analyzing original tree structure...")
        original_leaf_count, original_point_count = count_original_leaf_stats(tree['root'])
        print(f"[ClusteringService] Original tree: {original_leaf_count} leaf nodes, {original_point_count} unique points")
        
        # Apply depth limiting
        print(f"[ClusteringService] Applying depth limit of {max_depth}...")
        limited_tree = {
            'root': limit_node_depth(tree['root'], 0)
        }
        
        # Copy any other tree-level properties
        for key, value in tree.items():
            if key != 'root':
                limited_tree[key] = value
        
        # Validate point preservation in cut tree
        print(f"[ClusteringService] Validating cut tree...")
        cut_leaf_count, cut_point_count = count_original_leaf_stats(limited_tree['root'])
        
        print(f"[ClusteringService] Tree depth limited to {max_depth} levels")
        print(f"[ClusteringService] Cut tree: {cut_leaf_count} leaf nodes, {cut_point_count} unique points")
        print(f"[ClusteringService] Nodes cut: {nodes_cut}")
        
        # Critical validation
        if original_point_count != cut_point_count:
            lost_points = original_point_count - cut_point_count
            gained_points = cut_point_count - original_point_count
            print(f"[ClusteringService] ❌ CRITICAL ERROR: Point count mismatch!")
            print(f"[ClusteringService] Original: {original_point_count} points in {original_leaf_count} leaves")
            print(f"[ClusteringService] Cut tree: {cut_point_count} points in {cut_leaf_count} leaves")
            if lost_points > 0:
                print(f"[ClusteringService] LOST {lost_points} points during cutting!")
            if gained_points > 0:
                print(f"[ClusteringService] GAINED {gained_points} points (possible double-counting)!")
            # Don't raise exception, but log clearly for debugging
        else:
            print(f"[ClusteringService] ✅ Point preservation SUCCESSFUL: all {original_point_count} points preserved")
            print(f"[ClusteringService] Leaf reduction: {original_leaf_count} → {cut_leaf_count} ({original_leaf_count - cut_leaf_count} leaves merged)")
        
        return limited_tree



    @classmethod
    def _validate_tree_structure(cls, tree: Dict[str, Any]) -> bool:
        """Validate that the tree structure is complete and has required fields."""
        if not tree or 'root' not in tree:
            return False
        
        def check_node(node):
            # Basic node validation
            if not isinstance(node, dict):
                return False
            
            # Node should have either children or be a leaf
            children = node.get('children', [])
            if children:
                # Internal node - should have children
                if not isinstance(children, list) or len(children) == 0:
                    return False
                return all(check_node(child) for child in children)
            else:
                # Leaf node - should have necessary identifiers
                return True
        
        return check_node(tree['root'])
    
    @staticmethod
    def _load_dataset_by_id(dataset_id):
        """
        Load dataset by ID using the same unified logic as _get_dataset_data.
        Returns (X, feature_headers, X_true_labels)
        """
        try:
            print(f"[DatasetLoader] Attempting to load dataset: {dataset_id}")
            
            # Priority 1: Check file_storage first (where uploaded CSV files and toy datasets are stored)
            from .clustering_api import file_storage
            if dataset_id in file_storage:
                stored_data = file_storage[dataset_id]
                print(f"[DatasetLoader] Found dataset in file_storage: {stored_data.keys()}")
                
                # Try processed data first
                if 'processed_data' in stored_data and stored_data['processed_data'] is not None:
                    processed_data = stored_data['processed_data']
                    if 'data' in processed_data:
                        try:
                            X = np.array(processed_data['data'], dtype=float)
                            feature_headers = stored_data.get('feature_names', [f"Feature {i+1}" for i in range(X.shape[1])])
                            X_true_labels = stored_data.get('labels', [])
                            print(f"[DatasetLoader] Successfully loaded from file_storage (processed): {X.shape}")
                            return X, feature_headers, X_true_labels
                        except (ValueError, TypeError) as e:
                            print(f"[DatasetLoader] Failed to convert processed data: {e}")
                
                # Try direct data access
                if 'data' in stored_data:
                    try:
                        X = np.array(stored_data['data'], dtype=float)
                        feature_headers = stored_data.get('feature_names', [f"Feature {i+1}" for i in range(X.shape[1])])
                        X_true_labels = stored_data.get('labels', [])
                        print(f"[DatasetLoader] Successfully loaded from file_storage (direct): {X.shape}")
                        return X, feature_headers, X_true_labels
                    except (ValueError, TypeError) as e:
                        print(f"[DatasetLoader] Failed to convert direct data: {e}")
            
            # Priority 2: Try ToyDatasetService for generating new datasets
            try:
                from .toy_dataset_service import ToyDatasetService
                print(f"[DatasetLoader] Generating new dataset via ToyDatasetService")
                
                # Use the proper generate_dataset method
                X, y = ToyDatasetService.generate_dataset(dataset_id)
                
                # Create feature headers
                # Map known datasets to their real feature names
                known_feature_names = {
                    'digits_small': [f"Pixel {i+1}" for i in range(64)],
                    'digits_full': [f"Pixel {i+1}" for i in range(64)],
                    'palmer_penguins': [
                        'bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g',
                        'sex', 'island_Biscoe', 'island_Dream', 'island_Torgersen'
                    ],
                    'wheats': [
                        'Area', 'Perimeter', 'Compactness', 'Kernel Length',
                        'Kernel Width', 'Asymmetry Coeff.', 'Groove Length'
                    ],
                    'olive_oil': [
                        'Palmitic', 'Palmitoleic', 'Stearic', 'Oleic',
                        'Linoleic', 'Linolenic', 'Arachidic', 'Eicosenoic'
                    ],
                    'zoo': [
                        'Hair', 'Feathers', 'Eggs', 'Milk', 'Airborne', 'Aquatic',
                        'Predator', 'Toothed', 'Backbone', 'Breathes', 'Venomous',
                        'Fins', 'Legs', 'Tail', 'Domestic', 'Catsize'
                    ],
                }
                if dataset_id in known_feature_names:
                    feature_headers = known_feature_names[dataset_id][:X.shape[1]]
                else:
                    feature_headers = [f"Feature {i+1}" for i in range(X.shape[1])]
                
                print(f"[DatasetLoader] Successfully generated {dataset_id} via ToyDatasetService: {X.shape}")
                return X, feature_headers, y
                    
            except Exception as toy_error:
                print(f"[DatasetLoader] ToyDatasetService failed: {toy_error}")
            
            # Approach 2: Try loading sample datasets directly using sklearn
            print(f"[DatasetLoader] Trying direct sklearn loading for {dataset_id}")
            
            if dataset_id == 'digits_small' or dataset_id == 'digits_full':
                from sklearn.datasets import load_digits
                digits = load_digits()
                
                if dataset_id == 'digits_small':
                    # Use first 1797 samples for digits_small
                    X = digits.data[:1797]
                    X_true_labels = digits.target[:1797]
                else:
                    # Use all samples for digits_full
                    X = digits.data
                    X_true_labels = digits.target
                
                feature_headers = [f"Pixel {i+1}" for i in range(X.shape[1])]
                print(f"[DatasetLoader] Successfully loaded {dataset_id} via sklearn: {X.shape}")
                return X, feature_headers, X_true_labels
                
            elif dataset_id == 'iris':
                from sklearn.datasets import load_iris
                iris = load_iris()
                X = iris.data
                feature_headers = iris.feature_names
                X_true_labels = iris.target
                print(f"[DatasetLoader] Successfully loaded {dataset_id} via sklearn: {X.shape}")
                return X, feature_headers, X_true_labels
                
            elif dataset_id == 'wine':
                from sklearn.datasets import load_wine
                wine = load_wine()
                X = wine.data
                feature_headers = wine.feature_names
                X_true_labels = wine.target
                print(f"[DatasetLoader] Successfully loaded {dataset_id} via sklearn: {X.shape}")
                return X, feature_headers, X_true_labels
                
            elif dataset_id == 'breast_cancer':
                from sklearn.datasets import load_breast_cancer
                cancer = load_breast_cancer()
                X = cancer.data
                feature_headers = cancer.feature_names
                X_true_labels = cancer.target
                print(f"[DatasetLoader] Successfully loaded {dataset_id} via sklearn: {X.shape}")
                return X, feature_headers, X_true_labels
            
            else:
                print(f"[DatasetLoader] Unknown dataset ID: {dataset_id}")
                return None, None, None
                
        except Exception as e:
            print(f"[DatasetLoader] Critical error loading dataset {dataset_id}: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None

class ClusteringAnalysisService:
    """Feature analysis helpers extracted from ClusteringService."""
    @staticmethod
    def analyze_clustering_insights(cluster_data, tree_data, selected_features, feature_names, analysis_options):
        """
        Analyze clustering insights for a specific clustering result.
        Moved from frontend to backend for better performance and consistency.
        """
        try:
            analysis_options = analysis_options or {}
            # Extract data from cluster_data
            points = np.array(cluster_data.get('points', []))
            labels = np.array(cluster_data.get('labels', []))
            original_points = cluster_data.get('original_points')
            
            if len(points) == 0 or len(labels) == 0:
                return {"error": "No clustering data available"}
            
            # Use original points if available, otherwise use reduced dimensionality points
            analysis_points = np.array(original_points) if original_points else points
            
            results = {}
            
            # Cluster summary analysis
            if analysis_options.get('featureImportance', False):
                cluster_summary = []
                unique_labels = np.unique(labels)
                
                for label in unique_labels:
                    cluster_mask = labels == label
                    cluster_points = analysis_points[cluster_mask]
                    cluster_size = np.sum(cluster_mask)
                    
                    # Calculate cluster statistics
                    centroid = np.mean(cluster_points, axis=0)
                    distances = np.linalg.norm(cluster_points - centroid, axis=1)
                    compactness = np.mean(distances)
                    
                    # Inter-cluster separation (average distance to other cluster centroids)
                    other_centroids = []
                    for other_label in unique_labels:
                        if other_label != label:
                            other_mask = labels == other_label
                            other_centroid = np.mean(analysis_points[other_mask], axis=0)
                            other_centroids.append(other_centroid)
                    
                    if other_centroids:
                        separations = [np.linalg.norm(centroid - other_centroid) 
                                     for other_centroid in other_centroids]
                        separation = np.mean(separations)
                    else:
                        separation = 0.0
                    
                    cluster_summary.append({
                        'id': int(label),
                        'size': int(cluster_size),
                        'percentage': float((cluster_size / len(points)) * 100),
                        'compactness': float(compactness),
                        'separation': float(separation),
                        'density': float(min(1.0 / max(compactness, 1e-6), 1e10)),  # Inverse of compactness, capped
                        'cohesion': float(min(1.0 / max(np.std(distances), 1e-6), 1e10))  # Inverse of distance variance, capped
                    })
                
                results['clusterSummary'] = cluster_summary
            
            # Feature importance analysis
            if analysis_options.get('featureImportance', False) and len(selected_features) > 0:
                feature_importance = []
                
                # Calculate feature importance based on inter-cluster variance
                for i, feature_idx in enumerate(selected_features):
                    if feature_idx < analysis_points.shape[1]:
                        feature_values = analysis_points[:, feature_idx]
                        
                        # Calculate between-cluster variance for this feature
                        overall_mean = np.mean(feature_values)
                        between_var = 0.0
                        
                        for label in np.unique(labels):
                            cluster_mask = labels == label
                            cluster_mean = np.mean(feature_values[cluster_mask])
                            cluster_size = np.sum(cluster_mask)
                            between_var += cluster_size * (cluster_mean - overall_mean) ** 2
                        
                        between_var /= len(points)
                        total_var = np.var(feature_values)
                        
                        # Feature importance as ratio of between-cluster to total variance
                        # Sanitize to prevent NaN/Inf
                        importance = between_var / max(total_var, 1e-10)
                        if math.isnan(importance) or math.isinf(importance):
                            importance = 0.0
                        importance = min(importance, 1e6)  # Cap extreme values
                        
                        feature_name = feature_names[i] if i < len(feature_names) else f"Feature {feature_idx}"
                        feature_importance.append({
                            'feature': feature_name,
                            'score': float(importance),
                            'index': int(feature_idx)
                        })
                
                # Sort by importance score
                feature_importance.sort(key=lambda x: x['score'], reverse=True)
                results['featureImportance'] = feature_importance
            
            # Cluster distribution analysis
            if analysis_options.get('clusterDistribution', False):
                distribution = {}
                for label in labels:
                    if int(label) not in distribution:
                        distribution[int(label)] = 0
                    distribution[int(label)] += 1
                
                results['clusterDistribution'] = distribution
            
            # Dimensionality analysis
            if analysis_options.get('dimensionalityAnalysis', False) and analysis_points.shape[1] > 1:
                # PCA analysis for dimensionality insights
                try:
                    scaler = StandardScaler()
                    scaled_points = scaler.fit_transform(analysis_points)
                    
                    pca = PCA()
                    pca.fit(scaled_points)
                    
                    explained_variance_ratio = pca.explained_variance_ratio_
                    cumulative_variance = np.cumsum(explained_variance_ratio)
                    
                    # Find effective dimensions (explaining 95% of variance)
                    effective_dims = np.argmax(cumulative_variance >= 0.95) + 1
                    
                    # Estimate intrinsic dimension (simplified)
                    intrinsic_dim = min(effective_dims + 2, analysis_points.shape[1])
                    
                    results['dimensionalityInsights'] = {
                        'totalDimensions': int(analysis_points.shape[1]),
                        'effectiveDimensions': int(effective_dims),
                        'explainedVariance': float(cumulative_variance[effective_dims - 1]),
                        'intrinsicDimension': int(intrinsic_dim),
                        'varianceRatios': ClusteringService._sanitize_array_for_json(explained_variance_ratio)
                    }
                except Exception as e:
                    print(f"Error in dimensionality analysis: {e}")
                    results['dimensionalityInsights'] = None
            
            return results
            
        except Exception as e:
            print(f"Error in analyze_clustering_insights: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def analyze_dataset_insights(dataset, data, selected_features, feature_names, analysis_type, options):
        """
        Analyze dataset insights for data exploration.
        Moved from frontend to backend for better performance.
        """
        try:
            options = options or {}
            if not data or len(data) == 0:
                return {"error": "No data available for analysis"}
            
            data_array = np.array(data)
            
            # Filter data to selected features
            if selected_features:
                if max(selected_features) >= data_array.shape[1]:
                    return {"error": "Selected feature index out of bounds"}
                filtered_data = data_array[:, selected_features]
                filtered_feature_names = [feature_names[i] if i < len(feature_names) else f"Feature {selected_features[i]}" 
                                        for i in range(len(selected_features))]
            else:
                filtered_data = data_array
                filtered_feature_names = feature_names[:data_array.shape[1]]
            
            insights = []
            
            # Feature variance insights
            for i in range(filtered_data.shape[1]):
                feature_values = filtered_data[:, i]
                variance = np.var(feature_values)
                feature_name = filtered_feature_names[i] if i < len(filtered_feature_names) else f"Feature {i}"
                
                if variance > 1.0:
                    insights.append({
                        'type': 'variance',
                        'title': 'High Variance Feature',
                        'description': f'{feature_name} shows high variance ({variance:.3f})',
                        'details': [f'{feature_name}: {variance:.3f}'],
                        'impact': 'This feature may dominate clustering and dimensionality reduction'
                    })
                elif variance < 0.1:
                    insights.append({
                        'type': 'variance',
                        'title': 'Low Variance Feature',
                        'description': f'{feature_name} shows low variance ({variance:.3f})',
                        'details': [f'{feature_name}: {variance:.3f}'],
                        'impact': 'Consider removing this feature as it provides little information'
                    })
            
            # Scale differences
            ranges = []
            for i in range(filtered_data.shape[1]):
                feature_values = filtered_data[:, i]
                feature_range = np.max(feature_values) - np.min(feature_values)
                feature_name = filtered_feature_names[i] if i < len(filtered_feature_names) else f"Feature {i}"
                ranges.append({'name': feature_name, 'range': feature_range, 'index': i})
            
            if len(ranges) > 1:
                max_range = max(r['range'] for r in ranges)
                min_range = min(r['range'] for r in ranges)
                
                if max_range / (min_range + 1e-6) > 100:
                    max_feature = next(r for r in ranges if r['range'] == max_range)
                    min_feature = next(r for r in ranges if r['range'] == min_range)
                    
                    insights.append({
                        'type': 'scaling',
                        'title': 'Scale Differences Detected',
                        'description': f'Feature scales vary by factor of {int(max_range / (min_range + 1e-6))}',
                        'details': [
                            f'Largest range: {max_feature["name"]} ({max_range:.2f})',
                            f'Smallest range: {min_feature["name"]} ({min_range:.2f})'
                        ],
                        'impact': 'Consider feature scaling/normalization before clustering'
                    })
            
            # Correlation analysis
            correlation_threshold = options.get('correlationThreshold', 0.7)
            if filtered_data.shape[1] > 1:
                correlation_matrix = np.corrcoef(filtered_data.T)
                high_correlations = []
                
                for i in range(correlation_matrix.shape[0]):
                    for j in range(i + 1, correlation_matrix.shape[1]):
                        corr = correlation_matrix[i, j]
                        if abs(corr) >= correlation_threshold:
                            feature1 = filtered_feature_names[i] if i < len(filtered_feature_names) else f"Feature {i}"
                            feature2 = filtered_feature_names[j] if j < len(filtered_feature_names) else f"Feature {j}"
                            high_correlations.append(f'{feature1} ↔ {feature2}: {corr:.3f}')
                
                if high_correlations:
                    insights.append({
                        'type': 'correlation',
                        'title': 'Strong Feature Correlations',
                        'description': f'{len(high_correlations)} feature pairs show strong correlation',
                        'details': high_correlations[:3],  # Show top 3
                        'impact': 'Redundant features detected - consider dimensionality reduction'
                    })
            
            # Generate recommendations
            recommendations = []
            
            if any(i['type'] == 'scaling' for i in insights):
                recommendations.append('Apply feature scaling (StandardScaler or MinMaxScaler)')
            
            if any(i['type'] == 'variance' and 'Low' in i['title'] for i in insights):
                recommendations.append('Remove low-variance features to reduce noise')
            
            if any(i['type'] == 'correlation' for i in insights):
                recommendations.append('Apply PCA or feature selection to reduce redundancy')
            
            if len(selected_features) > 10:
                recommendations.append('Consider dimensionality reduction for better visualization')
            
            return {
                'insights': insights,
                'recommendedActions': recommendations,
                'analysisMethod': 'backend'
            }
            
        except Exception as e:
            print(f"Error in analyze_dataset_insights: {e}")
            return {"error": str(e)}

    @staticmethod
    def analyze_cluster_summary(cluster_data, selected_features, feature_names, options):
        """
        Generate comprehensive cluster summary statistics.
        Optimized backend implementation for performance.
        """
        try:
            # Extract data from cluster_data
            points = np.array(cluster_data.get('points', []))
            labels = np.array(cluster_data.get('labels', []))
            original_points = cluster_data.get('original_points')
            
            if len(points) == 0 or len(labels) == 0:
                return {"error": "No cluster data available for analysis"}
            
            # Use original points if available, otherwise use current points
            analysis_points = np.array(original_points) if original_points else points
            
            # Filter points by selected features if specified
            if selected_features and len(selected_features) > 0:
                if analysis_points.shape[1] > max(selected_features):
                    analysis_points = analysis_points[:, selected_features]
            
            unique_labels = np.unique(labels)
            summary = []
            
            # Calculate global statistics for comparison
            global_mean = np.mean(analysis_points, axis=0)
            
            for label in unique_labels:
                # Get points belonging to this cluster
                cluster_mask = labels == label
                cluster_points = analysis_points[cluster_mask]
                
                if len(cluster_points) == 0:
                    continue
                
                size = len(cluster_points)
                percentage = (size / len(labels)) * 100
                
                # Calculate cluster centroid
                centroid = np.mean(cluster_points, axis=0)
                
                # Calculate compactness (average distance to centroid)
                distances_to_centroid = np.linalg.norm(cluster_points - centroid, axis=1)
                compactness = np.mean(distances_to_centroid)
                
                # Calculate separation (distance to nearest other cluster centroid)
                other_centroids = []
                for other_label in unique_labels:
                    if other_label != label:
                        other_mask = labels == other_label
                        other_points = analysis_points[other_mask]
                        if len(other_points) > 0:
                            other_centroid = np.mean(other_points, axis=0)
                            other_centroids.append(other_centroid)
                
                if other_centroids:
                    distances_to_others = [np.linalg.norm(centroid - other_centroid) 
                                         for other_centroid in other_centroids]
                    separation = min(distances_to_others)
                else:
                    separation = 0.0
                
                # Calculate density (points per unit volume - simplified as points per compactness)
                # Cap to prevent Inf
                density = size / max(compactness, 1e-6)
                if math.isinf(density) or density > 1e10:
                    density = 1e10
                
                # Calculate cohesion (separation to compactness ratio)
                # Cap to prevent Inf
                cohesion = separation / max(compactness, 1e-6)
                if math.isinf(cohesion) or cohesion > 1e10:
                    cohesion = 1e10
                
                summary.append({
                    'id': int(label),
                    'size': int(size),
                    'percentage': float(percentage),
                    'compactness': float(compactness),
                    'separation': float(separation),
                    'density': float(density),
                    'cohesion': float(cohesion),
                    'centroid': ClusteringService._sanitize_array_for_json(centroid)
                })
            
            # Sort by cluster ID
            summary.sort(key=lambda x: x['id'])
            
            return {
                'cluster_summary': summary,
                'total_clusters': len(unique_labels),
                'total_points': len(labels),
                'analysis_method': 'backend'
            }
            
        except Exception as e:
            print(f"Error in analyze_cluster_summary: {e}")
            return {"error": str(e)}

    @staticmethod
    def analyze_feature_importance(cluster_data, selected_features, feature_names, options):
        """
        Calculate feature importance for clustering analysis using variance ratio method.
        Optimized backend implementation with scikit-learn.
        """
        try:
            # Extract data from cluster_data
            points = np.array(cluster_data.get('points', []))
            labels = np.array(cluster_data.get('labels', []))
            original_points = cluster_data.get('original_points')
            
            if len(points) == 0 or len(labels) == 0:
                return {"error": "No cluster data available for analysis"}
            
            # Use original points if available for feature importance
            if original_points is not None and len(original_points) > 0:
                analysis_points = np.array(original_points)
                print(f"[FeatureImportance] Using original_points with shape: {analysis_points.shape}")
            else:
                analysis_points = points
                print(f"[FeatureImportance] Using points with shape: {analysis_points.shape}")
                print(f"[FeatureImportance] Warning: No original_points available, using reduced dimensionality data")
            
            # For feature importance analysis, we always analyze ALL features
            # Feature filtering is not appropriate here as we need the complete picture
            effective_feature_names = feature_names
            
            print(f"[FeatureImportance] Analysis will cover {analysis_points.shape[1]} features")
            
            num_features = analysis_points.shape[1]
            unique_labels = np.unique(labels)
            importance_scores = []
            
            # Calculate feature importance using between-cluster vs within-cluster variance
            for feature_idx in range(num_features):
                feature_values = analysis_points[:, feature_idx]
                
                # Calculate overall mean
                overall_mean = np.mean(feature_values)
                total_variance = np.var(feature_values)
                
                # Calculate between-cluster variance
                between_variance = 0.0
                within_variance = 0.0
                
                for label in unique_labels:
                    cluster_mask = labels == label
                    cluster_values = feature_values[cluster_mask]
                    
                    if len(cluster_values) == 0:
                        continue
                    
                    cluster_mean = np.mean(cluster_values)
                    cluster_size = len(cluster_values)
                    
                    # Between-cluster variance contribution
                    between_variance += cluster_size * (cluster_mean - overall_mean) ** 2
                    
                    # Within-cluster variance contribution
                    within_variance += np.sum((cluster_values - cluster_mean) ** 2)
                
                # Normalize by total number of points
                between_variance /= len(labels)
                within_variance /= len(labels)
                
                # Calculate importance score as ratio of between to within variance
                if within_variance > 1e-8:
                    importance_score = between_variance / within_variance
                else:
                    importance_score = between_variance  # If within-variance is zero
                
                # Normalize score to 0-1 range
                normalized_score = min(importance_score / (importance_score + 1), 1.0)
                
                feature_name = (effective_feature_names[feature_idx] 
                              if feature_idx < len(effective_feature_names) 
                              else f"Feature {feature_idx}")
                
                importance_scores.append({
                    'feature': feature_name,
                    'score': float(normalized_score),
                    'index': feature_idx,
                    'raw_score': float(importance_score),
                    'between_variance': float(between_variance),
                    'within_variance': float(within_variance)
                })
            
            # Sort by importance score (descending)
            importance_scores.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'feature_importance': importance_scores,
                'method': 'variance_ratio',
                'num_features': num_features,
                'num_clusters': len(unique_labels),
                'analysis_method': 'backend'
            }
            
        except Exception as e:
            print(f"Error in analyze_feature_importance: {e}")
            return {"error": str(e)}

    @staticmethod
    def analyze_feature_importance_dataset(dataset_id, cluster_labels, selected_features, feature_names, options):
        """
        Calculate feature importance by loading dataset directly - guaranteed to work with big datasets.
        This method loads the original dataset and performs feature importance analysis.
        """
        try:
            print(f"[FeatureImportanceDataset] ========== STARTING ANALYSIS ==========")
            print(f"[FeatureImportanceDataset] Dataset ID: {dataset_id}")
            print(f"[FeatureImportanceDataset] Cluster labels provided: {len(cluster_labels) if cluster_labels else 0}")
            print(f"[FeatureImportanceDataset] Selected features: {len(selected_features)}")
            print(f"[FeatureImportanceDataset] Feature names: {len(feature_names)}")
            
            # Load the original dataset using the same logic as clustering
            X, feature_headers, X_true_labels = ClusteringService._load_dataset_by_id(dataset_id)
            
            if X is None or len(X) == 0:
                error_msg = f"Failed to load dataset: {dataset_id}"
                print(f"[FeatureImportanceDataset] ERROR: {error_msg}")
                return {"error": error_msg}
            
            print(f"[FeatureImportanceDataset] ✅ Successfully loaded dataset!")
            print(f"[FeatureImportanceDataset] Dataset shape: {X.shape}")
            print(f"[FeatureImportanceDataset] Feature headers: {len(feature_headers) if feature_headers else 0}")
            print(f"[FeatureImportanceDataset] Sample data range: min={np.min(X):.3f}, max={np.max(X):.3f}, mean={np.mean(X):.3f}")
            
            # Validate cluster labels
            if not cluster_labels or len(cluster_labels) != len(X):
                error_msg = f"Cluster labels length ({len(cluster_labels) if cluster_labels else 0}) doesn't match dataset size ({len(X)})"
                print(f"[FeatureImportanceDataset] ERROR: {error_msg}")
                return {"error": error_msg}
            
            labels = np.array(cluster_labels)
            unique_labels = np.unique(labels)
            print(f"[FeatureImportanceDataset] ✅ Cluster labels validated!")
            print(f"[FeatureImportanceDataset] Unique clusters: {unique_labels}")
            print(f"[FeatureImportanceDataset] Cluster counts: {[np.sum(labels == label) for label in unique_labels]}")
            
            # Use provided feature names or generate them
            if not feature_names or len(feature_names) < X.shape[1]:
                if feature_headers and len(feature_headers) >= X.shape[1]:
                    effective_feature_names = feature_headers[:X.shape[1]]
                else:
                    effective_feature_names = [f"Feature {i+1}" for i in range(X.shape[1])]
            else:
                effective_feature_names = feature_names[:X.shape[1]]
            
            num_features = X.shape[1]
            importance_scores = []
            
            print(f"[FeatureImportanceDataset] Analyzing {num_features} features")
            
            # Calculate feature importance using between-cluster vs within-cluster variance
            for feature_idx in range(num_features):
                feature_values = X[:, feature_idx]
                
                # Skip features with all NaN or invalid values
                if np.all(np.isnan(feature_values)) or np.all(np.isinf(feature_values)):
                    print(f"[FeatureImportanceDataset] Skipping feature {feature_idx}: all values are NaN/inf")
                    importance_scores.append({
                        'feature': (effective_feature_names[feature_idx] 
                                  if feature_idx < len(effective_feature_names) 
                                  else f"Feature {feature_idx+1}"),
                        'score': 0.0,
                        'index': feature_idx,
                        'raw_score': 0.0,
                        'between_variance': 0.0,
                        'within_variance': 0.0
                    })
                    continue
                
                # Handle NaN values by using nanmean and nanstd
                valid_mask = ~np.isnan(feature_values) & ~np.isinf(feature_values)
                if np.sum(valid_mask) < 2:
                    print(f"[FeatureImportanceDataset] Skipping feature {feature_idx}: insufficient valid values")
                    importance_scores.append({
                        'feature': (effective_feature_names[feature_idx] 
                                  if feature_idx < len(effective_feature_names) 
                                  else f"Feature {feature_idx+1}"),
                        'score': 0.0,
                        'index': feature_idx,
                        'raw_score': 0.0,
                        'between_variance': 0.0,
                        'within_variance': 0.0
                    })
                    continue
                
                # Calculate overall mean using valid values only
                overall_mean = np.nanmean(feature_values)
                
                # Calculate between-cluster variance and within-cluster variance
                between_variance = 0.0
                within_variance = 0.0
                total_valid_points = 0
                
                for label in unique_labels:
                    cluster_mask = labels == label
                    cluster_values = feature_values[cluster_mask]
                    
                    # Filter out NaN/inf values
                    cluster_valid_mask = ~np.isnan(cluster_values) & ~np.isinf(cluster_values)
                    cluster_valid_values = cluster_values[cluster_valid_mask]
                    
                    if len(cluster_valid_values) == 0:
                        continue
                    
                    cluster_mean = np.mean(cluster_valid_values)
                    cluster_size = len(cluster_valid_values)
                    total_valid_points += cluster_size
                    
                    # Between-cluster variance contribution
                    if not np.isnan(cluster_mean) and not np.isnan(overall_mean):
                        between_variance += cluster_size * (cluster_mean - overall_mean) ** 2
                    
                    # Within-cluster variance contribution
                    within_cluster_var = np.sum((cluster_valid_values - cluster_mean) ** 2)
                    if not np.isnan(within_cluster_var):
                        within_variance += within_cluster_var
                
                # Normalize by total number of valid points
                if total_valid_points > 0:
                    between_variance /= total_valid_points
                    within_variance /= total_valid_points
                else:
                    between_variance = 0.0
                    within_variance = 0.0
                
                # Calculate importance score as ratio of between to within variance
                if within_variance > 1e-10 and not np.isnan(within_variance) and not np.isnan(between_variance):
                    importance_score = between_variance / within_variance
                else:
                    # If within-variance is zero or invalid, use between-variance directly
                    importance_score = between_variance if not np.isnan(between_variance) else 0.0
                
                # Ensure importance_score is valid
                if np.isnan(importance_score) or np.isinf(importance_score):
                    importance_score = 0.0
                
                # Normalize score to 0-1 range (safer normalization)
                if importance_score > 0:
                    normalized_score = importance_score / (importance_score + 1.0)
                else:
                    normalized_score = 0.0
                
                # Final safety check
                if np.isnan(normalized_score) or np.isinf(normalized_score):
                    normalized_score = 0.0
                
                feature_name = (effective_feature_names[feature_idx] 
                              if feature_idx < len(effective_feature_names) 
                              else f"Feature {feature_idx+1}")
                
                # Ensure all values are finite before converting to float
                safe_normalized_score = 0.0 if np.isnan(normalized_score) or np.isinf(normalized_score) else float(normalized_score)
                safe_importance_score = 0.0 if np.isnan(importance_score) or np.isinf(importance_score) else float(importance_score)
                safe_between_variance = 0.0 if np.isnan(between_variance) or np.isinf(between_variance) else float(between_variance)
                safe_within_variance = 0.0 if np.isnan(within_variance) or np.isinf(within_variance) else float(within_variance)
                
                importance_scores.append({
                    'feature': feature_name,
                    'score': safe_normalized_score,
                    'index': feature_idx,
                    'raw_score': safe_importance_score,
                    'between_variance': safe_between_variance,
                    'within_variance': safe_within_variance
                })
                
                # Debug logging for first few features
                if feature_idx < 5:
                    print(f"[FeatureImportanceDataset] Feature {feature_idx} ({feature_name}): score={safe_normalized_score:.6f}, between={safe_between_variance:.6f}, within={safe_within_variance:.6f}")
            
            # Sort by importance score (descending)
            importance_scores.sort(key=lambda x: x['score'], reverse=True)
            
            print(f"[FeatureImportanceDataset] Completed analysis for {num_features} features")
            
            return {
                'feature_importance': importance_scores,
                'method': 'variance_ratio_dataset',
                'num_features': num_features,
                'num_clusters': len(unique_labels),
                'dataset_id': dataset_id,
                'analysis_method': 'backend_dataset'
            }
            
        except Exception as e:
            print(f"Error in analyze_feature_importance_dataset: {e}")
            return {"error": str(e)}

    @staticmethod
    def analyze_feature_statistics(data, selected_features, feature_names, options):
        """
        Calculate comprehensive feature statistics.
        Optimized backend implementation using NumPy with intelligent caching.
        """
        try:
            options = options or {}
            if not data or len(data) == 0:
                return {"error": "No data available for analysis"}
            
            data_array = np.array(data)
            
            # Check cache first
            from .ship_cache_service import SHiPCacheService
            # cached_result = SHiPCacheService.get_cached_stats(
            #     data_array, 'feature_statistics', selected_features, options
            # )
            cached_result = None
            if cached_result:
                return cached_result
            
            # Filter by selected features if specified
            if selected_features and len(selected_features) > 0:
                if data_array.shape[1] > max(selected_features):
                    data_array = data_array[:, selected_features]
                    effective_feature_names = [feature_names[i] if i < len(feature_names) else f"Feature {i}" 
                                             for i in selected_features]
                else:
                    effective_feature_names = feature_names
            else:
                effective_feature_names = feature_names
            
            num_features = data_array.shape[1]
            statistics = []
            
            for feature_idx in range(num_features):
                feature_values = data_array[:, feature_idx]
                
                # Handle missing values (NaN, None, inf)
                valid_mask = np.isfinite(feature_values)
                valid_values = feature_values[valid_mask]
                
                if len(valid_values) == 0:
                    # All values are invalid
                    statistics.append({
                        'feature': feature_idx,
                        'feature_name': (effective_feature_names[feature_idx] 
                                       if feature_idx < len(effective_feature_names) 
                                       else f"Feature {feature_idx}"),
                        'count': 0,
                        'missing': len(feature_values),
                        'mean': None,
                        'std': None,
                        'min': None,
                        'max': None,
                        'variance': None,
                        'unique': 0,
                        'skewness': None,
                        'kurtosis': None
                    })
                    continue
                
                # Calculate basic statistics
                mean = np.mean(valid_values)
                std = np.std(valid_values, ddof=1) if len(valid_values) > 1 else 0.0
                variance = np.var(valid_values, ddof=1) if len(valid_values) > 1 else 0.0
                min_val = np.min(valid_values)
                max_val = np.max(valid_values)
                unique_count = len(np.unique(valid_values))
                missing_count = len(feature_values) - len(valid_values)
                
                # Calculate skewness and kurtosis
                if len(valid_values) > 2 and std > 1e-8:
                    # Simple skewness calculation
                    normalized_values = (valid_values - mean) / std
                    skewness = np.mean(normalized_values ** 3)
                    kurtosis = np.mean(normalized_values ** 4) - 3  # Excess kurtosis
                    
                    # Sanitize skewness and kurtosis
                    if math.isnan(skewness) or math.isinf(skewness):
                        skewness = 0.0
                    else:
                        skewness = max(-1e6, min(skewness, 1e6))  # Cap extreme values
                    
                    if math.isnan(kurtosis) or math.isinf(kurtosis):
                        kurtosis = 0.0
                    else:
                        kurtosis = max(-1e6, min(kurtosis, 1e6))  # Cap extreme values
                else:
                    skewness = 0.0
                    kurtosis = 0.0
                
                # Sanitize all float values before appending
                mean = 0.0 if math.isnan(mean) or math.isinf(mean) else mean
                std = 0.0 if math.isnan(std) or math.isinf(std) else std
                variance = 0.0 if math.isnan(variance) or math.isinf(variance) else variance
                min_val = 0.0 if math.isnan(min_val) or math.isinf(min_val) else min_val
                max_val = 0.0 if math.isnan(max_val) or math.isinf(max_val) else max_val
                
                feature_name = (effective_feature_names[feature_idx] 
                              if feature_idx < len(effective_feature_names) 
                              else f"Feature {feature_idx}")
                
                statistics.append({
                    'feature': feature_idx,
                    'feature_name': feature_name,
                    'count': int(len(valid_values)),
                    'missing': int(missing_count),
                    'mean': float(mean),
                    'std': float(std),
                    'min': float(min_val),
                    'max': float(max_val),
                    'variance': float(variance),
                    'unique': int(unique_count),
                    'skewness': float(skewness),
                    'kurtosis': float(kurtosis)
                })
            
            result = {
                'feature_statistics': statistics,
                'total_features': num_features,
                'total_samples': len(data_array),
                'analysis_method': 'backend'
            }
            
            # Cache the result for future use
            # SHiPCacheService.cache_stats_result(
            #     data_array, 'feature_statistics', result, selected_features, options
            # )
            
            return result
            
        except Exception as e:
            print(f"Error in analyze_feature_statistics: {e}")
            return {"error": str(e)}

    @staticmethod
    def analyze_correlation_matrix(data, selected_features, feature_names, options):
        """
        Calculate correlation matrix for selected features.
        Optimized backend implementation with support for Pearson and Spearman correlation.
        """
        try:
            options = options or {}
            if not data or len(data) == 0:
                return {"error": "No data available for analysis"}
            
            data_array = np.array(data)
            
            # Check cache first
            from .ship_cache_service import SHiPCacheService
            # cached_result = SHiPCacheService.get_cached_stats(
            #     data_array, 'correlation_matrix', selected_features, options
            # )
            cached_result = None
            if cached_result:
                return cached_result
            
            # Filter by selected features if specified
            if selected_features and len(selected_features) > 0:
                if data_array.shape[1] > max(selected_features):
                    data_array = data_array[:, selected_features]
                    effective_feature_names = [feature_names[i] if i < len(feature_names) else f"Feature {i}" 
                                             for i in selected_features]
                else:
                    effective_feature_names = feature_names
            else:
                effective_feature_names = feature_names
            
            num_features = data_array.shape[1]
            
            if num_features < 2:
                return {"error": "Need at least 2 features for correlation analysis"}
            
            # Get correlation method (default to Spearman for better non-linear handling)
            correlation_method = options.get('correlation_method', 'spearman')
            
            # Handle missing values by using only valid pairs
            correlation_matrix = np.full((num_features, num_features), np.nan)
            
            for i in range(num_features):
                for j in range(num_features):
                    if i == j:
                        correlation_matrix[i, j] = 1.0
                    else:
                        values_i = data_array[:, i]
                        values_j = data_array[:, j]
                        
                        # Find valid pairs (both values are finite)
                        valid_mask = np.isfinite(values_i) & np.isfinite(values_j)
                        valid_i = values_i[valid_mask]
                        valid_j = values_j[valid_mask]
                        
                        if len(valid_i) > 2:  # Need at least 3 points for Spearman
                            if correlation_method.lower() == 'spearman':
                                # Calculate Spearman rank correlation (better for non-linear relationships)
                                correlation, _ = spearmanr(valid_i, valid_j)
                                correlation_matrix[i, j] = correlation if np.isfinite(correlation) else 0.0
                            else:
                                # Default to Pearson correlation
                                correlation = np.corrcoef(valid_i, valid_j)[0, 1]
                                correlation_matrix[i, j] = correlation if np.isfinite(correlation) else 0.0
                        else:
                            correlation_matrix[i, j] = 0.0
            
            # Find top correlations (excluding self-correlations)
            correlations_list = []
            threshold = options.get('correlation_threshold', 0.0)
            
            for i in range(num_features):
                for j in range(i + 1, num_features):
                    corr_value = correlation_matrix[i, j]
                    if np.isfinite(corr_value) and abs(corr_value) >= threshold:
                        feature_name_i = (effective_feature_names[i] 
                                        if i < len(effective_feature_names) 
                                        else f"Feature {i}")
                        feature_name_j = (effective_feature_names[j] 
                                        if j < len(effective_feature_names) 
                                        else f"Feature {j}")
                        
                        correlations_list.append({
                            'feature1': feature_name_i,
                            'feature2': feature_name_j,
                            'correlation': float(corr_value),
                            'abs_correlation': float(abs(corr_value)),
                            'feature1_index': i,
                            'feature2_index': j
                        })
            
            # Sort by absolute correlation value (descending)
            correlations_list.sort(key=lambda x: x['abs_correlation'], reverse=True)
            
            # Get top correlations (limit to top 10 by default)
            top_limit = options.get('top_correlations_limit', 10)
            top_correlations = correlations_list[:top_limit]
            
            result = {
                'correlation_matrix': ClusteringService._sanitize_array_for_json(correlation_matrix),
                'feature_names': effective_feature_names,
                'top_correlations': top_correlations,
                'all_correlations': correlations_list,
                'num_features': num_features,
                'threshold': threshold,
                'correlation_method': correlation_method,
                'analysis_method': 'backend'
            }
            
            # Cache the result for future use
            # SHiPCacheService.cache_stats_result(
            #     data_array, 'correlation_matrix', result, selected_features, options
            # )
            
            return result
            
        except Exception as e:
            print(f"Error in analyze_correlation_matrix: {e}")
            return {"error": str(e)}
    




def _enum_to_str_list(enum_cls):
    # For pybind11 enums, dir(enum_cls) gives all names, filter out dunder methods and enum instance properties
    return [name for name in dir(enum_cls) if not name.startswith('__') and not name.endswith('__') and name not in ['name', 'value']]

AVAILABLE_ULTRAMETRIC_TREE_TYPES = _enum_to_str_list(UTreeType)
AVAILABLE_PARTITIONING_METHODS = _enum_to_str_list(PMethod)


__all__ = [
    "ClusterParams",
    "ClusteringService",
    "ClusteringAnalysisService",
    "AVAILABLE_ULTRAMETRIC_TREE_TYPES",
    "AVAILABLE_PARTITIONING_METHODS",
]
