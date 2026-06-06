<template>
  <AppLayout>
    <template #sidebar>
      <SharedSidebar
        :sampleOptions="[...globalState.sampleOptions.value]"
        :selectedSample="selectedSample"
        :showParameters="true"
        :showVisualizationOptions="false"
        :quickStats="quickStatsDisplay"
        :isDendrogramVisible="false"
        :isScatterVisible="false"
        :isIcicleVisible="false"
        :showDataManagement="false"
        @run-selected="handleRunSelected"
        @run-loaded="handleRunLoaded"
        v-bind="sidebarState"
      >
        <!-- Tree Type Selection -->
        <template #tree-type-select>
          <select
            id="tree-type"
            v-model="selectedTreeType"
            class="control-select"
          >
            <option v-for="type in treeTypes" :key="type" :value="type">{{ type }}</option>
          </select>
        </template>

        <!-- Power Parameter Selection -->
        <template #power-select>
          <input
            type="range"
            id="power"
            v-model="selectedPower"
            min="0"
            max="10"
            step="1"
            class="control-range"
          />
          <span class="range-value">{{ selectedPower }}</span>
        </template>

        <!-- Partition Method Selection -->
        <template #partition-method-select>
          <select
            id="partition-method"
            v-model="selectedPartitionMethod"
            class="control-select"
          >
            <option v-for="method in partitionMethods" :key="method" :value="method">{{ method }}</option>
          </select>
        </template>

        <!-- K Input -->
        <template #k-slider>
          <div class="k-input-container">
            <input
              type="number"
              id="cluster-k"
              v-model="selectedK"
              min="2"
              :max="maxK"
              step="1"
              class="k-number-input"
            />
            <span class="k-input-hint">Range: 2-{{ maxK }}</span>
          </div>
        </template>

        <!-- Run Button -->
        <template #run-button>
          <button 
            @click="runClustering" 
            class="run-clustering-btn"
            :disabled="!hasValidData"
          >
            Run Clustering
          </button>
        </template>

        <!-- Single Run Selection -->
        <template #page-controls>
          <div class="control-section">
            <h3 class="section-title">Analysis Controls</h3>
            <div class="info-box">
              Deep dive into clustering results with comprehensive statistics and insights. Select a run from the History tab.
            </div>
            
            <!-- Feature Selection for Analysis -->
            <div v-if="selectedRunId && selectedRun && availableFeatures.length > 0" class="feature-selection">
              <h4>Feature Selection</h4>
              <div class="info-box small">
                Select features to focus the clustering analysis on specific dimensions.
              </div>
              
              <div class="feature-list">
                <label class="feature-item" v-for="(feature, index) in availableFeatures" :key="feature">
                  <input
                    type="checkbox"
                    :value="index"
                    v-model="selectedFeatures"
                    @change="updateAnalysis"
                  />
                  <span>{{ feature }}</span>
                </label>
              </div>
              
              <div class="feature-actions">
                <button @click="selectAllFeatures" class="feature-btn">Select All</button>
                <button @click="clearAllFeatures" class="feature-btn">Clear All</button>
              </div>
            </div>

          </div>
        </template>
      </SharedSidebar>
    </template>    
    
    <template #default>
      <div class="clustering-explorer-content">
        <div class="page-header">
          <h1>Clustering Explorer</h1>
          <p>In-depth analysis of individual clustering results</p>
        </div>

        <!-- Run Overview -->
        <div v-if="selectedRun" class="overview-section">
          <h2>Analysis Overview</h2>
          <div class="run-summary-card">
            <div class="run-info">
              <h3>{{ selectedRun.dataset }}</h3>
              <div class="run-metadata">
                <div class="meta-item">
                  <span class="meta-label">Algorithm:</span>
                  <span class="meta-value">{{ selectedRun.treeType }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">Partition Method:</span>
                  <span class="meta-value">{{ selectedRun.partitionMethod }}</span>
                </div>
                
                <div class="meta-item">
                  <span class="meta-label">Power Parameter:</span>
                  <span class="meta-value">{{ selectedRun.selectedPower }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">Clusters:</span>
                  <span class="meta-value">{{ actualClusterCount }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">Date:</span>
                  <span class="meta-value">{{ formatDate(selectedRun.timestamp) }}</span>
                </div>
              </div>
            </div>
            <div class="run-metrics">
              <div class="metric-card" v-if="selectedRun.metrics?.silhouetteScore"
                   v-tooltip="{ key: 'metrics.silhouette' }">
                <div class="metric-value">{{ selectedRun.metrics.silhouetteScore.toFixed(3) }}</div>
                <div class="metric-label">Silhouette Score</div>
                <div class="metric-quality" :class="getQualityClass(selectedRun.metrics.silhouetteScore, 'silhouette')">
                  {{ getQualityText(selectedRun.metrics.silhouetteScore, 'silhouette') }}
                </div>
              </div>
              <div class="metric-card" v-if="selectedRun.metrics?.dbIndex"
                   v-tooltip="{ key: 'metrics.daviesBouldin' }">
                <div class="metric-value">{{ selectedRun.metrics.dbIndex.toFixed(3) }}</div>
                <div class="metric-label">Davies-Bouldin</div>
                <div class="metric-quality" :class="getQualityClass(selectedRun.metrics.dbIndex, 'db')">
                  {{ getQualityText(selectedRun.metrics.dbIndex, 'db') }}
                </div>
              </div>
              <div class="metric-card" v-if="selectedRun.metrics?.calinskiHarabasz"
                   v-tooltip="{ key: 'metrics.calinskiHarabasz' }">
                <div class="metric-value">{{ formatLargeNumber(selectedRun.metrics.calinskiHarabasz) }}</div>
                <div class="metric-label">Calinski-Harabasz</div>
                <div class="metric-quality" :class="getQualityClass(selectedRun.metrics.calinskiHarabasz, 'calinski')">
                  {{ getQualityText(selectedRun.metrics.calinskiHarabasz, 'calinski') }}
                </div>
              </div>
              <div class="metric-card" v-if="selectedRun.metrics?.discoScore !== undefined"
                   v-tooltip="{ key: 'metrics.disco' }">
                <div class="metric-value">{{ safeFormat(selectedRun.metrics.discoScore) }}</div>
                <div class="metric-label">DISCO Score</div>
                <div class="metric-quality" :class="getQualityClass(selectedRun.metrics.discoScore, 'disco')">
                  {{ getQualityText(selectedRun.metrics.discoScore, 'disco') }}
                </div>
              </div>
            </div>
            
            <!-- Unified Tooltip Component -->
            <TooltipComponent
              :visible="tooltipManager.globalState.visible"
              :content="tooltipManager.globalState.config.content"
              :title="tooltipManager.globalState.config.title"
              :position="tooltipManager.globalState.config.position"
              :theme="tooltipManager.globalState.config.theme"
              :size="tooltipManager.globalState.config.size"
              :target-element="tooltipManager.globalState.targetElement"
              :offset="tooltipManager.globalState.config.offset"
              :show-arrow="tooltipManager.globalState.config.showArrow"
              :interactive="tooltipManager.globalState.config.interactive"
              :show-close="tooltipManager.globalState.config.showClose"
              :max-width="tooltipManager.globalState.config.maxWidth"
              :is-rich-content="tooltipManager.globalState.config.isRichContent"
              :z-index="tooltipManager.globalState.config.zIndex"
              @close="tooltipManager.hide()"
            />
          </div>
        </div>

        <div class="visualizations-grid" v-if="selectedRun && analysisResults">
          <!-- Cluster Summary Table -->
          <div v-if="showClusterDetails && (clusterSummary || loadingStates.clusterSummary)" class="viz-card full-width">
            <h3>Cluster Summary</h3>
            <div v-if="loadingStates.clusterSummary" class="loading-state">
              <div class="loading-spinner"></div>
              <p>Calculating cluster statistics...</p>
            </div>
            <div v-else-if="clusterSummary" class="cluster-summary-table">
              <table class="analysis-table">
                <thead>
                  <tr>
                    <th>Cluster</th>
                    <th>Size</th>
                    <th>Percentage</th>
                    <th v-tooltip="{ key: 'metrics.compactness' }">Compactness</th>
                    <th v-tooltip="{ key: 'metrics.separation' }">Separation</th>
                    <th v-tooltip="{ key: 'metrics.density' }">Density</th>
                    <th v-tooltip="{ key: 'metrics.cohesion' }">Cohesion</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="cluster in clusterSummary" :key="cluster.id">
                    <td class="cluster-id">{{ cluster.id }}</td>
                    <td>{{ cluster.size.toLocaleString() }}</td>
                    <td>{{ cluster.percentage.toFixed(1) }}%</td>
                    <td>{{ cluster.compactness.toFixed(3) }}</td>
                    <td>{{ cluster.separation.toFixed(3) }}</td>
                    <td>{{ cluster.density.toFixed(3) }}</td>
                    <td>{{ cluster.cohesion.toFixed(3) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Feature Importance Analysis -->
          <div v-if="showFeatureImportance && (featureImportance || loadingStates.featureImportance)" class="viz-card feature-importance-card">
            <h3>Feature Importance</h3>
            <div class="feature-importance-explanation">
              <p><strong>How it's calculated:</strong> Features are ranked by their ability to separate clusters. The score compares between-cluster variance (how different cluster means are) to within-cluster variance (how scattered points are within each cluster). Higher scores indicate features that better distinguish between clusters.</p>
            </div>
            <div v-if="loadingStates.featureImportance" class="loading-state">
              <div class="loading-spinner"></div>
              <p>Analyzing feature importance...</p>
            </div>
            <div v-else-if="featureImportance" class="feature-importance-container">
              <div class="importance-header">
                <p class="importance-summary">
                  Showing top {{ Math.min(featureImportanceDisplayCount, featureImportance.length) }} most important features out of {{ featureImportance.length }} total features analyzed
                </p>
                <div class="importance-controls" v-if="featureImportance.length > 10">
                  <label>
                    Show:
                    <select v-model="featureImportanceDisplayCount" class="control-select small">
                      <option :value="10">Top 10</option>
                      <option :value="20">Top 20</option>
                      <option :value="50" v-if="featureImportance.length > 20">Top 50</option>
                      <option :value="featureImportance.length" v-if="featureImportance.length <= 100">All {{ featureImportance.length }}</option>
                    </select>
                  </label>
                </div>
              </div>
              <div class="importance-content">
                <div class="importance-chart" ref="featureImportanceChart"></div>
                <div class="importance-details">
                  <div v-for="(importance, index) in featureImportance.slice(0, featureImportanceDisplayCount)" :key="index" class="importance-item">
                    <div class="importance-rank">#{{ index + 1 }}</div>
                    <div class="feature-name">{{ importance.feature }}</div>
                    <div class="importance-bar">
                      <div class="importance-fill" :style="{ width: importance.score * 100 + '%' }"></div>
                    </div>
                    <div class="importance-score">{{ importance.score.toFixed(3) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Cluster Distribution -->
          <div v-if="showClusterDistribution && clusterDistribution" class="viz-card cluster-distribution-card">
            <h3>Cluster Size Distribution</h3>
            <div class="cluster-distribution-container">
              <div class="distribution-chart" ref="clusterDistributionChart"></div>
            </div>
          </div>


        </div>

        <!-- Empty State -->
        <div v-if="!selectedRun" class="empty-state">
          <div class="empty-icon">🔍</div>
          <h3>Select a Clustering Run to Analyze</h3>
          <p>Choose a clustering result from the sidebar to start your deep analysis.</p>
        </div>

        <!-- Loading State -->
        <div v-if="isAnalyzing" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Generating advanced analysis...</p>
        </div>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue';
import { useGlobalState } from '~/composables/useGlobalState';
import { useSidebarState } from '~/composables/useSidebarState';
import { useDatasetManager } from '~/composables/useDatasetManager';
import { useTooltipManager } from '~/composables/useTooltipManager';
import TooltipComponent from '~/components/TooltipComponent.vue';
import * as d3 from 'd3'

const globalState = useGlobalState()
const sidebar = useSidebarState()
const sidebarState = sidebar.state
const datasetManager = useDatasetManager()
const tooltipManager = useTooltipManager()

// Reactive data
const selectedSample = ref('blobs')
const selectedRunId = ref<string>('')
const isAnalyzing = ref(false)

// Clustering parameters
const selectedTreeType = ref<string>('DCTree')
const selectedPower = ref<number>(2)
const selectedPartitionMethod = ref<string>('auto')
const selectedK = ref<number>(3)
const treeVisualizationType = ref<string>('summarized')
const realTreeDepth = ref<number>(100)
const treeTypes = ref<string[]>([])
const partitionMethods = ref<string[]>([])
const maxK = ref<number>(10)

// Analysis options - always show useful components
const showClusterDetails = ref(true)
const showFeatureImportance = ref(true)
const showClusterDistribution = ref(true)
const featureImportanceDisplayCount = ref(10)

// Feature selection
const availableFeatures = ref<string[]>([])
const selectedFeatures = ref<number[]>([])

// Visualization controls (unused for now - prepared for future features)
// const colorBy = ref('cluster')
// const sizeBy = ref('uniform')

// Analysis results
const analysisResults = ref<any>(null)
const clusterSummary = ref<any[]>([])
const featureImportance = ref<any[]>([])
const clusterDistribution = ref<any>(null)

// Loading states for different analysis types
const loadingStates = ref({
  clusterSummary: false,
  featureImportance: false,
  clusterDistribution: false
})

// Component refs
const featureImportanceChart = ref<HTMLElement>()
const clusterDistributionChart = ref<HTMLElement>()

// Add proper interface definitions for run parameters
interface RunParameters {
  sample: string;
  uploadedFileName?: string;
  originalFeatureCount?: number;
  featureNames?: string[];
  [key: string]: any;
}

// ClusterRun interface moved to types file or can be imported from global state

// Computed properties
// availableRuns computed property removed - directly using globalState.clusterRuns in template

const selectedRun = ref<ClusterRun | null>(null)

// Watch for changes in selectedRunId and load the run data
watch(selectedRunId, async (newRunId) => {
  if (newRunId) {
    console.log('[ClusteringExplorer] Loading run data for ID:', newRunId)
    selectedRun.value = await globalState.getRunByIdAsync(newRunId)
    if (!selectedRun.value) {
      console.warn('[ClusteringExplorer] Failed to load run data for ID:', newRunId)
      // Try to get it from the active run directly
      const activeRun = globalState.activeRun.value
      if (activeRun && activeRun.id === newRunId) {
        console.log('[ClusteringExplorer] Using active run as fallback')
        selectedRun.value = activeRun
      }
    } else {
      console.log('[ClusteringExplorer] Successfully loaded run data:', selectedRun.value.dataset)
    }
  } else {
    selectedRun.value = null
  }
}, { immediate: true })

// Watch for changes in active run data to handle timing issues
watch(() => globalState.activeRun.value, async (newActiveRun) => {
  if (newActiveRun && newActiveRun.id === selectedRunId.value) {
    console.log('[ClusteringExplorer] Active run data updated, reloading analysis')
    await loadRunAnalysis()
  }
}, { deep: true })

const quickStatsDisplay = computed(() => {
  // First priority: Check active run directly
  const activeRun = globalState.activeRun.value
  if (activeRun?.clusterData?.points) {
    const stats = {
      pointCount: activeRun.clusterData.points.length,
      featureCount: selectedFeatures.value.length || activeRun.clusterData.points[0]?.length || 0
    }
    console.log('[ClusteringExplorer] QuickStats from active run:', stats)
    return stats
  }
  
  // Second priority: Check selected run
  if (!selectedRun.value) {
    console.log('[ClusteringExplorer] QuickStats: No selected run')
    return { pointCount: 0, featureCount: 0 }
  }
  
  const stats = {
    pointCount: selectedRun.value?.clusterData?.points?.length || 0,
    featureCount: selectedFeatures.value.length || selectedRun.value?.clusterData?.points?.[0]?.length || 0
  }
  console.log('[ClusteringExplorer] QuickStats from selected run:', stats)
  return stats
})

const selectedFeatureNames = computed(() => {
  return selectedFeatures.value.map(index => availableFeatures.value[index] || `Feature ${index + 1}`)
})

const actualClusterCount = computed(() => {
  // First try selected run
  if (selectedRun.value?.clusterData?.labels) {
    return new Set(selectedRun.value.clusterData.labels).size
  }
  
  // Fallback to active run
  const activeRun = globalState.activeRun.value
  if (activeRun?.clusterData?.labels) {
    return new Set(activeRun.clusterData.labels).size
  }
  
  return 0
})


// ClusterSummaryItem interface moved to types file or can be imported from composables

interface FeatureImportanceItem {
  feature: string;
  score: number;
  index: number;
}


// Computed property to get the original feature count from the run data (similar to clustering.vue)
const rawFeatureCount = computed(() => {
  let run = selectedRun.value
  
  // If no selected run, try active run as fallback
  if (!run) {
    const activeRun = globalState.activeRun.value
    if (activeRun && activeRun.id === selectedRunId.value) {
      run = activeRun
    } else {
      return 0
    }
  }
  
  // Debug the computed property itself
  console.log('[ClusteringExplorer] rawFeatureCount computed debug:', {
    hasClusterData: !!run.clusterData,
    hasOriginalPoints: !!run.clusterData?.original_points,
    originalPointsLength: run.clusterData?.original_points?.length,
    firstPointLength: run.clusterData?.original_points?.[0]?.length,
    currentDatasetFeatureCount: globalState.currentDataset.value?.featureCount,
    runParametersFeatureCount: (run.parameters as any)?.originalFeatureCount
  })
  
  // First priority: Check if we have original_points from cluster data
  if (run.clusterData?.original_points && run.clusterData.original_points.length > 0 && run.clusterData.original_points[0]?.length > 0) {
    console.log('[ClusteringExplorer] Using original_points length:', run.clusterData.original_points[0].length)
    return run.clusterData.original_points[0].length
  }
  
  // Second priority: Get from global dataset state (most reliable for current active dataset)
  const currentDataset = globalState.currentDataset.value
  if (currentDataset && currentDataset.featureCount && currentDataset.featureCount > 0) {
    console.log('[ClusteringExplorer] Using currentDataset featureCount:', currentDataset.featureCount)
    return currentDataset.featureCount
  }
  
  // Third priority: Use stored parameters from the run (if available)
  const runParams = run.parameters as RunParameters
  if (runParams && runParams.originalFeatureCount) {
    console.log('[ClusteringExplorer] Using run parameters originalFeatureCount:', runParams.originalFeatureCount)
    return runParams.originalFeatureCount
  }
  
  // Fourth priority: Get from cluster data points only if no DR was applied
  if (run.clusterData?.points?.length > 0 && run.clusterData.points[0]?.length > 0) {
    const hasReducedDimensions = run.clusterData.dimensionality_reduction && 
      (run.clusterData.dimensionality_reduction.pca || run.clusterData.dimensionality_reduction.umap)
    
    if (!hasReducedDimensions) {
      console.log('[ClusteringExplorer] Using cluster data points length:', run.clusterData.points[0].length)
      return run.clusterData.points[0].length
    }
  }
  
  // Fifth priority: Known sample data defaults - use global state sampleOptions
  const datasetName = run.dataset?.toLowerCase()
  if (datasetName) {
    const sampleOption = globalState.sampleOptions.find(opt => opt.value === datasetName);
    if (sampleOption?.dimensions) {
      return sampleOption.dimensions;
    }
  }
  
  // Last resort: try to get from the run metadata
  if (run.clusterData?.points?.length > 0 && run.clusterData.points[0]?.length > 0) {
    return run.clusterData.points[0].length
  }
  
  return 0
})

// Computed property to get feature names from multiple sources
const computedFeatureNames = computed(() => {
  const run = selectedRun.value
  if (!run) return []
  
  const featureCount = rawFeatureCount.value
  if (featureCount === 0) return []
  
  // First priority: Try to get feature names from the dataset manager if it matches the current dataset
  const currentDataset = globalState.currentDataset.value
  if (currentDataset && currentDataset.name === run.dataset) {
    const managerFeatures = datasetManager.getFeatureNames()
    if (managerFeatures.length >= featureCount) {
      return managerFeatures.slice(0, featureCount)
    }
  }
  
  // Second priority: Try to get from run parameters if stored
  const runParams = run.parameters as RunParameters
  if (runParams && runParams.featureNames && Array.isArray(runParams.featureNames)) {
    if (runParams.featureNames.length >= featureCount) {
      return runParams.featureNames.slice(0, featureCount)
    }
  }
  
  // Third priority: Try to get from global state dataset headers
  if (currentDataset && currentDataset.headers && currentDataset.headers.length >= featureCount) {
    return currentDataset.headers.slice(0, featureCount)
  }
  
  // Fourth priority: Generate default feature names
  return Array.from({ length: featureCount }, (_, i) => `Feature ${i + 1}`)
})

// Event handlers
const handleRunSelected = (runId: string) => {
  selectedRunId.value = runId
  loadRunAnalysis()
}

const handleRunLoaded = (run: any) => {
  if (run && run.id) {
    selectedRunId.value = run.id
    loadRunAnalysis()
  }
}

const loadRunAnalysis = async () => {
  if (!selectedRunId.value) {
    analysisResults.value = null
    return
  }
  
  let run = selectedRun.value
  if (!run) {
    console.warn('[ClusteringExplorer] No run data available, trying active run as fallback')
    // Try to get from active run as fallback
    const activeRun = globalState.activeRun.value
    if (activeRun && activeRun.id === selectedRunId.value) {
      console.log('[ClusteringExplorer] Using active run as fallback for analysis')
      run = activeRun
    } else {
      console.error('[ClusteringExplorer] Cannot load analysis: no run data available')
      analysisResults.value = null
      return
    }
  }
  
  // Always set analysisResults first to show the UI
  analysisResults.value = {
    timestamp: new Date(),
    runId: selectedRunId.value
  }
  
  // Direct feature count calculation using the local run variable
  let featureCount = 0
  let featureNames: string[] = []
  
  // First priority: Check if we have original_points from cluster data
  if (run.clusterData?.original_points && run.clusterData.original_points.length > 0 && run.clusterData.original_points[0]?.length > 0) {
    featureCount = run.clusterData.original_points[0].length
    console.log('[ClusteringExplorer] Using original_points length:', featureCount)
  }
  // Second priority: Get from global dataset state
  else if (globalState.currentDataset.value?.featureCount && globalState.currentDataset.value.featureCount > 0) {
    featureCount = globalState.currentDataset.value.featureCount
    console.log('[ClusteringExplorer] Using currentDataset featureCount:', featureCount)
  }
  // Third priority: Use stored parameters from the run
  else if ((run.parameters as any)?.originalFeatureCount) {
    featureCount = (run.parameters as any).originalFeatureCount
    console.log('[ClusteringExplorer] Using run parameters originalFeatureCount:', featureCount)
  }
  // Fourth priority: Get from cluster data points if no DR was applied
  else if (run.clusterData?.points?.length > 0 && run.clusterData.points[0]?.length > 0) {
    const hasReducedDimensions = !!(run.clusterData?.dimensionality_reduction?.pca || run.clusterData?.dimensionality_reduction?.umap)
    if (!hasReducedDimensions) {
      featureCount = run.clusterData.points[0].length
      console.log('[ClusteringExplorer] Using cluster data points length:', featureCount)
    }
  }
  
  // Generate feature names
  if (featureCount > 0) {
    // Try to get feature names from dataset manager
    const currentDataset = globalState.currentDataset.value
    if (currentDataset && currentDataset.name === run.dataset) {
      const managerFeatures = datasetManager.getFeatureNames()
      if (managerFeatures.length >= featureCount) {
        featureNames = managerFeatures.slice(0, featureCount)
      }
    }
    
    // Fallback to run parameters
    if (featureNames.length === 0) {
      const runParams = run.parameters as any
      if (runParams?.featureNames && Array.isArray(runParams.featureNames) && runParams.featureNames.length >= featureCount) {
        featureNames = runParams.featureNames.slice(0, featureCount)
      }
    }
    
    // Fallback to dataset headers
    if (featureNames.length === 0 && currentDataset?.headers && currentDataset.headers.length >= featureCount) {
      featureNames = currentDataset.headers.slice(0, featureCount)
    }
    
    // Final fallback to generated names
    if (featureNames.length === 0) {
      featureNames = Array.from({ length: featureCount }, (_, i) => `Feature ${i + 1}`)
    }
    
    availableFeatures.value = featureNames
    
    // Select all features by default if none selected
    if (selectedFeatures.value.length === 0) {
      selectedFeatures.value = Array.from({ length: featureCount }, (_, i) => i)
    } else {
      // Ensure selected features are valid for current dataset
      selectedFeatures.value = selectedFeatures.value.filter(index => index < featureCount)
    }
    
    console.log(`[ClusteringExplorer] Loaded ${featureCount} features:`, featureNames.slice(0, 10))
  } else {
    console.warn('[ClusteringExplorer] No features detected for run:', run.dataset)
    availableFeatures.value = []
    selectedFeatures.value = []
  }
  
  // If no cluster data, still show the UI but skip analysis generation
  if (!run.clusterData) {
    console.warn('[ClusteringExplorer] No cluster data available for run:', run.dataset)
    return
  }
  
  isAnalyzing.value = true
  
  try {
    // Generate basic cluster analysis
    try {
      await generateClusterSummary(run)
    } catch (error) {
      console.warn('[ClusteringExplorer] Failed to generate cluster summary:', error)
    }
    
    // Generate additional analyses based on user selections
    if (showFeatureImportance.value) {
      try {
        await generateFeatureImportance(run)
      } catch (error) {
        console.warn('[ClusteringExplorer] Failed to generate feature importance:', error)
      }
    }
    
    if (showClusterDistribution.value) {
      try {
        await generateClusterDistribution(run)
      } catch (error) {
        console.warn('[ClusteringExplorer] Failed to generate cluster distribution:', error)
      }
    }
    
    nextTick(() => {
      renderVisualizations()
    })
    
  } finally {
    isAnalyzing.value = false
  }
}

const hasValidData = computed(() => {
  // Check if we have a valid dataset to cluster with
  const currentDataset = globalState.currentDataset.value
  if (!currentDataset) return false
  
  // For clustering, we need a valid dataset (sample, uploaded, or imported)
  const hasDataset = currentDataset.type === 'sample' || 
                    (currentDataset.type === 'uploaded' && currentDataset.data) ||
                    (currentDataset.type === 'imported' && currentDataset.data)
  
  return hasDataset
})

const runClustering = () => {
  if (!hasValidData.value) return
  
  // Update global state with current parameters
  globalState.updateClusteringParameter('treeType', selectedTreeType.value)
  globalState.updateClusteringParameter('power', selectedPower.value)
  globalState.updateClusteringParameter('partitionMethod', selectedPartitionMethod.value)
  globalState.updateClusteringParameter('selectedK', selectedK.value)
  
  // Navigate to clustering page
  navigateTo('/clustering')
}

const updateAnalysis = () => {
  if (selectedRunId.value) {
    loadRunAnalysis()
  }
}

// Feature selection methods
const selectAllFeatures = () => {
  selectedFeatures.value = Array.from({ length: availableFeatures.value.length }, (_, i) => i)
  updateAnalysis()
}

const clearAllFeatures = () => {
  selectedFeatures.value = []
  updateAnalysis()
}


const generateClusterSummary = async (run?: any) => {
  if (!run) run = selectedRun.value
  if (!run?.clusterData?.labels || !run.clusterData.points) return
  
  // Determine if we should use backend analysis
  const dataPoints = run.clusterData.points
  const shouldUseBackend = dataPoints.length > 1000 || selectedFeatures.value.length > 10
  
  loadingStates.value.clusterSummary = true
  
  if (shouldUseBackend) {
    try {
      console.log('[ClusteringExplorer] Using backend for cluster summary analysis')
      
      const analysisRequest = {
        cluster_data: run.clusterData,
        selected_features: selectedFeatures.value,
        feature_names: selectedFeatureNames.value,
        options: {
          include_centroids: true,
          calculate_advanced_metrics: true
        }
      }
      
      const response = await $fetch('/api/analyze/cluster-summary', {
        method: 'POST',
        body: analysisRequest
      })
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      clusterSummary.value = response.cluster_summary
      console.log(`[ClusteringExplorer] Backend cluster summary completed for ${response.total_clusters} clusters`)
      loadingStates.value.clusterSummary = false
      return
      
    } catch (error) {
      console.warn('[ClusteringExplorer] Backend cluster summary failed, falling back to frontend:', error)
      // Fall through to frontend calculation
    }
  }
  
  // Frontend fallback for smaller datasets or when backend fails
  console.log('[ClusteringExplorer] Using frontend for cluster summary analysis')
  
  const { labels, points } = run.clusterData
  const uniqueLabels = [...new Set(labels)]
  const summary = []
  
  for (const label of uniqueLabels) {
    const clusterPoints = points.filter((_: any, index: number) => labels[index] === label)
    const size = clusterPoints.length
    const percentage = (size / labels.length) * 100
    
    // Calculate cluster centroid
    const centroid = calculateCentroid(clusterPoints)
    
    // Calculate compactness (average distance to centroid)
    const compactness = calculateAverageDistance(clusterPoints, centroid)
    
    // Calculate separation (distance to nearest other cluster)
    const otherCentroids = uniqueLabels
      .filter(l => l !== label)
      .map(l => {
        const otherPoints = points.filter((_: any, index: number) => labels[index] === l)
        return calculateCentroid(otherPoints)
      })
    
    const separation = otherCentroids.length > 0 
      ? Math.min(...otherCentroids.map(c => calculateDistance(centroid, c)))
      : 0
    
    // Calculate density (points per unit volume - simplified)
    const density = size / (compactness * compactness + 1)
    
    // Calculate cohesion (silhouette-like measure for this cluster)
    const cohesion = separation / (compactness + 0.001)
    
    summary.push({
      id: label,
      size,
      percentage,
      compactness,
      separation,
      density,
      cohesion,
      centroid
    })
  }
  
  clusterSummary.value = summary.sort((a, b) => (a.id as number) - (b.id as number))
  
  // Reset loading state
  loadingStates.value.clusterSummary = false
}

/**
 * Generate feature importance analysis for clustering results
 * 
 * Feature importance is calculated using variance ratio method:
 * - Backend (for large datasets): Uses variance_ratio method with optimized calculations
 * - Frontend (for smaller datasets): Calculates between-cluster vs within-cluster variance
 * 
 * Algorithm:
 * 1. For each feature, calculate the mean value across all data points
 * 2. For each cluster, calculate the cluster mean for that feature
 * 3. Between-cluster variance = Σ(cluster_size * (cluster_mean - overall_mean)²)
 * 4. Within-cluster variance = Σ(Σ(point_value - cluster_mean)²) for all clusters
 * 5. Importance score = between_variance / (within_variance + ε)
 * 
 * Higher scores indicate features that better separate clusters (high between-cluster variance)
 * relative to variation within clusters (low within-cluster variance).
 */
const generateFeatureImportance = async (run?: any) => {
  if (!run) run = selectedRun.value
  if (!run?.clusterData?.points || !run.clusterData.labels) return
  
  // Use original points if available, otherwise use current points
  const points = run.clusterData.original_points || run.clusterData.points
  const labels = run.clusterData.labels
  const numFeatures = rawFeatureCount.value
  
  loadingStates.value.featureImportance = true
  
  // Always use the new dataset-based backend endpoint for reliable analysis
  try {
    console.log('[ClusteringExplorer] Using new dataset-based backend for feature importance analysis')
    
    // Extract dataset identifier from run dataset name
    let datasetId = run.dataset
    if (datasetId.includes('(') && datasetId.includes(' samples')) {
      // Extract base name from "digits_full (5620 samples)" -> "digits_full"
      datasetId = datasetId.split(' (')[0]
    }
    
    console.log('[ClusteringExplorer] Dataset ID:', datasetId)
    console.log('[ClusteringExplorer] Cluster labels:', run.clusterData?.labels?.length, 'labels')
    
    // Use ALL features for importance analysis, not just selected ones
    const allFeatures = Array.from({ length: numFeatures }, (_, i) => i)
    const allFeatureNames = Array.from({ length: numFeatures }, (_, i) => 
      availableFeatures.value[i] || `Feature ${i + 1}`
    )

    const analysisRequest = {
      dataset_id: datasetId,
      cluster_labels: run.clusterData.labels,
      selected_features: allFeatures,
      feature_names: allFeatureNames,
      options: {
        method: 'variance_ratio',
        normalize: true,
        include_raw_scores: true
      }
    }
    
    const response = await $fetch('/api/analyze/feature-importance-dataset', {
      method: 'POST',
      body: analysisRequest
    })
    
    if (response.error) {
      throw new Error(response.error)
    }
    
    // Convert backend response to frontend format
    featureImportance.value = response.feature_importance.map((item: any) => ({
      feature: item.feature,
      score: item.score,
      index: item.index
    }))
    
    console.log(`[ClusteringExplorer] Dataset-based feature importance completed for ${response.num_features} features`)
    loadingStates.value.featureImportance = false
    return
    
  } catch (error) {
    console.warn('[ClusteringExplorer] Dataset-based feature importance failed, falling back to legacy method:', error)
    // Fall through to frontend calculation
  }
  
  // Frontend fallback for smaller datasets or when backend fails
  console.log('[ClusteringExplorer] Using frontend for feature importance analysis')
  
  const importance: FeatureImportanceItem[] = []
  
  // Calculate feature importance using cluster separation for ALL features (not just selected ones)
  // This ensures we get the full picture of feature importance across the entire dataset
  const featuresToAnalyze = Array.from({ length: numFeatures }, (_, i) => i)
  
  for (const featureIndex of featuresToAnalyze) {
    if (featureIndex >= numFeatures) continue
    
    // Extract all values for this feature across all data points
    const featureValues = points.map((point: number[]) => point[featureIndex])
    
    // Calculate between-cluster variance vs within-cluster variance for this feature
    const uniqueLabels = [...new Set(labels)]
    let betweenVariance = 0
    let withinVariance = 0
    
    // Step 1: Calculate overall mean for this feature
    const overallMean = featureValues.reduce((sum: number, val: number) => sum + val, 0) / featureValues.length
    
    // Step 2: For each cluster, calculate contribution to between and within variance
    for (const label of uniqueLabels) {
      const clusterValues = featureValues.filter((_: number, index: number) => labels[index] === label)
      const clusterMean = clusterValues.reduce((sum: number, val: number) => sum + val, 0) / clusterValues.length
      const clusterSize = clusterValues.length
      
      // Between-cluster variance: how much this cluster's mean differs from overall mean
      betweenVariance += clusterSize * Math.pow(clusterMean - overallMean, 2)
      
      // Within-cluster variance: how much points in this cluster vary from cluster mean
      const clusterWithinVariance = clusterValues.reduce((sum: number, val: number) => sum + Math.pow(val - clusterMean, 2), 0)
      withinVariance += clusterWithinVariance
    }
    
    // Step 3: Calculate importance score as ratio of between to within variance
    const score = betweenVariance / (withinVariance + 1e-8) // Add small epsilon to avoid division by zero
    
    importance.push({
      feature: availableFeatures.value[featureIndex] || `Feature ${featureIndex + 1}`,
      score: Math.min(score / 100, 1), // Normalize to 0-1 range for display
      index: featureIndex
    })
  }
  
  featureImportance.value = importance.sort((a, b) => b.score - a.score)
  
  // Reset loading state
  loadingStates.value.featureImportance = false
}

const generateClusterDistribution = async (run?: any) => {
  if (!run) run = selectedRun.value
  if (!run?.clusterData?.labels || !run.clusterData.points) return
  
  const labels = run.clusterData.labels
  const distribution: Record<number, number> = {}
  
  for (const label of labels) {
    if (!distribution[label]) {
      distribution[label] = 0
    }
    distribution[label]++
  }
  
  clusterDistribution.value = distribution
}


// Utility functions
const calculateCentroid = (points: number[][]): number[] => {
  if (points.length === 0) return []
  
  const dimensions = points[0].length
  const centroid = new Array(dimensions).fill(0)
  
  points.forEach(point => {
    point.forEach((value, dim) => {
      centroid[dim] += value
    })
  })
  
  return centroid.map(sum => sum / points.length)
}

const calculateDistance = (point1: number[], point2: number[]): number => {
  let sum = 0
  for (let i = 0; i < Math.min(point1.length, point2.length); i++) {
    sum += Math.pow(point1[i] - point2[i], 2)
  }
  return Math.sqrt(sum)
}

const calculateAverageDistance = (points: number[][], centroid: number[]): number => {
  if (points.length === 0) return 0
  
  const distances = points.map(point => calculateDistance(point, centroid))
  return distances.reduce((sum, dist) => sum + dist, 0) / distances.length
}

const formatDate = (date: Date | string): string => {
  const d = new Date(date);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const formatLargeNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toFixed(0)
}

const safeFormat = (val: number | undefined | null, digits: number = 3): string => {
  if (val === undefined || val === null || isNaN(val)) return 'N/A'
  return val.toFixed(digits)
}

const getQualityClass = (value: number, metric: string): string => {
  switch (metric) {
    case 'silhouette':
      if (value >= 0.7) return 'excellent'
      if (value >= 0.5) return 'good'
      if (value >= 0.3) return 'fair'
      return 'poor'
    case 'db':
      if (value <= 0.5) return 'excellent'
      if (value <= 1.0) return 'good'
      if (value <= 1.5) return 'fair'
      return 'poor'
    case 'calinski':
      if (value >= 1000) return 'excellent'
      if (value >= 500) return 'good'
      if (value >= 100) return 'fair'
      return 'poor'
    case 'ari':
      if (value >= 0.8) return 'excellent'
      if (value >= 0.6) return 'good'
      if (value >= 0.4) return 'fair'
      return 'poor'
    case 'disco':
      if (value >= 0.7) return 'excellent'
      if (value >= 0.5) return 'good'
      if (value >= 0.3) return 'fair'
      return 'poor'
    default:
      return 'neutral'
  }
}

const getQualityText = (value: number, metric: string): string => {
  const quality = getQualityClass(value, metric)
  const qualityTexts = {
    excellent: 'Excellent',
    good: 'Good',
    fair: 'Fair',
    poor: 'Poor',
    neutral: 'Neutral'
  }
  return qualityTexts[quality as keyof typeof qualityTexts] || 'Unknown'
}

// Visualization functions
const renderVisualizations = () => {
  renderFeatureImportanceChart()
  renderClusterDistribution()
}

const renderFeatureImportanceChart = () => {
  if (!featureImportanceChart.value || !featureImportance.value.length) return
  
  d3.select(featureImportanceChart.value).selectAll("*").remove()
  
  const data = featureImportance.value.slice(0, 10) // Top 10 features
  const margin = { top: 20, right: 20, bottom: 40, left: 100 }
  const width = 400 - margin.left - margin.right
  const height = 300 - margin.top - margin.bottom
  
  const svg = d3.select(featureImportanceChart.value)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  const x = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.score) || 1])
    .range([0, width])
  
  const y = d3.scaleBand()
    .domain(data.map(d => d.feature))
    .range([0, height])
    .padding(0.1)
  
  svg.selectAll(".bar")
    .data(data)
    .enter()
    .append("rect")
    .attr("class", "bar")
    .attr("x", 0)
    .attr("y", d => y(d.feature) || 0)
    .attr("width", d => x(d.score))
    .attr("height", y.bandwidth())
    .attr("fill", "#3b82f6")
    .attr("opacity", 0.8)
  
  svg.append("g")
    .call(d3.axisLeft(y))
  
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x))
}


const renderClusterDistribution = () => {
  if (!clusterDistributionChart.value || !clusterDistribution.value) return
  
  d3.select(clusterDistributionChart.value).selectAll("*").remove()
  
  const data = Object.entries(clusterDistribution.value).map(([label, count]) => ({
    label: parseInt(label),
    count
  }))
  
  const margin = { top: 20, right: 20, bottom: 40, left: 60 }
  const width = 600 - margin.left - margin.right
  const height = 300 - margin.top - margin.bottom
  
  const svg = d3.select(clusterDistributionChart.value)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
     const x = d3.scaleBand()
     .domain(data.map((d: any) => d.label.toString()))
     .range([0, width])
     .padding(0.1)
   
      const y = d3.scaleLinear()
      .domain([0, Math.max(...data.map((d: any) => d.count as number)) || 1])
      .range([height, 0])
  
  svg.selectAll(".bar")
    .data(data)
    .enter()
    .append("rect")
    .attr("class", "bar")
    .attr("x", (d: any) => x(d.label.toString()) || 0)
    .attr("y", (d: any) => y(d.count))
    .attr("width", x.bandwidth())
    .attr("height", (d: any) => height - y(d.count))
    .attr("fill", "#3b82f6")
    .attr("opacity", 0.8)
  
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x))
  
  svg.append("g")
    .call(d3.axisLeft(y))
  
  // Add X-axis label
  svg.append("text")
    .attr("transform", `translate(${width / 2}, ${height + margin.bottom - 5})`)
    .style("text-anchor", "middle")
    .style("font-size", "12px")
    .style("fill", "#374151")
    .text("Cluster ID")
  
  // Add Y-axis label
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "12px")
    .style("fill", "#374151")
    .text("Number of Points")
}

