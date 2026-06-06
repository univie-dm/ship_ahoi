/**
 * Shared utility functions for tree data processing and visualization
 */

export interface TreeNode {
  id: string;
  label?: string | number;
  name?: string;
  color?: string;
  color_composition?: Array<{
    label: string;
    color: string;
    count: number;
    proportion: number;
  }>;
  children?: TreeNode[];
  pointIndices?: number[];
  data_indices?: number[];
  _data_indices?: number[];
  _subtree_size?: number;
  x?: number;
  y?: number;
  depth?: number;
  value?: number;
  height?: number;
  _is_summary?: boolean;
  _original_child_count?: number;
}

/**
 * Extracts point indices from a tree node with consistent fallback logic
 * Enhanced to handle depth-cut nodes and server-side point merging
 * @param node - Tree node to extract indices from
 * @returns Array of valid numeric point indices
 */
export function extractPointIndices(node: any): number[] {
  if (!node) return [];

  // Priority order: pointIndices > data_indices > _data_indices > single id/label (only for leaf nodes)
  let indices: any[] = [];

  if (node.pointIndices && Array.isArray(node.pointIndices)) {
    indices = node.pointIndices;
  } else if (node.data_indices && Array.isArray(node.data_indices)) {
    indices = node.data_indices;
  } else if (node._data_indices && Array.isArray(node._data_indices)) {
    // Handle legacy _data_indices field
    indices = node._data_indices;
  } else if ((!node.children || node.children.length === 0) && node.id !== undefined) {
    // Only use id as point index for leaf nodes (handle both string and number ids)
    if (typeof node.id === 'number') {
      indices = [node.id];
    } else if (typeof node.id === 'string' && node.id.match(/^\d+$/)) {
      const numericId = parseInt(node.id);
      if (!isNaN(numericId)) {
        indices = [numericId];
      }
    }
  } else if ((!node.children || node.children.length === 0) && node.label !== undefined) {
    // Only use label as point index for leaf nodes
    const numericLabel = parseInt(String(node.label));
    if (!isNaN(numericLabel)) {
      indices = [numericLabel];
    }
  }

  // Filter and validate indices
  const validIndices = indices
    .filter((idx: any) => typeof idx === 'number' && !isNaN(idx) && idx >= 0)
    .map((idx: any) => Math.floor(idx)); // Ensure integers

  // Debug logging for cut nodes to help diagnose issues
  if (node._was_cut && validIndices.length > 0) {
    console.log(`[TREE-UTILS] Cut node ${node.id} has ${validIndices.length} merged point indices`);
  }

  return validIndices;
}

/**
 * Recursively collects point indices from all descendant nodes
 * @param node - Root node to start collection from
 * @returns Array of all unique point indices from descendants
 */
export function collectAllPointIndices(node: any): number[] {
  if (!node) return [];

  const allIndices: number[] = [];
  const stack = [node];

  while (stack.length > 0) {
    const currentNode = stack.pop();
    if (!currentNode) continue;

    // Get indices from current node
    const nodeIndices = extractPointIndices(currentNode);
    allIndices.push(...nodeIndices);

    // Add children to stack
    if (currentNode.children && Array.isArray(currentNode.children)) {
      stack.push(...currentNode.children);
    }
  }

  // Remove duplicates and sort
  return [...new Set(allIndices)].sort((a, b) => a - b);
}

/**
 * Convert tree data to a standardized format for D3 processing
 * @param treeData - Raw tree data from backend
 * @returns Processed tree node or null if invalid
 */
