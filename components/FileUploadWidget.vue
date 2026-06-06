<template>
  <div class="file-upload-widget">
    <!-- Upload Area -->
    <div 
      class="upload-area" 
      :class="{ 
        'drag-over': isDragOver, 
        'has-file': uploadedFile && !isProcessing, 
        'processing': isProcessing,
        'error': hasError
      }"
      @click="!isProcessing && triggerFileInput()" 
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <input 
        ref="fileInput" 
        type="file" 
        :accept="acceptedFormats" 
        @change="handleFileSelect"
        style="display: none"
      >
      
      <!-- Upload Placeholder -->
      <div v-if="!uploadedFile && !hasError" class="upload-placeholder">
        <div class="upload-icon">📤</div>
        <div class="upload-text">
          <h4>{{ uploadText }}</h4>
          <p>or <span class="upload-link">click to browse</span></p>
          <div class="upload-hint">{{ formatHint }}</div>
        </div>
      </div>
      
      <!-- File Info -->
      <div v-else-if="uploadedFile && !isProcessing && !hasError" class="file-info">
        <div class="file-icon">📄</div>
        <div class="file-details">
          <h4>{{ uploadedFile.name }}</h4>
          <p>{{ formatFileSize(uploadedFile.size) }}</p>
          <div v-if="fileStats" class="file-stats">
            <span>{{ fileStats.rows.toLocaleString() }} rows</span>
            <span>{{ fileStats.columns }} columns</span>
            <span v-if="fileStats.missingValues > 0" class="warning">
              {{ fileStats.missingValues }} missing values
            </span>
            <span v-if="processingMethod !== 'unknown'" 
                  :class="processingMethod === 'backend' ? 'processing-backend' : 'processing-frontend'">
              {{ processingMethod === 'backend' ? '⚡ Backend' : '💻 Frontend' }}
            </span>
          </div>
        </div>
        <button @click.stop="removeFile" class="remove-btn" title="Remove file">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <!-- Processing State -->
      <div v-else-if="isProcessing" class="processing-state">
        <div class="processing-icon">
          <div class="spinner"></div>
        </div>
        <div class="processing-text">
          <h4>Processing {{ uploadedFile?.name }}</h4>
          <div class="progress-container">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: processingProgress + '%' }"></div>
            </div>
            <span class="progress-text">{{ Math.round(processingProgress) }}%</span>
          </div>
          <p class="processing-stage">{{ currentProcessingStage }}</p>
        </div>
      </div>
      
      <!-- Error State -->
      <div v-else-if="hasError" class="error-state">
        <div class="error-icon">❌</div>
        <div class="error-text">
          <h4>Upload Failed</h4>
          <p>{{ errorMessage }}</p>
          <button @click="clearError" class="retry-btn">Try Again</button>
        </div>
      </div>
    </div>

    <!-- File Options (only show after successful upload) -->
    <div v-if="uploadedFile && !isProcessing && !hasError && showOptions" class="file-options">
      <div class="option-group">
        <label class="checkbox-label">
          <input 
            type="checkbox" 
            v-model="hasHeaders" 
            @change="handleHeaderToggle"
            class="checkbox"
          />
          <span class="checkbox-text">First row contains column headers</span>
        </label>
      </div>
      
      <div v-if="showMissingValueOptions && fileStats?.missingValues > 0" class="option-group">
        <label class="option-label">Handle missing values:</label>
        <div class="radio-group">
          <label class="radio-option">
            <input type="radio" value="remove" v-model="missingValueStrategy" @change="handleOptionsChange">
            <span>Remove rows with missing values</span>
          </label>
          <label class="radio-option">
            <input type="radio" value="fill_mean" v-model="missingValueStrategy" @change="handleOptionsChange">
            <span>Fill with mean (numeric columns)</span>
          </label>
          <label class="radio-option">
            <input type="radio" value="fill_median" v-model="missingValueStrategy" @change="handleOptionsChange">
            <span>Fill with median (numeric columns)</span>
          </label>
          <label class="radio-option">
            <input type="radio" value="fill_zero" v-model="missingValueStrategy" @change="handleOptionsChange">
            <span>Fill with zero</span>
          </label>
          <label class="radio-option">
            <input type="radio" value="keep" v-model="missingValueStrategy" @change="handleOptionsChange">
            <span>Keep as is</span>
          </label>
        </div>
      </div>

      <div v-if="showNormalizationOptions" class="option-group">
        <label class="option-label">Normalization:</label>
        <select v-model="normalization" @change="handleOptionsChange" class="select-input">
          <option value="none">None</option>
          <option value="standard">Standard Scaler (z-score)</option>
          <option value="minmax">Min-Max Scaler (0-1)</option>
        </select>
      </div>
    </div>

    <!-- Enhanced Column Configuration (if enabled and has data) -->
    <div v-if="showColumnConfiguration && uploadedFile && !isProcessing && !hasError && showColumnConfig" class="column-config-section">
      <EnhancedColumnConfiguration
        :headers="previewHeaders"
        :column-types="columnTypes"
        :categorical-columns="categoricalColumns"
        :column-info="backendMetadata?.columnInfo || []"
        :initial-missing-strategy="missingValueStrategy"
        :initial-normalization="normalization"
        :categorical-mappings-from-processing="backendMetadata?.processing_info?.categorical_info || {}"
        @configuration-changed="handleEnhancedColumnConfigurationChanged"
      />
    </div>

    <!-- Data Preview (if enabled) -->
    <div v-if="showPreview && previewData.length > 0 && !isProcessing" class="data-preview">
      <h4>Data Preview (First 10 rows)</h4>
      <div class="preview-table-container">
        <table class="preview-table">
          <thead>
            <tr>
              <th v-for="(header, index) in previewHeaders" :key="index">
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in previewData" :key="rowIndex">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">
                {{ formatCellValue(cell) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useFileUpload } from '~/composables/useFileUpload'
import { useMemoryManagement } from '~/composables/useMemoryManagement'
import EnhancedColumnConfiguration from '~/components/EnhancedColumnConfiguration.vue'

interface FileStats {
  rows: number
  columns: number
  missingValues: number
  hasHeaders: boolean
}

interface FileData {
  type: 'upload'
  file: File
  name: string
  data: number[][]
  rawData?: any[][]
  headers: string[]
  rowCount: number
  columnCount: number
  fileStats: FileStats
  hasHeaders: boolean
  missingValueStrategy: string
  normalization: string
  categoricalColumns?: Set<number>
  columnTypes?: string[]
  featureColumns?: number[]
  labelColumns?: number[]
  ignoredColumns?: number[]
  // Backend integration fields
  fileId?: string
  backendMetadata?: any
  useBackend?: boolean
}

interface Props {
  acceptedFormats?: string
  maxFileSize?: number
  uploadText?: string
  formatHint?: string
  showOptions?: boolean
  showPreview?: boolean
  showMissingValueOptions?: boolean
  showNormalizationOptions?: boolean
  showColumnConfiguration?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  acceptedFormats: '.csv,.xlsx,.xls',
  maxFileSize: 100 * 1024 * 1024, // 100MB
  uploadText: 'Drop your file here',
  formatHint: 'Supports CSV, Excel files up to 100MB',
  showOptions: true,
  showPreview: true,
  showMissingValueOptions: true,
  showNormalizationOptions: true,
  showColumnConfiguration: true
})

