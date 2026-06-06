<template>
  <div class="enhanced-column-config">
    <div class="config-header">
      <h4>📊 Column Configuration</h4>
      <p>Configure how each column should be used in your analysis</p>
      
      <!-- Quick Actions -->
      <div class="quick-actions">
        <button @click="selectAllAsFeatures" class="quick-action-btn">
          🎯 All as Features
        </button>
        <button @click="autoDetectTypes" class="quick-action-btn">
          🤖 Auto-detect
        </button>
        <button @click="resetConfiguration" class="quick-action-btn">
          🔄 Reset
        </button>
      </div>
    </div>

    <!-- Configuration Summary -->
    <div class="config-summary">
      <div class="summary-card feature">
        <div class="summary-icon">🎯</div>
        <div class="summary-content">
          <div class="summary-value">{{ featureCount }}</div>
          <div class="summary-label">Features</div>
        </div>
      </div>
      
      <div class="summary-card label">
        <div class="summary-icon">🏷️</div>
        <div class="summary-content">
          <div class="summary-value">{{ labelCount }}</div>
          <div class="summary-label">Labels</div>
        </div>
      </div>
      
      <div class="summary-card ignored">
        <div class="summary-icon">❌</div>
        <div class="summary-content">
          <div class="summary-value">{{ ignoredCount }}</div>
          <div class="summary-label">Ignored</div>
        </div>
      </div>
    </div>

    <!-- Column List -->
    <div class="column-list">
      <div class="list-header">
        <span class="col-name">Column Name</span>
        <span class="col-type">Type</span>
        <span class="col-usage">Usage</span>
        <span class="col-actions">Actions</span>
      </div>

      <div v-for="(column, index) in columns" :key="index" class="column-row" :class="{ 'has-issues': hasColumnIssues(column) }">
        
        <!-- Column Name -->
        <div class="column-name">
          <span class="name-text">{{ column.name }}</span>
          <div class="column-preview">
            {{ getColumnPreview(column) }}
          </div>
        </div>

        <!-- Column Type -->
        <div class="column-type">
          <span class="type-badge" :class="column.detectedType">
            {{ formatColumnType(column.detectedType) }}
          </span>
          <div v-if="column.isCategorical" class="categorical-indicator">
            🏷️ {{ column.uniqueCount }} unique
          </div>
        </div>

        <!-- Usage Selection -->
        <div class="column-usage">
          <select 
            v-model="column.usage" 
            @change="handleUsageChange(column, index)"
            class="usage-select"
            :class="column.usage"
          >
            <option value="feature">🎯 Feature</option>
            <option value="label">🏷️ Label</option>
            <option value="ignore">❌ Ignore</option>
          </select>
        </div>

        <!-- Column Actions -->
        <div class="column-actions">
          <button 
            v-if="column.usage === 'feature'" 
            @click="toggleNormalization(column)"
            class="action-btn normalize"
            :class="{ active: column.normalize }"
            title="Toggle normalization"
          >
            📏 Norm
          </button>
          
          <button 
            v-if="column.detectedType === 'categorical'" 
            @click="toggleEncoding(column)"
            class="action-btn encoding"
            :class="{ active: column.oneHotEncode }"
            title="Toggle one-hot encoding"
          >
            🔀 OneHot
          </button>
          
          <button 
            @click="showColumnDetails(column)"
            class="action-btn details"
            title="View column details"
          >
            ℹ️
          </button>
        </div>

        <!-- Column Issues Warning -->
        <div v-if="hasColumnIssues(column)" class="column-issues">
          <div v-for="issue in getColumnIssues(column)" :key="issue" class="issue-item">
            ⚠️ {{ issue }}
          </div>
        </div>
      </div>
    </div>

    <!-- Categorical Mappings Preview -->
    <CategoryMappingPreview 
      v-if="categoricalMappingsFromProcessing && Object.keys(categoricalMappingsFromProcessing).length > 0"
      :categorical-mappings="categoricalMappingsFromProcessing"
    />

    <!-- Advanced Options -->
    <div class="advanced-options" v-if="showAdvanced">
      <h5>🔧 Advanced Options</h5>
      
      <div class="option-group">
        <label>Default Normalization:</label>
        <select v-model="defaultNormalization" @change="applyDefaultNormalization" class="advanced-select">
          <option value="none">None</option>
          <option value="standard">Standard (z-score)</option>
          <option value="minmax">Min-Max (0-1)</option>
          <option value="robust">Robust (median-based)</option>
        </select>
        <div class="normalization-note">
          <span class="note-text">Standard scaler (z-score normalization) will be used when normalization is enabled</span>
        </div>
      </div>

      <div class="option-group">
        <label>Missing Value Strategy:</label>
        <select v-model="missingValueStrategy" @change="emitConfiguration" class="advanced-select">
          <option value="keep">Keep as is</option>
          <option value="remove">Remove rows with missing values</option>
          <option value="fill_mean">Fill with column mean</option>
        </select>
        <div v-if="totalMissingValues > 0" class="missing-summary">
          <span class="missing-count">{{ totalMissingValues }} missing values detected</span>
        </div>
      </div>
    </div>

    <!-- Toggle Advanced -->
    <button @click="showAdvanced = !showAdvanced" class="toggle-advanced">
      {{ showAdvanced ? '🔼 Hide Advanced Options' : '🔽 Show Advanced Options' }}
    </button>

    <!-- Validation Messages -->
    <div v-if="validationErrors.length > 0" class="validation-errors">
      <h6>⚠️ Configuration Issues:</h6>
      <ul>
        <li v-for="error in validationErrors" :key="error">{{ error }}</li>
      </ul>
    </div>

    <!-- Column Details Modal -->
    <div v-if="selectedColumn" class="column-details-modal" @click="closeColumnDetails">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h5>📊 {{ selectedColumn.name }}</h5>
          <button @click="closeColumnDetails" class="close-btn">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-item">
            <strong>Type:</strong> {{ formatColumnType(selectedColumn.detectedType) }}
          </div>
          <div class="detail-item">
            <strong>Unique Values:</strong> {{ selectedColumn.uniqueCount }}
          </div>
          <div class="detail-item">
            <strong>Missing Values:</strong> {{ selectedColumn.missingCount }}
          </div>
          <div v-if="selectedColumn.sampleValues.length > 0" class="detail-item">
            <strong>Sample Values:</strong>
            <div class="sample-values">
              <span v-for="(value, index) in selectedColumn.sampleValues.slice(0, 5)" :key="index" class="sample-value">
                {{ value }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import CategoryMappingPreview from '~/components/CategoryMappingPreview.vue'

interface ColumnConfig {
  name: string
  detectedType: 'numeric' | 'categorical' | 'integer' | 'boolean' | 'mixed' | 'empty'
  usage: 'feature' | 'label' | 'ignore'
  index: number
  normalize: boolean
  oneHotEncode: boolean
  isCategorical: boolean
  uniqueCount: number
  missingCount: number
  sampleValues: string[]
}

interface Props {
  headers: string[]
  columnTypes: string[]
  categoricalColumns?: Set<number>
  columnInfo?: any[]
  initialMissingStrategy?: string
  initialNormalization?: string
  categoricalMappingsFromProcessing?: Record<string, any>
}

const props = withDefaults(defineProps<Props>(), {
  categoricalColumns: () => new Set(),
  columnInfo: () => [],
  initialMissingStrategy: 'keep',
  initialNormalization: 'none',
  categoricalMappingsFromProcessing: () => ({})
})

const emit = defineEmits<{
  'configuration-changed': [config: {
    featureColumns: number[]
    labelColumns: number[]
    ignoredColumns: number[]
    columnConfigs: any[]
    missingValueStrategy: string
    normalization: string
  }]
}>()

// State
const columns = ref<ColumnConfig[]>([])
const showAdvanced = ref(false)
const selectedColumn = ref<ColumnConfig | null>(null)
const missingValueStrategy = ref(props.initialMissingStrategy)
const defaultNormalization = ref(props.initialNormalization)

// Computed
const featureCount = computed(() => columns.value.filter(col => col.usage === 'feature').length)
const labelCount = computed(() => columns.value.filter(col => col.usage === 'label').length)
const ignoredCount = computed(() => columns.value.filter(col => col.usage === 'ignore').length)
const totalMissingValues = computed(() => {
  return columns.value.reduce((total, col) => total + (col.missingCount || 0), 0)
})

const validationErrors = computed(() => {
  const errors = []
  
  if (featureCount.value === 0) {
    errors.push('At least one feature column is required for clustering')
  }
  
  if (labelCount.value > 1) {
    errors.push('Only one label column is allowed for ARI calculation')
  }
  
  const totalColumns = props.headers.length
  if (ignoredCount.value === totalColumns) {
    errors.push('Cannot ignore all columns')
  }
  
  return errors
})

// Initialize columns
const initializeColumns = () => {
  columns.value = props.headers.map((header, index) => {
    const detectedType = (props.columnTypes[index] as ColumnConfig['detectedType']) || 'mixed'
    const columnInfo = props.columnInfo[index] || {}
    
    // Smart usage detection
    let usage: ColumnConfig['usage'] = 'feature'
    const headerLower = header.toLowerCase()
    
    // Check for label indicators
    const labelKeywords = ['label', 'target', 'class', 'category', 'group', 'cluster', 'y', 'ground_truth', 'true_label']
    if (labelKeywords.some(keyword => headerLower.includes(keyword))) {
      usage = 'label'
    }
    
    // Check for ID or index columns to ignore
    const ignoreKeywords = ['id', 'index', 'row_number', 'timestamp', 'date']
    if (ignoreKeywords.some(keyword => headerLower.includes(keyword))) {
      usage = 'ignore'
    }
    
    return {
      name: header,
      detectedType,
      usage,
      index,
      normalize: (detectedType === 'numeric' || detectedType === 'integer') && !(props.categoricalColumns.has(index) || detectedType === 'categorical'),
      oneHotEncode: detectedType === 'categorical',
      isCategorical: props.categoricalColumns.has(index) || detectedType === 'categorical',
      uniqueCount: columnInfo.unique_count || 0,
      missingCount: columnInfo.null_count || 0,
      sampleValues: columnInfo.sample_values || []
    }
  })
  
  // Ensure only one label column
  const labelColumns = columns.value.filter(col => col.usage === 'label')
  if (labelColumns.length > 1) {
    labelColumns.slice(1).forEach(col => col.usage = 'feature')
  }
  
  emitConfiguration()
}

// Methods
const selectAllAsFeatures = () => {
  columns.value.forEach(col => {
    if (col.usage !== 'ignore') {
      col.usage = 'feature'
    }
  })
  emitConfiguration()
}

const autoDetectTypes = () => {
  columns.value.forEach(col => {
    const headerLower = col.name.toLowerCase()
    
    // Reset to feature first
    col.usage = 'feature'
    
    // Check for label indicators
    const labelKeywords = ['label', 'target', 'class', 'category', 'group', 'cluster', 'y', 'ground_truth', 'true_label']
    if (labelKeywords.some(keyword => headerLower.includes(keyword))) {
      col.usage = 'label'
    }
    
    // Check for columns to ignore
    const ignoreKeywords = ['id', 'index', 'row_number', 'timestamp', 'date']
    if (ignoreKeywords.some(keyword => headerLower.includes(keyword))) {
      col.usage = 'ignore'
    }
    
    // Set normalization based on type
    col.normalize = (col.detectedType === 'numeric' || col.detectedType === 'integer') && col.usage === 'feature'
    col.oneHotEncode = col.detectedType === 'categorical' && col.usage === 'feature'
  })
  
  // Ensure only one label
  const labelColumns = columns.value.filter(col => col.usage === 'label')
  if (labelColumns.length > 1) {
    labelColumns.slice(1).forEach(col => col.usage = 'feature')
  }
  
  emitConfiguration()
}

const resetConfiguration = () => {
  initializeColumns()
}

const handleUsageChange = (column: ColumnConfig, index: number) => {
  // If setting as label, make sure only one label exists
  if (column.usage === 'label') {
    columns.value.forEach((col, i) => {
      if (i !== index && col.usage === 'label') {
        col.usage = 'feature'
      }
    })
  }
  
  // Update normalization and encoding based on usage
  if (column.usage === 'feature') {
    // Don't normalize categorical columns even if they're features
    column.normalize = (column.detectedType === 'numeric' || column.detectedType === 'integer') && !column.isCategorical
    column.oneHotEncode = column.detectedType === 'categorical'
  } else {
    column.normalize = false
    column.oneHotEncode = false
  }
  
  emitConfiguration()
}

const toggleNormalization = (column: ColumnConfig) => {
  column.normalize = !column.normalize
  
  // Warn about normalizing categorical columns
  if (column.normalize && column.isCategorical) {
    console.warn(`Warning: Normalization enabled for categorical column "${column.name}". This may cause issues with label encoding.`)
  }
  
  emitConfiguration()
}

const toggleEncoding = (column: ColumnConfig) => {
  column.oneHotEncode = !column.oneHotEncode
  emitConfiguration()
}

const showColumnDetails = (column: ColumnConfig) => {
  selectedColumn.value = column
}

const closeColumnDetails = () => {
  selectedColumn.value = null
}

const applyDefaultNormalization = () => {
  if (defaultNormalization.value !== 'none') {
    columns.value.forEach(col => {
      if (col.usage === 'feature' && (col.detectedType === 'numeric' || col.detectedType === 'integer')) {
        col.normalize = true
      }
    })
  } else {
    columns.value.forEach(col => {
      col.normalize = false
    })
  }
  emitConfiguration()
}

const formatColumnType = (type: string): string => {
  const typeMap = {
    'numeric': 'Numeric',
    'categorical': 'Categorical',
    'integer': 'Integer',
    'boolean': 'Boolean',
    'mixed': 'Mixed',
    'empty': 'Empty'
  }
  return typeMap[type as keyof typeof typeMap] || type
}

const getColumnPreview = (column: ColumnConfig): string => {
  if (column.sampleValues.length > 0) {
    return column.sampleValues.slice(0, 3).join(', ')
  }
  return 'No preview available'
}

const hasColumnIssues = (column: ColumnConfig): boolean => {
  return getColumnIssues(column).length > 0
}

const getColumnIssues = (column: ColumnConfig): string[] => {
  const issues = []
  
  if (column.missingCount > 0) {
    const percentage = Math.round((column.missingCount / (column.missingCount + column.uniqueCount)) * 100)
    if (percentage > 50) {
      issues.push(`High missing values (${percentage}%)`)
    }
  }
  
  if (column.usage === 'feature' && column.detectedType === 'empty') {
    issues.push('Column appears to be empty')
  }
  
  if (column.usage === 'feature' && column.uniqueCount === 1) {
    issues.push('Column has only one unique value')
  }
  
  return issues
}

const emitConfiguration = () => {
  const featureColumns = columns.value
    .filter(col => col.usage === 'feature')
    .map(col => col.index)
  
  const labelColumns = columns.value
    .filter(col => col.usage === 'label')
    .map(col => col.index)
  
  const ignoredColumns = columns.value
    .filter(col => col.usage === 'ignore')
    .map(col => col.index)
  
  const columnConfigs = columns.value.map(col => ({
    name: col.name,
    index: col.index,
    usage: col.usage,
    dataType: col.detectedType,
    normalize: col.normalize,
    oneHotEncode: col.oneHotEncode,
    isCategorical: col.isCategorical
  }))
  
  emit('configuration-changed', {
    featureColumns,
    labelColumns,
    ignoredColumns,
    columnConfigs,
    missingValueStrategy: missingValueStrategy.value,
    normalization: defaultNormalization.value
  })
}

// Initialize on mount and when props change
onMounted(() => {
  initializeColumns()
})

watch(() => [props.headers, props.columnTypes], () => {
  initializeColumns()
}, { deep: true })
</script>

<style scoped>
.enhanced-column-config {
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.config-header {
  padding: 20px;
  background: white;
  border-bottom: 1px solid #e2e8f0;
}

.config-header h4 {
  margin: 0 0 8px 0;
  color: #1f2937;
  font-size: 1.125rem;
  font-weight: 600;
}

.config-header p {
  margin: 0 0 16px 0;
  color: #6b7280;
  font-size: 0.875rem;
}

.quick-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-action-btn {
  padding: 6px 12px;
  background: #e5e7eb;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-action-btn:hover {
  background: #d1d5db;
  border-color: #9ca3af;
}

.config-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 20px;
  background: #f8fafc;
}

.summary-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.summary-icon {
  font-size: 1.5rem;
}

.summary-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
}

