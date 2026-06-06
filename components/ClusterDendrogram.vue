<template>
  <div class="dendrogram-container">
    <ClientOnly>
      <div
        ref="treeContainer"
        class="tree-container"
        :style="{ width: `${props.width}px`, height: `${props.height}px` }"
      ></div>
      <template #fallback>
        <div class="loading-container" :style="{ width: `${props.width}px`, height: `${props.height}px` }">
          <div class="loading-spinner"></div>
          <p>Loading tree visualization...</p>
        </div>
      </template>
      <div v-if="!props.tree || !props.tree.root" class="no-data-message">
        <div 
          class="no-data-icon"
          v-tooltip="{
            content: 'Run clustering analysis to generate a dendrogram visualization of your data hierarchy',
            theme: 'info',
            position: 'top'
          }"
        >🌳</div>
        <p>No tree data to display.</p>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick, defineEmits } from 'vue';
import * as d3 from 'd3';
import { convertTreeToStandardFormat, extractPointIndices, validateTreePointIndices, calculateNodeSize, calculateNodePointCount, type TreeNode } from '~/composables/useTreeUtils';
import { useMemoryManagement } from '~/composables/useMemoryManagement';

const emit = defineEmits(['update:highlightedPoints', 'nodeSelected', 'clearSelections']);

const props = defineProps({
  tree: Object,
  width: {
    type: Number,
    default: 800
  },
  height: {
    type: Number,
    default: 600
  },
  nodeData: {
    type: Object,
    default: () => ({})
  },
  layout: {
    type: String,
    default: 'cartesian'
  },
  selectedColorBy: {
    type: String,
    default: 'predicted'
  },
  selectedOutlierStyle: {
    type: String,
    default: 'prominent'
  },
  highlightedNode: {
    type: Object,
    default: null
  },
  selectedNodes: {
    type: Set,
    default: () => new Set()
  }
});

const treeContainer = ref<HTMLElement | null>(null);
let svg: any = null;
let treeGroup: any = null;
let zoomBehavior: any = null;
let highlightTimeout: NodeJS.Timeout | null = null;
let mouseOverThrottleTimeout: NodeJS.Timeout | null = null;
let clearHighlightTimeout: NodeJS.Timeout | null = null;
// Hover performance throttling
let lastHoverTime = 0;
let hoverAnimationFrame: number | null = null;
const HOVER_THROTTLE_MS = 32; // ~30-60fps

// Memory management
const { trackLargeObject, forceGarbageCollection } = useMemoryManagement();

// Debug logging utility
const debug = process.env.NODE_ENV === 'development' ? console.log : () => {};
const debugWarn = process.env.NODE_ENV === 'development' ? console.warn : () => {};
const debugError = process.env.NODE_ENV === 'development' ? console.error : () => {};

// Helper function to calculate ground truth composition for a node
const calculateGroundTruthComposition = (nodeData: any): any[] | null => {
  if (!props.nodeData?.ground_truth?.labels || !props.nodeData?.ground_truth?.color_map) {
    return null;
  }
  
  // Get point indices for this node
  const pointIndices = extractPointIndices(nodeData);
  if (!pointIndices || pointIndices.length === 0) {
    return null;
  }
  
  const groundTruthLabels = props.nodeData.ground_truth.labels;
  const colorMap = props.nodeData.ground_truth.color_map;
  
  // Count ground truth labels for this node's points
  const labelCounts: { [key: string]: number } = {};
  let totalPoints = 0;
  
  for (const pointIndex of pointIndices) {
    if (pointIndex >= 0 && pointIndex < groundTruthLabels.length) {
      const label = String(groundTruthLabels[pointIndex]);
      labelCounts[label] = (labelCounts[label] || 0) + 1;
      totalPoints++;
    }
  }
  
  if (totalPoints === 0) {
    return null;
  }
  
  // Convert to composition format
  const composition = Object.entries(labelCounts).map(([label, count]) => ({
    label,
    count,
    proportion: count / totalPoints,
    color: colorMap[label] || '#cccccc'
  }));
  
  // Sort by count (highest first)
  composition.sort((a, b) => b.count - a.count);
  
  return composition;
};

// Color function for handling ground truth vs predicted colors
const getNodeColor = (nodeData: any): string => {
  if (props.selectedColorBy === 'ground_truth' && props.nodeData?.ground_truth) {
    // First try to use existing ground truth composition
    let composition = nodeData.ground_truth_composition;
    
    // If no composition exists, calculate it from point indices
    if (!composition || !Array.isArray(composition) || composition.length === 0) {
      composition = calculateGroundTruthComposition(nodeData);
    }
    
    // Use the calculated or existing composition
    if (composition && Array.isArray(composition) && composition.length > 0) {
      // Validate composition structure
      const validComposition = composition.filter((comp: any) => 
        comp && comp.color && comp.count > 0
      );
      
      if (validComposition.length === 0) {
        if (process.env.NODE_ENV === 'development') {
          debugWarn('Invalid ground truth composition structure, falling back to predicted color');
        }
        return nodeData.color || '#cccccc';
      }
      
      // If multiple ground truth labels, always use grey for mixed nodes
      if (validComposition.length > 1) {
        return '#BDBDBD'; // Grey for mixed nodes
      }
      
      // Single ground truth label - use its color
      const gtLabel = validComposition[0];
      if (gtLabel.color && gtLabel.color !== '#cccccc') {
        return gtLabel.color;
      }
    }
    
    // Fallback: try to use ground truth color map directly if available
    if (props.nodeData.ground_truth?.color_map && Object.keys(props.nodeData.ground_truth.color_map).length > 0) {
      // Get the first available ground truth color as fallback
      const firstGTColor = Object.values(props.nodeData.ground_truth.color_map)[0];
      if (firstGTColor && firstGTColor !== '#cccccc') {
        if (process.env.NODE_ENV === 'development') {
          debugWarn('Using fallback ground truth color from color map');
        }
        return firstGTColor;
      }
    }
    
    // Final fallback to predicted color with warning
    if (process.env.NODE_ENV === 'development') {
      debugWarn('No valid ground truth color found, falling back to predicted color');
    }
  }
  
  // Default predicted coloring
  if (nodeData.color_composition && nodeData.color_composition.length > 1) {
    return '#BDBDBD'; // Grey for mixed predicted clusters
  }
  
  // Special handling for outlier leaf nodes (label -1) - only in predicted mode
  if (props.selectedColorBy !== 'ground_truth') {
    const pointIndices = extractPointIndices(nodeData);
    if (pointIndices && pointIndices.length > 0 && props.nodeData?.labels) {
      // Check if this is a leaf node with only outlier points
      const isLeafNode = !nodeData.children || nodeData.children.length === 0;
      if (isLeafNode) {
        const allOutliers = pointIndices.every(idx => 
          idx >= 0 && idx < props.nodeData.labels.length && 
          String(props.nodeData.labels[idx]) === '-1'
        );
        if (allOutliers) {
          return '#000000'; // Black for outlier leaf nodes in tree (predicted mode only)
        }
      }
    }
    
    // Also check if nodeData.color is red (indicating backend assigned outlier color) and override it
    if (nodeData.color === '#FF0000') {
      return '#000000'; // Force black for any red outlier nodes from backend (predicted mode only)
    }
  }
  
  return nodeData.color || '#cccccc';
};

