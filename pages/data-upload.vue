<template>
  <AppLayout :showSidebar="false">
    <template #default>
      <div class="data-upload-page">
        <div class="container">
          <!-- Header -->
          <div class="page-header">
            <button @click="handleBack" class="back-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15,18 9,12 15,6"></polyline>
              </svg>
              Back
            </button>
            <div class="header-content">
              <h1 v-if="isReturningUser">Change Your Data</h1>
              <h1 v-else>Select Your Data</h1>
              <p v-if="isReturningUser">Choose new sample data or upload a different dataset. Your current parameters will be preserved.</p>
              <p v-else>Choose sample data or upload your own dataset to begin clustering analysis</p>
            </div>
          </div>

          <!-- Current Dataset (if exists) -->
          <div v-if="currentDataset && !changingData" class="current-dataset-display">
            <div class="dataset-card">
              <div class="dataset-header">
                <div class="dataset-icon">✅</div>
                <div class="dataset-info">
                  <h3>{{ currentDataset.name }}</h3>
                  <p>{{ currentDataset.type === 'sample' ? 'Sample Dataset' : (currentDataset.type === 'imported' ? 'Imported Dataset' : 'Uploaded File') }}</p>
                  <div class="dataset-stats">
                    <span v-if="currentDataset.pointCount">{{ currentDataset.pointCount.toLocaleString() }} points</span>
                    <span v-if="currentDataset.featureCount">{{ currentDataset.featureCount }} features</span>
                  </div>
                </div>
              </div>
              <div class="dataset-actions">
                <button @click="proceedToClustering" class="primary-btn large">
                  Continue to Analysis →
                </button>
                <button @click="changingData = true" class="secondary-btn">
                  Change Data
                </button>
                <button v-if="isReturningUser" @click="startFreshAnalysis" class="tertiary-btn">
                  Start Fresh (Reset All)
                </button>
              </div>
            </div>
          </div>

          <!-- Data Selection -->
          <div v-if="!currentDataset || changingData" class="data-selection">
            
            <!-- File Upload Section -->
            <div class="selection-section">
              <div class="section-header">
                <h2>📁 Upload Your Data</h2>
                <p>CSV or Excel files with automatic preprocessing</p>
              </div>
              
              <!-- Simple Upload Area -->
              <div class="upload-zone" 
                   :class="{ 'drag-over': isDragOver, 'has-file': uploadedFile, 'processing': isProcessing }"
                   @click="!isProcessing && triggerFileInput()" 
                   @dragover.prevent="isDragOver = true"
                   @dragleave.prevent="isDragOver = false"
                   @drop.prevent="handleFileDrop">
                
                <input ref="fileInput" type="file" accept=".csv,.xlsx,.xls" @change="handleFileSelect" style="display: none">
                
                <div v-if="!uploadedFile && !isProcessing" class="upload-placeholder">
                  <div class="upload-icon">📤</div>
                  <h3>Drop your file here or click to browse</h3>
                  <p>Supports CSV, Excel files up to 100MB</p>
                </div>
                
                <div v-if="uploadedFile && !isProcessing" class="file-preview">
                  <div class="file-icon">📄</div>
                  <div class="file-info">
                    <h4>{{ uploadedFile.name }}</h4>
                    <p>{{ formatFileSize(uploadedFile.size) }}</p>
                    <div v-if="fileStats" class="file-details">
                      <span>{{ fileStats.rows.toLocaleString() }} rows</span>
                      <span>{{ fileStats.columns }} columns</span>
                      <span v-if="fileStats.missingValues > 0" class="warning">{{ fileStats.missingValues }} missing</span>
                    </div>
                  </div>
                  <button @click.stop="removeFile" class="remove-btn">✕</button>
                </div>
                
                <div v-if="isProcessing" class="processing-state">
                  <div class="spinner"></div>
                  <h4>Processing {{ uploadedFile?.name }}</h4>
                  <p>{{ currentProcessingStage }}</p>
                </div>
              </div>
              
              <!-- File Options -->
              <div v-if="uploadedFile && !isProcessing" class="file-options">
                <div class="options-grid">
                  <div class="option-group">
                    <label class="option-label">
                      <input type="checkbox" v-model="hasHeaders">
                      First row contains headers
                    </label>
                  </div>
                  
                  <div v-if="fileStats?.missingValues > 0" class="option-group">
                    <label>Missing values ({{ fileStats.missingValues }} detected):</label>
                    <select v-model="missingValueStrategy" class="select-input">
                      <option value="keep">Keep as is</option>
                      <option value="remove">Remove rows with missing values</option>
                      <option value="fill_mean">Fill with column mean</option>
                    </select>
                  </div>
                </div>
                
                <!-- Data Preview -->
                <div v-if="previewData.length > 0" class="data-preview">
                  <div class="preview-header">
                    <h4>Data Preview (First 5 rows)</h4>
                  </div>
                  
                  <div class="preview-container">
                    <div class="preview-table">
                      <table>
                        <thead>
                          <tr>
                            <th v-for="(header, index) in previewHeaders" :key="index">{{ header }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, rowIndex) in previewData.slice(0, 5)" :key="rowIndex">
                            <td v-for="(cell, cellIndex) in row" :key="cellIndex" 
                                :class="{ 'missing-value': cell === null || cell === undefined || cell === '' }">
                              {{ formatCell(cell) }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
                
                <!-- Basic Configuration Button -->
                <div class="basic-config-actions">
                  <button @click="showColumnConfiguration = true" class="secondary-btn large">
                    🔧 Configure Columns
                  </button>
                  <button @click="confirmFileUpload" class="primary-btn large">
                    Use Dataset as is →
                  </button>
                </div>
              </div>
              
              <!-- Enhanced Column Configuration -->
              <div v-if="showColumnConfiguration && uploadedFile && !isProcessing" class="column-configuration-section">
                <div class="config-header">
                  <h3>Configure Your Data Columns</h3>
                  <p>Select which columns to use as features and how to handle them</p>
                </div>
                
                <!-- Column Configuration Table -->
                <div class="column-config-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Column Name</th>
                        <th>Sample Values</th>
                        <th>Data Type</th>
                        <th>Missing Values</th>
                        <th>Usage</th>
                        <th>Normalize</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(col, index) in columnConfigs" :key="index" :class="{ 'categorical-row': col.isCategorical }">
                        <td>
                          <strong>{{ col.name }}</strong>
                        </td>
                        <td class="sample-values">
                          {{ formatSampleValues(col.samples) }}
                        </td>
                        <td>
                          <span class="data-type-badge" :class="col.dataType">
                            {{ getDataTypeLabel(col.dataType) }}
                          </span>
                        </td>
                        <td class="missing-count">
                          <span v-if="col.missingCount > 0" class="missing-badge">
                            {{ col.missingCount }}
                          </span>
                          <span v-else class="no-missing">✓</span>
                        </td>
                        <td>
                          <select v-model="col.usage" class="usage-select">
                            <option value="feature">Feature</option>
                            <option value="label">Label/Target</option>
                            <option value="ignore">Ignore</option>
                          </select>
                        </td>
                        <td>
                          <label v-if="col.usage === 'feature' && !col.isCategorical" class="normalize-checkbox">
                            <input type="checkbox" v-model="col.normalize">
                            <span>Normalize</span>
                          </label>
                          <span v-else class="not-applicable">N/A</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                
                <!-- Bulk Actions -->
                <div class="bulk-actions">
                  <button @click="selectAllAsFeatures" class="btn-secondary">All as Features</button>
                  <button @click="selectOnlyNumericAsFeatures" class="btn-secondary">Numeric as Features</button>
                  <button @click="clearAllSelections" class="btn-secondary">Clear All</button>
                </div>
                
                
                <!-- Configuration Actions -->
                <div class="config-actions">
                  <button @click="showColumnConfiguration = false" class="secondary-btn">
                    Back to Basic Settings
                  </button>
                  <button @click="confirmFileUploadWithConfig" class="primary-btn large" :disabled="featureColumnCount === 0">
                    Use Configured Data →
                  </button>
                </div>
              </div>
            </div>

            <!-- Sample Data Section -->
            <div class="selection-section">
              <div class="section-header">
                <h2>🎯 Sample Datasets</h2>
                <p>Quick start with pre-built datasets organized by type and complexity</p>
              </div>

              <!-- Study Datasets -->
              <div v-if="sampleOptionsByCategory.study?.length" class="dataset-category">
                <h3 class="category-title">
                  Study Datasets
                </h3>
                <div class="sample-grid">
                  <div
                    v-for="sample in sampleOptionsByCategory.study"
                    :key="sample.value"
                    class="sample-card study-card"
                    :class="{ active: selectedSample === sample.value }"
                    @click="selectSample(sample.value)"
                  >
                    <h4>{{ sample.label }}</h4>
                    <div class="dataset-stats">
                      <span>{{ sample.typical_samples.toLocaleString() }} samples</span>
                      <span>{{ sample.dimensions }} features</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 2D Synthetic Datasets -->
              <div class="dataset-category">
                <h3 class="category-title">
                  <span class="category-icon">📊</span>
                  2D Synthetic Datasets
                  <span class="category-description">Perfect for visualization and basic clustering</span>
                </h3>
                <div class="sample-grid">
                  <div 
                    v-for="sample in sampleOptionsByCategory.synthetic_2d" 
                    :key="sample.value"
                    class="sample-card"
                    :class="{ active: selectedSample === sample.value }"
                    @click="selectSample(sample.value)"
                  >
                    <div class="card-header">
                      <div class="title-with-icon">
                        <span class="dataset-icon">{{ getDatasetIcon(sample.value) }}</span>
                        <h4>{{ sample.label }}</h4>
                      </div>
                      <div class="badges">
                        <span class="difficulty-badge" :class="sample.difficulty">{{ sample.difficulty }}</span>
                        <span class="dimension-badge">{{ sample.dimensions }}D</span>
                        <span v-if="sample.requiresDownload" class="download-badge">📥 Download</span>
                      </div>
                    </div>
                    <p class="description">{{ sample.description }}</p>
                    <div class="dataset-stats">
                      <span>{{ sample.typical_samples.toLocaleString() }} samples typical</span>
                    </div>
                  </div>
                </div>
              </div>


              <!-- Real-World Datasets -->
              <div class="dataset-category">
                <h3 class="category-title">
                  <span class="category-icon">🌍</span>
                  Real-World Datasets
                  <span class="category-description">Classic machine learning datasets for realistic testing</span>
                </h3>
                <div class="sample-grid">
                  <div 
                    v-for="sample in sampleOptionsByCategory.real_world" 
                    :key="sample.value"
                    class="sample-card real-world"
                    :class="{ active: selectedSample === sample.value }"
                    @click="selectSample(sample.value)"
                  >
                    <div class="card-header">
                      <div class="title-with-icon">
                        <span class="dataset-icon">{{ getDatasetIcon(sample.value) }}</span>
                        <h4>{{ sample.label }}</h4>
                      </div>
                      <div class="badges">
                        <span class="difficulty-badge" :class="sample.difficulty">{{ sample.difficulty }}</span>
                        <span class="dimension-badge">{{ sample.dimensions }}D</span>
                        <span class="real-badge">Real Data</span>
                        <span v-if="sample.requiresDownload" class="download-badge">📥 Download</span>
                      </div>
                    </div>
                    <p class="description">{{ sample.description }}</p>
                    <div class="dataset-stats">
                      <span>{{ sample.typical_samples.toLocaleString() }} samples fixed</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Enhanced Sample Configuration -->
              <div v-if="selectedSample && selectedSampleInfo" class="sample-config enhanced">
                <div class="config-header">
                  <h4>Configure {{ selectedSampleInfo.label }} Dataset</h4>
                  <div class="selected-info">
                    <span class="difficulty-badge" :class="selectedSampleInfo.difficulty">{{ selectedSampleInfo.difficulty }}</span>
                    <span class="dimension-badge">{{ selectedSampleInfo.dimensions }}D</span>
                  </div>
                </div>
                
                <div class="config-grid">
                  <!-- Sample Size Configuration -->
                  <div class="config-row">
                    <label>Number of data points:</label>
                    <div class="slider-group">
                      <input 
                        type="range" 
                        :min="selectedSampleInfo.category === 'real_world' ? selectedSampleInfo.typical_samples : 50" 
                        :max="selectedSampleInfo.category === 'real_world' ? selectedSampleInfo.typical_samples : 10000" 
                        :step="getStepSize()"
                        v-model.number="n_samples"
                        class="slider"
                        :disabled="selectedSampleInfo.category === 'real_world' || selectedSampleInfo.category === 'study'"
                      />
                      <div class="value-controls">
                        <span class="slider-value">
                          {{ n_samples.toLocaleString() }}
                          <span v-if="selectedSampleInfo.category === 'real_world'" class="fixed-note">(fixed size)</span>
                          <span v-if="selectedSampleInfo.category === 'study'" class="fixed-note">(fixed size)</span>
                        </span>
                        <input 
                          v-if="selectedSampleInfo.category !== 'real_world' || selectedSampleInfo.category !== 'study'"
                          type="number" 
                          v-model.number="n_samples"
                          :min="50"
                          :max="10000"
                          class="direct-input"
                          placeholder="Enter size"
                        />
                      </div>
                    </div>
                  </div>

                  <!-- Dimensions Configuration for High-D datasets -->
                  <div v-if="selectedSampleInfo.supports_custom_dims" class="config-row">
                    <label>Number of features/dimensions:</label>
                    <div class="slider-group">
                      <input 
                        type="range" 
                        :min="selectedSampleInfo.dimensions" 
                        :max="selectedSampleInfo.max_dims || 50" 
                        step="1"
                        v-model.number="n_features"
                        class="slider"
                      />
                      <span class="slider-value">{{ n_features || selectedSampleInfo.dimensions }}D</span>
                    </div>
                  </div>
                </div>

                <div class="config-description">
                  <p><strong>About this dataset:</strong> {{ selectedSampleInfo.description }}</p>
                  <p v-if="selectedSampleInfo.category === 'real_world'">
                    <em>Real-world datasets have fixed sizes and are automatically normalized.</em>
                  </p>
                  <p v-if="selectedSampleInfo.category === 'study'">
                    <em>Study datasets have fixed sizes and are automatically normalized.</em>
                  </p>
                </div>

                <button @click="confirmSampleData" class="primary-btn large">
                  Use {{ selectedSampleInfo.label }} Dataset
                  <span class="config-preview">
                    ({{ n_samples.toLocaleString() }} samples, {{ n_features || selectedSampleInfo.dimensions }} features)
                  </span>
                </button>
              </div>
            </div>
            
            <!-- Cancel when changing existing data -->
            <div v-if="changingData" class="change-actions">
              <button @click="changingData = false" class="secondary-btn">
                Cancel - Keep Current Data
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, shallowRef, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppLayout from '~/components/AppLayout.vue'
import { useGlobalState } from '~/composables/useGlobalState'
import { useFileUpload } from '~/composables/useFileUpload'
import { useColumnConfiguration } from '~/composables/useColumnConfiguration'
import { useFileUploadAPI } from '~/composables/useFileUploadAPI'
import type { DataProcessingConfig } from '~/composables/useFileUploadAPI'
import FileUploadWidget from '~/components/FileUploadWidget.vue'

const router = useRouter()
const route = useRoute()
const globalState = useGlobalState()
const { handleFileUpload, handleFileUploadEnhanced, detectColumnTypes, USE_BACKEND_PROCESSING } = useFileUpload()
const { initializeColumnConfig } = useColumnConfiguration()
const fileUploadAPI = useFileUploadAPI()

// Enhanced sample options with categories
const sampleOptions = computed(() => globalState.sampleOptions.value)
const sampleOptionsByCategory = computed(() => globalState.sampleOptionsByCategory.value)

// State
const currentDataset = computed(() => globalState.currentDataset.value)
const changingData = ref(false)
const isReturningUser = computed(() => globalState.isOnboardingCompleted.value)

// Backend preview state
const useBackendPreview = ref(false)
const backendPreviewData = shallowRef<any[][]>([])
const backendPreviewHeaders = shallowRef<string[]>([])
const backendPreviewLoading = ref(false)

// Sample data state
const selectedSample = ref<string | null>(null)
const n_samples = ref(1000)
const n_features = ref<number | null>(null)

// Get selected sample info
const selectedSampleInfo = computed(() => {
  if (!selectedSample.value) return null
  return globalState.getSampleOption(selectedSample.value)
})

// Get appropriate step size based on current sample size
const getStepSize = () => {
  if (n_samples.value <= 1000) return 50
  if (n_samples.value <= 10000) return 100
  if (n_samples.value <= 100000) return 1000
  return 10000
}

// Dataset icon mapping function
const getDatasetIcon = (datasetType: string): string => {
  const iconMap: Record<string, string> = {
    // 2D Synthetic Datasets
    'blobs': '🟡',
    'moons': '🌙',
    'circles': '⭕',
    'aniso': '🔷',
    'varied': '🔵',
    'spiral': '🌀',
    
    // High-Dimensional Datasets
    'blobs_nd': '🌌',  // Cosmic web simulation
    'classification_nd': '🧬',  // Gene expression network
    'sparse_clusters': '⚛️',  // Quantum state manifold
    'hypercube': '💎',  // Crystalline lattice
    'swiss_roll_3d': '🧬',  // Protein folding space
    'neural_embedding': '🤖',  // Neural network embedding
    
    // Real-World Datasets
    'iris': '🌸',
    'wine': '🍷',
    'breast_cancer': '🏥',
    'digits_small': '🔢',
    'coil20': '📷',
    'olivetti_faces': '👤',
    'digits_full': '🔟',
    'california_housing': '🏠',
    'diabetes': '💉',
    'palmer_penguins': '🐧'
  }
  
  return iconMap[datasetType] || '📊'
}

// File upload state
const uploadedFile = ref<File | null>(null)
const fileStats = ref<any>(null)
const isProcessing = ref(false)
const isDragOver = ref(false)
const currentProcessingStage = ref('')
const fileInput = ref<HTMLInputElement>()
const uploadResult = shallowRef<any>(null)

// File options
const hasHeaders = ref(true)
const missingValueStrategy = ref('keep')
const normalization = ref('standard')

// Preview data
const previewData = shallowRef<any[][]>([])
const previewHeaders = shallowRef<string[]>([])

// Column configuration
const showColumnConfiguration = ref(false)
const columnConfigs = shallowRef<ColumnConfig[]>([])

// Column configuration interface
interface ColumnConfig {
  name: string
  samples: any[]
  dataType: string
  isCategorical: boolean
  missingCount: number
  usage: 'feature' | 'label' | 'ignore'
  normalize: boolean
}

// Computed properties for column configuration
const featureColumnCount = computed(() => 
  columnConfigs.value.filter(col => col.usage === 'feature').length
)

const labelColumnCount = computed(() => 
  columnConfigs.value.filter(col => col.usage === 'label').length
)

const ignoredColumnCount = computed(() => 
  columnConfigs.value.filter(col => col.usage === 'ignore').length
)

const normalizedColumnCount = computed(() => 
  columnConfigs.value.filter(col => col.usage === 'feature' && col.normalize && !col.isCategorical).length
)



// Helper to check if any columns have specific normalization settings
const hasColumnSpecificNormalization = (): boolean => {
  return columnConfigs.value.some(col => col.normalize && col.usage === 'feature' && !col.isCategorical)
}

// Simple missing value detection
const isMissingValue = (cell: any): boolean => {
  return cell === null || cell === undefined || cell === '' || cell === 'null' || cell === 'N/A' || cell === 'nan'
}

// Backend preview function for accurate processing results
const getBackendPreview = async () => {
  if (!uploadedFile.value) return

  try {
    backendPreviewLoading.value = true
    
    // Get the file upload result to get fileId
    const result = await handleFileUploadEnhanced(uploadedFile.value)
    
    if (!result.fileId) {
      throw new Error('No file ID available for backend preview')
    }
    
    // Get feature and label column information from current column configuration
    const featureColumns = columnConfigs.value
      .map((col, index) => col.usage === 'feature' ? index : -1)
      .filter(index => index !== -1)
    
    const labelColumns = columnConfigs.value
      .map((col, index) => col.usage === 'label' ? index : -1)
      .filter(index => index !== -1)
    
    const ignoredColumns = columnConfigs.value
      .map((col, index) => col.usage === 'ignore' ? index : -1)
      .filter(index => index !== -1)
    
    // Determine categorical encoding based on whether we have categorical features
    const hasCategoricalFeatures = columnConfigs.value.some(col => 
      col.isCategorical && col.usage === 'feature'
    )
    const categoricalEncoding = hasCategoricalFeatures ? 'label' : 'none'
    
    // Create backend processing configuration
    const processingConfig = {
      missing_value_strategy: missingValueStrategy.value as any,
      normalization: normalization.value as any,
      categorical_encoding: categoricalEncoding as 'none' | 'label' | 'onehot',
      feature_columns: featureColumns,
      label_columns: labelColumns,
      ignored_columns: ignoredColumns,
      columns: columnConfigs.value.map((col, index) => ({
        name: col.name,
        index: index,
        data_type: col.dataType as any,
        usage: col.usage,
        normalize: col.normalize,
        is_categorical: col.isCategorical
      }))
    }
    
    // Get backend processed preview
    const previewResult = await fileUploadAPI.getProcessedPreview(result.fileId, processingConfig)
    
    // Update backend preview state
    backendPreviewData.value = previewResult.data
    
    // Preserve original column names for feature columns
    const originalHeaders = previewHeaders.value || []
    backendPreviewHeaders.value = featureColumns.map(colIndex => 
      originalHeaders[colIndex] || `Column_${colIndex + 1}`
    )
    
    useBackendPreview.value = true
    
  } catch (error) {
    console.error('Backend preview error:', error)
    useBackendPreview.value = false
  } finally {
    backendPreviewLoading.value = false
  }
}

// Helper functions for preview processing
const applyMissingValuePreview = (data: any[][], strategy: string): any[][] => {
  if (strategy === 'keep') return data
  
  const processed = data.map(row => [...row])
  
  if (strategy === 'remove') {
    // Remove rows with any missing values (excluding European numbers)
    return processed.filter(row => !row.some(cell => isMissingValue(cell)))
  }
  
  if (strategy === 'fill_mean' || strategy === 'fill_median') {
    // Calculate mean/median for numeric columns
    const stats = calculateColumnStats(processed)
    processed.forEach(row => {
      row.forEach((cell, colIndex) => {
        if (isMissingValue(cell)) {
          const stat = stats[colIndex]
          if (stat && stat.isNumeric) {
            row[colIndex] = strategy === 'fill_mean' ? stat.mean : stat.median
          } else if (stat && stat.mode !== null) {
            row[colIndex] = stat.mode
          }
        }
      })
    })
  }
  
  if (strategy === 'fill_zero') {
    processed.forEach(row => {
      row.forEach((cell, colIndex) => {
        if (isMissingValue(cell)) {
          row[colIndex] = 0
        }
      })
    })
  }
  
  return processed
}

const applyNormalizationPreview = (data: any[][], method: string): any[][] => {
  if (method === 'none' && !hasColumnSpecificNormalization()) return data
  
  const processed = data.map(row => [...row])
  const stats = calculateColumnStats(processed)
  
  processed.forEach(row => {
    row.forEach((cell, colIndex) => {
      const stat = stats[colIndex]
      if (stat && stat.isNumeric && typeof cell === 'number') {
        // Check if this column should be normalized
        let shouldNormalize = false
        
        if (columnConfigs.value.length > 0 && colIndex < columnConfigs.value.length) {
          const config = columnConfigs.value[colIndex]
          shouldNormalize = config.normalize && config.usage === 'feature' && !config.isCategorical
        } else if (method !== 'none') {
          // Fall back to global normalization setting
          shouldNormalize = true
        }
        
        if (shouldNormalize) {
          const normMethod = method || 'standard'
          if (normMethod === 'standard' && stat.std > 0) {
            row[colIndex] = (cell - stat.mean) / stat.std
          } else if (normMethod === 'minmax' && stat.max !== stat.min) {
            row[colIndex] = (cell - stat.min) / (stat.max - stat.min)
          }
        }
      }
    })
  })
  
  return processed
}

const calculateColumnStats = (data: any[][]) => {
  if (data.length === 0) return []
  
  const stats = []
  const columnCount = data[0].length
  
  for (let colIndex = 0; colIndex < columnCount; colIndex++) {
    const values = data.map(row => row[colIndex]).filter(val => !isMissingValue(val))
    const numericValues = values.map(val => parseFloat(val)).filter(val => !isNaN(val))
    
    const isNumeric = numericValues.length > 0
    let mean = 0, median = 0, min = 0, max = 0, std = 0, mode = null
    
    if (isNumeric) {
      mean = numericValues.reduce((sum, val) => sum + val, 0) / numericValues.length
      std = Math.sqrt(numericValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / numericValues.length)
      min = Math.min(...numericValues)
      max = Math.max(...numericValues)
      
      const sorted = [...numericValues].sort((a, b) => a - b)
      median = sorted.length % 2 === 0 
        ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
        : sorted[Math.floor(sorted.length / 2)]
    }
    
    // Calculate mode for non-numeric data
    if (!isNumeric && values.length > 0) {
      const frequency: Record<any, number> = {}
      values.forEach(val => frequency[val] = (frequency[val] || 0) + 1)
      mode = Object.keys(frequency).reduce((a, b) => frequency[a] > frequency[b] ? a : b)
    }
    
    stats[colIndex] = { isNumeric, mean, median, min, max, std, mode }
  }
  
  return stats
}

const detectMissingValueChanges = (original: any[][], processed: any[][]): any => {
  const originalMissing = countMissingInData(original)
  const processedMissing = countMissingInData(processed)
  return {
    before: originalMissing,
    after: processedMissing,
    rowsRemoved: original.length - processed.length
  }
}

const detectNormalizationChanges = (original: any[][], processed: any[][]): any => {
  const changes = []
  if (original.length > 0 && processed.length > 0) {
    for (let colIndex = 0; colIndex < original[0].length; colIndex++) {
      const originalValues = original.map(row => row[colIndex]).filter(val => typeof val === 'number')
      const processedValues = processed.map(row => row[colIndex]).filter(val => typeof val === 'number')
      
      if (originalValues.length > 0 && processedValues.length > 0) {
        const originalMean = originalValues.reduce((sum, val) => sum + val, 0) / originalValues.length
        const processedMean = processedValues.reduce((sum, val) => sum + val, 0) / processedValues.length
        
        if (Math.abs(originalMean - processedMean) > 0.0001) {
          changes.push({
            column: colIndex,
            originalMean: originalMean.toFixed(3),
            processedMean: processedMean.toFixed(3)
          })
        }
      }
    }
  }
  return changes
}

const countMissingInData = (data: any[][]): number => {
  return data.reduce((total, row) => {
    return total + row.reduce((rowTotal, cell) => {
      return rowTotal + (isMissingValue(cell) ? 1 : 0)
    }, 0)
  }, 0)
}

// Categorical encoding preview
const applyCategoricalEncodingPreview = (data: any[][]): any[][] => {
  if (columnConfigs.value.length === 0) return data
  
  const processed = data.map(row => [...row])
  
  // Get feature column indices (after column filtering has been applied)
  const featureIndices = columnConfigs.value
    .map((config, index) => config.usage === 'feature' ? index : -1)
    .filter(index => index !== -1)
  
  // Build mapping from original column index to position in filtered data
  const originalToFilteredMap = new Map()
  featureIndices.forEach((originalIndex, filteredIndex) => {
    originalToFilteredMap.set(originalIndex, filteredIndex)
  })
  
  // Process each categorical column that is a feature
  columnConfigs.value.forEach((config, originalColIndex) => {
    // Only encode if it's categorical AND a feature column AND present in filtered data
    if (config.isCategorical && config.usage === 'feature' && originalToFilteredMap.has(originalColIndex)) {
      const filteredColIndex = originalToFilteredMap.get(originalColIndex)
      
      if (filteredColIndex < processed[0]?.length) {
        // Apply simple label encoding for preview (just convert to numbers)
        const uniqueValues = [...new Set(processed.map(row => row[filteredColIndex]))]
          .filter(val => val !== null && val !== undefined && val !== '')
        
        // Sort values for consistent encoding
        uniqueValues.sort()
        
        const valueMap = {}
        uniqueValues.forEach((val, idx) => {
          valueMap[val] = idx
        })
        
        console.log(`[applyCategoricalEncodingPreview] Encoding column ${originalColIndex} (position ${filteredColIndex}):`, valueMap)
        
        processed.forEach(row => {
          if (row[filteredColIndex] !== null && row[filteredColIndex] !== undefined && row[filteredColIndex] !== '') {
            const originalValue = row[filteredColIndex]
            const encodedValue = valueMap[originalValue]
            if (encodedValue !== undefined) {
              row[filteredColIndex] = encodedValue
            }
          }
        })
      }
    }
  })
  
  return processed
}

// Column filtering preview (show only feature columns)
const applyColumnFilteringPreview = (data: any[][]): any[][] => {
  if (columnConfigs.value.length === 0) return data
  
  const featureIndices = columnConfigs.value
    .map((config, index) => config.usage === 'feature' ? index : -1)
    .filter(index => index !== -1)
  
  if (featureIndices.length === 0) return data
  
  return data.map(row => featureIndices.map(idx => row[idx] || null))
}

// Detect categorical encoding changes
const detectCategoricalChanges = (original: any[][], processed: any[][]): any => {
  const changes = []
  
  columnConfigs.value.forEach((config, colIndex) => {
    if (config.isCategorical && colIndex < original[0]?.length && colIndex < processed[0]?.length) {
      const originalValues = original.map(row => row[colIndex])
      const processedValues = processed.map(row => row[colIndex])
      
      const originalUnique = [...new Set(originalValues)].length
      const processedUnique = [...new Set(processedValues)].length
      
      if (originalUnique !== processedUnique) {
        changes.push({
          column: config.name,
          originalUnique,
          processedUnique,
          encoding: 'label'
        })
      }
    }
  })
  
  return changes
}

// Detect column filtering changes
const detectColumnFilteringChanges = (original: any[][], processed: any[][]): any => {
  const originalColumns = original[0]?.length || 0
  const processedColumns = processed[0]?.length || 0
  
  const featureCount = columnConfigs.value.filter(col => col.usage === 'feature').length
  const ignoredCount = columnConfigs.value.filter(col => col.usage === 'ignore').length
  const labelCount = columnConfigs.value.filter(col => col.usage === 'label').length
  
  return {
    originalColumns,
    processedColumns,
    featureCount,
    ignoredCount,
    labelCount,
    columnsRemoved: originalColumns - processedColumns
  }
}

// Methods
const handleBack = () => {
  const from = route.query.from as string
  if (from === 'onboarding') {
    router.push('/')
  } else if (from === 'clustering') {
    router.push('/clustering')
  } else {
    router.push('/')
  }
}

const startFreshAnalysis = () => {
  // Reset all onboarding and clustering state
  globalState.resetOnboardingState()
  globalState.clearDataset()
  globalState.clearClusteringParameters()
  
  // Redirect to index page to start fresh
  router.push('/')
}

const proceedToClustering = () => {
  const from = route.query.from as string
  if (from === 'onboarding') {
    // Signal that we're returning from data upload with data
    sessionStorage.setItem('returningFromDataUpload', 'true')
    sessionStorage.setItem('onboardingInProgress', 'true')
    sessionStorage.setItem('onboardingStep', 'parameters')
    
    // Preserve experience level if it was stored
    const experienceLevel = sessionStorage.getItem('onboardingExperienceLevel')
    if (experienceLevel) {
      sessionStorage.setItem('onboardingExperienceLevel', experienceLevel)
    }
    
    // Return to main page to continue onboarding
    router.push('/')
  } else {
    // For returning users, go directly back to clustering
    // The parameters are already set in global state
    router.push('/clustering')
  }
}

// Sample data methods
const selectSample = (sample: string) => {
  selectedSample.value = sample
  uploadedFile.value = null
  
  // Set default values when selecting a sample
  const sampleInfo = globalState.getSampleOption(sample)
  if (sampleInfo) {
    n_samples.value = sampleInfo.typical_samples
    n_features.value = sampleInfo.supports_custom_dims ? sampleInfo.dimensions : null
  }
  
  // Auto-scroll to configuration section
  nextTick(() => {
    const configElement = document.querySelector('.sample-config.enhanced')
    if (configElement) {
      configElement.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start',
        inline: 'nearest'
      })
    }
  })
}

