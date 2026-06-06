1<template>
  <div class="scatter-plot-container">
    <svg id="cluster-scatter-plot" ref="svg" :width="width" :height="height"></svg>
    
    <!-- Regular tooltip for non-image datasets -->
    <div v-if="hoveredPointInfo && !showImageTooltip" class="svg-tooltip" :style="tooltipStyle">
      <div>Point {{ hoveredPointInfo.originalIndex }}</div>
      <div v-if="hoveredPointInfo.cluster !== undefined">Cluster: {{ hoveredPointInfo.cluster }}</div>
      <div>X: {{ hoveredPointInfo.x?.toFixed(3) }}</div>
      <div>Y: {{ hoveredPointInfo.y?.toFixed(3) }}</div>
    </div>
    
    <!-- Image tooltip for image datasets -->
    <ImageTooltip
      v-if="showImageTooltip"
      :pointIndex="hoveredPointInfo?.originalIndex || null"
      :cluster="hoveredPointInfo?.cluster"
      :label="hoveredPointInfo?.label"
      :x="hoveredPointInfo?.x"
      :y="hoveredPointInfo?.y"
      :mouseX="mousePosition.x"
      :mouseY="mousePosition.y"
      :datasetName="datasetName"
      :isVisible="!!hoveredPointInfo"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue';
import * as d3 from 'd3';
import { useMemoryManagement } from '~/composables/useMemoryManagement';
import ImageTooltip from './ImageTooltip.vue';

// Define an interface for the data prop
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

const props = defineProps({
  data: Object as () => ClusterData,
  width: { type: Number, default: 600 },
  height: { type: Number, default: 400 },
  highlightedIndices: {
    type: Array as () => number[],
    default: () => []
  },
  selectedXAxis: { type: String, default: 'feature-0' }, // Added
  selectedYAxis: { type: String, default: 'feature-1' },  // Added
  selectedColorBy: { type: String, default: 'predicted' }, // Added
  selectedOutlierStyle: { type: String, default: 'prominent' }, // Added
  datasetName: { type: String, default: '' },
  featureNames: {
    type: Array as () => string[],
    default: () => []
  }
});
const svg = ref<SVGSVGElement | null>(null);

const emit = defineEmits(['pointClicked']);

// Performance optimization variables
let lastHoverTime = 0;
let hoverThrottleTimeout: NodeJS.Timeout | null = null;
const HOVER_THROTTLE_MS = 16; // ~60fps

// Zoom state management
const zoom = ref({ x: 0, y: 0, scale: 1 });
const isDragging = ref(false);
const lastMousePos = ref({ x: 0, y: 0 });
let zoomAnimationId: number | null = null;

// Image tooltip support with performance optimizations
const hoveredPointInfo = ref<any>(null);
const mousePosition = ref({ x: 0, y: 0 });
const tooltipStyle = ref<Record<string, string>>({});

// Check if current dataset supports image tooltips
const isImageDataset = computed(() => {
  if (!props.datasetName) return false;
  const imageDatasets = [
    'digits_full', 'digits_small', 'olivetti_faces', 'lfw_faces',
    'coil20', 'coil100', 'mnist_full', 'fashion_mnist'
  ];
  return imageDatasets.includes(props.datasetName);
});

const showImageTooltip = computed(() => {
  return isImageDataset.value && !!hoveredPointInfo.value;
});

// Get additional label info if available
const getLabelInfo = (originalIndex: number) => {
  // Check if ground truth labels are available
  if (props.data?.ground_truth?.labels && originalIndex < props.data.ground_truth.labels.length) {
    return props.data.ground_truth.labels[originalIndex];
  }
  return undefined;
};

// Setup mouse event listeners
const setupMouseEvents = () => {
  if (!svg.value) return;
  
  svg.value.addEventListener('wheel', handleWheel, { passive: false });
  svg.value.addEventListener('mousedown', handleMouseDown);
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};

const removeMouseEvents = () => {
  if (svg.value) {
    svg.value.removeEventListener('wheel', handleWheel);
    svg.value.removeEventListener('mousedown', handleMouseDown);
  }
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
};

// Get zoom-aware hover detection radius
const getHoverRadius = (dataLength: number) => {
  const baseSearchRadius = 12;
  const zoomAdjustedRadius = baseSearchRadius / zoom.value.scale;
  const adaptiveRadius = Math.max(zoomAdjustedRadius, Math.min(20, dataLength / 500));
  return adaptiveRadius;
};

// Optimized mouse over handler to reduce Vue reactivity overhead with zoom awareness
const handleMouseOver = (event: any, d: any) => {
  // Update mouse position for image tooltip
  mousePosition.value = {
    x: event.pageX,
    y: event.pageY
  };
  
  // Fix cluster label handling - cluster 0 is valid, not unknown
  let clusterLabel = 'Unknown';
  if (d.cluster !== undefined && d.cluster !== null) {
    clusterLabel = String(d.cluster);
  } else if (props.data?.labels && d.originalIndex >= 0 && d.originalIndex < props.data.labels.length) {
    const label = props.data.labels[d.originalIndex];
    if (label !== undefined && label !== null) {
      clusterLabel = String(label);
    }
  }
  
  // Set hovered point info with minimal object creation
  hoveredPointInfo.value = {
    originalIndex: d.originalIndex,
    cluster: clusterLabel,
    x: d.x,
    y: d.y,
    label: isImageDataset.value ? getLabelInfo(d.originalIndex) : undefined
  };
  
  // For non-image datasets, show regular tooltip
  if (!isImageDataset.value) {
    const rect = svg.value?.getBoundingClientRect();
    if (rect) {
      tooltipStyle.value = {
        position: 'absolute',
        left: `${event.pageX - rect.left + 10}px`,
        top: `${event.pageY - rect.top - 10}px`,
        zIndex: '9999',
        pointerEvents: 'none'
      };
    }
  }
};

