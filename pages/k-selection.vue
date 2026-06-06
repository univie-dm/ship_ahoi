<template>
  <AppLayout :showSidebar="true">
    <template #sidebar>
      <SharedSidebar
        :sampleOptions="sampleOptions"
        :currentPartitionMethod="'K'"
        :showVisualizationOptions="false"
        :showExportImport="true"
        :showPageControls="false"
        :isDendrogramVisible="false"
        :isScatterVisible="!!clusterVisualizationData"
        :isIcicleVisible="false"
        :showDataManagement="false"
      >
        <!-- Tree Type Select Slot -->
        <template #tree-type-select>
          <select v-model="clusterParams.treeType" @change="handleParameterChange" class="form-select">
            <option v-for="treeType in availableTreeTypes" :key="treeType" :value="treeType">
              {{ treeType }}
            </option>
          </select>
        </template>

        <!-- Power Select Slot -->
        <template #power-select>
          <div class="power-input-container">
            <input
              type="range"
              v-model.number="clusterParams.power"
              @change="handleParameterChange"
              min="0"
              max="10"
              step="1"
              class="form-range"
            />
            <span class="power-value">{{ clusterParams.power }}</span>
          </div>
        </template>

        <!-- K Range Controls Slot -->
        <template #k-slider>
          <div class="k-range-sidebar">
            <div class="k-range-inputs-sidebar">
              <input
                type="number"
                v-model.number="kRangeStart"
                @change="updateKRange"
                min="2"
                max="20"
                placeholder="Min"
                class="form-input k-input-small"
              />
              <span class="range-separator">to</span>
              <input
                type="number"
                v-model.number="kRangeEnd"
                @change="updateKRange"
                min="2"
                max="20"
                placeholder="Max"
                class="form-input k-input-small"
              />
            </div>
            <div class="k-range-display-sidebar">
              Testing: {{ kRange.join(', ') }}
            </div>
          </div>
        </template>

        <!-- Run Analysis Button Slot -->
        <template #run-button>
          <button
            v-if="!isLoading"
            @click="runKSelectionAnalysis"
            :disabled="!globalState.currentDataset.value"
            class="btn btn-primary analysis-btn"
          >
            Run K-Selection Analysis
          </button>
          <LoadingBar
            v-else
            :isLoading="isLoading"
            message="Analyzing k-values..."
            :onAbort="abortAnalysis"
          />
        </template>
      </SharedSidebar>
    </template>

    <template #default>
      <div class="k-selection-content">
        <!-- Page Header -->
        <div class="page-header">
          <h1>K-Selection Analysis</h1>
          <p>Determine the optimal number of clusters using various validation methods and interactive visualizations</p>
        </div>

        <!-- Analysis Results -->
        <div v-if="analysisResults" class="analysis-results">
          <!-- Optimal K Suggestions -->
          <div class="optimal-k-suggestions">
            <h3>Optimal K Suggestions</h3>
            <div class="suggestions-grid">
              <div
                v-for="(k, method) in analysisResults.optimal_k_suggestions"
                :key="method"
                class="suggestion-card"
                :class="{ 'highlighted': selectedOptimalK === k }"
                @click="selectOptimalK(k)"
              >
                <div class="method-name">{{ formatMethodName(method) }}</div>
                <div class="k-value">k = {{ k }}</div>
              </div>
            </div>
          </div>

          <!-- Plot Selection Controls -->
          <div class="plot-selection-controls">
            <h4>Select Plot:</h4>
            <label><input type="radio" v-model="selectedPlotType" value="elbow"> Elbow Method</label>
            <label><input type="radio" v-model="selectedPlotType" value="silhouette"> Silhouette Score</label>
            <label><input type="radio" v-model="selectedPlotType" value="davies_bouldin"> Davies-Bouldin Index</label>
            <label><input type="radio" v-model="selectedPlotType" value="calinski"> Calinski-Harabasz Index</label>
            <label><input type="radio" v-model="selectedPlotType" value="disco"> DISCO Score</label>
          </div>

          <!-- K-Selection Plots -->
          <KSelectionPlots
            :results="analysisResults"
            :selectedPlotType="selectedPlotType"
            @k-hovered="handleKHovered"
            @k-unhovered="handleKUnhovered"
            @k-clicked="handleKClicked"
          />

          <!-- Cluster Visualization Section -->
          <div ref="clusterVisualizationSection" class="cluster-visualization-section">
            <div class="section-header">
              <h3>Cluster Visualization</h3>
              <p>Interactive scatter plot showing clusters for the selected k value</p>
            </div>

            <!-- K Value Selector for Visualization -->
            <div class="k-selector">
              <label for="visualization-k-select">View clusters for k = </label>
              <select
                id="visualization-k-select"
                v-model="selectedVisualizationK"
                @change="updateClusterVisualization"
                class="form-select inline-select"
              >
                <option v-for="k in analysisResults.k_values" :key="k" :value="k">
                  {{ k }}
                </option>
              </select>

              <button
                v-if="suggestedK"
                @click="selectSuggestedK"
                class="btn btn-suggestion"
              >
                Use Suggested k={{ suggestedK }}
              </button>
            </div>

            <!-- Cluster Scatter Plot Loading State -->
            <div v-if="isLoadingVisualization" class="visualization-loading-state">
              <div class="loading-spinner"></div>
              <p>Loading k={{ selectedVisualizationK }} clustering visualization...</p>
              <div v-if="isLoadingVisualization" class="loading-progress">
                <p class="loading-hint">
                  🚀 Using fast PCA visualization - UMAP & t-SNE computing in background and will be shared across all k-values
                </p>
              </div>
            </div>

            <!-- Cluster Scatter Plot -->
            <div v-else-if="clusterVisualizationData" class="cluster-plot-container">
                          <div class="plot-wrapper">
              <div class="plot-inner">
                <ClusterScatterPlot
                  :data="clusterVisualizationData"
                  :width="900"
                  :height="600"
                  :selectedXAxis="selectedXAxis"
                  :selectedYAxis="selectedYAxis"
                  :colorMap="clusterVisualizationData.color_map"
                  :scatterColors="clusterVisualizationData.scatter_colors"
                  :datasetName="datasetNameForImages"
                  :featureNames="globalState.currentDataset.value?.headers || []"
                />
              </div>
            </div>

              <!-- Axis Controls -->
              <div class="axis-controls">
                <div class="axis-control">
                  <label>X-Axis:</label>
                  <select v-model="selectedXAxis" class="form-select">
                    <option v-for="axis in availableAxes" :key="axis.value" :value="axis.value">
                      {{ axis.label }}{{ axis.loading ? ' ⏳' : '' }}
                    </option>
                  </select>
                </div>
                <div class="axis-control">
                  <label>Y-Axis:</label>
                  <select v-model="selectedYAxis" class="form-select">
                    <option v-for="axis in availableAxes" :key="axis.value" :value="axis.value">
                      {{ axis.label }}{{ axis.loading ? ' ⏳' : '' }}
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Metrics Summary -->
            <div v-if="currentClusterMetrics" class="metrics-summary">
              <h4>Clustering Metrics for k={{ selectedVisualizationK }}</h4>
              <div class="metrics-grid">
                <div class="metric-card" v-if="currentClusterMetrics.silhouette !== null"
                     v-tooltip="{ key: 'metrics.silhouette' }">
                  <div class="metric-value">{{ formatMetric(currentClusterMetrics.silhouette) }}</div>
                  <div class="metric-label">Silhouette Score</div>
                  <div class="metric-quality" :class="getQualityClass(currentClusterMetrics.silhouette, 'silhouette')">
                    {{ getQualityText(currentClusterMetrics.silhouette, 'silhouette') }}
                  </div>
                </div>
                <div class="metric-card" v-if="currentClusterMetrics.davies_bouldin !== null"
                     v-tooltip="{ key: 'metrics.daviesBouldin' }">
                  <div class="metric-value">{{ formatMetric(currentClusterMetrics.davies_bouldin) }}</div>
                  <div class="metric-label">Davies-Bouldin Index</div>
                  <div class="metric-quality" :class="getQualityClass(currentClusterMetrics.davies_bouldin, 'db')">
                    {{ getQualityText(currentClusterMetrics.davies_bouldin, 'db') }}
                  </div>
                </div>
                <div class="metric-card" v-if="currentClusterMetrics.calinski_harabasz !== null"
                     v-tooltip="{ key: 'metrics.calinskiHarabasz' }">
                  <div class="metric-value">{{ formatMetric(currentClusterMetrics.calinski_harabasz) }}</div>
                  <div class="metric-label">Calinski-Harabasz Index</div>
                  <div class="metric-quality" :class="getQualityClass(currentClusterMetrics.calinski_harabasz, 'calinski')">
                    {{ getQualityText(currentClusterMetrics.calinski_harabasz, 'calinski') }}
                  </div>
                </div>
                <div class="metric-card" v-if="currentClusterMetrics.wcss !== null">
                  <div class="metric-value">{{ formatMetric(currentClusterMetrics.wcss) }}</div>
                  <div class="metric-label">WCSS</div>
                  <div class="metric-description">Within-cluster sum of squares</div>
                </div>
                <div class="metric-card" v-if="currentClusterMetrics.disco !== null"
                     v-tooltip="{ key: 'metrics.disco' }">
                  <div class="metric-value">{{ formatMetric(currentClusterMetrics.disco) }}</div>
                  <div class="metric-label">DISCO Score</div>
                  <div class="metric-quality" :class="getQualityClass(currentClusterMetrics.disco, 'disco')">
                    {{ getQualityText(currentClusterMetrics.disco, 'disco') }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Loading State -->
        <LoadingBar
          v-if="isLoading"
          :isLoading="isLoading"
          message="Analyzing different k values..."
          :onAbort="abortAnalysis"
        />

        <!-- Empty State -->
        <div v-if="!analysisResults && !isLoading" class="empty-state">
          <h3>Ready for K-Selection Analysis</h3>
          <p>Configure your parameters above and click "Run K-Selection Analysis" to get started.</p>
        </div>
      </div>
    </template>
  </AppLayout>

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

  <!-- Onboarding Wizard -->
  <Suspense v-if="showOnboardingWizard">
    <template #default>
      <OnboardingWizard
        :startFresh="true"
        @close="showOnboardingWizard = false"
        @finish="handleOnboardingFinish"
      />
    </template>
    <template #fallback>
      <div class="wizard-loading-overlay">
        <div class="wizard-loading-spinner"></div>
        <p>Loading onboarding...</p>
      </div>
    </template>
  </Suspense>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick, defineAsyncComponent } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import * as d3 from 'd3'