export function convertTreeToStandardFormat(treeData: any): TreeNode | null {
  if (!treeData) {
    console.warn('[useTreeUtils] convertTreeToStandardFormat called with null/undefined data');
    return null;
  }
  
  // Handle case where tree data is a JSON string
  let parsedTreeData = treeData;
  if (typeof treeData === 'string') {
    console.log('[useTreeUtils] Parsing tree data from JSON string, length:', treeData.length);
    try {
      parsedTreeData = JSON.parse(treeData);
    } catch (e) {
      console.error('[useTreeUtils] Failed to parse tree JSON string:', e);
      return null;
    }
  }
  
  if (!parsedTreeData || !parsedTreeData.root) {
    console.error('[useTreeUtils] Invalid tree structure - missing root:', {
      hasTreeData: !!parsedTreeData,
      hasRoot: !!(parsedTreeData && parsedTreeData.root),
      treeDataKeys: parsedTreeData ? Object.keys(parsedTreeData) : []
    });
    return null;
  }

  console.log('[useTreeUtils] Starting tree conversion:', {
    hasRoot: !!parsedTreeData.root,
    rootKeys: parsedTreeData.root ? Object.keys(parsedTreeData.root) : [],
    rootHasChildren: !!(parsedTreeData.root && parsedTreeData.root.children),
    rootChildrenCount: parsedTreeData.root && parsedTreeData.root.children ? parsedTreeData.root.children.length : 0
  });

  let totalNodesProcessed = 0;
  let leafNodesCount = 0;
  let internalNodesCount = 0;

  function processNode(node: any, depth = 0): TreeNode {
    totalNodesProcessed++;
    
    const processedNode: TreeNode = {
      id: node.id || node.label || `node_${Math.random()}`,
      label: node.label,
      name: node.name,
      color: node.color || '#cccccc',
      color_composition: node.color_composition,
      depth,
      height: node.height,
      _is_summary: node._is_summary,
      _original_child_count: node._original_child_count,
      pointIndices: [],
      value: 1 // Default value for leaf nodes
    };

    // Extract point indices using standardized method
    if (!node.children || node.children.length === 0) {
      // Leaf node
      leafNodesCount++;
      processedNode.pointIndices = extractPointIndices(node);
      
      if (totalNodesProcessed <= 5) { // Log first few leaf nodes for debugging
        console.log(`[useTreeUtils] Leaf node ${processedNode.id} at depth ${depth}:`, {
          pointIndices: processedNode.pointIndices,
          rawPointIndices: node.pointIndices,
          rawDataIndices: node.data_indices,
          nodeId: node.id,
          nodeLabel: node.label
        });
      }
    } else {
      // Internal node - process children first
      internalNodesCount++;
      processedNode.children = node.children.map((child: any) => processNode(child, depth + 1));
      
      // For internal nodes, always collect from children unless it's a summarized node with direct indices
      const directIndices = extractPointIndices(node);
      
      if (directIndices.length > 0 && (node._is_summary || node.pointIndices || node.data_indices)) {
        // Use direct indices only for summarized nodes or nodes that explicitly have pointIndices
        processedNode.pointIndices = directIndices;
      } else {
        // Collect from children for regular internal nodes
        processedNode.pointIndices = (processedNode.children || []).reduce((acc: number[], child: TreeNode) => {
          return acc.concat(child.pointIndices || []);
        }, []);
        
        // Remove duplicates and sort
        processedNode.pointIndices = [...new Set(processedNode.pointIndices)].sort((a, b) => a - b);
      }
      
      // Set value to number of unique descendants
      processedNode.value = processedNode.pointIndices.length || 1;
      
      if (totalNodesProcessed <= 5) { // Log first few internal nodes for debugging
        console.log(`[useTreeUtils] Internal node ${processedNode.id} at depth ${depth}:`, {
          childrenCount: processedNode.children ? processedNode.children.length : 0,
          pointIndicesCount: processedNode.pointIndices.length,
          directIndicesCount: directIndices.length,
          isSummary: node._is_summary
        });
      }
    }

    return processedNode;
  }

  const result = processNode(parsedTreeData.root);
  
  console.log('[useTreeUtils] Tree conversion completed:', {
    totalNodesProcessed,
    leafNodesCount,
    internalNodesCount,
    rootHasChildren: !!(result && result.children),
    rootChildrenCount: result && result.children ? result.children.length : 0,
    rootPointIndicesCount: result ? result.pointIndices.length : 0
  });

  return result;
}