// Convert tree data to D3 hierarchy
function convertTreeToD3Format(treeData: any): TreeNode | null {
  debug('[ClusterDendrogram] Converting tree to D3 format:', {
    hasTreeData: !!treeData,
    treeDataType: typeof treeData,
    treeDataKeys: treeData ? Object.keys(treeData) : []
  });
  
  const standardTree = convertTreeToStandardFormat(treeData);
  
  if (!standardTree) {
    debugWarn('[ClusterDendrogram] Failed to convert tree to standard format');
    return null;
  }
  
  debug('[ClusterDendrogram] Tree converted to standard format:', {
    hasStandardTree: !!standardTree,
    standardTreeId: standardTree.id,
    hasChildren: !!(standardTree.children),
    childrenCount: standardTree.children ? standardTree.children.length : 0,
    pointIndicesCount: standardTree.pointIndices ? standardTree.pointIndices.length : 0
  });
  
  // Validate tree structure
  if (!validateTreePointIndices(standardTree)) {
    debugWarn('[ClusterDendrogram] Tree validation failed, but continuing with available data');
  } else {
    debug('[ClusterDendrogram] Tree validation passed');
  }
  
  return standardTree;
}

function renderTree() {
  try {
    if (!treeContainer.value || !props.tree) return;

    if (!isFinite(props.width) || !isFinite(props.height) || props.width <= 0 || props.height <= 0) {
      debugWarn('Invalid dimensions for dendrogram:', { width: props.width, height: props.height });
      return;
    }

    const container = d3.select(treeContainer.value);
    container.selectAll('*').remove();

    const treeData = convertTreeToD3Format(props.tree);
    if (!treeData) {
      debugError('[ClusterDendrogram] No tree data after conversion');
      return;
    }

    debug('[ClusterDendrogram] Creating D3 hierarchy from converted tree data');
    
    svg = container.append('svg')
      .attr('id', 'cluster-dendrogram')
      .attr('width', props.width)
      .attr('height', props.height)
      .style('border', '1px solid #ccc')
      .on('click', (event: any) => {
        // Clear selections when clicking on empty background
        if (event.target === svg.node() || event.target.tagName === 'svg') {
          emit('clearSelections');
        }
      });

    treeGroup = svg.append('g').attr('class', 'tree-group');

    const root = d3.hierarchy(treeData);
    debug('[ClusterDendrogram] D3 hierarchy created:', {
      hasRoot: !!root,
      hasDescendants: !!(root && root.descendants),
      descendantsCount: root && root.descendants ? root.descendants().length : 0,
      rootData: root ? root.data : null,
      rootChildren: root && root.children ? root.children.length : 0
    });
    
    if (!root || !root.descendants || root.descendants().length === 0) {
      debugWarn('[ClusterDendrogram] Invalid tree data for dendrogram - no descendants found');
      debugWarn('[ClusterDendrogram] Root details:', {
        hasRoot: !!root,
        hasDescendants: !!(root && root.descendants),
        descendantsCount: root && root.descendants ? root.descendants().length : 0
      });
      return;
    }
    
    debug('[ClusterDendrogram] D3 hierarchy validation passed, proceeding with layout');

    let treeLayout;
    if (props.layout === 'radial') {
      const radius = Math.min(props.width, props.height) / 2 - 40;
      treeLayout = d3.tree<TreeNode>()
        .size([2 * Math.PI, radius])
        .separation((a, b) => (a.parent == b.parent ? 2 : 4) / a.depth);
    } else {
        // Improved spacing to prevent node overlap
        const leafCount = root.leaves().length;
        // More generous spacing calculation to prevent overlap
        const minNodeSpacing = 30; // Increased from 18 to provide more space
        const calculatedHeight = Math.max(leafCount * minNodeSpacing, props.height - 80);
        const validHeight = Math.min(calculatedHeight, props.height + 400); // Allow more vertical space
        const validWidth = Math.max(props.width - 100, 200);
        
        treeLayout = d3.tree<TreeNode>()
          .size([validHeight, validWidth])
          .separation((a, b) => {
            // Improved separation based on node siblings and depth
            const baseSeparation = a.parent == b.parent ? 1.8 : 2.4;
            // Add extra spacing for nodes with many siblings
            const siblingCount = a.parent ? a.parent.children?.length || 1 : 1;
            const siblingFactor = Math.min(1 + (siblingCount - 1) * 0.1, 2);
            return baseSeparation * siblingFactor;
          });
    }

    trackLargeObject(treeData);
    const treeNodes = treeLayout(root);
    
    debug('[ClusterDendrogram] Tree layout applied:', {
      hasTreeNodes: !!treeNodes,
      treeNodesDescendants: treeNodes ? treeNodes.descendants().length : 0,
      treeNodesLinks: treeNodes ? treeNodes.links().length : 0
    });

    const descendants = treeNodes.descendants();
    debug('[ClusterDendrogram] Processing descendants:', {
      descendantsCount: descendants.length,
      firstFewDescendants: descendants.slice(0, 3).map(d => ({
        id: d.data?.id,
        hasData: !!d.data,
        x: d.x,
        y: d.y,
        hasChildren: !!(d.children),
        childrenCount: d.children ? d.children.length : 0
      }))
    });

    treeNodes.descendants().forEach((d: any) => {
      if (!isFinite(d.x)) d.x = 0;
      if (!isFinite(d.y)) d.y = 0;
      d.x0 = d.x;
      d.y0 = d.y;
    });

    if (props.layout === 'radial') {
      // Create links
      const links = treeNodes.links();
      debug('[ClusterDendrogram] Creating radial links:', { linksCount: links.length });
      
      treeGroup.selectAll('.link')
        .data(links)
        .enter()
        .append('path')
        .attr('class', 'link')
        .attr('d', d3.linkRadial()
          .angle((d: any) => d.x)
          .radius((d: any) => d.y) as any)
        .style('fill', 'none')
        .style('stroke', '#999')
        .style('stroke-width', 1.5);

      // Create nodes
      const nodeData = treeNodes.descendants();
      debug('[ClusterDendrogram] Creating radial nodes:', { nodesCount: nodeData.length });
      
      const nodes = treeGroup.selectAll('.node')
        .data(nodeData)
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', (d: any) => `
          rotate(${d.x * 180 / Math.PI - 90})
          translate(${d.y},0)
        `);

      nodes.append('circle')
        .attr('r', (d: any) => {
          const baseSize = calculateNodeSize(d.data, { minSize: 4, maxSize: 16, scaleFactor: 1.2, useDepth: true });
          // Make outlier nodes slightly larger
          const pointIndices = extractPointIndices(d.data);
          const isOutlierLeaf = pointIndices && pointIndices.length > 0 && props.nodeData?.labels &&
            (!d.data.children || d.data.children.length === 0) &&
            pointIndices.every(idx => 
              idx >= 0 && idx < props.nodeData.labels.length && 
              String(props.nodeData.labels[idx]) === '-1'
            );
          return isOutlierLeaf ? baseSize + 2 : baseSize;
        })
        .style('fill', (d: any) => getNodeColor(d.data))
        .style('stroke', (d: any) => {
          // Special border for outlier nodes
          const pointIndices = extractPointIndices(d.data);
          const isOutlierLeaf = pointIndices && pointIndices.length > 0 && props.nodeData?.labels &&
            (!d.data.children || d.data.children.length === 0) &&
            pointIndices.every(idx => 
              idx >= 0 && idx < props.nodeData.labels.length && 
              String(props.nodeData.labels[idx]) === '-1'
            );
          return isOutlierLeaf ? '#000000' : '#fff';
        })
        .style('stroke-width', (d: any) => {
          // Thicker border for outlier nodes
          const pointIndices = extractPointIndices(d.data);
          const isOutlierLeaf = pointIndices && pointIndices.length > 0 && props.nodeData?.labels &&
            (!d.data.children || d.data.children.length === 0) &&
            pointIndices.every(idx => 
              idx >= 0 && idx < props.nodeData.labels.length && 
              String(props.nodeData.labels[idx]) === '-1'
            );
          return isOutlierLeaf ? 3 : 2;
        });
      
      // Add expansion indicators for expandable nodes (skip root in radial layout)
      nodes.filter((d: any) => (d.children || d._children) && d.depth > 0)
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .style('font-size', '10px')
        .style('font-weight', 'bold')
        .style('fill', '#333')
        .style('pointer-events', 'none')
        .text((d: any) => d._children ? '+' : '−');
    } else {
        treeGroup.attr('transform', 'translate(50, 50)');
        // Create links
        const links = treeNodes.links();
        debug('[ClusterDendrogram] Creating horizontal links:', { linksCount: links.length });
        
        const linkElements = treeGroup.selectAll('.link')
            .data(links)
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('d', d3.linkHorizontal()
            .x((d: any) => isFinite(d.y) ? d.y : 0)
            .y((d: any) => isFinite(d.x) ? d.x : 0) as any)
            .style('fill', 'none')
            .style('stroke', '#999')
            .style('stroke-width', 2);

        // Create nodes
        const nodeData = treeNodes.descendants();
        debug('[ClusterDendrogram] Creating horizontal nodes:', { nodesCount: nodeData.length });
        
        const nodes = treeGroup.selectAll('.node')
            .data(nodeData)
            .enter()
            .append('g')
            .attr('class', 'node')
            .attr('transform', (d: any) => {
                const x = isFinite(d.x) ? d.x : 0;
                const y = isFinite(d.y) ? d.y : 0;
                return `translate(${y},${x})`;
            });
        
        nodes.append('circle')
            .attr('r', (d: any) => {
              const baseSize = calculateNodeSize(d.data, { minSize: 5, maxSize: 20, scaleFactor: 1.0, useDepth: false });
              // Make outlier nodes slightly larger
              const pointIndices = extractPointIndices(d.data);
              const isOutlierLeaf = pointIndices && pointIndices.length > 0 && props.nodeData?.labels &&
                (!d.data.children || d.data.children.length === 0) &&
                pointIndices.every(idx => 
                  idx >= 0 && idx < props.nodeData.labels.length && 
                  String(props.nodeData.labels[idx]) === '-1'
                );
              return isOutlierLeaf ? baseSize + 3 : baseSize;
            })
            .style('fill', (d: any) => getNodeColor(d.data))
            .style('stroke', (d: any) => {
              // Special border for outlier nodes
              const pointIndices = extractPointIndices(d.data);
              const isOutlierLeaf = pointIndices && pointIndices.length > 0 && props.nodeData?.labels &&
                (!d.data.children || d.data.children.length === 0) &&
                pointIndices.every(idx => 
                  idx >= 0 && idx < props.nodeData.labels.length && 
                  String(props.nodeData.labels[idx]) === '-1'
                );
              return isOutlierLeaf ? '#000000' : '#fff';
            })
            .style('stroke-width', (d: any) => {
              // Thicker border for outlier nodes
              const pointIndices = extractPointIndices(d.data);
              const isOutlierLeaf = pointIndices && pointIndices.length > 0 && props.nodeData?.labels &&
                (!d.data.children || d.data.children.length === 0) &&
                pointIndices.every(idx => 
                  idx >= 0 && idx < props.nodeData.labels.length && 
                  String(props.nodeData.labels[idx]) === '-1'
                );
              return isOutlierLeaf ? 3 : 2;
            });

        // Add expansion indicators for expandable nodes
        nodes.filter((d: any) => d.children || d._children)
            .append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .style('font-size', '12px')
            .style('font-weight', 'bold')
            .style('fill', '#333')
            .style('pointer-events', 'none')
            .text((d: any) => d._children ? '+' : '−');
    }


    if (props.layout === 'radial') {
      treeGroup.append('text')
        .attr('x', 0)
        .attr('y', 0)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('fill', '#666')
        .style('pointer-events', 'none')
        .text('C');
    }

    // Center the dendrogram
    const bounds = treeGroup.node().getBBox();
    const fullWidth = bounds.width;
    const fullHeight = bounds.height;
    const width = props.width;
    const height = props.height;
        const scale = Math.min(1.2, 1.1 / Math.max(fullWidth / width, fullHeight / height)); // Restore original scaling
    const midX = bounds.x + fullWidth / 2;
    const midY = bounds.y + fullHeight / 2;
    const translateX = width / 2 - midX * scale;
    const translateY = height / 2 - midY * scale;

    const initialTransform = d3.zoomIdentity.translate(translateX, translateY).scale(scale);

    zoomBehavior = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        treeGroup.attr('transform', event.transform);
      });

    svg.call(zoomBehavior);
    svg.call(zoomBehavior.transform, initialTransform);

    // Add event listeners to initial nodes
    const initialNodes = treeGroup.selectAll('.node');
    attachNodeEventListeners(initialNodes);
    
    // Apply selection styling to initial nodes
    applySelectionStyling(initialNodes);

    function attachNodeEventListeners(nodeSelection: any) {
      nodeSelection
        .style('cursor', 'pointer')
        .on('click', (event: any, d: any) => {
          event.stopPropagation();
          
          // Shift+Click validation (relaxed for D3.js compatibility)
          if (event.shiftKey && event.type === 'click') {
            // Basic validation for Shift+Click:
            // - shiftKey: Shift must be held
            // - type === 'click': Must be actual click event
            // Note: Removed strict button checks as they don't work reliably with D3.js events
            
            const nodeId = d.data.id;
            const isCurrentlySelected = props.selectedNodes.has(nodeId);
            const pointIndices = extractPointIndices(d.data);
            
            // Add debounce to prevent rapid-fire selections
            const now = Date.now();
            const lastClickKey = `click_${nodeId}`;
            if (window.lastClickTime && window.lastClickTime[lastClickKey] && 
                now - window.lastClickTime[lastClickKey] < 200) {
              // Ignore clicks within 200ms of the last click on this node
              return;
            }
            if (!window.lastClickTime) window.lastClickTime = {};
            window.lastClickTime[lastClickKey] = now;
            
            console.log(`[DENDROGRAM] Shift+click on node ${nodeId}, currently selected: ${isCurrentlySelected}`);
            
            // Emit selection event
            emit('nodeSelected', {
              nodeId: nodeId,
              points: pointIndices || [],
              isSelected: !isCurrentlySelected
            });
            
            // Update visual state immediately
            const circle = d3.select(event.currentTarget).select('circle');
            if (!isCurrentlySelected) {
              // Add selection styling
              circle
                .style('stroke', '#ff6b35')
                .style('stroke-width', 4)
                .style('filter', 'drop-shadow(0 0 6px rgba(255, 107, 53, 0.8))');
            } else {
              // Remove selection styling
              circle
                .style('stroke', '#fff')
                .style('stroke-width', 2)
                .style('filter', null);
            }
            
            return; // Don't expand/collapse when selecting
          }
          
          // Normal click behavior (expand/collapse)
          if (d.children) {
            d._children = d.children;
            d.children = null;
          } else if (d._children) {
            d.children = d._children;
            d._children = null;
          }
          // Re-render the tree with animation
          updateTree(d);
        })
        .on('mouseover', function(this: any, event: any, d: any) {
          const circle = d3.select(this).select('circle');
          const nodeId = d.data.id;
          const isSelected = props.selectedNodes.has(nodeId);
          
          // Only apply hover styling to unselected nodes to avoid confusion
          if (!isSelected) {
            // Normal hover styling for unselected nodes only
            circle.style('stroke', '#333').style('stroke-width', 3);
            
            // Add glow effect for expandable nodes
            if (d.children || d._children) {
              circle.style('filter', 'drop-shadow(0 0 6px rgba(51, 51, 51, 0.6))');
            }
          }
          // Selected nodes keep their selection styling during hover
          
          // Throttled highlight emission using rAF + time gating
          const now = performance.now();
          const emitHighlight = () => {
            try {
              const pointIndices = extractPointIndices(d.data);
              if (pointIndices.length > 0) {
                emit('update:highlightedPoints', pointIndices);
              }
              // Lightweight tooltip logic
              if (d.data.color_composition?.length > 1) {
                showTooltip(event, d.data.color_composition, d.data.ground_truth_composition);
              } else if (pointIndices.length > 0) {
                showSimpleTooltip(event, d, pointIndices.length);
              }
            } catch (error) {
              console.warn('[DENDROGRAM] Error in mouseover handler:', error);
            }
          };

          if (now - lastHoverTime < HOVER_THROTTLE_MS) {
            if (hoverAnimationFrame) cancelAnimationFrame(hoverAnimationFrame);
            hoverAnimationFrame = requestAnimationFrame(() => {
              emitHighlight();
              hoverAnimationFrame = null;
            });
          } else {
            lastHoverTime = now;
            emitHighlight();
          }
        })
        .on('mouseout', function(this: any, event: any, d: any) {
          const circle = d3.select(this).select('circle');
          const nodeId = d.data.id;
          const isSelected = props.selectedNodes.has(nodeId);
          
          // Only reset styling for unselected nodes
          if (!isSelected) {
            // Restore default styling for unselected nodes
            circle.style('stroke', '#fff').style('stroke-width', 2);
            circle.style('filter', null);
          }
          // Selected nodes keep their selection styling
          
          // Cancel any pending mouseover action
          if (mouseOverThrottleTimeout) {
            clearTimeout(mouseOverThrottleTimeout);
            mouseOverThrottleTimeout = null;
          }
          
          // Debounce the highlight clearing to prevent flickering between nodes
          if (clearHighlightTimeout) {
            clearTimeout(clearHighlightTimeout);
          }
          clearHighlightTimeout = setTimeout(() => {
            try {
              emit('update:highlightedPoints', []);
              hideTooltip();
            } catch (error) {
              console.warn('[DENDROGRAM] Error in mouseout handler:', error);
            }
            clearHighlightTimeout = null;
          }, 100); // Longer delay to prevent flickering between nodes
        });
    }

    // Apply selection styling to nodes based on selectedNodes prop
    function applySelectionStyling(nodeSelection: any) {
      nodeSelection.each(function(d: any) {
        const circle = d3.select(this).select('circle');
        const nodeId = d.data.id;
        const isSelected = props.selectedNodes.has(nodeId);
        
        if (isSelected) {
          // Apply selection styling
          circle
            .style('stroke', '#ff6b35')
            .style('stroke-width', 4)
            .style('filter', 'drop-shadow(0 0 6px rgba(255, 107, 53, 0.8))');
        } else {
          // Ensure default styling
          circle
            .style('stroke', '#fff')
            .style('stroke-width', 2)
            .style('filter', null);
        }
      });
    }

    // Progressive rendering for large trees
    function renderNodesProgressively(allNodes: any[], source: any, duration: number) {
      const chunkSize = 50; // Render 50 nodes at a time
      let currentIndex = 0;
      
      function renderNodeChunk() {
        const endIndex = Math.min(currentIndex + chunkSize, allNodes.length);
        const chunk = allNodes.slice(currentIndex, endIndex);
        
        // Process this chunk of nodes
        const nodeUpdate = treeGroup.selectAll(`.node-chunk-${Math.floor(currentIndex / chunkSize)}`)
          .data(chunk, (d: any) => d.data.id);

        const nodeEnter = nodeUpdate.enter().append('g')
          .attr('class', `node node-chunk-${Math.floor(currentIndex / chunkSize)}`)
          .style('opacity', 0);

        // Apply positioning based on layout
        if (props.layout === 'radial') {
          nodeEnter.attr('transform', `
            rotate(${source.x0 * 180 / Math.PI - 90})
            translate(${source.y0},0)
          `);
        } else {
          nodeEnter.attr('transform', () => {
            const x = isFinite(source.x0) ? source.x0 : (isFinite(source.x) ? source.x : 0);
            const y = isFinite(source.y0) ? source.y0 : (isFinite(source.y) ? source.y : 0);
            return `translate(${y},${x})`;
          });
        }

        // Add circle elements
        nodeEnter.append('circle')
          .attr('r', 0)
          .style('fill', (d: any) => getNodeColor(d.data))
          .style('stroke', '#fff')
          .style('stroke-width', 2);

        // Add expansion indicators
        nodeEnter.filter((d: any) => (d.children || d._children) && (props.layout !== 'radial' || d.depth > 0))
          .append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '0.35em')
          .style('font-size', props.layout === 'radial' ? '10px' : '12px')
          .style('font-weight', 'bold')
          .style('fill', '#333')
          .style('pointer-events', 'none')
          .style('opacity', 0)
          .text((d: any) => d._children ? '+' : '−');

        // Attach event listeners
        attachNodeEventListeners(nodeEnter);
        
        // Apply selection styling
        applySelectionStyling(nodeEnter);

        // Animate nodes in
        const nodeUpdateMerged = nodeEnter.merge(nodeUpdate);
        nodeUpdateMerged.transition()
          .duration(duration)
          .style('opacity', 1)
          .attr('transform', (d: any) => {
            if (props.layout === 'radial') {
              return `rotate(${d.x * 180 / Math.PI - 90}) translate(${d.y},0)`;
            } else {
              return `translate(${d.y},${d.x})`;
            }
          });

        currentIndex = endIndex;
        
        // Continue with next chunk if there are more nodes
        if (currentIndex < allNodes.length) {
          requestAnimationFrame(renderNodeChunk);
        } else {
          console.log(`ClusterDendrogram: Progressive rendering completed for ${allNodes.length} nodes`);
        }
      }
      
      // Start progressive rendering
      requestAnimationFrame(renderNodeChunk);
    }

    function updateTree(source: any) {
      const duration = 300;
      const updatedNodes = treeLayout(root);
      const allNodes = updatedNodes.descendants();
      
      allNodes.forEach((d: any) => {
        if (!isFinite(d.x)) d.x = 0;
        if (!isFinite(d.y)) d.y = 0;
      });

      // Performance optimization: Use chunked rendering for large trees
      if (allNodes.length > 200) {
        console.log(`ClusterDendrogram: Using progressive rendering for ${allNodes.length} nodes`);
        renderNodesProgressively(allNodes, source, duration);
        return;
      }

      const nodeUpdate = treeGroup.selectAll('.node')
        .data(allNodes, (d: any) => d.data.id);

      const nodeEnter = nodeUpdate.enter().append('g')
        .attr('class', 'node')
        .style('opacity', 0);

      if (props.layout === 'radial') {
        nodeEnter.attr('transform', `
          rotate(${source.x0 * 180 / Math.PI - 90})
          translate(${source.y0},0)
        `);
      } else {
        nodeEnter.attr('transform', () => {
            const x = isFinite(source.x0) ? source.x0 : (isFinite(source.x) ? source.x : 0);
            const y = isFinite(source.y0) ? source.y0 : (isFinite(source.y) ? source.y : 0);
            return `translate(${y},${x})`;
        });
      }

      nodeEnter.append('circle')
        .attr('r', 0)
        .style('fill', (d: any) => getNodeColor(d.data))
        .style('stroke', '#fff')
        .style('stroke-width', 2);

      // Add expansion indicators for expandable nodes (skip root in radial layout)
      nodeEnter.filter((d: any) => (d.children || d._children) && (props.layout !== 'radial' || d.depth > 0))
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .style('font-size', props.layout === 'radial' ? '10px' : '12px')
        .style('font-weight', 'bold')
        .style('fill', '#333')
        .style('pointer-events', 'none')
        .style('opacity', 0)
        .text((d: any) => d._children ? '+' : '−');

      // Attach event listeners to newly created nodes
      attachNodeEventListeners(nodeEnter);
      
      // Apply selection styling to newly created nodes
      applySelectionStyling(nodeEnter);

      const nodeUpdateMerged = nodeEnter.merge(nodeUpdate);

      const nodeTransition = nodeUpdateMerged.transition().duration(duration).style('opacity', 1);
      
      if (props.layout === 'radial') {
        nodeTransition.attr('transform', (d: any) => `
          rotate(${d.x * 180 / Math.PI - 90})
          translate(${d.y},0)
        `);
      } else {
        nodeTransition.attr('transform', (d: any) => {
            const validX = isFinite(d.x) ? d.x : 0;
            const validY = isFinite(d.y) ? d.y : 0;
            
            d.x0 = validX;
            d.y0 = validY;
            return `translate(${validY},${validX})`;
        });
      }

      nodeUpdateMerged.select('circle').transition().duration(duration)
        .attr('r', (d: any) => {
          // Use the same sizing logic as initial render
          if (props.layout === 'radial') {
            return calculateNodeSize(d.data, { minSize: 4, maxSize: 16, scaleFactor: 1.2, useDepth: true });
          } else {
            return calculateNodeSize(d.data, { minSize: 5, maxSize: 20, scaleFactor: 1.0, useDepth: false });
          }
        })
        .style('stroke', '#fff')
        .style('stroke-width', 2);

      // Update expansion indicators
      nodeUpdateMerged.select('text').transition().duration(duration)
        .style('opacity', 1)
        .text((d: any) => d._children ? '+' : '−');

      const nodeExitTransition = nodeUpdate.exit().transition().duration(duration).style('opacity', 0).remove();

      if (props.layout === 'radial') {
        nodeExitTransition.attr('transform', `
          rotate(${source.x * 180 / Math.PI - 90})
          translate(${source.y},0)
        `);
      } else {
        nodeExitTransition.attr('transform', () => {
            const x = isFinite(source.x) ? source.x : 0;
            const y = isFinite(source.y) ? source.y : 0;
            return `translate(${y},${x})`;
        });
      }

      const linkUpdate = treeGroup.selectAll('.link')
        .data(updatedNodes.links(), (d: any) => d.target.data.id);

      const linkEnter = linkUpdate.enter().insert('path', 'g')
        .attr('class', 'link')
        .style('fill', 'none')
        .style('stroke', '#999')
        .style('stroke-width', 1.5)

      if (props.layout === 'radial') {
        linkEnter.attr('d', d3.linkRadial()
          .angle((d: any) => source.x0)
          .radius((d: any) => source.y0) as any);
      } else {
        linkEnter.attr('d', () => {
            const x = isFinite(source.x0) ? source.x0 : (isFinite(source.x) ? source.x : 0);
            const y = isFinite(source.y0) ? source.y0 : (isFinite(source.y) ? source.y : 0);
            const o = { x, y };
            return (d3.linkHorizontal() as any)({ source: o, target: o });
        });
      }

      const linkTransition = linkEnter.merge(linkUpdate).transition().duration(duration);
      const linkExitTransition = linkUpdate.exit().transition().duration(duration).remove();

      if (props.layout === 'radial') {
        linkTransition.attr('d', d3.linkRadial()
          .angle((d: any) => d.x)
          .radius((d: any) => d.y) as any);
        linkExitTransition.attr('d', d3.linkRadial()
          .angle((d: any) => source.x)
          .radius((d: any) => source.y) as any);
      } else {
        linkTransition.attr('d', d3.linkHorizontal()
            .x((d: any) => isFinite(d.y) ? d.y : 0)
            .y((d: any) => isFinite(d.x) ? d.x : 0) as any);
        linkExitTransition.attr('d', () => {
            const x = isFinite(source.x) ? source.x : 0;
            const y = isFinite(source.y) ? source.y : 0;
            const o = { x, y };
            return (d3.linkHorizontal() as any)({ source: o, target: o });
        });
      }
    }

    root.descendants().forEach((d: any) => {
      if (d.depth > 2 && d.children) {
        d._children = d.children;
        d.children = null;
      }
      d.x0 = d.x;
      d.y0 = d.y;
    });
    
    updateTree(root);

  } catch (error) {
    debugError('Error rendering dendrogram tree:', error);
    if (svg) {
      svg.selectAll('*').interrupt().remove();
      svg = null;
    }
    hideTooltip();
    if (treeContainer.value) {
      const container = d3.select(treeContainer.value);
      container.selectAll('*').remove();
      container.append('div')
        .style('display', 'flex')
        .style('align-items', 'center')
        .style('justify-content', 'center')
        .style('height', '100%')
        .style('color', '#666')
        .text('Error rendering tree visualization');
    }
    forceGarbageCollection();
  }
}

// Tooltip functions with proper cleanup
let tooltip: any = null;
let tooltipCleanupTimer: NodeJS.Timeout | null = null;

function showTooltip(event: any, colorComposition: any[], groundTruthComposition?: any[]) {
  hideTooltip();
  
  tooltip = d3.select('body').append('div')
    .attr('class', 'tree-tooltip')
    .style('position', 'absolute')
    .style('background', 'rgba(0, 0, 0, 0.8)')
    .style('color', 'white')
    .style('padding', '8px')
    .style('border-radius', '4px')
    .style('font-size', '12px')
    .style('pointer-events', 'none')
    .style('opacity', 0);

  let content = '';

  if (props.selectedColorBy === 'ground_truth' && groundTruthComposition && groundTruthComposition.length > 0) {
    // Show ground truth composition when ground truth is selected
    const groundTruthContent = groundTruthComposition.map(comp => 
      `<div style="margin: 2px 0;">
        <span style="display: inline-block; width: 12px; height: 12px; background: ${comp.color}; margin-right: 5px;"></span>
        ${comp.label}: ${comp.count} (${(comp.proportion * 100).toFixed(1)}%)
      </div>`
    ).join('');
    
    content = `<strong>Ground Truth:</strong><br/>${groundTruthContent}`;
    
    // Optionally show predicted clusters as secondary info
    if (colorComposition && colorComposition.length > 0) {
      const predictedContent = colorComposition.map(comp => 
        `<div style="margin: 2px 0;">
          <span style="display: inline-block; width: 12px; height: 12px; background: ${comp.color}; margin-right: 5px;"></span>
          ${comp.label}: ${comp.count} (${(comp.proportion * 100).toFixed(1)}%)
        </div>`
      ).join('');
      content += `<br/><strong>Predicted Clusters:</strong><br/>${predictedContent}`;
    }
  } else {
    // Default behavior - show predicted clusters
    const predictedContent = colorComposition.map(comp => 
      `<div style="margin: 2px 0;">
        <span style="display: inline-block; width: 12px; height: 12px; background: ${comp.color}; margin-right: 5px;"></span>
        ${comp.label}: ${comp.count} (${(comp.proportion * 100).toFixed(1)}%)
      </div>`
    ).join('');

    content = `<strong>Predicted Clusters:</strong><br/>${predictedContent}`;

    if (groundTruthComposition && groundTruthComposition.length > 0) {
      const groundTruthContent = groundTruthComposition.map(comp => 
        `<div style="margin: 2px 0;">
          <span style="display: inline-block; width: 12px; height: 12px; background: ${comp.color}; margin-right: 5px;"></span>
          ${comp.label}: ${comp.count} (${(comp.proportion * 100).toFixed(1)}%)
        </div>`
      ).join('');
      
      content += `<br/><strong>Ground Truth:</strong><br/>${groundTruthContent}`;
    }
  }

  tooltip.html(content)
    .style('left', (event.pageX + 10) + 'px')
    .style('top', (event.pageY - 10) + 'px')
    .transition()
    .duration(200)
    .style('opacity', 1);
}

function showSimpleTooltip(event: any, d: any, pointCount: number) {
  hideTooltip();
  
  tooltip = d3.select('body').append('div')
    .attr('class', 'tree-tooltip')
    .style('position', 'absolute')
    .style('background', 'rgba(0, 0, 0, 0.8)')
    .style('color', 'white')
    .style('padding', '8px')
    .style('border-radius', '4px')
    .style('font-size', '12px')
    .style('pointer-events', 'none')
    .style('opacity', 0);

  const label = d.data.label !== undefined ? String(d.data.label) : (d.data.name || (d.data.id === '-1' ? 'internal node' : d.data.id) || 'Node');
  const nodeType = d.data._is_summary ? 'Summary' : ((!d.children && !d._children) ? 'Leaf' : 'Internal');
  const actualPointCount = calculateNodePointCount(d.data);
  
  const content = `<strong>${label}</strong><br/>Type: ${nodeType}<br/>Data Points: ${actualPointCount}<br/>Depth: ${d.depth}`;

  tooltip.html(content)
    .style('left', (event.pageX + 10) + 'px')
    .style('top', (event.pageY - 10) + 'px')
    .transition()
    .duration(200)
    .style('opacity', 1);
}

function hideTooltip() {
  // Clear any pending cleanup
  if (tooltipCleanupTimer) {
    clearTimeout(tooltipCleanupTimer);
    tooltipCleanupTimer = null;
  }
  
  if (tooltip) {
    // Cancel any ongoing transitions
    tooltip.interrupt();
    
    // Remove immediately or with transition
    if (tooltip.node()) {
      tooltip.transition()
        .duration(200)
        .style('opacity', 0)
        .on('end', function() {
          // Ensure removal even if transition is interrupted
          if (tooltip && tooltip.node()) {
            tooltip.remove();
          }
        })
        .remove();
    }
    
    tooltip = null;
  }
  
  // Cleanup any orphaned tooltips
  d3.selectAll('.tree-tooltip').remove();
}

const handleResize = () => {
  if (svg) {
    svg.attr('width', props.width)
       .attr('height', props.height);
    renderTree();
  }
};

function highlightNodeInTree(highlightedNodeInfo: any) {
  console.log('[DENDROGRAM] highlightNodeInTree called with:', highlightedNodeInfo);
  if (!svg || !treeGroup || !highlightedNodeInfo) {
    console.log('[DENDROGRAM] Missing requirements - svg:', !!svg, 'treeGroup:', !!treeGroup, 'highlightedNodeInfo:', !!highlightedNodeInfo);
    return;
  }
  
  const { nodeId } = highlightedNodeInfo;
  console.log('[DENDROGRAM] Looking for node with ID:', nodeId);
  
  // Clear any existing timeout
  if (highlightTimeout) {
    clearTimeout(highlightTimeout);
    highlightTimeout = null;
  }
  
  // Clear any existing highlights
  treeGroup.selectAll('.node circle')
    .style('stroke', '#fff')
    .style('stroke-width', 2)
    .style('filter', null)
    .style('box-shadow', null);
  
  // Remove any existing highlight elements
  treeGroup.selectAll('.highlight-glow').remove();
  treeGroup.selectAll('.highlight-label').remove();
  treeGroup.selectAll('.highlight-ray').remove();
  
  // Find all nodes with the target ID
  const candidateNodes = treeGroup.selectAll('.node')
    .filter((d: any) => d.data.id === nodeId);
  
  console.log('[DENDROGRAM] Found', candidateNodes.size(), 'nodes with ID:', nodeId);
  
  if (!candidateNodes.empty()) {
    // If multiple nodes have the same ID, select the one with the highest depth (deepest)
    let targetNode = null;
    let maxDepth = -1;
    
    candidateNodes.each(function(d: any) {
      const nodeDepth = d.depth || 0;
      console.log('[DENDROGRAM] Node', d.data.id, 'at depth', nodeDepth);
      if (nodeDepth > maxDepth) {
        maxDepth = nodeDepth;
        targetNode = this;
      }
    });
    
    if (targetNode) {
      console.log('[DENDROGRAM] Highlighting deepest node with ID:', nodeId, 'at depth:', maxDepth);
      // Enhanced highlighting with better visual effects
      const circle = d3.select(targetNode).select('circle');
      
      // Apply enhanced highlight styling
      circle
        .style('stroke', '#ff6b35')
        .style('stroke-width', 6)
        .style('filter', 'drop-shadow(0 0 12px rgba(255, 107, 53, 0.8)) drop-shadow(0 0 24px rgba(255, 107, 53, 0.4))')
        .style('stroke-dasharray', '4,2')
        .style('stroke-dashoffset', 0);
      
      // Add pulsing animation
      circle
        .transition()
        .duration(1000)
        .style('stroke-dashoffset', -12)
        .on('end', function repeat() {
          d3.select(this)
            .transition()
            .duration(1000)
            .style('stroke-dashoffset', -24)
            .on('end', repeat);
        });
    }
    
    // Note: Camera centering removed to prevent unwanted view changes when clicking scatter plot points
    
    // Set timeout to clear highlight after 5 seconds
    highlightTimeout = setTimeout(() => {
      console.log('[DENDROGRAM] Clearing highlight after 5 seconds');
      treeGroup.selectAll('.node circle')
        .interrupt() // Stop any ongoing animations
        .style('stroke', '#fff')
        .style('stroke-width', 2)
        .style('filter', null)
        .style('stroke-dasharray', null)
        .style('stroke-dashoffset', null);
      highlightTimeout = null;
    }, 5000);
  } else {
    console.warn('[DENDROGRAM] Target node not found in current view:', nodeId);
    console.log('[DENDROGRAM] Falling back to find deepest visible node containing the point...');
    
    // Fallback: find the deepest visible node that contains this point
    if (highlightedNodeInfo.pointIndex !== undefined) {
      const pointIndex = highlightedNodeInfo.pointIndex;
      const allVisibleNodes = treeGroup.selectAll('.node').data();
      
      let fallbackNode = null;
      let maxDepth = -1;
      
      // Find the deepest visible node that contains this point
      for (const nodeData of allVisibleNodes) {
        const nodeIndices = extractPointIndices(nodeData.data);
        if (nodeIndices.includes(pointIndex)) {
          const nodeDepth = nodeData.depth || 0;
          console.log('[DENDROGRAM] Visible node', nodeData.data.id, 'at depth', nodeDepth, 'contains point', pointIndex);
          
          if (nodeDepth > maxDepth) {
            maxDepth = nodeDepth;
            fallbackNode = nodeData;
          }
        }
      }
      
      if (fallbackNode) {
        console.log('[DENDROGRAM] Found fallback node:', fallbackNode.data.id, 'at depth:', maxDepth);
        
        // Find the DOM element for this fallback node
        const fallbackElement = treeGroup.selectAll('.node')
          .filter((d: any) => d === fallbackNode)
          .node();
        
        if (fallbackElement) {
          console.log('[DENDROGRAM] Highlighting fallback node:', fallbackNode.data.id);
          const circle = d3.select(fallbackElement).select('circle');
          
          // Apply enhanced highlight styling
          circle
            .style('stroke', '#ff6b35')
            .style('stroke-width', 6)
            .style('filter', 'drop-shadow(0 0 12px rgba(255, 107, 53, 0.8)) drop-shadow(0 0 24px rgba(255, 107, 53, 0.4))')
            .style('stroke-dasharray', '4,2')
            .style('stroke-dashoffset', 0);
          
          // Add pulsing animation
          circle
            .transition()
            .duration(1000)
            .style('stroke-dashoffset', -12)
            .on('end', function repeat() {
              d3.select(this)
                .transition()
                .duration(1000)
                .style('stroke-dashoffset', -24)
                .on('end', repeat);
            });
            
          // Note: Camera centering removed to prevent unwanted view changes when clicking scatter plot points
          
          // Set timeout to clear highlight after 5 seconds
          highlightTimeout = setTimeout(() => {
            console.log('[DENDROGRAM] Clearing fallback highlight after 5 seconds');
            treeGroup.selectAll('.node circle')
              .interrupt() // Stop any ongoing animations
              .style('stroke', '#fff')
              .style('stroke-width', 2)
              .style('filter', null)
              .style('stroke-dasharray', null)
              .style('stroke-dashoffset', null);
            highlightTimeout = null;
          }, 5000);
        }
      } else {
        console.log('[DENDROGRAM] No visible node found containing point', pointIndex);
      }
    }
    
    // Log available nodes for debugging
    const availableNodes = treeGroup.selectAll('.node').data().map((d: any) => d.data.id);
    console.log('[DENDROGRAM] Available node IDs:', availableNodes.slice(0, 10), '... (showing first 10)');
  }
}

watch(() => props.tree, (newVal) => {
  if (newVal && newVal.root) renderTree();
}, { deep: true });

watch(() => [props.width, props.height, props.layout, props.selectedColorBy], () => {
  if (props.tree && props.tree.root) renderTree();
});

watch(() => props.highlightedNode, (newHighlightedNode) => {
  console.log('[DENDROGRAM] highlightedNode changed:', newHighlightedNode);
  if (newHighlightedNode && svg) {
    console.log('[DENDROGRAM] About to highlight node:', newHighlightedNode.nodeId);
    highlightNodeInTree(newHighlightedNode);
  } else {
    console.log('[DENDROGRAM] No highlighted node or SVG not ready');
  }
}, { deep: true });

onMounted(async () => {
  await nextTick();
  setTimeout(() => {
    if (props.tree && props.tree.root) renderTree();
  }, 100);
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  debug('[ClusterDendrogram] Starting comprehensive cleanup');
  
  // Clean up timeout
  if (highlightTimeout) {
    clearTimeout(highlightTimeout);
    highlightTimeout = null;
  }
  
  // Clean up global event listeners
  window.removeEventListener('resize', handleResize);
  
  // Clean up tooltip and any pending timers
  hideTooltip();
  if (tooltipCleanupTimer) {
    clearTimeout(tooltipCleanupTimer);
    tooltipCleanupTimer = null;
  }
  
  // Comprehensive D3 cleanup
  if (svg) {
    // Interrupt any ongoing transitions
    svg.selectAll('*').interrupt();
    
    // Remove all event listeners with namespaces to prevent conflicts
    svg.selectAll('.node')
      .on('click.dendrogram', null)
      .on('mouseover.dendrogram', null)
      .on('mouseout.dendrogram', null)
      .on('mouseenter.dendrogram', null)
      .on('mouseleave.dendrogram', null);
    
    svg.selectAll('.link')
      .on('click.dendrogram', null)
      .on('mouseover.dendrogram', null)
      .on('mouseout.dendrogram', null);
    
    // Remove zoom behavior completely
    if (zoomBehavior) {
      svg.on('.zoom', null);
      svg.call(zoomBehavior.transform, d3.zoomIdentity); // Reset transform
      zoomBehavior = null;
    }
    
    // Remove all other potential event listeners
    svg.on('click', null)
       .on('mouseover', null)
       .on('mouseout', null)
       .on('wheel', null)
       .on('touchstart', null)
       .on('touchmove', null)
       .on('touchend', null);
    
    // Clear all SVG content
    svg.selectAll('*').remove();
    svg = null;
  }
  
  // Clear references
  if (treeGroup) {
    treeGroup = null;
  }
  
  // Clean up container
  if (treeContainer.value) {
    const container = d3.select(treeContainer.value);
    container.selectAll('*').remove();
    // Remove any remaining event listeners from container
    container.on('click', null)
             .on('mouseover', null)
             .on('mouseout', null);
  }
  
  // Clean up any orphaned tooltips in the DOM
  d3.selectAll('.tree-tooltip').remove();
  
  // Force garbage collection in development
  if (process.env.NODE_ENV === 'development') {
    setTimeout(() => {
      forceGarbageCollection();
      debug('[ClusterDendrogram] Cleanup completed');
    }, 100);
  }
});
</script>

<style scoped>
.dendrogram-container {
  background-color: #ffffff;
  overflow: hidden;
  height: 100%;
}

.tree-container {
  background-color: #ffffff;
  overflow: hidden;
  width: 100%;
  height: 100%;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #f9fafb;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  color: #6b7280;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.no-data-message {
  text-align: center;
  padding: 48px 24px;
  color: #6b7280;
}

.no-data-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

.no-data-message p {
  margin: 0;
  font-size: 0.875rem;
}

:global(.tree-tooltip) {
  position: absolute;
  background: rgba(17, 24, 39, 0.95);
  color: white;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 0.75rem;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(8px);
  max-width: 240px;
  line-height: 1.4;
}

:global(.node) {
  cursor: pointer;
}

:global(.node circle) {
  transition: all 0.2s ease;
}

:global(.node:hover circle) {
  stroke-width: 3px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

:global(.link) {
  transition: stroke-width 0.2s ease;
}

</style>