import { useGlobalState } from '~/composables/useGlobalState'
import { useStudySession } from '~/composables/useStudySession'
import { useFileUploadAPI } from '~/composables/useFileUploadAPI'
import { useTooltipManager } from '~/composables/useTooltipManager'
import { useToast } from '~/composables/useToast'
import { useBackgroundKSelection } from '~/composables/useBackgroundKSelection'
import AppLayout from '~/components/AppLayout.vue';
import SharedSidebar from '~/components/SharedSidebar.vue'
import KSelectionPlots from '~/components/KSelectionPlots.vue'
import LoadingBar from '~/components/LoadingBar.vue'
import TooltipComponent from '~/components/TooltipComponent.vue'

// Lazy load onboarding wizard
const OnboardingWizard = defineAsyncComponent(() => import('~/components/onboarding/OnboardingWizard.vue'));
import ClusterScatterPlot from '~/components/ClusterScatterPlot.vue'

// Interfaces
interface KSelectionResults {
  k_values: number[]
  metrics: {
    wcss: (number | null)[]
    silhouette: (number | null)[]
    davies_bouldin: (number | null)[]
    calinski_harabasz: (number | null)[]
    elbow_scores: (number | null)[]
    disco: (number | null)[]
  }
  optimal_k_suggestions: Record<string, number>
  cluster_results: Array<{
    k: number
    labels: number[]
    n_clusters: number
  }>
  data_points: number[][]
  high_dimensional_dataset?: boolean
  original_feature_count?: number
  show_only_dr_methods?: boolean
  pca_components?: number[][] | null
  data_cache_id?: string | null
  dr_cluster_id?: string | null
  dr_status?: 'started' | 'failed' | null
  umap_components?: number[][] | null
  tsne_components?: number[][] | null
}

interface ClusterData {
  points: number[][]
  labels: number[]
  centers?: number[][]
  color_map?: Record<string, string>
  scatter_colors?: string[]
  dimensionality_reduction?: {
    pca: number[][] | null
    umap: number[][] | null
    tsne: number[][] | null
  }
  evaluation_metrics?: {
    silhouette_score?: number
    db_index?: number
    calinski_harabasz?: number
    disco_score?: number
  }
  high_dimensional_dataset?: boolean
  original_feature_count?: number
  show_only_dr_methods?: boolean
}

// Initialize global state and router
const globalState = useGlobalState()
const studySession = useStudySession()
const fileUploadAPI = useFileUploadAPI()
const router = useRouter()
const route = useRoute()
const tooltipManager = useTooltipManager()
const { addToast } = useToast()
const backgroundKSelection = useBackgroundKSelection()

// Register callbacks for background k-selection completion while component is mounted
const unregisterComplete = backgroundKSelection.onComplete((results) => {
  console.log('[K-Selection] Background operation completed while mounted - applying results')
  isLoading.value = false
  currentAnalysisOperationId.value = null
  handleAnalysisComplete(results)
})
const unregisterError = backgroundKSelection.onError((errorMsg) => {
  console.log('[K-Selection] Background operation failed while mounted:', errorMsg)
  isLoading.value = false
  currentAnalysisOperationId.value = null
  alert(`K-Selection analysis failed: ${errorMsg}`)
})

// Clean up callbacks on unmount
onUnmounted(() => {
  unregisterComplete()
  unregisterError()
})

// Enhanced dimensionality reduction state with cluster tracking
const isLoadingDR = ref(false)
const currentClusterId = ref<string | null>(null)
let drPollingInterval: NodeJS.Timeout | null = null

// Global DR state - shared across all k values
const globalDRState = ref<{
  isComputing: boolean
  isCompleted: boolean
  clusterId: string | null
  umap: number[][] | null
  tsne: number[][] | null
  datasetId: string | null  // Track which dataset this DR computation is for
}>({
  isComputing: false,
  isCompleted: false,
  clusterId: null,
  umap: null,
  tsne: null,
  datasetId: null
})

// Modern state management with operation tracking
const isLoading = ref(false)
const isLoadingVisualization = ref(false)

// Template references
const clusterVisualizationSection = ref<HTMLElement | null>(null)

// Enhanced abort controllers with operation ID tracking
const analysisAbortController = ref<AbortController | null>(null)
const visualizationAbortController = ref<AbortController | null>(null)
const currentAnalysisOperationId = ref<string | null>(null)
const currentVisualizationOperationId = ref<string | null>(null)

// Enhanced abort function for async k-selection operations with backend process termination
const abortAnalysis = async () => {
  console.log('[K-Selection] Abort requested by user')

  // Abort via background composable (handles backend abort + polling cancellation)
  await backgroundKSelection.abortOperation()

  // Frontend abort - cancel any ongoing fetch requests
  if (analysisAbortController.value) {
    analysisAbortController.value.abort()
    analysisAbortController.value = null
    console.log('[K-Selection] Frontend request aborted')
  }

  // Clean up DR polling as well
  if (drPollingInterval) {
    clearInterval(drPollingInterval);
    drPollingInterval = null;
    isLoadingDR.value = false;
    console.log('[K-Selection] Stopped DR polling due to abort')
  }

  // Clean up global DR state
  globalDRState.value = { isComputing: false, isCompleted: false, clusterId: null, umap: null, tsne: null, datasetId: null }

  // Clean up state immediately
  isLoading.value = false
  currentAnalysisOperationId.value = null
  console.log('[K-Selection] Analysis operation aborted by user - all cleanup completed')
}

const abortVisualization = async () => {
  // Backend abort for visualization operations
  if (currentVisualizationOperationId.value) {
    try {
      await $fetch(`/api/abort/${currentVisualizationOperationId.value}`, {
        method: 'POST'
      })
      console.log('[K-Selection] Backend visualization process abort requested')
    } catch (error) {
      console.error('[K-Selection] Failed to abort backend visualization process:', error)
    }
  }
  
  // Frontend abort
  if (visualizationAbortController.value) {
    visualizationAbortController.value.abort()
    visualizationAbortController.value = null
  }
  
  // Clean up state
  isLoadingVisualization.value = false
  currentVisualizationOperationId.value = null
  console.log('[K-Selection] Visualization operation aborted by user')
}
const analysisResults = ref<KSelectionResults | null>(null)
const selectedVisualizationK = ref(3)

// Performance monitoring for large datasets
const performanceMetrics = ref({
  analysisTime: 0,
  renderingTime: 0,
  memoryUsage: 0,
  dataSize: 0,
  lastUpdate: null as Date | null
})

const trackAnalysisTime = (startTime: number) => {
  const duration = performance.now() - startTime
  performanceMetrics.value.analysisTime = duration
  console.log(`[K-Selection] Analysis completed in ${duration.toFixed(2)}ms`)
}

const trackMemoryUsage = () => {
  if (typeof window !== 'undefined' && (performance as any).memory) {
    const memoryInfo = (performance as any).memory
    performanceMetrics.value.memoryUsage = memoryInfo.usedJSHeapSize / 1024 / 1024 // MB
    performanceMetrics.value.lastUpdate = new Date()
  }
}

// Onboarding wizard state and functions
const showOnboardingWizard = ref(false)

const startOnboarding = () => {
  showOnboardingWizard.value = true
}

const handleOnboardingFinish = (onboardingState: any) => {
  showOnboardingWizard.value = false

  // Use nextTick to ensure DOM updates before navigation
  nextTick(async () => {
    // Set global state from onboarding wizard
    if (onboardingState.data.type === 'sample') {
      const sampleName = onboardingState.data.value;
      // Get dimensions from global state sampleOptions instead of hardcoded mapping
      const sampleOption = globalState.sampleOptions.value.find(opt => opt.value === sampleName);
      const dimensions = sampleOption?.dimensions || 2;
      const headers = Array.from({ length: dimensions }, (_, i) => `Feature ${i + 1}`);
      
      globalState.setDataset({
        name: onboardingState.data.name,
        type: 'sample',
        sampleName: onboardingState.data.value,
        n_samples: onboardingState.data.n_samples,
        headers,
        featureCount: dimensions
      });

    } else if (onboardingState.data.type === 'upload') {
      // Set uploaded data in global state
      globalState.setDataset({
        name: onboardingState.data.name,
        type: 'uploaded',
        data: onboardingState.data.parsedData,
        headers: onboardingState.data.headers,
        pointCount: onboardingState.data.rowCount,
        featureCount: onboardingState.data.columnCount,
        hasHeaders: onboardingState.data.hasHeaders,
        missingValueStrategy: onboardingState.data.missingValueStrategy,
        normalization: onboardingState.data.normalization
      });
    }

    // Set clustering parameters
    globalState.setClusteringParameters({
      treeType: onboardingState.parameters.treeType,
      partitionMethod: onboardingState.parameters.partitionMethod,
      power: onboardingState.parameters.power,
      selectedK: onboardingState.parameters.k
    });

    // Mark onboarding as completed
    globalState.setOnboardingCompleted(true);

    console.log('Onboarding completed, data and parameters set');
  });
}
const clusterVisualizationData = ref<ClusterData | null>(null)
const suggestedK = ref<number | null>(null)
const selectedOptimalK = ref<number | null>(null)
const kRangeStart = ref(2)
const kRangeEnd = ref(10)

