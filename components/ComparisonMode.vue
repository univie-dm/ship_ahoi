<template>
  <div v-if="show" class="comparison-section">
    <div class="comparison-header">
      <div class="comparison-header-main">
        <h3>Run Comparison ({{ selectedRuns.length }} / 5 runs)</h3>
        
        <!-- Axis Selection for Scatter Plot Previews -->
        <div v-if="selectedRuns.length > 0" class="axis-controls-compact">
          <span class="axis-controls-label">Plot Axes:</span>
          <select :value="props.selectedXAxis" @input="$emit('update:selectedXAxis', $event.target.value)" class="axis-select-compact">
            <option v-for="axis in availableAxes" :key="axis.value" :value="axis.value">
              {{ axis.label }}
            </option>
          </select>
          <span class="axis-separator">×</span>
          <select :value="props.selectedYAxis" @input="$emit('update:selectedYAxis', $event.target.value)" class="axis-select-compact">
            <option v-for="axis in availableAxes" :key="axis.value" :value="axis.value">
              {{ axis.label }}
            </option>
          </select>
        </div>
      </div>
      
      <div class="comparison-actions">
        <!-- Mobile View Toggle -->
        <div v-if="showMobileViewToggle" class="mobile-view-toggle">
          <button 
            @click="$emit('update:mobileViewMode', 'cards')"
            :class="['view-toggle-btn', { active: props.mobileViewMode === 'cards' }]"
          >
            📱 Cards
          </button>
          <button 
            @click="$emit('update:mobileViewMode', 'table')"
            :class="['view-toggle-btn', { active: props.mobileViewMode === 'table' }]"
          >
            📊 Table
          </button>
        </div>
        
        <button @click="$emit('exitComparison')" class="exit-comparison-btn">
          Exit Comparison
        </button>
      </div>
    </div>

    <div class="comparison-content">
      <!-- Metrics Overview -->
      <div class="comparison-card">
        <div class="metrics-header">
          <h4>Performance Metrics Comparison</h4>
          <div class="metric-selector">
            <label for="metricSelect">Compare:</label>
            <select 
              id="metricSelect"
              :value="props.selectedMetric" 
              @input="$emit('update:selectedMetric', $event.target.value); $emit('renderMetricsChart')"
              class="metric-select"
            >
              <option 
                v-for="metric in availableMetrics" 
                :key="metric.key" 
                :value="metric.key"
              >
                {{ metric.name }}
              </option>
            </select>
            <div class="metric-info" v-if="selectedMetricInfo">
              <span class="metric-description">{{ selectedMetricInfo.description }}</span>
              <span class="metric-direction" :class="selectedMetricInfo.higher_better ? 'higher-better' : 'lower-better'">
                {{ selectedMetricInfo.higher_better ? '↑ Higher is better' : '↓ Lower is better' }}
              </span>
            </div>
          </div>
        </div>
        <div ref="metricsChart" class="chart-container"></div>
      </div>

      <!-- Clustering Results Visualization -->
      <div class="comparison-card full-width">
        <h4>Clustering Results Visualization</h4>
        <div class="results-comparison-grid" :class="getGridLayoutClass(selectedRuns.length)">
          <div v-for="run in selectedRuns" :key="run.id" class="result-comparison-panel" :class="getPanelSizeClass(selectedRuns.length)">
            <div class="panel-header">
              <h5>{{ formatRunTitle(run) }}</h5>
              <div class="panel-actions">
                <div class="run-badge" :class="getRunBadgeClass(run)">
                  {{ run.treeType }}
                </div>
              </div>
            </div>
            <div :ref="(el) => setChartRef(run.id, el)" class="comparison-chart" :class="getChartSizeClass(selectedRuns.length)"></div>
            <div class="panel-metrics">
              <div class="metric-row">
                <span class="metric-label">Clusters:</span>
                <span class="metric-value">{{ getActualClusterCount(run) }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Silhouette:</span>
                <span class="metric-value" :class="getBestMetricClass('silhouetteScore', run.metrics?.silhouetteScore, selectedRuns)">
                  {{ formatMetric(run.metrics?.silhouetteScore, 3) }}
                </span>
              </div>
              <div class="metric-row">
                <span class="metric-label">DB Index:</span>
                <span class="metric-value" :class="getBestMetricClass('dbIndex', run.metrics?.dbIndex, selectedRuns)">
                  {{ formatMetric(run.metrics?.dbIndex, 3) }}
                </span>
              </div>
              <div class="metric-row">
                <span class="metric-label">C-H Index:</span>
                <span class="metric-value" :class="getBestMetricClass('calinskiHarabasz', run.metrics?.calinskiHarabasz, selectedRuns)">
                  {{ formatMetric(run.metrics?.calinskiHarabasz, 2) }}
                </span>
              </div>
              <div class="metric-row">
                <span class="metric-label">ARI:</span>
                <span class="metric-value" :class="getBestMetricClass('ari', run.metrics?.ari, selectedRuns)">
                  {{ formatMetric(run.metrics?.ari, 3) }}
                </span>
              </div>
              <div class="metric-row">
                <span class="metric-label">DISCO:</span>
                <span class="metric-value" :class="getBestMetricClass('discoScore', run.metrics?.discoScore, selectedRuns)">
                  {{ formatMetric(run.metrics?.discoScore, 3) }}
                </span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Points:</span>
                <span class="metric-value">{{ run.clusterData?.points?.length || 'N/A' }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Dataset:</span>
                <span class="metric-value">{{ run.dataset }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Comparison Table -->
      <div class="comparison-card full-width">
        <h4>Detailed Comparison</h4>
        <div v-show="!props.showMobileViewToggle || props.mobileViewMode === 'table'" class="comparison-table-wrapper">
          <table class="comparison-table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Dataset</th>
                <th>Algorithm</th>
                <th>Partition Method</th>
                <th>K Value</th>
                <th>Power</th>
                <th>Silhouette Score</th>
                <th>DB Index</th>
                <th>Calinski-Harabasz</th>
                <th>ARI</th>
                <th>DISCO</th>
                <th>Points</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="run in selectedRuns" :key="run.id">
                <td class="run-name-cell">{{ formatRunTitle(run) }}</td>
                <td>{{ run.dataset }}</td>
                <td>
                  <span class="algorithm-badge" :class="getRunBadgeClass(run)">
                    {{ run.treeType }}
                  </span>
                </td>
                <td>{{ run.partitionMethod }}</td>
                <td class="metric-cell">{{ getActualClusterCount(run) }}</td>
                <td class="metric-cell">{{ formatPower(run.selectedPower) }}</td>
                <td class="metric-cell" :class="getBestMetricClass('silhouetteScore', run.metrics?.silhouetteScore, selectedRuns)">
                  {{ formatMetric(run.metrics?.silhouetteScore, 3) }}
                </td>
                <td class="metric-cell" :class="getBestMetricClass('dbIndex', run.metrics?.dbIndex, selectedRuns)">
                  {{ formatMetric(run.metrics?.dbIndex, 3) }}
                </td>
                <td class="metric-cell" :class="getBestMetricClass('calinskiHarabasz', run.metrics?.calinskiHarabasz, selectedRuns)">
                  {{ formatMetric(run.metrics?.calinskiHarabasz, 2) }}
                </td>
                <td class="metric-cell" :class="getBestMetricClass('ari', run.metrics?.ari, selectedRuns)">
                  {{ formatMetric(run.metrics?.ari, 3) }}
                </td>
                <td class="metric-cell" :class="getBestMetricClass('discoScore', run.metrics?.discoScore, selectedRuns)">
                  {{ formatMetric(run.metrics?.discoScore, 3) }}
                </td>
                <td class="metric-cell">{{ run.clusterData?.points?.length || 'N/A' }}</td>
                <td class="date-cell">{{ formatDate(run.timestamp) }}</td>
                <td class="actions-cell">
                  <button @click="$emit('loadRun', run.id)" class="action-btn load-btn">Load</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <!-- Mobile Cards View -->
        <div v-show="props.showMobileViewToggle && props.mobileViewMode === 'cards'" class="mobile-cards">
          <div v-for="run in selectedRuns" :key="run.id" class="mobile-run-card">
            <div class="mobile-card-header">
              <h5>{{ formatRunTitle(run) }}</h5>
              <span class="run-badge" :class="getRunBadgeClass(run)">{{ run.treeType }}</span>
            </div>
            <div class="mobile-card-content">
              <div class="card-row">
                <span class="card-label">Dataset:</span>
                <span class="card-value">{{ run.dataset }}</span>
              </div>
              <div class="card-row">
                <span class="card-label">Algorithm:</span>
                <span class="card-value">{{ run.treeType }}</span>
              </div>
              <div class="card-row">
                <span class="card-label">Partition:</span>
                <span class="card-value">{{ run.partitionMethod }}</span>
              </div>
              <div class="card-row">
                <span class="card-label">Clusters:</span>
                <span class="card-value">{{ getActualClusterCount(run) }}</span>
              </div>
              <div class="card-row">
                <span class="card-label">Silhouette:</span>
                <span class="card-value" :class="getBestMetricClass('silhouetteScore', run.metrics?.silhouetteScore, selectedRuns)">
                  {{ formatMetric(run.metrics?.silhouetteScore, 3) }}
                </span>
              </div>
              <div class="card-row">
                <span class="card-label">DB Index:</span>
                <span class="card-value" :class="getBestMetricClass('dbIndex', run.metrics?.dbIndex, selectedRuns)">
                  {{ formatMetric(run.metrics?.dbIndex, 3) }}
                </span>
              </div>
              <div class="card-row">
                <span class="card-label">CH Index:</span>
                <span class="card-value" :class="getBestMetricClass('calinskiHarabasz', run.metrics?.calinskiHarabasz, selectedRuns)">
                  {{ formatMetric(run.metrics?.calinskiHarabasz, 2) }}
                </span>
              </div>
              <div class="card-row">
                <span class="card-label">ARI:</span>
                <span class="card-value" :class="getBestMetricClass('ari', run.metrics?.ari, selectedRuns)">
                  {{ formatMetric(run.metrics?.ari, 3) }}
                </span>
              </div>
              <div class="card-row">
                <span class="card-label">DISCO:</span>
                <span class="card-value" :class="getBestMetricClass('discoScore', run.metrics?.discoScore, selectedRuns)">
                  {{ formatMetric(run.metrics?.discoScore, 3) }}
                </span>
              </div>
              <div class="card-row">
                <span class="card-label">Points:</span>
                <span class="card-value">{{ run.clusterData?.points?.length || 'N/A' }}</span>
              </div>
              <div class="card-row">
                <span class="card-label">Date:</span>
                <span class="card-value">{{ formatDate(run.timestamp) }}</span>
              </div>
              <div class="card-actions">
                <button @click="$emit('loadRun', run.id)" class="mobile-load-btn">Load Run</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, watch } from 'vue'
import type { ClusterRun } from '~/composables/useGlobalState'
import * as d3 from 'd3'

interface Props {
  show: boolean
  selectedRuns: ClusterRun[]
  availableAxes: Array<{value: string, label: string}>
  availableMetrics: Array<{key: string, name: string, color: string, higher_better: boolean, description: string}>
  selectedMetricInfo: any
  showMobileViewToggle: boolean
  mobileViewMode: 'table' | 'cards'
  selectedXAxis: string
  selectedYAxis: string
  selectedMetric: string
}

interface Emits {
  (e: 'update:selectedXAxis', value: string): void
  (e: 'update:selectedYAxis', value: string): void
  (e: 'update:selectedMetric', value: string): void
  (e: 'update:mobileViewMode', value: 'table' | 'cards'): void
  (e: 'renderMetricsChart'): void
  (e: 'exitComparison'): void
  (e: 'loadRun', runId: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const metricsChart = ref<HTMLElement>()
const chartRefs = ref<Record<string, HTMLElement | null>>({})

const setChartRef = (runId: string, el: HTMLElement | null) => {
  if (el) {
    chartRefs.value[runId] = el
  } else {
    // Clean up when ref is removed
    if (chartRefs.value[runId]) {
      d3.select(chartRefs.value[runId]).selectAll('*').remove()
      delete chartRefs.value[runId]
    }
  }
}

// Utility functions
const formatDate = (timestamp: Date | string): string => {
  const d = new Date(timestamp);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatRunTitle = (run: ClusterRun): string => {
  return `${run.dataset} (${run.treeType})`
}

const getActualClusterCount = (run: ClusterRun): number => {
  if (run.actualClusterCount !== undefined && run.actualClusterCount !== null) {
    // Convert string to number if needed
    const count = typeof run.actualClusterCount === 'string' ? parseInt(run.actualClusterCount, 10) : run.actualClusterCount
    if (!isNaN(count)) return count
  }
  
  if (run.clusterData?.labels && Array.isArray(run.clusterData.labels)) {
    const uniqueLabels = new Set(run.clusterData.labels)
    return uniqueLabels.size
  }
  
  // Convert selectedK string to number if needed
  const selectedK = typeof run.selectedK === 'string' ? parseInt(run.selectedK, 10) : run.selectedK
  return selectedK || 0
}

const getRunBadgeClass = (run: ClusterRun): string => {
  switch (run.treeType.toLowerCase()) {
    case 'ship':
      return 'badge-ship'
    case 'kmeans':
      return 'badge-kmeans'
    case 'dbscan':
      return 'badge-dbscan'
    case 'hierarchical':
      return 'badge-hierarchical'
    default:
      return 'badge-default'
  }
}

const getBestMetricClass = (metricKey: string, value: number | undefined, runs: ClusterRun[]): string => {
  if (value === undefined || value === null) return ''
  
  const values = runs
    .map(r => r.metrics?.[metricKey as keyof typeof r.metrics])
    .filter(v => v !== undefined && v !== null) as number[]
  
  if (values.length <= 1) return ''
  
  const isHigherBetter = ['silhouetteScore', 'calinskiHarabasz', 'ari', 'discoScore'].includes(metricKey)
  const bestValue = isHigherBetter ? Math.max(...values) : Math.min(...values)
  
  return value === bestValue ? 'best-metric' : ''
}

const getGridLayoutClass = (count: number): string => {
  if (count <= 2) return 'grid-1-2'
  if (count <= 4) return 'grid-2-2'
  return 'grid-2-3' // Maximum 5 runs, use 2x3 grid
}

const getPanelSizeClass = (count: number): string => {
  if (count <= 2) return 'panel-large'
  if (count <= 4) return 'panel-medium'
  return 'panel-small' // For 5 runs
}

const getChartSizeClass = (count: number): string => {
  if (count <= 2) return 'chart-large'
  if (count <= 4) return 'chart-medium'
  return 'chart-small' // For 5 runs
}

const formatPower = (power: number | string | undefined | null): string => {
  if (power === undefined || power === null) return 'N/A'
  
  // Convert string to number if needed
  const numPower = typeof power === 'string' ? parseFloat(power) : power
  
  // Check if conversion failed
  if (isNaN(numPower)) return 'N/A'
  
  if (Number.isInteger(numPower)) return numPower.toString()
  return numPower.toFixed(2)
}

const formatMetric = (value: number | string | undefined | null, decimals: number = 3): string => {
  if (value === undefined || value === null) return 'N/A'
  
  // Convert string to number if needed
  const num = typeof value === 'string' ? parseFloat(value) : value
  
  // Check if conversion failed
  if (isNaN(num)) return 'N/A'
  
  return num.toFixed(decimals)
}

// Watch for changes in selected runs to clean up removed charts
watch(() => props.selectedRuns, (newRuns, oldRuns) => {
  if (oldRuns) {
    const oldRunIds = new Set(oldRuns.map(r => r.id))
    const newRunIds = new Set(newRuns.map(r => r.id))
    
    // Clean up charts for removed runs
    oldRunIds.forEach(runId => {
      if (!newRunIds.has(runId) && chartRefs.value[runId]) {
        d3.select(chartRefs.value[runId]).selectAll('*').remove()
        delete chartRefs.value[runId]
      }
    })
  }
}, { deep: true })

// Cleanup function
onBeforeUnmount(() => {
  // Clear all D3 selections and event listeners
  if (metricsChart.value) {
    d3.select(metricsChart.value).selectAll('*').remove()
  }
  
  // Clear chart refs
  Object.values(chartRefs.value).forEach(ref => {
    if (ref) {
      d3.select(ref).selectAll('*').remove()
    }
  })
  
  // Clear refs
  chartRefs.value = {}
})

defineExpose({
  metricsChart,
  chartRefs
})
</script>

<style scoped>
/* Main comparison section styles */
.comparison-section {
  margin-top: 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.comparison-header {
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 1rem;
}

.comparison-header-main h3 {
  margin: 0 0 1rem 0;
  color: #1e293b;
  font-size: 1.25rem;
  font-weight: 600;
}

.axis-controls-compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.axis-controls-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #64748b;
}

.axis-select-compact {
  padding: 0.375rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  background: white;
}

.axis-separator {
  font-weight: 600;
  color: #64748b;
}

.comparison-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.mobile-view-toggle {
  display: flex;
  gap: 0.25rem;
  margin-right: 0.5rem;
}

.view-toggle-btn {
  padding: 0.375rem 0.75rem;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.view-toggle-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.export-btn, .exit-comparison-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.detailed-btn {
  background: #3b82f6;
  color: white;
}

.detailed-btn:hover {
  background: #2563eb;
}

.visual-btn {
  background: #10b981;
  color: white;
}

.visual-btn:hover {
  background: #059669;
}

.viz-btn {
  background: #8b5cf6;
  color: white;
}

.viz-btn:hover {
  background: #7c3aed;
}

.exit-comparison-btn {
  background: #ef4444;
  color: white;
}

.exit-comparison-btn:hover {
  background: #dc2626;
}

/* Comparison content styles */
.comparison-content {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.comparison-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
}

.comparison-card.full-width {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.comparison-card h4 {
  margin: 0 0 1rem 0;
  color: #1e293b;
  font-size: 1.125rem;
  font-weight: 600;
}

/* Metrics header */
.metrics-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.metric-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.metric-selector label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #64748b;
}

.metric-select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.75rem;
}

.metric-description {
  color: #64748b;
}

.metric-direction {
  font-weight: 600;
}

.higher-better {
  color: #059669;
}

.lower-better {
  color: #dc2626;
}

/* Chart container */
.chart-container {
  min-height: 420px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fafafa;
  overflow: hidden;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
}

/* Results comparison grid */
.results-comparison-grid {
  display: grid;
  gap: 1rem;
  justify-content: center;
}

.grid-1-2 {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  width: 100%;
}

.grid-2-2 {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  width: 100%;
}

.grid-2-3 {
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  width: 100%;
}

.result-comparison-panel {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  background: #fafafa;
  overflow: hidden;
  max-width: 100%;
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.panel-header h5 {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: #1e293b;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.run-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-ship {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge-kmeans {
  background: #fef3c7;
  color: #d97706;
}

.badge-dbscan {
  background: #ecfdf5;
  color: #059669;
}

.badge-hierarchical {
  background: #fce7f3;
  color: #be185d;
}

.badge-default {
  background: #f3f4f6;
  color: #374151;
}


.comparison-chart {
  min-height: 200px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  margin-bottom: 1rem;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
}

.chart-large {
  min-height: 300px;
}

.chart-medium {
  min-height: 250px;
}

.chart-small {
  min-height: 200px;
}

/* Panel metrics */
.panel-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  font-size: 0.75rem;
}

.metric-row {
  display: flex;
  justify-content: space-between;
}

.metric-label {
  color: #64748b;
  font-weight: 500;
}

.metric-value {
  font-weight: 600;
  color: #1e293b;
}

.best-metric {
  color: #059669;
  background: #ecfdf5;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
}

/* Comparison table */
.comparison-table-wrapper {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.comparison-table th,
.comparison-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: middle;
  line-height: 1.5;
  height: auto;
  min-height: 3rem;
}

.comparison-table th {
  background: #f8fafc;
  font-weight: 600;
  color: #374151;
  vertical-align: middle;
}

.comparison-table tbody tr {
  height: 3rem;
}

.comparison-table tbody td {
  vertical-align: middle !important;
}

.algorithm-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.metric-cell.best-metric {
  background: #ecfdf5;
  color: #059669;
}

.action-btn {
  padding: 0.375rem 0.75rem;
  border: none;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.load-btn {
  background: #3b82f6;
  color: white;
}

.load-btn:hover {
  background: #2563eb;
}



/* Mobile cards */
.mobile-cards {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mobile-run-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  background: #fafafa;
}

.mobile-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.mobile-card-header h5 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.mobile-card-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.card-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-label {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}

.card-value {
  font-size: 0.875rem;
  color: #1e293b;
  font-weight: 600;
}

.card-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.mobile-load-btn {
  width: 100%;
  padding: 0.75rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.mobile-load-btn:hover {
  background: #2563eb;
}

/* Responsive design */
@media (max-width: 1024px) {
  .grid-1-2,
  .grid-2-2,
  .grid-2-3 {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    width: 100%;
  }
  
  .comparison-section,
  .comparison-card.full-width {
    width: 100%;
    max-width: 100%;
  }
  
  .panel-metrics {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .comparison-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .comparison-actions {
    justify-content: center;
  }
  
  .grid-1-2,
  .grid-2-2,
  .grid-2-3 {
    grid-template-columns: 1fr;
    width: 100%;
  }
  
  .comparison-section,
  .comparison-card.full-width {
    width: 100%;
    max-width: 100%;
  }
  
  .metrics-header {
    flex-direction: column;
  }
  
  .axis-controls-compact {
    justify-content: center;
  }
}

@media (max-width: 640px) {
  .comparison-section {
    margin: 1rem 0;
    border-radius: 8px;
  }
  
  .comparison-header,
  .comparison-content {
    padding: 1rem;
  }
  
  .comparison-actions {
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .export-btn,
  .exit-comparison-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>