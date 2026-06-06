<template>
  <div class="k-selection-plots">
    <div v-if="results" class="plots-grid">
      <!-- Elbow Method Plot -->
      <div v-show="selectedPlotType === 'elbow'" class="plot-card full-width">
        <div class="plot-header">
          <div class="plot-title-section">
            <h4>Elbow Method</h4>
            <p class="plot-description">Identifies optimal K where the rate of distortion improvement significantly drops.</p>
          </div>
        </div>
        <div ref="elbowPlot" class="plotly-plot"></div>
      </div>

      <!-- Silhouette Score Plot -->
      <div v-show="selectedPlotType === 'silhouette'" class="plot-card full-width">
        <div class="plot-header">
          <div class="plot-title-section">
            <h4>Silhouette Score</h4>
            <p class="plot-description">Measures how similar an object is to its own cluster compared to other clusters. Higher is better.</p>
          </div>
        </div>
        <div ref="silhouettePlot" class="plotly-plot"></div>
      </div>

      <!-- Davies-Bouldin Index Plot -->
      <div v-show="selectedPlotType === 'davies_bouldin'" class="plot-card full-width">
        <div class="plot-header">
          <div class="plot-title-section">
            <h4>Davies-Bouldin Index</h4>
            <p class="plot-description">Measures the ratio of within-cluster scatter to between-cluster separation. Lower is better.</p>
          </div>
        </div>
        <div ref="daviesBouldinPlot" class="plotly-plot"></div>
      </div>

      <!-- Calinski-Harabasz Index Plot -->
      <div v-show="selectedPlotType === 'calinski'" class="plot-card full-width">
        <div class="plot-header">
          <div class="plot-title-section">
            <h4>Calinski-Harabasz Index</h4>
            <p class="plot-description">Measures the ratio of between-cluster variance to within-cluster variance. Higher is better.</p>
          </div>
        </div>
        <div ref="calinskiHarabaszPlot" class="plotly-plot"></div>
      </div>

      <!-- DISCO Score Plot -->
      <div v-show="selectedPlotType === 'disco'" class="plot-card full-width">
        <div class="plot-header">
          <div class="plot-title-section">
            <h4>DISCO Score</h4>
            <p class="plot-description">Density-based Internal Separatedness Cluster Overlap metric. Higher is better.</p>
          </div>
        </div>
        <div ref="discoPlot" class="plotly-plot"></div>
      </div>
    </div>
    <div v-else class="empty-state">
      <p>Run K-Selection Analysis to see the plots.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as d3 from 'd3'

// Props
const props = defineProps({
  results: Object,
  selectedPlotType: { type: String, default: 'elbow' }
})

// Emits
const emit = defineEmits(['k-hovered', 'k-unhovered', 'k-clicked'])

// Plot refs
const elbowPlot = ref<HTMLElement | null>(null)
const silhouettePlot = ref<HTMLElement | null>(null)
const daviesBouldinPlot = ref<HTMLElement | null>(null)
const calinskiHarabaszPlot = ref<HTMLElement | null>(null)
const discoPlot = ref<HTMLElement | null>(null)

// D3 chart dimensions
const chartConfig = {
  width: 800,
  height: 400,
  margin: { top: 30, right: 40, bottom: 60, left: 80 }
}

// Plotting function with D3.js
const plotMetrics = () => {
  if (!props.results || !props.results.k_values || !props.results.metrics) {
    // Clear all plots if no results
    clearAllPlots()
    return
  }

  const kValues = props.results.k_values
  const metrics = props.results.metrics

  // Plot based on selected type
  switch (props.selectedPlotType) {
    case 'elbow':
      if (elbowPlot.value) {
        createD3Plot(
          elbowPlot.value,
          kValues,
          metrics.wcss,
          'Within-Cluster Sum of Squares (WCSS)',
          'WCSS vs. Number of Clusters (Elbow Method)',
          '#3498db'
        )
      }
      break
    case 'silhouette':
      if (silhouettePlot.value) {
        createD3Plot(
          silhouettePlot.value,
          kValues,
          metrics.silhouette,
          'Silhouette Score',
          'Silhouette Score vs. Number of Clusters',
          '#2ecc71',
          [-1, 1] // Y-axis range for silhouette
        )
      }
      break
    case 'davies_bouldin':
      if (daviesBouldinPlot.value) {
        createD3Plot(
          daviesBouldinPlot.value,
          kValues,
          metrics.davies_bouldin,
          'Davies-Bouldin Index',
          'Davies-Bouldin Index vs. Number of Clusters',
          '#e74c3c'
        )
      }
      break
    case 'calinski':
      if (calinskiHarabaszPlot.value) {
        createD3Plot(
          calinskiHarabaszPlot.value,
          kValues,
          metrics.calinski_harabasz,
          'Calinski-Harabasz Index',
          'Calinski-Harabasz Index vs. Number of Clusters',
          '#f39c12'
        )
      }
      break
    case 'disco':
      if (discoPlot.value) {
        createD3Plot(
          discoPlot.value,
          kValues,
          metrics.disco,
          'DISCO Score',
          'DISCO Score vs. Number of Clusters',
          '#8e44ad',
          [-1, 1]
        )
      }
      break
  }
}