// Lifecycle
onMounted(async () => {
  // Initialize clustering parameters from global state
  const savedParams = globalState.clusteringParameters.value
  if (savedParams) {
    selectedTreeType.value = savedParams.treeType || 'DCTree'
    selectedPower.value = savedParams.power || 2
    selectedPartitionMethod.value = savedParams.partitionMethod || 'auto'
    selectedK.value = savedParams.selectedK || 3
  }

  // Load backend clustering options
  try {
    const options = await $fetch('/api/cluster/options')
    treeTypes.value = options.treeTypes || ['DCTree']
    partitionMethods.value = options.partitionMethods || ['auto']
    
    // Validate selected values against available options
    if (!treeTypes.value.includes(selectedTreeType.value)) {
      selectedTreeType.value = treeTypes.value[0] || 'DCTree'
    }
    if (!partitionMethods.value.includes(selectedPartitionMethod.value)) {
      selectedPartitionMethod.value = partitionMethods.value[0] || 'auto'
    }
  } catch (error) {
    console.warn('Failed to load clustering options:', error)
    // Use defaults
    treeTypes.value = ['DCTree']
    partitionMethods.value = ['auto']
  }

  // Auto-select the active run if available
  if (globalState.activeRun.value) {
    console.log('[ClusteringExplorer] Auto-selecting active run:', globalState.activeRun.value.id)
    selectedRunId.value = globalState.activeRun.value.id
    loadRunAnalysis()
  } else {
    console.log('[ClusteringExplorer] No active run found on mount')
    // Try to use the most recent run if available
    if (globalState.clusterRuns.value.length > 0) {
      const mostRecentRun = globalState.clusterRuns.value[0]
      console.log('[ClusteringExplorer] Using most recent run:', mostRecentRun.id)
      selectedRunId.value = mostRecentRun.id
      loadRunAnalysis()
    }
  }
})

