<template>
  <div class="column-configuration">
    <div class="config-header">
      <h4>Column Configuration</h4>
      <p>Configure how each column should be used in the analysis</p>
    </div>
    
    <div class="columns-grid">
      <div 
        v-for="(column, index) in columns" 
        :key="index"
        class="column-item"
      >
        <div class="column-header">
          <span class="column-name">{{ column.name }}</span>
          <span class="column-type" :class="column.type">{{ formatColumnType(column.type) }}</span>
        </div>
        
        <div class="column-usage">
          <select 
            v-model="column.usage" 
            @change="handleColumnUsageChange"
            class="usage-select"
          >
            <option value="feature">Feature</option>
            <option value="label">Label/Target</option>
            <option value="ignore">Ignore</option>
          </select>
        </div>
        
        <div v-if="column.usage === 'label'" class="label-info">
          <div class="info-badge">
            <span class="info-icon">🎯</span>
            <span>Will be used for ARI calculation</span>
          </div>
        </div>
      </div>
    </div>
    
    <div class="configuration-summary">
      <div class="summary-item">
        <span class="summary-label">Features:</span>
        <span class="summary-value">{{ featureCount }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Labels:</span>
        <span class="summary-value">{{ labelCount }}</span>
      </div>
      <div class="summary-item">
        <span class="summary-label">Ignored:</span>
        <span class="summary-value">{{ ignoredCount }}</span>
      </div>
    </div>
    
    <div v-if="labelCount > 1" class="warning-message">
      <div class="warning-icon">⚠️</div>
      <span>Multiple label columns detected. Only the first one will be used for ARI calculation.</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface Column {
  name: string
  type: 'numeric' | 'categorical' | 'integer' | 'boolean' | 'mixed' | 'empty'
  usage: 'feature' | 'label' | 'ignore'
  index: number
}

interface Props {
  headers: string[]
  columnTypes: string[]
  categoricalColumns?: Set<number>
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'configuration-changed': [config: {
    featureColumns: number[]
    labelColumns: number[]
    ignoredColumns: number[]
  }]
}>()

// Initialize columns with smart defaults
const columns = ref<Column[]>([])

const initializeColumns = () => {
  columns.value = props.headers.map((header, index) => {
    const type = props.columnTypes[index] as Column['type'] || 'numeric'
    
    // Smart defaults for usage based on column name and type
    let usage: 'feature' | 'label' | 'ignore' = 'feature'
    
    // Check if column name suggests it's a label/target
    const headerLower = header.toLowerCase()
    const labelKeywords = ['label', 'target', 'class', 'category', 'group', 'cluster', 'y', 'ground_truth', 'true_label']
    
    if (labelKeywords.some(keyword => headerLower.includes(keyword))) {
      usage = 'label'
    } else if (type === 'categorical' && props.categoricalColumns?.has(index)) {
      // Suggest categorical columns as potential labels
      usage = 'label'
    }
    
    return {
      name: header,
      type,
      usage,
      index
    }
  })
  
  // Ensure only one label column is selected by default
  const labelIndices = columns.value.map((col, idx) => col.usage === 'label' ? idx : -1).filter(idx => idx >= 0)
  if (labelIndices.length > 1) {
    // Keep only the first label column, make others features
    labelIndices.slice(1).forEach(idx => {
      columns.value[idx].usage = 'feature'
    })
  }
  
  emitConfiguration()
}

// Computed values
const featureCount = computed(() => columns.value.filter(col => col.usage === 'feature').length)
const labelCount = computed(() => columns.value.filter(col => col.usage === 'label').length)
const ignoredCount = computed(() => columns.value.filter(col => col.usage === 'ignore').length)

// Methods
const formatColumnType = (type: string): string => {
  const typeMap: Record<string, string> = {
    'numeric': 'Numeric',
    'categorical': 'Categorical',
    'integer': 'Integer',
    'boolean': 'Boolean',
    'mixed': 'Mixed',
    'empty': 'Empty'
  }
  return typeMap[type] || type
}

const handleColumnUsageChange = () => {
  // Ensure only one label column
  const labelColumns = columns.value.filter(col => col.usage === 'label')
  if (labelColumns.length > 1) {
    // Keep the most recently changed one, make others features
    const lastChanged = labelColumns[labelColumns.length - 1]
    columns.value.forEach(col => {
      if (col.usage === 'label' && col !== lastChanged) {
        col.usage = 'feature'
      }
    })
  }
  
  emitConfiguration()
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
  
  emit('configuration-changed', {
    featureColumns,
    labelColumns,
    ignoredColumns
  })
}

// Watch for prop changes and reinitialize
watch(() => [props.headers, props.columnTypes], () => {
  initializeColumns()
}, { immediate: true })
</script>

<style scoped>
.column-configuration {
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  margin-top: 16px;
}

.config-header {
  margin-bottom: 20px;
}

.config-header h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px 0;
}

.config-header p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

.columns-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.column-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.column-name {
  font-weight: 500;
  color: #374151;
  flex: 1;
}

.column-type {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.column-type.numeric,
.column-type.integer {
  background: #dbeafe;
  color: #1e40af;
}

.column-type.categorical {
  background: #fef3c7;
  color: #92400e;
}

.column-type.boolean {
  background: #d1fae5;
  color: #065f46;
}

.column-type.mixed {
  background: #f3e8ff;
  color: #7c3aed;
}

.column-type.empty {
  background: #f1f5f9;
  color: #64748b;
}

.column-usage {
  margin-bottom: 8px;
}

.usage-select {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  font-size: 0.875rem;
  color: #374151;
}

.usage-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.label-info {
  margin-top: 8px;
}

.info-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: #ecfdf5;
  border: 1px solid #d1fae5;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #065f46;
}

.info-icon {
  font-size: 0.875rem;
}

.configuration-summary {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 12px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.summary-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.summary-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
}

.warning-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #92400e;
}

.warning-icon {
  font-size: 1rem;
}

/* Responsive */
@media (max-width: 640px) {
  .column-configuration {
    padding: 16px;
  }
  
  .configuration-summary {
    flex-direction: column;
    gap: 8px;
  }
  
  .column-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>