.summary-label {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 500;
}

.summary-card.feature { border-left: 4px solid #3b82f6; }
.summary-card.label { border-left: 4px solid #10b981; }
.summary-card.ignored { border-left: 4px solid #ef4444; }

.missing-summary {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #f59e0b;
  font-weight: 500;
}

.missing-count {
  background: #fef3c7;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #f59e0b;
}

.column-list {
  background: white;
}

.list-header {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr;
  gap: 16px;
  padding: 16px 20px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-weight: 600;
  font-size: 0.75rem;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.column-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  transition: all 0.2s ease;
}

.column-row:hover {
  background: #f8fafc;
}

.column-row.has-issues {
  background: #fef2f2;
  border-left: 3px solid #f59e0b;
}

.column-name {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.name-text {
  font-weight: 500;
  color: #111827;
}

.column-preview {
  font-size: 0.75rem;
  color: #6b7280;
  font-family: monospace;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.column-type {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.type-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
}

.type-badge.numeric,
.type-badge.integer {
  background: #dbeafe;
  color: #1e40af;
}

.type-badge.categorical {
  background: #fef3c7;
  color: #92400e;
}

.type-badge.boolean {
  background: #d1fae5;
  color: #065f46;
}

.type-badge.mixed {
  background: #f3e8ff;
  color: #7c3aed;
}

.type-badge.empty {
  background: #f1f5f9;
  color: #64748b;
}

.categorical-indicator {
  font-size: 0.7rem;
  color: #6b7280;
}

.usage-select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 0.875rem;
  font-weight: 500;
}

.usage-select.feature {
  border-color: #3b82f6;
  background: #eff6ff;
}

.usage-select.label {
  border-color: #10b981;
  background: #ecfdf5;
}

.usage-select.ignore {
  border-color: #ef4444;
  background: #fef2f2;
}

.column-actions {
  display: flex;
  gap: 4px;
}

.action-btn {
  padding: 4px 8px;
  background: #e5e7eb;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: #d1d5db;
}

.action-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #2563eb;
}

.column-issues {
  grid-column: 1 / -1;
  margin-top: 8px;
  padding: 8px;
  background: #fef3c7;
  border-radius: 6px;
  border: 1px solid #fcd34d;
}

.issue-item {
  font-size: 0.75rem;
  color: #92400e;
  margin-bottom: 4px;
}

.issue-item:last-child {
  margin-bottom: 0;
}

.advanced-options {
  padding: 20px;
  background: #f8fafc;
  border-top: 1px solid #e5e7eb;
}

.advanced-options h5 {
  margin: 0 0 16px 0;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 600;
}

.option-group {
  margin-bottom: 16px;
}

.option-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.advanced-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: white;
  font-size: 0.875rem;
}

.normalization-note {
  margin-top: 8px;
  padding: 8px 12px;
  background: #f0f9ff;
  border: 1px solid #e0f2fe;
  border-radius: 4px;
}

.note-text {
  font-size: 0.75rem;
  color: #0369a1;
  font-style: italic;
}

.toggle-advanced {
  width: 100%;
  padding: 12px;
  background: #f3f4f6;
  border: none;
  border-top: 1px solid #e5e7eb;
  font-size: 0.875rem;
  font-weight: 500;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-advanced:hover {
  background: #e5e7eb;
}

.validation-errors {
  padding: 16px 20px;
  background: #fef2f2;
  border-top: 1px solid #fecaca;
}

.validation-errors h6 {
  margin: 0 0 8px 0;
  color: #dc2626;
  font-size: 0.875rem;
  font-weight: 600;
}

.validation-errors ul {
  margin: 0;
  padding-left: 20px;
}

.validation-errors li {
  color: #dc2626;
  font-size: 0.875rem;
  margin-bottom: 4px;
}

.column-details-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h5 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: #6b7280;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 20px;
}

.detail-item {
  margin-bottom: 12px;
}

.detail-item strong {
  color: #374151;
  margin-right: 8px;
}

.sample-values {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.sample-value {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-family: monospace;
}

/* Responsive Design */
@media (max-width: 768px) {
  .config-summary {
    grid-template-columns: 1fr;
  }
  
  .list-header,
  .column-row {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  
  .column-actions {
    justify-content: flex-start;
  }
  
  .quick-actions {
    flex-direction: column;
  }
  
  .modal-content {
    margin: 20px;
    width: calc(100% - 40px);
  }
}
</style>