// Memory management
const { trackLargeObject, forceGarbageCollection } = useMemoryManagement();

// Manual coordinate transformation function for zoom
const transformPoint = (dataX: number, dataY: number, xScale: any, yScale: any) => {
  const baseX = xScale(dataX);
  const baseY = yScale(dataY);
  
  // Apply zoom transformation manually (screen-space coordinates)
  const screenX = (baseX * zoom.value.scale) + zoom.value.x;
  const screenY = (baseY * zoom.value.scale) + zoom.value.y;
  
  return { x: screenX, y: screenY };
};

// Throttled rendering functions for zoom performance
const throttledZoomRender = () => {
  if (zoomAnimationId !== null) return;
  
  zoomAnimationId = requestAnimationFrame(() => {
    // Instead of full redraw, update positions and axes efficiently
    if (svg.value) {
      const svgEl = d3.select(svg.value);
      const renderData = (svgEl.node() as any).__renderData;
      
      if (renderData) {
        const { dataForPlot, xScale, yScale, centersForPlot } = renderData;
        
        // Update point positions
        svgEl.selectAll('circle')
          .attr('cx', (d: any) => {
            const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
            return transformed.x;
          })
          .attr('cy', (d: any) => {
            const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
            return transformed.y;
          });
        
        // Update center positions if they exist
        if (centersForPlot) {
          svgEl.selectAll('rect')
            .attr('x', (d: any) => {
              const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
              return transformed.x - 8;
            })
            .attr('y', (d: any) => {
              const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
              return transformed.y - 8;
            });
        }
        
        // Update axes
        const updateAxes = (svgEl.node() as any).__updateAxes;
        if (updateAxes) {
          updateAxes();
        }
      }
    }
    
    zoomAnimationId = null;
  });
};

// Mouse event handlers for zoom and pan
const handleWheel = (event: WheelEvent) => {
  event.preventDefault();
  
  if (!svg.value) return;
  
  const rect = svg.value.getBoundingClientRect();
  const mouseX = event.clientX - rect.left;
  const mouseY = event.clientY - rect.top;
  
  const scaleFactor = event.deltaY > 0 ? 0.9 : 1.1;
  const newScale = Math.max(0.1, Math.min(20, zoom.value.scale * scaleFactor));
  
  // Calculate zoom center offset
  const scaleRatio = newScale / zoom.value.scale;
  zoom.value.x = mouseX - (mouseX - zoom.value.x) * scaleRatio;
  zoom.value.y = mouseY - (mouseY - zoom.value.y) * scaleRatio;
  zoom.value.scale = newScale;
  
  throttledZoomRender();
};

const handleMouseDown = (event: MouseEvent) => {
  if (event.button !== 0) return; // Only left mouse button
  // Prevent text selection while dragging to pan
  event.preventDefault();
  
  isDragging.value = true;
  lastMousePos.value = { x: event.clientX, y: event.clientY };
  
  if (svg.value) {
    svg.value.style.cursor = 'grabbing';
  }
};

const handleMouseMove = (event: MouseEvent) => {
  if (!isDragging.value) return;
  
  const deltaX = event.clientX - lastMousePos.value.x;
  const deltaY = event.clientY - lastMousePos.value.y;
  
  zoom.value.x += deltaX;
  zoom.value.y += deltaY;
  
  lastMousePos.value = { x: event.clientX, y: event.clientY };
  
  throttledZoomRender();
};

const handleMouseUp = () => {
  isDragging.value = false;
  
  if (svg.value) {
    svg.value.style.cursor = '';
  }
};

// Debug logging utility
const debug = process.env.NODE_ENV === 'development' ? console.log : () => {};
const debugWarn = process.env.NODE_ENV === 'development' ? console.warn : () => {};
const debugError = process.env.NODE_ENV === 'development' ? console.error : () => {};

const samplingInfo = computed(() => props.data?.sampling_info || null);

// Convert original highlighted indices to sampled indices for display
const adjustedHighlightedIndices = computed(() => {
  if (!props.highlightedIndices || props.highlightedIndices.length === 0) {
    return [];
  }
  
  // If data was sampled, convert original indices to sampled indices
  if (props.data?.index_mapping && props.data.sampling_info?.was_sampled) {
    const mapping = props.data.index_mapping.original_to_sampled;
    return props.highlightedIndices
      .map(originalIdx => mapping[originalIdx])
      .filter(sampledIdx => sampledIdx !== undefined);
  }
  
  // If no sampling, use original indices
  return props.highlightedIndices;
});