const emit = defineEmits<{
  'file-uploaded': [data: FileData]
  'file-removed': []
  'processing-start': []
  'processing-progress': [progress: number]
  'processing-error': [error: string]
}>()

// File upload composables  
const { 
  handleFileUpload, 
  detectColumnTypes, 
  handleFileUploadEnhanced, 
  processDataEnhanced,
  USE_BACKEND_PROCESSING 
} = useFileUpload()
const { trackLargeObject, clearLargeData } = useMemoryManagement()

// Reactive state
const fileInput = ref<HTMLInputElement>()
const uploadedFile = ref<File | null>(null)
const rawData = ref<any[][]>([])
const processedData = ref<number[][]>([])
const fileStats = ref<FileStats | null>(null)
const hasHeaders = ref(true)
const missingValueStrategy = ref('keep')
const normalization = ref('none')
const categoricalColumns = ref<Set<number>>(new Set())
const columnTypes = ref<string[]>([])
const featureColumns = ref<number[]>([])
const labelColumns = ref<number[]>([])
const ignoredColumns = ref<number[]>([])
const showColumnConfig = ref(false)

// Backend integration state
const fileId = ref<string | null>(null)
const backendMetadata = ref<any>(null)
const useBackendProcessing = ref(USE_BACKEND_PROCESSING.value)
const processingMethod = ref<'backend' | 'frontend' | 'unknown'>('unknown')
const backendConnectionStatus = ref<'unknown' | 'connected' | 'failed'>('unknown')