/**
 * Validates that point indices are properly propagated throughout the tree
 * @param node - Tree node to validate
 * @returns True if validation passes
 */
export function validateTreePointIndices(node: TreeNode | null): boolean {
  if (!node) return false;

  const stack = [node];
  let isValid = true;

  while (stack.length > 0 && isValid) {
    const currentNode = stack.pop();
    if (!currentNode) continue;

    // Check that node has point indices
    if (!currentNode.pointIndices || !Array.isArray(currentNode.pointIndices)) {
      console.warn(`Node ${currentNode.id} missing pointIndices`);
      isValid = false;
      break;
    }

    // Check that indices are valid numbers
    if (currentNode.pointIndices.some(idx => typeof idx !== 'number' || isNaN(idx) || idx < 0)) {
      console.warn(`Node ${currentNode.id} has invalid pointIndices:`, currentNode.pointIndices);
      isValid = false;
      break;
    }

    // Add children to stack
    if (currentNode.children && Array.isArray(currentNode.children)) {
      stack.push(...currentNode.children);
    }
  }

  return isValid;
}

/**
 * Calculates the actual number of data points contained in a tree node
 * @param node - Tree node to calculate point count for
 * @returns Number of data points in the node
 */
export function calculateNodePointCount(node: any): number {
  if (!node) return 0;

  // Priority order: _subtree_size > pointIndices.length > direct calculation
  if (typeof node._subtree_size === 'number' && node._subtree_size > 0) {
    return node._subtree_size;
  }

  // Try to get point indices and count them
  const pointIndices = extractPointIndices(node);
  if (pointIndices.length > 0) {
    return pointIndices.length;
  }

  // For internal nodes, collect from all descendants
  if (node.children && Array.isArray(node.children)) {
    const allIndices = collectAllPointIndices(node);
    return allIndices.length;
  }

  // Fallback to 1 for leaf nodes
  return 1;
}

export interface NodeSizingOptions {
  minSize?: number;
  maxSize?: number;
  scaleFactor?: number;
  useDepth?: boolean;
  logScale?: boolean;
}

/**
 * Calculates node size based on actual data point count with intelligent scaling
 * @param node - Tree node to calculate size for
 * @param options - Sizing configuration options
 * @returns Calculated node radius
 */
export function calculateNodeSize(node: any, options: NodeSizingOptions = {}): number {
  const {
    minSize = 4,
    maxSize = 20,
    scaleFactor = 1.0,
    useDepth = false,
    logScale = true
  } = options;

  const pointCount = calculateNodePointCount(node);
  
  // Handle edge cases
  if (pointCount <= 0) return minSize;
  if (pointCount === 1) return minSize + 1;

  let baseSize: number;
  
  if (logScale) {
    // Logarithmic scaling for better visual distribution
    baseSize = Math.log(pointCount + 1) * scaleFactor * 3;
  } else {
    // Linear scaling with square root for moderate growth
    baseSize = Math.sqrt(pointCount) * scaleFactor;
  }

  // Apply depth adjustment if enabled
  if (useDepth && typeof node.depth === 'number') {
    const depthFactor = Math.max(0.5, 1 - (node.depth * 0.1));
    baseSize *= depthFactor;
  }

  // Ensure size is within bounds
  return Math.max(minSize, Math.min(maxSize, baseSize));
}

/**
 * Finds the most specific (smallest) node in the tree that contains a specific point index
 * This ensures only the most precise node is highlighted, not its parents
 * @param tree - Root tree node to search
 * @param pointIndex - The point index to find
 * @returns The smallest node containing the point, or null if not found
 */
