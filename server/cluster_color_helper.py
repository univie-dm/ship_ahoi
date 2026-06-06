import json
import sys
import time
import os
from .confusion_matrix_color_mapper import apply_confusion_matrix_color_mapping


def _safe_json_parse(json_str: str):
    """
    Safely parse JSON string, handling deep nesting that would cause RecursionError.
    """
    if not json_str:
        return None
    
    original_limit = sys.getrecursionlimit()
    try:
        # Try standard JSON parsing with increased recursion limit
        sys.setrecursionlimit(max(10000, original_limit))
        return json.loads(json_str)
    except RecursionError:
        # Fall back to iterative parser from clustering_service
        try:
            from .clustering_service import ClusteringService
            return ClusteringService._iterative_json_parse(json_str)
        except Exception as e:
            print(f"[ClusterColorHelper] JSON parsing failed: {e}")
            raise
    finally:
        sys.setrecursionlimit(original_limit)


# Load pre-generated color palette for fast performance
def load_pregenerated_palette():
    """Load pre-generated color palette from JSON file."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Try to load research-based palette first (preferred)
        research_palette_file = os.path.join(script_dir, "research_based_color_palette.json")
        if os.path.exists(research_palette_file):
            with open(research_palette_file, 'r') as f:
                color_data = json.load(f)
            print(f"[ClusterColorHelper] Loading research-based palette: {color_data['metadata']['generation_method']}")
            return color_data['colors'], color_data['metadata']
        
    except Exception as e:
        print(f"Warning: Could not load pre-generated palette: {e}")
        return None, None

# Try to load distinctipy as fallback
try:
    import distinctipy
    DISTINCTIPY_AVAILABLE = True
except ImportError:
    DISTINCTIPY_AVAILABLE = False

class ClusterColorHelper:
    """
    Helper for assigning consistent colors to clusters and tree nodes.
    - Assigns a color to each cluster label (for scatter plot).
    - Assigns a color to each leaf node in the tree (by label or id).
    - Provides color lookup for both scatter and tree visualizations.
    - Directly assigns a color property to each node in a tree (advanced JSON tree).
    """
    def __init__(self, labels=None, tree=None, palette=None, ground_truth_labels=None, outlier_style='prominent'):
        # Load high-quality colors quickly from pre-generated palette
        color_loading_start = time.time()
        
        if palette is None:
            # Try to load pre-generated palette first (fastest)
            print("[ClusterColorHelper] Loading pre-generated color palette...")
            palette, metadata = load_pregenerated_palette()
            
            if palette:
                load_time = time.time() - color_loading_start
                print(f"[ClusterColorHelper] Loaded {len(palette)} pre-generated colors in {load_time:.4f} seconds")
                # Reduced logging - removed detailed metadata output
            else:
                # Fallback to distinctipy if pre-generated palette fails
                if DISTINCTIPY_AVAILABLE:
                    print("[ClusterColorHelper] Using distinctipy fallback...")
                    try:
                        colors_rgb = distinctipy.get_colors(
                            n_colors=100,  # Reduced for speed
                            pastel_factor=0.3,
                            exclude_colors=[(1.0, 1.0, 1.0), (0.8, 0.8, 0.8), (0.5, 0.5, 0.5), (0.0, 0.0, 0.0)]
                        )
                        palette = [f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}" for r, g, b in colors_rgb]
                        print(f"[ClusterColorHelper] Generated {len(palette)} colors with distinctipy")
                    except Exception as e:
                        print(f"[ClusterColorHelper] Distinctipy failed: {e}")
                        palette = None
                
                # Final fallback to built-in scientific palette
                if not palette:
                    print("[ClusterColorHelper] Using built-in scientific palette...")
                    # Scientific color palette based on research and accessibility standards
                    palette = [
                        # Paul Tol's bright colors (research-backed, colorblind-friendly)
                        '#4477AA', '#EE6677', '#228833', '#CCBB44', '#66CCEE',
                        '#AA3377', '#CC6677', '#332288', '#DDCC77', '#117733',
                        
                        # High-contrast primary colors for good visibility
                        '#e60049', '#0bb4ff', '#50e991', '#e6d800', '#9b19f5',
                        '#ffa300', '#dc0ab4', '#b3d4ff', '#00bfa0',
                        
                        # IBM Carbon Design colors (professional, accessible)
                        '#6929c4', '#1192e8', '#005d5d', '#9f1853', '#fa4d56',
                        '#570408', '#198038', '#002d9c', '#ee538b', '#b28600',
                        
                        # Extended matplotlib improved colors
                        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                        '#8c564b', '#e377c2', '#bcbd22', '#17becf',
                        
                        # Additional scientific colors for large datasets
                        '#009d9a', '#012749', '#8a3800', '#a56eff', '#be95ff',
                        '#82cfff', '#42be65', '#ffb000', '#ff8389', '#ba4e00',
                        
                        # Viridis-inspired discrete colors (perceptually uniform)
                        '#440154', '#482878', '#3e4989', '#31688e', '#26828e',
                        '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725'
                    ]
                    print(f"[ClusterColorHelper] Using built-in scientific palette with {len(palette)} colors")
                
        self.palette = palette
        
        color_loading_time = time.time() - color_loading_start
        print(f"[ClusterColorHelper] Total color loading took {color_loading_time:.4f} seconds")
        
        # Store ground truth labels if provided
        self.ground_truth_labels = [str(l) for l in ground_truth_labels] if ground_truth_labels is not None else None
        
        # Store final cluster assignments for each data point (e.g., from ship.fit_predict())
        # These are converted to strings for consistent keying.
        self.point_final_labels = [str(l) for l in labels] if labels is not None else []
        
        # Store original predicted labels for confusion matrix mapping
        self.original_predicted_labels = labels if labels is not None else []

        # Determine unique final cluster labels to build the color map
        unique_final_labels_for_map = []
        raw_unique_labels = []
        if self.point_final_labels: # Use point_final_labels if available
            raw_unique_labels = self._unique_in_order(self.point_final_labels)
            
            # Exclude outlier labels (-1) from regular color mapping to prevent index shifting
            # Outliers will be handled separately to ensure consistent colors for regular clusters
            non_outlier_labels = [label for label in raw_unique_labels if str(label) != '-1']
            
            # Sort them to ensure consistent color mapping across runs
            try:
                # Attempt to sort numerically if they are string numbers, then lexicographically
                # Original working logic: handles numeric strings properly without tuple sorting
                unique_final_labels_for_map = sorted(non_outlier_labels, key=lambda x: int(x) if x.isdigit() and not x.startswith('0') and len(x) > 1 else (int(x) if x.isdigit() else x) )
            except (ValueError, TypeError): 
                # Fallback to simple lexicographical sort if mixed types or other parsing issues
                unique_final_labels_for_map = sorted(non_outlier_labels, key=str)
        
        # Create color mapping for regular clusters only (outliers handled separately)
        self.label_to_color = {
            label: self.palette[i % len(self.palette)]
            for i, label in enumerate(unique_final_labels_for_map)
        }
        
        # Special handling for outliers (label -1) - color based on style setting for scatter plot
        self.outlier_style = outlier_style
        # Check if outliers exist in the original raw labels (not the filtered map)
        if self.point_final_labels and '-1' in raw_unique_labels:
            self.label_to_color['-1'] = '#000000' if outlier_style == 'subtle' else '#FF0000'  # Black for subtle, red for prominent
        
        # Create ground truth color mapping if ground truth labels are provided
        self.ground_truth_label_to_color = {}
        if self.ground_truth_labels:
            unique_gt_labels = self._unique_in_order(self.ground_truth_labels)
            try:
                # Sort ground truth labels consistently
                unique_gt_labels = sorted(unique_gt_labels, key=lambda x: int(x) if x.isdigit() and not x.startswith('0') and len(x) > 1 else (int(x) if x.isdigit() else x))
            except (ValueError, TypeError):
                unique_gt_labels = sorted(unique_gt_labels, key=str)
            
            # Use same palette starting from index 0 to match regular clustering colors
            self.ground_truth_label_to_color = {
                label: self.palette[i % len(self.palette)]
                for i, label in enumerate(unique_gt_labels)
            }
            
            # Apply confusion matrix color mapping if both predicted and ground truth labels are available
            if self.point_final_labels and self.ground_truth_labels:
                try:
                    print("[ClusterColorHelper] Applying confusion matrix color mapping...")
                    mapped_colors, mapped_color_map, quality_metrics = apply_confusion_matrix_color_mapping(
                        predicted_labels=self.original_predicted_labels,
                        ground_truth_labels=ground_truth_labels,
                        predicted_color_map=self.label_to_color,
                        ground_truth_color_map=self.ground_truth_label_to_color
                    )
                    
                    # Update the predicted color mapping to use ground truth colors
                    self.label_to_color = mapped_color_map
                    self.confusion_matrix_quality = quality_metrics
                    
                    # Ensure outlier color is preserved after confusion matrix mapping
                    if '-1' in raw_unique_labels:
                        self.label_to_color['-1'] = '#000000' if outlier_style == 'subtle' else '#FF0000'
                    
                    print(f"[ClusterColorHelper] Confusion matrix mapping applied successfully!")
                    print(f"[ClusterColorHelper] Mapping accuracy: {quality_metrics.get('mapping_accuracy', 0):.3f}")
                    
                except Exception as e:
                    print(f"[ClusterColorHelper] Warning: Confusion matrix color mapping failed: {e}")
                    self.confusion_matrix_quality = {'error': str(e)}
            else:
                self.confusion_matrix_quality = None
        
        # Validation: ensure color mapping was created correctly
        if unique_final_labels_for_map and not self.label_to_color:
            print(f"WARNING: ClusterColorHelper - unique_final_labels_for_map has {len(unique_final_labels_for_map)} labels but label_to_color is empty!")
        
        # Reduced debug logging - only show for very small datasets or when there are issues
        if self.point_final_labels and len(self.point_final_labels) < 100:  # Only for very small datasets
            print(f"DEBUG ClusterColorHelper init: point_final_labels (first 10): {self.point_final_labels[:10]}")
        
        # Additional validation for proper color mapping
        if self.point_final_labels and self.label_to_color:
            # Check that all labels in point_final_labels have corresponding colors
            missing_colors = []
            for label in self.point_final_labels[:20]:  # Check first 20 labels
                if str(label) not in self.label_to_color:
                    missing_colors.append(label)
            if missing_colors:
                print(f"WARNING: ClusterColorHelper - Some labels missing from color mapping: {missing_colors[:5]}{'...' if len(missing_colors) > 5 else ''}")
        

        if tree is not None:
            if not self.label_to_color:
                 print("Warning: ClusterColorHelper.label_to_color is empty. " +
                       "This can happen if 'labels' (final cluster assignments) were not provided or were empty. " +
                       "Tree colors will be default.")
            self.assign_colors_to_tree(tree)

    def _unique_in_order(self, arr):
        seen = set()
        result = []
        for x in arr:
            s = str(x)
            if s not in seen:
                seen.add(s)
                result.append(s)
        return result

    def _extract_labels_from_tree(self, tree):
        # Handle string JSON with safe parsing for deep trees
        if isinstance(tree, str):
            try:
                tree = _safe_json_parse(tree)
            except (json.JSONDecodeError, RecursionError) as e:
                print(f"Failed to parse tree JSON: {e}")
                return []
                
        # Recursively collect all leaf labels (or ids if no label)
        leaves = []
        def collect_leaves(node):
            if not node.get('children'):
                leaves.append(str(node.get('label', node.get('id'))))
            else:
                for child in node['children']:
                    collect_leaves(child)
        
        if tree and 'root' in tree:
            collect_leaves(tree['root'])
        return self._unique_in_order(leaves)

    def assign_colors_to_tree(self, tree):
        start_time_total = time.time()
        if isinstance(tree, str):
            try:
                tree = _safe_json_parse(tree)
            except (json.JSONDecodeError, RecursionError) as e:
                print(f"Failed to parse tree JSON for color assignment: {e}")
                print(f"[ClusterColorHelper] assign_colors_to_tree (JSON decode error) took {time.time() - start_time_total:.4f} seconds")
                return

        default_color = '#cccccc'

        if not self.label_to_color or not self.point_final_labels:
            print("ClusterColorHelper.assign_colors_to_tree: " +
                  "Missing label_to_color map or point_final_labels. Assigning default colors to all tree nodes.")
            
            def assign_default_recursive(node_to_color):
                node_to_color['color'] = default_color
                for child_node in node_to_color.get('children', []):
                    assign_default_recursive(child_node)
            if tree and 'root' in tree:
                assign_default_recursive(tree['root'])
            print(f"[ClusterColorHelper] assign_colors_to_tree (default colors) took {time.time() - start_time_total:.4f} seconds")
            return

        # Recursive helper function
        # Returns a dictionary: {final_cluster_label: count_of_points_in_subtree}
        def assign_and_get_subtree_cluster_counts(node):
            nodes_processed[0] += 1
            # Removed progress logging to reduce noise
            is_leaf = not node.get('children')

            if is_leaf:
                current_cluster_counts = {}
                
                # Handle different ways to identify point indices in leaf nodes
                # Priority: pointIndices > data_indices > single id/label
                point_indices = None
                if 'pointIndices' in node and isinstance(node['pointIndices'], list):
                    point_indices = node['pointIndices']
                elif 'data_indices' in node and isinstance(node['data_indices'], list):
                    point_indices = node['data_indices']
                elif node.get('id') is not None and isinstance(node.get('id'), int):
                    point_indices = [node['id']]
                elif node.get('label') is not None and isinstance(node.get('label'), int):
                    point_indices = [node['label']]
                
                # Debug logging for small trees (removed for performance)
                # if len(self.point_final_labels) < 100:  # Only for small datasets
                #     print(f"DEBUG leaf node processing: node_id={node.get('id')}, has_pointIndices={bool(node.get('pointIndices'))}, has_data_indices={bool(node.get('data_indices'))}, point_indices={point_indices}")
                #     if point_indices:
                #         print(f"DEBUG leaf node: point_indices={point_indices}, indices_type={type(point_indices[0]) if point_indices else None}")
                
                # Process point indices to determine colors
                if point_indices and isinstance(point_indices, list):
                    # Collect cluster labels for all points in this leaf - optimized version
                    labels_in_leaf = []
                    point_final_labels = self.point_final_labels  # Cache for performance
                    max_index = len(point_final_labels) - 1
                    
                    for point_index in point_indices:
                        # Optimized type checking and conversion
                        if isinstance(point_index, str):
                            if point_index.isdigit():
                                point_index = int(point_index)
                            else:
                                continue
                        
                        if isinstance(point_index, int) and 0 <= point_index <= max_index:
                            labels_in_leaf.append(point_final_labels[point_index])
                    
                    # Count occurrences of each label - optimized version
                    label_to_color = self.label_to_color  # Cache for performance
                    for label in labels_in_leaf:
                        str_label = str(label)  # Ensure label is string
                        if str_label in label_to_color:
                            current_cluster_counts[str_label] = current_cluster_counts.get(str_label, 0) + 1
                    
                    # Store the total point count for hover functionality
                    total_points_in_leaf = len(labels_in_leaf)
                    node['point_count'] = total_points_in_leaf
                    
                    # Assign color based on dominant label or mixed if multiple
                    if len(current_cluster_counts) == 1:
                        dominant_label = list(current_cluster_counts.keys())[0]
                        # Special handling for outliers (label -1) - always black in tree
                        if str(dominant_label) == '-1':
                            node['color'] = '#000000'  # Always black for outlier leaf nodes in tree
                        else:
                            node['color'] = self.label_to_color.get(str(dominant_label), default_color)
                    elif len(current_cluster_counts) > 1:
                        node['color'] = '#BDBDBD'  # Mixed colors
                        # Add color composition for mixed leaf nodes
                        total_points = sum(current_cluster_counts.values())
                        node['color_composition'] = [
                            {
                                'label': str(label),
                                'color': self.label_to_color.get(str(label), default_color),
                                'count': count,
                                'proportion': count / total_points
                            }
                            for label, count in sorted(current_cluster_counts.items(), key=lambda x: str(x[0]))
                        ]
                    else:
                        node['color'] = default_color
                else:
                    # Fallback for single point identification
                    point_index = node.get('id') 
                    
                    # Handle both integer and string IDs (due to normalization)
                    if point_index is not None:
                        try:
                            # Convert to int if it's a string representation of an integer
                            if isinstance(point_index, str) and point_index.isdigit():
                                point_index = int(point_index)
                            
                            if isinstance(point_index, int) and 0 <= point_index < len(self.point_final_labels):
                                final_cluster_label_for_point = self.point_final_labels[point_index]
                                # Special handling for outliers (label -1) - always black in tree
                                if str(final_cluster_label_for_point) == '-1':
                                    node['color'] = '#000000'  # Always black for outlier leaf nodes in tree
                                else:
                                    node['color'] = self.label_to_color.get(str(final_cluster_label_for_point), default_color)
                                # Store point count for hover functionality
                                node['point_count'] = 1
                                # Only count if it's a recognized final cluster with a color mapping
                                str_final_label = str(final_cluster_label_for_point)  # Ensure string
                                if str_final_label in self.label_to_color:
                                    current_cluster_counts[str_final_label] = 1
                                
                                # Debug logging for small trees
                                if len(self.point_final_labels) < 100:
                                    print(f"DEBUG single point: node_id={node.get('id')}, point_index={point_index}, final_label={final_cluster_label_for_point}, color={node.get('color')}")
                            else:
                                node['color'] = default_color
                                node['point_count'] = 0
                                if len(self.point_final_labels) < 100:
                                    print(f"DEBUG single point FAILED: node_id={node.get('id')}, point_index={point_index}, valid_range=0-{len(self.point_final_labels)-1}")
                        except (ValueError, TypeError):
                            node['color'] = default_color
                            node['point_count'] = 0
                            if len(self.point_final_labels) < 100:
                                print(f"DEBUG single point CONVERSION ERROR: node_id={node.get('id')}, point_index={point_index}, type={type(point_index)}")
                    else:
                        node['color'] = default_color
                        node['point_count'] = 0
                
                return current_cluster_counts
            else: # Internal node
                aggregated_subtree_counts = {}
                
                # First, process children to get their point coverage (to avoid double counting)
                child_covered_points = set()
                if node.get('children'):
                    for child in node['children']:
                        child_counts = assign_and_get_subtree_cluster_counts(child)
                        for label, count in child_counts.items():
                            str_label = str(label)  # Ensure label is string
                            aggregated_subtree_counts[str_label] = aggregated_subtree_counts.get(str_label, 0) + count
                        
                        # Track which points are covered by children to avoid double counting - optimized
                        child_point_indices = child.get('pointIndices', child.get('data_indices', []))
                        if isinstance(child_point_indices, list):
                            for idx in child_point_indices:
                                # Optimized type checking and conversion
                                if isinstance(idx, str):
                                    if idx.isdigit():
                                        child_covered_points.add(int(idx))
                                elif isinstance(idx, int):
                                    child_covered_points.add(idx)
                
                # Then, process parent's direct points ONLY if they're not already covered by children
                parent_point_indices = node.get('pointIndices') or node.get('data_indices', [])
                if isinstance(parent_point_indices, list) and parent_point_indices:
                    # Find points in parent that are NOT already covered by children - optimized
                    uncovered_parent_points = []
                    for point_index in parent_point_indices:
                        # Optimized type checking and conversion
                        if isinstance(point_index, str):
                            if point_index.isdigit():
                                point_index = int(point_index)
                            else:
                                continue
                        
                        if isinstance(point_index, int) and point_index not in child_covered_points:
                            uncovered_parent_points.append(point_index)
                    
                    # Only count uncovered points to avoid double counting - optimized
                    point_final_labels = self.point_final_labels  # Cache for performance
                    max_index = len(point_final_labels) - 1
                    label_to_color = self.label_to_color  # Cache for performance
                    
                    for point_index in uncovered_parent_points:
                        if 0 <= point_index <= max_index:
                            label = point_final_labels[point_index]
                            str_label = str(label)  # Ensure label is string
                            if str_label in label_to_color:
                                aggregated_subtree_counts[str_label] = aggregated_subtree_counts.get(str_label, 0) + 1
                    
                    # Debug logging for double-counting prevention (removed for performance)
                    # if len(self.point_final_labels) < 100:
                    #     total_parent_points = len(parent_point_indices)
                    #     covered_by_children = len(child_covered_points & set(parent_point_indices))
                    #     uncovered_count = len(uncovered_parent_points)
                    #     print(f"DEBUG internal node anti-double-count: node_id={node.get('id')}, parent_points={total_parent_points}, covered_by_children={covered_by_children}, uncovered={uncovered_count}")
                
                # Store the raw counts, could be useful for other purposes or detailed hover.
                if aggregated_subtree_counts:
                    node['subtree_cluster_counts'] = aggregated_subtree_counts
                
                # Calculate total point count for this subtree
                total_points_in_subtree = sum(aggregated_subtree_counts.values())
                node['point_count'] = total_points_in_subtree
                
                # Validation: Ensure point count doesn't exceed total dataset size
                if total_points_in_subtree > len(self.point_final_labels):
                    print(f"WARNING: Node {node.get('id')} has {total_points_in_subtree} points but dataset only has {len(self.point_final_labels)} points!")
                    print(f"  Node subtree_counts: {aggregated_subtree_counts}")
                    # Cap the point count to dataset size to prevent invalid displays
                    node['point_count'] = len(self.point_final_labels)
                
                # Debug logging for small trees (reduced verbosity)
                if len(self.point_final_labels) < 50:
                    print(f"DEBUG internal node: node_id={node.get('id')}, point_count={total_points_in_subtree}")

                # Handle coloring based on cluster composition
                if not aggregated_subtree_counts: 
                    node['color'] = default_color
                elif len(aggregated_subtree_counts) == 1: 
                    unified_final_cluster = list(aggregated_subtree_counts.keys())[0]
                    node['color'] = self.label_to_color.get(str(unified_final_cluster), default_color)
                else: # Multiple final cluster types in descendants
                    # For summary nodes, use a slightly different color to distinguish them
                    is_summary = (node.get('_is_summary') or 
                                'summary' in str(node.get('id', '')) or 
                                node.get('_original_child_count', 0) > 0)
                    
                    if is_summary:
                        node['color'] = '#A0A0A0'  # Lighter grey for summary nodes
                    else:
                        node['color'] = '#BDBDBD'  # Regular grey for mixed internal nodes

                    # Add detailed color composition for potential advanced rendering or hover info
                    total_count_in_subtree = sum(aggregated_subtree_counts.values())
                    if total_count_in_subtree > 0:
                        # Sort items by cluster label for consistent order in the composition list
                        # Attempt to sort numerically if labels are digits, otherwise lexicographically
                        sorted_counts = []
                        try:
                            # Ensure labels are strings for isdigit() and consistent sorting
                            # Use tuple sorting to avoid mixed type comparison
                            sorted_counts = sorted(
                                aggregated_subtree_counts.items(),
                                key=lambda item: (0, int(str(item[0]))) if str(item[0]).isdigit() else (1, str(item[0]))
                            )
                        except (ValueError, TypeError): # Fallback if conversion to int fails for unforeseen reasons
                            sorted_counts = sorted(aggregated_subtree_counts.items(), key=lambda item: str(item[0]))

                        node['color_composition'] = [
                            {
                                'label': str(label), # Ensure label is string
                                'color': self.label_to_color.get(str(label), default_color),
                                'count': count,
                                'proportion': count / total_count_in_subtree
                            }
                            for label, count in sorted_counts
                        ]
                
                return aggregated_subtree_counts

        nodes_processed = [0]  # Use list to make it mutable in nested function
        
        if tree and 'root' in tree:
            print(f"[ClusterColorHelper] Starting color assignment for tree with {len(self.point_final_labels)} data points")
            assign_and_get_subtree_cluster_counts(tree['root'])
            print(f"[ClusterColorHelper] Finished processing {nodes_processed[0]} total nodes")
            
            # Final validation for point count integrity
            if len(self.point_final_labels) <= 1000:  # Only for reasonably sized datasets
                self._validate_tree_point_counts(tree['root'])
        
        # Reduced timing logging - only show for large trees (>1000 nodes)
        if nodes_processed[0] > 1000:
            print(f"[ClusterColorHelper] Total assign_colors_to_tree took {time.time() - start_time_total:.4f} seconds")

    def _validate_tree_point_counts(self, root):
        """Validate that tree point counts are reasonable and don't exceed dataset bounds."""
        total_dataset_size = len(self.point_final_labels)
        issues_found = 0
        max_node_count = 0
        
        # Traverse tree and check each node
        stack = [root]
        while stack:
            node = stack.pop()
            node_count = node.get('point_count', 0)
            
            if node_count > total_dataset_size:
                issues_found += 1
                if issues_found <= 3:  # Limit output
                    print(f"WARNING: Node {node.get('id')} has invalid point count: {node_count} > {total_dataset_size}")
            
            max_node_count = max(max_node_count, node_count)
            
            # Process children
            if node.get('children'):
                stack.extend(node['children'])
        
        if issues_found == 0:
            print(f"[ClusterColorHelper] Point count validation passed. Max node count: {max_node_count}/{total_dataset_size}")
        else:
            print(f"[ClusterColorHelper] Point count validation found {issues_found} issues. Please check tree structure.")

    def get_color(self, label):
        # Special handling for outliers (label -1) - color based on style setting
        str_label = str(label)
        if str_label == '-1':
            return '#000000' if getattr(self, 'outlier_style', 'prominent') == 'subtle' else '#FF0000'  # Black for subtle, red for prominent
        # Only use grey if label is not in color map
        if str_label in self.label_to_color:
            return self.label_to_color[str_label]
        return '#cccccc'

    def get_color_list_for_labels(self, labels):
        return [self.get_color(label) for label in labels]

    def get_color_for_tree_node(self, node):
        # Use the color property if present, else fallback to label/id lookup
        if 'color' in node:
            return node['color']
        label = node.get('label', node.get('id'))
        return self.get_color(label)
    
    def get_ground_truth_color(self, label):
        """Get color for ground truth label"""
        if not self.ground_truth_label_to_color:
            return '#cccccc'
        str_label = str(label)
        return self.ground_truth_label_to_color.get(str_label, '#cccccc')
    
    def get_ground_truth_color_list(self, labels):
        """Get list of colors for ground truth labels"""
        return [self.get_ground_truth_color(label) for label in labels]
    
    def has_ground_truth(self):
        """Check if ground truth labels are available"""
        return self.ground_truth_labels is not None and len(self.ground_truth_labels) > 0
    
    def add_ground_truth_coloring_to_tree(self, tree):
        """Add ground truth color composition to tree nodes"""
        if not self.has_ground_truth():
            return

        print(f"[ClusterColorHelper] Adding ground truth coloring to tree with {len(self.ground_truth_labels)} labels")
        nodes_processed = [0]

        def add_composition(node):
            nodes_processed[0] += 1
            # Removed progress logging to reduce noise
                
            point_indices = node.get('pointIndices', [])
            if not point_indices:
                # If no pointIndices, try to get from children WITHOUT recursive calls
                if node.get('children'):
                    for child in node['children']:
                        # Just get the point indices, don't recursively process the child yet
                        child_point_indices = child.get('pointIndices', [])
                        point_indices.extend(child_point_indices)
                # Only set pointIndices if it was actually empty and we found some from children
                if point_indices:
                    node['pointIndices'] = point_indices

            if point_indices:
                gt_label_counts = {}
                ground_truth_labels = self.ground_truth_labels  # Cache for performance
                max_index = len(ground_truth_labels) - 1
                
                for point_index in point_indices:
                    if 0 <= point_index <= max_index:
                        gt_label = ground_truth_labels[point_index]
                        gt_label_counts[gt_label] = gt_label_counts.get(gt_label, 0) + 1

                if gt_label_counts:
                    total_points = sum(gt_label_counts.values())
                    node['ground_truth_composition'] = [
                        {
                            'label': str(label),
                            'color': self.get_ground_truth_color(label),
                            'count': count,
                            'proportion': count / total_points
                        }
                        for label, count in sorted(gt_label_counts.items())
                    ]

            # Process children recursively (this is the ONLY recursive call)
            if node.get('children'):
                for child in node['children']:
                    add_composition(child)

        if tree and 'root' in tree:
            add_composition(tree['root'])
            print(f"[ClusterColorHelper] Finished ground truth processing for {nodes_processed[0]} nodes")
    
    def _calculate_cluster_agreement(self, predicted_composition, ground_truth_composition):
        """Calculate agreement score between predicted and ground truth compositions"""
        if not predicted_composition or not ground_truth_composition:
            return 0.0
        
        # Simple agreement based on dominant label matching
        pred_dominant = max(predicted_composition, key=lambda x: x['count'])
        gt_dominant = max(ground_truth_composition, key=lambda x: x['count'])
        
        # Calculate overlap proportion
        total_pred = sum(item['count'] for item in predicted_composition)
        total_gt = sum(item['count'] for item in ground_truth_composition)
        
        if total_pred == 0 or total_gt == 0:
            return 0.0
        
        # Simple agreement: proportion of overlap between dominant clusters
        agreement = min(pred_dominant['proportion'], gt_dominant['proportion'])
        return float(agreement)
    
    def get_confusion_matrix_quality(self):
        """Get confusion matrix color mapping quality metrics"""
        return getattr(self, 'confusion_matrix_quality', None)
