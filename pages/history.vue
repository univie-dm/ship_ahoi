<template>
  <AppLayout :showSidebar="false">
    <template #default>
      <div class="history-page full-width">
        <div class="page-header">
          <h1>Clustering Run History</h1>
          <p>View, compare, and manage all your clustering experiments. Select multiple runs to compare performance metrics and visualizations side-by-side, or load any previous session to restore all settings and data.</p>
          
          <!-- Redis sync status indicator -->
          <div class="sync-status" v-if="globalState.historyPersistence.value.state.value.syncEnabled">
            <span class="sync-indicator" :class="getSyncStatusClass()">
              {{ globalState.historyPersistence.statusText }}
            </span>
            <span class="sync-count" v-if="globalState.historyPersistence.value.state.value.lastSyncTime">
              Last sync: {{ formatSyncTime(globalState.historyPersistence.value.state.value.lastSyncTime) }}
            </span>
          </div>
        </div>

        <div v-if="globalState.clusterRuns.value.length === 0" class="empty-history">
          <div class="empty-icon">📊</div>
          <h2>No clustering runs yet</h2>
          <p>Start by creating your first clustering analysis</p>
          <nuxt-link to="/" class="start-btn">
            Start Clustering
          </nuxt-link>
        </div>

        <div v-else class="history-content">

          <!-- Filters Component - Only show when not in comparison mode -->
          <HistoryFilters
            v-if="!comparisonState.comparisonMode.value"
            :filterDataset="filterState.filterDataset.value"
            :filterAlgorithm="filterState.filterAlgorithm.value"
            :sortBy="filterState.sortBy.value"
            :uniqueDatasets="filterState.uniqueDatasets.value"
            :uniqueAlgorithms="filterState.uniqueAlgorithms.value"
            :viewMode="viewMode"
            :selectedCount="comparisonState.selectedRuns.value.length"
            @update:filterDataset="filterState.filterDataset.value = $event"
            @update:filterAlgorithm="filterState.filterAlgorithm.value = $event"
            @update:sortBy="filterState.sortBy.value = $event"
            @update:viewMode="viewMode = $event"
            @clearSelection="comparisonState.clearSelection"
          />

          <!-- Comparison Mode Component -->
          <ComparisonMode
            v-if="comparisonState.comparisonMode.value"
            :show="comparisonState.comparisonMode.value"
            :selectedRuns="comparisonState.selectedRunsData.value"
            :availableAxes="comparisonState.availableAxes.value"
            :availableMetrics="comparisonState.availableMetrics.value"
            :selectedMetricInfo="comparisonState.selectedMetricInfo.value"
            :showMobileViewToggle="comparisonState.showMobileViewToggle.value"
            :mobileViewMode="comparisonState.mobileViewMode.value"
            :selectedXAxis="comparisonState.selectedXAxis.value"
            :selectedYAxis="comparisonState.selectedYAxis.value"
            :selectedMetric="comparisonState.selectedMetric.value"
            @update:mobileViewMode="comparisonState.mobileViewMode.value = $event"
            @update:selectedXAxis="comparisonState.selectedXAxis.value = $event"
            @update:selectedYAxis="comparisonState.selectedYAxis.value = $event"
            @update:selectedMetric="comparisonState.selectedMetric.value = $event"
            @renderMetricsChart="renderMetricsChart"
            @exportVisualization="exportVisualizationPNG"
            @exitComparison="comparisonState.exitComparison"
            @loadRun="loadRun"
            ref="comparisonModeRef"
          />

          <!-- Runs Display -->
          <div v-if="!comparisonState.comparisonMode.value" class="runs-display">
            <!-- Selection Controls -->
            <div v-if="filterState.filteredRuns.value.length > 0" class="selection-controls">
              <label class="select-all-label">
                <input
                  type="checkbox"
                  :checked="allVisibleSelected"
                  :indeterminate="someVisibleSelected"
                  @change="toggleSelectAll"
                  class="select-all-checkbox"
                />
                Select All Visible
              </label>
              <span class="selection-count">
                {{ comparisonState.selectedRuns.value.length }} of {{ filterState.filteredRuns.value.length }} selected
                <span v-if="comparisonState.selectedRuns.value.length === comparisonState.MAX_COMPARISON_RUNS" class="selection-limit-warning">
                  (Maximum {{ comparisonState.MAX_COMPARISON_RUNS }} runs)
                </span>
              </span>
              <button
                v-if="comparisonState.selectedRuns.value.length >= 2"
                @click="handleStartComparison"
                class="compare-selected-btn"
                :class="{ 'pulse-animation': comparisonState.selectedRuns.value.length >= 2 }"
              >
                📊 Compare {{ comparisonState.selectedRuns.value.length }} Runs
              </button>
            </div>

            <!-- List View -->
            <div v-if="viewMode === 'list'" class="list-view">
              <div class="list-header">
                <div class="list-header-row">
                  <div class="col-select">Select</div>
                  <div class="col-dataset">Dataset</div>
                  <div class="col-algorithm">Algorithm</div>
                  <div class="col-clusters">Clusters</div>
                  <div class="col-metrics">Metrics</div>
                  <div class="col-date">Date</div>
                  <div class="col-actions">Actions</div>
                </div>
              </div>
              <div class="list-body">
                <div
                  v-for="run in filterState.filteredRuns.value"
                  :key="run.id"
                  class="list-row"
                  :class="{ 'selected-row': comparisonState.selectedRuns.value.includes(run.id) }"
                >
                  <div class="col-select">
                    <input
                      type="checkbox"
                      :checked="comparisonState.selectedRuns.value.includes(run.id)"
                      @change="handleRunSelection(run.id)"
                    />
                  </div>
                  <div class="col-dataset">{{ run.dataset.value }}</div>
                  <div class="col-algorithm">
                    <span class="algorithm-badge" :class="getAlgorithmClass(run.treeType)">
                      {{ run.treeType }}
                    </span>
                  </div>
                  <div class="col-clusters">{{ getActualClusterCount(run) }}</div>
                  <div class="col-metrics">
                    <div class="metrics-summary">
                      <span v-if="run.metrics?.silhouetteScore" class="metric-item">
                        S: {{ run.metrics.silhouetteScore.toFixed(3) }}
                      </span>
                      <span v-if="run.metrics?.dbIndex" class="metric-item">
                        DB: {{ run.metrics.dbIndex.toFixed(3) }}
                      </span>
                    </div>
                  </div>
                  <div class="col-date">{{ formatDate(run.timestamp) }}</div>
                  <div class="col-actions">
                    <button @click="loadRun(run.id)" class="action-btn load-btn">Load</button>
                    <button @click="deleteRun(run.id)" class="action-btn delete-btn">Delete</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Cards View -->
            <div v-else class="cards-view">
              <div class="cards-grid">
                <RunCard
                  v-for="run in filterState.filteredRuns.value"
                  :key="run.id"
                  :run="run"
                  :isActive="globalState.activeRun.value?.id === run.id"
                  :isSelected="comparisonState.selectedRuns.value.includes(run.id)"
                  @toggleSelection="handleRunSelection"
                  @loadRun="loadRun"
                  @setActive="setActiveRun"
                  @deleteRun="deleteRun"
                />
              </div>
            </div>
          </div>

          <!-- Study Session History -->
          <div class="study-session-history">
            <div class="session-header">
              <h2>Study Session History</h2>
              <div class="session-header-actions">
                <button @click="handleStartSession" class="session-action-btn start-session-btn" title="Start a new session">
                  ▶ Start Session
                </button>
                <button
                  @click="handleDownloadLog"
                  class="session-action-btn download-log-btn"
                  :disabled="studySession.sessionHistory.value.length === 0"
                  title="Download session log as JSON"
                >
                  📥 Download Log
                </button>
                <button
                  @click="handleClearSession"
                  class="session-action-btn clear-session-btn"
                  :disabled="studySession.sessionHistory.value.length === 0"
                  title="Clear session and start fresh"
                >
                  🗑️ Clear Session
                </button>
              </div>
            </div>
            <div v-if="studySession.sessionHistory.value.length === 0" class="empty-session">
              <p>No session entries yet. Start a session and run some clusterings to see results here.</p>
            </div>
            <table v-else class="session-table">
              <thead>
                <tr>
                  <th class="sortable-col" @click="toggleSessionSort('timestamp')">
                    Date {{ sessionSortKey === 'timestamp' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('dataset')">
                    Dataset {{ sessionSortKey === 'dataset' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('algorithm')">
                    Algorithm {{ sessionSortKey === 'algorithm' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('k')">
                    K {{ sessionSortKey === 'k' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('silhouetteScore')">
                    Silhouette {{ sessionSortKey === 'silhouetteScore' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('dbIndex')">
                    DB Index {{ sessionSortKey === 'dbIndex' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('calinskiHarabasz')">
                    Calinski {{ sessionSortKey === 'calinskiHarabasz' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('discoScore')">
                    DISCO {{ sessionSortKey === 'discoScore' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th class="sortable-col" @click="toggleSessionSort('ari')">
                    ARI {{ sessionSortKey === 'ari' ? (sessionSortAsc ? '▲' : '▼') : '' }}
                  </th>
                  <th>Elapsed</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in sortedSessionHistory" :key="entry.id">
                  <td>{{ formatDate(entry.timestamp) }}</td>
                  <td>{{ entry.params.uploadedFileName || entry.params.sample }}</td>
                  <td>{{ entry.params.treeType }}</td>
                  <td>{{ entry.params.k }}</td>
                  <td>{{ entry.metrics.silhouetteScore != null ? entry.metrics.silhouetteScore.toFixed(3) : '-' }}</td>
                  <td>{{ entry.metrics.dbIndex != null ? entry.metrics.dbIndex.toFixed(3) : '-' }}</td>
                  <td>{{ entry.metrics.calinskiHarabasz != null ? entry.metrics.calinskiHarabasz.toFixed(0) : '-' }}</td>
                  <td>{{ entry.metrics.discoScore != null ? entry.metrics.discoScore.toFixed(3) : '-' }}</td>
                  <td>{{ entry.metrics.ari != null ? entry.metrics.ari.toFixed(3) : '-' }}</td>
                  <td>{{ formatElapsed(entry.elapsedSeconds) }}</td>
                  <td>
                    <button @click="loadSessionEntry(entry)" class="action-btn load-btn">Load</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGlobalState, type ClusterRun } from '~/composables/useGlobalState'
import { useHistoryFilters } from '~/composables/useHistoryFilters'
import { useRunComparison } from '~/composables/useRunComparison'
import { useStudySession, type StudyParameterEntry } from '~/composables/useStudySession'
import * as d3 from 'd3'

const router = useRouter()
const globalState = useGlobalState()
const studySession = useStudySession()

// Initialize composables
const filterState = useHistoryFilters(globalState.clusterRuns)
const comparisonState = useRunComparison(globalState.getRunById)

// Local state
const viewMode = ref<'list' | 'cards'>('cards')
const comparisonModeRef = ref()

// Study session sort state
const sessionSortKey = ref<string>('timestamp')
const sessionSortAsc = ref(false)

const toggleSessionSort = (key: string) => {
  if (sessionSortKey.value === key) {
    sessionSortAsc.value = !sessionSortAsc.value
  } else {
    sessionSortKey.value = key
    sessionSortAsc.value = true
  }
}

const sortedSessionHistory = computed(() => {
  const entries = studySession.sessionHistory.value.map((entry: StudyParameterEntry, index: number) => ({
    ...entry,
    id: entry.timestamp + '_' + index
  }))

  return entries.slice().sort((a: any, b: any) => {
    let aVal: any, bVal: any
    const key = sessionSortKey.value

    switch (key) {
      case 'timestamp':
        aVal = new Date(a.timestamp).getTime()
        bVal = new Date(b.timestamp).getTime()
        break
      case 'dataset':
        aVal = a.params?.uploadedFileName || a.params?.sample || ''
        bVal = b.params?.uploadedFileName || b.params?.sample || ''
        break
      case 'algorithm':
        aVal = a.params?.treeType || ''
        bVal = b.params?.treeType || ''
        break
      case 'k':
        aVal = a.params?.k || 0
        bVal = b.params?.k || 0
        break
      case 'silhouetteScore':
        aVal = a.metrics?.silhouetteScore ?? -Infinity
        bVal = b.metrics?.silhouetteScore ?? -Infinity
        break
      case 'dbIndex':
        aVal = a.metrics?.dbIndex ?? Infinity
        bVal = b.metrics?.dbIndex ?? Infinity
        break
      case 'calinskiHarabasz':
        aVal = a.metrics?.calinskiHarabasz ?? -Infinity
        bVal = b.metrics?.calinskiHarabasz ?? -Infinity
        break
      case 'discoScore':
        aVal = a.metrics?.discoScore ?? -Infinity
        bVal = b.metrics?.discoScore ?? -Infinity
        break
      case 'ari':
        aVal = a.metrics?.ari ?? -Infinity
        bVal = b.metrics?.ari ?? -Infinity
        break
      default:
        aVal = 0
        bVal = 0
    }

    if (aVal < bVal) return sessionSortAsc.value ? -1 : 1
    if (aVal > bVal) return sessionSortAsc.value ? 1 : -1
    return 0
  })
})

// Computed properties
const allVisibleSelected = computed(() => {
  return filterState.filteredRuns.value.length > 0 && 
         filterState.filteredRuns.value.every(run => comparisonState.selectedRuns.value.includes(run.id))
})

const someVisibleSelected = computed(() => {
  return comparisonState.selectedRuns.value.length > 0 && !allVisibleSelected.value
})

// Methods
const toggleSelectAll = () => {
  if (allVisibleSelected.value) {
    // Deselect all visible runs
    const visibleIds = filterState.filteredRuns.value.map(run => run.id)
    comparisonState.deselectAllRuns(visibleIds)
  } else {
    // Select all visible runs
    const visibleIds = filterState.filteredRuns.value.map(run => run.id)
    comparisonState.selectAllRuns(visibleIds)
  }
}

const handleRunSelection = (runId: string) => {
  const success = comparisonState.toggleRunSelection(runId)
  if (!success) {
    // Show warning that maximum runs are already selected
    alert(`Maximum ${comparisonState.MAX_COMPARISON_RUNS} runs can be selected for comparison`)
  }
}

const handleStartComparison = async () => {
  await comparisonState.startComparison()
  await nextTick()
  renderComparisonCharts()
}

const formatDate = (timestamp: Date | string): string => {
  const d = new Date(timestamp);
  return d.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatElapsed = (seconds: number): string => {
  if (seconds === undefined || seconds === null) return '-'
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  
  if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`
  if (mins > 0) return `${mins}m ${secs}s`
  return `${secs}s`
}

const formatSyncTime = (timestamp: Date): string => {
  const now = new Date()
  const diff = now.getTime() - timestamp.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (seconds < 60) return `${seconds}s ago`
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return timestamp.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const getSyncStatusClass = (): string => {
  const state = globalState.historyPersistence.value.state.value
  if (state.isLoading) return 'sync-loading'
  if (!state.isConnected) return 'sync-disconnected'
  if (state.error) return 'sync-error'
  return 'sync-connected'
}

const getActualClusterCount = (run: ClusterRun): number => {
  if (run.actualClusterCount !== undefined && run.actualClusterCount !== null) {
    return run.actualClusterCount
  }
  
  if (run.clusterData?.labels && Array.isArray(run.clusterData.labels)) {
    const uniqueLabels = new Set(run.clusterData.labels)
    return uniqueLabels.size
  }
  
  return run.selectedK || 0
}

const getAlgorithmClass = (algorithm: string): string => {
  switch (algorithm.toLowerCase()) {
    case 'ship':
      return 'algorithm-ship'
    case 'kmeans':
      return 'algorithm-kmeans'
    case 'dbscan':
      return 'algorithm-dbscan'
    case 'hierarchical':
      return 'algorithm-hierarchical'
    default:
      return 'algorithm-default'
  }
}

const loadRun = async (runId: string) => {
  const run = await globalState.getRunByIdAsync(runId)
  if (!run) {
    console.error('Run not found:', runId)
    return
  }

  try {
    // Check if we need to switch datasets
    const currentDataset = globalState.currentDataset.value
    const needsDatasetSwitch = !currentDataset || 
      (run.parameters.uploadedFileName && currentDataset.type !== 'uploaded' && currentDataset.type !== 'imported') ||
      (run.parameters.uploadedFileName && currentDataset.fileName !== run.parameters.uploadedFileName) ||
      (run.parameters.sample && currentDataset.type !== 'sample') ||
      (run.parameters.sample && currentDataset.sampleName !== run.parameters.sample)

    if (needsDatasetSwitch) {
      console.log('Dataset switch needed for run:', run.dataset, 'from current:', currentDataset?.name)
      
      // Create appropriate dataset info for the run
      if (run.parameters.uploadedFileName) {
        // For uploaded files, create basic dataset info
        const datasetInfo = {
          name: run.parameters.uploadedFileName,
          type: 'uploaded' as const,
          fileName: run.parameters.uploadedFileName,
          pointCount: run.clusterData?.points?.length || 0,
          featureCount: run.clusterData?.points?.[0]?.length || 0
        }
        globalState.setDataset(datasetInfo)
        console.log('Switched to uploaded dataset:', datasetInfo.name)
      } else if (run.parameters.sample) {
        // For sample data, find the option to get correct dimensions
        const sampleOption = globalState.getSampleOption(run.parameters.sample)
        if (sampleOption) {
          const datasetInfo = {
            name: sampleOption.label,
            type: 'sample' as const,
            sampleName: run.parameters.sample,
            n_samples: run.parameters.n_samples || sampleOption.typical_samples,
            featureCount: sampleOption.dimensions,
            pointCount: run.parameters.n_samples || sampleOption.typical_samples,
            headers: Array.from({ length: sampleOption.dimensions }, (_, i) => `Feature ${i + 1}`)
          }
          globalState.setDataset(datasetInfo)
          console.log('Switched to sample dataset:', datasetInfo.name)
        }
      }
    }

    // Set active run which triggers parameter loading in clustering page
    globalState.setActiveRun(runId)
    
    // Navigate back to clustering page
    await navigateTo('/clustering')
  } catch (error) {
    console.error('Failed to load run:', error)
  }
}

const loadSessionEntry = async (entry: StudyParameterEntry) => {
  // Set parameters from the study session log into the global context
  globalState.setClusteringParameters({
    treeType: entry.params.treeType,
    partitionMethod: entry.params.partitionMethod,
    power: entry.params.power,
    selectedK: entry.params.k
  })

  // Optionally set the dataset as well if defined in entry.params
  if (entry.params.sample) {
    const sampleOption = globalState.getSampleOption(entry.params.sample)
    if (sampleOption) {
      const datasetInfo = {
        name: sampleOption.label,
        type: 'sample' as const,
        sampleName: entry.params.sample,
        n_samples: entry.params.n_samples || sampleOption.typical_samples,
        featureCount: sampleOption.dimensions,
        pointCount: entry.params.n_samples || sampleOption.typical_samples,
        headers: Array.from({ length: sampleOption.dimensions }, (_, i) => `Feature ${i + 1}`)
      }
      globalState.setDataset(datasetInfo)
    }
  } else if (entry.params.uploadedFileName) {
    const datasetInfo = {
      name: entry.params.uploadedFileName,
      type: 'uploaded' as const,
      fileName: entry.params.uploadedFileName,
      fileId: entry.params.fileId
    }
    globalState.setDataset(datasetInfo)
  }

  // Clear any existing active run so it's a fresh run with these parameters
  globalState.clearActiveRun()

  if (entry.source === 'k-selection') {
    await navigateTo({ path: '/k-selection', query: { autostart: 'true' } })
  } else {
    await navigateTo({ path: '/clustering', query: { autostart: 'true' } })
  }
}

const handleStartSession = () => {
  if (studySession.sessionActive.value) {
    if (!confirm('A session is already active. Start a new one? (Current session data will remain in the log)')) {
      return
    }
  }
  studySession.startSession()
}

const handleClearSession = async () => {
  if (!confirm('Are you sure you want to clear the session log? This cannot be undone.')) {
    return
  }
  await studySession.clearSession('current')
}

const handleDownloadLog = () => {
  studySession.downloadSessionLog()
}

const setActiveRun = (runId: string) => {
  const run = globalState.getRunById(runId)
  if (run) {
    try {
      globalState.setActiveRun(runId)
    } catch (error) {
      console.error('Failed to set active run:', error)
    }
  } else {
    console.error('Run not found:', runId)
  }
}

const deleteRun = async (runId: string) => {
  if (confirm('Are you sure you want to delete this clustering run?')) {
    globalState.deleteRun(runId)
    // Remove from selection if it was selected
    const index = comparisonState.selectedRuns.value.indexOf(runId)
    if (index !== -1) {
      comparisonState.selectedRuns.value.splice(index, 1)
    }
  }
}

// Chart rendering methods
const renderMetricsChart = () => {
  if (!comparisonModeRef.value?.metricsChart) return
  
  try {
    const container = comparisonModeRef.value.metricsChart
    const selectedRuns = comparisonState.selectedRunsData.value
    const metric = comparisonState.selectedMetric.value
    
    // Clear previous chart and event listeners
    d3.select(container).selectAll('*').on('.zoom', null).on('.drag', null).on('mouseover', null).on('mouseout', null)
    d3.select(container).selectAll('*').remove()
    d3.selectAll('.chart-tooltip').remove() // Clear any existing tooltips
  
    // Create chart with more space for legend
    const margin = { top: 20, right: 30, bottom: 40, left: 60 }
    const legendHeight = 120
    const containerWidth = container.clientWidth || 600
    const width = Math.max(300, Math.min(800, containerWidth - margin.left - margin.right))
    const height = 300 - margin.top - margin.bottom
    
    const svg = d3.select(container)
      .append('svg')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom + legendHeight)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)
    
    // Extract metric values with better error handling
    const data = selectedRuns.map((run, index) => {
      const metricValue = run.metrics?.[metric as keyof typeof run.metrics]
      
      // Create short, clean names for chart bars
      const shortName = `Run ${index + 1}`
      
      // Full name for tooltips and legend
      const timestamp = run.timestamp.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
      const fullName = `${run.dataset} (${run.treeType}) - ${timestamp}`
      
      return {
        run: shortName,
        fullName: fullName,
        value: typeof metricValue === 'number' && !isNaN(metricValue) ? metricValue : null,
        index,
        runId: run.id
      }
    }).filter(d => d.value !== null && d.value !== undefined) // Only include runs with valid metric values
    
    // Handle case where no data is available
    if (data.length === 0) {
      svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('fill', '#64748b')
        .text(`No ${comparisonState.selectedMetricInfo.value?.name || metric} data available for selected runs`)
      return
    }
    
    // Create scales
    const xScale = d3.scaleBand()
      .domain(data.map(d => d.run))
      .range([0, width])
      .padding(0.2)
    
    const values = data.map(d => d.value!)
    const extent = d3.extent(values) as [number, number]
    
    // Better handling of single value or very close values
    let yDomain: [number, number]
    if (extent[0] === extent[1]) {
      const val = extent[0]
      const padding = Math.abs(val) * 0.1 || 0.1
      yDomain = [val - padding, val + padding]
    } else {
      const range = extent[1] - extent[0]
      const padding = range * 0.1
      yDomain = [extent[0] - padding, extent[1] + padding]
    }
    
    const yScale = d3.scaleLinear()
      .domain(yDomain)
      .nice()
      .range([height, 0])
    
    // Improved color scale with better colors for up to 5 runs
    const colorScale = d3.scaleOrdinal()
      .domain(data.map(d => d.runId))
      .range(['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'])

    // Create bars
    svg.selectAll('.bar')
      .data(data)
      .enter().append('rect')
      .attr('class', 'bar')
      .attr('x', d => xScale(d.run) || 0)
      .attr('width', xScale.bandwidth())
      .attr('y', d => yScale(d.value!))
      .attr('height', d => Math.max(0, height - yScale(d.value!)))
      .attr('fill', d => colorScale(d.runId))
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 1)
      .on('mouseover', function(event, d) {
        // Add tooltip on hover
        const tooltip = d3.select('body').append('div')
          .attr('class', 'chart-tooltip')
          .style('position', 'absolute')
          .style('background', '#1f2937')
          .style('color', 'white')
          .style('padding', '8px')
          .style('border-radius', '4px')
          .style('font-size', '12px')
          .style('z-index', '1000')
          .style('pointer-events', 'none')
          .html(`<strong>${d.fullName}</strong><br/>${comparisonState.selectedMetricInfo.value?.name || metric}: ${d.value!.toFixed(3)}`)
        
        tooltip.style('left', (event.pageX + 10) + 'px')
          .style('top', (event.pageY - 10) + 'px')
      })
      .on('mouseout', function() {
        d3.selectAll('.chart-tooltip').remove()
      })
    
    // Add value labels on top of bars
    svg.selectAll('.bar-label')
      .data(data)
      .enter().append('text')
      .attr('class', 'bar-label')
      .attr('x', d => (xScale(d.run) || 0) + xScale.bandwidth() / 2)
      .attr('y', d => yScale(d.value!) - 5)
      .attr('text-anchor', 'middle')
      .style('font-size', '11px')
      .style('font-weight', '500')
      .style('fill', '#374151')
      .text(d => d.value!.toFixed(3))
    
    // Add axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(xScale))
      .selectAll('text')
      .style('text-anchor', 'end')
      .attr('dx', '-.8em')
      .attr('dy', '.15em')
      .attr('transform', 'rotate(-45)')
      .style('font-size', '10px')
    
    svg.append('g')
      .call(d3.axisLeft(yScale).ticks(5))
    
    // Add chart title
    const metricInfo = comparisonState.selectedMetricInfo.value
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -5)
      .attr('text-anchor', 'middle')
      .style('font-size', '14px')
      .style('font-weight', '600')
      .style('fill', '#1e293b')
      .text(`${metricInfo?.name || metric} Comparison`)
    
    // Add y-axis label
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', 0 - margin.left)
      .attr('x', 0 - (height / 2))
      .attr('dy', '1em')
      .style('text-anchor', 'middle')
      .style('font-size', '12px')
      .style('fill', '#64748b')
      .text(metricInfo?.name || metric)
    
    // Add legend below the chart
    const legendStartY = height + 60
    const legendContainer = svg.append('g')
      .attr('class', 'legend')
      .attr('transform', `translate(0, ${legendStartY})`)
    
    // Add legend title
    legendContainer.append('text')
      .attr('x', 0)
      .attr('y', -10)
      .style('font-size', '12px')
      .style('font-weight', '600')
      .style('fill', '#1e293b')
      .text('Run Details:')
    
    // Add legend items
    data.forEach((d, i) => {
      const legendItem = legendContainer.append('g')
        .attr('class', 'legend-item')
        .attr('transform', `translate(0, ${i * 18})`)
      
      // Color square
      legendItem.append('rect')
        .attr('width', 12)
        .attr('height', 12)
        .attr('fill', colorScale(d.runId))
        .attr('stroke', '#ffffff')
        .attr('stroke-width', 1)
      
      // Run label and details
      legendItem.append('text')
        .attr('x', 18)
        .attr('y', 9)
        .style('font-size', '11px')
        .style('fill', '#374151')
        .text(`${d.run}: ${d.fullName}`)
    })
      
  } catch (error) {
    console.error('Error rendering metrics chart:', error)
    // Show error message in chart
    const container = comparisonModeRef.value.metricsChart
    if (container) {
      d3.select(container).selectAll('*').remove()
      const svg = d3.select(container)
        .append('svg')
        .attr('width', 400)
        .attr('height', 300)
        .append('g')
        .attr('transform', 'translate(200,150)')
      
      svg.append('text')
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('fill', '#ef4444')
        .text('Error rendering chart')
    }
  }
}

const renderComparisonCharts = () => {
  try {
    // Render metrics chart
    renderMetricsChart()
    
    // Render individual scatter plots
    if (!comparisonModeRef.value?.chartRefs) return
    
    const chartRefs = comparisonModeRef.value.chartRefs
    
    comparisonState.selectedRunsData.value.forEach(run => {
    const container = chartRefs[run.id]
    if (!container || !run.clusterData?.points) return
    
    // Clear previous chart and event listeners
    d3.select(container).selectAll('*').on('.zoom', null).on('.drag', null).on('mouseover', null).on('mouseout', null)
    d3.select(container).selectAll('*').remove()
    
    // Create scatter plot
    const margin = { top: 10, right: 10, bottom: 30, left: 40 }
    const containerWidth = container.clientWidth || 300
    const containerHeight = container.clientHeight || 250
    const width = Math.max(200, containerWidth - margin.left - margin.right)
    const height = Math.max(150, containerHeight - margin.top - margin.bottom)
    
    const svg = d3.select(container)
      .append('svg')
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)
    
    // Extract point data
    const points = run.clusterData.points.map((point, index) => ({
      x: comparisonState.getAxisValue(point, run, comparisonState.selectedXAxis.value),
      y: comparisonState.getAxisValue(point, run, comparisonState.selectedYAxis.value),
      cluster: run.clusterData?.labels?.[index] || 0
    }))
    
    // Create scales with padding to prevent overflow
    const xExtent = d3.extent(points, d => d.x) as [number, number]
    const yExtent = d3.extent(points, d => d.y) as [number, number]
    
    // Add 5% padding to each axis to prevent points from rendering at exact edges
    const xRange = xExtent[1] - xExtent[0]
    const yRange = yExtent[1] - yExtent[0]
    const xPadding = xRange * 0.05
    const yPadding = yRange * 0.05
    
    const xScale = d3.scaleLinear()
      .domain([xExtent[0] - xPadding, xExtent[1] + xPadding])
      .range([0, width])
    
    const yScale = d3.scaleLinear()
      .domain([yExtent[0] - yPadding, yExtent[1] + yPadding])
      .range([height, 0])
    
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
    
    // Create points
    svg.selectAll('.point')
      .data(points)
      .enter().append('circle')
      .attr('class', 'point')
      .attr('cx', d => xScale(d.x))
      .attr('cy', d => yScale(d.y))
      .attr('r', 2)
      .attr('fill', d => colorScale(d.cluster.toString()))
      .attr('opacity', 0.7)
    
    // Add axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(xScale).ticks(5))
    
    svg.append('g')
      .call(d3.axisLeft(yScale).ticks(5))
    })
  } catch (error) {
    console.error('Error rendering comparison charts:', error)
  }
}

// Export methods (simplified implementations)
const exportDetailedReport = () => {
  const data = {
    runs: comparisonState.selectedRunsData.value,
    exportDate: new Date().toISOString(),
    selectedMetric: comparisonState.selectedMetric.value
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'clustering-comparison-report.json'
  a.click()
  URL.revokeObjectURL(url)
}

const exportVisualReport = () => {
  // Simplified HTML report export
  const html = `
    <html>
      <head><title>Clustering Comparison Report</title></head>
      <body>
        <h1>Clustering Comparison Report</h1>
        <p>Generated on: ${new Date().toLocaleString()}</p>
        <p>Number of runs compared: ${comparisonState.selectedRunsData.value.length}</p>
        <!-- Add more report content here -->
      </body>
    </html>
  `
  
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'clustering-comparison-report.html'
  a.click()
  URL.revokeObjectURL(url)
}

const exportAllVisualizations = (format: string) => {
  // Simplified export implementation
  console.log(`Exporting all visualizations as ${format}`)
}

const exportVisualizationPNG = (runId: string, format: string) => {
  // Simplified export implementation
  console.log(`Exporting visualization for run ${runId} as ${format}`)
}


// Watch for axis changes and re-render charts
watch([() => comparisonState.selectedXAxis.value, () => comparisonState.selectedYAxis.value], () => {
  console.log('Axis selection changed:', {
    x: comparisonState.selectedXAxis.value,
    y: comparisonState.selectedYAxis.value
  });
  if (comparisonState.comparisonMode.value) {
    nextTick(() => {
      console.log('Re-rendering comparison charts due to axis change.');
      renderComparisonCharts()
    })
  }
})

// Watch for metric changes and re-render metrics chart
watch(() => comparisonState.selectedMetric.value, () => {
  if (comparisonState.comparisonMode.value) {
    nextTick(() => {
      renderMetricsChart()
    })
  }
})

// Lifecycle hooks
onMounted(async () => {
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', comparisonState.updateWindowWidth)
  }
  
  // Initialize Redis history persistence
  await globalState.initializeHistoryPersistence()
  
  // Try to load additional runs from Redis history
  try {
    await globalState.loadHistoryRuns()
  } catch (error) {
    console.warn('Failed to load history runs from Redis:', error)
  }

  // Load study session history from backend
  try {
    await studySession.loadSessionHistory('current')
  } catch (error) {
    console.warn('Failed to load study session history:', error)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', comparisonState.updateWindowWidth)
  }
  
  // Cleanup history persistence
  globalState.historyPersistence.value.cleanup()
  
  // Clear any D3 selections and event listeners
  if (comparisonModeRef.value?.metricsChart) {
    const metricsChart = comparisonModeRef.value.metricsChart
    d3.select(metricsChart).selectAll('*').on('.zoom', null).on('.drag', null).on('mouseover', null).on('mouseout', null)
    d3.select(metricsChart).selectAll('*').remove()
  }
  
  if (comparisonModeRef.value?.chartRefs) {
    Object.values(comparisonModeRef.value.chartRefs).forEach((ref: any) => {
      if (ref) {
        d3.select(ref).selectAll('*').on('.zoom', null).on('.drag', null).on('mouseover', null).on('mouseout', null)
        d3.select(ref).selectAll('*').remove()
      }
    })
  }
  
  // Clear any tooltips that might be left behind
  d3.selectAll('.chart-tooltip').remove()
})
</script>

<style scoped>
.app-layout .main-content-wrapper .sidebar {
  display: none !important;
}

.app-layout .main-content-wrapper .content-area {
  margin-left: 0 !important;
  width: 100vw !important;
  max-width: 100vw !important;
}


.history-page.full-width {
  width: 100%;
  max-width: 100%;
  margin-left: 0 !important;
  padding: 1.5rem;
  min-height: calc(100vh - 4rem);
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  box-sizing: border-box;
  overflow-x: hidden;
}

.history-content {
  width: 100%;
  max-width: 100%;
  margin: 0;
  box-sizing: border-box;
}

/* Comparison mode layout improvements */
.comparison-mode {
  width: 100%;
  max-width: 100%;
  margin: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: flex-start;
  gap: 1rem;
  padding: 0;
}

.comparison-mode .metrics-chart,
.comparison-mode .chartRefs {
  width: 100%;
  max-width: 100%;
  margin: 0 0 2rem 0;
  box-sizing: border-box;
  padding: 0;
}

/* Remove fixed sidebar width overrides - let AppLayout handle responsive sizing */

.page-header {
  text-align: center;
  margin-bottom: 1.5rem;
}

.page-header h1 {
  font-size: 1.75rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.25rem 0;
}

.page-header p {
  font-size: 1rem;
  color: #64748b;
  margin: 0.5rem 0 0 0;
  line-height: 1.6;
}

.sync-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  font-size: 0.875rem;
  justify-content: center;
}

.sync-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
}

.sync-indicator::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.sync-connected::before {
  background: #10b981;
}

.sync-loading::before {
  background: #f59e0b;
  animation: pulse 1.5s ease-in-out infinite;
}

.sync-disconnected::before {
  background: #ef4444;
}

.sync-error::before {
  background: #ef4444;
}

.sync-count {
  color: #6b7280;
  font-size: 0.8rem;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.empty-history {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-history h2 {
  font-size: 1.5rem;
  color: #374151;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
}

.empty-history p {
  color: #6b7280;
  margin: 0 0 24px 0;
}

.start-btn {
  display: inline-flex;
  align-items: center;
  padding: 12px 24px;
  background: #111827;
  color: #ffffff;
  border-radius: 8px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s ease;
}

.start-btn:hover {
  background: #000000;
  transform: translateY(-1px);
}

/* Selection Controls */
.selection-controls {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.select-all-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  cursor: pointer;
}

.select-all-checkbox {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid #d1d5db;
  accent-color: #111827;
}

.selection-count {
  font-size: 0.875rem;
  color: #6b7280;
  flex: 1;
}

.selection-limit-warning {
  color: #ef4444;
  margin-left: 8px;
  font-size: 0.75rem;
}

.compare-selected-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  background: #111827;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.compare-selected-btn:hover {
  background: #000000;
  transform: translateY(-1px);
}

.pulse-animation {
  animation: pulse-shadow 2s infinite;
}

@keyframes pulse-shadow {
  0% { box-shadow: 0 0 0 0 rgba(17, 24, 39, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(17, 24, 39, 0); }
  100% { box-shadow: 0 0 0 0 rgba(17, 24, 39, 0); }
}

/* List View */
.list-view {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.list-header {
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.list-header-row {
  display: grid;
  grid-template-columns: 48px 2fr 1.5fr 1fr 2fr 1.5fr 140px;
  padding: 12px 16px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.list-body {
  max-height: 600px;
  overflow-y: auto;
}

.list-row {
  display: grid;
  grid-template-columns: 48px 2fr 1.5fr 1fr 2fr 1.5fr 140px;
  padding: 16px;
  border-bottom: 1px solid #f3f4f6;
  align-items: center;
  transition: background-color 0.15s ease;
}

.list-row:last-child {
  border-bottom: none;
}

.list-row:hover {
  background: #f9fafb;
}

.list-row.selected-row {
  background: #eff6ff;
}

.col-select {
  display: flex;
  justify-content: center;
}

.col-dataset {
  font-weight: 500;
  color: #111827;
}

.col-algorithm {
  display: flex;
}

.algorithm-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  background: #f3f4f6;
  color: #374151;
}

.algorithm-ship { background: #eff6ff; color: #1e40af; }
.algorithm-kmeans { background: #ecfdf5; color: #047857; }
.algorithm-dbscan { background: #fff7ed; color: #c2410c; }
.algorithm-hierarchical { background: #f5f3ff; color: #6d28d9; }

.col-clusters {
  color: #4b5563;
  font-variant-numeric: tabular-nums;
}

.metrics-summary {
  display: flex;
  gap: 12px;
}

.metric-item {
  font-size: 0.75rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
}

.col-date {
  font-size: 0.875rem;
  color: #6b7280;
}

.col-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #ffffff;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.load-btn {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.load-btn:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}

.delete-btn {
  color: #dc2626;
}

.delete-btn:hover {
  background: #fef2f2;
  border-color: #fecaca;
}

/* Cards View */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

/* Responsive */
@media (max-width: 1024px) {
  .list-header-row, .list-row {
    grid-template-columns: 48px 2fr 1.5fr 1fr 140px;
  }
  
  .col-metrics, .col-date {
    display: none;
  }
}

@media (max-width: 768px) {
  .page-header {
    margin-bottom: 24px;
  }
  
  .sync-status {
    position: static;
    margin-top: 12px;
    justify-content: flex-start;
  }
  
  .selection-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .compare-selected-btn {
    width: 100%;
    justify-content: center;
  }
  
  .list-view {
    display: none;
  }
  
  .cards-grid {
    grid-template-columns: 1fr;
  }
  
  .page-header h1 {
    font-size: 1.75rem;
  }
  
  .page-subtitle {
    font-size: 1rem;
  }
}

/* Import notification styles */
:global(.import-notification) {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  max-width: 400px;
  min-width: 300px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  animation: slideInRight 0.3s ease-out;
  font-family: 'Inter', system-ui, sans-serif;
}

:global(.import-notification.success) {
  background: #f0f9ff;
  border: 1px solid #0ea5e9;
}

:global(.import-notification.error) {
  background: #fef2f2;
  border: 1px solid #ef4444;
}

:global(.import-notification .notification-content) {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  gap: 12px;
}

:global(.import-notification .notification-icon) {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

:global(.import-notification .notification-text) {
  flex: 1;
}

:global(.import-notification .notification-text strong) {
  display: block;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
  color: #1f2937;
}

:global(.import-notification.success .notification-text strong) {
  color: #0369a1;
}

:global(.import-notification.error .notification-text strong) {
  color: #dc2626;
}

:global(.import-notification .notification-text p) {
  margin: 0;
  font-size: 13px;
  line-height: 1.4;
  color: #6b7280;
}

:global(.import-notification .notification-close) {
  background: none;
  border: none;
  font-size: 18px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  margin-left: 8px;
  flex-shrink: 0;
  line-height: 1;
}

:global(.import-notification .notification-close:hover) {
  color: #6b7280;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Study Session Header */
.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.session-header h2 {
  margin: 0;
}

.session-header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.session-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #ffffff;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-action-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.start-session-btn {
  color: #059669;
  border-color: #a7f3d0;
  background: #ecfdf5;
}

.start-session-btn:hover:not(:disabled) {
  background: #d1fae5;
  border-color: #6ee7b7;
}

.download-log-btn {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.download-log-btn:hover:not(:disabled) {
  background: #dbeafe;
  border-color: #93c5fd;
}

.clear-session-btn {
  color: #dc2626;
  border-color: #fecaca;
  background: #fef2f2;
}

.clear-session-btn:hover:not(:disabled) {
  background: #fee2e2;
  border-color: #fca5a5;
}

.empty-session {
  text-align: center;
  padding: 32px 16px;
  color: #6b7280;
  font-size: 0.9rem;
}
</style>