// Cache for cluster visualization data to avoid redundant API calls
const clusterDataCache = ref<Map<number, ClusterData>>(new Map())

// Plot visibility states
const selectedPlotType = ref('elbow') // Default to Elbow plot

// Clustering parameters - initialize from global state if available
const initializeClusterParams = () => {
  const savedParams = globalState.clusteringParameters.value
  return {
    treeType: savedParams?.treeType || 'DCTree',
    power: savedParams?.power || 2.0
  }
}

const clusterParams = reactive(initializeClusterParams())

// Available options
const availableTreeTypes = ref<string[]>([])

// Axis selection for scatter plot - default to PCA as first choice
const selectedXAxis = ref('pca-0')
const selectedYAxis = ref('pca-1')

// Computed properties
const sampleOptions = computed(() => {
  return globalState.sampleOptions.value.map(opt => ({ 
    label: opt.label, 
    value: opt.value 
  }))
})

const kRange = computed(() => {
  const range = []
  for (let k = kRangeStart.value; k <= kRangeEnd.value; k++) {
    range.push(k)
  }
  return range
})

const availableAxes = computed(() => {
  if (!analysisResults.value) return []

  const axes = []
  
  // Get the original feature count from analysis results
  const numFeatures = analysisResults.value.data_points?.[0]?.length || 0
  const originalFeatureCount = analysisResults.value.original_feature_count || numFeatures || 0
  const showOnlyDRMethods = analysisResults.value.show_only_dr_methods || false
  const isHighDimensional = analysisResults.value.high_dimensional_dataset || false
  
  // Debug logging to understand the issue
  console.log(`[K-Selection] Debug - originalFeatureCount: ${originalFeatureCount}, numFeatures: ${numFeatures}, isHighDimensional: ${isHighDimensional}, showOnlyDRMethods: ${showOnlyDRMethods}`)
  console.log(`[K-Selection] Debug - analysisResults.original_feature_count:`, analysisResults.value.original_feature_count)
  
  // Get feature names from global state headers
  const headers = globalState.currentDataset.value?.headers || []

  // ALWAYS add PCA axes first - PCA is computed directly during analysis
  if (analysisResults.value.pca_components && analysisResults.value.pca_components.length > 0) {
    axes.push(
      { value: 'pca-0', label: 'PCA Component 1', loading: false },
      { value: 'pca-1', label: 'PCA Component 2', loading: false }
    )
  } else if (showOnlyDRMethods) {
    // For high-dimensional datasets, if PCA is missing, show it as loading
    // This should be rare due to backend improvements, but provides better UX
    axes.push(
      { value: 'pca-0', label: 'PCA Component 1', loading: true },
      { value: 'pca-1', label: 'PCA Component 2', loading: true }
    )
    console.warn('[K-Selection] PCA components missing for high-dimensional dataset - showing loading state')
  }

  // Only add feature axes if we're NOT in "show only DR methods" mode
  if (!showOnlyDRMethods && numFeatures > 0) {
    // Add feature axes
    for (let i = 0; i < numFeatures; i++) {
      const featureName = headers[i] ? headers[i] : `Feature ${i + 1}`
      axes.push({
        value: `feature-${i}`,
        label: featureName,
        loading: false
      })
    }
  }

  // Only show UMAP and t-SNE if they are actually available or currently being computed
  // Check if UMAP/t-SNE are available from analysis results or global state
  const hasUmapFromAnalysis = !!analysisResults.value.umap_components
  const hasTsneFromAnalysis = !!analysisResults.value.tsne_components
  const hasUmapFromGlobal = globalDRState.value.umap !== null
  const hasTsneFromGlobal = globalDRState.value.tsne !== null
  
  const hasUmap = hasUmapFromAnalysis || hasUmapFromGlobal
  const hasTsne = hasTsneFromAnalysis || hasTsneFromGlobal
  const isComputingDR = globalDRState.value.isComputing
  
  // Only show UMAP axes if they exist OR are currently being computed
  if (hasUmap || isComputingDR) {
    const isLoadingUmap = !hasUmap && isComputingDR
    axes.push(
      { value: 'umap-0', label: 'UMAP Component 1', loading: isLoadingUmap },
      { value: 'umap-1', label: 'UMAP Component 2', loading: isLoadingUmap }
    )
  }

  // Only show t-SNE axes if they exist OR are currently being computed
  if (hasTsne || isComputingDR) {
    const isLoadingTsne = !hasTsne && isComputingDR
    axes.push(
      { value: 'tsne-0', label: 't-SNE Component 1', loading: isLoadingTsne },
      { value: 'tsne-1', label: 't-SNE Component 2', loading: isLoadingTsne }
    )
  }
  
  // Log the final decision
  if (hasUmap || hasTsne || isComputingDR) {
    console.log(`[K-Selection] DR axes shown for ${originalFeatureCount} features. UMAP ready: ${hasUmap} (analysis: ${hasUmapFromAnalysis}, global: ${hasUmapFromGlobal}), t-SNE ready: ${hasTsne} (analysis: ${hasTsneFromAnalysis}, global: ${hasTsneFromGlobal}), computing: ${isComputingDR}`)
  } else {
    console.log(`[K-Selection] No DR axes shown - no UMAP/t-SNE data available and not computing (${originalFeatureCount} features)`)
  }

  return axes
})

const currentClusterMetrics = computed(() => {
  if (!analysisResults.value || !analysisResults.value.k_values) return null

  const kIndex = analysisResults.value.k_values.indexOf(selectedVisualizationK.value)
  if (kIndex === -1) return null

  return {
    silhouette: analysisResults.value.metrics.silhouette[kIndex] ?? null,
    davies_bouldin: analysisResults.value.metrics.davies_bouldin[kIndex] ?? null,
    calinski_harabasz: analysisResults.value.metrics.calinski_harabasz[kIndex] ?? null,
    wcss: analysisResults.value.metrics.wcss[kIndex] ?? null,
    disco: analysisResults.value.metrics.disco[kIndex] ?? null
  }
})

// Get dataset name suitable for image API (sample name for sample datasets)
const datasetNameForImages = computed(() => {
  const currentDataset = globalState.currentDataset.value;
  if (currentDataset?.type === 'sample' && currentDataset.sampleName) {
    return currentDataset.sampleName;
  }
  return '';
})

// Redis cache status for debugging high-dimensional datasets
const redisCacheStatus = computed(() => {
  if (!analysisResults.value) return null;
  
  const isHighDimensional = analysisResults.value.high_dimensional_dataset || false;
  const originalFeatureCount = analysisResults.value.original_feature_count || 0;
  const hasCacheId = !!analysisResults.value.data_cache_id;
  const hasDataPoints = !!(analysisResults.value.data_points?.length);
  
  return {
    isHighDimensional,
    originalFeatureCount,
    hasCacheId,
    hasDataPoints,
    cacheId: analysisResults.value.data_cache_id || null,
    strategy: isHighDimensional ? 'Redis cache required' : 'Direct data available',
    needsRedis: isHighDimensional && !hasCacheId
  };
})

// Methods
const handleParameterChange = () => {
  // Update cluster parameters when sidebar controls change
  console.log('Parameters changed:', clusterParams)
  
  // Clear all caches when parameters change since cached results are no longer valid
  clusterDataCache.value.clear()
  globalDRCache.value = null // Also clear global DR cache
  globalDRState.value = { isComputing: false, isCompleted: false, clusterId: null, umap: null, tsne: null, datasetId: null }
  
  // Stop any ongoing DR polling
  if (drPollingInterval) {
    clearInterval(drPollingInterval);
    drPollingInterval = null;
    isLoadingDR.value = false;
  }
  
  console.log('Cleared all caches and stopped DR polling due to parameter change')
  console.log('Redis cache will be invalidated for new parameter combination')
  
  // Clear persisted results since parameters changed
  clearPersistedAnalysisResults()
  
  // If we have analysis results, update the current visualization with new parameters
  if (analysisResults.value) {
    updateClusterVisualization()
  }
}

const updateKRange = () => {
  if (kRangeStart.value > kRangeEnd.value) {
    kRangeEnd.value = kRangeStart.value
  }
}

const selectOptimalK = (k: number) => {
  selectedOptimalK.value = k
  selectedVisualizationK.value = k
  updateClusterVisualization()
}

const formatMethodName = (method: string): string => {
  const nameMap: Record<string, string> = {
    'elbow': 'Elbow Method',
    'silhouette': 'Silhouette Score',
    'davies_bouldin': 'Davies-Bouldin Index',
    'calinski_harabasz': 'Calinski-Harabasz Index',
    'disco': 'DISCO Score'
  }
  return nameMap[method] || method
}

