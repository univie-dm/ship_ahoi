<template>
  <div class="canvas-scatter-plot-container">
    <canvas ref="canvas" :width="width" :height="height" @mousemove="handleMouseMove" @mouseleave="handleMouseLeave"
      @click="handleClick" @dblclick="handleDoubleClick" @wheel="handleWheel" @mousedown="handleMouseDown" @mouseup="handleMouseUp" class="scatter-canvas"></canvas>

    <!-- Regular tooltip for non-image datasets -->
    <div v-if="hoveredPoint && !showImageTooltip" class="tooltip" :style="tooltipStyle">
      <div>Point {{ hoveredPoint.originalIndex }}</div>
      <div v-if="hoveredPoint.cluster !== undefined">Cluster: {{ hoveredPoint.cluster }}</div>
      <div>X: {{ hoveredPoint.x.toFixed(3) }}</div>
      <div>Y: {{ hoveredPoint.y.toFixed(3) }}</div>
    </div>

    <!-- Image tooltip for image datasets -->
    <ImageTooltip v-if="showImageTooltip" :pointIndex="hoveredPoint?.originalIndex || null"
      :cluster="hoveredPoint?.cluster" :label="hoveredPoint?.label" :x="hoveredPoint?.x" :y="hoveredPoint?.y"
      :mouseX="mousePosition.x" :mouseY="mousePosition.y" :datasetName="datasetName" :isVisible="!!hoveredPoint" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed, nextTick } from 'vue';
import * as d3 from 'd3';
import ImageTooltip from './ImageTooltip.vue';
import { useGlobalState } from '~/composables/useGlobalState';
import scientificColors from '~/composables/useScientificColors';

// Define interfaces
interface DimensionalityReductionData {
  pca: number[][] | null;
  umap: number[][] | null;
  tsne: number[][] | null;
}

interface ClusterData {
  points: number[][];
  labels?: (string | number)[];
  centers?: number[][];
  color_map?: Record<string, string>;
  scatter_colors?: string[];
  dimensionality_reduction?: DimensionalityReductionData;
  sampling_info?: {
    was_sampled: boolean;
    original_count: number;
    final_count: number;
    strategy: string;
    sampling_ratio: number;
  };
  index_mapping?: {
    original_to_sampled: Record<number, number>;
    sampled_to_original: number[];
  };
  node_mappings?: Record<string, number[]>;
  ground_truth?: {
    labels: (string | number)[];
    colors: string[];
    color_map: Record<string, string>;
    unique_labels: string[];
  };
}

interface Point {
  x: number;
  y: number;
  cluster: string | number | undefined;
  color: string;
  originalIndex: number;
  sampledIndex: number;
  highlighted: boolean;
  label?: string | number; // For ground truth labels in image datasets
}

interface QuadTreeNode {
  x: number;
  y: number;
  width: number;
  height: number;
  points: Point[];
  children?: QuadTreeNode[];
  capacity: number;
}

const props = defineProps({
  data: Object as () => ClusterData,
  width: { type: Number, default: 600 },
  height: { type: Number, default: 400 },
  highlightedIndices: {
    type: Array as () => number[],
    default: () => []
  },
  selectedXAxis: { type: String, default: 'feature-0' },
  selectedYAxis: { type: String, default: 'feature-1' },
  selectedColorBy: { type: String, default: 'predicted' },
  selectedOutlierStyle: { type: String, default: 'prominent' },
  datasetName: { type: String, default: '' },
  featureNames: {
    type: Array as () => string[],
    default: () => []
  }
});

const emit = defineEmits(['pointHovered', 'pointClicked']);

// Component lifecycle state
const isMounted = ref(false);
const isUnmounting = ref(false);

