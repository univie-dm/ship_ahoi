<template>
  <div class="icicle-container">
    <ClientOnly>
      <div
        ref="icicleContainer"
        class="icicle-svg-container"
        :style="{ width: `${props.width}px`, height: `${props.height}px` }"
      ></div>
      <template #fallback>
        <div class="loading-container" :style="{ width: `${props.width}px`, height: `${props.height}px` }">
          <div class="loading-spinner"></div>
          <p>Loading icicle visualization...</p>
        </div>
      </template>
      <div v-if="!props.tree || !props.tree.root" class="no-data-message">
        <div class="no-data-icon">🧊</div>
        <p>No tree data to display.</p>
      </div>
    </ClientOnly>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick, defineEmits } from 'vue';
import * as d3 from 'd3';
import { convertTreeToStandardFormat, extractPointIndices, validateTreePointIndices, type TreeNode } from '~/composables/useTreeUtils';
import { useMemoryManagement } from '~/composables/useMemoryManagement';
import scientificColors from '~/composables/useScientificColors';

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

const icicleContainer = ref<HTMLElement | null>(null);
let svg: any = null;
let icicleGroup: any = null;

// Memory management
const { trackLargeObject, forceGarbageCollection } = useMemoryManagement();

let tooltip: any = null;
let renderInProgress = false;
let clearHighlightTimeout: NodeJS.Timeout | null = null;
let hideTooltipTimeout: NodeJS.Timeout | null = null;
let highlightTimeout: NodeJS.Timeout | null = null;
let highlightThrottleTimeout: NodeJS.Timeout | null = null;

// Performance optimization variables
let lastHoverTime = 0;
let hoverAnimationFrame: number | null = null;
const HOVER_THROTTLE_MS = 32; // ~30fps for better performance

// Hover state tracking
let currentHoveredElement: any = null;
let isHovering = false;

// Performance cache for hover styles
const hoverStyleCache = new Map<string, any>();

// Optimized hover emission function
const handleHoverEmission = (d: any) => {
  // Double-check component state before emitting
  if (isUnmounting.value || !isMounted.value) {
    return;
  }
  
  try {
    // Extract and emit point indices for scatter plot highlighting
    const pointIndices = extractPointIndices(d.data);
    if (pointIndices && pointIndices.length > 0) {
      // Use safe emit to prevent Vue reactivity errors
      safeEmit('update:highlightedPoints', pointIndices);
    }
  } catch (error) {
    // Silent error handling - continue execution
    console.warn('[IciclePlot] Error in highlight emission:', error);
  }
};

// Component lifecycle state
const isMounted = ref(false);
const isUnmounting = ref(false);