const getAxisLabel = (axisKey: string): string => {
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
};

const xAxisLabel = computed(() => getAxisLabel(props.selectedXAxis));
const yAxisLabel = computed(() => getAxisLabel(props.selectedYAxis));

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
  // This assumes centers are in the original feature space if not otherwise specified
  if (allPoints[pointIndex]?.length > 1 && (axisKey === 'feature-0' || axisKey === 'feature-1')) {
      const parts = axisKey.split('-');
      const featureIndex = parseInt(parts[1], 10);
      return allPoints[pointIndex]?.[featureIndex];
  }
  return undefined;
}

// Dynamic sizing based on dataset size to reduce overlap  
function getDynamicSizes(pointCount: number) {
  if (pointCount < 1000) {
    return { baseRadius: 3, highlightedRadius: 6, baseOpacity: 0.8 };
  } else if (pointCount < 5000) {
    return { baseRadius: 2.5, highlightedRadius: 5, baseOpacity: 0.6 };
  } else if (pointCount < 20000) {
    return { baseRadius: 2, highlightedRadius: 4, baseOpacity: 0.5 };
  } else {
    return { baseRadius: 1.5, highlightedRadius: 3, baseOpacity: 0.4 };
  }
}

// Performance optimization: Chunked rendering for large datasets
function renderPointsInChunks(
  g: any, 
  dataForPlot: any[], 
  xScale: any, 
  yScale: any, 
  colorFn: (index: number) => string, 
  highlightedSet: Set<number>,
  labels?: (string | number)[],
  margin?: any
) {
  const chunkSize = 100; // Render 100 points at a time
  let currentIndex = 0;
  const dynamicSizes = getDynamicSizes(dataForPlot.length);
  
  function renderChunk() {
    const endIndex = Math.min(currentIndex + chunkSize, dataForPlot.length);
    const chunk = dataForPlot.slice(currentIndex, endIndex);
    
    // Render this chunk of points with zoom-aware transformations
    g.selectAll(`circle.chunk-${Math.floor(currentIndex / chunkSize)}`)
      .data(chunk)
      .enter()
      .append('circle')
      .attr('class', `chunk-${Math.floor(currentIndex / chunkSize)}`)
      .attr('cx', (d: any) => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.x;
      })
      .attr('cy', (d: any) => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.y;
      })
      .attr('r', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') {
          return isHighlighted ? dynamicSizes.highlightedRadius + 2 : dynamicSizes.baseRadius + 2; // Larger for prominent outliers
        }
        return isHighlighted ? dynamicSizes.highlightedRadius : dynamicSizes.baseRadius;
      })
      .attr('fill', (d: any) => colorFn(d.originalIndex))
      .attr('opacity', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return 1; // Full opacity for prominent outliers
        return isHighlighted ? 1 : dynamicSizes.baseOpacity;
      })
      .attr('stroke', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return '#000000'; // Black border for prominent outliers
        return isHighlighted ? 'black' : 'none';
      })
      .attr('stroke-width', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return 2; // Thick border for prominent outliers
        return isHighlighted ? 2 : 0;
      })
      .style('cursor', 'pointer')
      .on('click', (event: any, d: any) => {
        event.stopPropagation();
        console.log('[SVG-CHUNKED] Point clicked:', d.originalIndex);
        emit('pointClicked', { originalIndex: d.originalIndex });
      })
      .on('mouseover', function(event: any, d: any) {
        // Throttle hover events for better performance in chunked rendering
        const now = performance.now();
        if (now - lastHoverTime < HOVER_THROTTLE_MS) {
          if (hoverThrottleTimeout) {
            clearTimeout(hoverThrottleTimeout);
          }
          
          hoverThrottleTimeout = setTimeout(() => {
            handleMouseOver(event, d);
          }, HOVER_THROTTLE_MS);
          return;
        }
        
        lastHoverTime = now;
        handleMouseOver(event, d);
      })
      .on('mouseout', function() {
        // Cancel any pending hover events
        if (hoverThrottleTimeout) {
          clearTimeout(hoverThrottleTimeout);
          hoverThrottleTimeout = null;
        }
        hoveredPointInfo.value = null;
      });
    
    currentIndex = endIndex;
    
    // Continue with next chunk if there are more points
    if (currentIndex < dataForPlot.length) {
      requestAnimationFrame(renderChunk);
    } else {
      console.log(`ClusterScatterPlot: Chunked rendering completed for ${dataForPlot.length} points`);
    }
  }
  
  // Start chunked rendering
  requestAnimationFrame(renderChunk);
}

