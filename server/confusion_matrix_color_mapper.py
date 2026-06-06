import numpy as np
from sklearn.metrics import confusion_matrix
from scipy.optimize import linear_sum_assignment
from typing import Dict, List, Tuple, Optional
import json

class ConfusionMatrixColorMapper:
    """
    Maps predicted cluster colors to ground truth colors using confusion matrix
    to ensure the same clusters have the same colors in both visualizations.
    """
    
    def __init__(self, predicted_labels: List, ground_truth_labels: List, 
                 predicted_colors: List[str], ground_truth_colors: List[str]):
        """
        Initialize the color mapper with clustering results and color palettes.
        
        Args:
            predicted_labels: List of predicted cluster labels
            ground_truth_labels: List of ground truth cluster labels  
            predicted_colors: List of colors for predicted clusters
            ground_truth_colors: List of colors for ground truth clusters
        """
        self.predicted_labels = np.array(predicted_labels)
        self.ground_truth_labels = np.array(ground_truth_labels)
        self.predicted_colors = predicted_colors
        self.ground_truth_colors = ground_truth_colors
        
        # Get unique labels
        self.unique_predicted = sorted(list(set(predicted_labels)))
        self.unique_ground_truth = sorted(list(set(ground_truth_labels)))
        
        # Create confusion matrix
        self.confusion_mat = confusion_matrix(ground_truth_labels, predicted_labels)
        
        # Use optimal mapping based on confusion matrix
        self.color_mapping = self._calculate_optimal_mapping()
        
    def _calculate_optimal_mapping(self) -> Dict[str, str]:
        """
        Calculate optimal color mapping using Hungarian algorithm (linear_sum_assignment).
        Maps predicted clusters to ground truth colors based on maximum overlap in confusion matrix.
        Fast O(n³) implementation ensuring optimal assignment and no color collisions.
        
        Returns:
            Dictionary mapping predicted cluster labels to ground truth colors
        """
        n_pred = len(self.unique_predicted)
        n_gt = len(self.unique_ground_truth)
        
        # Handle edge cases
        if n_pred == 0 or n_gt == 0:
            print("[ConfusionMatrixColorMapper] No clusters to map")
            return {}
        
        # Create cost matrix for Hungarian algorithm (maximize overlap = minimize negative overlap)
        # Pad matrix to be square if needed
        max_size = max(n_pred, n_gt)
        cost_matrix = np.zeros((max_size, max_size))
        
        # Fill cost matrix with negative overlap values (to maximize overlap)
        for pred_idx in range(n_pred):
            for gt_idx in range(n_gt):
                overlap = self.confusion_mat[gt_idx, pred_idx]
                cost_matrix[pred_idx, gt_idx] = -overlap  # Negative for maximization
        
        # Use Hungarian algorithm for optimal assignment
        pred_indices, gt_indices = linear_sum_assignment(cost_matrix)
        
        # Create mapping from assignment results
        mapping = {}
        print(f"[ConfusionMatrixColorMapper] Hungarian algorithm optimal assignment:")
        
        for pred_idx, gt_idx in zip(pred_indices, gt_indices):
            # Only process valid assignments within our cluster ranges
            if pred_idx < n_pred and gt_idx < n_gt:
                pred_label = self.unique_predicted[pred_idx]
                gt_label = self.unique_ground_truth[gt_idx]
                overlap = self.confusion_mat[gt_idx, pred_idx]
                
                # Assign ground truth color to predicted cluster
                if gt_idx < len(self.ground_truth_colors):
                    gt_color = self.ground_truth_colors[gt_idx]
                    mapping[str(pred_label)] = gt_color
                    print(f"  Predicted cluster {pred_label} -> GT cluster {gt_label} (overlap: {overlap}, color: {gt_color})")
                else:
                    # Fallback to predicted color if GT color not available
                    if pred_idx < len(self.predicted_colors):
                        mapping[str(pred_label)] = self.predicted_colors[pred_idx]
                        print(f"  Predicted cluster {pred_label} -> fallback predicted color (overlap: {overlap})")
        
        # Handle any unmapped predicted clusters (shouldn't happen with Hungarian algorithm)
        for pred_idx, pred_label in enumerate(self.unique_predicted):
            if str(pred_label) not in mapping:
                if pred_idx < len(self.predicted_colors):
                    mapping[str(pred_label)] = self.predicted_colors[pred_idx]
                    print(f"  Unmapped predicted cluster {pred_label} -> original predicted color")
        
        print(f"[ConfusionMatrixColorMapper] Optimal mapping completed: {len(mapping)} clusters mapped")
        return mapping
    
    def _keep_predicted_colors_unchanged(self) -> Dict[str, str]:
        """
        Keep predicted cluster colors unchanged - they are the source of truth.
        
        Returns:
            Dictionary mapping predicted cluster labels to their original predicted colors
        """
        mapping = {}
        for pred_idx, pred_label in enumerate(self.unique_predicted):
            if pred_idx < len(self.predicted_colors):
                mapping[str(pred_label)] = self.predicted_colors[pred_idx]
                print(f"[ConfusionMatrixColorMapper] Keeping predicted cluster {pred_label} -> original color {self.predicted_colors[pred_idx]}")
        
        return mapping
    
    def get_mapped_predicted_colors(self) -> List[str]:
        """
        Get the list of colors for predicted clusters mapped to ground truth colors.
        
        Returns:
            List of colors for each data point based on predicted clusters but using GT colors
        """
        mapped_colors = []
        for label in self.predicted_labels:
            mapped_color = self.color_mapping.get(str(label), '#cccccc')
            mapped_colors.append(mapped_color)
        return mapped_colors
    
    def get_mapped_color_map(self) -> Dict[str, str]:
        """
        Get the color mapping dictionary for predicted clusters (unchanged).
        
        Returns:
            Dictionary mapping predicted cluster labels to their original colors
        """
        return self.color_mapping
    
    def get_ground_truth_color_map(self) -> Dict[str, str]:
        """
        Get the adjusted ground truth color mapping.
        
        Returns:
            Dictionary mapping ground truth cluster labels to adjusted colors
        """
        return self.get_adjusted_ground_truth_colors()
    
    def get_mapping_quality_metrics(self) -> Dict[str, float]:
        """
        Calculate quality metrics for the color mapping.
        
        Returns:
            Dictionary with mapping quality metrics
        """
        # Calculate total overlap for each mapping
        total_points = len(self.predicted_labels)
        correctly_mapped_points = 0
        
        for pred_idx, pred_label in enumerate(self.unique_predicted):
            # Find ground truth cluster this predicted cluster is mapped to
            mapped_gt_color = self.color_mapping.get(str(pred_label))
            
            # Find which ground truth cluster has this color
            mapped_gt_idx = None
            for gt_idx, gt_color in enumerate(self.ground_truth_colors):
                if gt_color == mapped_gt_color:
                    mapped_gt_idx = gt_idx
                    break
            
            if mapped_gt_idx is not None:
                # Count points that are correctly mapped
                overlap = self.confusion_mat[mapped_gt_idx, pred_idx]
                correctly_mapped_points += overlap
        
        mapping_accuracy = correctly_mapped_points / total_points if total_points > 0 else 0.0
        
        # Calculate cluster-level mapping quality
        cluster_mapping_scores = []
        for pred_idx, pred_label in enumerate(self.unique_predicted):
            pred_col = self.confusion_mat[:, pred_idx]
            max_overlap = np.max(pred_col)
            total_pred_points = np.sum(pred_col)
            
            if total_pred_points > 0:
                cluster_purity = max_overlap / total_pred_points
                cluster_mapping_scores.append(cluster_purity)
        
        avg_cluster_purity = np.mean(cluster_mapping_scores) if cluster_mapping_scores else 0.0
        
        return {
            'mapping_accuracy': float(mapping_accuracy),
            'average_cluster_purity': float(avg_cluster_purity),
            'num_predicted_clusters': len(self.unique_predicted),
            'num_ground_truth_clusters': len(self.unique_ground_truth),
            'total_points': total_points
        }
    
    def print_mapping_summary(self):
        """Print a summary of the color mapping."""
        print("\n[ConfusionMatrixColorMapper] Color Mapping Summary:")
        print("=" * 60)
        
        for pred_label, gt_color in self.color_mapping.items():
            print(f"Predicted Cluster {pred_label} -> Ground Truth Color {gt_color}")
        
        metrics = self.get_mapping_quality_metrics()
        print(f"\nMapping Quality Metrics:")
        print(f"  Mapping Accuracy: {metrics['mapping_accuracy']:.3f}")
        print(f"  Average Cluster Purity: {metrics['average_cluster_purity']:.3f}")
        print(f"  Predicted Clusters: {metrics['num_predicted_clusters']}")
        print(f"  Ground Truth Clusters: {metrics['num_ground_truth_clusters']}")
        print("=" * 60)