// Safe emit function to prevent Vue reactivity errors during navigation
const safeEmit = (eventName: 'update:highlightedPoints', ...args: any[]) => {
  // Multiple safety checks before emitting
  if (isUnmounting.value || !isMounted.value || !icicleContainer.value) {
    return;
  }
  
  try {
    emit(eventName, ...args);
  } catch (error: any) {
    // Silent handling of Vue reactivity errors during navigation
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[IciclePlot] Vue reactivity error during ${eventName} emit (likely navigation):`, error?.message || error);
    }
  }
};

// Add proper lifecycle tracking
onMounted(() => {
  isMounted.value = true;
});

onBeforeUnmount(() => {
  isUnmounting.value = true;
});

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
          console.warn('IciclePlot: Invalid ground truth composition structure, falling back to predicted color');
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
          console.warn('IciclePlot: Using fallback ground truth color from color map');
        }
        return firstGTColor;
      }
    }
    
    // Final fallback to predicted color with warning
    if (process.env.NODE_ENV === 'development') {
      console.warn('IciclePlot: No valid ground truth color found, falling back to predicted color');
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

// Convert tree data to D3 hierarchy format for icicle plot
function convertTreeToIcicleFormat(treeData: any): TreeNode | null {
  const standardTree = convertTreeToStandardFormat(treeData);
  
  if (!standardTree) {
    console.warn('[IciclePlot] Failed to convert tree to standard format');
    return null;
  }
  
  // Validate tree structure
  if (!validateTreePointIndices(standardTree)) {
    console.warn('[IciclePlot] Tree validation failed, but continuing with available data');
  }
  
  return standardTree;
}

// Simple event handlers matching dendrogram approach
function createEventHandlers() {
    const handleMouseOver = function(this: any, event: any, d: any) {
    // Early exit if component is unmounting
    if (isUnmounting.value || !isMounted.value) {
      return;
    }

    // Early throttling check to avoid expensive operations
    const now = performance.now();
    if (now - lastHoverTime < HOVER_THROTTLE_MS) {
      // Still update hover state but skip expensive operations
      currentHoveredElement = this;
      isHovering = true;
      return;
    }
    
    lastHoverTime = now;

    // Update hover state tracking
    currentHoveredElement = this;
    isHovering = true;

    // Cancel any pending clear highlight timeout since we're hovering
    if (clearHighlightTimeout) {
      clearTimeout(clearHighlightTimeout);
      clearHighlightTimeout = null;
    }

    // Cache expensive DOM selection
    const rect = d3.select(this);
    const nodeId = d.data.id;
    const isSelected = props.selectedNodes.has(nodeId);
    
    // Only apply styling to unselected nodes
    if (!isSelected) {
      // Use cached hover style or calculate and cache it
      let hoverStyle = hoverStyleCache.get(nodeId);
      if (!hoverStyle) {
        const currentFill = rect.style('fill') || rect.attr('fill') || '#cccccc';
        hoverStyle = scientificColors.getHighlightStyle(currentFill);
        hoverStyleCache.set(nodeId, hoverStyle);
      }
      
      // Batch style changes for better performance
      rect
        .style('opacity', 1.0)
        .style('stroke-width', 2)
        .style('stroke', hoverStyle.strokeColor);
    }

    // Throttled hover emission using requestAnimationFrame
    if (hoverAnimationFrame) {
      cancelAnimationFrame(hoverAnimationFrame);
    }
    
    hoverAnimationFrame = requestAnimationFrame(() => {
      handleHoverEmission(d);
      hoverAnimationFrame = null;
    });

    // Debounced tooltip operations
    if (hideTooltipTimeout) {
      clearTimeout(hideTooltipTimeout);
      hideTooltipTimeout = null;
    }
    
    // Show appropriate tooltip with slight delay to avoid rapid changes
    setTimeout(() => {
      if (currentHoveredElement === this && isHovering) {
        if (d.data.color_composition && d.data.color_composition.length > 1) {
          showTooltip(event, d.data.color_composition, d.data.ground_truth_composition);
        } else {
          showSimpleTooltip(event, d);
        }
      }
    }, 50); // 50ms delay for tooltip stability
  };

  const handleMouseOut = function(this: any, event: any, d: any) {
    // Early exit if component is unmounting
    if (isUnmounting.value || !isMounted.value) {
      return;
    }

    // Check if we're truly leaving the current element
    if (currentHoveredElement === this) {
      isHovering = false;
      currentHoveredElement = null;
    }

    // Optimize performance: early exit for selected nodes
    const nodeId = d.data.id;
    const isSelected = props.selectedNodes.has(nodeId);
    
    // Only reset styling for unselected nodes
    if (!isSelected) {
      // Cache DOM selection for better performance
      const rect = d3.select(this);
      
      // Batch style changes for better performance
      rect
        .style('opacity', 0.8)
        .style('stroke-width', 0.5)
        .style('stroke', '#ffffff')
        .style('filter', null);
    }
    // Selected nodes keep their selection styling

    // Cancel any pending hover animation frame
    if (hoverAnimationFrame) {
      cancelAnimationFrame(hoverAnimationFrame);
      hoverAnimationFrame = null;
    }

    // Use longer delay for highlight clearing to prevent flickering when moving between adjacent elements
    if (clearHighlightTimeout) {
      clearTimeout(clearHighlightTimeout);
    }
    clearHighlightTimeout = setTimeout(() => {
      // Only clear highlights if we're truly not hovering over any element
      if (isHovering || isUnmounting.value || !isMounted.value) {
        return;
      }
      
      try {
        // Use safe emit to prevent Vue reactivity errors
        safeEmit('update:highlightedPoints', []);
      } catch (error) {
        // Silent error handling - continue execution
        console.warn('[IciclePlot] Error in highlight clear:', error);
      }
      clearHighlightTimeout = null;
    }, 100); // Reduced delay for better performance while maintaining stability

    // Optimized debounce for tooltip hiding
    if (hideTooltipTimeout) {
      clearTimeout(hideTooltipTimeout);
    }
    hideTooltipTimeout = setTimeout(() => {
      hideTooltip();
      hideTooltipTimeout = null;
    }, 25); // Optimized delay for responsive tooltip hiding
  };

  const handleMouseMove = function(this: any, event: any, d: any) {
    // Early exit if component is unmounting
    if (isUnmounting.value || !isMounted.value) {
      return;
    }

    // Ensure hover state is maintained during mouse movement
    if (currentHoveredElement === this) {
      isHovering = true;
      
      // Cancel any pending clear highlight timeout since we're still hovering
      if (clearHighlightTimeout) {
        clearTimeout(clearHighlightTimeout);
        clearHighlightTimeout = null;
      }
    }

    // Update tooltip position if visible
    if (tooltip && tooltip.style('opacity') > 0) {
      tooltip
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    }
  };

  return { handleMouseOver, handleMouseOut, handleMouseMove };
}

// Apply selection styling to rectangles based on selectedNodes prop
function applySelectionStyling(rectSelection: any) {
  rectSelection.each(function(d: any) {
    const rect = d3.select(this);
    const nodeId = d.data.id;
    const isSelected = props.selectedNodes.has(nodeId);
    
    if (isSelected) {
      // Apply selection styling
      rect
        .style('stroke', '#ff6b35')
        .style('stroke-width', 4)
        .style('filter', 'drop-shadow(0 0 6px rgba(255, 107, 53, 0.8))');
    } else {
      // Ensure default styling
      rect
        .style('stroke', '#ffffff')
        .style('stroke-width', 0.5)
        .style('filter', null);
    }
  });
}

function renderIciclePlot() {
  if (!icicleContainer.value || !props.tree || renderInProgress || !isMounted.value || isUnmounting.value) return;

  renderInProgress = true;
  const renderStart = performance.now();
  
  // Clear hover style cache on re-render to prevent stale data
  hoverStyleCache.clear();

  try {
    const container = d3.select(icicleContainer.value);
    
    // Comprehensive cleanup of existing elements and event listeners
    if (svg) {
      // Remove all event listeners with proper D3 cleanup
      svg.selectAll('.icicle-cell')
        .on('mouseenter', null)
        .on('mouseleave', null)
        .on('mouseover', null)
        .on('mouseout', null)
        .on('mousemove', null)
        .on('click', null);
      
      // Clean up any existing highlight overlays
      svg.selectAll('.highlight-overlay').remove();
      svg.selectAll('.highlight-glow').remove();
    }
    
    container.selectAll('*').remove();
    
    // Reset references and state
    svg = null;
    icicleGroup = null;

    const treeData = convertTreeToIcicleFormat(props.tree);
    if (!treeData) return;

    // Define margins first
    const margin = { top: 2, right: 2, bottom: 2, left: 2 };
    const innerWidth = Math.max(0, props.width - margin.left - margin.right);
    const innerHeight = Math.max(0, props.height - margin.top - margin.bottom);

    // Create SVG with performance optimizations
    svg = container.append('svg')
      .attr('id', 'cluster-icicle-plot')
      .attr('width', props.width)
      .attr('height', props.height)
      .style('background-color', '#ffffff')
      .style('shape-rendering', 'crispEdges') // Optimize rendering
      .on('click', (event: any) => {
        // Clear selections when clicking on empty background
        if (event.target === svg.node() || event.target.tagName === 'svg') {
          emit('clearSelections');
        }
      });

    // Add SVG filter definitions for better highlighting effects
    const defs = svg.append('defs');
    
    // Enhanced glow filter that doesn't cause size reduction
    const glowFilter = defs.append('filter')
      .attr('id', 'icicle-glow-filter')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');
    
    // Create multiple glow layers for better effect
    glowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '3')
      .attr('result', 'glow1');
    
    glowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '6')
      .attr('result', 'glow2');
    
    // Merge the glows
    const feMerge = glowFilter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'glow2');
    feMerge.append('feMergeNode').attr('in', 'glow1');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Stronger glow filter for small nodes that need enhanced visibility
    const strongGlowFilter = defs.append('filter')
      .attr('id', 'icicle-strong-glow-filter')
      .attr('x', '-100%')
      .attr('y', '-100%')
      .attr('width', '300%')
      .attr('height', '300%');
    
    // Create stronger glow layers for small nodes
    strongGlowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '4')
      .attr('result', 'strongGlow1');
    
    strongGlowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '8')
      .attr('result', 'strongGlow2');

    strongGlowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '12')
      .attr('result', 'strongGlow3');
    
    // Merge the stronger glows
    const strongMerge = strongGlowFilter.append('feMerge');
    strongMerge.append('feMergeNode').attr('in', 'strongGlow3');
    strongMerge.append('feMergeNode').attr('in', 'strongGlow2');
    strongMerge.append('feMergeNode').attr('in', 'strongGlow1');
    strongMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Create icicle group with proper margins
    icicleGroup = svg.append('g')
      .attr('class', 'icicle-group')
      .attr('transform', `translate(${margin.left}, ${margin.top})`);

    // Create D3 hierarchy with meaningful node values for proper icicle distribution
    const root = d3.hierarchy(treeData)
      .sum((d: any) => {
        // Use point count for more meaningful space distribution
        const pointIndices = extractPointIndices(d);
        return Math.max(1, pointIndices ? pointIndices.length : 1);
      })
      .sort((a: any, b: any) => (b.value || 0) - (a.value || 0));

    // Calculate tree depth for equal height distribution
    const maxDepth = root.height;
    const levelHeight = maxDepth > 0 ? innerHeight / (maxDepth + 1) : innerHeight;
    
    // Create standard partition layout with no padding to ensure children fill parent width
    const partition = d3.partition<TreeNode>()
      .size([innerWidth, innerHeight])
      .padding(0) // No padding to ensure proper parent-child width relationship
      .round(false); // Don't round to avoid width distribution issues

    // Apply partition layout
    partition(root);
    
    // Fix icicle layout to ensure children properly fill parent width
    const fixChildWidths = (node: any) => {
      if (node.children && node.children.length > 0) {
        // Calculate total value of children
        const totalChildValue = node.children.reduce((sum: number, child: any) => sum + (child.value || 0), 0);
        
        if (totalChildValue > 0) {
          // Redistribute children to fill parent width exactly
          let currentX = node.x0;
          const parentWidth = node.x1 - node.x0;
          
          node.children.forEach((child: any, index: number) => {
            const childRatio = (child.value || 0) / totalChildValue;
            const childWidth = parentWidth * childRatio;
            
            child.x0 = currentX;
            child.x1 = currentX + childWidth;
            
            // Ensure last child exactly reaches parent's right edge
            if (index === node.children.length - 1) {
              child.x1 = node.x1;
            }
            
            currentX = child.x1;
            
            // Recursively fix children
            fixChildWidths(child);
          });
        }
      }
    };
    
    // Start fixing from root
    fixChildWidths(root);
    
    // Adjust heights to be equal per level
    root.descendants().forEach((d: any) => {
      const depth = d.depth;
      d.y0 = depth * levelHeight;
      d.y1 = (depth + 1) * levelHeight;
    });

    // Create optimized color scale
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    // Get all nodes (including internal nodes) - remove problematic filtering
    // that was causing nodes to be excluded and creating dead space
    const nodes = root.descendants().filter((d: any) => {
      const width = d.x1 - d.x0;
      const height = d.y1 - d.y0;
      // Only filter out nodes that are too small to be meaningful
      return width > 0.5 && height > 0.5;
    });


    // Create simple event handlers
    const { handleMouseOver, handleMouseOut, handleMouseMove } = createEventHandlers();

    // Create rectangles for each node with optimized rendering
    const cells = icicleGroup.selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'icicle-cell');

    // Add rectangles with proper coordinate usage (no clamping that creates dead space)
    cells.append('rect')
      .attr('x', (d: any) => d.x0)
      .attr('y', (d: any) => d.y0)
      .attr('width', (d: any) => d.x1 - d.x0)
      .attr('height', (d: any) => d.y1 - d.y0)
      .style('fill', (d: any) => {
        // Use getNodeColor function or fallback to depth-based coloring
        const nodeColor = getNodeColor(d.data);
        return nodeColor !== '#cccccc' ? nodeColor : colorScale(d.depth.toString());
      })
      .style('stroke', '#ffffff')
      .style('stroke-width', 0.5)
      .style('cursor', 'pointer')
      .style('opacity', 0.8)
      // Attach optimized event handlers with better hover detection
      .on('mouseenter', handleMouseOver)
      .on('mouseleave', handleMouseOut)
      .on('mousemove', handleMouseMove)
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
          
          console.log(`[ICICLE] Shift+click on node ${nodeId}, currently selected: ${isCurrentlySelected}`);
          
          // Emit selection event
          emit('nodeSelected', {
            nodeId: nodeId,
            points: pointIndices || [],
            isSelected: !isCurrentlySelected
          });
          
          // Update visual state immediately
          const rect = d3.select(event.currentTarget);
          if (!isCurrentlySelected) {
            // Add selection styling
            rect
              .style('stroke', '#ff6b35')
              .style('stroke-width', 4)
              .style('filter', 'drop-shadow(0 0 6px rgba(255, 107, 53, 0.8))');
          } else {
            // Remove selection styling
            rect
              .style('stroke', '#ffffff')
              .style('stroke-width', 0.5)
              .style('filter', null);
          }
          
          return; // Don't trigger any expand/collapse behavior for icicle
        }
        // Normal click behavior can be added here if needed
      });

    // Apply selection styling to rectangles
    const rectangles = cells.selectAll('rect');
    applySelectionStyling(rectangles);

    // Text labels removed for cleaner visualization

    const renderEnd = performance.now();
    const renderTime = renderEnd - renderStart;
    
    renderInProgress = false;
  } catch (error) {
    console.error('[IciclePlot] Error during rendering:', error);
    renderInProgress = false;
  }
}

// Enhanced tooltip functions with robust error handling and race condition prevention
function showTooltip(event: any, colorComposition: any[], groundTruthComposition?: any[]) {
  if (!isMounted.value || isUnmounting.value) {
    return;
  }
  
  try {
    // Immediate cleanup of any existing tooltip
    forceHideTooltip();
    
    tooltip = d3.select('body').append('div')
      .attr('class', 'icicle-tooltip')
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.8)')
      .style('color', 'white')
      .style('padding', '8px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', '1000')
      .style('max-width', '250px')
      .style('word-wrap', 'break-word');

    const predictedContent = colorComposition.map(comp => 
      `<div style="margin: 2px 0; display: flex; align-items: center;">
        <span style="display: inline-block; width: 12px; height: 12px; background: ${comp.color}; margin-right: 5px; border-radius: 2px;"></span>
        <span>${comp.label}: ${comp.count} (${(comp.proportion * 100).toFixed(1)}%)</span>
      </div>`
    ).join('');

    let content = `<strong>Predicted Clusters:</strong><br/>${predictedContent}`;
    
    if (groundTruthComposition && groundTruthComposition.length > 0) {
      const groundTruthContent = groundTruthComposition.map(comp => 
        `<div style="margin: 2px 0; display: flex; align-items: center;">
          <span style="display: inline-block; width: 12px; height: 12px; background: ${comp.color}; margin-right: 5px; border-radius: 2px;"></span>
          <span>${comp.label}: ${comp.count} (${(comp.proportion * 100).toFixed(1)}%)</span>
        </div>`
      ).join('');
      
      content += `<br/><strong>Ground Truth:</strong><br/>${groundTruthContent}`;
    }

    tooltip.html(content)
      .style('left', (event.pageX + 10) + 'px')
      .style('top', (event.pageY - 10) + 'px')
      .transition()
      .duration(100)
      .style('opacity', 1);
  } catch (error) {
    console.warn('[IciclePlot] Error showing tooltip:', error);
  }
}

function showSimpleTooltip(event: any, d: any) {
  if (!isMounted.value || isUnmounting.value) {
    return;
  }
  
  try {
    // Immediate cleanup of any existing tooltip
    forceHideTooltip();
    
    tooltip = d3.select('body').append('div')
      .attr('class', 'icicle-tooltip')
      .style('position', 'absolute')
      .style('background', 'rgba(0, 0, 0, 0.8)')
      .style('color', 'white')
      .style('padding', '8px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('z-index', '1000')
      .style('max-width', '200px')
      .style('word-wrap', 'break-word');

    const label = d.data.label !== undefined ? String(d.data.label) : (d.data.name || (d.data.id === '-1' ? 'internal node' : d.data.id) || 'Node');
    const pointCount = d.data.pointIndices ? d.data.pointIndices.length : (extractPointIndices(d.data).length || 0);
    const nodeType = d.data._is_summary ? 'Summary' : ((!d.data.children || d.data.children.length === 0) ? 'Leaf' : 'Internal');
    const nodeValue = d.value || 0;

    tooltip.html(`
      <strong>${label}</strong><br/>
      Type: ${nodeType}<br/>
      Points: ${pointCount}<br/>
      Value: ${nodeValue}<br/>
      Depth: ${d.depth}
    `)
      .style('left', (event.pageX + 10) + 'px')
      .style('top', (event.pageY - 10) + 'px')
      .transition()
      .duration(100)
      .style('opacity', 1);
  } catch (error) {
    console.warn('[IciclePlot] Error showing simple tooltip:', error);
  }
}

function hideTooltip() {
  if (tooltip) {
    // Immediately interrupt any ongoing transitions to prevent race conditions
    tooltip.interrupt();
    
    // Faster transition for better responsiveness
    tooltip.transition()
      .duration(100)
      .style('opacity', 0)
      .on('end', () => {
        if (tooltip) {
          tooltip.remove();
          tooltip = null;
        }
      });
  }
}

// Force immediate tooltip cleanup without transitions
function forceHideTooltip() {
  if (tooltip) {
    tooltip.interrupt();
    tooltip.remove();
    tooltip = null;
  }
  // Also clean up any orphaned tooltips
  d3.selectAll('.icicle-tooltip').remove();
}

// Optimized resize handler with throttling
let resizeTimeout: number | null = null;
const handleResize = () => {
  if (!isMounted.value || isUnmounting.value) {
    return;
  }
  
  if (resizeTimeout) {
    clearTimeout(resizeTimeout);
  }
  
  resizeTimeout = window.setTimeout(() => {
    if (svg && props.tree?.root && !isUnmounting.value) {
      svg.attr('width', props.width)
         .attr('height', props.height);
      renderIciclePlot();
    }
    resizeTimeout = null;
  }, 150); // Debounce resize events
};

// Optimized watchers with better performance
watch(() => props.tree, (newVal, oldVal) => {
  // Skip unnecessary re-renders
  if (newVal === oldVal || !isMounted.value || isUnmounting.value) return;
  
  if (newVal?.root) {
    // Small delay to ensure DOM is ready
    nextTick(() => {
      if (!isUnmounting.value) {
        setTimeout(() => {
          if (!isUnmounting.value) {
            renderIciclePlot();
          }
        }, 50);
      }
    });
  }
}, { deep: true }); // Deep watch to detect ground truth color changes

watch(() => [props.width, props.height, props.selectedColorBy], ([newWidth, newHeight, newColorBy], [oldWidth, oldHeight, oldColorBy]) => {
  // Skip if dimensions haven't actually changed or component is unmounting
  if ((newWidth === oldWidth && newHeight === oldHeight && newColorBy === oldColorBy) || !isMounted.value || isUnmounting.value) return;
  
  if (props.tree?.root && svg) {
    handleResize();
  }
}, { immediate: false });

watch(() => props.highlightedNode, (newHighlightedNode) => {
  if (newHighlightedNode && svg && isMounted.value && !isUnmounting.value) {
    highlightNodeInIcicle(newHighlightedNode);
  }
}, { deep: true });

// Helper function to check if a point is within container bounds with margin
function isWithinBounds(x: number, y: number, margin: number = 20): boolean {
  return x >= margin && 
         y >= margin && 
         x <= (props.width - margin) && 
         y <= (props.height - margin);
}

// Helper function to calculate available space in each direction
function calculateAvailableSpace(nodeCenterX: number, nodeCenterY: number, nodeData: any) {
  return {
    top: nodeData.y0,
    bottom: props.height - nodeData.y1,
    left: nodeData.x0,
    right: props.width - nodeData.x1
  };
}

// Create a pointing arrow to guide users to the highlighted node
function createPointingArrow(nodeData: any, highlightStyle: any, isSmallNode: boolean) {
  if (!icicleGroup || !nodeData) return;
  
  const nodeWidth = nodeData.x1 - nodeData.x0;
  const nodeHeight = nodeData.y1 - nodeData.y0;
  const nodeCenterX = nodeData.x0 + nodeWidth / 2;
  const nodeCenterY = nodeData.y0 + nodeHeight / 2;
  
  // Calculate available space in each direction
  const availableSpace = calculateAvailableSpace(nodeCenterX, nodeCenterY, nodeData);
  
  // Minimum space required for arrow and text
  const minArrowSpace = 60; // Space needed for arrow line + text
  
  // Determine the best direction based on available space
  const directions = [
    { name: 'top', space: availableSpace.top, priority: 1 },
    { name: 'bottom', space: availableSpace.bottom, priority: 2 },
    { name: 'left', space: availableSpace.left, priority: 3 },
    { name: 'right', space: availableSpace.right, priority: 4 }
  ];
  
  // Sort by available space (descending) and then by priority
  directions.sort((a, b) => {
    if (b.space !== a.space) return b.space - a.space;
    return a.priority - b.priority;
  });
  
  // Find the first direction with sufficient space
  let chosenDirection = directions.find(d => d.space >= minArrowSpace)?.name || directions[0].name;
  
  // Calculate arrow positions based on chosen direction and available space
  let arrowStartX, arrowStartY, arrowEndX, arrowEndY, arrowDirection;
  
  switch (chosenDirection) {
    case 'top':
      // Arrow points down from above
      const topOffset = Math.min(40, Math.max(25, availableSpace.top - 25));
      arrowStartX = nodeCenterX;
      arrowStartY = nodeData.y0 - topOffset;
      arrowEndX = nodeCenterX;
      arrowEndY = nodeData.y0 - 10;
      arrowDirection = 'down';
      
      // Ensure arrow start is within bounds
      if (!isWithinBounds(arrowStartX, arrowStartY)) {
        arrowStartY = Math.max(25, arrowStartY);
      }
      break;
      
    case 'bottom':
      // Arrow points up from below
      const bottomOffset = Math.min(40, Math.max(25, availableSpace.bottom - 25));
      arrowStartX = nodeCenterX;
      arrowStartY = nodeData.y1 + bottomOffset;
      arrowEndX = nodeCenterX;
      arrowEndY = nodeData.y1 + 10;
      arrowDirection = 'up';
      
      // Ensure arrow start is within bounds
      if (!isWithinBounds(arrowStartX, arrowStartY)) {
        arrowStartY = Math.min(props.height - 25, arrowStartY);
      }
      break;
      
    case 'left':
      // Arrow points right from left
      const leftOffset = Math.min(50, Math.max(30, availableSpace.left - 30));
      arrowStartX = nodeData.x0 - leftOffset;
      arrowStartY = nodeCenterY;
      arrowEndX = nodeData.x0 - 15;
      arrowEndY = nodeCenterY;
      arrowDirection = 'right';
      
      // Ensure arrow start is within bounds
      if (!isWithinBounds(arrowStartX, arrowStartY)) {
        arrowStartX = Math.max(25, arrowStartX);
      }
      break;
      
    case 'right':
    default:
      // Arrow points left from right
      const rightOffset = Math.min(50, Math.max(30, availableSpace.right - 30));
      arrowStartX = nodeData.x1 + rightOffset;
      arrowStartY = nodeCenterY;
      arrowEndX = nodeData.x1 + 15;
      arrowEndY = nodeCenterY;
      arrowDirection = 'left';
      
      // Ensure arrow start is within bounds
      if (!isWithinBounds(arrowStartX, arrowStartY)) {
        arrowStartX = Math.min(props.width - 25, arrowStartX);
      }
      break;
  }
  
  // Create arrow line
  const arrowLine = icicleGroup.append('line')
    .attr('class', 'highlight-arrow')
    .attr('x1', arrowStartX)
    .attr('y1', arrowStartY)
    .attr('x2', arrowEndX)
    .attr('y2', arrowEndY)
    .style('stroke', highlightStyle.strokeColor)
    .style('stroke-width', '3px')
    .style('stroke-linecap', 'round')
    .style('opacity', 0);
  
  // Create arrowhead
  const arrowSize = isSmallNode ? 8 : 10;
  let arrowPath = '';
  
  switch (arrowDirection) {
    case 'down':
      arrowPath = `M${arrowEndX},${arrowEndY} L${arrowEndX - arrowSize/2},${arrowEndY - arrowSize} L${arrowEndX + arrowSize/2},${arrowEndY - arrowSize} Z`;
      break;
    case 'up':
      arrowPath = `M${arrowEndX},${arrowEndY} L${arrowEndX - arrowSize/2},${arrowEndY + arrowSize} L${arrowEndX + arrowSize/2},${arrowEndY + arrowSize} Z`;
      break;
    case 'right':
      arrowPath = `M${arrowEndX},${arrowEndY} L${arrowEndX - arrowSize},${arrowEndY - arrowSize/2} L${arrowEndX - arrowSize},${arrowEndY + arrowSize/2} Z`;
      break;
    case 'left':
      arrowPath = `M${arrowEndX},${arrowEndY} L${arrowEndX + arrowSize},${arrowEndY - arrowSize/2} L${arrowEndX + arrowSize},${arrowEndY + arrowSize/2} Z`;
      break;
  }
  
  const arrowHead = icicleGroup.append('path')
    .attr('class', 'highlight-arrow')
    .attr('d', arrowPath)
    .style('fill', highlightStyle.strokeColor)
    .style('stroke', highlightStyle.strokeColor)
    .style('stroke-width', '1px')
    .style('opacity', 0);
  
  // Add text label near the arrow with boundary checking
  const textOffset = 15;
  const textWidth = 100; // Approximate width of "Selected Point" text
  const textHeight = 16; // Approximate height of text
  let textX, textY, textAnchor = 'middle';
  
  // Calculate initial text position based on arrow direction
  if (arrowDirection === 'down') {
    textX = arrowStartX;
    textY = arrowStartY - textOffset;
  } else if (arrowDirection === 'up') {
    textX = arrowStartX;
    textY = arrowStartY + textOffset + textHeight;
  } else if (arrowDirection === 'right') {
    textX = arrowStartX - textOffset;
    textY = arrowStartY + 5;
    textAnchor = 'end';
  } else { // left
    textX = arrowStartX + textOffset;
    textY = arrowStartY + 5;
    textAnchor = 'start';
  }
  
  // Adjust text position to ensure it stays within bounds
  const textMargin = 10;
  
  // Horizontal boundary checking
  if (textAnchor === 'middle') {
    // For centered text, check both sides
    if (textX - textWidth/2 < textMargin) {
      textX = textMargin + textWidth/2;
    } else if (textX + textWidth/2 > props.width - textMargin) {
      textX = props.width - textMargin - textWidth/2;
    }
  } else if (textAnchor === 'start') {
    // For left-aligned text
    if (textX + textWidth > props.width - textMargin) {
      textX = props.width - textMargin - textWidth;
      textAnchor = 'end';
    }
  } else if (textAnchor === 'end') {
    // For right-aligned text
    if (textX - textWidth < textMargin) {
      textX = textMargin + textWidth;
      textAnchor = 'start';
    }
  }
  
  // Vertical boundary checking
  if (textY < textMargin + textHeight) {
    textY = textMargin + textHeight;
  } else if (textY > props.height - textMargin) {
    textY = props.height - textMargin;
  }
  
  const arrowText = icicleGroup.append('text')
    .attr('class', 'arrow-text')
    .attr('x', textX)
    .attr('y', textY)
    .style('fill', '#000000')  // Always black text for better readability
    .style('font-family', 'Arial, serif')
    .style('font-size', '12px')
    .style('font-weight', 'bold')
    .style('text-anchor', textAnchor)
    .style('opacity', 0)
    .text('Selected Point');
  
  // Animate arrow appearance
  arrowLine
    .transition()
    .duration(500)
    .style('opacity', 0.9);
    
  arrowHead
    .transition()
    .duration(500)
    .style('opacity', 0.9);
  
  arrowText
    .transition()
    .duration(500)
    .style('opacity', 0.8);
  
  // Add pulsing animation to the arrow
  function pulseArrow() {
    arrowLine
      .transition()
      .duration(1000)
      .style('opacity', 0.5)
      .transition()
      .duration(1000)
      .style('opacity', 0.9)
      .on('end', pulseArrow);
    
    arrowHead
      .transition()
      .duration(1000)
      .style('opacity', 0.5)
      .transition()
      .duration(1000)
      .style('opacity', 0.9);
  }
  
  // Start pulsing after initial animation
  setTimeout(pulseArrow, 500);
}

function highlightNodeInIcicle(highlightedNodeInfo: any) {
  if (!svg || !icicleGroup || !highlightedNodeInfo || !isMounted.value || isUnmounting.value) {
    return;
  }
  
  
  const { nodeId } = highlightedNodeInfo;
  
  // Clear any existing timeout immediately - this allows new arrows to appear on subsequent clicks
  if (highlightTimeout) {
    clearTimeout(highlightTimeout);
    highlightTimeout = null;
  }
  
  // COMPLETELY clear any existing highlights - be very explicit
  icicleGroup.selectAll('rect')
    .style('stroke', '#fff')
    .style('stroke-width', 0.5)
    .style('filter', null)
    .style('stroke-dasharray', null)
    .style('stroke-dashoffset', null)
    .style('fill-opacity', null)
    .interrupt(); // Stop any ongoing animations
  
  // Remove any existing highlight elements
  icicleGroup.selectAll('.highlight-overlay').remove();
  icicleGroup.selectAll('.highlight-glow').remove();
  icicleGroup.selectAll('.highlight-label-group').remove();
  icicleGroup.selectAll('.highlight-ray').remove();
  icicleGroup.selectAll('.highlight-arrow').remove();
  icicleGroup.selectAll('.arrow-text').remove();
  
  // Find all nodes with the target ID with safe data access
  let candidateNodes;
  try {
    candidateNodes = icicleGroup.selectAll('rect')
      .filter((d: any) => d && d.data && d.data.id === nodeId);
  } catch (error) {
    console.warn('[ICICLE] Error filtering nodes by ID:', error);
    return;
  }
  
  if (!candidateNodes.empty()) {
    // If multiple nodes have the same ID, select the one with the highest depth (deepest)
    let targetNode = null;
    let targetData = null;
    let maxDepth = -1;
    
    try {
      candidateNodes.each(function(d: any) {
        if (!d || typeof d.depth === 'undefined') {
          console.warn('[ICICLE] Invalid node data encountered:', d);
          return;
        }
        const nodeDepth = d.depth || 0;
        if (nodeDepth > maxDepth) {
          maxDepth = nodeDepth;
          targetNode = this;
          targetData = d;
        }
      });
    } catch (error) {
      console.warn('[ICICLE] Error iterating through candidate nodes:', error);
      return;
    }
    
    if (targetNode && targetData) {
      // Get the background color of the node to determine best highlight color
      const nodeElement = d3.select(targetNode);
      const backgroundColor = nodeElement.style('fill') || nodeElement.attr('fill') || '#cccccc';
      
      // Calculate intelligent highlight style based on background color
      const highlightStyle = scientificColors.getHighlightStyle(backgroundColor);
      
      // Calculate node dimensions for enhanced visibility
      const nodeWidth = (targetData as any).x1 - (targetData as any).x0;
      const nodeHeight = (targetData as any).y1 - (targetData as any).y0;
      const nodeArea = nodeWidth * nodeHeight;
      const isSmallNode = nodeArea < 2000; // Threshold for small nodes
      
      // Enhanced highlighting for better visibility, especially for small nodes
      const strokeWidth = isSmallNode ? highlightStyle.strokeWidth + 2 : highlightStyle.strokeWidth + 1;
      const glowIntensity = isSmallNode ? 'url(#icicle-strong-glow-filter)' : 'url(#icicle-glow-filter)';
      
      // Create a highlight overlay that sits on top of the original rectangle
      const highlightOverlay = icicleGroup.append('rect')
        .attr('class', 'highlight-overlay')
        .attr('x', (targetData as any).x0)
        .attr('y', (targetData as any).y0)
        .attr('width', nodeWidth)
        .attr('height', nodeHeight)
        .style('fill', 'none')
        .style('stroke', highlightStyle.strokeColor)
        .style('stroke-width', `${strokeWidth}px`)
        .style('stroke-dasharray', isSmallNode ? '6,3' : '8,4')
        .style('stroke-dashoffset', 0)
        .style('filter', glowIntensity)
        .style('pointer-events', 'none')
        .style('opacity', 0.95);
      
      // For very small nodes, add an additional outer glow rectangle
      if (isSmallNode) {
        const expandBy = Math.max(3, Math.min(nodeWidth * 0.3, nodeHeight * 0.3));
        const outerGlowRect = icicleGroup.append('rect')
          .attr('class', 'highlight-glow')
          .attr('x', (targetData as any).x0 - expandBy)
          .attr('y', (targetData as any).y0 - expandBy)
          .attr('width', nodeWidth + (expandBy * 2))
          .attr('height', nodeHeight + (expandBy * 2))
          .style('fill', 'none')
          .style('stroke', highlightStyle.strokeColor)
          .style('stroke-width', '2px')
          .style('stroke-opacity', 0.4)
          .style('filter', `drop-shadow(0 0 8px ${highlightStyle.glowColor})`)
          .style('pointer-events', 'none');
          
        // Add breathing animation to outer glow
        outerGlowRect
          .transition()
          .duration(2000)
          .style('stroke-opacity', 0.3)
          .transition()
          .duration(2000)
          .style('stroke-opacity', 0.6)
          .on('end', function repeatGlow() {
            d3.select(this)
              .transition()
              .duration(2000)
              .style('stroke-opacity', 0.3)
              .transition()
              .duration(2000)
              .style('stroke-opacity', 0.6)
              .on('end', repeatGlow);
          });
      }
      
      // Add pulsing animation to the main overlay
      highlightOverlay
        .transition()
        .duration(1500)
        .style('stroke-dashoffset', isSmallNode ? -18 : -24)
        .on('end', function repeat() {
          d3.select(this)
            .transition()
            .duration(1500)
            .style('stroke-dashoffset', isSmallNode ? -36 : -48)
            .on('end', repeat);
        });
      
      // Optional: Add a subtle glow effect around the node without affecting its size
      const glowOverlay = icicleGroup.append('rect')
        .attr('class', 'highlight-glow')
        .attr('x', (targetData as any).x0 - 2)
        .attr('y', (targetData as any).y0 - 2)
        .attr('width', ((targetData as any).x1 - (targetData as any).x0) + 4)
        .attr('height', ((targetData as any).y1 - (targetData as any).y0) + 4)
        .style('fill', 'none')
        .style('stroke', '#000000')
        .style('stroke-width', '1px')
        .style('opacity', 0.3)
        .style('filter', 'blur(2px)')
        .style('pointer-events', 'none');
      
      // Add pointing arrow for better user guidance
      createPointingArrow(targetData, highlightStyle, isSmallNode);
      
      // Set timeout to clear highlight after 5 seconds
      highlightTimeout = setTimeout(() => {
        icicleGroup.selectAll('.highlight-overlay').remove();
        icicleGroup.selectAll('.highlight-glow').remove();
        icicleGroup.selectAll('.highlight-arrow').remove();
        icicleGroup.selectAll('.arrow-text').remove();
        highlightTimeout = null;
      }, 5000);
    }
  } else {
    console.warn('[ICICLE] Target node not found in current view:', nodeId);
    console.log('[ICICLE] Falling back to find deepest visible node containing the point...');
    
    // Fallback: find the deepest visible node that contains this point
    if (highlightedNodeInfo.pointIndex !== undefined) {
      const pointIndex = highlightedNodeInfo.pointIndex;
      const allVisibleNodes = icicleGroup.selectAll('rect').data();
      
      let fallbackNode = null;
      let maxDepth = -1;
      
      // Find the deepest visible node that contains this point
      for (const nodeData of allVisibleNodes) {
        const nodeIndices = extractPointIndices(nodeData.data);
        if (nodeIndices.includes(pointIndex)) {
          const nodeDepth = nodeData.depth || 0;
          console.log('[ICICLE] Visible node', nodeData.data.id, 'at depth', nodeDepth, 'contains point', pointIndex);
          
          if (nodeDepth > maxDepth) {
            maxDepth = nodeDepth;
            fallbackNode = nodeData;
          }
        }
      }
      
      if (fallbackNode) {
        console.log('[ICICLE] Found fallback node:', fallbackNode.data.id, 'at depth:', maxDepth);
        
        // Create highlight overlay for fallback node using the same approach
        const highlightOverlay = icicleGroup.append('rect')
          .attr('class', 'highlight-overlay')
          .attr('x', fallbackNode.x0)
          .attr('y', fallbackNode.y0)
          .attr('width', fallbackNode.x1 - fallbackNode.x0)
          .attr('height', fallbackNode.y1 - fallbackNode.y0)
          .style('fill', 'none')
          .style('stroke', '#000000')
          .style('stroke-width', '3px')
          .style('stroke-dasharray', '8,4')
          .style('stroke-dashoffset', 0)
          .style('filter', 'url(#icicle-glow-filter)')
          .style('pointer-events', 'none')
          .style('opacity', 0.9);
        
        // Add pulsing animation
        highlightOverlay
          .transition()
          .duration(1500)
          .style('stroke-dashoffset', -24)
          .on('end', function repeat() {
            d3.select(this)
              .transition()
              .duration(1500)
              .style('stroke-dashoffset', -48)
              .on('end', repeat);
          });
        
        // Add glow effect
        icicleGroup.append('rect')
          .attr('class', 'highlight-glow')
          .attr('x', fallbackNode.x0 - 2)
          .attr('y', fallbackNode.y0 - 2)
          .attr('width', (fallbackNode.x1 - fallbackNode.x0) + 4)
          .attr('height', (fallbackNode.y1 - fallbackNode.y0) + 4)
          .style('fill', 'none')
          .style('stroke', '#000000')
          .style('stroke-width', '1px')
          .style('opacity', 0.3)
          .style('filter', 'blur(2px)')
          .style('pointer-events', 'none');
        
        // Add pointing arrow for fallback node using the same smart positioning
        const fallbackHighlightStyle = {
          strokeColor: '#000000',
          strokeWidth: 3,
          glowColor: 'rgba(0, 0, 0, 0.7)',
          shadowColor: '#000000'
        };
        const nodeArea = (fallbackNode.x1 - fallbackNode.x0) * (fallbackNode.y1 - fallbackNode.y0);
        const isSmallFallbackNode = nodeArea < 2000;
        createPointingArrow(fallbackNode, fallbackHighlightStyle, isSmallFallbackNode);
        
        // Set timeout to clear highlight after 5 seconds
        highlightTimeout = setTimeout(() => {
          icicleGroup.selectAll('.highlight-overlay').remove();
          icicleGroup.selectAll('.highlight-glow').remove();
          icicleGroup.selectAll('.highlight-arrow').remove();
          icicleGroup.selectAll('.arrow-text').remove();
          highlightTimeout = null;
        }, 5000);
      } else {
        console.log('[ICICLE] No visible node found containing point', pointIndex);
      }
    }
    
    // Log available nodes for debugging with safe data access
    try {
      const allRects = icicleGroup.selectAll('rect');
      const rectData = allRects.data();
      const availableNodes = rectData
        .filter((d: any) => d && d.data && d.data.id !== undefined)
        .map((d: any) => d.data.id);
      console.log('[ICICLE] Available node IDs:', availableNodes.slice(0, 10), '... (showing first 10)');
    } catch (error) {
      console.warn('[ICICLE] Error accessing node data for debugging:', error);
    }
  }
}

onMounted(async () => {
  await nextTick();
  
  // Set mounted state
  isMounted.value = true;
  
  // Small delay to ensure proper DOM mounting
  setTimeout(() => {
    if (!isUnmounting.value && props.tree?.root) {
      renderIciclePlot();
    }
  }, 100);
  
  // Add resize listener with throttling
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  // Immediately set unmounting state to prevent any new operations
  isUnmounting.value = true;
  isMounted.value = false;
  
  // Clean up global event listeners
  window.removeEventListener('resize', handleResize);
  
  // Clear performance caches
  hoverStyleCache.clear();
  
  // Clean up timeouts
  if (resizeTimeout) {
    clearTimeout(resizeTimeout);
    resizeTimeout = null;
  }
  
  if (clearHighlightTimeout) {
    clearTimeout(clearHighlightTimeout);
    clearHighlightTimeout = null;
  }
  
  if (hideTooltipTimeout) {
    clearTimeout(hideTooltipTimeout);
    hideTooltipTimeout = null;
  }
  
  if (highlightTimeout) {
    clearTimeout(highlightTimeout);
    highlightTimeout = null;
  }
  
  if (highlightThrottleTimeout) {
    clearTimeout(highlightThrottleTimeout);
    highlightThrottleTimeout = null;
  }
  
  if (hoverAnimationFrame) {
    cancelAnimationFrame(hoverAnimationFrame);
    hoverAnimationFrame = null;
  }

  // Reset hover state
  currentHoveredElement = null;
  isHovering = false;
  
  // Clean up highlight overlays
  if (icicleGroup) {
    try {
      icicleGroup.selectAll('.highlight-overlay').remove();
      icicleGroup.selectAll('.highlight-glow').remove();
    } catch (error) {
      // Ignore errors during cleanup
    }
  }
  
  // Clean up tooltip with enhanced cleanup
  forceHideTooltip();
  
  // Comprehensive D3 cleanup
  if (svg) {
    try {
      // Interrupt any ongoing transitions
      svg.selectAll('*').interrupt();
      
      // Remove all event listeners with namespaces
      svg.selectAll('.icicle-cell')
        .on('mouseover.icicle', null)
        .on('mouseout.icicle', null)
        .on('mousemove.icicle', null)
        .on('mouseenter.icicle', null)
        .on('mouseleave.icicle', null)
        .on('click.icicle', null);
      
      // Remove any zoom or interaction behaviors
      svg.on('.zoom', null)
         .on('.drag', null)
         .on('.brush', null)
         .on('click', null)
         .on('mouseover', null)
         .on('mouseout', null);
      
      // Clear all SVG content
      svg.selectAll('*').remove();
    } catch (error) {
      // Ignore errors during cleanup
    }
    svg = null;
  }
  
  // Clear references and state
  icicleGroup = null;
  renderInProgress = false;
  
  // Clean up container with enhanced cleanup
  if (icicleContainer.value) {
    try {
      const container = d3.select(icicleContainer.value);
      container.selectAll('*').remove();
      // Remove any container event listeners
      container.on('click', null)
               .on('mouseover', null)
               .on('mouseout', null);
    } catch (error) {
      // Ignore errors during cleanup
    }
  }
  
  // Force garbage collection in development
  if (process.env.NODE_ENV === 'development') {
    setTimeout(() => {
      try {
        forceGarbageCollection();
      } catch (error) {
        // Ignore errors during garbage collection
      }
    }, 100);
  }
});
</script>

<style scoped>
.icicle-container {
  background-color: #ffffff;
  overflow: hidden;
  width: 100%;
  height: 100%;
  position: relative;
}

.icicle-svg-container {
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

/* Global tooltip styles for better performance */
:global(.icicle-tooltip) {
  font-family: 'Inter', system-ui, sans-serif;
  line-height: 1.4;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}


/* Reduce motion for users who prefer it */
@media (prefers-reduced-motion: reduce) {
  .icicle-cell rect {
    transition: none !important;
  }
  
  :global(.icicle-tooltip) {
    transition: none !important;
  }
}
</style>