// Known feature names for real-world sample datasets
const KNOWN_FEATURE_NAMES: Record<string, string[]> = {
  'palmer_penguins': [
    'bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g',
    'sex', 'island_Biscoe', 'island_Dream', 'island_Torgersen'
  ],
  'wheats': [
    'Area', 'Perimeter', 'Compactness', 'Kernel Length',
    'Kernel Width', 'Asymmetry Coeff.', 'Groove Length'
  ],
  'olive_oil': [
    'Palmitic', 'Palmitoleic', 'Stearic', 'Oleic',
    'Linoleic', 'Linolenic', 'Arachidic', 'Eicosenoic'
  ],
  'zoo': [
    'Hair', 'Feathers', 'Eggs', 'Milk', 'Airborne', 'Aquatic',
    'Predator', 'Toothed', 'Backbone', 'Breathes', 'Venomous',
    'Fins', 'Legs', 'Tail', 'Domestic', 'Catsize'
  ],
}

const confirmSampleData = () => {
  if (!selectedSample.value || !selectedSampleInfo.value) return

  const sample = selectedSampleInfo.value
  const dimensions = n_features.value || sample.dimensions
  const sampleName = selectedSample.value
  const headers = KNOWN_FEATURE_NAMES[sampleName] || Array.from({ length: dimensions }, (_, i) => `Feature ${i + 1}`)
  
  globalState.setDataset({
    name: sample.label,
    type: 'sample',
    sampleName: selectedSample.value,
    n_samples: n_samples.value,
    headers,
    featureCount: dimensions,
    // Enhanced metadata
    category: sample.category,
    difficulty: sample.difficulty,
    description: sample.description,
    // Pass n_features to backend if applicable
    n_features: dimensions > 2 ? dimensions : undefined
  })
  
  changingData.value = false
  proceedToClustering()
}