// High-timeout polling system for k-selection analysis
const pollForAnalysisCompletion = async (operationId: string): Promise<KSelectionResults | null> => {
  const maxAttempts = 1200 // 20 minutes at 1-second intervals
  let attempts = 0
  let consecutiveErrors = 0
  const maxConsecutiveErrors = 5
  
  console.log(`[K-Selection] Starting high-timeout polling for operation ${operationId}`)
  
  while (attempts < maxAttempts && currentAnalysisOperationId.value === operationId) {
    try {
      console.log(`[K-Selection] Polling attempt ${attempts + 1}/${maxAttempts} for operation ${operationId}`)
      
      // Individual request timeout: 15 seconds
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 15000)
      
      const status = await $fetch(`/api/k-selection/status/${operationId}`, {
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      console.log(`[K-Selection] Status response:`, status)
      
      // Reset consecutive errors on successful response
      consecutiveErrors = 0
      
      if (status.status === 'completed') {
        console.log('[K-Selection] Analysis completed successfully, result received')
        return status.result
      } else if (status.status === 'failed') {
        console.error('[K-Selection] Analysis failed:', status.error)
        throw new Error(status.error || 'K-selection analysis failed')
      } else if (status.status === 'not_found') {
        console.error('[K-Selection] Analysis operation not found')
        throw new Error('K-selection analysis operation not found')
      } else if (status.status === 'running') {
        console.log(`[K-Selection] Analysis still running, elapsed: ${status.elapsed_time?.toFixed(2)}s`)
      } else {
        console.log(`[K-Selection] Unknown status: ${status.status}`)
      }
      
      // Dynamic polling intervals - start fast, then slow down for efficiency
      let pollInterval = 1000 // Start with 1 second
      if (attempts > 30) pollInterval = 2000 // After 30 seconds, poll every 2 seconds
      if (attempts > 120) pollInterval = 5000 // After 2 minutes, poll every 5 seconds
      
      await new Promise(resolve => setTimeout(resolve, pollInterval))
      attempts++
      
    } catch (error: any) {
      if (currentAnalysisOperationId.value !== operationId) {
        // Operation was aborted
        console.log('[K-Selection] Polling stopped due to abort')
        return null
      }
      
      consecutiveErrors++
      console.error(`[K-Selection] Polling error on attempt ${attempts + 1} (consecutive errors: ${consecutiveErrors}):`, error)
      
      // If too many consecutive errors, give up
      if (consecutiveErrors >= maxConsecutiveErrors) {
        console.error(`[K-Selection] Too many consecutive errors (${consecutiveErrors}), giving up`)
        throw new Error(`K-selection analysis failed after ${consecutiveErrors} consecutive errors. Last error: ${error.message}`)
      }
      
      // Exponential backoff for network errors: 2s → 4s → 8s → 10s (max)
      const errorWaitTime = Math.min(2000 * consecutiveErrors, 10000)
      console.log(`[K-Selection] Waiting ${errorWaitTime}ms before retry due to error`)
      await new Promise(resolve => setTimeout(resolve, errorWaitTime))
      attempts++
    }
  }
  
  // Timeout reached
  console.error('[K-Selection] Analysis polling timeout reached after', attempts, 'attempts')
  throw new Error(`K-selection analysis timed out after ${Math.floor(maxAttempts / 60)} minutes`)
}

// Helper function to validate and sanitize column configuration
const validateAndFixColumnConfig = (columnConfig: any[]): any[] => {
  if (!Array.isArray(columnConfig)) {
    console.warn('[K-Selection] columnConfig is not an array, using empty array');
    return [];
  }
  
  return columnConfig.filter((col, index) => {
    // Check if column object is valid
    if (!col || typeof col !== 'object') {
      console.warn(`[K-Selection] Invalid column config at index ${index}:`, col);
      return false;
    }
    
    // Ensure required properties exist
    const hasRequiredProps = col.name !== undefined && 
                            col.index !== undefined && 
                            col.data_type !== undefined &&
                            col.usage !== undefined;
    
    if (!hasRequiredProps) {
      console.warn(`[K-Selection] Column config missing required properties at index ${index}:`, col);
      return false;
    }
    
    // Ensure properties are the correct type
    if (typeof col.name !== 'string' || 
        typeof col.index !== 'number' || 
        typeof col.data_type !== 'string' || 
        typeof col.usage !== 'string') {
      console.warn(`[K-Selection] Column config has invalid property types at index ${index}:`, col);
      return false;
    }
    
    return true;
  }).map(col => ({
    name: String(col.name),
    index: Number(col.index),
    data_type: String(col.data_type),
    usage: String(col.usage),
    normalize: Boolean(col.normalize),
    is_categorical: Boolean(col.is_categorical)
  }));
};

const fetchUploadedFileData = async (fileId: string): Promise<number[][] | null> => {
  try {
    console.log('[fetchUploadedFileData] Attempting to fetch data for fileId:', fileId);
    
    // Get the current dataset to extract processing configuration
    const currentDataset = globalState.currentDataset.value;
    if (!currentDataset) {
      console.error('[fetchUploadedFileData] No current dataset available');
      return null;
    }
    
    // Validate and sanitize column configuration
    const validatedColumns = validateAndFixColumnConfig(currentDataset.columnConfig || []);
    console.log('[fetchUploadedFileData] Validated columns:', validatedColumns.length, 'valid columns out of', (currentDataset.columnConfig || []).length);
    
    // Build processing configuration from dataset info with validated columns
    const processingConfig = {
      missing_value_strategy: (currentDataset.missingValueStrategy as 'keep' | 'remove' | 'fill_mean' | 'fill_median' | 'fill_zero' | 'fill_mode') || 'keep',
      normalization: (currentDataset.normalization as 'none' | 'standard' | 'minmax' | 'robust') || 'none',
      categorical_encoding: 'none' as const,
      feature_columns: Array.from(currentDataset.featureColumns || []),
      label_columns: Array.from(currentDataset.labelColumns || []),
      ignored_columns: [],
      columns: validatedColumns
    };
    
    console.log('[fetchUploadedFileData] Using processing config:', processingConfig);
    
    // Call the processData API to get the processed data
    const response = await fileUploadAPI.processData(fileId, processingConfig);
    
    if (response && response.data) {
      console.log('[fetchUploadedFileData] Successfully fetched data:', response.data.length, 'rows');
      return response.data;
    } else {
      console.error('[fetchUploadedFileData] No data in response');
      return null;
    }
  } catch (error) {
    console.error('[fetchUploadedFileData] Error fetching file data:', error);
    
    // Check if this is a column configuration error and try with simplified config
    if (error instanceof Error && (error.message.includes('column') || error.message.includes('422'))) {
      console.warn('[fetchUploadedFileData] Column configuration error detected, retrying with simplified config...');
      
      try {
        // Fallback: Try with minimal configuration
        const fallbackConfig = {
          missing_value_strategy: 'keep' as const,
          normalization: 'none' as const,
          categorical_encoding: 'none' as const,
          feature_columns: [],
          label_columns: [],
          ignored_columns: [],
          columns: []
        };
        
        console.log('[fetchUploadedFileData] Retrying with fallback config:', fallbackConfig);
        const fallbackResponse = await fileUploadAPI.processData(fileId, fallbackConfig);
        
        if (fallbackResponse && fallbackResponse.data) {
          console.log('[fetchUploadedFileData] Successfully fetched data with fallback config:', fallbackResponse.data.length, 'rows');
          return fallbackResponse.data;
        }
      } catch (fallbackError) {
        console.error('[fetchUploadedFileData] Fallback configuration also failed:', fallbackError);
      }
    }
    
    return null;
  }
};

const runKSelectionAnalysis = async () => {
  if (!globalState.currentDataset.value) {
    alert('Please select and confirm a data source first.')
    return
  }
  
  // Validate dataset has valid data
  const dataset = globalState.currentDataset.value
  
  if (dataset.type === 'sample' && (!dataset.sampleName && !dataset.name)) {
    alert('No sample dataset selected. Please select a sample dataset first.')
    return
  }
  
  if (dataset.type === 'imported' && (!dataset.data || dataset.data.length === 0)) {
    alert('No imported dataset data available. Please re-import the dataset.')
    return
  }

  // Warn if using BallTree/KDTree with high-dimensional data
  const featureCount = dataset.featureCount || 0
  const spatialTrees = ['BallTree', 'KDTree']
  if (spatialTrees.includes(clusterParams.treeType) && featureCount > 50) {
    addToast(
      `Warning: ${clusterParams.treeType} performs poorly with high-dimensional data (${featureCount} features). Consider using DCTree or CoverTree instead.`,
      'warning'
    )
  }

  isLoading.value = true
  analysisResults.value = null
  selectedOptimalK.value = null

  // Create abort controller and reset operation tracking
  analysisAbortController.value = new AbortController()
  currentAnalysisOperationId.value = null

  try {
    // Handle data preparation for uploaded files (CSV)
    let dataToUse: number[][] | null = null
    
    if (dataset.type === 'uploaded' || dataset.type === 'imported') {
      // First try to use existing data
      if (dataset.data && dataset.data.length > 0) {
        dataToUse = dataset.data
      } else if (dataset.fileId) {
        // If no data but we have a fileId, fetch the data
        console.log('[K-Selection] No data available, fetching using fileId:', dataset.fileId)
        const fetchedData = await fetchUploadedFileData(dataset.fileId)
        if (fetchedData && fetchedData.length > 0) {
          dataToUse = fetchedData
        } else {
          alert('Failed to load data from the uploaded file. Please try uploading the file again.')
          return
        }
      } else {
        alert('No data found in the uploaded dataset. Please upload a valid dataset first.')
        return
      }
    }

    // For sample datasets, prefer using the exact same points as the current clustering run.
    // IMPORTANT: for high-dimensional datasets the clustering backend returns a 2D PCA
    // projection in `points` (and nulls out `original_points`) to keep the response small.
    // Forwarding those projected points would make the k-selector cluster a 2D projection
    // while the clustering tab clusters the full-dimensional data — producing very different
    // (and misleadingly "cleaner") results. So only forward points when they are genuinely
    // in the original feature space; otherwise leave data null and let the backend
    // deterministically regenerate the identical full-dimensional sample (same random_state).
    if (dataset.type === 'sample') {
      const activeRun = globalState.activeRun.value
      const sameSample = activeRun && activeRun.parameters?.sample === (dataset.sampleName || dataset.name)
      const sameSize = !!(activeRun && activeRun.parameters?.n_samples === (dataset.n_samples || 200))
      if (sameSample && sameSize && activeRun.clusterData) {
        const runPoints = activeRun.clusterData.original_points || activeRun.clusterData.points
        const originalFeatureCount = activeRun.clusterData.original_feature_count
        const pointDims = Array.isArray(runPoints) && runPoints.length > 0 && Array.isArray(runPoints[0])
          ? runPoints[0].length
          : 0
        // Points are a projection if their dimensionality doesn't match the original features
        // (e.g. 2D PCA of a 365-feature dataset). Only forward full-dimensional points.
        const pointsAreFullDimensional = pointDims > 0 &&
          (!originalFeatureCount || pointDims === originalFeatureCount)
        if (pointsAreFullDimensional) {
          console.log('[K-Selection] Using full-dimensional points from active run to ensure identical dataset between pages')
          dataToUse = runPoints
        } else {
          console.log(`[K-Selection] Active run points are dimensionally reduced (${pointDims}D vs ${originalFeatureCount} features); letting backend regenerate full-dimensional sample for parity with the clustering tab`)
        }
      }
    }
    
    const requestData = {
      sample: dataset.type === 'sample' ? (dataset.sampleName || dataset.name) : 'blobs',
      n_samples: dataset.type === 'sample' ? (dataset.n_samples || 200) : (dataset.pointCount || 200),
      data: dataToUse, // when provided, backend should use these exact points
      treeType: clusterParams.treeType,
      power: clusterParams.power,
      k_range: kRange.value,
      random_state: 42,
      fileId: dataset.fileId || null,
      // DISCO metric processing included in batch (no separate requests)
      include_disco: true
    }
    
    console.log('[K-Selection] Starting analysis with modern polling pattern:', requestData)
    
    // Track performance for large datasets
    const analysisStartTime = performance.now()
    trackMemoryUsage()

    // Start analysis - returns immediately with operation ID
    const startResponse = await $fetch('/api/k-selection/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
      signal: analysisAbortController.value?.signal
    })

    console.log('K-selection API start response:', startResponse)
    
    // Handle both synchronous and asynchronous responses
    if (startResponse.operation_id) {
      // Asynchronous mode - use background polling (survives navigation)
      currentAnalysisOperationId.value = startResponse.operation_id
      console.log('[K-Selection] Received operation ID:', startResponse.operation_id)

      // Start background polling - this continues even if user navigates away
      backgroundKSelection.startOperation(startResponse.operation_id)

      // Don't clear isLoading here - it will be cleared when results arrive
      // via the onComplete callback or when the user navigates back
      return

    } else if (startResponse.k_values) {
      // Synchronous mode - results returned immediately
      console.log('[K-Selection] Received synchronous results immediately')
      
      // Validate results
      if (!startResponse.k_values || !Array.isArray(startResponse.k_values) || startResponse.k_values.length === 0) {
        console.error('K-Selection: Invalid response format:', startResponse)
        alert('K-Selection analysis returned invalid results. Please try again with different parameters.')
        return
      }
      
      // Validate critical components exist
      if (!startResponse.metrics || !startResponse.optimal_k_suggestions) {
        console.error('K-Selection: Missing critical analysis components:', startResponse)
        alert('K-Selection analysis incomplete. Some metrics may be missing.')
      }
      
      // Check for high-dimensional dataset issues
      if (startResponse.high_dimensional_dataset && !startResponse.pca_components) {
        console.warn('K-Selection: High-dimensional dataset missing PCA components')
      }
      
      if (startResponse.high_dimensional_dataset && !startResponse.data_cache_id) {
        console.warn('K-Selection: High-dimensional dataset missing cache ID - background processing may fail')
      }
      
      // Track analysis completion time
      trackAnalysisTime(analysisStartTime)

      handleAnalysisComplete(startResponse)

      // Clear loading for synchronous results
      isLoading.value = false
      analysisAbortController.value = null

    } else {
      // Neither operation_id nor results - invalid response
      console.error('K-Selection: Invalid API response - no operation_id or results:', startResponse)
      throw new Error('Invalid response from k-selection API - no operation ID or results received')
    }

  } catch (error: any) {
    console.error('Error running k-selection analysis:', error)

    // Check if the error is from abortion
    if (error.name === 'AbortError') {
      console.log('[K-Selection] Analysis was aborted by user')
      // Don't show alert for user-initiated abort
    } else {
      let userMessage = 'An unexpected error occurred during analysis.'

      if (error instanceof TypeError && error.message.includes('fetch')) {
        userMessage = 'Network error: Could not connect to the server. Please check your connection and try again.'
      } else if (error instanceof Error) {
        userMessage = `Analysis error: ${error.message}`
      }

      alert(`K-Selection analysis failed: ${userMessage}`)
    }
    // Only clear loading on error - for async operations, loading is managed by background composable
    isLoading.value = false
    analysisAbortController.value = null
    currentAnalysisOperationId.value = null
  }
}