export function findDeepestNodeContainingPoint(tree: TreeNode | null, pointIndex: number): TreeNode | null {
  if (!tree || typeof pointIndex !== 'number' || pointIndex < 0) {
    console.log('[TREE-UTILS] Invalid input - tree:', !!tree, 'pointIndex:', pointIndex);
    return null;
  }

  let bestNode: TreeNode | null = null;
  let minPointCount = Infinity;
  let maxDepthForMinCount = -1;
  let nodesChecked = 0;
  let nodesWithIndices = 0;
  let candidateNodes: Array<{node: TreeNode, depth: number, pointCount: number}> = [];

  function searchNode(node: TreeNode, currentDepth: number = 0): void {
    if (!node) {
      console.log(`[TREE-UTILS] Skipping null node at depth ${currentDepth}`);
      return;
    }
    nodesChecked++;

    // Enhanced debugging for tree structure
    if (nodesChecked <= 10) {
      console.log(`[TREE-UTILS] Checking node ${node.id} at depth ${currentDepth}, has children: ${!!(node.children && node.children.length > 0)}, children count: ${node.children ? node.children.length : 0}`);
    }

    // Check if this node contains the point
    const nodeIndices = extractPointIndices(node);
    if (nodeIndices.length > 0) {
      nodesWithIndices++;
      if (nodesChecked <= 10) { // Log first 10 nodes for debugging
        console.log(`[TREE-UTILS] Node ${node.id} at depth ${currentDepth} has indices:`, nodeIndices.slice(0, 10), nodeIndices.length > 10 ? `... (${nodeIndices.length} total)` : '');
      }
      
      if (nodeIndices.includes(pointIndex)) {
        const pointCount = nodeIndices.length;
        candidateNodes.push({node, depth: currentDepth, pointCount});
        
        console.log(`[TREE-UTILS] FOUND point ${pointIndex} in node ${node.id} at depth ${currentDepth} with ${pointCount} points`);
        
        // Select the node with the fewest points (most specific)
        // If tied, prefer the deeper node (more specific in hierarchy)
        if (pointCount < minPointCount || (pointCount === minPointCount && currentDepth > maxDepthForMinCount)) {
          minPointCount = pointCount;
          maxDepthForMinCount = currentDepth;
          bestNode = node;
          console.log(`[TREE-UTILS] NEW BEST node: ${node.id} (${pointCount} points, depth ${currentDepth})`);
        }
      }
    } else if (nodesChecked <= 10) {
      console.log(`[TREE-UTILS] Node ${node.id} at depth ${currentDepth} has NO indices`);
    }

    // Search children recursively
    if (node.children && Array.isArray(node.children) && node.children.length > 0) {
      if (nodesChecked <= 5) {
        console.log(`[TREE-UTILS] Searching ${node.children.length} children of node ${node.id}`);
      }
      for (const child of node.children) {
        searchNode(child, currentDepth + 1);
      }
    } else if (nodesChecked <= 10) {
      console.log(`[TREE-UTILS] Node ${node.id} has no children (leaf node)`);
    }
  }

  console.log(`[TREE-UTILS] Searching for point ${pointIndex} in tree...`);
  console.log(`[TREE-UTILS] Tree root info:`, {
    id: tree.id,
    hasChildren: !!(tree.children && tree.children.length > 0),
    childrenCount: tree.children ? tree.children.length : 0,
    hasPointIndices: !!(tree.pointIndices && tree.pointIndices.length > 0),
    pointIndicesCount: tree.pointIndices ? tree.pointIndices.length : 0
  });
  
  searchNode(tree, 0);
  
  console.log(`[TREE-UTILS] Search complete. Checked ${nodesChecked} nodes, ${nodesWithIndices} had indices.`);
  console.log(`[TREE-UTILS] Found ${candidateNodes.length} candidate nodes:`, 
    candidateNodes.map(c => `${c.node.id}(${c.pointCount}pts,d${c.depth})`).join(', '));
  console.log(`[TREE-UTILS] Selected best node: ${bestNode?.id || 'none'} with ${minPointCount} points at depth ${maxDepthForMinCount}`);
  
  return bestNode;
}