// File upload methods
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    processFile(target.files[0])
  }
}

const handleFileDrop = (event: DragEvent) => {
  isDragOver.value = false
  if (event.dataTransfer?.files && event.dataTransfer.files[0]) {
    processFile(event.dataTransfer.files[0])
  }
}

const processFile = async (file: File) => {
  uploadedFile.value = file
  isProcessing.value = true
  selectedSample.value = null
  
  try {
    currentProcessingStage.value = 'Reading file...'
    console.log('[data-upload.vue] About to call handleFileUploadEnhanced')
    console.log('[data-upload.vue] USE_BACKEND_PROCESSING:', USE_BACKEND_PROCESSING.value)
    const result = await handleFileUploadEnhanced(file)
    
    currentProcessingStage.value = 'Analyzing data...'
    uploadResult.value = result
    
    // Set up file stats
    fileStats.value = {
      rows: result.rowCount,
      columns: result.columnCount,
      missingValues: countMissingValues(result.data)
    }
    
    // Set up preview data with proper header handling
    setupPreview(result)
    
    // Set up column configuration
    setupColumnConfiguration(result)
    
    console.log('File processed successfully:', result)
  } catch (error) {
    console.error('Error processing file:', error)
    alert('Error processing file: ' + error)
    removeFile()
  } finally {
    isProcessing.value = false
  }
}