// UI state
const isDragOver = ref(false)
const isProcessing = ref(false)
const processingProgress = ref(0)
const currentProcessingStage = ref('')
const hasError = ref(false)
const errorMessage = ref('')

// Processing stages
const stages = [
  'Reading file...',
  'Parsing data...',
  'Detecting headers...',
  'Analyzing columns...',
  'Processing missing values...',
  'Applying transformations...',
  'Finalizing...'
]

// Computed properties
const previewHeaders = computed(() => {
  if (!rawData.value.length) return []
  
  // Use backend headers if available, otherwise generate from data
  if (backendMetadata.value?.columnInfo) {
    return backendMetadata.value.columnInfo.map((col: any, i: number) => 
      col.name || `Column ${i + 1}`
    )
  }
  
  // For backend-processed data with headers, extract from first row if no columnInfo
  if (backendMetadata.value && hasHeaders.value && rawData.value.length > 0) {
    // If backend didn't provide column names, extract from first row
    return rawData.value[0]?.map((h: any, i: number) => {
      if (h === null || h === undefined) return `Column ${i + 1}`
      
      const header = String(h).trim()
      if (header && 
          header !== 'null' && 
          header !== 'undefined' && 
          header !== 'NaN' &&
          header.length > 0 &&
          header.length < 100) {
        return header
      }
      return `Column ${i + 1}`
    }) || Array.from({ length: rawData.value[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
  }
  
  // Frontend processing: extract headers from first row if detected
  if (hasHeaders.value && rawData.value.length > 0) {
    return rawData.value[0]?.map((h: any, i: number) => {
      if (h === null || h === undefined) return `Column ${i + 1}`
      
      const header = String(h).trim()
      // Validate header quality
      if (header && 
          header !== 'null' && 
          header !== 'undefined' && 
          header !== 'NaN' &&
          header.length > 0 &&
          header.length < 100) {
        return header
      }
      return `Column ${i + 1}`
    }) || []
  } else {
    return Array.from({ length: rawData.value[0]?.length || 0 }, (_, i) => `Column ${i + 1}`)
  }
})

const previewData = computed(() => {
  if (!rawData.value.length) return []
  
  // For backend-processed data, check if headers need to be skipped
  if (backendMetadata.value) {
    // If backend provided column info, headers are already extracted, use all data
    if (backendMetadata.value.columnInfo) {
      return rawData.value.slice(0, 10) // First 10 rows for preview
    }
    // If no column info but headers detected, skip first row
    const startRow = hasHeaders.value ? 1 : 0
    return rawData.value.slice(startRow, startRow + 10)
  }
  
  // For frontend processing, skip first row if it contains headers
  const startRow = hasHeaders.value ? 1 : 0
  return rawData.value.slice(startRow, startRow + 10)
})

// File handling methods
const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    processFile(target.files[0])
  }
}

const handleDragOver = (event: DragEvent) => {
  if (!isProcessing.value) {
    isDragOver.value = true
  }
}

const handleDragLeave = (event: DragEvent) => {
  isDragOver.value = false
}

const handleDrop = (event: DragEvent) => {
  isDragOver.value = false
  if (!isProcessing.value && event.dataTransfer?.files && event.dataTransfer.files[0]) {
    processFile(event.dataTransfer.files[0])
  }
}

const processFile = async (file: File) => {
  // Validate file size
  if (file.size > props.maxFileSize) {
    showError(`File size (${formatFileSize(file.size)}) exceeds maximum allowed size of ${formatFileSize(props.maxFileSize)}`)
    return
  }

  uploadedFile.value = file
  isProcessing.value = true
  processingProgress.value = 0
  hasError.value = false
  emit('processing-start')

  try {
    // Stage 1: Reading file
    currentProcessingStage.value = stages[0]
    processingProgress.value = 10

    // Stage 2: Parsing data
    currentProcessingStage.value = stages[1]
    processingProgress.value = 20

    // Use enhanced file upload with backend integration
    console.log('[FileUploadWidget] About to call handleFileUploadEnhanced')
    console.log('[FileUploadWidget] USE_BACKEND_PROCESSING.value:', USE_BACKEND_PROCESSING.value)
    console.log('[FileUploadWidget] useBackendProcessing.value:', useBackendProcessing.value)
    
    const fileData = await handleFileUploadEnhanced(file, useBackendProcessing.value)
    
    // Store backend metadata if available and update processing method indicator
    if (fileData.fileId) {
      fileId.value = fileData.fileId
      backendMetadata.value = fileData.backendMetadata
      processingMethod.value = 'backend'
      backendConnectionStatus.value = 'connected'
      console.log('[FileUploadWidget] ✅ Backend processing successful')
    } else {
      processingMethod.value = 'frontend' 
      console.log('[FileUploadWidget] ⚠️ Using frontend processing fallback')
    }
    
    // Handle rawData based on whether backend processed the file
    let originalData: any[][] = []
    
    if (backendMetadata.value) {
      // Backend processed: use the processed data (headers already extracted)
      console.log('[FileUploadWidget] Using backend-processed data')
      originalData = fileData.data.map(row => row.map(cell => cell))
    } else if (file.name.toLowerCase().endsWith('.csv')) {
      // Frontend processing: parse original CSV for missing value detection
      console.log('[FileUploadWidget] Frontend processing: parsing original CSV')
      const text = await file.text()
      const lines = text.trim().split(/\r?\n/).filter(line => line.trim())
      originalData = lines.map(line => {
        // Improved CSV parsing to handle quoted values and commas within quotes
        const result = []
        let current = ''
        let inQuotes = false
        let quoteChar = ''
        
        for (let i = 0; i < line.length; i++) {
          const char = line[i]
          const nextChar = i + 1 < line.length ? line[i + 1] : ''
          
          if (!inQuotes) {
            if (char === '"' || char === "'") {
              inQuotes = true
              quoteChar = char
            } else if (char === ',') {
              result.push(current.trim())
              current = ''
            } else {
              current += char
            }
          } else {
            if (char === quoteChar) {
              if (nextChar === quoteChar) {
                // Escaped quote
                current += char
                i++ // Skip next quote
              } else {
                // End of quoted section
                inQuotes = false
              }
            } else {
              current += char
            }
          }
        }
        
        // Add the last value
        result.push(current.trim())
        return result
      })
    } else {
      // For non-CSV files, use the processed data
      originalData = fileData.data.map(row => row.map(cell => cell))
    }
    
    rawData.value = originalData
    
    console.log('[FileUploadWidget] rawData set with', originalData.length, 'rows')
    console.log('[FileUploadWidget] Backend processed:', !!backendMetadata.value)
    console.log('[FileUploadWidget] Headers detected:', fileData.hasHeaders)
    
    // Stage 3: Detecting headers
    currentProcessingStage.value = stages[2]
    processingProgress.value = 40
    
    hasHeaders.value = fileData.hasHeaders || detectHeaders()
    categoricalColumns.value = fileData.categoricalColumns || new Set()

    // Stage 4: Analyzing columns
    currentProcessingStage.value = stages[3]
    processingProgress.value = 60
    
    const stats = analyzeData()
    fileStats.value = stats
    
    // Detect column types for configuration
    columnTypes.value = detectColumnTypes(rawData.value, hasHeaders.value)
    
    // Show column configuration if enabled (regardless of headers)
    if (props.showColumnConfiguration) {
      showColumnConfig.value = true
    }

    // Stage 5: Processing missing values
    currentProcessingStage.value = stages[4]
    processingProgress.value = 80

    // Stage 6: Applying transformations
    currentProcessingStage.value = stages[5]
    processingProgress.value = 90

    processedData.value = fileData.data

    // Stage 7: Finalizing
    currentProcessingStage.value = stages[6]
    processingProgress.value = 100

    // Track large data for memory management
    trackLargeObject(rawData.value)
    trackLargeObject(processedData.value)

    // Emit file uploaded event
    emitFileData()

    setTimeout(() => {
      isProcessing.value = false
      processingProgress.value = 0
    }, 500)

  } catch (error) {
    console.error('Error processing file:', error)
    
    // Update processing method and connection status based on error
    if (error instanceof Error) {
      const errorMessage = error.message.toLowerCase()
      
      if (errorMessage.includes('backend connection failed') || 
          errorMessage.includes('network error') ||
          errorMessage.includes('cannot connect')) {
        backendConnectionStatus.value = 'failed'
        processingMethod.value = 'frontend'
      }
    }
    
    showError(error instanceof Error ? error.message : 'Failed to process file')
  }
}

const convertToStringArray = (data: number[][]): any[][] => {
  // Convert processed numeric data back to mixed types for preview
  // This function is no longer needed since we preserve original data
  return data.map(row => row.map(cell => cell))
}

const detectHeaders = (): boolean => {
  if (!rawData.value.length || rawData.value.length < 2) return false
  
  const firstRow = rawData.value[0]
  const secondRow = rawData.value[1]
  
  if (!secondRow) return false
  
  // Simple heuristic: if first row contains mostly strings and second row contains mostly numbers
  const firstRowStrings = firstRow.filter(cell => typeof cell === 'string' && isNaN(Number(cell))).length
  const secondRowNumbers = secondRow.filter(cell => !isNaN(Number(cell))).length
  
  return firstRowStrings > firstRow.length * 0.5 && secondRowNumbers > secondRow.length * 0.5
}

const analyzeData = (): FileStats => {
  // Handle data analysis based on backend vs frontend and header detection
  let dataRows: any[][]
  if (backendMetadata.value?.columnInfo) {
    // Backend already extracted headers, use all data for analysis
    dataRows = rawData.value
  } else {
    // Frontend processing or backend without column extraction
    dataRows = hasHeaders.value ? rawData.value.slice(1) : rawData.value
  }
  let missingCount = 0
  
  for (const row of dataRows) {
    for (const cell of row) {
      // More comprehensive missing value detection
      if (cell === null || 
          cell === undefined || 
          cell === '' || 
          cell === 'null' || 
          cell === 'NULL' ||
          cell === 'NaN' || 
          cell === 'nan' ||
          cell === 'N/A' ||
          cell === 'n/a' ||
          cell === '#N/A' ||
          cell === '-' ||
          (typeof cell === 'string' && cell.trim() === '') ||
          (typeof cell === 'number' && isNaN(cell))) {
        missingCount++
      }
    }
  }
  
  return {
    rows: dataRows.length,
    columns: rawData.value[0]?.length || 0,
    missingValues: missingCount,
    hasHeaders: hasHeaders.value
  }
}

const handleHeaderToggle = () => {
  fileStats.value = analyzeData()
  emitFileData()
}

const handleOptionsChange = () => {
  emitFileData()
}

const handleEnhancedColumnConfigurationChanged = (config: { 
  featureColumns: number[], 
  labelColumns: number[], 
  ignoredColumns: number[],
  columnConfigs: any[],
  missingValueStrategy: string,
  normalization: string
}) => {
  featureColumns.value = config.featureColumns
  labelColumns.value = config.labelColumns
  ignoredColumns.value = config.ignoredColumns
  missingValueStrategy.value = config.missingValueStrategy
  normalization.value = config.normalization
  
  // Store column configurations for backend processing
  if (backendMetadata.value) {
    backendMetadata.value.columnConfigs = config.columnConfigs
  }
  
  emitFileData()
}

const emitFileData = () => {
  if (!uploadedFile.value || !fileStats.value) return

  const headers = previewHeaders.value
  
  // Handle data processing based on backend vs frontend and header detection
  let dataToProcess: any[][]
  if (backendMetadata.value?.columnInfo) {
    // Backend already extracted headers, use all data
    dataToProcess = rawData.value
  } else {
    // Frontend processing or backend without column extraction
    dataToProcess = hasHeaders.value ? rawData.value.slice(1) : rawData.value
  }

  const fileData: FileData = {
    type: 'upload',
    file: uploadedFile.value,
    name: uploadedFile.value.name,
    data: processedData.value,
    rawData: dataToProcess, // Use processed data that excludes header row when hasHeaders is true
    headers,
    rowCount: dataToProcess.length, // Correct row count after header processing
    columnCount: fileStats.value.columns,
    fileStats: {
      ...fileStats.value,
      rows: dataToProcess.length, // Update row count to reflect actual data rows
      hasHeaders: hasHeaders.value
    },
    hasHeaders: hasHeaders.value,
    missingValueStrategy: missingValueStrategy.value,
    normalization: normalization.value,
    categoricalColumns: categoricalColumns.value,
    columnTypes: columnTypes.value,
    featureColumns: featureColumns.value,
    labelColumns: labelColumns.value,
    ignoredColumns: ignoredColumns.value,
    // Backend integration fields
    fileId: fileId.value,
    backendMetadata: backendMetadata.value,
    useBackend: useBackendProcessing.value
  }

  emit('file-uploaded', fileData)
}

const removeFile = async () => {
  // Clear large data from memory
  if (rawData.value.length > 0) {
    clearLargeData(rawData.value)
  }
  if (processedData.value.length > 0) {
    clearLargeData(processedData.value)
  }

  // Clean up backend file if exists
  if (fileId.value && useBackendProcessing.value) {
    try {
      const { fileUploadAPI } = useFileUpload()
      await fileUploadAPI.deleteFile(fileId.value)
    } catch (error) {
      console.warn('Failed to delete backend file:', error)
    }
  }

  uploadedFile.value = null
  rawData.value = []
  processedData.value = []
  fileStats.value = null
  hasError.value = false
  columnTypes.value = []
  featureColumns.value = []
  labelColumns.value = []
  ignoredColumns.value = []
  showColumnConfig.value = false
  
  // Clear backend state
  fileId.value = null
  backendMetadata.value = null
  
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  
  emit('file-removed')
}

const showError = (message: string) => {
  hasError.value = true
  errorMessage.value = message
  isProcessing.value = false
  emit('processing-error', message)
}

const clearError = () => {
  hasError.value = false
  errorMessage.value = ''
  removeFile()
}

// Utility functions
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatCellValue = (value: any): string => {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'number') return value.toLocaleString()
  return String(value).length > 50 ? String(value).substring(0, 50) + '...' : String(value)
}

