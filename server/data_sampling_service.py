import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from sklearn.cluster import KMeans
import random
import time


class DataSamplingService:
    """
    Service for intelligently sampling large datasets for visualization.
    This makes scatterplot rendering feasible for very large datasets.
    """
    
    @classmethod
    def sample_for_visualization(cls, 
                                points: List[List[float]], 
                                labels: List[int], 
                                max_points: int = 5000,
                                strategy: str = "stratified",
                                preserve_clusters: bool = True,
                                random_state: int = 42) -> Dict[str, Any]:
        """
        Sample data points for visualization while preserving cluster structure.
        
        Args:
            points: Original data points
            labels: Cluster labels for each point
            max_points: Maximum number of points to include in visualization
            strategy: Sampling strategy ('stratified', 'random', 'representative')
            preserve_clusters: Whether to maintain cluster proportions
            random_state: Random seed for reproducibility
            
        Returns:
            Dictionary with sampled data and metadata
        """
        start_time_total = time.time()
        points_array = np.array(points)
        labels_array = np.array(labels)
        
        total_points = len(points)
        
        if total_points <= max_points:
            # Dataset is already small enough
            print(f"[DataSamplingService] No sampling applied, total_points ({total_points}) <= max_points ({max_points}). Took {time.time() - start_time_total:.4f} seconds")
            return {
                'points': points,
                'labels': labels,
                'original_indices': list(range(total_points)),
                'sampling_info': {
                    'was_sampled': False,
                    'original_count': total_points,
                    'final_count': total_points,
                    'strategy': strategy
                }
            }
        
        # Set random seed
        np.random.seed(random_state)
        random.seed(random_state)
        
        start_time_sampling_strategy = time.time()
        if strategy == "stratified":
            sampled_data = cls._stratified_sampling(
                points_array, labels_array, max_points, preserve_clusters
            )
        elif strategy == "representative":
            sampled_data = cls._representative_sampling(
                points_array, labels_array, max_points, random_state
            )
        else:  # random
            sampled_data = cls._random_sampling(
                points_array, labels_array, max_points
            )
        end_time_sampling_strategy = time.time()
        print(f"[DataSamplingService] Sampling strategy '{strategy}' took {end_time_sampling_strategy - start_time_sampling_strategy:.4f} seconds")
        
        end_time_total = time.time()
        print(f"[DataSamplingService] Total sample_for_visualization took {end_time_total - start_time_total:.4f} seconds")

        return {
            **sampled_data,
            'sampling_info': {
                'was_sampled': True,
                'original_count': total_points,
                'final_count': len(sampled_data['points']),
                'strategy': strategy,
                'sampling_ratio': len(sampled_data['points']) / total_points,
                'preserve_clusters': preserve_clusters
            }
        }
    
    @classmethod
    def _stratified_sampling(cls, points: np.ndarray, labels: np.ndarray, 
                           max_points: int, preserve_clusters: bool) -> Dict[str, Any]:
        """
        Optimized stratified sampling that maintains cluster proportions.
        """
        start_time = time.time()
        unique_labels = np.unique(labels)
        sampled_indices = np.array([], dtype=np.int32)
        
        if preserve_clusters:
            # Vectorized calculation of cluster counts
            label_counts = np.bincount(labels)
            total_points = len(points)
            
            for label in unique_labels:
                cluster_proportion = label_counts[label] / total_points
                cluster_sample_size = max(1, int(max_points * cluster_proportion))
                
                # Vectorized cluster index selection
                cluster_mask = labels == label
                cluster_indices = np.where(cluster_mask)[0]
                
                # Efficient sampling
                if len(cluster_indices) <= cluster_sample_size:
                    sampled_indices = np.concatenate([sampled_indices, cluster_indices])
                else:
                    # Use numpy's random choice for efficiency
                    cluster_sample = np.random.choice(
                        cluster_indices, 
                        size=cluster_sample_size, 
                        replace=False
                    )
                    sampled_indices = np.concatenate([sampled_indices, cluster_sample])
        else:
            # Equal points per cluster - optimized
            points_per_cluster = max(1, max_points // len(unique_labels))
            
            for label in unique_labels:
                cluster_mask = labels == label
                cluster_indices = np.where(cluster_mask)[0]
                
                if len(cluster_indices) <= points_per_cluster:
                    sampled_indices = np.concatenate([sampled_indices, cluster_indices])
                else:
                    cluster_sample = np.random.choice(
                        cluster_indices, 
                        size=points_per_cluster, 
                        replace=False
                    )
                    sampled_indices = np.concatenate([sampled_indices, cluster_sample])
        
        # Ensure we don't exceed max_points - efficient final sampling
        if len(sampled_indices) > max_points:
            sampled_indices = np.random.choice(
                sampled_indices, 
                size=max_points, 
                replace=False
            )
        
        # Sort indices for better cache performance when accessing data
        sampled_indices = np.sort(sampled_indices)
        end_time = time.time()
        print(f"[DataSamplingService] _stratified_sampling took {end_time - start_time:.4f} seconds")
        
        return {
            'points': points[sampled_indices].tolist(),
            'labels': labels[sampled_indices].tolist(),
            'original_indices': sampled_indices.tolist()
        }
    
    @classmethod
    def _representative_sampling(cls, points: np.ndarray, labels: np.ndarray, 
                               max_points: int, random_state: int) -> Dict[str, Any]:
        """
        Representative sampling using clustering within clusters.
        """
        start_time = time.time()
        unique_labels = np.unique(labels)
        sampled_indices = []
        
        points_per_cluster = max(1, max_points // len(unique_labels))
        
        for label in unique_labels:
            cluster_indices = np.where(labels == label)[0]
            cluster_points = points[cluster_indices]
            
            if len(cluster_points) <= points_per_cluster:
                sampled_indices.extend(cluster_indices)
            else:
                # Use K-means to find representative points within the cluster
                n_representatives = min(points_per_cluster, len(cluster_points))
                
                if cluster_points.shape[1] >= 2 and len(cluster_points) > n_representatives:
                    try:
                        kmeans = KMeans(
                            n_clusters=n_representatives, 
                            random_state=random_state,
                            n_init=5
                        )
                        kmeans.fit(cluster_points)
                        
                        # Find closest points to centroids
                        representatives = []
                        for centroid in kmeans.cluster_centers_:
                            distances = np.sum((cluster_points - centroid) ** 2, axis=1)
                            closest_idx = np.argmin(distances)
                            representatives.append(cluster_indices[closest_idx])
                        
                        sampled_indices.extend(representatives)
                    except Exception:
                        # Fallback to random sampling if K-means fails
                        cluster_sample = np.random.choice(
                            cluster_indices, 
                            size=n_representatives, 
                            replace=False
                        )
                        sampled_indices.extend(cluster_sample)
                else:
                    # Too few points or dimensions for K-means
                    cluster_sample = np.random.choice(
                        cluster_indices, 
                        size=n_representatives, 
                        replace=False
                    )
                    sampled_indices.extend(cluster_sample)
        end_time = time.time()
        print(f"[DataSamplingService] _representative_sampling took {end_time - start_time:.4f} seconds")
        
        return {
            'points': points[sampled_indices].tolist(),
            'labels': labels[sampled_indices].tolist(),
            'original_indices': sampled_indices.tolist()
        }
    
    @classmethod
    def _random_sampling(cls, points: np.ndarray, labels: np.ndarray, 
                        max_points: int) -> Dict[str, Any]:
        """
        Simple random sampling.
        """
        start_time = time.time()
        sampled_indices = np.random.choice(
            len(points), 
            size=min(max_points, len(points)), 
            replace=False
        )
        end_time = time.time()
        print(f"[DataSamplingService] _random_sampling took {end_time - start_time:.4f} seconds")
        
        return {
            'points': points[sampled_indices].tolist(),
            'labels': labels[sampled_indices].tolist(),
            'original_indices': sampled_indices.tolist()
        }
    
    @classmethod
    def get_sampling_recommendations(cls, data_size: int) -> Dict[str, Any]:
        """
        Get recommended sampling parameters based on data size.
        """
        if data_size <= 1000:
            return {
                'should_sample': False,
                'max_points': data_size,
                'strategy': 'none'
            }
        elif data_size <= 10000:
            return {
                'should_sample': True,
                'max_points': min(5000, data_size),
                'strategy': 'stratified'
            }
        elif data_size <= 100000:
            return {
                'should_sample': True,
                'max_points': 3000,
                'strategy': 'stratified'
            }
        else:  # Very large datasets
            return {
                'should_sample': True,
                'max_points': 2000,
                'strategy': 'representative'
            }
    
    @classmethod
    def apply_sampling_to_cluster_data(cls, cluster_data: Dict[str, Any], 
                                     max_points: int = None) -> Dict[str, Any]:
        """
        Apply sampling to full cluster data structure with enhanced mapping support.
        """
        if not cluster_data.get('points') or not cluster_data.get('labels'):
            return cluster_data
        
        data_size = len(cluster_data['points'])
        
        # Get recommendations if max_points not specified
        if max_points is None:
            recommendations = cls.get_sampling_recommendations(data_size)
            if not recommendations['should_sample']:
                return cluster_data
            max_points = recommendations['max_points']
        
        # Sample the data
        sampled = cls.sample_for_visualization(
            points=cluster_data['points'],
            labels=cluster_data['labels'],
            max_points=max_points,
            strategy='stratified'
        )
        
        # Create new cluster data with sampled points
        result = cluster_data.copy()
        result['points'] = sampled['points']
        result['labels'] = sampled['labels']
        result['original_indices'] = sampled['original_indices']
        
        # Create efficient mapping for interactive features
        # Map from original index to sampled index
        original_to_sampled = {
            orig_idx: new_idx 
            for new_idx, orig_idx in enumerate(sampled['original_indices'])
        }
        result['index_mapping'] = {
            'original_to_sampled': original_to_sampled,
            'sampled_to_original': sampled['original_indices']
        }
        
        # Update scatter colors if present - optimized with list comprehension
        if 'scatter_colors' in cluster_data and cluster_data['scatter_colors']:
            original_colors = cluster_data['scatter_colors']
            result['scatter_colors'] = [
                original_colors[i] for i in sampled['original_indices']
            ]
        
        # Update dimensionality reduction data if present - optimized with memory management
        if 'dimensionality_reduction' in cluster_data and cluster_data['dimensionality_reduction']:
            dr_data = cluster_data['dimensionality_reduction']
            new_dr_data = {}
            
            if dr_data.get('pca'):
                # Use numpy array slicing for efficiency and clear intermediate arrays
                pca_array = np.array(dr_data['pca'])
                sampled_pca = pca_array[sampled['original_indices']]
                new_dr_data['pca'] = sampled_pca.tolist()
                # Clear intermediate arrays to save memory
                del pca_array, sampled_pca
            
            if dr_data.get('umap'):
                # Use numpy array slicing for efficiency and clear intermediate arrays
                umap_array = np.array(dr_data['umap'])
                sampled_umap = umap_array[sampled['original_indices']]
                new_dr_data['umap'] = sampled_umap.tolist()
                # Clear intermediate arrays to save memory
                del umap_array, sampled_umap
            
            result['dimensionality_reduction'] = new_dr_data
        
        # Add sampling metadata
        result['sampling_info'] = sampled['sampling_info']
        
        return result
    
    @classmethod
    def get_highlighted_sampled_indices(cls, original_highlighted_indices: List[int], 
                                      index_mapping: Dict[str, Any]) -> List[int]:
        """
        Convert original data indices to sampled data indices for highlighting.
        
        Args:
            original_highlighted_indices: Indices in the original dataset
            index_mapping: Mapping information from apply_sampling_to_cluster_data
            
        Returns:
            List of indices in the sampled dataset
        """
        if not index_mapping or 'original_to_sampled' not in index_mapping:
            return []
        
        original_to_sampled = index_mapping['original_to_sampled']
        sampled_indices = []
        
        for orig_idx in original_highlighted_indices:
            if orig_idx in original_to_sampled:
                sampled_indices.append(original_to_sampled[orig_idx])
        
        return sampled_indices 