<template>
  <div class="category-mapping-preview">
    <div class="mapping-header">
      <h5>🏷️ Categorical Data Mappings</h5>
      <p>View how categorical values are encoded to numbers</p>
    </div>

    <div v-if="!hasCategoricalMappings" class="no-mappings">
      <div class="no-mappings-icon">📊</div>
      <p>No categorical columns detected or no mappings available</p>
    </div>

    <div v-else class="mappings-container">
      <div 
        v-for="(mapping, columnName) in categoricalMappings" 
        :key="columnName"
        class="mapping-section"
      >
        <div class="column-header">
          <h6>{{ columnName }}</h6>
          <div class="encoding-info">
            <span class="encoding-badge" :class="mapping.encoding_method">
              {{ mapping.encoding_method === 'label' ? 'Label Encoding' : 'One-Hot Encoding' }}
            </span>
            <span class="count-badge">{{ mapping.unique_count || mapping.classes?.length || 0 }} unique values</span>
          </div>
        </div>

        <!-- Label Encoding Mapping -->
        <div v-if="mapping.encoding_method === 'label'" class="label-mapping">
          <div class="mapping-table">
            <div class="table-header">
              <span>Original Value</span>
              <span>Encoded As</span>
            </div>
            <div 
              v-for="(encodedValue, originalValue) in mapping.mapping" 
              :key="originalValue"
              class="mapping-row"
            >
              <span class="original-value">{{ originalValue }}</span>
              <span class="encoded-value">{{ encodedValue }}</span>
            </div>
          </div>
        </div>

        <!-- One-Hot Encoding Mapping -->
        <div v-else-if="mapping.encoding_method === 'onehot'" class="onehot-mapping">
          <div class="onehot-info">
            <p>Each unique value becomes a separate binary column:</p>
          </div>
          <div class="onehot-columns">
            <div 
              v-for="(columnName, originalValue) in mapping.mapping"
              :key="originalValue"
              class="onehot-column"
            >
              <span class="original-value">{{ originalValue }}</span>
              <span class="arrow">→</span>
              <span class="new-column">{{ columnName }}</span>
            </div>
          </div>
        </div>

        <!-- Warning for high cardinality -->
        <div v-if="(mapping.unique_count || mapping.classes?.length || 0) > 10" class="cardinality-warning">
          <div class="warning-icon">⚠️</div>
          <div class="warning-text">
            <strong>High cardinality detected:</strong> 
            This column has {{ mapping.unique_count || mapping.classes?.length }} unique values. 
            Consider using label encoding or grouping values to reduce dimensionality.
          </div>
        </div>
      </div>
    </div>

    <!-- Export Options -->
    <div v-if="hasCategoricalMappings" class="export-options">
      <button @click="exportMappings" class="export-btn">
        📤 Export Mappings as CSV
      </button>
      <button @click="copyMappings" class="copy-btn">
        📋 Copy to Clipboard
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface CategoricalMapping {
  encoding_method: 'label' | 'onehot'
  classes?: string[]
  mapping?: Record<string, any>
  reverse_mapping?: Record<number, string>
  new_columns?: string[]
  original_values?: string[]
  unique_count?: number
}

interface Props {
  categoricalMappings: Record<string, CategoricalMapping>
}

const props = defineProps<Props>()

const hasCategoricalMappings = computed(() => {
  return Object.keys(props.categoricalMappings).length > 0
})

const exportMappings = () => {
  if (!hasCategoricalMappings.value) return

  let csv = 'Column,Original Value,Encoded Value/Column\n'
  
  Object.entries(props.categoricalMappings).forEach(([columnName, mapping]) => {
    if (mapping.encoding_method === 'label' && mapping.mapping) {
      Object.entries(mapping.mapping).forEach(([original, encoded]) => {
        csv += `"${columnName}","${original}","${encoded}"\n`
      })
    } else if (mapping.encoding_method === 'onehot' && mapping.mapping) {
      Object.entries(mapping.mapping).forEach(([original, newColumn]) => {
        csv += `"${columnName}","${original}","${newColumn}"\n`
      })
    }
  })

  // Create and download CSV file
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'categorical_mappings.csv'
  a.click()
  window.URL.revokeObjectURL(url)
}

const copyMappings = async () => {
  if (!hasCategoricalMappings.value) return

  let text = 'Categorical Data Mappings:\n\n'
  
  Object.entries(props.categoricalMappings).forEach(([columnName, mapping]) => {
    text += `${columnName} (${mapping.encoding_method} encoding):\n`
    
    if (mapping.encoding_method === 'label' && mapping.mapping) {
      Object.entries(mapping.mapping).forEach(([original, encoded]) => {
        text += `  "${original}" → ${encoded}\n`
      })
    } else if (mapping.encoding_method === 'onehot' && mapping.mapping) {
      Object.entries(mapping.mapping).forEach(([original, newColumn]) => {
        text += `  "${original}" → ${newColumn}\n`
      })
    }
    text += '\n'
  })

  try {
    await navigator.clipboard.writeText(text)
    // Could emit an event or show a toast notification here
  } catch (err) {
    console.error('Failed to copy to clipboard:', err)
  }
}
</script>

<style scoped>
.category-mapping-preview {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
}

.mapping-header h5 {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px 0;
}

.mapping-header p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0 0 16px 0;
}

.no-mappings {
  text-align: center;
  padding: 24px;
  color: #9ca3af;
}

.no-mappings-icon {
  font-size: 2rem;
  margin-bottom: 8px;
}

.mappings-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mapping-section {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 16px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.column-header h6 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.encoding-info {
  display: flex;
  gap: 8px;
}

.encoding-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.encoding-badge.label {
  background: #dbeafe;
  color: #1d4ed8;
}

.encoding-badge.onehot {
  background: #d1fae5;
  color: #059669;
}

.count-badge {
  padding: 2px 8px;
  background: #f3f4f6;
  color: #6b7280;
  border-radius: 12px;
  font-size: 0.75rem;
}

.label-mapping .mapping-table {
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
}

.table-header {
  display: grid;
  grid-template-columns: 1fr 120px;
  background: #f9fafb;
  padding: 8px 12px;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
}

.mapping-row {
  display: grid;
  grid-template-columns: 1fr 120px;
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.875rem;
}

.mapping-row:last-child {
  border-bottom: none;
}

.original-value {
  color: #374151;
  font-family: 'Monaco', 'Menlo', monospace;
}

.encoded-value {
  color: #1d4ed8;
  font-weight: 500;
  text-align: center;
}

.onehot-info {
  margin-bottom: 12px;
}

.onehot-info p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

.onehot-columns {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.onehot-column {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 4px;
  font-size: 0.875rem;
}

.arrow {
  color: #9ca3af;
  font-weight: 500;
}

.new-column {
  color: #059669;
  font-family: 'Monaco', 'Menlo', monospace;
  font-weight: 500;
}

.cardinality-warning {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 4px;
}

.warning-icon {
  flex-shrink: 0;
}

.warning-text {
  font-size: 0.875rem;
  color: #92400e;
}

.export-options {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.export-btn, .copy-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  color: #374151;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.export-btn:hover, .copy-btn:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.export-btn:active, .copy-btn:active {
  background: #f3f4f6;
}

/* Responsive Design */
@media (max-width: 640px) {
  .column-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .table-header, .mapping-row {
    grid-template-columns: 1fr 80px;
  }
  
  .onehot-column {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .export-options {
    flex-direction: column;
  }
}
</style>