function drawClusters() {
  if (!svg.value || !props.data || !props.data.points) return;

  const startTime = performance.now();
  console.log('ClusterScatterPlot: Starting render...');

  const { points, labels, centers, color_map, scatter_colors, dimensionality_reduction } = props.data;
  const activeDR = dimensionality_reduction;
  const currentWidth = props.width;
  const currentHeight = props.height;
  const margin = { top: 20, right: 30, bottom: 60, left: 70 }; // Increased bottom/left for labels

  const svgEl = d3.select(svg.value);
  svgEl.selectAll('*').remove();

  // For high-dimensional datasets, points array may be empty but PCA data should be available
  // Check if we have any data to display - either original points or dimensionality reduction data
  const hasOriginalPoints = points.length > 0;
  const hasPCAData = activeDR?.pca && Array.isArray(activeDR.pca) && activeDR.pca.length > 0;
  const hasUMAPData = activeDR?.umap && Array.isArray(activeDR.umap) && activeDR.umap.length > 0;
  const hasTSNEData = activeDR?.tsne && Array.isArray(activeDR.tsne) && activeDR.tsne.length > 0;
  
  // For high-dimensional datasets, use PCA data as the primary point source when original points are empty
  const effectivePoints = hasOriginalPoints ? points : (hasPCAData ? activeDR?.pca || [] : []);
  const isUsingDRAsPoints = !hasOriginalPoints && hasPCAData;
  
  console.log(`[ClusterScatterPlot] Data status: original=${hasOriginalPoints ? points.length : 0}, PCA=${hasPCAData ? activeDR?.pca?.length || 0 : 0}, UMAP=${hasUMAPData ? activeDR?.umap?.length || 0 : 0}, t-SNE=${hasTSNEData ? activeDR?.tsne?.length || 0 : 0}, using=${isUsingDRAsPoints ? 'PCA' : 'original'} as points`);
  
  if (effectivePoints.length === 0) {
    svgEl.append('text')
      .attr('x', currentWidth / 2)
      .attr('y', currentHeight / 2)
      .attr('text-anchor', 'middle')
      .text('No data to display.');
    return;
  }

  // Performance optimization: Log data processing time for large datasets
  const dataProcessStart = performance.now();
  const dataForPlot = effectivePoints.map((p, sampledIndex) => {
    // Convert sampled index to original index if data was sampled
    const originalIndex = props.data?.index_mapping?.sampled_to_original?.[sampledIndex] ?? sampledIndex;
    
    // For high-dimensional datasets using PCA as points, we need to handle axis data differently
    const xVal = isUsingDRAsPoints ? 
      (props.selectedXAxis === 'pca-0' ? p[0] : (props.selectedXAxis === 'pca-1' ? p[1] : getAxisData(sampledIndex, props.selectedXAxis, effectivePoints, activeDR))) :
      getAxisData(sampledIndex, props.selectedXAxis, effectivePoints, activeDR);
    const yVal = isUsingDRAsPoints ? 
      (props.selectedYAxis === 'pca-0' ? p[0] : (props.selectedYAxis === 'pca-1' ? p[1] : getAxisData(sampledIndex, props.selectedYAxis, effectivePoints, activeDR))) :
      getAxisData(sampledIndex, props.selectedYAxis, effectivePoints, activeDR);
    return { x: xVal, y: yVal, originalIndex, sampledIndex };
  }).filter(d => d.x !== undefined && d.y !== undefined);
  const dataProcessEnd = performance.now();
  
  if (effectivePoints.length > 1000) {
    console.log(`ClusterScatterPlot: Data processing took ${(dataProcessEnd - dataProcessStart).toFixed(2)}ms for ${effectivePoints.length} points`);
  }

  if (dataForPlot.length === 0) {
    svgEl.append('text')
      .attr('x', currentWidth / 2)
      .attr('y', currentHeight / 2)
      .attr('text-anchor', 'middle')
      .text('Selected axes not available for all points.');
    return;
  }
  
  const allX = dataForPlot.map(p => p.x as number);
  const allY = dataForPlot.map(p => p.y as number);

  const xExtent = d3.extent(allX) as [number, number] | [undefined, undefined];
  const yExtent = d3.extent(allY) as [number, number] | [undefined, undefined];

  if (xExtent[0] === undefined || xExtent[1] === undefined || yExtent[0] === undefined || yExtent[1] === undefined) {
    return;
  }

  const xScale = d3.scaleLinear().domain(xExtent as [number, number]).nice().range([margin.left, currentWidth - margin.right]);
  const yScale = d3.scaleLinear().domain(yExtent as [number, number]).nice().range([currentHeight - margin.bottom, margin.top]);

  // Create groups for different layers
  const g = svgEl.append("g"); // Group for zoomable content
  const axisGroup = svgEl.append("g"); // Group for axes (not zoomable)
  
  // Set up clipping region to prevent points from rendering outside plot area
  const clipId = `clip-${Math.random().toString(36).substr(2, 9)}`;
  svgEl.append("defs")
    .append("clipPath")
    .attr("id", clipId)
    .append("rect")
    .attr("x", margin.left)
    .attr("y", margin.top)
    .attr("width", currentWidth - margin.left - margin.right)
    .attr("height", currentHeight - margin.top - margin.bottom);
  
  // Apply clipping to the zoomable content
  g.attr("clip-path", `url(#${clipId})`);

  // Add dynamic axes with zoom-aware tick spacing
  const updateAxes = () => {
    // Clear existing axes
    axisGroup.selectAll('.x-axis').remove();
    axisGroup.selectAll('.y-axis').remove();
    
    // Calculate zoom scale and translation
    const zoomScale = zoom.value.scale;
    const zoomTranslateX = zoom.value.x;
    const zoomTranslateY = zoom.value.y;
    
    // Calculate the visible data range based on current zoom and pan
    const visibleXMin = xScale.invert((margin.left - zoomTranslateX) / zoomScale);
    const visibleXMax = xScale.invert((currentWidth - margin.right - zoomTranslateX) / zoomScale);
    const visibleYMin = yScale.invert((currentHeight - margin.bottom - zoomTranslateY) / zoomScale);
    const visibleYMax = yScale.invert((margin.top - zoomTranslateY) / zoomScale);
    
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
    
    const xRange = Math.abs(visibleXMax - visibleXMin);
    const yRange = Math.abs(visibleYMax - visibleYMin);
    const xStepSize = getOptimalStepSize(xRange);
    const yStepSize = getOptimalStepSize(yRange);
    
    // Generate tick values
    const xTicks = [];
    const yTicks = [];
    
    const xStartTick = Math.ceil(visibleXMin / xStepSize) * xStepSize;
    const yStartTick = Math.ceil(visibleYMin / yStepSize) * yStepSize;
    
    for (let tick = xStartTick; tick <= visibleXMax; tick += xStepSize) {
      if (tick >= visibleXMin) xTicks.push(tick);
    }
    
    for (let tick = yStartTick; tick <= visibleYMax; tick += yStepSize) {
      if (tick >= visibleYMin) yTicks.push(tick);
    }
    
    // Create custom axes with calculated ticks
    const xAxisGroup = axisGroup.append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0,${currentHeight - margin.bottom})`);
    
    const yAxisGroup = axisGroup.append("g")
      .attr("class", "y-axis")
      .attr("transform", `translate(${margin.left},0)`);
    
    // Render X axis ticks
    xTicks.forEach(tick => {
      const xPos = (xScale(tick) * zoomScale) + zoomTranslateX;
      if (xPos >= margin.left && xPos <= currentWidth - margin.right) {
        xAxisGroup.append('line')
          .attr('x1', xPos)
          .attr('x2', xPos)
          .attr('y1', 0)
          .attr('y2', 6)
          .attr('stroke', 'currentColor')
          .attr('stroke-width', 1);
        
        // Format tick labels based on step size magnitude
        const precision = Math.max(0, -Math.floor(Math.log10(xStepSize)) + 1);
        const label = precision > 0 ? tick.toFixed(precision) : tick.toString();
        
        xAxisGroup.append('text')
          .attr('x', xPos)
          .attr('y', 20)
          .attr('text-anchor', 'middle')
          .attr('fill', 'currentColor')
          .style('font-size', '11px')
          .text(label);
      }
    });
    
    // Render Y axis ticks
    yTicks.forEach(tick => {
      const yPos = (yScale(tick) * zoomScale) + zoomTranslateY;
      if (yPos >= margin.top && yPos <= currentHeight - margin.bottom) {
        yAxisGroup.append('line')
          .attr('x1', -6)
          .attr('x2', 0)
          .attr('y1', yPos)
          .attr('y2', yPos)
          .attr('stroke', 'currentColor')
          .attr('stroke-width', 1);
        
        // Format tick labels based on step size magnitude
        const precision = Math.max(0, -Math.floor(Math.log10(yStepSize)) + 1);
        const label = precision > 0 ? tick.toFixed(precision) : tick.toString();
        
        yAxisGroup.append('text')
          .attr('x', -10)
          .attr('y', yPos + 4)
          .attr('text-anchor', 'end')
          .attr('fill', 'currentColor')
          .style('font-size', '11px')
          .text(label);
      }
    });
    
    // Add axis lines
    xAxisGroup.append('line')
      .attr('x1', margin.left)
      .attr('x2', currentWidth - margin.right)
      .attr('y1', 0)
      .attr('y2', 0)
      .attr('stroke', 'currentColor')
      .attr('stroke-width', 1);
    
    yAxisGroup.append('line')
      .attr('x1', 0)
      .attr('x2', 0)
      .attr('y1', margin.top)
      .attr('y2', currentHeight - margin.bottom)
      .attr('stroke', 'currentColor')
      .attr('stroke-width', 1);
    
    // Add axis labels
    xAxisGroup.append("text")
      .attr("y", margin.bottom - 5)
      .attr("x", currentWidth / 2)
      .attr("text-anchor", "middle")
      .attr("fill", "currentColor")
      .style("font-size", "12px")
      .text(xAxisLabel.value);
    
    yAxisGroup.append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", -margin.left + 15)
      .attr("x", -(currentHeight / 2))
      .attr("text-anchor", "middle")
      .attr("fill", "currentColor")
      .style("font-size", "12px")
      .text(yAxisLabel.value);
  };
  
  // Initial axis render
  updateAxes();
  
  // Store updateAxes function for zoom updates
  (svgEl.node() as any).__updateAxes = updateAxes;
    
  const labelToColor = color_map;
  let colorFn: (originalIndex: number) => string;

  // Ground truth coloring support
  if (props.selectedColorBy === 'ground_truth' && props.data.ground_truth) {
    const groundTruthColors = props.data.ground_truth.colors;
    const groundTruthColorMap = props.data.ground_truth.color_map;
    const groundTruthLabels = props.data.ground_truth.labels;
    
    if (groundTruthColors && Array.isArray(groundTruthColors) && groundTruthColors.length === effectivePoints.length) {
      colorFn = (originalIndex: number) => groundTruthColors[originalIndex];
    } else if (groundTruthColorMap && groundTruthLabels && Array.isArray(groundTruthLabels)) {
      colorFn = (originalIndex: number) => groundTruthColorMap[String(groundTruthLabels[originalIndex])] || '#cccccc';
    } else {
      const d3ColorScale = d3.scaleOrdinal(d3.schemeCategory10);
      colorFn = (originalIndex: number) => {
        if (groundTruthLabels && groundTruthLabels[originalIndex] !== undefined) {
          return d3ColorScale(String(groundTruthLabels[originalIndex]));
        }
        return '#cccccc';
      };
    }
  } else {
    // Default predicted cluster coloring
    if (scatter_colors && Array.isArray(scatter_colors) && scatter_colors.length === effectivePoints.length) {
      colorFn = (originalIndex: number) => {
        // Check for outliers (label -1) first
        if (labels && String(labels[originalIndex]) === '-1') {
          return props.selectedOutlierStyle === 'subtle' ? '#000000' : '#FF0000'; // Black for subtle, red for prominent
        }
        return scatter_colors[originalIndex];
      };
    } else if (labelToColor && labels && Array.isArray(labels)) {
      colorFn = (originalIndex: number) => {
        const label = String(labels[originalIndex]);
        // Special handling for outliers (label -1) - color based on style setting
        if (label === '-1') {
          return props.selectedOutlierStyle === 'subtle' ? '#000000' : '#FF0000'; // Black for subtle, red for prominent
        }
        return labelToColor[label] || '#cccccc';
      };
    } else {
      const d3ColorScale = d3.scaleOrdinal(d3.schemeCategory10);
      colorFn = (originalIndex: number) => {
        if (labels && labels[originalIndex] !== undefined) {
          const label = String(labels[originalIndex]);
          // Special handling for outliers (label -1) - color based on style setting
          if (label === '-1') {
            return props.selectedOutlierStyle === 'subtle' ? '#000000' : '#FF0000'; // Black for subtle, red for prominent
          }
          return d3ColorScale(label);
        }
        return '#cccccc';
      };
    }
  }
  
  const highlightedSet = new Set(adjustedHighlightedIndices.value || []);
  const dynamicSizes = getDynamicSizes(dataForPlot.length);

  // Store centers data for zoom updates
  let centersForPlot = null;
  if (centers && centers.length > 0) {
    centersForPlot = centers.map((center, i) => {
        let xVal, yVal;
        if (props.selectedXAxis.startsWith('feature-') && props.selectedYAxis.startsWith('feature-')) {
            xVal = getAxisData(i, props.selectedXAxis, centers);
            yVal = getAxisData(i, props.selectedYAxis, centers);
        } else {
            xVal = centers[i]?.[0];
            yVal = centers[i]?.[1];
        }
        return { x: xVal, y: yVal, originalIndex: i };
    }).filter(c => c.x !== undefined && c.y !== undefined);
  }
  
  // Performance optimization: Use chunked rendering for large datasets
  if (dataForPlot.length > 500) {
    console.log(`ClusterScatterPlot: Using chunked rendering for ${dataForPlot.length} points`);
    renderPointsInChunks(g, dataForPlot, xScale, yScale, colorFn, highlightedSet, labels, margin);
  } else {
    // Use dynamic sizing for smaller datasets too with zoom-aware transformations
    g.selectAll('circle')
      .data(dataForPlot)
      .enter()
      .append('circle')
      .attr('cx', d => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.x;
      })
      .attr('cy', d => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.y;
      })
      .attr('r', d => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') {
          return isHighlighted ? dynamicSizes.highlightedRadius + 2 : dynamicSizes.baseRadius + 2; // Larger for prominent outliers
        }
        return isHighlighted ? dynamicSizes.highlightedRadius : dynamicSizes.baseRadius;
      })
      .attr('fill', d => colorFn(d.originalIndex))
      .attr('opacity', d => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return 1; // Full opacity for prominent outliers
        return isHighlighted ? 1 : dynamicSizes.baseOpacity;
      })
      .attr('stroke', d => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return '#000000'; // Black border for prominent outliers
        return isHighlighted ? 'black' : 'none';
      })
      .attr('stroke-width', d => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return 2; // Thick border for prominent outliers
        return isHighlighted ? 2 : 0;
      })
      .style('cursor', 'pointer')
      .on('click', (event: any, d: any) => {
        event.stopPropagation();
        console.log('[SVG] Point clicked:', d.originalIndex);
        emit('pointClicked', { originalIndex: d.originalIndex });
      })
      .on('mouseover', function(event: any, d: any) {
        // Throttle hover events for better performance in direct rendering
        const now = performance.now();
        if (now - lastHoverTime < HOVER_THROTTLE_MS) {
          if (hoverThrottleTimeout) {
            clearTimeout(hoverThrottleTimeout);
          }
          
          hoverThrottleTimeout = setTimeout(() => {
            handleMouseOver(event, d);
          }, HOVER_THROTTLE_MS);
          return;
        }
        
        lastHoverTime = now;
        handleMouseOver(event, d);
      })
      .on('mouseout', function() {
        // Cancel any pending hover events
        if (hoverThrottleTimeout) {
          clearTimeout(hoverThrottleTimeout);
          hoverThrottleTimeout = null;
        }
        hoveredPointInfo.value = null;
      });
  }

  if (centersForPlot && centersForPlot.length > 0) {
    g.selectAll('rect')
      .data(centersForPlot)
      .enter()
      .append('rect')
      .attr('x', d => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.x - 8;
      })
      .attr('y', d => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.y - 8;
      })
      .attr('width', 16)
      .attr('height', 16)
      .attr('fill', (d, i) => {
          if (labels && labelToColor && labels.length > 0) {
            const d3ColorScale = d3.scaleOrdinal(d3.schemeCategory10);
            return d3ColorScale(String(d.originalIndex));
          }
          return 'black';
      })
      .attr('stroke', '#333')
      .attr('stroke-width', 2);
  }
  // Setup mouse events for zoom and pan
  setupMouseEvents();
  
  // Store the updateAxes function and other data for zoom updates
  (svgEl.node() as any).__renderData = {
    dataForPlot,
    xScale,
    yScale,
    colorFn,
    highlightedSet,
    labels,
    margin,
    centersForPlot
  };

  const endTime = performance.now();
  const renderTime = endTime - startTime;
  console.log(`ClusterScatterPlot: Render completed in ${renderTime.toFixed(2)}ms for ${points.length} points`);
  
  // Log performance warning for large datasets
  if (renderTime > 1000) {
    console.warn(`ClusterScatterPlot: Slow render detected (${renderTime.toFixed(2)}ms). Consider optimizations for ${points.length} points.`);
  }
}

// Optimized watchers - split to prevent unnecessary re-renders from dimensionality reduction updates
// Watch for core data changes that affect visualization
watch(() => [
  props.data?.points, 
  props.data?.labels, 
  props.data?.centers,
  props.data?.scatter_colors,
  props.data?.color_map,
  props.data?.ground_truth,
  props.width, 
  props.height, 
  props.selectedXAxis, 
  props.selectedYAxis, 
  props.selectedColorBy
], () => {
  // Reset zoom when data changes (new run selected)
  zoom.value = { x: 0, y: 0, scale: 1 };
  drawClusters();
}, { immediate: true, deep: false });

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
  // Reset zoom when dimensionality reduction data changes
  zoom.value = { x: 0, y: 0, scale: 1 };
  drawClusters();
}, { immediate: false, deep: false });

// Optimized highlighting update logic
let highlightUpdateInProgress = false;
let lastHighlightedIndices: number[] = [];

watch(() => adjustedHighlightedIndices.value, (newIndices) => {
  // Prevent recursive updates and unnecessary redraws
  if (highlightUpdateInProgress) return;
  
  // Only update if we have a valid SVG and data
  if (!svg.value || !props.data?.points) return;
  
  // Quick check if arrays are actually different to avoid unnecessary updates
  if (arraysEqual(newIndices, lastHighlightedIndices)) return;
  
  // Set flag to prevent recursion
  highlightUpdateInProgress = true;
  lastHighlightedIndices = [...newIndices];
  
  // Update highlighting efficiently
  updateHighlighting(newIndices);
  
  // Clear flag after minimal delay
  requestAnimationFrame(() => {
    highlightUpdateInProgress = false;
  });
}, { immediate: false });

function arraysEqual(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false;
  const sortedA = [...a].sort((x, y) => x - y);
  const sortedB = [...b].sort((x, y) => x - y);
  for (let i = 0; i < sortedA.length; i++) {
    if (sortedA[i] !== sortedB[i]) return false;
  }
  return true;
}

function updateHighlighting(indices: number[]) {
  if (!svg.value) return;
  
  const highlightStart = performance.now();
  const svgEl = d3.select(svg.value);
  const highlightedSet = new Set(indices);
  const { labels, points } = props.data || {};
  
  // Calculate dynamic sizes based on current data size
  const pointCount = points?.length || 0;
  const dynamicSizes = getDynamicSizes(pointCount);
  
  // Get stored render data for coordinate transformations
  const renderData = (svgEl.node() as any).__renderData;
  if (!renderData) {
    // Fallback to basic highlighting if render data not available
    svgEl.selectAll('circle')
      .attr('r', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') {
          return isHighlighted ? dynamicSizes.highlightedRadius + 2 : dynamicSizes.baseRadius + 2;
        }
        return isHighlighted ? dynamicSizes.highlightedRadius : dynamicSizes.baseRadius;
      })
      .attr('opacity', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return 1;
        return isHighlighted ? 1 : dynamicSizes.baseOpacity;
      })
      .attr('stroke', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return '#000000';
        return isHighlighted ? 'black' : 'none';
      })
      .attr('stroke-width', (d: any) => {
        const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
        const isHighlighted = highlightedSet.has(d.originalIndex);
        if (isOutlier && props.selectedOutlierStyle === 'prominent') return 2;
        return isHighlighted ? 2 : 0;
      });
    return;
  }
  
  const { xScale, yScale } = renderData;
  
  // Update circle highlighting with dynamic sizing and zoom-aware positioning
  svgEl.selectAll('circle')
    .attr('cx', (d: any) => {
      const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
      return transformed.x;
    })
    .attr('cy', (d: any) => {
      const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
      return transformed.y;
    })
    .attr('r', (d: any) => {
      const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
      const isHighlighted = highlightedSet.has(d.originalIndex);
      if (isOutlier && props.selectedOutlierStyle === 'prominent') {
        return isHighlighted ? dynamicSizes.highlightedRadius + 2 : dynamicSizes.baseRadius + 2;
      }
      return isHighlighted ? dynamicSizes.highlightedRadius : dynamicSizes.baseRadius;
    })
    .attr('opacity', (d: any) => {
      const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
      const isHighlighted = highlightedSet.has(d.originalIndex);
      if (isOutlier && props.selectedOutlierStyle === 'prominent') return 1;
      return isHighlighted ? 1 : dynamicSizes.baseOpacity;
    })
    .attr('stroke', (d: any) => {
      const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
      const isHighlighted = highlightedSet.has(d.originalIndex);
      if (isOutlier && props.selectedOutlierStyle === 'prominent') return '#000000';
      return isHighlighted ? 'black' : 'none';
    })
    .attr('stroke-width', (d: any) => {
      const isOutlier = labels && String(labels[d.originalIndex]) === '-1';
      const isHighlighted = highlightedSet.has(d.originalIndex);
      if (isOutlier && props.selectedOutlierStyle === 'prominent') return 2;
      return isHighlighted ? 2 : 0;
    });
  
  // Update centers if they exist
  if (renderData.centersForPlot) {
    svgEl.selectAll('rect')
      .attr('x', (d: any) => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.x - 8;
      })
      .attr('y', (d: any) => {
        const transformed = transformPoint(d.x as number, d.y as number, xScale, yScale);
        return transformed.y - 8;
      });
  }
  
  // Update axes
  const updateAxes = (svgEl.node() as any).__updateAxes;
  if (updateAxes) {
    updateAxes();
  }
  
  const highlightEnd = performance.now();
  if (indices.length > 100) {
    console.log(`ClusterScatterPlot: Highlighting update took ${(highlightEnd - highlightStart).toFixed(2)}ms for ${indices.length} highlighted points`);
  }
}

onMounted(() => {
  drawClusters();
});

onBeforeUnmount(() => {
  debug('[ClusterScatterPlot] Starting comprehensive cleanup');
  
  // Reset update flags and data
  highlightUpdateInProgress = false;
  lastHighlightedIndices = [];
  
  // Comprehensive D3 cleanup to prevent memory leaks
  if (svg.value) {
    const svgEl = d3.select(svg.value);
    
    // Interrupt any ongoing transitions
    svgEl.selectAll('*').interrupt();
    
    // Remove all event listeners with namespaces
    svgEl.selectAll('circle')
      .on('mouseover.scatter', null)
      .on('mouseout.scatter', null)
      .on('mouseenter.scatter', null)
      .on('mouseleave.scatter', null)
      .on('click.scatter', null);
    
    svgEl.selectAll('rect')
      .on('mouseover.scatter', null)
      .on('mouseout.scatter', null)
      .on('click.scatter', null);
    
    svgEl.selectAll('text')
      .on('mouseover.scatter', null)
      .on('mouseout.scatter', null);
    
    // Remove custom mouse events
    removeMouseEvents();
    
    // Remove zoom and drag behaviors
    svgEl.on('.zoom', null)
         .on('.drag', null)
         .on('.brush', null);
    
    // Remove other potential event listeners
    svgEl.on('click', null)
         .on('mouseover', null)
         .on('mouseout', null)
         .on('wheel', null)
         .on('touchstart', null)
         .on('touchmove', null)
         .on('touchend', null);
    
    // Clear all SVG content
    svgEl.selectAll('*').remove();
  }
  
  // Clean up any remaining tooltips or overlays
  d3.selectAll('.scatter-tooltip').remove();
  d3.selectAll('.scatter-overlay').remove();
  
  // Force garbage collection in development
  if (process.env.NODE_ENV === 'development') {
    setTimeout(() => {
      forceGarbageCollection();
      debug('[ClusterScatterPlot] Cleanup completed');
    }, 100);
  }
});
</script>

<style scoped>
.scatter-plot-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  /* Prevent text selection/highlighting during pan/zoom */
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
}

svg {
  display: block;
  max-width: 100%;
  max-height: 100%;
  margin: 0 auto;
  /* Ensure default cursor is visible */
  cursor: default;
}

/* Prevent axis text from being selected or capturing drag events */
svg text {
  -webkit-user-select: none;
  -moz-user-select: none;
  -ms-user-select: none;
  user-select: none;
  pointer-events: none;
}

/* Ensure interactive elements have visible cursors */
svg circle:hover,
svg rect:hover {
  cursor: pointer !important;
}

/* Custom crosshair cursor for the SVG area when not hovering over points */
svg:not(:hover circle):not(:hover rect) {
  cursor: url('data:image/svg+xml;charset=utf-8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g stroke="%23000000" stroke-width="2" fill="none"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></g><g stroke="%23ffffff" stroke-width="1" fill="none"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></g></svg>') 12 12, crosshair;
}

/* SVG tooltip styles */
.svg-tooltip {
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
</style>