// Watch for changes in active run
watch(() => globalState.activeRun.value, (newActiveRun) => {
  if (newActiveRun && selectedRunId.value !== newActiveRun.id) {
    console.log('[ClusteringExplorer] Active run changed, loading:', newActiveRun.id)
    selectedRunId.value = newActiveRun.id
    loadRunAnalysis()
  } else if (!newActiveRun && selectedRunId.value) {
    console.log('[ClusteringExplorer] Active run cleared, clearing selection')
    selectedRunId.value = ''
    analysisResults.value = null
  }
})

// Watch for clustering parameter changes and sync with global state
watch([selectedTreeType, selectedPower, selectedPartitionMethod, selectedK], () => {
  globalState.updateClusteringParameter('treeType', selectedTreeType.value)
  globalState.updateClusteringParameter('power', selectedPower.value)
  globalState.updateClusteringParameter('partitionMethod', selectedPartitionMethod.value)
  globalState.updateClusteringParameter('selectedK', selectedK.value)
})
</script>

<style scoped>
.clustering-explorer-content {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
  font-family: 'Inter', sans-serif;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
}

.page-header p {
  color: #6b7280;
  font-size: 1rem;
  margin: 0;
}

/* Overview Section */
.overview-section {
  margin-bottom: 40px;
}