// Cleanup on component unmount
onBeforeUnmount(() => {
  if (rawData.value.length > 0) {
    clearLargeData(rawData.value)
  }
  if (processedData.value.length > 0) {
    clearLargeData(processedData.value)
  }
})

// Watch for progress updates
watch(processingProgress, (newProgress) => {
  emit('processing-progress', newProgress)
})
</script>

<style scoped>
.file-upload-widget {
  width: 100%;
}

/* Upload Area */
.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s ease;
  background: #fafafa;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-area:hover {
  border-color: #9ca3af;
  background: #f9fafb;
}

.upload-area.drag-over {
  border-color: #3b82f6;
  background: #f0f7ff;
}

.upload-area.has-file {
  border-style: solid;
  border-color: #10b981;
  background: #f0fdf4;
}

.upload-area.processing {
  cursor: not-allowed;
  opacity: 0.8;
  border-color: #f59e0b;
  background: #fffbeb;
}

.upload-area.error {
  border-color: #ef4444;
  background: #fef2f2;
}

/* Upload Placeholder */
.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon {
  font-size: 2.5rem;
  color: #9ca3af;
}

.upload-text h4 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
}

.upload-text p {
  font-size: 0.9375rem;
  color: #6b7280;
  margin: 0;
}

.upload-link {
  color: #3b82f6;
  font-weight: 500;
}