/**
 * Alternative function name for clarity - finds the smallest node containing a point
 * @param tree - Root tree node to search  
 * @param pointIndex - The point index to find
 * @returns The smallest node containing the point, or null if not found
 */
export function findSmallestNodeContainingPoint(tree: TreeNode | null, pointIndex: number): TreeNode | null {
  return findDeepestNodeContainingPoint(tree, pointIndex);
}

/**
 * Gets the path from root to a specific node
 * @param tree - Root tree node
 * @param targetNode - The node to find the path to
 * @returns Array of nodes from root to target, or empty array if not found
 */
export function getPathToNode(tree: TreeNode | null, targetNode: TreeNode | null): TreeNode[] {
  if (!tree || !targetNode) return [];

  function findPath(node: TreeNode, path: TreeNode[]): TreeNode[] | null {
    const currentPath = [...path, node];
    
    // Check if this is the target node
    if (node.id === targetNode.id) {
      return currentPath;
    }

    // Search children
    if (node.children && Array.isArray(node.children)) {
      for (const child of node.children) {
        const result = findPath(child, currentPath);
        if (result) return result;
      }
    }

    return null;
  }

  return findPath(tree, []) || [];
}

/**
 * Checks if a node is visible in the current tree view state
 * For dendrogram: checks if the node is in the expanded path
 * For icicle: all nodes are visible by default
 * @param tree - Root tree node
 * @param targetNode - The node to check visibility for
 * @param expandedNodes - Set of expanded node IDs (for dendrogram)
 * @returns True if the node is visible in current view
 */
export function isNodeVisibleInTree(
  tree: TreeNode | null, 
  targetNode: TreeNode | null, 
  expandedNodes?: Set<string>
): boolean {
  if (!tree || !targetNode) return false;

  // If no expansion state provided, assume all nodes are visible (icicle plot)
  if (!expandedNodes) return true;

  // Get path to target node
  const pathToNode = getPathToNode(tree, targetNode);
  if (pathToNode.length === 0) return false;

  // Check if all ancestors are expanded (excluding the target node itself)
  for (let i = 0; i < pathToNode.length - 1; i++) {
    const node = pathToNode[i];
    if (!expandedNodes.has(node.id)) {
      return false;
    }
  }

  return true;
}

/**
 * Finds the deepest visible node in the tree that contains a specific point
 * This version respects the current tree expansion state (for dendrogram)
 * @param tree - Root tree node to search
 * @param pointIndex - The point index to find
 * @param expandedNodes - Set of expanded node IDs (optional, for dendrogram)
 * @returns The deepest visible node containing the point, or null if not found
 */
export function findDeepestVisibleNodeContainingPoint(
  tree: TreeNode | null, 
  pointIndex: number,
  expandedNodes?: Set<string>
): TreeNode | null {
  if (!tree || typeof pointIndex !== 'number' || pointIndex < 0) {
    console.log('[TREE-UTILS] findDeepestVisibleNodeContainingPoint: Invalid input');
    return null;
  }

  let bestNode: TreeNode | null = null;
  let maxDepth = -1;

  function searchVisibleNodes(node: TreeNode, depth: number = 0): void {
    if (!node) return;

    // Check if this node is visible in current tree state
    if (!isNodeVisibleInTree(tree, node, expandedNodes)) {
      return; // Skip this node and its children if not visible
    }

    // Check if this node contains the point
    const nodeIndices = extractPointIndices(node);
    if (nodeIndices.length > 0 && nodeIndices.includes(pointIndex)) {
      const pointCount = nodeIndices.length;
      
      console.log(`[TREE-UTILS] Visible node ${node.id} at depth ${depth} contains point ${pointIndex} (${pointCount} points)`);
      
      // Select the deepest node (highest depth value)
      if (depth > maxDepth) {
        maxDepth = depth;
        bestNode = node;
        console.log(`[TREE-UTILS] New deepest visible node: ${node.id} (${pointCount} points, depth ${depth})`);
      }
    }

    // Search children only if this node is expanded (or if no expansion state)
    if (node.children && Array.isArray(node.children)) {
      if (!expandedNodes || expandedNodes.has(node.id)) {
        for (const child of node.children) {
          searchVisibleNodes(child, depth + 1);
        }
      }
    }
  }

  console.log(`[TREE-UTILS] Searching for deepest visible node containing point ${pointIndex}...`);
  searchVisibleNodes(tree, 0);
  
  console.log(`[TREE-UTILS] Best visible node found: ${bestNode?.id || 'none'}`);
  return bestNode;
}