.overview-section h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 16px 0;
}

.run-summary-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 32px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.run-info {
  padding-right: 32px;
  border-right: 1px solid #e5e7eb;
}

.run-info h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 16px 0;
}

.run-metadata {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.meta-label {
  color: #6b7280;
}

.meta-value {
  font-weight: 500;
  color: #111827;
}

/* Metrics Grid */
.run-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.metric-card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: all 0.2s ease;
}

.metric-card:hover {
  border-color: #d1d5db;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 0.75rem;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.metric-quality {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 9999px;
}

/* Quality Colors */
.metric-quality.excellent { background: #dcfce7; color: #166534; }
.metric-quality.good { background: #dbeafe; color: #1e40af; }
.metric-quality.fair { background: #fef9c3; color: #854d0e; }
.metric-quality.poor { background: #fee2e2; color: #991b1b; }

/* Visualizations Grid */
.visualizations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 24px;
}

.viz-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.viz-card.full-width {
  grid-column: 1 / -1;
}

.viz-card h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 24px 0;
}

/* Tables */
.analysis-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.analysis-table th {
  text-align: left;
  padding: 12px 16px;
  background: #f9fafb;
  color: #4b5563;
  font-weight: 600;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
}

.analysis-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  color: #111827;
}

.analysis-table tr:last-child td {
  border-bottom: none;
}

.cluster-id {
  font-weight: 600;
  color: #3b82f6;
}

/* Feature Importance */
.feature-importance-explanation {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 24px;
  font-size: 0.875rem;
  color: #4b5563;
  line-height: 1.5;
}

.importance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.importance-summary {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

.importance-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}

.importance-rank {
  width: 32px;
  font-weight: 600;
  color: #9ca3af;
  font-size: 0.875rem;
}

.feature-name {
  width: 150px;
  font-weight: 500;
  color: #111827;
  font-size: 0.875rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.importance-bar {
  flex: 1;
  height: 8px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}

.importance-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 4px;
}

.importance-score {
  width: 60px;
  text-align: right;
  font-family: monospace;
  color: #4b5563;
  font-size: 0.875rem;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  background: #f9fafb;
  border: 1px dashed #e5e7eb;
  border-radius: 12px;
  margin-top: 40px;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  color: #9ca3af;
}

.empty-state h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
}

.empty-state p {
  color: #6b7280;
  font-size: 1rem;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #6b7280;
}

.loading-spinner {
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Sidebar Styles */
.control-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid #e5e7eb;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 16px;
}

.info-box {
  background-color: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  padding: 12px;
  font-size: 0.875rem;
  color: #1e40af;
  margin-bottom: 16px;
}


.analysis-controls {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.analysis-controls h4 {
  margin: 0 0 12px 0;
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  color: #374151;
  cursor: pointer;
}

.form-group input[type="checkbox"] {
  accent-color: #3b82f6;
}

.feature-btn {
  background-color: #6b7280;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
  flex: 1;
}

.feature-btn:hover {
  background-color: #4b5563;
}

.feature-btn:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}

.feature-btn.primary {
  background-color: #3b82f6;
}

.feature-btn.primary:hover {
  background-color: #2563eb;
}

</style>