// These handlers are no longer needed since we use global state
const handleFileProcessed = (fileData: any) => {
  // This is handled by the upload page and global state
  console.log('File processed event received, but using global state instead')
}

const handleDataSourceConfirmed = (dataSource: any) => {
  // This is handled by the upload page and global state
  console.log('Data source confirmed event received, but using global state instead')
}

// Performance optimized K-value interaction handlers
let lastKHoverTime = 0;
let kHoverTimeout: NodeJS.Timeout | null = null;
const K_HOVER_THROTTLE_MS = 100; // Throttle k-hover events more aggressively

const handleKHovered = (k: number) => {
  // Throttle hover events to reduce performance impact
  const now = performance.now();
  if (now - lastKHoverTime < K_HOVER_THROTTLE_MS) {
    if (kHoverTimeout) {
      clearTimeout(kHoverTimeout);
    }
    
    kHoverTimeout = setTimeout(() => {
      handleKHovered(k);
    }, K_HOVER_THROTTLE_MS);
    return;
  }
  
  lastKHoverTime = now;
  
  // Visual feedback only - no scatterplot update on hover for better performance
  // Could add subtle visual highlighting here in the future if needed
};

const handleKUnhovered = () => {
  // Cancel any pending hover processing
  if (kHoverTimeout) {
    clearTimeout(kHoverTimeout);
    kHoverTimeout = null;
  }
  
  // Clear hover visual feedback
};

