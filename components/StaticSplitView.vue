<template>
  <div class="static-split-view">
    <!-- Header with labels -->
    <div class="split-header">
      <div class="header-left">
        <span class="header-icon">🏷️</span>
        <span class="header-title">Ground Truth Labels</span>
        <span class="cluster-count">{{ groundTruthClusterCount }} clusters</span>
      </div>
      <div class="header-divider"></div>
      <div class="header-right">
        <span class="header-icon">🔬</span>
        <span class="header-title">Predicted Clusters</span>
        <span class="cluster-count">{{ predictedClusterCount }} clusters</span>
      </div>
    </div>

    <!-- Split content with 50/50 layout -->
    <div class="split-content">
      <!-- Ground Truth Panel (Left) -->
      <div class="panel ground-truth-panel">
        <div class="panel-inner">
          <!-- Tree Visualization -->
          <div class="tree-section" :style="{ height: `${treeHeight}px` }">
            <ClusterDendrogram 
              v-if="treeVisualizationType === 'dendrogram'"
              :key="`gt-dendrogram-${activeRunId}-${selectedOutlierStyle}`"
              :tree="treeData" 
              :width="panelWidth" 
              :height="treeHeight" 
              :nodeData="nodeData"
              :layout="dendrogramLayout"
              selectedColorBy="ground_truth"
              :selectedOutlierStyle="selectedOutlierStyle"
              :highlightedNode="highlightedNodeInTree"
              :selectedNodes="selectedNodes"
              @update:highlightedPoints="handleGroundTruthHighlight"
              @nodeSelected="handleNodeSelection"
              @clearSelections="clearAllSelections"
            />
            <IciclePlot 
              v-else-if="treeVisualizationType === 'icicle'"
              :key="`gt-icicle-${activeRunId}-${selectedOutlierStyle}`"
              :tree="treeData" 
              :width="panelWidth" 
              :height="treeHeight" 
              :nodeData="nodeData"
              selectedColorBy="ground_truth"
              :selectedOutlierStyle="selectedOutlierStyle"
              :highlightedNode="highlightedNodeInTree"
              :selectedNodes="selectedNodes"
              @update:highlightedPoints="handleGroundTruthHighlight"
              @nodeSelected="handleNodeSelection"
              @clearSelections="clearAllSelections"
            />
          </div>

          <!-- Scatter Plot -->
          <div class="scatter-section" :style="{ height: `${scatterHeight}px` }">
            <CanvasScatterPlot 
              :key="`gt-scatter-${activeRunId}`"
              :data="nodeData" 
              :highlightedIndices="computedGroundTruthHighlights" 
              :selectedXAxis="selectedXAxis" 
              :selectedYAxis="selectedYAxis"
              :selectedColorBy="'ground_truth'"
              :selectedOutlierStyle="selectedOutlierStyle"
              :datasetName="datasetName"
              :featureNames="featureNames"
              :width="panelWidth"
              :height="scatterHeight"
              @pointClicked="handlePointClicked"
              @pointHovered="handlePointHovered"
            />
          </div>
        </div>
      </div>

      <!-- Predicted Clusters Panel (Right) -->
      <div class="panel predicted-panel">
        <div class="panel-inner">
          <!-- Tree Visualization -->
          <div class="tree-section" :style="{ height: `${treeHeight}px` }">
            <ClusterDendrogram 
              v-if="treeVisualizationType === 'dendrogram'"
              :key="`pred-dendrogram-${activeRunId}-${selectedOutlierStyle}`"
              :tree="treeData" 
              :width="panelWidth" 
              :height="treeHeight" 
              :nodeData="nodeData"
              :layout="dendrogramLayout"
              selectedColorBy="predicted"
              :selectedOutlierStyle="selectedOutlierStyle"
              :highlightedNode="highlightedNodeInTree"
              :selectedNodes="selectedNodes"
              @update:highlightedPoints="handlePredictedHighlight"
              @nodeSelected="handleNodeSelection"
              @clearSelections="clearAllSelections"
            />
            <IciclePlot 
              v-else-if="treeVisualizationType === 'icicle'"
              :key="`pred-icicle-${activeRunId}-${selectedOutlierStyle}`"
              :tree="treeData" 
              :width="panelWidth" 
              :height="treeHeight" 
              :nodeData="nodeData"
              selectedColorBy="predicted"
              :selectedOutlierStyle="selectedOutlierStyle"
              :highlightedNode="highlightedNodeInTree"
              :selectedNodes="selectedNodes"
              @update:highlightedPoints="handlePredictedHighlight"
              @nodeSelected="handleNodeSelection"
              @clearSelections="clearAllSelections"
            />
          </div>

          <!-- Scatter Plot -->
          <div class="scatter-section" :style="{ height: `${scatterHeight}px` }">
            <CanvasScatterPlot 
              :key="`pred-scatter-${activeRunId}`"
              :data="nodeData" 
              :highlightedIndices="computedPredictedHighlights" 
              :selectedXAxis="selectedXAxis" 
              :selectedYAxis="selectedYAxis"
              :selectedColorBy="'predicted'"
              :selectedOutlierStyle="selectedOutlierStyle"
              :datasetName="datasetName"
              :featureNames="featureNames"
              :width="panelWidth"
              :height="scatterHeight"
              @pointClicked="handlePointClicked"
              @pointHovered="handlePointHovered"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue';