.upload-hint {
  font-size: 0.875rem;
  color: #9ca3af;
  margin-top: 8px;
}

/* File Info */
.file-info {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.file-icon {
  font-size: 2rem;
  color: #10b981;
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  text-align: left;
}

.file-details h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px 0;
}

.file-details p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0 0 4px 0;
}

.file-stats {
  display: flex;
  gap: 12px;
  font-size: 0.75rem;
  color: #6b7280;
}

.file-stats .warning {
  color: #f59e0b;
  font-weight: 500;
}

.file-stats .processing-backend {
  color: #10b981;
  font-weight: 500;
  font-size: 0.7rem;
}

.file-stats .processing-frontend {
  color: #f59e0b;
  font-weight: 500;
  font-size: 0.7rem;
}

.remove-btn {
  background: none;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.remove-btn:hover {
  border-color: #ef4444;
  color: #ef4444;
  background: #fef2f2;
}

/* Processing State */
.processing-state {
  display: flex;
  align-items: center;
  gap: 20px;
  width: 100%;
}

.processing-icon {
  flex-shrink: 0;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.processing-text {
  flex: 1;
  text-align: left;
}

.processing-text h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  font-weight: 500;
  color: #3b82f6;
  min-width: 40px;
}

.processing-stage {
  font-size: 0.75rem;
  color: #6b7280;
  margin: 0;
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.error-icon {
  font-size: 2rem;
}

.error-text {
  text-align: center;
}

.error-text h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #dc2626;
  margin: 0 0 4px 0;
}

.error-text p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0 0 12px 0;
}