const handleKClicked = (k: number) => {
  // Cancel any pending hover processing
  if (kHoverTimeout) {
    clearTimeout(kHoverTimeout);
    kHoverTimeout = null;
  }
  
  // Update scatterplot only on click for better UX
  selectedVisualizationK.value = k;
  
  // Scroll to cluster visualization section after k value update
  nextTick(() => {
    if (clusterVisualizationSection.value) {
      clusterVisualizationSection.value.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
};

// Handle loading a run from history
const handleRunLoaded = async (run: any) => {
  console.log('[K-Selection] handleRunLoaded called with run:', {
    id: run.id,
    dataset: run.dataset,
    treeType: run.treeType,
    partitionMethod: run.partitionMethod,
    selectedK: run.selectedK,
    selectedPower: run.selectedPower
  });
  
  try {
    // Restore the dataset state based on the run's parameters
    if (run.parameters.datasetInfo && (run.parameters.datasetInfo.type === 'uploaded' || run.parameters.datasetInfo.type === 'imported')) {
      const datasetInfoFromRun = run.parameters.datasetInfo;
      console.log('[K-Selection] Restoring uploaded/imported dataset from run:', datasetInfoFromRun.name);
      
      // Update global state with the dataset from the run
      globalState.setDataset({
        ...datasetInfoFromRun,
        // Ensure we have the fileId for potential backend operations
        fileId: run.parameters.fileId || datasetInfoFromRun.fileId,
        datasetId: run.parameters.datasetId || datasetInfoFromRun.datasetId // Restore datasetId
      });
      
    } else if (run.parameters.sample) {
      // Handle sample datasets or imported datasets
      console.log('[K-Selection] Restoring sample dataset from run:', run.parameters.sample);
      
      const sampleName = run.parameters.sample;
      // Get dimensions from global state sampleOptions instead of hardcoded mapping
      const sampleOption = globalState.sampleOptions.value.find(opt => opt.value === sampleName);
      
      if (sampleOption) {
        // Valid sample dataset
        const dimensions = sampleOption.dimensions;
        const headers = Array.from({ length: dimensions }, (_, i) => `Feature ${i + 1}`);
        
        globalState.setDataset({
          name: sampleOption.label,
          type: 'sample',
          sampleName: sampleName,
          n_samples: run.parameters.n_samples || sampleOption.typical_samples,
          headers,
          featureCount: dimensions
        });
      } else {
        // Likely an imported dataset - create imported dataset context
        console.log('[K-Selection] Sample not found, treating as imported dataset:', sampleName);
        
        // Try to get feature count from run data
        let featureCount = 2; // Default fallback
        if (run.clusterData?.points && run.clusterData.points.length > 0) {
          featureCount = run.clusterData.points[0].length;
        }
        
        const headers = Array.from({ length: featureCount }, (_, i) => `Feature_${i + 1}`);
        
        globalState.setDataset({
          name: sampleName,
          type: 'imported',
          data: run.clusterData?.points || [],
          fileName: sampleName,
          pointCount: run.clusterData?.points?.length || 0,
          featureCount: featureCount,
          headers: headers,
          fileId: run.parameters.fileId || `imported_${run.id}`
        });
      }
    }
    
    // Restore clustering parameters
    clusterParams.treeType = run.treeType;
    clusterParams.power = run.selectedPower;
    
    // Update global clustering parameters
    globalState.setClusteringParameters({
      treeType: run.treeType,
      partitionMethod: run.partitionMethod,
      power: run.selectedPower
    });
    
    // If the run has k-range information, restore it
    if (run.parameters.kRange) {
      kRangeStart.value = Math.min(...run.parameters.kRange);
      kRangeEnd.value = Math.max(...run.parameters.kRange);
      updateKRange();
    }
    
    console.log('[K-Selection] Successfully loaded run:', run.dataset);
    console.log('[K-Selection] Final parameters after loading:', {
      treeType: clusterParams.treeType,
      power: clusterParams.power,
      kRange: kRange.value
    });
    
  } catch (error) {
    console.error('[K-Selection] Error loading run:', error);
  }
};

const handleResetDataSource = () => {
  console.log('Data source reset')
  // Clear global state and redirect to onboarding
  globalState.clearDataset()
  analysisResults.value = null
  clusterVisualizationData.value = null
  
  // Clear cache when resetting data source
  clusterDataCache.value.clear()
  globalDRCache.value = null
  globalDRState.value = { isComputing: false, isCompleted: false, clusterId: null, umap: null, tsne: null, datasetId: null }
  console.log('Cleared cluster data cache, global DR cache, and global DR state due to data source reset')
  
  router.push('/')
}

const createDatasetSignature = (dataset: any) => {
  if (dataset.type === 'sample') {
    return `sample_${dataset.sampleName || dataset.name}_${dataset.n_samples || 200}`
  } else if (dataset.type === 'uploaded' || dataset.type === 'imported') {
    return `${dataset.type}_${dataset.fileName || dataset.name}_${dataset.pointCount || 0}_${dataset.featureCount || 0}`
  }
  return 'unknown'
}

const persistAnalysisResults = (results: KSelectionResults) => {
  try {
    localStorage.setItem('k-selection-results', JSON.stringify(results))
    localStorage.setItem('k-selection-timestamp', Date.now().toString())
    
    // Store dataset signature to validate results later
    if (globalState.currentDataset.value) {
      const signature = createDatasetSignature(globalState.currentDataset.value)
      localStorage.setItem('k-selection-dataset-signature', signature)
    }
  } catch (error) {
    console.warn('Failed to persist analysis results:', error)
  }
}

const loadPersistedAnalysisResults = (): KSelectionResults | null => {
  try {
    const results = localStorage.getItem('k-selection-results')
    const timestamp = localStorage.getItem('k-selection-timestamp')
    
    if (results && timestamp) {
      const age = Date.now() - parseInt(timestamp)
      // Only use persisted results if less than 1 hour old
      if (age < 60 * 60 * 1000) {
        return JSON.parse(results)
      }
    }
  } catch (error) {
    console.warn('Failed to load persisted analysis results:', error)
  }
  return null
}

const clearPersistedAnalysisResults = () => {
  try {
    localStorage.removeItem('k-selection-results')
    localStorage.removeItem('k-selection-timestamp')
    localStorage.removeItem('k-selection-dataset-signature')
  } catch (error) {
    console.warn('Failed to clear persisted analysis results:', error)
  }
}

const handleAnalysisComplete = (results: KSelectionResults) => {
  analysisResults.value = results
  
  if (results.k_values && results.k_values.length > 0) {
    selectedVisualizationK.value = results.k_values[0]
  } else {
    selectedVisualizationK.value = 3
    console.warn('No k_values in results, using default k=3')
  }
  
  // Log all k-values to study session
  results.k_values.forEach((kVal, idx) => {
    studySession.logParameterSet('k-selection', {
      treeType: clusterParams.treeType,
      power: clusterParams.power,
      k: kVal,
      k_range: kRange.value,
      sample: globalState.currentDataset.value?.sampleName,
      uploadedFileName: globalState.currentDataset.value?.fileName,
      fileId: globalState.currentDataset.value?.fileId
    }, {
      silhouetteScore: results.metrics.silhouette ? results.metrics.silhouette[idx] : undefined,
      dbIndex: results.metrics.davies_bouldin ? results.metrics.davies_bouldin[idx] : undefined,
      calinskiHarabasz: results.metrics.calinski_harabasz ? results.metrics.calinski_harabasz[idx] : undefined,
      discoScore: results.metrics.disco ? results.metrics.disco[idx] : undefined,
      ari: results.metrics.ari ? results.metrics.ari[idx] : undefined
    })
  })
  
  // Clear cache when new analysis is completed
  clusterDataCache.value.clear()
  globalDRCache.value = null
  globalDRState.value = { isComputing: false, isCompleted: false, clusterId: null, umap: null, tsne: null, datasetId: null }
  console.log('Cleared cluster data cache, global DR cache, and global DR state for new analysis')

  // Persist results to prevent disappearing on reload
  persistAnalysisResults(results)

  // Set suggested k from the most common suggestion
  const suggestions = Object.values(results.optimal_k_suggestions)
  if (suggestions.length > 0) {
    suggestedK.value = suggestions[0]
  }

  // Since PCA is now computed directly in analysis results, we don't need to fetch it separately
  // Start DR polling if we have a DR cluster_id from the analysis
  console.log('[K-Selection] PCA available from analysis results - no separate fetch needed')
  console.log('[K-Selection] Analysis complete - data_cache_id:', results.data_cache_id)
  console.log('[K-Selection] Analysis complete - high_dimensional_dataset:', results.high_dimensional_dataset)
  console.log('[K-Selection] Analysis complete - has data_points:', !!(results.data_points?.length))
  console.log('[K-Selection] Analysis complete - data_points length:', results.data_points?.length || 0)
  console.log('[K-Selection] Analysis complete - dr_cluster_id:', results.dr_cluster_id)
  
  // Start DR polling if cluster_id is available from analysis
  if (results.dr_cluster_id && results.dr_status === 'started') {
    console.log(`[K-Selection] Starting DR polling with cluster_id from analysis: ${results.dr_cluster_id}`)
    globalDRState.value.clusterId = results.dr_cluster_id
    globalDRState.value.isComputing = true
    globalDRState.value.datasetId = createDatasetId(globalState.currentDataset.value)
    startGlobalDimensionalityReductionPolling(results.dr_cluster_id)
  } else {
    console.log('[K-Selection] No DR cluster_id from analysis - UMAP/t-SNE will not be available')
  }
  
  updateClusterVisualization()
}

const selectSuggestedK = () => {
  if (suggestedK.value) {
    selectedVisualizationK.value = suggestedK.value
    updateClusterVisualization()
  }
}

// Background UMAP/t-SNE polling that updates all k-values at once
const startGlobalDimensionalityReductionPolling = (clusterId: string) => {
  // Prevent duplicate polling sessions
  if (drPollingInterval) {
    console.log('[K-Selection] Stopping existing background DR polling before starting new one');
    clearInterval(drPollingInterval);
    drPollingInterval = null;
  }
  
  // Early termination if global DR data already exists
  if (globalDRState.value.isCompleted && globalDRState.value.umap && globalDRState.value.tsne) {
    console.log('[K-Selection] Background DR data already available, skipping polling');
    globalDRState.value.isComputing = false;
    return;
  }
  
  // Validate cluster ID
  if (!clusterId || clusterId.trim() === '') {
    console.warn('[K-Selection] Invalid cluster ID provided for background DR polling:', clusterId);
    globalDRState.value.isComputing = false;
    return;
  }
  
  // Reset state properly
  currentClusterId.value = clusterId;
  
  // Start with 2-second delay to avoid blocking main UI
  setTimeout(() => {
    isLoadingDR.value = true;
    console.log(`[K-Selection] Starting background UMAP/t-SNE polling for cluster: ${clusterId}`);
    
    let pollAttempts = 0;
    const maxPollAttempts = 120; // 10 minutes at 5-second intervals (reasonable for background)
    let consecutiveErrors = 0;
    const maxConsecutiveErrors = 3; // Fail faster for better UX
    
    drPollingInterval = setInterval(async () => {
      try {
        // Stop polling if cluster ID changed (new analysis started)
        if (globalDRState.value.clusterId !== clusterId) {
          console.log('[K-Selection] Stopping background DR polling - cluster ID changed');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          globalDRState.value.isComputing = false;
          return;
        }
        
        // Early termination if global DR data already exists (prevents redundant polling)
        if (globalDRState.value.isCompleted && globalDRState.value.umap && globalDRState.value.tsne) {
          console.log('[K-Selection] Background DR data already complete, stopping polling');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          globalDRState.value.isComputing = false;
          return;
        }
        
        pollAttempts++;
        if (pollAttempts > maxPollAttempts) {
          console.warn('[K-Selection] Background UMAP/t-SNE polling timeout - stopping after', maxPollAttempts, 'attempts');
          console.warn('[K-Selection] UMAP/t-SNE will remain unavailable for this session');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          globalDRState.value.isComputing = false;
          return;
        }
        
        console.log(`[K-Selection] Background UMAP/t-SNE poll attempt ${pollAttempts}/${maxPollAttempts} for cluster ${clusterId}`);
        
        // Individual request timeout: 10 seconds 
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const statusData = await $fetch(`/api/cluster/${clusterId}/dimensionality-reduction/status`, {
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        console.log(`[K-Selection] Background UMAP/t-SNE status ${pollAttempts}/${maxPollAttempts}:`, statusData.status);
        
        // Reset consecutive errors on successful response
        consecutiveErrors = 0;
        
        if (statusData.status === 'completed') {
          // Get results with timeout
          const resultController = new AbortController();
          const resultTimeoutId = setTimeout(() => resultController.abort(), 10000);
          
          const resultData = await $fetch(`/api/cluster/${clusterId}/dimensionality-reduction/result`, {
            signal: resultController.signal
          });
          
          clearTimeout(resultTimeoutId);
          console.log(`[K-Selection] Background UMAP/t-SNE results received:`, {
            hasUmap: !!resultData.umap,
            hasTsne: !!resultData.tsne,
            umapStatus: resultData.umap_status,
            tsneStatus: resultData.tsne_status
          });
          
          if (resultData && !resultData.error) {
            // Update global DR state
            if (resultData.umap && resultData.umap_status === 'completed') {
              globalDRState.value.umap = resultData.umap;
              console.log('[K-Selection] ✅ UMAP computation completed');
            }
            if (resultData.tsne && resultData.tsne_status === 'completed') {
              globalDRState.value.tsne = resultData.tsne;
              console.log('[K-Selection] ✅ t-SNE computation completed');
            }
            
            // Update all cached k values with new DR data (batch update)
            await nextTick();
            clusterDataCache.value.forEach((cachedData, cachedK) => {
              if (cachedData.dimensionality_reduction) {
                if (globalDRState.value.umap) {
                  cachedData.dimensionality_reduction.umap = globalDRState.value.umap;
                }
                if (globalDRState.value.tsne) {
                  cachedData.dimensionality_reduction.tsne = globalDRState.value.tsne;
                }
              }
            });
            
            // Update current visualization if visible
            if (clusterVisualizationData.value?.dimensionality_reduction) {
              let updated = false;
              if (globalDRState.value.umap) {
                clusterVisualizationData.value.dimensionality_reduction.umap = globalDRState.value.umap;
                updated = true;
              }
              if (globalDRState.value.tsne) {
                clusterVisualizationData.value.dimensionality_reduction.tsne = globalDRState.value.tsne;
                updated = true;
              }
              
              if (updated) {
                // Trigger reactivity
                clusterVisualizationData.value = { ...clusterVisualizationData.value };
                console.log('[K-Selection] Updated current visualization with background UMAP/t-SNE');
              }
            }
            
            // Check if both UMAP and t-SNE are completed - only then stop polling
            if (globalDRState.value.umap && globalDRState.value.tsne) {
              globalDRState.value.isCompleted = true;
              globalDRState.value.isComputing = false;
              console.log('[K-Selection] 🎉 Background UMAP/t-SNE computation completed - stopping polling');
              
              // Stop polling - both tasks completed
              clearInterval(drPollingInterval!);
              drPollingInterval = null;
              isLoadingDR.value = false;
              return; // Exit the polling function
            } else {
              console.log(`[K-Selection] Partial DR results received - continuing polling (UMAP: ${!!globalDRState.value.umap}, t-SNE: ${!!globalDRState.value.tsne})`);
            }
          } else {
            console.log('[K-Selection] DR result fetch completed but no valid data received');
          }
          
          // Continue polling if we reach here (not both completed)
          
        } else if (statusData.status === 'failed') {
          console.error(`[K-Selection] Background UMAP/t-SNE failed for cluster ${clusterId}:`, statusData.error || 'Unknown error');
          
          // Show user-friendly error message
          let userMessage = 'Background UMAP/t-SNE computation failed';
          if (statusData.error && statusData.error.includes('Insufficient')) {
            userMessage = 'Dataset too small for UMAP/t-SNE computation. Only PCA is available.';
          } else if (statusData.error && statusData.error.includes('No data')) {
            userMessage = 'Data not available for UMAP/t-SNE computation.';
          }
          
          console.warn(`[K-Selection] ${userMessage}`);
          
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          globalDRState.value.isComputing = false;
          
        } else if (statusData.status === 'not_found') {
          console.warn(`[K-Selection] Background UMAP/t-SNE task not found - may have been cleaned up`);
          
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          globalDRState.value.isComputing = false;
          
        } else {
          // Continue polling if status is 'processing' or other intermediate status
          if (statusData.umap_status || statusData.tsne_status) {
            console.log(`[K-Selection] Background processing... UMAP: ${statusData.umap_status || 'pending'}, t-SNE: ${statusData.tsne_status || 'pending'}`);
          }
        }
        
      } catch (error: any) {
        consecutiveErrors++;
        console.error(`[K-Selection] DR polling error ${consecutiveErrors}/${maxConsecutiveErrors}:`, error.message);
        
        // Stop polling if too many consecutive errors
        if (consecutiveErrors >= maxConsecutiveErrors) {
          console.error('[K-Selection] Too many consecutive background UMAP/t-SNE polling errors - stopping');
          console.warn('[K-Selection] UMAP/t-SNE will remain unavailable for this session');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          globalDRState.value.isComputing = false;
        }
      }
    }, 5000); // Poll every 5 seconds
  }, 2000); // Initial 2-second delay
};

// Global dimensionality reduction cache - shared across all k values
const globalDRCache = ref<{
  pca: number[][] | null;
  umap: number[][] | null;
  tsne: number[][] | null;
  cluster_id?: string;
} | null>(null);

// Helper function to create a unique dataset identifier
const createDatasetId = (dataset: any): string => {
  if (!dataset) return 'unknown';
  
  if (dataset.type === 'sample') {
    return `sample_${dataset.sampleName || dataset.name}_${dataset.n_samples || 1000}`;
  } else if (dataset.type === 'uploaded') {
    return `uploaded_${dataset.fileId || dataset.fileName || dataset.name}_${dataset.pointCount || 0}`;
  }
  
  return `${dataset.type}_${dataset.name}`;
};


const updateClusterVisualization = async () => {
  if (!analysisResults.value) return

  const k = selectedVisualizationK.value;
  
  // Check cache first
  if (clusterDataCache.value.has(k)) {
    console.log(`[K-Selection] Using cached data for k=${k}`);
    clusterVisualizationData.value = clusterDataCache.value.get(k) || null;
    return;
  }

  // Find clustering labels for this k value from analysis results
  const clusterResult = analysisResults.value.cluster_results.find(result => result.k === k);
  if (!clusterResult) {
    console.error(`[K-Selection] No clustering result found for k=${k}`);
    return;
  }

  console.log(`[K-Selection] Building visualization for k=${k} using existing analysis results`);
  isLoadingVisualization.value = true;

  try {
    if (!analysisResults.value) {
      console.error('[K-Selection] Analysis results not available');
      return;
    }
    
    // Prefer backend-provided visualization so we get canonical colors
    const isHighDimensional = analysisResults.value.high_dimensional_dataset || false;
    const hasCacheId = !!(analysisResults.value as any).data_cache_id;
    const hasDataPoints = (analysisResults.value.data_points && analysisResults.value.data_points.length > 0);
    const reqBody: any = {
      n_clusters: k,
      treeType: clusterParams.treeType,
      power: clusterParams.power,
      random_state: 42,
      skip_umap: true,
      skip_tsne: true,
      data_cache_id: hasCacheId ? (analysisResults.value as any).data_cache_id : null,
      data: hasDataPoints ? analysisResults.value.data_points : null,
      sample: datasetNameForImages.value || undefined
    };

    
    let visResponse: any | null = null;
    try {
      const resp = await $fetch('/api/k-selection/cluster-visualization', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      if (resp.ok) {
        visResponse = await resp.json();
      } else {
        console.warn(`[K-Selection] cluster-visualization returned HTTP ${resp.status}`);
      }
    } catch (e) {
      console.warn('[K-Selection] cluster-visualization request failed, falling back to local build:', e);
    }

    let visualizationData: any;
    if (visResponse && !visResponse.error) {
      // Use backend result including canonical colors
      visualizationData = {
        points: visResponse.points || analysisResults.value.data_points || [],
        labels: visResponse.labels || clusterResult.labels,
        centers: visResponse.centers || [],
        dimensionality_reduction: visResponse.dimensionality_reduction || {
          pca: analysisResults.value.pca_components || null,
          umap: null,
          tsne: null
        },
        evaluation_metrics: visResponse.evaluation_metrics || {},
        high_dimensional_dataset: isHighDimensional,
        original_feature_count: analysisResults.value.original_feature_count || 0,
        show_only_dr_methods: analysisResults.value.show_only_dr_methods || false,
        color_map: visResponse.color_map || {},
        scatter_colors: visResponse.scatter_colors || []
      };
    } else {
      // Fallback to existing local build to avoid blank UI
      const kIndex = analysisResults.value.k_values.indexOf(k);
      visualizationData = {
        points: analysisResults.value.data_points,
        labels: clusterResult.labels,
        centers: [],
        dimensionality_reduction: {
          pca: analysisResults.value.pca_components || null,
          umap: null,
          tsne: null
        },
        evaluation_metrics: {
          silhouette_score: kIndex >= 0 ? analysisResults.value.metrics.silhouette[kIndex] || undefined : undefined,
          db_index: kIndex >= 0 ? analysisResults.value.metrics.davies_bouldin[kIndex] || undefined : undefined,
          calinski_harabasz: kIndex >= 0 ? analysisResults.value.metrics.calinski_harabasz[kIndex] || undefined : undefined,
          disco_score: kIndex >= 0 ? analysisResults.value.metrics.disco[kIndex] || undefined : undefined
        },
        high_dimensional_dataset: isHighDimensional,
        original_feature_count: analysisResults.value.original_feature_count || 0,
        show_only_dr_methods: analysisResults.value.show_only_dr_methods || false
      };
    }

    // If DR completed globally, plug it in
    if (globalDRState.value.umap) {
      visualizationData.dimensionality_reduction.umap = globalDRState.value.umap;
    }
    if (globalDRState.value.tsne) {
      visualizationData.dimensionality_reduction.tsne = globalDRState.value.tsne;
    }

    // Cache and set
    clusterDataCache.value.set(k, visualizationData);
    clusterVisualizationData.value = visualizationData;

  } catch (error) {
    console.error('Error updating cluster visualization:', error as Error)
  } finally {
    isLoadingVisualization.value = false
  }
}


const formatMetric = (value: number | null): string => {
  if (value === null || value === undefined) return 'N/A'
  if (value === Infinity || isNaN(value)) return '∞'
  return value.toFixed(3)
}

const loadClusterOptions = async () => {
  try {
    const options = await $fetch('/api/cluster/options')
    availableTreeTypes.value = options.treeTypes || []
  } catch (error) {
    console.error('Error loading cluster options:', error)
  }
}

// Auto-load active run data
const loadActiveRun = async () => {
  const activeRun = globalState.activeRun.value;
  if (activeRun) {
    console.log('[K-Selection] Auto-loading active run:', activeRun.dataset, 'ID:', activeRun.id);
    await handleRunLoaded(activeRun);
  } else {
    console.log('[K-Selection] No active run to load');
  }
};

// Lifecycle
onMounted(async () => {
  loadClusterOptions()
  
  // Check if we have a dataset, if not redirect to onboarding
  if (!globalState.currentDataset.value) {
    console.log('No dataset found, redirecting to onboarding')
    router.push('/')
    return
  }
  
  // Auto-load active run FIRST (if exists) to set parameters and dataset
  console.log('[K-Selection] Checking for active run on mount...');
  const activeRun = globalState.activeRun.value;
  const hasActiveRun = !!activeRun;
  
  if (hasActiveRun) {
    console.log('[K-Selection] Found active run on mount:', activeRun.dataset, 'ID:', activeRun.id);
    await loadActiveRun();
  } else {
    console.log('[K-Selection] No active run found on mount');
  }
  
  // Check if a background k-selection operation completed while we were away
  const backgroundResults = backgroundKSelection.consumeResults()
  if (backgroundResults) {
    console.log('[K-Selection] Found completed background results on mount - applying')
    handleAnalysisComplete(backgroundResults)
  } else if (backgroundKSelection.isRunning.value) {
    // Operation still in progress - show loading state and register callback
    console.log('[K-Selection] Background operation still running - reconnecting')
    isLoading.value = true
    currentAnalysisOperationId.value = backgroundKSelection.operationId.value
  } else {
    // Check for background errors
    const backgroundError = backgroundKSelection.consumeError()
    if (backgroundError) {
      console.log('[K-Selection] Background operation failed:', backgroundError)
      alert(`K-Selection analysis failed: ${backgroundError}`)
    }
  }

  // Only load persisted analysis results if no background operation is active
  if (!backgroundKSelection.isRunning.value && !backgroundResults) {
    const persistedResults = loadPersistedAnalysisResults()
    if (persistedResults && globalState.currentDataset.value) {
      // Only use persisted results if they match the current dataset
      const currentDatasetSignature = createDatasetSignature(globalState.currentDataset.value)
      const persistedDatasetSignature = localStorage.getItem('k-selection-dataset-signature')

      if (persistedDatasetSignature === currentDatasetSignature) {
        console.log('Loaded persisted analysis results matching current dataset')
        analysisResults.value = persistedResults
        selectedVisualizationK.value = persistedResults.k_values[0] || 3

        // Set suggested k from the most common suggestion
        const suggestions = Object.values(persistedResults.optimal_k_suggestions)
        if (suggestions.length > 0) {
          suggestedK.value = suggestions[0]
        }

        updateClusterVisualization()
      } else {
        console.log('Persisted analysis results do not match current dataset, clearing them')
        clearPersistedAnalysisResults()
      }
    }
  }
  
  // Sync clustering parameters with global state (already initialized above)
  const params = globalState.clusteringParameters.value
  if (params) {
    // Update parameters if they've changed since initialization
    if (params.treeType && params.treeType !== clusterParams.treeType) {
      clusterParams.treeType = params.treeType
    }
    if (params.power && params.power !== clusterParams.power) {
      clusterParams.power = params.power
    }
    console.log('Synced clustering parameters with global state:', params)
  }
  
  // Restore visualization preferences from global state (persisted across page navigations)
  const savedVizPrefs = globalState.visualizationPreferences.value;
  if (savedVizPrefs.selectedXAxis && savedVizPrefs.selectedYAxis) {
    selectedXAxis.value = savedVizPrefs.selectedXAxis;
    selectedYAxis.value = savedVizPrefs.selectedYAxis;
    console.log('[K-Selection] Restored axis selections from global state:', savedVizPrefs.selectedXAxis, savedVizPrefs.selectedYAxis);
  }
  if (savedVizPrefs.selectedPlotType) {
    selectedPlotType.value = savedVizPrefs.selectedPlotType;
    console.log('[K-Selection] Restored plot type from global state:', savedVizPrefs.selectedPlotType);
  }

  // Check for auto-start request from history
  if (route.query.autostart === 'true') {
    setTimeout(() => {
      console.log('[K-Selection] Auto-start requested via query parameter');
      runAnalysis();
    }, 500);
  }
})

// Watch for visualization k changes
watch(selectedVisualizationK, updateClusterVisualization)

// Watch for global DR state changes and update all cached visualizations
watch(() => globalDRState.value.isCompleted, (isCompleted) => {
  if (isCompleted && globalDRState.value.umap && globalDRState.value.tsne) {
    console.log('[K-Selection] 🎉 Background UMAP/t-SNE completed - updating all cached visualizations');
    
    // Update all cached k values with new DR data
    clusterDataCache.value.forEach((cachedData, cachedK) => {
      if (cachedData.dimensionality_reduction) {
        cachedData.dimensionality_reduction.umap = globalDRState.value.umap;
        cachedData.dimensionality_reduction.tsne = globalDRState.value.tsne;
      }
    });
    
    // Update current visualization if visible
    if (clusterVisualizationData.value?.dimensionality_reduction) {
      clusterVisualizationData.value.dimensionality_reduction.umap = globalDRState.value.umap;
      clusterVisualizationData.value.dimensionality_reduction.tsne = globalDRState.value.tsne;
      // Trigger reactivity
      clusterVisualizationData.value = { ...clusterVisualizationData.value };
      console.log('[K-Selection] ✅ Current visualization updated with background UMAP/t-SNE');
    }
    
    // Auto-switch axis selection to t-SNE when it becomes available
    // This fixes the issue where axis labels show "PCA Component" while t-SNE data is displayed
    if (globalDRState.value.tsne && selectedXAxis.value.startsWith('pca-')) {
      console.log('[K-Selection] Auto-switching axes from PCA to t-SNE (t-SNE now available)');
      selectedXAxis.value = 'tsne-0';
      selectedYAxis.value = 'tsne-1';
    }
  }
})

// Watch for analysis results changes and auto-set to PCA when available
watch(analysisResults, (newResults) => {
  if (newResults?.pca_components) {
    // Always prefer PCA when it becomes available from analysis results
    console.log('[K-Selection] Auto-setting axes to PCA (PCA computed in analysis)')
    selectedXAxis.value = 'pca-0'
    selectedYAxis.value = 'pca-1'
  } else if (newResults && !newResults.pca_components) {
    // If PCA isn't available, fallback to features temporarily (for low-dimensional datasets)
    const numFeatures = newResults.data_points?.[0]?.length || 0
    const showOnlyDRMethods = newResults.show_only_dr_methods || false
    const isHighDimensional = newResults.high_dimensional_dataset || false
    
    if (!showOnlyDRMethods && numFeatures > 0) {
      console.log('[K-Selection] PCA not ready, using feature axes temporarily')
      selectedXAxis.value = 'feature-0'
      selectedYAxis.value = 'feature-1'
    } else if (isHighDimensional) {
      console.warn('[K-Selection] High-dimensional dataset without PCA - no visualization axes available!')
      // For high-dimensional datasets, we must wait for PCA or show error
      selectedXAxis.value = 'pca-0'  // Set anyway, will show loading
      selectedYAxis.value = 'pca-1'
    }
  }
}, { immediate: false })

// Watch for parameter changes and save to global state for persistence
watch(() => [clusterParams.treeType, clusterParams.power], 
  ([newTreeType, newPower]) => {
    // Update global parameters when they change on this page
    const currentGlobalParams = globalState.clusteringParameters.value || {};
    const updatedParams = {
      ...currentGlobalParams,
      treeType: newTreeType,
      power: newPower
    };
    
    // Only update if parameters have actually changed
    if (currentGlobalParams.treeType !== newTreeType || 
        currentGlobalParams.power !== newPower) {
      
      console.log('[K-Selection] Saving parameters to global state:', updatedParams);
      globalState.setClusteringParameters(updatedParams);
    }
  }, 
  { deep: false }
)

// Watch for changes to the active run and auto-load
watch(() => globalState.activeRun.value, async (newActiveRun, oldActiveRun) => {
  // Only process if the run actually changed
  if (newActiveRun?.id === oldActiveRun?.id) {
    return
  }
  
  console.log('[K-Selection] Active run changed from', oldActiveRun?.dataset, 'to', newActiveRun?.dataset);
  
  if (newActiveRun && !isLoading.value) {
    console.log('[K-Selection] Loading new active run:', newActiveRun.dataset, 'ID:', newActiveRun.id);
    await handleRunLoaded(newActiveRun);
  } else if (!newActiveRun) {
    console.log('[K-Selection] No active run - cleared');
  }
}, { immediate: false })

// Enhanced cleanup on component unmount
onUnmounted(() => {
  // Clear DR polling intervals (these are UI-only, not the main analysis)
  if (drPollingInterval) {
    clearInterval(drPollingInterval);
    drPollingInterval = null;
    console.log('[K-Selection] Cleared DR polling on unmount');
  }

  // Reset DR-related state
  currentClusterId.value = null;
  isLoadingDR.value = false;

  // Do NOT abort the k-selection analysis - let it continue in the background
  // so the user can navigate to other tabs and come back to see results
  if (backgroundKSelection.isRunning.value) {
    console.log('[K-Selection] Analysis still running - will continue in background')
  }

  // Abort visualization operations (these are less important)
  if (currentVisualizationOperationId.value) {
    abortVisualization()
  }

  // Save visualization preferences to global state for persistence across page navigations
  globalState.setVisualizationPreferences({
    selectedXAxis: selectedXAxis.value,
    selectedYAxis: selectedYAxis.value,
    selectedPlotType: selectedPlotType.value,
  });

  // Clear caches and large data references to free memory
  clusterDataCache.value.clear();
  globalDRCache.value = null;
  globalDRState.value = { isComputing: false, isCompleted: false, clusterId: null, umap: null, tsne: null, datasetId: null };
  clusterVisualizationData.value = null;
  // Don't clear analysisResults - keep them if available

  console.log('[K-Selection] Cleanup completed - analysis continues in background if running')
})

// Quality rating functions (similar to clustering-explorer.vue)
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

// Set page title
useHead({
  title: 'K-Selection Analysis | Clustering Workflow'
})
</script>

<style scoped>
@import '~/assets/css/pages/k-selection.css';
</style>

