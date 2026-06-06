<template>
  <div class="run-comparison">
    <div class="comparison-overview">
      <h4>Comparison Overview</h4>
      <div class="overview-stats">
        <div class="stat-card">
          <div class="stat-number">{{ runs.length }}</div>
          <div class="stat-label">Runs</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ uniqueDatasets.length }}</div>
          <div class="stat-label">Datasets</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ uniqueAlgorithms.length }}</div>
          <div class="stat-label">Algorithms</div>
        </div>
      </div>
    </div>

    <div class="comparison-details">
      <div class="comparison-table-container">
        <table class="comparison-table">
          <thead>
            <tr>
              <th>Property</th>
              <th v-for="(run, index) in runs" :key="run.id" class="run-column">
                Run {{ index + 1 }}
                <div class="run-timestamp">{{ formatDate(run.timestamp) }}</div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="property-label">Dataset</td>
              <td v-for="run in runs" :key="`dataset-${run.id}`">
                <span class="dataset-name">{{ run.dataset }}</span>
                <div class="dataset-type">{{ run.parameters.sample }}</div>
              </td>
            </tr>
            <tr>
              <td class="property-label">Algorithm</td>
              <td v-for="run in runs" :key="`algo-${run.id}`">
                {{ run.treeType }}
              </td>
            </tr>
            <tr>
              <td class="property-label">Partition Method</td>
              <td v-for="run in runs" :key="`partition-${run.id}`">
                {{ run.partitionMethod }}
              </td>
            </tr>
            <tr>
              <td class="property-label">K Value</td>
              <td v-for="run in runs" :key="`k-${run.id}`">
                <span class="k-value">{{ run.selectedK }}</span>
              </td>
            </tr>
            <tr>
              <td class="property-label">Power</td>
              <td v-for="run in runs" :key="`power-${run.id}`">
                {{ run.selectedPower }}
              </td>
            </tr>
            <tr v-if="hasMetrics">
              <td class="property-label">Silhouette Score</td>
              <td v-for="run in runs" :key="`silhouette-${run.id}`">
                <span v-if="run.metrics?.silhouetteScore" class="metric-value">
                  {{ run.metrics.silhouetteScore.toFixed(3) }}
                </span>
                <span v-else class="no-metric">-</span>
              </td>
            </tr>
            <tr v-if="hasMetrics">
              <td class="property-label">Davies-Bouldin Index</td>
              <td v-for="run in runs" :key="`db-${run.id}`">
                <span v-if="run.metrics?.dbIndex" class="metric-value">
                  {{ run.metrics.dbIndex.toFixed(3) }}
                </span>
                <span v-else class="no-metric">-</span>
              </td>
            </tr>
            <tr v-if="hasMetrics">
              <td class="property-label">Calinski-Harabasz Index</td>
              <td v-for="run in runs" :key="`ch-${run.id}`">
                <span v-if="run.metrics?.calinskiHarabasz" class="metric-value">
                  {{ run.metrics.calinskiHarabasz.toFixed(3) }}
                </span>
                <span v-else class="no-metric">-</span>
              </td>
            </tr>
            <tr v-if="hasMetrics && hasAriMetrics">
              <td class="property-label">Adjusted Rand Index (ARI)</td>
              <td v-for="run in runs" :key="`ari-${run.id}`">
                <span v-if="run.metrics?.ari !== undefined" class="metric-value ari-metric">
                  {{ run.metrics.ari.toFixed(3) }}
                </span>
                <span v-else class="no-metric">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="comparison-visualizations">
      <h4>Visual Comparison</h4>
      
      <!-- Metrics Chart -->
      <div v-if="hasMetrics" class="metrics-chart">
        <h5>Performance Metrics</h5>
        <div class="chart-container">
          <canvas ref="metricsChartCanvas" width="600" height="300"></canvas>
        </div>
      </div>

      <!-- Parameter Distribution -->
      <div class="parameter-charts">
        <div class="chart-section">
          <h5>K Value Distribution</h5>
          <div class="k-distribution">
            <div 
              v-for="k in uniqueKValues" 
              :key="k"
              class="k-bar"
              :style="{ height: `${(kValueCounts[k] / runs.length) * 100}%` }"
            >
              <span class="k-label">{{ k }}</span>
              <span class="k-count">{{ kValueCounts[k] }}</span>
            </div>
          </div>
        </div>

        <div class="chart-section">
          <h5>Algorithm Distribution</h5>
          <div class="algorithm-distribution">
            <div 
              v-for="algo in uniqueAlgorithms" 
              :key="algo"
              class="algo-item"
            >
              <span class="algo-name">{{ algo }}</span>
              <div class="algo-bar">
                <div 
                  class="algo-fill"
                  :style="{ width: `${(algorithmCounts[algo] / runs.length) * 100}%` }"
                ></div>
              </div>
              <span class="algo-count">{{ algorithmCounts[algo] }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="comparison-actions">
      <button @click="exportComparison" class="export-btn">
        📊 Export Comparison
      </button>
      <button @click="generateReport" class="report-btn">
        📄 Generate Report
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import type { ClusterRun } from '~/composables/useGlobalState'

const props = defineProps<{
  runs: ClusterRun[]
}>()

const metricsChartCanvas = ref<HTMLCanvasElement>()

const uniqueDatasets = computed(() => {
  const datasets = props.runs.map(run => run.dataset)
  return [...new Set(datasets)]
})

const uniqueAlgorithms = computed(() => {
  const algorithms = props.runs.map(run => run.treeType)
  return [...new Set(algorithms)]
})

const uniqueKValues = computed(() => {
  const kValues = props.runs.map(run => run.selectedK)
  return [...new Set(kValues)].sort((a, b) => a - b)
})

const kValueCounts = computed(() => {
  const counts: Record<number, number> = {}
  props.runs.forEach(run => {
    counts[run.selectedK] = (counts[run.selectedK] || 0) + 1
  })
  return counts
})

const algorithmCounts = computed(() => {
  const counts: Record<string, number> = {}
  props.runs.forEach(run => {
    counts[run.treeType] = (counts[run.treeType] || 0) + 1
  })
  return counts
})

const hasMetrics = computed(() => {
  return props.runs.some(run => 
    run.metrics?.silhouetteScore || 
    run.metrics?.dbIndex || 
    run.metrics?.calinskiHarabasz ||
    run.metrics?.ari !== undefined
  )
})

const hasAriMetrics = computed(() => {
  return props.runs.some(run => run.metrics?.ari !== undefined)
})

const formatDate = (date: Date | string) => {
  const d = new Date(date);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

const drawMetricsChart = () => {
  if (!metricsChartCanvas.value || !hasMetrics.value) return

  const canvas = metricsChartCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const metrics = ['silhouetteScore', 'dbIndex', 'calinskiHarabasz', 'ari']
  const metricLabels = ['Silhouette Score', 'Davies-Bouldin', 'Calinski-Harabasz', 'ARI']
  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b']

  const margin = { top: 20, right: 20, bottom: 60, left: 80 }
  const chartWidth = canvas.width - margin.left - margin.right
  const chartHeight = canvas.height - margin.top - margin.bottom

  // Draw background
  ctx.fillStyle = '#f9fafb'
  ctx.fillRect(margin.left, margin.top, chartWidth, chartHeight)

  // Draw grid
  ctx.strokeStyle = '#e5e7eb'
  ctx.lineWidth = 1
  for (let i = 0; i <= 10; i++) {
    const y = margin.top + (chartHeight / 10) * i
    ctx.beginPath()
    ctx.moveTo(margin.left, y)
    ctx.lineTo(margin.left + chartWidth, y)
    ctx.stroke()
  }

  // Draw bars for each metric
  const barWidth = chartWidth / (metrics.length * props.runs.length + metrics.length - 1)
  let xOffset = margin.left

  metrics.forEach((metric, metricIndex) => {
    const values = props.runs.map(run => run.metrics?.[metric as keyof typeof run.metrics] || 0)
    const maxValue = Math.max(...values) || 1

    values.forEach((value, runIndex) => {
      const barHeight = (value / maxValue) * chartHeight
      const x = xOffset + runIndex * barWidth
      const y = margin.top + chartHeight - barHeight

      ctx.fillStyle = colors[metricIndex]
      ctx.fillRect(x, y, barWidth * 0.8, barHeight)

      // Draw value label
      ctx.fillStyle = '#374151'
      ctx.font = '10px Inter'
      ctx.textAlign = 'center'
      ctx.fillText(value.toFixed(2), x + barWidth * 0.4, y - 5)
    })

    xOffset += props.runs.length * barWidth + barWidth
  })

  // Draw legend
  ctx.font = '12px Inter'
  ctx.textAlign = 'left'
  metricLabels.forEach((label, index) => {
    const legendY = margin.top + chartHeight + 30 + index * 15
    ctx.fillStyle = colors[index]
    ctx.fillRect(margin.left, legendY - 10, 10, 10)
    ctx.fillStyle = '#374151'
    ctx.fillText(label, margin.left + 15, legendY)
  })
}

const exportComparison = () => {
  const data = {
    comparisonDate: new Date().toISOString(),
    runs: props.runs.map(run => ({
      id: run.id,
      dataset: run.dataset,
      treeType: run.treeType,
      partitionMethod: run.partitionMethod,
      selectedK: run.selectedK,
      selectedPower: run.selectedPower,
      timestamp: run.timestamp,
      metrics: run.metrics
    }))
  }

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const datePart = new Date().toISOString().substring(0, 10);
  a.download = `run-comparison-${datePart}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const generateReport = () => {
  // Generate a comprehensive text report
  let report = `Clustering Run Comparison Report\n`
  report += `Generated: ${new Date().toLocaleString()}\n\n`
  
  report += `Summary:\n`
  report += `- Total runs compared: ${props.runs.length}\n`
  report += `- Unique datasets: ${uniqueDatasets.value.join(', ')}\n`
  report += `- Algorithms used: ${uniqueAlgorithms.value.join(', ')}\n`
  report += `- K values tested: ${uniqueKValues.value.join(', ')}\n\n`

  report += `Detailed Comparison:\n`
  props.runs.forEach((run, index) => {
    report += `\nRun ${index + 1} (${formatDate(run.timestamp)}):\n`
    report += `  Dataset: ${run.dataset} (${run.parameters.sample})\n`
    report += `  Algorithm: ${run.treeType}\n`
    report += `  Partition Method: ${run.partitionMethod}\n`
    report += `  K Value: ${run.selectedK}\n`
    report += `  Power: ${run.selectedPower}\n`
    
    if (run.metrics) {
      report += `  Metrics:\n`
      if (run.metrics.silhouetteScore) {
        report += `    Silhouette Score: ${run.metrics.silhouetteScore.toFixed(3)}\n`
      }
      if (run.metrics.dbIndex) {
        report += `    Davies-Bouldin Index: ${run.metrics.dbIndex.toFixed(3)}\n`
      }
      if (run.metrics.calinskiHarabasz) {
        report += `    Calinski-Harabasz Index: ${run.metrics.calinskiHarabasz.toFixed(3)}\n`
      }
    }
  })

  const blob = new Blob([report], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const datePart = new Date().toISOString().substring(0, 10);
  a.download = `clustering-report-${datePart}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await nextTick()
  if (hasMetrics.value) {
    drawMetricsChart()
  }
})
</script>

<style scoped>
.run-comparison {
  background-color: white;
  border-radius: 8px;
  padding: 24px;
}

.comparison-overview {
  margin-bottom: 32px;
}

.comparison-overview h4 {
  margin: 0 0 16px 0;
  font-size: 1.25rem;
  color: #111827;
}

.overview-stats {
  display: flex;
  gap: 16px;
}

.stat-card {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  min-width: 100px;
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: #3b82f6;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.comparison-table-container {
  overflow-x: auto;
  margin-bottom: 32px;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.comparison-table th {
  background-color: #f9fafb;
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
}

.comparison-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: top;
}

.run-column {
  min-width: 150px;
}

.run-timestamp {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 400;
  margin-top: 4px;
}

.property-label {
  font-weight: 600;
  color: #374151;
  background-color: #f9fafb;
}

.dataset-name {
  font-weight: 600;
  display: block;
}

.dataset-type {
  font-size: 0.75rem;
  color: #6b7280;
}

.k-value {
  font-weight: 600;
  color: #059669;
}

.metric-value {
  font-weight: 600;
  color: #3b82f6;
}

.ari-metric {
  color: #f59e0b !important;
}

.no-metric {
  color: #9ca3af;
  font-style: italic;
}

.comparison-visualizations {
  margin-bottom: 32px;
}

.comparison-visualizations h4 {
  margin: 0 0 24px 0;
  font-size: 1.25rem;
  color: #111827;
}

.comparison-visualizations h5 {
  margin: 0 0 16px 0;
  font-size: 1rem;
  color: #374151;
}

.metrics-chart {
  margin-bottom: 32px;
}

.chart-container {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.parameter-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.chart-section {
  background-color: #f9fafb;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.k-distribution {
  display: flex;
  align-items: end;
  gap: 8px;
  height: 100px;
  margin-top: 16px;
}

.k-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 20px;
  background-color: #3b82f6;
  border-radius: 4px 4px 0 0;
  min-width: 40px;
  position: relative;
}

.k-label {
  position: absolute;
  bottom: -20px;
  font-size: 0.75rem;
  color: #374151;
  font-weight: 500;
}

.k-count {
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 4px;
}

.algorithm-distribution {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.algo-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.algo-name {
  font-size: 0.875rem;
  color: #374151;
  min-width: 80px;
}

.algo-bar {
  flex-grow: 1;
  height: 16px;
  background-color: #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.algo-fill {
  height: 100%;
  background-color: #10b981;
  transition: width 0.3s ease;
}

.algo-count {
  font-size: 0.875rem;
  color: #374151;
  font-weight: 600;
  min-width: 20px;
}

.comparison-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.export-btn,
.report-btn {
  background-color: #3b82f6;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.export-btn:hover,
.report-btn:hover {
  background-color: #2563eb;
}

.report-btn {
  background-color: #059669;
}

.report-btn:hover {
  background-color: #047857;
}
</style>