import * as d3 from 'd3';
import ClusterDendrogram from './ClusterDendrogram.vue';
import IciclePlot from './IciclePlot.vue';
import CanvasScatterPlot from './CanvasScatterPlot.vue';

const emit = defineEmits(['update:highlightedPoints', 'pointClicked', 'pointHovered', 'nodesSelected']);

const props = defineProps({
  // Tree data and visualization props
  treeData: Object,
  treeVisualizationType: {
    type: String,
    default: 'icicle'
  },
  dendrogramLayout: {
    type: String,
    default: 'radial'
  },
  
  // Node data
  nodeData: Object,
  
  // Highlighting
  highlightedNodeInTree: Object,
  
  // Scatter plot props
  selectedXAxis: String,
  selectedYAxis: String,
  selectedOutlierStyle: String,
  datasetName: String,
  featureNames: Array,
  
  // Dimensions
  width: {
    type: Number,
    default: 1200
  },
  height: {
    type: Number,
    default: 800
  },
  
  // Active run ID for key updates
  activeRunId: String,
  
  // Cluster counts
  groundTruthClusterCount: {
    type: Number,
    default: 0
  },
  predictedClusterCount: {
    type: Number,
    default: 0
  }
});

// Highlighted points state for cross-panel synchronization
const highlightedPointsFromGroundTruth = ref<number[]>([]);
const highlightedPointsFromPredicted = ref<number[]>([]);

// Selection state management
const selectedNodes = ref<Set<string>>(new Set()); // Store selected node IDs
const nodeIdToPoints = ref<Map<string, number[]>>(new Map()); // Map nodeId to its points
const selectedPointsFromNodes = ref<number[]>([]); // Points from all selected nodes combined
let selectionTimeout: NodeJS.Timeout | null = null; // Auto-clear timeout for selections

// Computed dimensions - simple 50/50 split
const panelWidth = computed(() => Math.floor((props.width - 40) / 2)); // Account for padding and divider
const treeHeight = computed(() => Math.floor(props.height * 0.6)); // 60% for tree
const scatterHeight = computed(() => Math.floor(props.height * 0.4)); // 40% for scatter

// Computed highlighted points that combine hover + selection
const computedGroundTruthHighlights = computed(() => {
  const combined = new Set([
    ...highlightedPointsFromGroundTruth.value,
    ...selectedPointsFromNodes.value
  ]);
  return Array.from(combined);
});

const computedPredictedHighlights = computed(() => {
  const combined = new Set([
    ...highlightedPointsFromPredicted.value,
    ...selectedPointsFromNodes.value
  ]);
  return Array.from(combined);
});

// Event handlers for highlighting synchronization
const handleGroundTruthHighlight = (points: number[]) => {
  // When hovering in ground truth tree, highlight points in BOTH scatter plots
  highlightedPointsFromGroundTruth.value = points;
  highlightedPointsFromPredicted.value = points;
  emit('update:highlightedPoints', points);
};

const handlePredictedHighlight = (points: number[]) => {
  // When hovering in predicted tree, highlight points in BOTH scatter plots
  highlightedPointsFromGroundTruth.value = points;
  highlightedPointsFromPredicted.value = points;
  emit('update:highlightedPoints', points);
};

// Note: CanvasScatterPlot doesn't emit update:highlightedPoints events
// It handles highlighting internally and only emits pointHovered/pointClicked
// The highlighting from tree interactions is handled by the computed properties

// Handle point clicks from scatter plots
const handlePointClicked = (event: any) => {
  emit('pointClicked', event);
};

// Handle point hovers from scatter plots
const handlePointHovered = (event: any) => {
  emit('pointHovered', event);
};

// Handle node selection (Shift+click in trees)
const handleNodeSelection = (event: { nodeId: string, points: number[], isSelected: boolean }) => {
  if (event.isSelected) {
    selectedNodes.value.add(event.nodeId);
    // Store the points for this nodeId
    nodeIdToPoints.value.set(event.nodeId, event.points || []);
  } else {
    selectedNodes.value.delete(event.nodeId);
    // Remove the points mapping for this nodeId
    nodeIdToPoints.value.delete(event.nodeId);
  }
  
  // Recalculate combined points from all selected nodes
  updateSelectedPoints();
  
  // Reset the auto-clear timeout whenever selections change
  resetSelectionTimeout();
  
  // Emit selection event to parent
  emit('nodesSelected', Array.from(selectedNodes.value));
};

// Update the combined points from all selected nodes
const updateSelectedPoints = () => {
  // Combine all points from selected nodes
  const allSelectedPoints = new Set<number>();
  
  // Iterate through all selected nodes and combine their points
  for (const nodeId of selectedNodes.value) {
    const points = nodeIdToPoints.value.get(nodeId);
    if (points) {
      points.forEach(point => allSelectedPoints.add(point));
    }
  }
  
  // Update the combined points array
  selectedPointsFromNodes.value = Array.from(allSelectedPoints);
  
  console.log(`[StaticSplitView] Selected ${selectedNodes.value.size} nodes with ${selectedPointsFromNodes.value.length} total points`);
};

