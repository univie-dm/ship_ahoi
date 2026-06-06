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
        @file-upload="handleFileUpload"
        @update:selectedSample="handleSampleChange"
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

        <!-- Dataset Controls -->
        <template #page-controls>
          <div class="control-section">
            <h3 class="section-title">Dataset Configuration</h3>
            <div class="info-box">
              Explore dataset properties, column statistics, and data quality metrics.
            </div>
            
            <div v-if="availableFeatures.length > 0" class="feature-selection">
              <h4>Feature Analysis</h4>
              <div v-if="availableFeatures.length > 20" class="info-box small">
                Note: For optimal visualization performance, only the first 20 features are selected by default. You can manually select/deselect specific features below.
              </div>
              <div class="feature-list">
                <label class="feature-item" v-for="(feature, index) in availableFeatures" :key="feature">
                  <input
                    type="checkbox"
                    :value="index"
                    v-model="selectedFeatures"
                    @change="updateFeatureSelection"
                  />
                  <span>{{ feature }}</span>
                </label>
              </div>
              
              <div class="feature-actions">
                <button @click="selectAllFeatures" class="feature-btn">
                  {{ availableFeatures.length > 20 ? 'Select First 20' : 'Select All' }}
                </button>
                <button @click="clearAllFeatures" class="feature-btn">Clear All</button>
              </div>
            </div>


            
          </div>
        </template>
      </SharedSidebar>
    </template>    
    
    <template #default>
      <div class="data-explorer-content">
        <div class="page-header">
          <h1>Dataset Explorer</h1>
          <p>Comprehensive analysis of dataset properties, statistics, and data quality</p>
        </div>

        <!-- Dataset Overview -->
        <div class="overview-section">
          <h2>Dataset Overview</h2>
          <div class="overview-cards">
            <div class="card">
              <div class="card-title">Data Points</div>
              <div class="card-value">{{ quickStatsDisplay.pointCount.toLocaleString() }}</div>
              <div class="card-description">Total number of rows</div>
            </div>
            <div class="card">
              <div class="card-title">Features</div>
              <div class="card-value">{{ rawFeatureCount }}</div>
              <div class="card-description">Total available columns</div>
            </div>
            <div class="card">
              <div class="card-title">Dataset Type</div>
              <div class="card-value">{{ datasetTypeDisplay }}</div>
              <div class="card-description">Data source</div>
            </div>
            <div class="card">
              <div class="card-title">Selected Features</div>
              <div class="card-value">{{ selectedFeatures.length }}</div>
              <div class="card-description">Features for analysis</div>
            </div>
          </div>
        </div>

        <!-- Dataset visualizations -->
        <div class="visualizations-grid">
          <!-- Feature Statistics Table -->
          <div class="viz-card full-width">
            <h3>Feature Statistics</h3>
            <div v-if="loadingStates.featureStats" class="loading-state">
              <div class="loading-spinner"></div>
              <p>Calculating feature statistics...</p>
            </div>
            <div v-else-if="featureStats && featureStats.length > 0" class="stats-table">
              <table class="stats-table-proper">
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>Mean</th>
                    <th>Std Dev</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>Missing</th>
                    <th>Unique</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="stat in featureStats" :key="stat.feature">
                    <td class="feature-name">{{ selectedFeatureNames[stat.feature] || `Feature ${stat.feature}` }}</td>
                    <td>{{ formatNumber(stat.mean) }}</td>
                    <td>{{ formatNumber(stat.std) }}</td>
                    <td>{{ formatNumber(stat.min) }}</td>
                    <td>{{ formatNumber(stat.max) }}</td>
                    <td>{{ stat.missing || 0 }}</td>
                    <td>{{ stat.unique || 'N/A' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="no-data">
              <p>No feature statistics available. Please select features to analyze.</p>
            </div>
          </div>


          <!-- Feature Distributions -->
          <div class="viz-card full-width">
            <h3>Feature Distributions</h3>
            <div v-if="selectedFeatures.length > 0" class="distribution-container">
              <div class="distribution-controls">
                <label>
                  Selected Feature:
                  <select v-model="selectedDistributionFeature" class="control-select">
                    <option v-for="(featureIndex, arrayIndex) in selectedFeatures" :key="featureIndex" :value="arrayIndex">
                      {{ computedFeatureNames[featureIndex] || `Feature ${featureIndex}` }}
                    </option>
                  </select>
                </label>
              </div>
              <div ref="distributionContainer" class="chart-container"></div>
            </div>
            <div v-else class="no-data">
              <p>Select features to view their distributions.</p>
            </div>
          </div>

          <!-- Feature Correlation Heatmap -->
          <div class="viz-card full-width">
            <h3>Feature Correlation Matrix</h3>
            <div class="info-box small">
              <p>
                Correlation measures how two features move together. We use the Pearson correlation coefficient r ∈ [-1, 1]:
                r ≈ +1 means strong positive (increase together), r ≈ -1 means strong negative (one up, other down), r ≈ 0 means little linear relationship.
              </p>
              <p>How to read this heatmap:</p>
              <ul class="heatmap-help-list">
                <li>Colors: blue = negative, white ≈ 0, red = positive.</li>
                <li>Cell values are r; the diagonal is always 1.00 (feature with itself).</li>
                <li>High |r| (e.g., > {{ correlationThreshold }}) suggests redundancy; consider keeping one feature.</li>
              </ul>
              <div class="legend-row" aria-hidden="true">
                <span class="legend-label">-1</span>
                <div class="legend-gradient"></div>
                <span class="legend-label">+1</span>
              </div>
            </div>
            <div v-if="loadingStates.correlationMatrix" class="loading-state">
              <div class="loading-spinner"></div>
              <p>Computing correlation matrix...</p>
            </div>
            <div v-else-if="selectedFeatures.length > 1">
              <div ref="heatmapContainer" class="chart-container large"></div>
            </div>
            <div v-else class="no-data">
              <p>Select at least 2 features to view correlation matrix.</p>
            </div>
          </div>

          <!-- Data Sample Preview -->
          <div class="viz-card full-width">
            <h3>Data Sample</h3>
            <div v-if="dataSample && dataSample.length > 0" class="sample-table">
              <table class="stats-table-proper">
                <thead>
                  <tr>
                    <th v-for="(feature, index) in selectedFeatureNames" :key="index">{{ feature }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIndex) in dataSample.slice(0, 10)" :key="rowIndex">
                    <td v-for="(value, colIndex) in row.slice(0, selectedFeatures.length)" :key="colIndex">
                      {{ formatNumber(value) }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <p class="sample-info">Showing first 10 rows of {{ selectedFeatures.length }} selected features</p>
            </div>
            <div v-else class="no-data">
              <p>No data sample available.</p>
            </div>
          </div>
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
import * as d3 from 'd3'

interface SampleOption {
  value: string;
  label: string;
}

const globalState = useGlobalState()
const sidebar = useSidebarState()
const sidebarState = sidebar.state
const datasetManager = useDatasetManager()

// Constants
const UPLOADED_FILE_MARKER_PREFIX = "Uploaded: ";

// Enhanced sample configurations with variable feature counts - synchronized with ToyDatasetService
const ENHANCED_SAMPLE_CONFIGURATIONS = {
  // === 2D Synthetic Datasets ===
  'blobs': { 
    dimensions: 8, 
    defaultSamples: 200,
    description: 'Multi-dimensional blob clusters',
    featureNames: ['Feature 1', 'Feature 2', 'Feature 3', 'Feature 4', 'Feature 5', 'Feature 6', 'Feature 7', 'Feature 8']
  },
  'moons': { 
    dimensions: 6, 
    defaultSamples: 200,
    description: 'Interleaving half-circles with noise features',
    featureNames: ['X Coordinate', 'Y Coordinate', 'Noise 1', 'Noise 2', 'Correlated 1', 'Correlated 2']
  },
  'circles': { 
    dimensions: 7, 
    defaultSamples: 200,
    description: 'Concentric circles with additional features',
    featureNames: ['X Coordinate', 'Y Coordinate', 'Radius', 'Angle', 'Noise 1', 'Noise 2', 'Composite']
  },
  'aniso': { 
    dimensions: 5, 
    defaultSamples: 200,
    description: 'Anisotropic blobs with transformations',
    featureNames: ['Feature 1', 'Feature 2', 'Transformed 1', 'Transformed 2', 'Scale Factor']
  },
  'varied': { 
    dimensions: 10, 
    defaultSamples: 200,
    description: 'Varied density clusters',
    featureNames: ['X', 'Y', 'Density', 'Spread', 'Angle', 'Scale', 'Noise 1', 'Noise 2', 'Composite 1', 'Composite 2']
  },
  'sparse_clusters': {
    dimensions: 40,
    defaultSamples: 800,
    description: 'High-dimensional sparse clustering with many irrelevant features',
    featureNames: Array.from({ length: 40 }, (_, i) => {
      if (i < 3) return `Cluster Feature ${i + 1}`
      if (i < 6) return `Signal Feature ${i - 2}`
      if (i < 10) return `Correlated Feature ${i - 5}`
      if (i < 20) return `Noise Feature ${i - 9}`
      return `Random Feature ${i - 19}`
    })
  },
  
  // === High-Dimensional Synthetic Datasets ===
  'blobs_nd': {
    dimensions: 10,
    defaultSamples: 500,
    description: 'Multi-dimensional Gaussian clusters',
    featureNames: Array.from({ length: 10 }, (_, i) => `Dimension ${i + 1}`)
  },
  'classification_nd': {
    dimensions: 15,
    defaultSamples: 1000,
    description: 'High-dimensional classification dataset with noise features',
    featureNames: Array.from({ length: 15 }, (_, i) => 
      i < 5 ? `Informative ${i + 1}` : `Feature ${i + 1}`)
  },
  'hypercube': {
    dimensions: 8,
    defaultSamples: 512,
    description: 'Clusters positioned on hypercube vertices',
    featureNames: Array.from({ length: 8 }, (_, i) => `Dimension ${i + 1}`)
  },
  'swiss_roll_3d': {
    dimensions: 3,
    defaultSamples: 1000,
    description: 'Swiss roll manifold in 3D space',
    featureNames: ['X Coordinate', 'Y Coordinate', 'Z Coordinate']
  },
  
  // === Real-World Datasets ===
  'iris': {
    dimensions: 4,
    defaultSamples: 150,
    description: 'Classic iris flower dataset',
    featureNames: ['Sepal Length', 'Sepal Width', 'Petal Length', 'Petal Width']
  },
  'wine': {
    dimensions: 13,
    defaultSamples: 178,
    description: 'Wine quality dataset',
    featureNames: ['Alcohol', 'Malic Acid', 'Ash', 'Alcalinity', 'Magnesium', 'Total Phenols', 'Flavanoids', 'Nonflavanoid Phenols', 'Proanthocyanins', 'Color Intensity', 'Hue', 'OD280/OD315', 'Proline']
  },
  'breast_cancer': {
    dimensions: 30,
    defaultSamples: 569,
    description: 'Breast cancer diagnosis dataset',
    featureNames: Array.from({ length: 30 }, (_, i) => `Feature ${i + 1}`)
  },
  'digits_small': {
    dimensions: 64,
    defaultSamples: 1797,
    description: 'Handwritten digits dataset (8x8 pixels)',
    featureNames: Array.from({ length: 64 }, (_, i) => `Pixel ${i + 1}`)
  },
  'digits_full': {
    dimensions: 64,
    defaultSamples: 5620,
    description: 'Full handwritten digits dataset (8x8 pixels)',
    featureNames: Array.from({ length: 64 }, (_, i) => `Pixel ${i + 1}`)
  },
  'coil20': {
    dimensions: 1024,
    defaultSamples: 1440,
    description: 'COIL20 object recognition dataset',
    featureNames: Array.from({ length: 1024 }, (_, i) => `Pixel ${i + 1}`)
  },
  'olivetti_faces': {
    dimensions: 4096,
    defaultSamples: 400,
    description: 'Olivetti faces dataset',
    featureNames: Array.from({ length: 4096 }, (_, i) => `Pixel ${i + 1}`)
  },
  'newsgroups': {
    dimensions: 10000,
    defaultSamples: 18000,
    description: '20 Newsgroups text classification',
    featureNames: Array.from({ length: 10000 }, (_, i) => `TF-IDF ${i + 1}`)
  },
  'california_housing': {
    dimensions: 8,
    defaultSamples: 20640,
    description: 'California housing prices dataset',
    featureNames: ['Longitude', 'Latitude', 'Housing Median Age', 'Total Rooms', 'Total Bedrooms', 'Population', 'Households', 'Median Income']
  },
  'coil100': {
    dimensions: 49152,
    defaultSamples: 7200,
    description: 'COIL100 object recognition dataset',
    featureNames: Array.from({ length: 49152 }, (_, i) => `Pixel ${i + 1}`)
  },
  'lfw_faces': {
    dimensions: 5828,
    defaultSamples: 13000,
    description: 'Labeled Faces in the Wild dataset',
    featureNames: Array.from({ length: 5828 }, (_, i) => `Pixel ${i + 1}`)
  },
  'mnist_full': {
    dimensions: 784,
    defaultSamples: 70000,
    description: 'MNIST handwritten digits dataset',
    featureNames: Array.from({ length: 784 }, (_, i) => `Pixel ${i + 1}`)
  },
  'fashion_mnist': {
    dimensions: 784,
    defaultSamples: 70000,
    description: 'Fashion-MNIST clothing images dataset',
    featureNames: Array.from({ length: 784 }, (_, i) => `Pixel ${i + 1}`)
  },
  'covtype': {
    dimensions: 54,
    defaultSamples: 581012,
    description: 'Forest cover type dataset',
    featureNames: Array.from({ length: 54 }, (_, i) => `Feature ${i + 1}`)
  }
} as const

// Reactive data
const selectedSample = ref<string>('')
const uploadedFileName = ref<string | null>(null)
const uploadedData = ref<number[][] | null>(null)
const currentData = ref<number[][]>([])

// Clustering parameters
const selectedTreeType = ref<string>('DCTree')
const selectedPower = ref<number>(2)
const selectedPartitionMethod = ref<string>('auto')
const selectedK = ref<number>(3)
const treeTypes = ref<string[]>([])
const partitionMethods = ref<string[]>([])
const maxK = ref<number>(10)

// Feature selection
const availableFeatures = ref<string[]>([])
const selectedFeatures = ref<number[]>([])
const correlationThreshold = ref(0.8)
const selectedDistributionFeature = ref(0)


// Analysis results
const featureStats = ref<any[]>([])
const dataSample = ref<number[][]>([])
const highCorrelations = ref<any[]>([])

// Loading states for different analysis types
const loadingStates = ref({
  featureStats: false,
  correlationMatrix: false
})

// Component refs
const heatmapContainer = ref<HTMLElement>()
const distributionContainer = ref<HTMLElement>()

// Computed properties
const rawFeatureCount = computed(() => {
  // First priority: Get from active run original_points if available (for high-dimensional datasets)
  const activeRun = globalState.activeRun.value
  if (activeRun && activeRun.clusterData && activeRun.clusterData.original_points && activeRun.clusterData.original_points.length > 0 && activeRun.clusterData.original_points[0]?.length > 0) {
    return activeRun.clusterData.original_points[0].length
  }
  
  // Second priority: Get from current dataset state
  const currentDataset = globalState.currentDataset.value
  if (currentDataset && currentDataset.featureCount && currentDataset.featureCount > 0) {
    return currentDataset.featureCount
  }
  
  // Third priority: Get from uploaded data
  if (uploadedData.value && uploadedData.value.length > 0 && uploadedData.value[0]?.length > 0) {
    return uploadedData.value[0].length
  }
  
  // Fourth priority: Get from current synthetic data
  if (currentData.value.length > 0 && currentData.value[0]?.length > 0) {
    return currentData.value[0].length
  }
  
  // Fourth priority: Get from enhanced sample configurations
  if (selectedSample.value && !selectedSample.value.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
    const config = ENHANCED_SAMPLE_CONFIGURATIONS[selectedSample.value as keyof typeof ENHANCED_SAMPLE_CONFIGURATIONS]
    if (config) {
      return config.dimensions
    }
  }
  
  // Fifth priority: Get from global state sample options (for high-D datasets)
  if (selectedSample.value && !selectedSample.value.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
    const sampleOption = globalState.sampleOptions.value.find(opt => opt.value === selectedSample.value)
    if (sampleOption && sampleOption.dimensions) {
      return sampleOption.dimensions
    }
  }
  
  // Fallback to default
  return 2
})

// Helper function to generate contextual feature names for datasets not in ENHANCED_SAMPLE_CONFIGURATIONS
const generateContextualFeatureNames = (sampleType: string, featureCount: number): string[] => {
  switch (sampleType) {
    case 'sparse_clusters':
      return Array.from({ length: featureCount }, (_, i) => {
        if (i < 3) return `Cluster Feature ${i + 1}`
        if (i < 6) return `Signal Feature ${i - 2}`
        if (i < 10) return `Correlated Feature ${i - 5}`
        if (i < 20) return `Noise Feature ${i - 9}`
        return `Random Feature ${i - 19}`
      })
    case 'blobs_nd':
      return Array.from({ length: featureCount }, (_, i) => 
        i < 2 ? `Primary Axis ${i + 1}` : `Dimension ${i + 1}`
      )
    case 'classification_nd':
      return Array.from({ length: featureCount }, (_, i) => 
        i < Math.floor(featureCount / 3) ? `Informative ${i + 1}` : `Feature ${i + 1}`
      )
    case 'hypercube':
      return Array.from({ length: featureCount }, (_, i) => `Dimension ${i + 1}`)
    default:
      return Array.from({ length: featureCount }, (_, i) => `Feature ${i + 1}`)
  }
}

const computedFeatureNames = computed(() => {
  const featureCount = rawFeatureCount.value
  
  // First priority: Get from dataset manager
  const currentDataset = globalState.currentDataset.value
  if (currentDataset && currentDataset.headers && currentDataset.headers.length >= featureCount) {
    return currentDataset.headers.slice(0, featureCount)
  }
  
  // Second priority: Get from enhanced sample configurations
  if (selectedSample.value && !selectedSample.value.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
    const config = ENHANCED_SAMPLE_CONFIGURATIONS[selectedSample.value as keyof typeof ENHANCED_SAMPLE_CONFIGURATIONS]
    if (config && config.featureNames && config.featureNames.length >= featureCount) {
      return config.featureNames.slice(0, featureCount)
    }
  }
  
  // Third priority: Get from dataset manager fallback
  const managerFeatures = datasetManager.getFeatureNames()
  if (managerFeatures.length >= featureCount) {
    return managerFeatures.slice(0, featureCount)
  }
  
  // Fourth priority: Check global state sample options for feature naming patterns
  if (selectedSample.value && !selectedSample.value.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
    const sampleOption = globalState.sampleOptions.value.find(opt => opt.value === selectedSample.value)
    if (sampleOption && sampleOption.dimensions === featureCount) {
      // Generate context-aware feature names based on dataset type
      return generateContextualFeatureNames(selectedSample.value, featureCount)
    }
  }
  
  // Default fallback
  return Array.from({ length: featureCount }, (_, i) => `Feature ${i + 1}`)
})

const quickStatsDisplay = computed(() => {
  return {
    pointCount: currentData.value.length,
    featureCount: rawFeatureCount.value
  }
})

const selectedFeatureNames = computed(() => {
  return selectedFeatures.value.map(index => computedFeatureNames.value[index] || `Feature ${index + 1}`)
})

const filteredData = computed(() => {
  if (!currentData.value.length || !selectedFeatures.value.length) return []
  return currentData.value.map(row => 
    selectedFeatures.value.map(index => {
      const value = row[index]
      // Don't replace missing values with 0 - preserve them as they are
      if (value === null || value === undefined || value === '') return null
      return value
    })
  )
})

const datasetTypeDisplay = computed(() => {
  const currentDataset = globalState.currentDataset.value
  if (currentDataset?.type === 'imported') return 'Imported Dataset'
  if (uploadedFileName.value) return 'Uploaded'
  return 'Sample Data'
})

const hasValidData = computed(() => {
  return currentData.value.length > 0 && selectedFeatures.value.length >= 2
})


// Utility function to fetch uploaded file data from backend
const fetchUploadedFileData = async (fileId: string): Promise<number[][] | null> => {
  try {
    console.log('[DataExplorer] Fetching file data for fileId:', fileId);
    const response = await $fetch(`/api/data/raw/${fileId}`);
    if (response && response.data) {
      console.log('[DataExplorer] Successfully fetched uploaded data:', response.data.length, 'rows');
      return response.data;
    } else {
      console.warn('[DataExplorer] File data not found in backend response');
      return null;
    }
  } catch (error) {
    console.warn('[DataExplorer] Failed to fetch file data from backend:', error);
    return null;
  }
};

// Utility function to fetch original dataset when PCA-reduced data is detected
const fetchOriginalDatasetForExploration = async (datasetName: string, fallbackData: number[][]) => {
  try {
    console.log(`[DataExplorer] Attempting to fetch original dataset: ${datasetName}`)
    
    // Try different API endpoints to get the original data
    const endpoints = [
      `/api/data/generate/${datasetName}`,
      `/api/toys/dataset/${datasetName}`,
      `/api/toys/sample/${datasetName}`
    ]
    
    for (const endpoint of endpoints) {
      try {
        console.log(`[DataExplorer] Trying endpoint: ${endpoint}`)
        const response = await $fetch(endpoint, {
          method: 'POST',
          body: { 
            n_samples: fallbackData.length,
            return_format: 'array'
          }
        })
        
        if (response && response.data && Array.isArray(response.data) && response.data.length > 0) {
          const originalData = response.data
          console.log(`[DataExplorer] Successfully fetched original dataset:`, {
            rows: originalData.length,
            cols: originalData[0]?.length || 0,
            endpoint: endpoint
          })
          currentData.value = originalData.map(row => [...row])
          return
        }
      } catch (endpointError) {
        console.log(`[DataExplorer] Endpoint ${endpoint} failed:`, endpointError)
        continue
      }
    }
    
    // If all endpoints fail, fall back to PCA data
    console.warn(`[DataExplorer] Could not fetch original dataset ${datasetName}, using PCA-reduced data`)
    currentData.value = fallbackData.map(row => [...row])
    
  } catch (error) {
    console.error('[DataExplorer] Error fetching original dataset:', error)
    // Fall back to PCA data
    currentData.value = fallbackData.map(row => [...row])
  }
};

// Event handlers
const handleRunSelected = (runId: string) => {
  // Not applicable for data explorer
}

const handleRunLoaded = async (run: any) => {
  console.log('DataExplorer: handleRunLoaded called with run:', {
    id: run.id,
    dataset: run.dataset,
    hasParameters: !!run.parameters
  });
  
  try {
    // Load the dataset associated with the run
    if (run.parameters?.sample) {
      // Handle sample data
      selectedSample.value = run.parameters.sample;
      uploadedData.value = null;
      uploadedFileName.value = null;
    } else if (run.parameters?.uploadedFileName) {
      // Handle uploaded file data
      console.log('DataExplorer: Loading uploaded file data for run:', run.parameters.uploadedFileName);
      
      // Try to get the file data from the backend
      const fileData = await fetchUploadedFileData(run.parameters.uploadedFileName);
      if (fileData) {
        uploadedData.value = fileData;
        uploadedFileName.value = run.parameters.uploadedFileName;
        selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + run.parameters.uploadedFileName;
      } else {
        console.warn('DataExplorer: Failed to load file data for run');
        return;
      }
    } else {
      console.warn('DataExplorer: Run has no valid dataset information');
      return;
    }
    
    // Update the global state with the loaded dataset
    await nextTick();
    
    // Force a complete update of the data explorer
    await updateCurrentData();
    updateAvailableFeatures();
    await updateFeatureSelection();
    
    console.log('DataExplorer: Successfully loaded run data');
  } catch (error) {
    console.error('DataExplorer: Error loading run data:', error);
  }
}

const handleSampleChange = (val: string) => {
  selectedSample.value = val
  if (!val.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
    uploadedData.value = null
    uploadedFileName.value = null
  }
  generateDataset()
}

const handleFileUpload = async (event: any) => {
  if (event.parsedData && event.fileName) {
    uploadedData.value = event.parsedData
    uploadedFileName.value = event.fileName
    selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + event.fileName
    
    console.log(`File ${event.fileName} uploaded successfully with ${event.rowCount} rows and ${event.columnCount} columns`)
    
    await updateCurrentData()
  }
}

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

// Data management functions
const updateCurrentData = async () => {
  // First priority: Check for active run data
  const activeRun = globalState.activeRun.value
  if (activeRun && activeRun.clusterData) {
    // Debug: Log the entire cluster data structure
    console.log('[DataExplorer] DEBUGGING activeRun.clusterData structure:', {
      hasPoints: !!activeRun.clusterData.points,
      pointsLength: activeRun.clusterData.points?.length || 0,
      pointsCols: activeRun.clusterData.points?.[0]?.length || 0,
      hasOriginalPoints: !!activeRun.clusterData.original_points,
      originalPointsLength: activeRun.clusterData.original_points?.length || 0,
      originalPointsCols: activeRun.clusterData.original_points?.[0]?.length || 0,
      clusterDataKeys: Object.keys(activeRun.clusterData || {}),
      datasetName: activeRun.dataset
    })
    
    // Prioritize original_points over points for high-dimensional data exploration
    let dataToUse = null
    let dataSource = ''
    
    if (activeRun.clusterData.original_points && activeRun.clusterData.original_points.length > 0) {
      dataToUse = activeRun.clusterData.original_points
      dataSource = 'original_points'
    } else if (activeRun.clusterData.points && activeRun.clusterData.points.length > 0) {
      dataToUse = activeRun.clusterData.points
      dataSource = 'points'
    }
    
    if (dataToUse) {
      const actualCols = dataToUse[0]?.length || 0
      const expectedCols = rawFeatureCount.value
      const isPCAReduced = actualCols < expectedCols && actualCols <= 2
      
      console.log(`[DataExplorer] PRIORITY: Using active run ${dataSource}:`, {
        rows: dataToUse.length,
        cols: actualCols,
        expectedCols: expectedCols,
        source: dataSource,
        isPCAReduced: isPCAReduced,
        firstRowSample: dataToUse[0]?.slice(0, 5)
      })
      
      // If data is PCA-reduced and we're missing dimensions, try to fetch original data
      if (isPCAReduced && selectedSample.value && !selectedSample.value.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
        console.log(`[DataExplorer] Data is PCA-reduced (${actualCols} cols vs ${expectedCols} expected), attempting to fetch original dataset`)
        await fetchOriginalDatasetForExploration(selectedSample.value, dataToUse)
      } else {
        currentData.value = dataToUse.map(row => [...row])
      }
      
      // Set sample type for uploaded/imported datasets
      if (activeRun.dataset && (activeRun.dataset.includes('Uploaded') || activeRun.dataset.includes('Imported'))) {
        selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + activeRun.dataset.replace(' (Uploaded)', '').replace(' (Imported)', '')
      }
    }
  } else {
    // Second priority: Use data from global state (from active clustering run)
    const globalDataset = globalState.currentDataset.value
    if (globalDataset && globalDataset.data && globalDataset.data.length > 0) {
      console.log('[DataExplorer] Using global state dataset:', globalDataset.data.length, 'rows')
      currentData.value = globalDataset.data.map(row => [...row])
      // Set sample type for uploaded/imported datasets
      if (globalDataset.type === 'uploaded' || globalDataset.type === 'imported') {
        selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + (globalDataset.fileName || globalDataset.name)
      }
    } else if (uploadedData.value?.length) {
      currentData.value = uploadedData.value
    } else {
      generateSyntheticData()
    }
  }
  
  console.log('[DataExplorer] Current data updated:', {
    dataLength: currentData.value.length,
    dataCols: currentData.value[0]?.length || 0,
    selectedSample: selectedSample.value,
    rawFeatureCount: rawFeatureCount.value
  })
  updateAvailableFeatures()
  calculateFeatureStatistics()
  updateDataSample()
  nextTick(async () => await renderVisualizations())
}

const generateDataset = () => {
  generateSyntheticData()
  updateAvailableFeatures()
  calculateFeatureStatistics()
  updateDataSample()
  nextTick(async () => await renderVisualizations())
}

const generateSyntheticData = () => {
  if (selectedSample.value.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
    console.log('[DataExplorer] Skipping synthetic data generation for uploaded data')
    return // Skip generation for uploaded data
  }
  
  // Check if we have real dataset data from global state first
  const currentDataset = globalState.currentDataset.value
  if (currentDataset && currentDataset.data && currentDataset.data.length > 0) {
    console.log(`[DataExplorer] Using real dataset data from global state: ${currentDataset.data.length} rows`)
    currentData.value = currentDataset.data.map(row => [...row])
    return
  }
  
  // Check if we have active run data
  const activeRun = globalState.activeRun.value
  if (activeRun && activeRun.clusterData) {
    console.log('[DataExplorer] DEBUGGING generateSyntheticData activeRun.clusterData:', {
      hasPoints: !!activeRun.clusterData.points,
      pointsLength: activeRun.clusterData.points?.length || 0,
      pointsCols: activeRun.clusterData.points?.[0]?.length || 0,
      hasOriginalPoints: !!activeRun.clusterData.original_points,
      originalPointsLength: activeRun.clusterData.original_points?.length || 0,
      originalPointsCols: activeRun.clusterData.original_points?.[0]?.length || 0
    })
    
    // Prioritize original_points over points for high-dimensional data exploration
    let dataToUse = null
    let dataSource = ''
    
    if (activeRun.clusterData.original_points && activeRun.clusterData.original_points.length > 0) {
      dataToUse = activeRun.clusterData.original_points
      dataSource = 'original_points'
    } else if (activeRun.clusterData.points && activeRun.clusterData.points.length > 0) {
      dataToUse = activeRun.clusterData.points
      dataSource = 'points'
    }
    
    if (dataToUse) {
      console.log(`[DataExplorer] SYNTHETIC: Using active run ${dataSource}: ${dataToUse.length} rows, ${dataToUse[0]?.length || 0} cols`)
      currentData.value = dataToUse.map(row => [...row])
      return
    }
  }
  
  // Get sample configuration from global state
  let config = ENHANCED_SAMPLE_CONFIGURATIONS[selectedSample.value as keyof typeof ENHANCED_SAMPLE_CONFIGURATIONS]
  
  // If no local config found, create one from global state
  if (!config && currentDataset && currentDataset.type === 'sample') {
    config = {
      dimensions: currentDataset.featureCount || 2,
      defaultSamples: currentDataset.n_samples || 200,
      description: `Sample dataset: ${currentDataset.name}` as any,
      featureNames: (currentDataset.headers || Array.from({ length: currentDataset.featureCount || 2 }, (_, i) => `Feature ${i + 1}`)) as any
    }
    console.log(`[DataExplorer] Using dynamic config for ${selectedSample.value}:`, config)
  }
  
  if (!config) {
    console.warn(`[DataExplorer] Unknown sample type: ${selectedSample.value}, falling back to empty data`)
    currentData.value = []
    return
  }
  
  const size = config.defaultSamples
  const dimensions = config.dimensions
  const data: number[][] = []
  const random = d3.randomNormal()
  
  console.log(`[DataExplorer] Generating ${size} samples with ${dimensions} dimensions for ${selectedSample.value}`)
  
  for (let i = 0; i < size; i++) {
    let point: number[]
    
    switch (selectedSample.value) {
      case 'moons':
        point = generateMoonsData(random, dimensions)
        break
      case 'circles':
        point = generateCirclesData(random, dimensions)
        break
      case 'aniso':
        point = generateAnisoData(random, dimensions)
        break
      case 'varied':
        point = generateVariedData(random, dimensions)
        break
      case 'sparse_clusters':
        point = generateSparseClustersData(random, dimensions)
        break
      default: // blobs
        point = generateBlobsData(random, dimensions)
    }
    
    data.push(point)
  }
  
  currentData.value = data
  console.log(`[DataExplorer] Generated dataset with ${data.length} rows and ${data[0]?.length || 0} features`)
}

// Enhanced data generation functions
function generateBlobsData(random: () => number, dimensions: number): number[] {
  const cluster_id = Math.floor(Math.random() * 3)
  const cluster_centers = [
    Array.from({ length: dimensions }, (_, i) => i < 2 ? [-1, -1][i] : (random() * 0.5)),
    Array.from({ length: dimensions }, (_, i) => i < 2 ? [0, 1][i] : (random() * 0.5)),
    Array.from({ length: dimensions }, (_, i) => i < 2 ? [1, -1][i] : (random() * 0.5))
  ]
  
  const center = cluster_centers[cluster_id]
  return center.map((c, i) => {
    if (i < 2) {
      return c + random() * 0.8 // Primary features with cluster structure
    } else if (i < 4) {
      return c + random() * 1.2 // Noisy features
    } else if (i < 6) {
      return center[0] * 0.3 + center[1] * 0.7 + random() * 0.5 // Correlated features
    } else {
      return random() * 2 - 1 // Pure noise features
    }
  })
}

function generateMoonsData(random: () => number, dimensions: number): number[] {
  const angle = Math.PI * Math.random()
  const radius = 1 + 0.1 * random()
  const x = radius * Math.cos(angle) + 0.1 * random()
  const y = radius * Math.sin(angle) + 0.1 * random()
  
  const point = [x, y]
  
  // Add additional features
  for (let i = 2; i < dimensions; i++) {
    if (i < 4) {
      point.push(random() * 0.5) // Noise features
    } else {
      point.push(x * 0.3 + y * 0.7 + random() * 0.3) // Correlated features
    }
  }
  
  return point
}

function generateCirclesData(random: () => number, dimensions: number): number[] {
  const theta = 2 * Math.PI * Math.random()
  const r = Math.random() < 0.5 ? 0.3 + 0.1 * Math.random() : 0.8 + 0.1 * Math.random()
  const x = r * Math.cos(theta) + 0.05 * random()
  const y = r * Math.sin(theta) + 0.05 * random()
  
  const point = [x, y, r, theta] // Include radius and angle as features
  
  // Add additional features
  for (let i = 4; i < dimensions; i++) {
    if (i < 6) {
      point.push(random() * 0.4) // Noise features
    } else {
      point.push(Math.sqrt(x*x + y*y) + random() * 0.2) // Composite features
    }
  }
  
  return point.slice(0, dimensions)
}

function generateAnisoData(random: () => number, dimensions: number): number[] {
  const blob_x = random()
  const blob_y = random()
  const transformed_x = 0.6 * blob_x - 0.6 * blob_y
  const transformed_y = -0.4 * blob_x + 0.8 * blob_y
  
  const point = [blob_x, blob_y, transformed_x, transformed_y]
  
  // Add scale factor and additional features
  for (let i = 4; i < dimensions; i++) {
    point.push(Math.abs(transformed_x) + Math.abs(transformed_y) + random() * 0.3)
  }
  
  return point.slice(0, dimensions)
}

function generateVariedData(random: () => number, dimensions: number): number[] {
  const cluster = Math.floor(Math.random() * 3)
  const centers = [[-2, -2], [0, 0], [2, 2]]
  const stds = [1.0, 2.5, 0.5]
  const center = centers[cluster]
  const std = stds[cluster]
  
  const x = center[0] + std * random()
  const y = center[1] + std * random()
  const density = 1.0 / (std + 0.1)
  const spread = std
  
  const point = [x, y, density, spread]
  
  // Add additional features with varying correlations
  for (let i = 4; i < dimensions; i++) {
    if (i < 6) {
      point.push(Math.atan2(y, x) + random() * 0.2) // Angle-based features
    } else if (i < 8) {
      point.push(random() * 1.5) // Pure noise
    } else {
      point.push(x * 0.4 + y * 0.6 + density * 0.3 + random() * 0.5) // Composite features
    }
  }
  
  return point.slice(0, dimensions)
}

function generateSparseClustersData(random: () => number, dimensions: number): number[] {
  // Generate high-dimensional sparse clusters with many irrelevant features
  const cluster_id = Math.floor(Math.random() * 3)
  const point: number[] = []
  
  // Define cluster centers for the first 3 meaningful dimensions
  const cluster_centers = [
    [-2, -2, -2],
    [0, 2, -1],
    [3, -1, 2]
  ]
  const center = cluster_centers[cluster_id]
  
  for (let i = 0; i < dimensions; i++) {
    if (i < 3) {
      // Core clustering features - clear signal
      point.push(center[i] + random() * 0.8)
    } else if (i < 6) {
      // Secondary signal features - weaker but still informative
      point.push(center[i % 3] * 0.5 + random() * 1.2)
    } else if (i < 10) {
      // Correlated features - dependent on core features
      point.push(center[0] * 0.3 + center[1] * 0.4 + random() * 0.7)
    } else if (i < 20) {
      // Noisy features - some weak correlation with cluster structure
      point.push(cluster_id * 0.2 + random() * 2.0)
    } else {
      // Pure random features - no clustering signal
      point.push(random() * 4.0 - 2.0)
    }
  }
  
  return point
}

const updateAvailableFeatures = () => {
  if (!currentData.value.length) return

  const featureCount = rawFeatureCount.value
  availableFeatures.value = computedFeatureNames.value

  // Select features by default if none selected, or when feature count changes
  // For all datasets, limit to first 20 features for visualization performance
  // All features are processed in the background regardless of selection
  if (selectedFeatures.value.length === 0 || selectedFeatures.value.some(index => index >= featureCount)) {
    const maxFeatures = Math.min(featureCount, 20)
    selectedFeatures.value = Array.from({ length: maxFeatures }, (_, i) => i)
    // Reset distribution feature when features change
    selectedDistributionFeature.value = 0
  }

  console.log(`[DataExplorer] Updated features: ${featureCount} total, available:`, availableFeatures.value)
  console.log(`[DataExplorer] Selected features:`, selectedFeatures.value)
}

const getDatasetId = () => {
  // Try to get dataset ID from various sources
  console.log('[DataExplorer] Determining dataset ID...')
  console.log('[DataExplorer] selectedSample:', selectedSample.value)
  
  // Priority 1: File ID from uploaded data (most specific)
  const currentDataset = globalState.currentDataset.value
  if (currentDataset?.fileId) {
    console.log('[DataExplorer] Using fileId from currentDataset:', currentDataset.fileId)
    return currentDataset.fileId
  }
  
  // Priority 2: Active run with file ID (for clustering results from uploaded data)
  const activeRun = globalState.activeRun.value
  if (activeRun?.parameters?.fileId) {
    console.log('[DataExplorer] Using fileId from activeRun:', activeRun.parameters.fileId)
    return activeRun.parameters.fileId
  }
  
  // Priority 3: Sample datasets (most reliable for toy data)
  if (selectedSample.value && !selectedSample.value.startsWith(UPLOADED_FILE_MARKER_PREFIX)) {
    console.log('[DataExplorer] Using sample dataset:', selectedSample.value)
    return selectedSample.value
  }
  
  // Priority 4: Active run ID (for cluster results)
  if (activeRun?.id) {
    console.log('[DataExplorer] Using activeRun id:', activeRun.id)
    return activeRun.id
  }
  
  console.log('[DataExplorer] No dataset ID found')
  return null
}

const calculateFeatureStatistics = async () => {
  if (!filteredData.value.length) return
  
  loadingStates.value.featureStats = true
  
  // Determine dataset ID and whether to use optimized dataset-based API
  const datasetId = getDatasetId()
  const dataSize = filteredData.value.length * (filteredData.value[0]?.length || 0)
  const useOptimizedAPI = dataSize > 50000 || selectedFeatures.value.length > 30 || datasetId
  
  try {
    if (useOptimizedAPI && datasetId) {
      console.log('[DataExplorer] Using optimized dataset-based API for feature statistics')
      console.log('[DataExplorer] Dataset ID:', datasetId, 'Data size:', dataSize, 'Features:', selectedFeatures.value.length)
      
      const analysisRequest = {
        dataset_id: datasetId,
        selected_features: selectedFeatures.value,
        feature_names: selectedFeatureNames.value,
        sample_size: dataSize > 100000 ? 2000 : null, // Sample for very large datasets
        options: {
          include_advanced_stats: true,
          handle_missing_values: true
        }
      }
      
      const response = await $fetch('/api/analyze/dataset/feature-statistics', {
        method: 'POST',
        body: analysisRequest
      })
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      // Convert backend response to frontend format
      featureStats.value = response.feature_statistics.map((stat: any) => ({
        feature: stat.feature,
        mean: stat.mean,
        std: stat.std,
        min: stat.min,
        max: stat.max,
        variance: stat.variance,
        missing: stat.missing,
        unique: stat.unique
      }))
      
      console.log(`[DataExplorer] Optimized feature statistics completed for ${response.total_features} features`)
      if (response.analysis_metadata?.sampled) {
        console.log(`[DataExplorer] Used sampling: ${response.analysis_metadata.sample_size} of ${response.analysis_metadata.original_shape} data points`)
      }
      loadingStates.value.featureStats = false
      
      return
    } else {
      console.log('[DataExplorer] Using direct API for feature statistics analysis')
      
      const analysisRequest = {
        data: filteredData.value,
        selected_features: selectedFeatures.value,
        feature_names: selectedFeatureNames.value,
        options: {
          include_advanced_stats: true,
          handle_missing_values: true
        }
      }
      
      const response = await $fetch('/api/analyze/feature-statistics', {
        method: 'POST',
        body: analysisRequest
      })
    }
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      // Convert backend response to frontend format
      featureStats.value = response.feature_statistics.map((stat: any) => ({
        feature: stat.feature,
        mean: stat.mean,
        std: stat.std,
        min: stat.min,
        max: stat.max,
        variance: stat.variance,
        missing: stat.missing,
        unique: stat.unique
      }))
      
      console.log(`[DataExplorer] Backend feature statistics completed for ${response.total_features} features`)
      loadingStates.value.featureStats = false
      
      return
      
  } catch (error: any) {
    console.warn('[DataExplorer] Backend feature statistics failed, falling back to frontend:', error)
    
    // Provide user feedback for specific error types
    if (error?.status === 422 || error?.statusCode === 422) {
      console.log('[DataExplorer] Request too large (422), using frontend calculation with sampling')
      // For 422 errors, sample the data for frontend processing
      if (filteredData.value.length > 1000) {
        const sampleSize = Math.min(1000, filteredData.value.length)
        const step = Math.floor(filteredData.value.length / sampleSize)
        const sampledData = filteredData.value.filter((_, index) => index % step === 0).slice(0, sampleSize)
        console.log(`[DataExplorer] Sampling ${sampledData.length} rows from ${filteredData.value.length} total for frontend processing`)
        // Use sampledData for frontend calculation below
        filteredData.value = sampledData
      }
    } else if (error?.status === 400 || error?.statusCode === 400) {
      console.log('[DataExplorer] Bad request (400), likely invalid data format')
    }
    
    // Fall through to frontend calculation
  }
  
  // Frontend fallback when backend fails
  console.log('[DataExplorer] Using frontend for feature statistics analysis')
  
  const stats = []
  const numFeatures = filteredData.value[0]?.length || 0
  
  for (let featureIndex = 0; featureIndex < numFeatures; featureIndex++) {
    const values = filteredData.value.map(row => row[featureIndex]).filter(v => v !== null && v !== undefined && !isNaN(v))
    
    if (values.length === 0) continue
    
    const mean = d3.mean(values) || 0
    const variance = d3.variance(values) || 0
    const std = Math.sqrt(variance)
    const min = d3.min(values) || 0
    const max = d3.max(values) || 0
    const missing = filteredData.value.length - values.length
    const unique = new Set(values).size
    
    stats.push({
      feature: featureIndex,
      mean,
      std,
      min,
      max,
      variance,
      missing,
      unique
    })
  }
  
  featureStats.value = stats
  
  // Reset loading state
  loadingStates.value.featureStats = false
  
}

const fetchDataSampleFromBackend = async (): Promise<number[][] | null> => {
  const datasetId = getDatasetId()
  
  try {
    if (datasetId && selectedFeatures.value.length > 0) {
      console.log('[DataExplorer] Using backend API for data samples')
      console.log('[DataExplorer] Dataset ID:', datasetId, 'Features:', selectedFeatures.value.length)
      
      const sampleRequest = {
        dataset_id: datasetId,
        selected_features: selectedFeatures.value,
        feature_names: selectedFeatureNames.value,
        sample_size: 20, // Number of rows to sample
        options: {
          handle_missing_values: true
        }
      }
      
      console.log('[DataExplorer] Sending data sample request:', sampleRequest)
      
      const response = await $fetch('/api/analyze/dataset/data-sample', {
        method: 'POST',
        body: sampleRequest
      })
      
      if (response && response.success && response.data_sample && Array.isArray(response.data_sample)) {
        console.log(`[DataExplorer] Backend data sample successful: ${response.data_sample.length} rows, ${response.data_sample[0]?.length || 0} cols`)
        console.log('[DataExplorer] Sample metadata:', response.metadata)
        return response.data_sample
      } else if (response && response.error) {
        console.error('[DataExplorer] Backend data sample error:', response.error)
        throw new Error(response.error)
      } else {
        console.warn('[DataExplorer] Invalid response format from data sample API')
        throw new Error('Invalid response format')
      }
    }
    
    // Fallback: Use filtered data (PCA-reduced) if no dataset ID
    console.log('[DataExplorer] No dataset ID available, using frontend filteredData for samples (PCA-reduced)')
    if (filteredData.value.length > 0 && selectedFeatures.value.length > 0) {
      return filteredData.value.slice(0, 20)
    }
    
    return []
    
  } catch (error: any) {
    console.error('[DataExplorer] Error fetching data sample from backend:', error)
    
    // Final fallback: Use filtered data (PCA-reduced)
    console.log('[DataExplorer] Falling back to frontend filteredData due to backend error')
    if (filteredData.value.length > 0 && selectedFeatures.value.length > 0) {
      return filteredData.value.slice(0, 20)
    }
    return []
  }
}

const updateDataSample = async () => {
  try {
    const sampleData = await fetchDataSampleFromBackend()
    
    if (sampleData && sampleData.length > 0) {
      dataSample.value = sampleData
      console.log(`[DataExplorer] Data sample updated:`, {
        sampleRows: dataSample.value.length,
        sampleCols: dataSample.value[0]?.length || 0,
        selectedFeatures: selectedFeatures.value.length,
        firstRow: dataSample.value[0]?.slice(0, 3) // Show first 3 values
      })
    } else {
      dataSample.value = []
      console.log(`[DataExplorer] Data sample cleared - no data available`)
    }
  } catch (error) {
    console.error('[DataExplorer] Error updating data sample:', error)
    dataSample.value = []
  }
}

// Feature selection functions
const updateFeatureSelection = async () => {
  // Reset distribution feature selection if it's out of bounds
  if (selectedDistributionFeature.value >= selectedFeatures.value.length) {
    selectedDistributionFeature.value = 0
  }
  
  calculateFeatureStatistics()
  await updateDataSample()
  nextTick(async () => await renderVisualizations())
}

const selectAllFeatures = async () => {
  // Limit to first 20 features to prevent graph overflow
  const maxFeatures = Math.min(availableFeatures.value.length, 20)
  selectedFeatures.value = Array.from({ length: maxFeatures }, (_, i) => i)
  await updateFeatureSelection()
}

const clearAllFeatures = async () => {
  selectedFeatures.value = []
  await updateFeatureSelection()
}

const analyzeCorrelations = async () => {
  if (!filteredData.value.length) return
  
  console.log('[DataExplorer] Starting correlation analysis')
  
  // Calculate correlations and trigger re-render
  const correlations = await calculateCorrelationMatrix(filteredData.value)
  
  // If backend already populated highCorrelations, ensure heatmap is re-rendered
  if (highCorrelations.value.length > 0) {
    console.log('[DataExplorer] Backend provided top correlations, ensuring heatmap is visible')
    // Force re-render of heatmap to ensure it doesn't disappear
    nextTick(async () => await renderCorrelationHeatmap())
    return
  }
  
  // Frontend correlation analysis (fallback)
  const allCorrelations = []
  
  // Collect all correlations between different features (excluding self-correlation)
  for (let i = 0; i < correlations.length; i++) {
    for (let j = i + 1; j < correlations[i].length; j++) {
      const corr = correlations[i][j]
      allCorrelations.push({
        feature1: selectedFeatureNames.value[i],
        feature2: selectedFeatureNames.value[j],
        correlation: corr
      })
    }
  }
  
  // Show only top 3 highest correlations by absolute value (regardless of threshold)
  highCorrelations.value = allCorrelations
    .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation))
    .slice(0, 3)
  
  console.log('[DataExplorer] Correlation analysis complete, top correlations:', highCorrelations.value)
  
  // Ensure heatmap is re-rendered after updating correlations
  nextTick(async () => await renderCorrelationHeatmap())
}


const calculateCorrelationMatrix = async (data: number[][]): Promise<number[][]> => {
  loadingStates.value.correlationMatrix = true
  
  // Determine dataset ID and whether to use optimized dataset-based API
  const datasetId = getDatasetId()
  const dataSize = data.length * (data[0]?.length || 0)
  const useOptimizedAPI = dataSize > 50000 || selectedFeatures.value.length > 30 || datasetId
  
  try {
    if (useOptimizedAPI && datasetId) {
      console.log('[DataExplorer] Using optimized dataset-based API for correlation matrix')
      console.log('[DataExplorer] Dataset ID:', datasetId, 'Data size:', dataSize, 'Features:', selectedFeatures.value.length)
      
      const analysisRequest = {
        dataset_id: datasetId,
        selected_features: selectedFeatures.value,
        feature_names: selectedFeatureNames.value,
        sample_size: dataSize > 100000 ? 2000 : null, // Sample for very large datasets
        options: {
          correlation_threshold: correlationThreshold.value,
          top_correlations_limit: 10,
          handle_missing_values: true
        }
      }
      
      const response = await $fetch('/api/analyze/dataset/correlation-matrix', {
        method: 'POST',
        body: analysisRequest
      })
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      // Update high correlations from backend response
      highCorrelations.value = response.top_correlations || []
      
      console.log(`[DataExplorer] Optimized correlation matrix completed for ${response.num_features} features`)
      if (response.analysis_metadata?.sampled) {
        console.log(`[DataExplorer] Used sampling: ${response.analysis_metadata.sample_size} of ${response.analysis_metadata.original_shape} data points`)
      }
      loadingStates.value.correlationMatrix = false
      return response.correlation_matrix
    } else {
      console.log('[DataExplorer] Using direct API for correlation matrix analysis')
      
      const analysisRequest = {
        data: data,
        selected_features: selectedFeatures.value,
        feature_names: selectedFeatureNames.value,
        options: {
          correlation_threshold: correlationThreshold.value,
          top_correlations_limit: 10,
          handle_missing_values: true
        }
      }
      
      const response = await $fetch('/api/analyze/correlation-matrix', {
        method: 'POST',
        body: analysisRequest
      })
    }
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      // Update high correlations from backend response
      highCorrelations.value = response.top_correlations || []
      
      console.log(`[DataExplorer] Backend correlation matrix completed for ${response.num_features} features`)
      loadingStates.value.correlationMatrix = false
      return response.correlation_matrix
      
  } catch (error: any) {
    console.warn('[DataExplorer] Backend correlation matrix failed, falling back to frontend:', error)
    
    // Provide user feedback for specific error types
    if (error?.status === 422 || error?.statusCode === 422) {
      console.log('[DataExplorer] Request too large (422), using frontend calculation with sampling')
      // For 422 errors, sample the data for frontend processing
      if (data.length > 1000) {
        const sampleSize = Math.min(1000, data.length)
        const step = Math.floor(data.length / sampleSize)
        const sampledData = data.filter((_, index) => index % step === 0).slice(0, sampleSize)
        console.log(`[DataExplorer] Sampling ${sampledData.length} rows from ${data.length} total for correlation matrix`)
        data = sampledData
      }
    } else if (error?.status === 400 || error?.statusCode === 400) {
      console.log('[DataExplorer] Bad request (400), likely invalid data format')
    }
    
    // Fall through to frontend calculation
  }
  
  // Frontend fallback when backend fails
  console.log('[DataExplorer] Using frontend for correlation matrix analysis')
  
  const numFeatures = data[0]?.length || 0
  const correlations: number[][] = []
  
  for (let i = 0; i < numFeatures; i++) {
    correlations[i] = []
    
    for (let j = 0; j < numFeatures; j++) {
      if (i === j) {
        correlations[i][j] = 1
      } else {
        // Filter paired values to ensure same-length arrays
        const validPairs = data
          .map(row => ({ valueI: row[i], valueJ: row[j] }))
          .filter(pair => 
            pair.valueI !== null && pair.valueI !== undefined && !isNaN(pair.valueI) &&
            pair.valueJ !== null && pair.valueJ !== undefined && !isNaN(pair.valueJ)
          )
        
        const valuesI = validPairs.map(pair => pair.valueI)
        const valuesJ = validPairs.map(pair => pair.valueJ)
        
        correlations[i][j] = calculatePearsonCorrelation(valuesI, valuesJ)
      }
    }
  }
  
  loadingStates.value.correlationMatrix = false
  return correlations
}

const calculatePearsonCorrelation = (x: number[], y: number[]): number => {
  const n = Math.min(x.length, y.length)
  if (n === 0) return 0
  
  const meanX = d3.mean(x) || 0
  const meanY = d3.mean(y) || 0
  
  let numerator = 0
  let sumXSquared = 0
  let sumYSquared = 0
  
  for (let i = 0; i < n; i++) {
    const deltaX = x[i] - meanX
    const deltaY = y[i] - meanY
    numerator += deltaX * deltaY
    sumXSquared += deltaX * deltaX
    sumYSquared += deltaY * deltaY
  }
  
  const denominator = Math.sqrt(sumXSquared * sumYSquared)
  return denominator === 0 ? 0 : numerator / denominator
}

// Visualization functions
const renderVisualizations = async () => {
  await renderCorrelationHeatmap()
  await renderDistribution()
}

const renderCorrelationHeatmap = async () => {
  if (!heatmapContainer.value || !filteredData.value.length || selectedFeatures.value.length < 2) return
  
  d3.select(heatmapContainer.value).selectAll("*").remove()
  
  const correlations = await calculateCorrelationMatrix(filteredData.value)
  const size = correlations.length
  
  if (size === 0) return
  
  const margin = { top: 100, right: 25, bottom: 30, left: 120 }
  const width = Math.min(600, heatmapContainer.value.clientWidth) - margin.left - margin.right
  const height = Math.min(600, width) - margin.top - margin.bottom
  
  const svg = d3.select(heatmapContainer.value)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  const cellSize = Math.min(width, height) / size
  
  const colorScale = d3.scaleSequential(d3.interpolateRdBu)
    .domain([1, -1])
  
  for (let i = 0; i < size; i++) {
    for (let j = 0; j < size; j++) {
      svg.append("rect")
        .attr("x", j * cellSize)
        .attr("y", i * cellSize)
        .attr("width", cellSize)
        .attr("height", cellSize)
        .style("fill", colorScale(correlations[i][j]))
        .style("stroke", "white")
        .style("stroke-width", 1)
      
      svg.append("text")
        .attr("x", j * cellSize + cellSize / 2)
        .attr("y", i * cellSize + cellSize / 2)
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .style("font-size", "10px")
        .style("fill", Math.abs(correlations[i][j]) > 0.5 ? "white" : "black")
        .text(correlations[i][j].toFixed(2))
    }
  }
  
  svg.selectAll(".x-label")
    .data(selectedFeatureNames.value)
    .enter()
    .append("text")
    .attr("class", "x-label")
    .attr("x", (d, i) => i * cellSize + cellSize / 2)
    .attr("y", -15)
    .attr("text-anchor", "start")
    .attr("transform", (d, i) => `rotate(-45, ${i * cellSize + cellSize / 2}, -15)`)
    .style("font-size", "11px")
    .text(d => d.length > 12 ? d.substring(0, 12) + '...' : d)
  
  svg.selectAll(".y-label")
    .data(selectedFeatureNames.value)
    .enter()
    .append("text")
    .attr("class", "y-label")
    .attr("x", -15)
    .attr("y", (d, i) => i * cellSize + cellSize / 2)
    .attr("text-anchor", "end")
    .attr("dy", "0.35em")
    .style("font-size", "11px")
    .text(d => d.length > 15 ? d.substring(0, 15) + '...' : d)
}

const fetchFeatureDistributionFromBackend = async (featureArrayIndex: number): Promise<number[] | null> => {
  const datasetId = getDatasetId()
  
  try {
    if (datasetId && selectedFeatures.value.length > 0 && featureArrayIndex < selectedFeatures.value.length) {
      const actualFeatureIndex = selectedFeatures.value[featureArrayIndex]
      console.log('[DataExplorer] Using backend API for feature distribution')
      console.log('[DataExplorer] Feature array index:', featureArrayIndex, 'Actual feature:', actualFeatureIndex, 'Name:', computedFeatureNames.value[actualFeatureIndex])
      
      const distributionRequest = {
        dataset_id: datasetId,
        selected_features: selectedFeatures.value,
        feature_names: selectedFeatureNames.value,
        feature_index: featureArrayIndex, // Index within the selected features array
        sample_size: 1000, // Number of values for distribution
        options: {
          handle_missing_values: true
        }
      }
      
      console.log('[DataExplorer] Sending feature distribution request:', distributionRequest)
      
      const response = await $fetch('/api/analyze/dataset/feature-distribution', {
        method: 'POST',
        body: distributionRequest
      })
      
      if (response && response.success && response.feature_values && Array.isArray(response.feature_values)) {
        console.log(`[DataExplorer] Backend feature distribution successful: ${response.feature_values.length} values for feature '${response.feature_name}'`)
        console.log('[DataExplorer] Distribution metadata:', response.metadata)
        return response.feature_values.filter(v => !isNaN(v))
      } else if (response && response.error) {
        console.error('[DataExplorer] Backend feature distribution error:', response.error)
        throw new Error(response.error)
      } else {
        console.warn('[DataExplorer] Invalid response format from feature distribution API')
        throw new Error('Invalid response format')
      }
    }
    
    // Fallback: Use filtered data (PCA-reduced) if no dataset ID or invalid index
    console.log('[DataExplorer] No dataset ID available or invalid feature index, using frontend filteredData for distribution (PCA-reduced)')
    if (filteredData.value.length > 0 && featureArrayIndex < filteredData.value[0]?.length) {
      return filteredData.value.map(row => row[featureArrayIndex]).filter(v => !isNaN(v))
    }
    
    return []
    
  } catch (error: any) {
    console.error('[DataExplorer] Error fetching feature distribution from backend:', error)
    
    // Final fallback: Use filtered data (PCA-reduced)
    console.log('[DataExplorer] Falling back to frontend filteredData due to backend error')
    if (filteredData.value.length > 0 && featureArrayIndex < filteredData.value[0]?.length) {
      return filteredData.value.map(row => row[featureArrayIndex]).filter(v => !isNaN(v))
    }
    return []
  }
}

const renderDistribution = async () => {
  if (!distributionContainer.value || selectedFeatures.value.length === 0) return
  
  d3.select(distributionContainer.value).selectAll("*").remove()
  
  const featureArrayIndex = selectedDistributionFeature.value
  const actualFeatureIndex = selectedFeatures.value[featureArrayIndex]
  
  console.log(`[DataExplorer] Rendering distribution:`, {
    featureArrayIndex,
    actualFeatureIndex,
    featureName: computedFeatureNames.value[actualFeatureIndex],
    selectedFeaturesLength: selectedFeatures.value.length
  })
  
  // Fetch values from backend API
  const values = await fetchFeatureDistributionFromBackend(featureArrayIndex)
  
  if (!values || values.length === 0) {
    console.log('[DataExplorer] No distribution data available')
    return
  }
  
  console.log(`[DataExplorer] Distribution values count: ${values.length}`)
  console.log(`[DataExplorer] Value range: ${Math.min(...values)} to ${Math.max(...values)}`)
  
  const margin = { top: 20, right: 60, bottom: 60, left: 60 } // Increased margins for better axis labels
  const width = distributionContainer.value.clientWidth - margin.left - margin.right
  const height = 300 - margin.top - margin.bottom
  
  const svg = d3.select(distributionContainer.value)
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`)
  
  // Handle small values by determining appropriate scale and format
  const [minVal, maxVal] = d3.extent(values) as [number, number]
  const range = maxVal - minVal
  const isVerySmall = Math.abs(maxVal) < 0.01 && Math.abs(minVal) < 0.01
  const hasNearZero = Math.abs(minVal) < 0.001 || Math.abs(maxVal) < 0.001
  const isConstantValue = range < 1e-10 // Values are essentially the same
  
  console.log(`[DataExplorer] Value analysis: min=${minVal}, max=${maxVal}, range=${range}, isVerySmall=${isVerySmall}, hasNearZero=${hasNearZero}, isConstantValue=${isConstantValue}`)
  
  let x, bins
  
  if (isConstantValue) {
    // Special case: all values are essentially the same
    console.log(`[DataExplorer] Detected constant values, using special rendering`)
    
    // Create a symmetric domain around the constant value
    const constantValue = (minVal + maxVal) / 2
    const padding = Math.max(Math.abs(constantValue) * 0.1, 0.001)
    
    x = d3.scaleLinear()
      .domain([constantValue - padding, constantValue + padding])
      .range([0, width])
    
    // Create a single bin for all values
    bins = [{
      x0: constantValue - padding/4,
      x1: constantValue + padding/4,
      length: values.length,
      data: values
    }]
  } else {
    // Normal case: values have some variation
    x = d3.scaleLinear()
      .domain(d3.extent(values) as [number, number])
      .nice() // This makes the domain more readable
      .range([0, width])
    
    // Adaptive binning based on data range and size
    let binCount = 20
    if (values.length < 50) binCount = 10
    if (values.length > 1000) binCount = 30
    if (isVerySmall) binCount = 15 // Fewer bins for very small values
    
    const histogram = d3.histogram()
      .value(d => d)
      .domain(x.domain() as [number, number])
      .thresholds(x.ticks(binCount))
    
    bins = histogram(values)
  }
  
  const y = d3.scaleLinear()
    .domain([0, d3.max(bins, d => d.length) || 0])
    .nice()
    .range([height, 0])
  
  // Draw bars with better spacing
  svg.selectAll("rect")
    .data(bins)
    .enter()
    .append("rect")
    .attr("x", d => x(d.x0 || 0))
    .attr("y", d => y(d.length))
    .attr("width", d => {
      if (isConstantValue) {
        // For constant values, use a fixed reasonable width
        return Math.max(20, width / 10)
      } else {
        const w = x(d.x1 || 0) - x(d.x0 || 0) - 1
        return Math.max(1, Math.min(w, width / (bins.length || 1))) // Ensure reasonable bar width
      }
    })
    .attr("height", d => height - y(d.length))
    .style("fill", "#3b82f6")
    .style("opacity", 0.7)
    .style("stroke", "#1e40af")
    .style("stroke-width", 0.5)
  
  // Format axis labels appropriately for small values
  const formatTick = (d: number) => {
    if (Math.abs(d) < 0.001) return d === 0 ? '0' : '< 0.001'
    if (Math.abs(d) < 0.01) return d.toFixed(4)
    if (Math.abs(d) < 1) return d.toFixed(3)
    return d.toFixed(2)
  }
  
  // X-axis with custom formatting
  const xAxis = d3.axisBottom(x)
    .tickFormat(formatTick)
  
  if (isConstantValue) {
    // For constant values, show fewer ticks centered around the value
    xAxis.ticks(3)
  } else {
    xAxis.ticks(Math.min(8, (bins.length || 20) / 2)) // Limit number of ticks
  }
  
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(xAxis)
    .selectAll("text")
    .style("font-size", "11px")
    .attr("transform", "rotate(-45)")
    .style("text-anchor", "end")
  
  // Y-axis
  svg.append("g")
    .call(d3.axisLeft(y).ticks(6))
    .selectAll("text")
    .style("font-size", "11px")
  
  // Add axis labels
  svg.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - (height / 2))
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "12px")
    .style("fill", "#666")
    .text("Frequency")
  
  svg.append("text")
    .attr("transform", `translate(${width / 2}, ${height + margin.bottom - 5})`)
    .style("text-anchor", "middle")
    .style("font-size", "12px")
    .style("fill", "#666")
    .text(computedFeatureNames.value[actualFeatureIndex] || `Feature ${actualFeatureIndex + 1}`)
  
  // Add summary statistics as text
  const valuesCopy = [...values] // Don't modify original array
  const mean = valuesCopy.reduce((sum, val) => sum + val, 0) / valuesCopy.length
  const median = valuesCopy.sort((a, b) => a - b)[Math.floor(valuesCopy.length / 2)]
  
  if (isConstantValue) {
    // Special text for constant values
    svg.append("text")
      .attr("x", width - 5)
      .attr("y", 15)
      .style("text-anchor", "end")
      .style("font-size", "10px")
      .style("fill", "#666")
      .text(`All values: ${formatTick(mean)}`)
    
    svg.append("text")
      .attr("x", width - 5)
      .attr("y", 28)
      .style("text-anchor", "end")
      .style("font-size", "10px")
      .style("fill", "#666")
      .text(`Count: ${values.length}`)
  } else {
    // Normal statistics
    svg.append("text")
      .attr("x", width - 5)
      .attr("y", 15)
      .style("text-anchor", "end")
      .style("font-size", "10px")
      .style("fill", "#666")
      .text(`Mean: ${formatTick(mean)}`)
    
    svg.append("text")
      .attr("x", width - 5)
      .attr("y", 28)
      .style("text-anchor", "end")
      .style("font-size", "10px")
      .style("fill", "#666")
      .text(`Median: ${formatTick(median)}`)
  }
  
  console.log(`[DataExplorer] Distribution rendered successfully for feature ${actualFeatureIndex} (isConstantValue: ${isConstantValue})`)
}

// Utility functions
const formatNumber = (value: any): string => {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value === 'string') {
    // Handle string values that might be categorical
    if (value === 'N/A' || value === 'null' || value === 'undefined' || value === '') return 'N/A'
    // Try to convert to number
    const numValue = parseFloat(value)
    if (isNaN(numValue)) return value // Return original string if can't be converted
    value = numValue
  }
  if (typeof value === 'number') {
    if (isNaN(value)) return 'N/A'
    if (Math.abs(value) < 0.001) return '< 0.001'
    return value.toFixed(3)
  }
  // For any other type, return as string
  return String(value)
}

const getQualityClass = (value: number): string => {
  if (value >= 0.95) return 'excellent'
  if (value >= 0.85) return 'good'
  if (value >= 0.7) return 'fair'
  return 'poor'
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

  // Initialize data - first check for active run
  const activeRun = globalState.activeRun.value
  if (activeRun) {
    console.log('[DataExplorer] Initializing with active run:', activeRun.dataset)
    if (activeRun.dataset && activeRun.dataset.includes('Uploaded')) {
      const fileName = activeRun.dataset.replace(' (Uploaded)', '')
      selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + fileName
      uploadedFileName.value = fileName
    }
  } else {
    // Initialize data from global state
    const currentDataset = globalState.currentDataset.value
    if (currentDataset) {
      if (currentDataset.type === 'sample') {
        selectedSample.value = currentDataset.sampleName || currentDataset.name.toLowerCase()
        uploadedData.value = null
        uploadedFileName.value = null
      } else if (currentDataset.type === 'uploaded' && currentDataset.data) {
        uploadedData.value = currentDataset.data.map(row => [...row])
        uploadedFileName.value = currentDataset.fileName || currentDataset.name
        selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + (currentDataset.fileName || currentDataset.name)
      }
    } else {
      // Fallback to default sample if no global dataset
      selectedSample.value = 'blobs'
    }
  }
  
  // Force data generation and UI update
  console.log('[DataExplorer] onMounted - calling updateCurrentData')
  await updateCurrentData()
})

// Watch for changes to the active run and auto-load (like clustering.vue)
watch(() => globalState.activeRun.value, async (newActiveRun, oldActiveRun) => {
  // Only process if the run actually changed
  if (newActiveRun?.id === oldActiveRun?.id) {
    return
  }
  
  console.log('DataExplorer: Active run changed from', oldActiveRun?.dataset, 'to', newActiveRun?.dataset);
  
  if (newActiveRun) {
    console.log('DataExplorer: Loading new active run:', newActiveRun.dataset, 'ID:', newActiveRun.id);
    
    // Handle uploaded datasets
    if (newActiveRun.dataset && newActiveRun.dataset.includes('Uploaded')) {
      const fileName = newActiveRun.dataset.replace(' (Uploaded)', '');
      selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + fileName;
      uploadedFileName.value = fileName;
    }
    
    // Update current data from active run
    await updateCurrentData();
  } else {
    // Clear data when no active run
    console.log('DataExplorer: No active run, clearing data');
    uploadedData.value = null;
    uploadedFileName.value = null;
    selectedSample.value = globalState.sampleOptions.value[0] || 'blobs';
    await updateCurrentData();
  }
}, { immediate: false });

// Watch for global dataset changes
watch(() => globalState.currentDataset.value, async (newDataset) => {
  if (newDataset) {
    console.log('DataExplorer: Global dataset changed:', newDataset.type, newDataset.name);
    
    if (newDataset.type === 'sample') {
      selectedSample.value = newDataset.sampleName || newDataset.name.toLowerCase()
      uploadedData.value = null
      uploadedFileName.value = null
    } else if (newDataset.type === 'uploaded' || newDataset.type === 'imported') {
      uploadedFileName.value = newDataset.fileName || newDataset.name
      selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + (newDataset.fileName || newDataset.name)
      
      // For uploaded/imported datasets, use the data directly if available
      if (newDataset.data && newDataset.data.length > 0) {
        uploadedData.value = newDataset.data.map(row => [...row])
      } else {
        uploadedData.value = null
      }
    }
    
    await updateCurrentData()
    
    // Force a complete refresh of the data explorer
    nextTick(async () => {
      updateAvailableFeatures()
      await updateFeatureSelection()
      console.log('DataExplorer: Dataset changed, forcing complete refresh')
    })
  }
}, { immediate: true })

// Watch for distribution feature changes
// Only watch for changes after initial mount, not on initial feature selection
let distributionWatcherInitialized = false
watch(selectedDistributionFeature, () => {
  if (distributionWatcherInitialized) {
    nextTick(async () => await renderDistribution())
  }
})
onMounted(() => {
  distributionWatcherInitialized = true
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
@import '~/assets/css/pages/data-explorer.css';
</style>