// Column configuration setup
const setupColumnConfiguration = (result: any) => {
  // Use the headers that were already correctly extracted by setupPreview
  let headers: string[] = []
  
  if (previewHeaders.value.length > 0) {
    // Use the already-correctly-extracted headers from setupPreview
    headers = previewHeaders.value.slice() // Create a copy
    console.log('[setupColumnConfiguration] Using headers from setupPreview:', headers)
  } else {
    // Fallback only if previewHeaders is empty (should rarely happen)
    console.log('[setupColumnConfiguration] Fallback: previewHeaders empty, generating defaults')
    headers = Array.from({ length: result.columnCount || 0 }, (_, i) => `Column ${i + 1}`)
  }
  
  // Use the data rows that correspond to the preview data (already processed by setupPreview)
  const dataRows = previewData.value.length > 0 ? previewData.value : (result.data || [])
  
  columnConfigs.value = headers.map((header: string, index: number) => {
    const columnData = dataRows.map((row: any[]) => row[index])
    const validValues = columnData.filter((v: any) => v !== null && v !== undefined && v !== '')
    const samples = validValues.slice(0, 3)
    
    // Detect data type
    const numericCount = validValues.filter((v: any) => !isNaN(Number(v))).length
    const numericRatio = validValues.length > 0 ? numericCount / validValues.length : 0
    const isCategorical = numericRatio < 0.8
    
    let dataType = 'mixed'
    if (isCategorical) {
      dataType = 'categorical'
    } else {
      const integerCount = validValues.filter((v: any) => Number.isInteger(Number(v))).length
      dataType = numericCount > 0 && integerCount / numericCount > 0.9 ? 'integer' : 'numeric'
    }
    
    // Count missing values
    const missingCount = columnData.filter((v: any) => 
      v === null || v === undefined || v === '' || v === 'null' || v === 'N/A'
    ).length
    
    return {
      name: header,
      samples,
      dataType,
      isCategorical,
      missingCount,
      usage: (!isCategorical && (dataType === 'numeric' || dataType === 'integer')) ? 'feature' as const : 'ignore' as const,
      normalize: !isCategorical && (dataType === 'numeric' || dataType === 'integer')
    }
  })
}