/**
 * Finds the deepest visible node containing a point (for icicle plot)
 * Icicle plots show all nodes, so this searches the entire tree for the deepest node
 * @param tree - Root tree node to search
 * @param pointIndex - The point index to find
 * @returns The deepest node containing the point, or null if not found
 */
export function findDeepestVisibleNodeForIcicle(
  tree: TreeNode | null, 
  pointIndex: number
): TreeNode | null {
  // For icicle plot, all nodes are visible, so use the original deepest search
  return findDeepestNodeContainingPoint(tree, pointIndex);
}

/**
 * Specialized search for depth-cut trees where cut nodes contain merged descendant points
 * This function prioritizes cut nodes since they represent the effective leaves of the tree
 * @param tree - Root tree node to search  
 * @param pointIndex - The point index to find
 * @returns The most appropriate node containing the point in a cut tree
 */
export function findNodeInCutTree(tree: TreeNode | null, pointIndex: number): TreeNode | null {
  if (!tree || typeof pointIndex !== 'number' || pointIndex < 0) {
    console.log('[TREE-UTILS] findNodeInCutTree: Invalid input');
    return null;
  }

  let bestNode: TreeNode | null = null;
  let bestScore = -1; // Combined score: depth + cut priority
  let candidateNodes: Array<{node: TreeNode, depth: number, pointCount: number, isCut: boolean}> = [];

  function searchCutTreeNode(node: TreeNode, currentDepth: number = 0): void {
    if (!node) return;

    const nodeIndices = extractPointIndices(node);
    if (nodeIndices.length > 0 && nodeIndices.includes(pointIndex)) {
      const isCutNode = !!(node as any)._was_cut;
      const pointCount = nodeIndices.length;
      
      candidateNodes.push({
        node, 
        depth: currentDepth, 
        pointCount, 
        isCut: isCutNode
      });

      // Scoring: prefer cut nodes (they contain merged descendants), then deeper nodes, then smaller point counts
      let score = currentDepth * 100; // Base score from depth
      if (isCutNode) {
        score += 1000; // High bonus for cut nodes since they represent the effective tree boundary
      }
      score += (1000 - pointCount); // Prefer nodes with fewer points (more specific)

      console.log(`[TREE-UTILS] Cut tree candidate: ${node.id} (depth: ${currentDepth}, points: ${pointCount}, cut: ${isCutNode}, score: ${score})`);

      if (score > bestScore) {
        bestScore = score;
        bestNode = node;
        console.log(`[TREE-UTILS] New best cut tree node: ${node.id} (score: ${score})`);
      }
    }

    // Continue searching children unless this is a cut node (cut nodes are effective leaves)
    if (node.children && Array.isArray(node.children) && !(node as any)._was_cut) {
      for (const child of node.children) {
        searchCutTreeNode(child, currentDepth + 1);
      }
    }
  }

  console.log(`[TREE-UTILS] Searching cut tree for point ${pointIndex}...`);
  searchCutTreeNode(tree, 0);
  
  console.log(`[TREE-UTILS] Cut tree search complete. Found ${candidateNodes.length} candidates.`);
  console.log(`[TREE-UTILS] Candidates:`, candidateNodes.map(c => 
    `${c.node.id}(d${c.depth},${c.pointCount}pts,cut:${c.isCut})`
  ).join(', '));
  
  return bestNode;
}