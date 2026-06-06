<template>
  <div class="data-status-section">
    <div v-if="!currentDataset" class="no-data-status">
      <div class="status-icon">📁</div>
      <h4>No Data Loaded</h4>
      <p>Upload data or select a sample to get started</p>
      <button @click="navigateToUpload" class="upload-btn">
        📤 Upload Data
      </button>
    </div>
    
    <div v-else class="data-loaded-status">
      <div class="status-icon">✅</div>
      <h4>{{ datasetTitle }}</h4>
      <div class="data-details">
        <div class="detail-item">
          <span class="detail-label">Type:</span>
          <span class="detail-value">{{ datasetType }}</span>
        </div>
        <div v-if="currentDataset.pointCount" class="detail-item">
          <span class="detail-label">Points:</span>
          <span class="detail-value">{{ currentDataset.pointCount.toLocaleString() }}</span>
        </div>
        <div v-if="currentDataset.featureCount" class="detail-item">
          <span class="detail-label">Features:</span>
          <span class="detail-value">{{ currentDataset.featureCount }}</span>
        </div>
      </div>
      <div class="status-actions">
        <button @click="navigateToUpload" class="change-btn">
          🔄 Change Data
        </button>
        <button @click="clearData" class="clear-btn">
          🗑️ Clear
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useGlobalState } from '~/composables/useGlobalState'

const router = useRouter()
const globalState = useGlobalState()

const currentDataset = computed(() => globalState.currentDataset.value)

const datasetTitle = computed(() => {
  if (!currentDataset.value) return ''
  
  if (currentDataset.value.type === 'sample') {
    return `Sample: ${currentDataset.value.name}`
  } else {
    return currentDataset.value.fileName || currentDataset.value.name
  }
})

const datasetType = computed(() => {
  if (!currentDataset.value) return ''
  
  return currentDataset.value.type === 'sample' ? 'Sample Dataset' : 'Uploaded File'
})

const navigateToUpload = () => {
  router.push('/upload')
}

const clearData = () => {
  if (confirm('Are you sure you want to clear the current dataset?')) {
    globalState.clearDataset()
    // Navigate to upload page after clearing
    router.push('/upload')
  }
}
</script>

<style scoped>
.data-status-section {
  padding: 16px;
  background: var(--step-content-bg);
  border-radius: 8px;
  border: 1px solid var(--step-border-color);
}

.no-data-status {
  text-align: center;
  padding: 20px 10px;
}

.data-loaded-status {
  padding: 10px 0;
}

.status-icon {
  font-size: 2rem;
  margin-bottom: 12px;
}

.no-data-status h4,
.data-loaded-status h4 {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--text-color-primary);
}

.no-data-status p {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  margin: 0 0 16px 0;
}

.data-details {
  margin: 12px 0;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 0.9rem;
}

.detail-label {
  color: var(--text-color-secondary);
  font-weight: 500;
}

.detail-value {
  color: var(--text-color-primary);
  font-weight: 600;
}

.status-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.upload-btn {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 10px 16px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
}

.upload-btn:hover {
  background: var(--color-primary-dark, #2563eb);
  transform: translateY(-1px);
}

.change-btn {
  background: var(--color-info);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  flex: 1;
}

.change-btn:hover {
  background: var(--color-info-dark, #0891b2);
}

.clear-btn {
  background: var(--color-danger);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  flex: 1;
}

.clear-btn:hover {
  background: var(--color-danger-dark, #dc2626);
}
</style> 