// Utility methods for column configuration
const formatSampleValues = (samples: any[]): string => {
  if (samples.length === 0) return 'No data'
  
  return samples.map(val => {
    if (val === null || val === undefined) return 'null'
    if (typeof val === 'string' && val.length > 15) {
      return val.substring(0, 15) + '...'
    }
    return String(val)
  }).join(', ')
}

const getDataTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'numeric': 'Number',
    'integer': 'Integer',
    'categorical': 'Text',
    'boolean': 'Boolean',
    'mixed': 'Mixed',
    'empty': 'Empty'
  }
  return labels[type] || type
}

// Bulk action methods
const selectAllAsFeatures = () => {
  columnConfigs.value = columnConfigs.value.map(col => ({
    ...col,
    usage: 'feature' as const
  }))
}

const selectOnlyNumericAsFeatures = () => {
  columnConfigs.value = columnConfigs.value.map(col => ({
    ...col,
    usage: (!col.isCategorical && (col.dataType === 'numeric' || col.dataType === 'integer')) 
      ? 'feature' as const 
      : 'ignore' as const
  }))
}

const clearAllSelections = () => {
  columnConfigs.value = columnConfigs.value.map(col => ({
    ...col,
    usage: 'ignore' as const,
    normalize: false
  }))
}

// Enhanced confirm upload with configuration - BACKEND PROCESSING
const confirmFileUploadWithConfig = async () => {
  if (!uploadedFile.value || !uploadResult.value) return
  
  try {
    isProcessing.value = true
    currentProcessingStage.value = 'Processing configured data with backend...'
    
    const result = uploadResult.value
    
    if (!result.fileId) {
      throw new Error('No file ID available for backend processing')
    }
    
    // Get feature and label column information from current column configuration
    const featureColumns = columnConfigs.value
      .map((col, index) => col.usage === 'feature' ? index : -1)
      .filter(index => index !== -1)
    
    const labelColumns = columnConfigs.value
      .map((col, index) => col.usage === 'label' ? index : -1)
      .filter(index => index !== -1)
    
    const groundTruthColumn = labelColumns.length > 0 ? labelColumns[0] : undefined
    const groundTruthColumnName = groundTruthColumn !== undefined
      ? columnConfigs.value[groundTruthColumn]?.name
      : undefined
    
    const ignoredColumns = columnConfigs.value
      .map((col, index) => col.usage === 'ignore' ? index : -1)
      .filter(index => index !== -1)
    
    // Determine categorical encoding based on whether we have categorical features
    const hasCategoricalFeatures = columnConfigs.value.some(col => 
      col.isCategorical && col.usage === 'feature'
    )
    const categoricalEncoding = hasCategoricalFeatures ? 'label' : 'none'
    
    // Create backend processing configuration
    const processingConfig: DataProcessingConfig = {
      missing_value_strategy: missingValueStrategy.value as any,
      normalization: normalization.value as any,
      categorical_encoding: categoricalEncoding as 'none' | 'label' | 'onehot',
      feature_columns: featureColumns,
      label_columns: labelColumns,
      ignored_columns: ignoredColumns,
      columns: columnConfigs.value.map((col, index) => ({
        name: col.name,
        index: index,
        data_type: col.dataType as any,
        usage: col.usage,
        normalize: col.normalize,
        is_categorical: col.isCategorical
      }))
    }
    
    console.log('Sending to backend for processing:', {
      fileId: result.fileId,
      processingConfig,
      featureColumns: featureColumns.length,
      missingValueStrategy: missingValueStrategy.value,
      normalization: normalization.value
    })
    
    // Process data with backend
    currentProcessingStage.value = 'Backend processing: missing values and normalization...'
    const processedResult = await fileUploadAPI.processData(result.fileId, processingConfig)
    
    console.log('Backend processing completed:', {
      originalShape: processedResult.processing_info.original_shape,
      processedShape: processedResult.processing_info.processed_shape,
      removedRows: processedResult.processing_info.removed_rows,
      missingStrategy: processedResult.processing_info.missing_strategy,
      normalization: processedResult.processing_info.normalization
    })
    
    // Create proper headers preserving original column names for features
    const originalHeaders = previewHeaders.value || []
    const featureHeadersPreserved = featureColumns.map(colIndex => 
      originalHeaders[colIndex] || `Column_${colIndex + 1}`
    )
    
    // Set dataset with backend-processed data but preserved headers
    globalState.setDataset({
      name: uploadedFile.value.name,
      type: 'uploaded',
      data: processedResult.data,
      fileName: uploadedFile.value.name,
      pointCount: processedResult.row_count,
      featureCount: processedResult.column_count,
      headers: featureHeadersPreserved,
      hasHeaders: hasHeaders.value,
      missingValueStrategy: missingValueStrategy.value,
      normalization: normalization.value,
      featureColumns,
      labelColumns,
      ignoredColumns,
      columnConfig: columnConfigs.value,
      dataConfig: {
        missingValueStrategy: missingValueStrategy.value,
        normalization: normalization.value,
        categoricalEncoding: processingConfig.categorical_encoding,
        columns: processingConfig.columns
      },
      fileId: result.fileId,  // This was already here, keeping it
      backendProcessed: true,
      processingInfo: processedResult.processing_info,
      groundTruthColumn,
      groundTruthColumnName
    })
    
    console.log('Dataset configured with backend processing:', {
      name: uploadedFile.value.name,
      rows: processedResult.row_count,
      features: processedResult.column_count,
      headers: processedResult.headers,
      backendProcessed: true,
      processingInfo: processedResult.processing_info
    })
    
    changingData.value = false
    proceedToClustering()
  } catch (error) {
    console.error('Error with backend processing:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
    alert(`Error processing file with backend: ${errorMessage}`)
  } finally {
    isProcessing.value = false
  }
}

const setupPreview = (processResult: any, overrideHasHeaders?: boolean) => {
  console.log('[setupPreview] Called with:', { 
    hasBackendMetadata: !!processResult.backendMetadata,
    hasHeaders: processResult.hasHeaders,
    dataLength: processResult.data?.length,
    overrideHasHeaders,
    firstRow: processResult.data?.[0]
  })
  
  // Determine if headers were detected (prefer explicit override, then backend result)
  const headersDetected = overrideHasHeaders !== undefined ? overrideHasHeaders : processResult.hasHeaders
  
  if (processResult.backendMetadata) {
    // Backend processing - headers are already extracted and provided separately
    // IMPORTANT: Backend data does NOT include header row - it's pure data
    console.log('[setupPreview] Backend processing detected')
    
    // DETAILED DEBUGGING: Let's see what backend actually returns
    console.log('[setupPreview] DEBUG - processResult.headers:', processResult.headers)
    console.log('[setupPreview] DEBUG - processResult.backendMetadata:', processResult.backendMetadata)
    console.log('[setupPreview] DEBUG - columnInfo:', processResult.backendMetadata.columnInfo)
    console.log('[setupPreview] DEBUG - columnInfo names:', 
      processResult.backendMetadata.columnInfo?.map((col: any, i: number) => 
        `[${i}]: "${col.name}" (${typeof col.name})`
      )
    )
    console.log('[setupPreview] DEBUG - processResult.data[0]:', processResult.data?.[0])
    console.log('[setupPreview] DEBUG - hasHeaders detected by backend:', processResult.hasHeaders)
    console.log('[setupPreview] DEBUG - hasHeaders UI checkbox:', hasHeaders.value)
    
    // Try to get headers from backend first
    let headersFromBackend = false
    
    if (processResult.headers && processResult.headers.length > 0) {
      // Check if backend headers are valid (not generic Column_X names)
      const hasValidHeaders = processResult.headers.some((header: string) => 
        header && !header.match(/^Column[_\s]*\d+$/i)
      )
      
      if (hasValidHeaders) {
        previewHeaders.value = processResult.headers
        headersFromBackend = true
        console.log('[setupPreview] Using valid processResult.headers:', previewHeaders.value)
      }
    }
    
    if (!headersFromBackend && processResult.backendMetadata.columnInfo && processResult.backendMetadata.columnInfo.length > 0) {
      // Check if columnInfo has valid names (not generic Column_X)
      const columnNames = processResult.backendMetadata.columnInfo.map((col: any, i: number) => col.name || `Column ${i + 1}`)
      const hasValidColumnNames = columnNames.some((name: string) => 
        name && !name.match(/^Column[_\s]*\d+$/i)
      )
      
      if (hasValidColumnNames) {
        previewHeaders.value = columnNames
        headersFromBackend = true
        console.log('[setupPreview] Using valid columnInfo names:', previewHeaders.value)
      }
    }
    
    // CRITICAL FIX: If backend failed to detect headers properly but we expect headers,
    // extract them from the first data row (since backend includes headers as data when detection fails)
    if (!headersFromBackend && hasHeaders.value && processResult.data && processResult.data.length > 0) {
      console.log('[setupPreview] Backend header detection failed, extracting from first data row')
      const firstRow = processResult.data[0]
      
      if (firstRow && firstRow.length > 0) {
        // Extract headers from first row and validate they look like header names
        const extractedHeaders = firstRow.map((cell: any, i: number) => {
          if (cell === null || cell === undefined || cell === '') {
            return `Column ${i + 1}`
          }
          const cellStr = String(cell).trim()
          // Check if this looks like a header (contains letters, reasonable length)
          if (cellStr.length > 0 && cellStr.length < 100 && /[a-zA-Z]/.test(cellStr)) {
            return cellStr
          }
          return `Column ${i + 1}`
        })
        
        previewHeaders.value = extractedHeaders
        previewData.value = processResult.data.slice(1) // Remove header row from data
        console.log('[setupPreview] Extracted headers from first row:', previewHeaders.value)
        console.log('[setupPreview] Data after removing header row:', previewData.value.length, 'rows')
      } else {
        console.log('[setupPreview] No data available to extract headers from')
        previewHeaders.value = Array.from({ length: processResult.data?.[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
        previewData.value = processResult.data || []
      }
    } else if (!headersFromBackend) {
      console.log('[setupPreview] No valid headers available, using defaults')
      previewHeaders.value = Array.from({ length: processResult.data?.[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
      previewData.value = processResult.data || []
    } else {
      // Headers were successfully extracted from backend
      previewData.value = processResult.data || []
    }
    
    console.log('[setupPreview] Backend result - Final Headers:', previewHeaders.value)
    console.log('[setupPreview] Backend data rows (no header row included):', previewData.value.length)
  } else if (headersDetected && processResult.data.length > 0) {
    // Frontend processing with headers detected by CSV parser
    console.log('[setupPreview] Frontend processing with headers')
    
    // CRITICAL FIX: Use detectedHeaders from CSV parser instead of re-extracting
    if (processResult.detectedHeaders && processResult.detectedHeaders.length > 0) {
      // Use the headers that were properly detected and extracted by the CSV parser
      previewHeaders.value = processResult.detectedHeaders.map((header: string, i: number) => {
        if (!header || header.trim() === '') {
          return `Column ${i + 1}`
        }
        return header.trim()
      })
      
      // Data is already clean (headers were already removed by CSV parser)
      previewData.value = processResult.data
      console.log('[setupPreview] Using detected headers from CSV parser:', previewHeaders.value)
    } else {
      // Fallback to old method only if detectedHeaders not available
      console.log('[setupPreview] No detectedHeaders available, falling back to first-row extraction')
      const firstRow = processResult.data[0] || []
      previewHeaders.value = firstRow.map((h: any, i: number) => {
        if (h === null || h === undefined) {
          return `Column ${i + 1}`
        }
        
        try {
          const headerStr = String(h).trim()
          // Validate header (not empty, not special values, reasonable length)
          if (headerStr && 
              headerStr !== 'null' && 
              headerStr !== 'undefined' && 
              headerStr !== 'NaN' &&
              headerStr.length > 0 &&
              headerStr.length < 100) {
            return headerStr
          }
        } catch (e) {
          console.warn(`[setupPreview] Header conversion failed for column ${i}:`, e)
        }
        return `Column ${i + 1}`
      })
      
      // Remove header row from data
      previewData.value = processResult.data.slice(1)
      console.log('[setupPreview] Frontend with headers - Extracted headers (fallback):', previewHeaders.value)
    }
  } else {
    // No headers - use all data and generate column names
    console.log('[setupPreview] No headers detected')
    previewHeaders.value = Array.from({ length: processResult.data[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
    previewData.value = processResult.data || []
  }
  
  // Update UI state
  hasHeaders.value = headersDetected
  
  // Comprehensive validation and debugging
  if (previewData.value.length === 0) {
    console.warn('[setupPreview] Warning: No preview data after processing')
  }
  
  if (previewHeaders.value.length === 0 && previewData.value.length > 0) {
    console.warn('[setupPreview] Warning: No headers but data exists')
    previewHeaders.value = Array.from({ length: previewData.value[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
  }
  
  // Validate header-data alignment
  if (previewData.value.length > 0 && previewHeaders.value.length !== previewData.value[0]?.length) {
    console.error('[setupPreview] ERROR: Header count mismatch!', {
      headerCount: previewHeaders.value.length,
      dataColumnCount: previewData.value[0]?.length,
      headers: previewHeaders.value,
      firstDataRow: previewData.value[0]
    })
  }
  
  // Check for potential data loss (first row accidentally treated as headers)
  if (processResult.data.length > 0 && previewData.value.length === processResult.data.length - 1 && !processResult.backendMetadata) {
    const possibleHeaders = processResult.data[0]
    const hasStringHeaders = possibleHeaders?.some((cell: any) => {
      const str = String(cell).trim()
      return isNaN(parseFloat(str)) && str !== '' && str !== 'null'
    })
    
    if (hasStringHeaders) {
      console.info('[setupPreview] First row contains string values, correctly treated as headers')
    } else {
      console.warn('[setupPreview] Warning: First row was skipped but may contain data:', possibleHeaders)
    }
  }
  
  console.log('[setupPreview] Final result:', {
    headers: previewHeaders.value,
    dataRowCount: previewData.value.length,
    originalDataRowCount: processResult.data?.length,
    firstDataSample: previewData.value[0],
    hasHeadersFlag: hasHeaders.value,
    backendProcessed: !!processResult.backendMetadata,
    dataLossDetected: processResult.data?.length && previewData.value.length < processResult.data.length
  })
  
  // Critical data loss detection
  if (processResult.data?.length && previewData.value.length < processResult.data.length) {
    const lostRows = processResult.data.length - previewData.value.length
    console.error(`[setupPreview] CRITICAL: Lost ${lostRows} rows during processing!`)
    console.error('[setupPreview] Original data length:', processResult.data.length)
    console.error('[setupPreview] Preview data length:', previewData.value.length)
    console.error('[setupPreview] Backend metadata:', !!processResult.backendMetadata)
    console.error('[setupPreview] Headers detected:', headersDetected)
  }
}

const countMissingValues = (data: any[][]): number => {
  let count = 0
  for (const row of data) {
    for (const cell of row) {
      if (cell === null || cell === undefined || cell === '' || cell === 'null' || cell === 'N/A') {
        count++
      }
    }
  }
  return count
}

const removeFile = () => {
  uploadedFile.value = null
  fileStats.value = null
  previewData.value = []
  previewHeaders.value = []
  if (fileInput.value) fileInput.value.value = ''
}

const confirmFileUpload = async () => {
  if (!uploadedFile.value || !uploadResult.value) return
  
  try {
    isProcessing.value = true
    currentProcessingStage.value = 'Finalizing data...'
    
    const result = uploadResult.value
    
    // Enhanced header and data processing using the same logic as preview
    console.log('[confirmFileUpload] Processing with hasHeaders checkbox:', hasHeaders.value)
    console.log('[confirmFileUpload] Backend hasHeaders flag:', result.hasHeaders)
    console.log('[confirmFileUpload] Backend metadata present:', !!result.backendMetadata)
    
    // Use setupPreview logic to ensure consistency, but capture the results
    const tempPreviewHeaders = previewHeaders.value
    const tempPreviewData = previewData.value
    const tempHasHeaders = hasHeaders.value
    
    // Run setup preview with current checkbox state to get consistent processing
    setupPreview(result, hasHeaders.value)
    
    // Capture the processed results
    let finalHeaders = [...previewHeaders.value]
    let finalData = [...previewData.value]
    
    // Restore original preview state (since this is for final processing, not preview)
    previewHeaders.value = tempPreviewHeaders
    previewData.value = tempPreviewData
    hasHeaders.value = tempHasHeaders
    
    console.log('[confirmFileUpload] Processed headers:', finalHeaders)
    console.log('[confirmFileUpload] Data rows after processing:', finalData.length)
    console.log('[confirmFileUpload] Original upload result rows:', result.data?.length)
    
    // Critical: Check for data loss during final processing
    if (result.data?.length && finalData.length < result.data.length) {
      const lostRows = result.data.length - finalData.length
      console.error(`[confirmFileUpload] CRITICAL: Lost ${lostRows} rows during final processing!`)
      console.error('[confirmFileUpload] This indicates header processing is removing data rows')
    }
    
    // Process missing values if strategy is not 'keep'
    if (missingValueStrategy.value !== 'keep' && finalData.length > 0) {
      finalData = await applyMissingValueStrategy(finalData, missingValueStrategy.value)
    }
    
    // Validate data integrity
    if (finalData.length === 0) {
      throw new Error('No data rows found after processing')
    }
    
    if (finalHeaders.length === 0) {
      throw new Error('No columns found in the data')
    }
    
    // Ensure all data rows have the same number of columns
    const expectedColumnCount = finalHeaders.length
    const validData = finalData.filter(row => {
      return Array.isArray(row) && row.length === expectedColumnCount
    })
    
    if (validData.length === 0) {
      throw new Error('No valid data rows with consistent column count')
    }
    
    if (validData.length < finalData.length) {
      console.warn(`Removed ${finalData.length - validData.length} rows with inconsistent column count`)
    }
    
    globalState.setDataset({
      name: uploadedFile.value.name,
      type: 'uploaded',
      data: validData,
      fileName: uploadedFile.value.name,
      pointCount: validData.length,
      featureCount: finalHeaders.length,
      headers: finalHeaders,
      originalData: result.data,
      hasHeaders: hasHeaders.value,
      missingValueStrategy: missingValueStrategy.value,
      normalization: normalization.value,
      backendMetadata: result.backendMetadata,
      fileId: result.fileId  // Add fileId to ensure it's preserved
    })
    
    console.log('=== FINAL DATASET SUMMARY ===')
    console.log('- Headers:', finalHeaders)
    console.log('- Final data rows:', validData.length)
    console.log('- Original file data rows:', result.data?.length)
    console.log('- Backend processed:', !!result.backendMetadata)
    console.log('- Headers detected:', result.hasHeaders)
    console.log('- Columns:', finalHeaders.length)
    console.log('- Missing value strategy:', missingValueStrategy.value)
    console.log('- Sample data:', validData.slice(0, 2))
    console.log('=== END DATASET SUMMARY ===')
    
    // Final data loss check
    if (result.data?.length && validData.length < result.data.length - 3) { // Allow for reasonable header removal
      console.error('🚨 CRITICAL DATA LOSS DETECTED!')
      console.error(`Original: ${result.data.length} rows, Final: ${validData.length} rows`)
      console.error('This suggests rows are being incorrectly dropped during processing')
    }
    
    changingData.value = false
    proceedToClustering()
  } catch (error) {
    console.error('Error confirming file upload:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
    alert(`Error processing file: ${errorMessage}`)
  } finally {
    isProcessing.value = false
  }
}

// Missing value strategy implementation
const applyMissingValueStrategy = async (data: any[][], strategy: string): Promise<any[][]> => {
  if (strategy === 'keep' || data.length === 0) {
    return data
  }
  
  console.log(`Applying missing value strategy: ${strategy}`)
  
  switch (strategy) {
    case 'remove':
      return data.filter(row => {
        return !row.some(cell => 
          cell === null || cell === undefined || cell === '' || 
          String(cell).toLowerCase() === 'null' || String(cell) === 'NaN' ||
          String(cell).toLowerCase() === 'n/a'
        )
      })
    
    case 'fill_mean':
      return fillWithColumnStats(data, 'mean')
    
    case 'fill_median':
      return fillWithColumnStats(data, 'median')
    
    case 'fill_zero':
      return data.map(row => 
        row.map(cell => isMissingValue(cell) ? 0 : cell)
      )
    
    case 'fill_forward':
      return fillForward(data)
    
    case 'fill_backward':
      return fillBackward(data)
    
    default:
      console.warn(`Unknown missing value strategy: ${strategy}, keeping data as-is`)
      return data
  }
}


const fillWithColumnStats = (data: any[][], statType: 'mean' | 'median'): any[][] => {
  if (data.length === 0) return data
  
  const columnCount = data[0].length
  const columnStats: number[] = []
  
  // Calculate stats for each column
  for (let col = 0; col < columnCount; col++) {
    const validValues = data
      .map(row => row[col])
      .filter(val => !isMissingValue(val) && !isNaN(parseFloat(String(val))))
      .map(val => parseFloat(String(val)))
    
    if (validValues.length === 0) {
      columnStats[col] = 0
    } else if (statType === 'mean') {
      columnStats[col] = validValues.reduce((sum, val) => sum + val, 0) / validValues.length
    } else { // median
      const sorted = [...validValues].sort((a, b) => a - b)
      const mid = Math.floor(sorted.length / 2)
      columnStats[col] = sorted.length % 2 === 0 
        ? (sorted[mid - 1] + sorted[mid]) / 2 
        : sorted[mid]
    }
  }
  
  // Fill missing values
  return data.map(row => 
    row.map((cell, colIndex) => {
      if (isMissingValue(cell)) {
        // Try to parse as number, fallback to stat value
        const numVal = parseFloat(String(cell))
        return isNaN(numVal) ? columnStats[colIndex] : numVal
      }
      return cell
    })
  )
}

const fillForward = (data: any[][]): any[][] => {
  if (data.length === 0) return data
  
  const result = data.map(row => [...row])
  const columnCount = data[0].length
  
  for (let col = 0; col < columnCount; col++) {
    let lastValidValue: any = null
    
    for (let row = 0; row < result.length; row++) {
      if (!isMissingValue(result[row][col])) {
        lastValidValue = result[row][col]
      } else if (lastValidValue !== null) {
        result[row][col] = lastValidValue
      }
    }
  }
  
  return result
}

const fillBackward = (data: any[][]): any[][] => {
  if (data.length === 0) return data
  
  const result = data.map(row => [...row])
  const columnCount = data[0].length
  
  for (let col = 0; col < columnCount; col++) {
    let nextValidValue: any = null
    
    // Go backwards through rows
    for (let row = result.length - 1; row >= 0; row--) {
      if (!isMissingValue(result[row][col])) {
        nextValidValue = result[row][col]
      } else if (nextValidValue !== null) {
        result[row][col] = nextValidValue
      }
    }
  }
  
  return result
}

// Header processing test function (for debugging)
const testHeaderProcessing = () => {
  console.log('=== Header Processing Test ===')
  
  // Test case 1: Clear headers
  const testData1 = [
    ['Name', 'Age', 'City', 'Label'],
    ['John', 25, 'NYC', 'A'],
    ['Jane', 30, 'LA', 'B']
  ]
  console.log('Test 1 - Clear headers:', {
    input: testData1,
    shouldDetectHeaders: true
  })
  
  // Test case 2: Numeric columns with headers
  const testData2 = [
    ['Feature1', 'Feature2', 'Target'],
    [1.5, 2.3, 0],
    [2.1, 1.8, 1]
  ]
  console.log('Test 2 - Numeric data with headers:', {
    input: testData2,
    shouldDetectHeaders: true
  })
  
  // Test case 3: No headers (all numeric)
  const testData3 = [
    [1.5, 2.3, 0],
    [2.1, 1.8, 1],
    [3.2, 1.1, 0]
  ]
  console.log('Test 3 - All numeric, no headers:', {
    input: testData3,
    shouldDetectHeaders: false
  })
  
  console.log('=== End Header Processing Test ===')
}

// Expose test function to window for manual testing
if (typeof window !== 'undefined') {
  (window as any).testHeaderProcessing = testHeaderProcessing
}

// Utility functions
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatCell = (value: any): string => {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'number') return value.toLocaleString()
  return String(value).length > 20 ? String(value).substring(0, 20) + '...' : String(value)
}

onMounted(() => {
  // Check if returning from onboarding
  const isFromOnboarding = sessionStorage.getItem('onboardingInProgress') === 'true';
  if (isFromOnboarding) {
    sessionStorage.removeItem('onboardingInProgress');
    sessionStorage.removeItem('onboardingStep');
    // Show a brief notification that they can proceed with upload
    console.log('Returned from onboarding - ready for data upload');
  }
  
  // Don't auto-show upload options if we have data
  if (currentDataset.value) {
    changingData.value = false
  }
})

// Watch for column configuration changes and trigger backend preview
watch([normalization, missingValueStrategy, columnConfigs], async () => {
  if (showColumnConfiguration.value && columnConfigs.value.length > 0 && uploadedFile.value) {
    // Debounce to avoid too many API calls
    await new Promise(resolve => setTimeout(resolve, 500))
    await getBackendPreview()
  }
}, { deep: true })

// Clear backend preview when file changes
watch(uploadedFile, () => {
  useBackendPreview.value = false
  backendPreviewData.value = []
  backendPreviewHeaders.value = []
})
</script>

<style scoped>
@import '~/assets/css/pages/data-upload.css';
</style>