def apply_confusion_matrix_color_mapping(
    predicted_labels: List, 
    ground_truth_labels: List,
    predicted_color_map: Dict[str, str],
    ground_truth_color_map: Dict[str, str]
) -> Tuple[List[str], Dict[str, str], Dict[str, float]]:
    """
    Apply confusion matrix-based color mapping to align predicted and ground truth colors.
    
    Args:
        predicted_labels: List of predicted cluster labels
        ground_truth_labels: List of ground truth cluster labels
        predicted_color_map: Original color map for predicted clusters
        ground_truth_color_map: Color map for ground truth clusters
        
    Returns:
        Tuple of (mapped_colors_list, mapped_color_map, quality_metrics)
    """
    try:
        # Convert color maps to lists in label order
        unique_predicted = sorted(list(set(predicted_labels)))
        unique_ground_truth = sorted(list(set(ground_truth_labels)))
        
        predicted_colors = [predicted_color_map.get(str(label), '#cccccc') for label in unique_predicted]
        ground_truth_colors = [ground_truth_color_map.get(str(label), '#cccccc') for label in unique_ground_truth]
        
        # Create color mapper
        mapper = ConfusionMatrixColorMapper(
            predicted_labels=predicted_labels,
            ground_truth_labels=ground_truth_labels,
            predicted_colors=predicted_colors,
            ground_truth_colors=ground_truth_colors
        )
        
        # Get mapped results
        mapped_colors = mapper.get_mapped_predicted_colors()
        mapped_color_map = mapper.get_mapped_color_map()
        quality_metrics = mapper.get_mapping_quality_metrics()
        
        # Print summary for debugging
        mapper.print_mapping_summary()
        
        return mapped_colors, mapped_color_map, quality_metrics
        
    except Exception as e:
        print(f"[ConfusionMatrixColorMapper] Error in color mapping: {e}")
        # Fallback to original colors
        original_colors = [predicted_color_map.get(str(label), '#cccccc') for label in predicted_labels]
        return original_colors, predicted_color_map, {'error': str(e)}