.retry-btn {
  background: #ef4444;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.retry-btn:hover {
  background: #dc2626;
}

/* File Options */
.file-options {
  margin-top: 20px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.option-group {
  margin-bottom: 16px;
}

.option-group:last-child {
  margin-bottom: 0;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox {
  width: 16px;
  height: 16px;
  border: 1px solid #d1d5db;
  border-radius: 3px;
  background: white;
}

.checkbox:checked {
  background: #3b82f6;
  border-color: #3b82f6;
}

.checkbox-text {
  font-size: 0.9375rem;
  color: #374151;
}

.option-label {
  font-size: 0.9375rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
  display: block;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.radio-option input[type="radio"] {
  margin: 0;
}

.select-input {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 0.9375rem;
  color: #374151;
  min-width: 200px;
}

/* Column Configuration */
.column-config-section {
  margin-top: 16px;
}

/* Data Preview */
.data-preview {
  margin-top: 20px;
}

.data-preview h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 12px 0;
}

.preview-table-container {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.preview-table th {
  background: #f8fafc;
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.875rem;
}

.preview-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.875rem;
  color: #4a5568;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-table tr:hover {
  background: #f8fafc;
}

/* Responsive Design */
@media (max-width: 640px) {
  .upload-area {
    padding: 24px 16px;
  }
  
  .file-info {
    flex-direction: column;
    gap: 12px;
  }
  
  .processing-state {
    flex-direction: column;
    gap: 16px;
  }
  
  .file-stats {
    flex-direction: column;
    gap: 4px;
  }
  
  .radio-group {
    gap: 6px;
  }
  
  .preview-table th,
  .preview-table td {
    padding: 6px 8px;
    max-width: 100px;
  }
}
</style>