// Safe emit function to prevent Vue reactivity errors during navigation
const safeEmit = (eventName: 'pointHovered' | 'pointClicked', ...args: any[]) => {
  // Multiple safety checks before emitting
  if (isUnmounting.value || !isMounted.value || !canvas.value) {
    return;
  }

  try {
    emit(eventName, ...args);
  } catch (error: any) {
    // Silent handling of Vue reactivity errors during navigation
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[CanvasScatterPlot] Vue reactivity error during ${eventName} emit (likely navigation):`, error?.message || error);
    }
  }
};

// Refs
const canvas = ref<HTMLCanvasElement | null>(null);
const hoveredPoint = ref<Point | null>(null);
const clickedPoint = ref<Point | null>(null);
const tooltipStyle = ref<Record<string, string>>({});

// Image tooltip support
const mousePosition = ref({ x: 0, y: 0 });

// Check if current dataset supports image tooltips
const isImageDataset = computed(() => {
  if (!props.datasetName) {
    console.log('[CANVAS] No dataset name provided');
    return false;
  }
  const imageDatasets = [
    'digits_full', 'digits_small', 'olivetti_faces', 'lfw_faces',
    'coil20', 'coil100', 'mnist_full', 'fashion_mnist'
  ];
  const isImage = imageDatasets.includes(props.datasetName);
  console.log('[CANVAS] Dataset name:', props.datasetName, 'Is image dataset:', isImage);
  return isImage;
});

const showImageTooltip = computed(() => {
  return isImageDataset.value && !!hoveredPoint.value
})

// Get additional label info if available
const getLabelInfo = (point: Point) => {
  // Check if ground truth labels are available
  if (props.data?.ground_truth?.labels && point.originalIndex < props.data.ground_truth.labels.length) {
    return props.data.ground_truth.labels[point.originalIndex];
  }
  return undefined;
};

// Performance and rendering state
const renderingInProgress = ref(false);
const lastRenderTime = ref(0);
const animationFrameId = ref<number | null>(null);
const debounceTimeout = ref<number | null>(null);
const clickedPointTimeout = ref<NodeJS.Timeout | null>(null);

// Zoom and pan state
const zoom = ref({ x: 0, y: 0, scale: 1 });
const isDragging = ref(false);
const lastMousePos = ref({ x: 0, y: 0 });

// QuadTree for spatial indexing
class QuadTree {
  private root: QuadTreeNode;
  private capacity = 10;

  constructor(x: number, y: number, width: number, height: number) {
    this.root = {
      x, y, width, height,
      points: [],
      capacity: this.capacity
    };
  }

  insert(point: Point): void {
    this.insertIntoNode(this.root, point);
  }

  private insertIntoNode(node: QuadTreeNode, point: Point): void {
    if (!this.isPointInBounds(node, point)) return;

    if (node.points.length < node.capacity && !node.children) {
      node.points.push(point);
      return;
    }

    if (!node.children) {
      this.subdivide(node);
    }

    for (const child of node.children!) {
      this.insertIntoNode(child, point);
    }
  }

  private subdivide(node: QuadTreeNode): void {
    const { x, y, width, height } = node;
    const halfWidth = width / 2;
    const halfHeight = height / 2;

    node.children = [
      { x, y, width: halfWidth, height: halfHeight, points: [], capacity: this.capacity },
      { x: x + halfWidth, y, width: halfWidth, height: halfHeight, points: [], capacity: this.capacity },
      { x, y: y + halfHeight, width: halfWidth, height: halfHeight, points: [], capacity: this.capacity },
      { x: x + halfWidth, y: y + halfHeight, width: halfWidth, height: halfHeight, points: [], capacity: this.capacity }
    ];

    // Redistribute points
    for (const point of node.points) {
      for (const child of node.children) {
        this.insertIntoNode(child, point);
      }
    }
    node.points = [];
  }

  private isPointInBounds(node: QuadTreeNode, point: Point): boolean {
    return point.x >= node.x && point.x < node.x + node.width &&
      point.y >= node.y && point.y < node.y + node.height;
  }

  queryRange(x: number, y: number, radius: number): Point[] {
    const results: Point[] = [];
    this.queryNode(this.root, x, y, radius, results);
    return results;
  }

  private queryNode(node: QuadTreeNode, x: number, y: number, radius: number, results: Point[]): void {
    if (!this.circleIntersectsRect(x, y, radius, node.x, node.y, node.width, node.height)) {
      return;
    }

    for (const point of node.points) {
      const distance = Math.sqrt((point.x - x) ** 2 + (point.y - y) ** 2);
      if (distance <= radius) {
        results.push(point);
      }
    }

    if (node.children) {
      for (const child of node.children) {
        this.queryNode(child, x, y, radius, results);
      }
    }
  }

  private circleIntersectsRect(cx: number, cy: number, radius: number,
    rx: number, ry: number, rw: number, rh: number): boolean {
    const closestX = Math.max(rx, Math.min(cx, rx + rw));
    const closestY = Math.max(ry, Math.min(cy, ry + rh));
    const distance = Math.sqrt((cx - closestX) ** 2 + (cy - closestY) ** 2);
    return distance <= radius;
  }
}

// Utility function to get axis label
function getAxisLabel(axisKey: string): string {
  if (axisKey.startsWith('feature-')) {
    const parts = axisKey.split('-');
    const index = parseInt(parts[1], 10);
    // Use actual feature name if available, otherwise fall back to "Feature N"
    if (props.featureNames && props.featureNames[index]) {
      return props.featureNames[index];
    }
    return `Feature ${index + 1}`;
  }
  if (axisKey.startsWith('pca-')) {
    const parts = axisKey.split('-');
    const index = parseInt(parts[1], 10);
    return `PCA Component ${index + 1}`;
  }
  if (axisKey.startsWith('umap-')) {
    const parts = axisKey.split('-');
    const index = parseInt(parts[1], 10);
    return `UMAP Dimension ${index + 1}`;
  }
  if (axisKey.startsWith('tsne-')) {
    const parts = axisKey.split('-');
    const index = parseInt(parts[1], 10);
    return `t-SNE Dimension ${index + 1}`;
  }
  return axisKey;
}

// Function to draw zoom-aware axes with labels and tick marks
function drawAxes(ctx: CanvasRenderingContext2D, xScale: any, yScale: any, points: Point[], transformPoint: (x: number, y: number) => {x: number, y: number}) {
  if (points.length === 0) return;

  const margin = { top: 20, right: 20, bottom: 40, left: 65 };

  // Calculate zoom-adjusted scales and visible ranges for proper tick spacing
  const zoomScale = zoom.value.scale;
  
  // Calculate the visible data range based on current zoom and pan
  const visibleXMin = xScale.invert((margin.left - zoom.value.x) / zoomScale);
  const visibleXMax = xScale.invert((props.width - margin.right - zoom.value.x) / zoomScale);
  const visibleYMin = yScale.invert((props.height - margin.bottom - zoom.value.y) / zoomScale);
  const visibleYMax = yScale.invert((margin.top - zoom.value.y) / zoomScale);
  
  // Calculate appropriate step sizes based on visible range and zoom level
  const visibleXRange = Math.abs(visibleXMax - visibleXMin);
  const visibleYRange = Math.abs(visibleYMax - visibleYMin);
  
  // Determine optimal step sizes based on range and zoom
  const getOptimalStepSize = (range: number) => {
    const rawStep = range / 6; // Target ~6 ticks
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const normalized = rawStep / magnitude;
    
    let stepSize;
    if (normalized <= 1) stepSize = magnitude;
    else if (normalized <= 2) stepSize = 2 * magnitude;
    else if (normalized <= 5) stepSize = 5 * magnitude;
    else stepSize = 10 * magnitude;
    
    return stepSize;
  };
  
  const xStepSize = getOptimalStepSize(visibleXRange);
  const yStepSize = getOptimalStepSize(visibleYRange);

  // Set axis styling
  ctx.strokeStyle = '#333';
  ctx.fillStyle = '#333';
  ctx.lineWidth = 1;
  ctx.font = '12px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // Draw X axis line (fixed position, not zoomed)
  ctx.beginPath();
  ctx.moveTo(margin.left, props.height - margin.bottom);
  ctx.lineTo(props.width - margin.right, props.height - margin.bottom);
  ctx.stroke();

  // Draw Y axis line (fixed position, not zoomed)
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top);
  ctx.lineTo(margin.left, props.height - margin.bottom);
  ctx.stroke();

  // Generate X axis ticks based on optimal step size
  const xTicks: number[] = [];
  const xStart = Math.ceil(visibleXMin / xStepSize) * xStepSize;
  for (let tick = xStart; tick <= visibleXMax; tick += xStepSize) {
    xTicks.push(tick);
  }
  
  // Draw X axis ticks and labels (zoom-aware)
  xTicks.forEach((tick: number) => {
    const baseX = xScale(tick);
    const transformed = { x: (baseX * zoomScale) + zoom.value.x, y: 0 };
    const x = transformed.x;
    
    // Only draw ticks that are visible within the axis bounds
    if (x >= margin.left && x <= props.width - margin.right) {
      // Draw tick mark
      ctx.beginPath();
      ctx.moveTo(x, props.height - margin.bottom);
      ctx.lineTo(x, props.height - margin.bottom + 5);
      ctx.stroke();

      // Draw tick label with appropriate precision
      const precision = Math.max(0, -Math.floor(Math.log10(xStepSize)) + 1);
      ctx.fillText(tick.toFixed(precision), x, props.height - margin.bottom + 15);
    }
  });

  // Generate Y axis ticks based on optimal step size
  const yTicks: number[] = [];
  const yStart = Math.ceil(visibleYMin / yStepSize) * yStepSize;
  for (let tick = yStart; tick <= visibleYMax; tick += yStepSize) {
    yTicks.push(tick);
  }

  // Draw Y axis ticks and labels (zoom-aware)
  ctx.textAlign = 'right';
  yTicks.forEach((tick: number) => {
    const baseY = yScale(tick);
    const transformed = { x: 0, y: (baseY * zoomScale) + zoom.value.y };
    const y = transformed.y;
    
    // Only draw ticks that are visible within the axis bounds
    if (y >= margin.top && y <= props.height - margin.bottom) {
      // Draw tick mark
      ctx.beginPath();
      ctx.moveTo(margin.left - 5, y);
      ctx.lineTo(margin.left, y);
      ctx.stroke();

      // Draw tick label with appropriate precision
      const precision = Math.max(0, -Math.floor(Math.log10(yStepSize)) + 1);
      ctx.fillText(tick.toFixed(precision), margin.left - 8, y);
    }
  });

  // Draw X axis label (fixed position)
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = '14px Arial';
  ctx.fillText(getAxisLabel(props.selectedXAxis), props.width / 2, props.height - 10);

  // Draw Y axis label (rotated, fixed position)
  ctx.save();
  ctx.translate(12, props.height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(getAxisLabel(props.selectedYAxis), 0, 0);
  ctx.restore();
}

// Utility function to get axis data
function getAxisData(pointIndex: number, axisKey: string, allPoints: number[][], drData?: DimensionalityReductionData): number | undefined {
  if (!axisKey) return undefined;

  if (axisKey.startsWith('feature-')) {
    const parts = axisKey.split('-');
    const featureIndex = parseInt(parts[1], 10);
    return allPoints[pointIndex]?.[featureIndex];
  }
  if (drData) {
    if (axisKey.startsWith('pca-') && drData.pca) {
      const parts = axisKey.split('-');
      const componentIndex = parseInt(parts[1], 10);
      return drData.pca[pointIndex]?.[componentIndex];
    }
    if (axisKey.startsWith('umap-') && drData.umap) {
      const parts = axisKey.split('-');
      const componentIndex = parseInt(parts[1], 10);
      return drData.umap[pointIndex]?.[componentIndex];
    }
    if (axisKey.startsWith('tsne-') && drData.tsne) {
      const parts = axisKey.split('-');
      const componentIndex = parseInt(parts[1], 10);
      return drData.tsne[pointIndex]?.[componentIndex];
    }
  }
  // Fallback for centers if they don't have DR data directly associated
  if (allPoints[pointIndex]?.length > 1 && (axisKey === 'feature-0' || axisKey === 'feature-1')) {
    const parts = axisKey.split('-');
    const featureIndex = parseInt(parts[1], 10);
    return allPoints[pointIndex]?.[featureIndex];
  }
  return undefined;
}

// Computed properties
const samplingInfo = computed(() => props.data?.sampling_info || null);

const processedData = computed(() => {
  if (!props.data?.points || props.data.points.length === 0) return [];

  const startTime = performance.now();
  const points = props.data.points;
  const labels = props.data.labels || [];
  const colorMap = props.data.color_map || {};
  const scatterColors = props.data.scatter_colors || [];
  const indexMapping = props.data.index_mapping;
  const dimensionalityReduction = props.data.dimensionality_reduction;

  const processed = points.map((point, sampledIndex) => {
    const originalIndex = indexMapping?.sampled_to_original?.[sampledIndex] ?? sampledIndex;
    const cluster = labels[sampledIndex];

    // Get axis data using the selected axes instead of hardcoded [0], [1]
    const xVal = getAxisData(sampledIndex, props.selectedXAxis, points, dimensionalityReduction);
    const yVal = getAxisData(sampledIndex, props.selectedYAxis, points, dimensionalityReduction);

    let color = '#1f77b4'; // Default blue from scientific palette

    // Use the same color logic as IciclePlot for consistency
    if (props.selectedColorBy === 'ground_truth' && props.data?.ground_truth) {
      // Ground truth coloring support - match IciclePlot logic
      const groundTruthColors = props.data.ground_truth.colors;
      const groundTruthColorMap = props.data.ground_truth.color_map;
      const groundTruthLabels = props.data.ground_truth.labels;

      if (groundTruthColors && Array.isArray(groundTruthColors) && groundTruthColors[sampledIndex]) {
        color = groundTruthColors[sampledIndex];
      } else if (groundTruthColorMap && groundTruthLabels && groundTruthLabels[sampledIndex] !== undefined) {
        const gtLabel = String(groundTruthLabels[sampledIndex]);
        color = groundTruthColorMap[gtLabel] || '#cccccc';
      }
    } else {
      // Predicted cluster coloring - match IciclePlot approach
      if (String(cluster) === '-1') {
        // Special handling for outliers (label -1) - consistent with IciclePlot
        color = '#000000'; // Always black for outliers in scatterplot (consistent with tree)
      } else {
        // Default predicted cluster coloring using scientific palette approach
        if (cluster !== undefined && scatterColors[sampledIndex]) {
          color = scatterColors[sampledIndex];
        } else if (cluster !== undefined && colorMap[cluster]) {
          color = colorMap[cluster];
        } else if (cluster !== undefined) {
          // Fallback to scientific palette if no color mapping available
          const palette = scientificColors.getScientificPalette('default', 20);
          const clusterIndex = typeof cluster === 'number' ? cluster : parseInt(String(cluster), 10);
          if (!isNaN(clusterIndex) && clusterIndex >= 0) {
            color = palette[clusterIndex % palette.length];
          }
        }
      }
    }

    return {
      x: xVal !== undefined ? xVal : point[0], // Fallback to original behavior if axis data not available
      y: yVal !== undefined ? yVal : point[1], // Fallback to original behavior if axis data not available
      cluster,
      color,
      originalIndex,
      sampledIndex,
      highlighted: false
    } as Point;
  }).filter(d => d.x !== undefined && d.y !== undefined && !isNaN(d.x) && !isNaN(d.y) && isFinite(d.x) && isFinite(d.y)); // Filter out points with missing or invalid axis data

  const processingTime = performance.now() - startTime;
  if (processingTime > 100) {
    console.log(`[CanvasScatterPlot] Data processing took ${processingTime.toFixed(1)}ms for ${processed.length} points`);
  }

  return processed;
});

// Create spatial index
let spatialIndex: QuadTree | null = null;

const createSpatialIndex = (points: Point[], scales: { x: any, y: any }) => {
  if (points.length === 0) return null;

  const xExtent = scales.x.domain();
  const yExtent = scales.y.domain();

  spatialIndex = new QuadTree(
    xExtent[0], yExtent[0],
    xExtent[1] - xExtent[0], yExtent[1] - yExtent[0]
  );

  for (const point of points) {
    spatialIndex.insert(point);
  }

  return spatialIndex;
};

// Rendering functions
const renderPoints = () => {
  if (!canvas.value || renderingInProgress.value) return;

  renderingInProgress.value = true;
  const startTime = performance.now();

  // Ensure canvas dimensions are properly set
  if (canvas.value.width !== props.width || canvas.value.height !== props.height) {
    canvas.value.width = props.width;
    canvas.value.height = props.height;
  }

  const ctx = canvas.value.getContext('2d')!;
  const points = processedData.value;

  // Clear canvas
  ctx.clearRect(0, 0, props.width, props.height);

  if (points.length === 0) {
    renderingInProgress.value = false;
    return;
  }

  // Enable high-quality rendering
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';

  // Create scales with proper margins for axes (no canvas transformation applied)
  const margin = { top: 20, right: 20, bottom: 40, left: 65 };
  const xExtent = d3.extent(points, d => d.x) as [number, number];
  const yExtent = d3.extent(points, d => d.y) as [number, number];

  const xScale = d3.scaleLinear()
    .domain(xExtent)
    .range([margin.left, props.width - margin.right]);

  const yScale = d3.scaleLinear()
    .domain(yExtent)
    .range([props.height - margin.bottom, margin.top]);

  // Manual coordinate transformation function for zoom
  const transformPoint = (dataX: number, dataY: number) => {
    const baseX = xScale(dataX);
    const baseY = yScale(dataY);
    
    // Apply zoom transformation manually (screen-space coordinates)
    const screenX = (baseX * zoom.value.scale) + zoom.value.x;
    const screenY = (baseY * zoom.value.scale) + zoom.value.y;
    
    return { x: screenX, y: screenY };
  };

  // Create spatial index for hover detection
  createSpatialIndex(points, { x: xScale, y: yScale });

  // Set up clipping region to prevent points from rendering outside plot area
  ctx.save();
  ctx.beginPath();
  ctx.rect(margin.left, margin.top, props.width - margin.left - margin.right, props.height - margin.top - margin.bottom);
  ctx.clip();

  // Update highlighted status
  const highlightedSet = new Set(props.highlightedIndices);
  points.forEach(point => {
    point.highlighted = highlightedSet.has(point.originalIndex);
  });

  // Unified Canvas design for all dataset sizes
  const pointCount = points.length;
  const hasHighlightedPoints = highlightedSet.size > 0;

  // Dynamic point sizing based on dataset size to reduce overlap
  let basePointRadius: number;
  let highlightedRadius: number;
  let baseOpacity: number;
  
  if (pointCount < 1000) {
    basePointRadius = 4;
    highlightedRadius = 7;
    baseOpacity = 0.8;
  } else if (pointCount < 5000) {
    basePointRadius = 3;
    highlightedRadius = 6;
    baseOpacity = 0.6;
  } else if (pointCount < 20000) {
    basePointRadius = 2;
    highlightedRadius = 4;
    baseOpacity = 0.5;
  } else {
    basePointRadius = 1.5;
    highlightedRadius = 3;
    baseOpacity = 0.4;
  }
  
  let useCircles = true;  // Always use circles for visual consistency

  // Sort points: regular points first, then highlighted points, then clicked point on top
  const regularPoints = points.filter(p => !p.highlighted && (!clickedPoint.value || p.originalIndex !== clickedPoint.value.originalIndex));
  const highlightedPoints = points.filter(p => p.highlighted && (!clickedPoint.value || p.originalIndex !== clickedPoint.value.originalIndex));
  const clickedPointToRender = clickedPoint.value ? points.filter(p => p.originalIndex === clickedPoint.value!.originalIndex) : [];

  // Canvas blending optimization for high-density datasets
  if (pointCount > 2000) {
    ctx.globalCompositeOperation = 'multiply'; // Better for overlapping points
  } else {
    ctx.globalCompositeOperation = 'source-over'; // Default for smaller datasets
  }

  // Render regular points (consistent with SVG styling)
  for (const point of regularPoints) {
    const transformed = transformPoint(point.x, point.y);
    const x = transformed.x;
    const y = transformed.y;

    if (isNaN(x) || isNaN(y)) continue;

    const isOutlier = String(point.cluster) === '-1';
    const isProminent = props.selectedOutlierStyle === 'prominent';

    // Determine point radius: use base size consistently, don't shrink when highlighting
    let pointRadius = basePointRadius;
    if (isOutlier && isProminent) {
      pointRadius = basePointRadius + 1; // Slightly larger for prominent outliers
    }

    // Special styling for prominent outliers
    if (isOutlier && isProminent) {
      ctx.globalAlpha = 1.0; // Full opacity for prominent outliers
      ctx.fillStyle = point.color;
      ctx.strokeStyle = '#000000'; // Black border
      ctx.lineWidth = 2;

      ctx.beginPath();
      ctx.arc(x, y, pointRadius, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();

      // Reset for next points
      ctx.globalAlpha = baseOpacity;
    } else {
      ctx.fillStyle = point.color;
      ctx.globalAlpha = baseOpacity;  // Use density-aware opacity

      ctx.beginPath();
      ctx.arc(x, y, pointRadius, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  // Render highlighted points with increased visibility (matching SVG)
  if (highlightedPoints.length > 0) {
    ctx.globalCompositeOperation = 'source-over'; // Reset to normal blending for highlights
    ctx.globalAlpha = 1.0;
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 2;  // Match SVG stroke width

    for (const point of highlightedPoints) {
      const transformed = transformPoint(point.x, point.y);
      const x = transformed.x;
      const y = transformed.y;

      if (isNaN(x) || isNaN(y)) continue;

      // Highlighted points use consistent styling with SVG
      ctx.fillStyle = point.color;
      ctx.beginPath();
      ctx.arc(x, y, highlightedRadius, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
    }
  }

  // Render clicked point with special visual feedback (most prominent)
  if (clickedPointToRender.length > 0) {
    ctx.globalCompositeOperation = 'source-over'; // Ensure clicked points are fully visible
    ctx.globalAlpha = 1.0;
    ctx.strokeStyle = '#FF6B35'; // Bright orange for click feedback
    ctx.lineWidth = 3;

    for (const point of clickedPointToRender) {
      const transformed = transformPoint(point.x, point.y);
      const x = transformed.x;
      const y = transformed.y;

      if (isNaN(x) || isNaN(y)) continue;

      // Create a pulsing effect for clicked points
      const clickRadius = highlightedRadius + 2;
      
      // Inner filled circle
      ctx.fillStyle = point.color;
      ctx.beginPath();
      ctx.arc(x, y, clickRadius, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
      
      // Outer pulsing ring
      ctx.beginPath();
      ctx.arc(x, y, clickRadius + 3, 0, 2 * Math.PI);
      ctx.strokeStyle = '#FF6B35';
      ctx.lineWidth = 2;
      ctx.globalAlpha = 0.6;
      ctx.stroke();
      
      // Reset alpha
      ctx.globalAlpha = 1.0;
    }
  }

  // Restore clipping context before drawing axes
  ctx.restore();

  // Draw axes with labels and tick marks
  drawAxes(ctx, xScale, yScale, points, transformPoint);

  // Reset canvas composite operation to default
  ctx.globalCompositeOperation = 'source-over';

  renderingInProgress.value = false;
  const renderTime = performance.now() - startTime;
  lastRenderTime.value = renderTime;

  if (renderTime > 50) {
    console.log(`[CanvasScatterPlot] Render took ${renderTime.toFixed(1)}ms for ${pointCount} points`);
  }
};

// Performance optimization variables for mouse events
let lastMouseMoveTime = 0;
let mouseMoveTimeout: NodeJS.Timeout | null = null;
const MOUSE_THROTTLE_MS = 16; // ~60fps

// Zoom-specific performance throttling
let zoomAnimationId: number | null = null;
let panAnimationId: number | null = null;
const ZOOM_THROTTLE_MS = 16; // ~60fps for smooth zoom

// Throttled rendering functions for zoom performance
const throttledZoomRender = () => {
  if (zoomAnimationId !== null) return;
  
  zoomAnimationId = requestAnimationFrame(() => {
    renderPoints();
    zoomAnimationId = null;
  });
};

const throttledPanRender = () => {
  if (panAnimationId !== null) return;
  
  panAnimationId = requestAnimationFrame(() => {
    renderPoints();
    panAnimationId = null;
  });
};

// Event handlers with performance optimizations
const handleMouseMove = (event: MouseEvent) => {
  if (!canvas.value) return;

  const rect = canvas.value.getBoundingClientRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;

  // Handle panning if dragging
  if (isDragging.value) {
    const deltaX = mouseX - lastMousePos.value.x;
    const deltaY = mouseY - lastMousePos.value.y;
    
    zoom.value = {
      ...zoom.value,
      x: zoom.value.x + deltaX,
      y: zoom.value.y + deltaY
    };
    
    lastMousePos.value = { x: mouseX, y: mouseY };
    
    // Use throttled rendering during panning for smooth 60fps
    throttledPanRender();
    return; // Skip hover detection while panning
  }

  if (!spatialIndex) return;

  // Throttle mouse move events for better performance (only for hover detection)
  const now = performance.now();
  if (now - lastMouseMoveTime < MOUSE_THROTTLE_MS) {
    // Cancel pending update and schedule new one
    if (mouseMoveTimeout) {
      clearTimeout(mouseMoveTimeout);
    }

    mouseMoveTimeout = setTimeout(() => {
      handleMouseMove(event);
    }, MOUSE_THROTTLE_MS);
    return;
  }

  // Clear any pending timeout since we're processing now
  if (mouseMoveTimeout) {
    clearTimeout(mouseMoveTimeout);
    mouseMoveTimeout = null;
  }

  lastMouseMoveTime = now;

  // Update mouse position for image tooltip (relative to viewport)
  mousePosition.value = {
    x: event.clientX,
    y: event.clientY
  };

  // Convert to data coordinates (accounting for zoom)
  const points = processedData.value;
  if (points.length === 0) return;

  // Convert mouse coordinates to zoom-aware coordinates
  const zoomAdjustedX = (mouseX - zoom.value.x) / zoom.value.scale;
  const zoomAdjustedY = (mouseY - zoom.value.y) / zoom.value.scale;

  const margin = { top: 20, right: 20, bottom: 40, left: 65 };
  const xExtent = d3.extent(points, d => d.x) as [number, number];
  const yExtent = d3.extent(points, d => d.y) as [number, number];

  const xScale = d3.scaleLinear()
    .domain(xExtent)
    .range([margin.left, props.width - margin.right]);

  const yScale = d3.scaleLinear()
    .domain(yExtent)
    .range([props.height - margin.bottom, margin.top]);

  const dataX = xScale.invert(zoomAdjustedX);
  const dataY = yScale.invert(zoomAdjustedY);

  // Optimized point detection with zoom-aware adaptive search radius
  const baseSearchRadius = 12;
  const zoomAdjustedRadius = baseSearchRadius / zoom.value.scale; // Smaller radius when zoomed in
  const adaptiveRadius = Math.max(zoomAdjustedRadius, Math.min(20, points.length / 500));
  const dataRadius = Math.abs(xScale.invert(adaptiveRadius) - xScale.invert(0));
  const nearbyPoints = spatialIndex.queryRange(dataX, dataY, dataRadius);

  // Find closest point with optimized distance calculation
  let closestPoint: Point | null = null;
  let minDistance = Infinity;

  for (const point of nearbyPoints) {
    const screenX = xScale(point.x);
    const screenY = yScale(point.y);
    const distance = Math.sqrt((zoomAdjustedX - screenX) ** 2 + (zoomAdjustedY - screenY) ** 2);

    if (distance < zoomAdjustedRadius && distance < minDistance) {
      minDistance = distance;
      closestPoint = point;
    }
  }

  // If no point found with spatial index, try brute force search for small datasets
  if (!closestPoint && points.length < 1000) {
    for (const point of points) {
      const screenX = xScale(point.x);
      const screenY = yScale(point.y);
      const distance = Math.sqrt((zoomAdjustedX - screenX) ** 2 + (zoomAdjustedY - screenY) ** 2);

      if (distance < zoomAdjustedRadius && distance < minDistance) {
        minDistance = distance;
        closestPoint = point;
      }
    }
  }

  if (closestPoint !== hoveredPoint.value) {
    hoveredPoint.value = closestPoint;

    if (closestPoint) {
      // Set pointer cursor when hovering over a data point
      if (canvas.value) {
        canvas.value.style.cursor = 'pointer';
      }

      // Add label info for image datasets
      if (isImageDataset.value) {
        closestPoint.label = getLabelInfo(closestPoint);
      }

      // For non-image datasets, set tooltip style
      if (!isImageDataset.value) {
        tooltipStyle.value = {
          position: 'absolute',
          left: `${mouseX + 10}px`,
          top: `${mouseY - 10}px`,
          background: 'rgba(0, 0, 0, 0.8)',
          color: 'white',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          pointerEvents: 'none',
          zIndex: '1000'
        };
      }

      safeEmit('pointHovered', {
        point: closestPoint,
        originalIndex: closestPoint.originalIndex
      });
    } else {
      // Reset to crosshair cursor when not hovering over a point
      if (canvas.value) {
        canvas.value.style.cursor = '';
      }
    }
  }
};

const handleMouseLeave = () => {
  // Early exit if component is unmounting
  if (isUnmounting.value || !isMounted.value) {
    return;
  }

  hoveredPoint.value = null;
  // Reset cursor to default crosshair when leaving canvas
  if (canvas.value) {
    canvas.value.style.cursor = '';
  }
  safeEmit('pointHovered', null);
};

const handleClick = (event: MouseEvent) => {
  console.log('[CANVAS] Click detected, hoveredPoint:', hoveredPoint.value);

  // Early exit if component is unmounting
  if (isUnmounting.value || !isMounted.value) {
    return;
  }

  if (hoveredPoint.value) {
    console.log('[CANVAS] About to emit pointClicked for originalIndex:', hoveredPoint.value.originalIndex);
    
    // Clear any existing clicked point timeout for immediate new arrow display
    if (clickedPointTimeout.value) {
      clearTimeout(clickedPointTimeout.value);
      clickedPointTimeout.value = null;
    }
    
    // Set clicked point for visual feedback
    clickedPoint.value = hoveredPoint.value;
    
    // Clear clicked point after 3 seconds
    clickedPointTimeout.value = setTimeout(() => {
      clickedPoint.value = null;
      clickedPointTimeout.value = null;
      // Trigger re-render to remove click highlight
      if (animationFrameId.value) {
        cancelAnimationFrame(animationFrameId.value);
      }
      animationFrameId.value = requestAnimationFrame(renderPoints);
    }, 3000);
    
    try {
      safeEmit('pointClicked', {
        point: hoveredPoint.value,
        originalIndex: hoveredPoint.value.originalIndex
      });
      console.log('[CANVAS] pointClicked event emitted');
    } catch (error) {
      console.warn('[CANVAS] Error emitting pointClicked:', error);
    }
  } else {
    console.log('[CANVAS] No hovered point, click ignored');
    // Clear any existing clicked point when clicking empty space
    clickedPoint.value = null;
  }
};

const handleDoubleClick = (event: MouseEvent) => {
  event.preventDefault();
  
  // Reset zoom to initial state
  zoom.value = { x: 0, y: 0, scale: 1 };
  
  // Trigger re-render
  renderPoints();
};

const handleWheel = (event: WheelEvent) => {
  event.preventDefault();
  
  if (!canvas.value) return;
  
  const rect = canvas.value.getBoundingClientRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  
  // Zoom factor: negative deltaY means zoom in, positive means zoom out
  const zoomFactor = event.deltaY > 0 ? 0.9 : 1.1;
  const newScale = Math.max(0.5, Math.min(20, zoom.value.scale * zoomFactor));
  
  // Calculate zoom center in canvas coordinates
  const zoomCenterX = (mouseX - zoom.value.x) / zoom.value.scale;
  const zoomCenterY = (mouseY - zoom.value.y) / zoom.value.scale;
  
  // Update zoom state to zoom toward mouse position
  zoom.value = {
    scale: newScale,
    x: mouseX - zoomCenterX * newScale,
    y: mouseY - zoomCenterY * newScale
  };
  
  // Use throttled rendering for smooth zoom
  throttledZoomRender();
};

const handleMouseDown = (event: MouseEvent) => {
  if (!canvas.value) return;
  
  const rect = canvas.value.getBoundingClientRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  
  isDragging.value = true;
  lastMousePos.value = { x: mouseX, y: mouseY };
  
  // Prevent text selection while dragging
  event.preventDefault();
};

const handleMouseUp = (event: MouseEvent) => {
  isDragging.value = false;
};

// Optimized watchers - split to prevent unnecessary re-renders from dimensionality reduction updates
// Watch for core data changes that affect visualization
watch(() => [
  props.data?.points,
  props.data?.labels,
  props.data?.centers,
  props.data?.scatter_colors,
  props.data?.color_map,
  props.data?.ground_truth
], () => {
  // Reset zoom when data changes (new run selected)
  zoom.value = { x: 0, y: 0, scale: 1 };
  
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value);
  }
  animationFrameId.value = requestAnimationFrame(renderPoints);
}, { deep: false });

// Watch for dimensionality reduction data only when relevant axes are selected
watch(() => {
  const dr = props.data?.dimensionality_reduction;
  if (!dr) return null;

  // Only watch the specific dimensionality reduction data that's currently being used
  if (props.selectedXAxis?.startsWith('umap-') || props.selectedYAxis?.startsWith('umap-')) {
    return dr.umap;
  }
  if (props.selectedXAxis?.startsWith('tsne-') || props.selectedYAxis?.startsWith('tsne-')) {
    return dr.tsne;
  }
  if (props.selectedXAxis?.startsWith('pca-') || props.selectedYAxis?.startsWith('pca-')) {
    return dr.pca;
  }
  return null;
}, () => {
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value);
  }
  animationFrameId.value = requestAnimationFrame(renderPoints);
}, { deep: false });

watch(() => props.highlightedIndices, () => {
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value);
  }
  animationFrameId.value = requestAnimationFrame(renderPoints);
}, { deep: true });

// Watch for axis changes to trigger re-rendering
watch(() => [props.selectedXAxis, props.selectedYAxis, props.selectedColorBy, props.selectedOutlierStyle], () => {
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value);
  }
  animationFrameId.value = requestAnimationFrame(renderPoints);
}, { deep: false });

// Watch for dimension changes to trigger re-rendering (critical for layout switching)
// Use debouncing to prevent excessive re-renders during rapid dimension changes
watch(() => [props.width, props.height], () => {
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value);
  }
  if (debounceTimeout.value) {
    clearTimeout(debounceTimeout.value);
  }

  // Debounce rapid dimension changes (common during layout switching)
  debounceTimeout.value = window.setTimeout(() => {
    animationFrameId.value = requestAnimationFrame(renderPoints);
  }, 16); // ~60fps debounce
}, { deep: false });

// Lifecycle
onMounted(() => {
  isMounted.value = true;
  nextTick(() => {
    renderPoints();
  });
});

onBeforeUnmount(() => {
  isUnmounting.value = true;
  isMounted.value = false;

  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value);
  }
  if (debounceTimeout.value) {
    clearTimeout(debounceTimeout.value);
  }
  if (clickedPointTimeout.value) {
    clearTimeout(clickedPointTimeout.value);
  }
  if (zoomAnimationId !== null) {
    cancelAnimationFrame(zoomAnimationId);
  }
  if (panAnimationId !== null) {
    cancelAnimationFrame(panAnimationId);
  }
});
</script>

<style scoped>
.canvas-scatter-plot-container {
  position: relative;
  display: inline-block;
}

.tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
}

canvas {
  background: white;
}

.scatter-canvas {
  /* Default: Use a robust crosshair cursor with better visibility */
  cursor: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g stroke="%23000000" stroke-width="2" fill="none"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></g><g stroke="%23ffffff" stroke-width="1" fill="none"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></g></svg>') 12 12, crosshair !important;

  /* Force visible cursor on white backgrounds */
  filter: contrast(1.2);
}

/* When JavaScript sets cursor to 'pointer' for data points, ensure it's visible */
.scatter-canvas[style*="cursor: pointer"] {
  cursor: pointer !important;
}

/* Fallback crosshair when cursor is reset */
.scatter-canvas:not([style*="cursor: pointer"]) {
  cursor: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g stroke="%23000000" stroke-width="2" fill="none"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></g><g stroke="%23ffffff" stroke-width="1" fill="none"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></g></svg>') 12 12, crosshair !important;
}
</style>