// Clear all selections
const clearAllSelections = () => {
  // Store the current selected nodes before clearing them
  const nodesToClear = Array.from(selectedNodes.value);
  
  selectedNodes.value.clear();
  nodeIdToPoints.value.clear();
  selectedPointsFromNodes.value = [];
  
  // Clear visual selection styling from tree nodes
  clearTreeSelectionStyling(nodesToClear);
  
  emit('nodesSelected', []);
  
  // Clear the auto-clear timeout since selections are already cleared
  if (selectionTimeout) {
    clearTimeout(selectionTimeout);
    selectionTimeout = null;
  }
};

// Clear visual selection styling from tree nodes
const clearTreeSelectionStyling = (nodeIds: string[]) => {
  // Clear selection styling from dendrogram circles
  const dendrogramCircles = document.querySelectorAll('#cluster-dendrogram .node circle');
  dendrogramCircles.forEach((circle: any) => {
    const node = d3.select(circle.parentNode);
    const nodeData = node.datum() as any;
    if (nodeData && nodeIds.includes(nodeData.data.id)) {
      d3.select(circle)
        .style('stroke', '#fff')
        .style('stroke-width', 2)
        .style('filter', null);
    }
  });
  
  // Clear selection styling from icicle plot rectangles
  const icicleRects = document.querySelectorAll('#cluster-icicle-plot .icicle-cell rect');
  icicleRects.forEach((rect: any) => {
    const node = d3.select(rect.parentNode);
    const nodeData = node.datum() as any;
    if (nodeData && nodeIds.includes(nodeData.data.id)) {
      d3.select(rect)
        .style('stroke', '#ffffff')
        .style('stroke-width', 0.5)
        .style('filter', null);
    }
  });
};

// Start or reset the auto-clear timeout for selections
const resetSelectionTimeout = () => {
  // Clear any existing timeout
  if (selectionTimeout) {
    clearTimeout(selectionTimeout);
  }
  
  // Only set timeout if there are selections
  if (selectedNodes.value.size > 0) {
    selectionTimeout = setTimeout(() => {
      console.log('[StaticSplitView] Auto-clearing selections after 20 seconds');
      clearAllSelections();
    }, 20000); // 20 seconds
  }
};

// Cleanup
onBeforeUnmount(() => {
  // Clear any pending highlights
  highlightedPointsFromGroundTruth.value = [];
  highlightedPointsFromPredicted.value = [];
  
  // Clear the selection timeout
  if (selectionTimeout) {
    clearTimeout(selectionTimeout);
    selectionTimeout = null;
  }
  
  console.log('StaticSplitView: Cleanup completed');
});
</script>

<style scoped>
.static-split-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.split-header {
  display: grid;
  grid-template-columns: 1fr 2px 1fr;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  padding: 16px 20px;
  gap: 20px;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left {
  justify-content: flex-start;
}

.header-right {
  justify-content: flex-start;
}

.header-divider {
  background: #d1d5db;
  width: 2px;
  align-self: stretch;
  margin: 4px 0;
}

.header-icon {
  font-size: 18px;
}

.header-title {
  font-weight: 600;
  font-size: 16px;
  color: #374151;
}

.cluster-count {
  background: #e5e7eb;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.split-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
}

.panel {
  display: flex;
  flex-direction: column;
  background: white;
  overflow: hidden;
}

.ground-truth-panel {
  border-right: 2px solid #e5e7eb;
}

.predicted-panel {
  border-left: 2px solid #e5e7eb;
}

.panel-inner {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.tree-section,
.scatter-section {
  flex-shrink: 0;
  border-bottom: 1px solid #f0f0f0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.scatter-section {
  border-bottom: none;
}

/* Ground truth styling */
.ground-truth-panel .cluster-count {
  background: #dbeafe;
  color: #1d4ed8;
}

/* Predicted panel styling */
.predicted-panel .cluster-count {
  background: #fecaca;
  color: #b91c1c;
}

/* Responsive design */
@media (max-width: 1200px) {
  .split-header {
    padding: 12px 16px;
    gap: 16px;
  }
  
  .header-title {
    font-size: 14px;
  }
  
  .cluster-count {
    font-size: 11px;
    padding: 3px 8px;
  }
}

@media (max-width: 768px) {
  .split-header {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto;
    gap: 8px;
    padding: 12px;
  }
  
  .header-divider {
    display: none;
  }
  
  .split-content {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
  
  .ground-truth-panel,
  .predicted-panel {
    border: none;
    border-bottom: 1px solid #e5e7eb;
  }
  
  .predicted-panel {
    border-bottom: none;
  }
}

/* Loading states */
.tree-section:empty::after,
.scatter-section:empty::after {
  content: 'Loading visualization...';
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  font-style: italic;
}
</style>