// D3.js plot creation function
const createD3Plot = (
  container: HTMLElement,
  kValues: number[],
  metricValues: (number | null)[],
  yAxisLabel: string,
  title: string,
  color: string,
  yRange?: [number, number]
) => {
  // Clear previous plot
  d3.select(container).selectAll('*').remove()

  // Filter out null values
  const validData = kValues
    .map((k, i) => ({ k, value: metricValues[i] }))
    .filter(d => d.value !== null && d.value !== undefined)

  if (validData.length === 0) return

  // Set up dimensions
  const { width, height, margin } = chartConfig
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom

  // Create SVG
  const svg = d3
    .select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .style('font-family', 'Inter, sans-serif')

  const g = svg
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)

  // Set up scales
  const xScale = d3
    .scaleLinear()
    .domain(d3.extent(validData, d => d.k) as [number, number])
    .range([0, innerWidth])

  const yExtent = d3.extent(validData, d => d.value) as [number, number]
  const yDomain = yRange || [
    yExtent[0] - (yExtent[1] - yExtent[0]) * 0.1,
    yExtent[1] + (yExtent[1] - yExtent[0]) * 0.1
  ]
  
  const yScale = d3
    .scaleLinear()
    .domain(yDomain)
    .range([innerHeight, 0])

  // Create line generator
  const line = d3
    .line<{ k: number; value: number }>()
    .x(d => xScale(d.k))
    .y(d => yScale(d.value))
    .curve(d3.curveMonotoneX)

  // Add axes
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(xScale).tickFormat(d3.format('d')))
    .append('text')
    .attr('x', innerWidth / 2)
    .attr('y', 40)
    .attr('fill', 'black')
    .style('text-anchor', 'middle')
    .style('font-size', '12px')
    .text('Number of Clusters (k)')

  g.append('g')
    .call(d3.axisLeft(yScale))
    .append('text')
    .attr('transform', 'rotate(-90)')
    .attr('y', -60)
    .attr('x', -innerHeight / 2)
    .attr('fill', 'black')
    .style('text-anchor', 'middle')
    .style('font-size', '12px')
    .text(yAxisLabel)

  // Add title
  svg
    .append('text')
    .attr('x', width / 2)
    .attr('y', 20)
    .attr('text-anchor', 'middle')
    .style('font-size', '14px')
    .style('font-weight', 'bold')
    .text(title)

  // Add line
  g.append('path')
    .datum(validData)
    .attr('fill', 'none')
    .attr('stroke', color)
    .attr('stroke-width', 2)
    .attr('d', line)

  // Add points with hover and click interactions
  g.selectAll('.point')
    .data(validData)
    .enter()
    .append('circle')
    .attr('class', 'point')
    .attr('cx', d => xScale(d.k))
    .attr('cy', d => yScale(d.value))
    .attr('r', 5)
    .attr('fill', color)
    .attr('stroke', 'white')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .on('mouseover', function(event, d) {
      d3.select(this).attr('r', 7)
      emit('k-hovered', d.k)
      
      // Show tooltip
      const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'plot-tooltip')
        .style('opacity', 0)
        .style('position', 'absolute')
        .style('background', 'rgba(0,0,0,0.8)')
        .style('color', 'white')
        .style('padding', '8px')
        .style('border-radius', '4px')
        .style('font-size', '12px')
        .style('pointer-events', 'none')
        .style('z-index', '1000')

      tooltip.transition().duration(200).style('opacity', 1)
      tooltip.html(`k=${d.k}<br/>${yAxisLabel}: ${d.value.toFixed(3)}`)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px')
    })
    .on('mouseout', function(event, d) {
      d3.select(this).attr('r', 5)
      emit('k-unhovered')
      d3.selectAll('.plot-tooltip').remove()
    })
    .on('click', function(event, d) {
      emit('k-clicked', d.k)
    })
}

// Clear all plots
const clearAllPlots = () => {
  if (elbowPlot.value) d3.select(elbowPlot.value).selectAll('*').remove()
  if (silhouettePlot.value) d3.select(silhouettePlot.value).selectAll('*').remove()
  if (daviesBouldinPlot.value) d3.select(daviesBouldinPlot.value).selectAll('*').remove()
  if (calinskiHarabaszPlot.value) d3.select(calinskiHarabaszPlot.value).selectAll('*').remove()
  if (discoPlot.value) d3.select(discoPlot.value).selectAll('*').remove()
}

// Export functionality for D3 SVG charts

// Watch for results or visibility changes to re-plot
watch(
  () => [props.results, props.selectedPlotType],
  () => {
    plotMetrics()
  },
  { deep: true, immediate: true }
)

onMounted(() => {
  plotMetrics();
});

onUnmounted(() => {
  // Clean up D3 plots on unmount
  clearAllPlots()
  // Remove any tooltips that might be lingering
  d3.selectAll('.plot-tooltip').remove()
});
</script>

<style scoped>
.k-selection-plots {
  margin-top: 24px;
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.plots-grid {
  display: flex; /* Changed to flex to allow single item to fill */
  justify-content: center; /* Center the single plot */
  align-items: center; /* Center vertically */
  gap: 24px;
}

.plot-card {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  background: #fdfdfd;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  flex: 1; /* Allow the single plot to grow and fill space */
  max-width: 100%; /* Ensure it doesn't overflow */
}

.plot-card.full-width {
  width: 100%;
}

.plot-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  gap: 20px;
}

.plot-title-section {
  flex: 1;
}

.plot-card h4 {
  margin-top: 0;
  color: #2c3e50;
  font-size: 1.2rem;
  margin-bottom: 10px;
}

.plot-description {
  font-size: 0.9rem;
  color: #7f8c8d;
  margin-bottom: 0;
  min-height: 40px; /* Ensure consistent height for descriptions */
}

.plot-export-buttons {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  flex-shrink: 0;
}


.plotly-plot {
  width: 100%;
  height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.plotly-plot svg {
  max-width: 100%;
  height: auto;
}

.empty-state {
  text-align: center;
  padding: 50px;
  color: #6c757d;
}

/* D3 tooltip styles */
:global(.plot-tooltip) {
  position: absolute;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  font-family: 'Inter', system-ui, sans-serif;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .plots-grid {
    grid-template-columns: 1fr;
  }
}
</style> 