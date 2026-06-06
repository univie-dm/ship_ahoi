import numpy as np
from typing import Any, Dict, List


def analyze_clustering_insights(cluster_data, tree_data, selected_features, feature_names, analysis_options):
    try:
        points = np.array(cluster_data.get('points', []))
        labels = np.array(cluster_data.get('labels', []))
        original_points = cluster_data.get('original_points')
        if len(points) == 0 or len(labels) == 0:
            return {"error": "No clustering data available"}
        analysis_points = np.array(original_points) if original_points else points
        results: Dict[str, Any] = {}

        if analysis_options.get('featureImportance', False):
            cluster_summary = []
            unique_labels = np.unique(labels)
            for label in unique_labels:
                cluster_mask = labels == label
                cluster_points = analysis_points[cluster_mask]
                cluster_size = np.sum(cluster_mask)
                centroid = np.mean(cluster_points, axis=0)
                distances = np.linalg.norm(cluster_points - centroid, axis=1)
                compactness = np.mean(distances)
                other_centroids = []
                for other_label in unique_labels:
                    if other_label != label:
                        other_mask = labels == other_label
                        other_centroid = np.mean(analysis_points[other_mask], axis=0)
                        other_centroids.append(other_centroid)
                if other_centroids:
                    separations = [np.linalg.norm(centroid - other_centroid) for other_centroid in other_centroids]
                    separation = np.mean(separations)
                else:
                    separation = 0.0
                cluster_summary.append({
                    'id': int(label),
                    'size': int(cluster_size),
                    'compactness': float(compactness),
                    'separation': float(separation),
                    'centroid': centroid.tolist() if hasattr(centroid, 'tolist') else list(centroid)
                })
            results['cluster_summary'] = cluster_summary

        if analysis_options.get('clusterStats', False):
            unique_labels = np.unique(labels)
            stats = {
                'num_clusters': int(len(unique_labels)),
                'cluster_sizes': {int(label): int(np.sum(labels == label)) for label in unique_labels}
            }
            results['cluster_stats'] = stats

        if analysis_options.get('distribution', False):
            distributions = []
            unique_labels = np.unique(labels)
            for label in unique_labels:
                cluster_mask = labels == label
                cluster_points = analysis_points[cluster_mask]
                mean = np.mean(cluster_points, axis=0)
                std = np.std(cluster_points, axis=0)
                distributions.append({
                    'cluster': int(label),
                    'mean': mean.tolist() if hasattr(mean, 'tolist') else list(mean),
                    'std': std.tolist() if hasattr(std, 'tolist') else list(std)
                })
            results['feature_distributions'] = distributions

        return results
    except Exception as e:
        return {"error": str(e)}


def analyze_dataset_insights(dataset, data, selected_features, feature_names, analysis_type, options):
    try:
        data_arr = np.array(data) if data is not None else None
        if data_arr is None or data_arr.size == 0:
            return {"error": "No dataset provided"}
        stats: Dict[str, Any] = {
            'num_samples': int(data_arr.shape[0]),
            'num_features': int(data_arr.shape[1]),
            'feature_means': np.mean(data_arr, axis=0).tolist(),
            'feature_stds': np.std(data_arr, axis=0).tolist(),
        }
        return {'dataset': dataset, 'stats': stats, 'analysis_type': analysis_type}
    except Exception as e:
        return {"error": str(e)}


def analyze_cluster_summary(cluster_data, selected_features, feature_names, options):
    try:
        points = np.array(cluster_data.get('points', []))
        labels = np.array(cluster_data.get('labels', []))
        if len(points) == 0 or len(labels) == 0:
            return {"error": "No clustering data available"}
        unique_labels = np.unique(labels)
        summary = []
        for label in unique_labels:
            mask = labels == label
            cluster_points = points[mask]
            centroid = np.mean(cluster_points, axis=0)
            summary.append({
                'cluster': int(label),
                'size': int(np.sum(mask)),
                'centroid': centroid.tolist() if hasattr(centroid, 'tolist') else list(centroid)
            })
        return {'summary': summary}
    except Exception as e:
        return {"error": str(e)}


def analyze_feature_importance(cluster_data, selected_features, feature_names, options):
    try:
        labels = np.array(cluster_data.get('labels', []))
        points = np.array(cluster_data.get('points', []))
        if points.size == 0 or labels.size == 0:
            return {"error": "No data for importance"}
        unique_labels = np.unique(labels)
        num_features = points.shape[1]
        importance_scores: List[Dict[str, Any]] = []
        for feature_idx in range(num_features):
            feature_values = points[:, feature_idx]
            overall_mean = np.mean(feature_values)
            between_variance = 0.0
            within_variance = 0.0
            for label in unique_labels:
                cluster_mask = labels == label
                cluster_values = feature_values[cluster_mask]
                if len(cluster_values) == 0:
                    continue
                cluster_mean = np.mean(cluster_values)
                cluster_size = len(cluster_values)
                between_variance += cluster_size * (cluster_mean - overall_mean) ** 2
                within_variance += np.sum((cluster_values - cluster_mean) ** 2)
            between_variance /= len(labels)
            within_variance /= len(labels)
            if within_variance > 1e-8:
                importance_score = between_variance / within_variance
            else:
                importance_score = between_variance
            normalized_score = min(importance_score / (importance_score + 1), 1.0)
            feature_name = feature_names[feature_idx] if feature_idx < len(feature_names) else f"Feature {feature_idx}"
            importance_scores.append({
                'feature': feature_name,
                'score': float(normalized_score),
                'index': feature_idx,
                'raw_score': float(importance_score),
                'between_variance': float(between_variance),
                'within_variance': float(within_variance)
            })
        importance_scores.sort(key=lambda x: x['score'], reverse=True)
        return {
            'feature_importance': importance_scores,
            'method': 'variance_ratio',
            'num_features': num_features,
            'num_clusters': len(unique_labels),
            'analysis_method': 'backend'
        }
    except Exception as e:
        return {"error": str(e)}


def analyze_feature_statistics(data, selected_features, feature_names, options):
    try:
        X = np.array(data)
        if X.size == 0:
            return {"error": "No data for statistics"}
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0)
        mins = np.min(X, axis=0)
        maxs = np.max(X, axis=0)
        rows = []
        for i in range(X.shape[1]):
            rows.append({
                'feature': feature_names[i] if i < len(feature_names) else f'Feature {i}',
                'mean': float(means[i]),
                'std': float(stds[i]),
                'min': float(mins[i]),
                'max': float(maxs[i])
            })
        return {'statistics': rows, 'count': X.shape[0]}
    except Exception as e:
        return {"error": str(e)}


def analyze_correlation_matrix(data, selected_features, feature_names, options):
    try:
        X = np.array(data)
        if X.size == 0:
            return {"error": "No data for correlation"}
        # Compute Pearson correlation matrix
        corr = np.corrcoef(X, rowvar=False)
        return {
            'correlation_matrix': corr.tolist(),
            'features': feature_names[: corr.shape[0]]
        }
    except Exception as e:
        return {"error": str(e)}

