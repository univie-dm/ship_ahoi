<template>
  <div 
    :class="[
      'run-card',
      { 
        'active-run': isActive,
        'selected-run': isSelected
      }
    ]"
    @click="$emit('toggleSelection', run.id)"
  >
    <div class="card-header">
      <input 
        type="checkbox" 
        :checked="isSelected"
        @click.stop
        @change="$emit('toggleSelection', run.id)"
        class="card-checkbox"
      />
      <span class="run-date">{{ formatDate(run.timestamp) }}</span>
    </div>

    <div class="card-content">
      <h4 class="run-title">{{ run.dataset }}</h4>
      <div class="run-details">
        <div class="detail-row">
          <span class="label">Algorithm:</span>
          <span class="value algorithm-badge" :class="getAlgorithmClass(run.treeType)">{{ run.treeType }}</span>
        </div>
        <div class="detail-row">
          <span class="label">Partition:</span>
          <span class="value">{{ run.partitionMethod }}</span>
        </div>
        <div class="detail-row">
          <span class="label">Clusters:</span>
          <span class="value">{{ getActualClusterCount(run) }}</span>
        </div>
        <div v-if="run.selectedPower" class="detail-row">
          <span class="label">Power:</span>
          <span class="value">{{ run.selectedPower }}</span>
        </div>
        
        <!-- Metrics display -->
        <div v-if="run.metrics" class="metrics-section">
          <div class="metrics-header">Performance Metrics</div>
          <div v-if="run.metrics.silhouetteScore !== undefined" class="detail-row metric-row">
            <span class="label">Silhouette:</span>
            <span class="value metric-value">{{ formatMetric(run.metrics.silhouetteScore) }}</span>
          </div>
          <div v-if="run.metrics.dbIndex !== undefined" class="detail-row metric-row">
            <span class="label">DB Index:</span>
            <span class="value metric-value">{{ formatMetric(run.metrics.dbIndex) }}</span>
          </div>
          <div v-if="run.metrics.calinskiHarabasz !== undefined" class="detail-row metric-row">
            <span class="label">CH Index:</span>
            <span class="value metric-value">{{ formatMetric(run.metrics.calinskiHarabasz,2) }}</span>
          </div>
          <div v-if="run.metrics.ari !== undefined" class="detail-row metric-row">
            <span class="label">ARI:</span>
            <span class="value metric-value ari-value">{{ formatMetric(run.metrics.ari) }}</span>
          </div>
          <div v-if="run.metrics.discoScore !== undefined" class="detail-row metric-row">
            <span class="label">DISCO:</span>
            <span class="value metric-value">{{ formatMetric(run.metrics.discoScore) }}</span>
          </div>
        </div>
        
        <div class="detail-row">
          <span class="label">Points:</span>
          <span class="value">{{ run.clusterData?.points?.length || 'N/A' }}</span>
        </div>
      </div>
    </div>

    <div class="card-actions">
      <button 
        @click.stop="$emit('loadRun', run.id)"
        class="card-action-btn load-btn"
        title="Load this clustering run"
      >
        📊 Load
      </button>
      <button 
        @click.stop="$emit('deleteRun', run.id)"
        class="card-action-btn delete-btn"
        title="Delete this run"
      >
        🗑️
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ClusterRun } from '~/composables/useGlobalState'

interface Props {
  run: ClusterRun
  isActive: boolean
  isSelected: boolean
}

interface Emits {
  (e: 'toggleSelection', runId: string): void
  (e: 'loadRun', runId: string): void
  (e: 'setActive', runId: string): void
  (e: 'deleteRun', runId: string): void
}

defineProps<Props>()
defineEmits<Emits>()

const formatDate = (timestamp: Date | string): string => {
  const d = new Date(timestamp);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getActualClusterCount = (run: ClusterRun): number => {
  // First, try to use the saved actualClusterCount (available for new runs)
  if (run.actualClusterCount !== undefined && run.actualClusterCount !== null) {
    return run.actualClusterCount
  }
  
  // Fallback: calculate from cluster labels (for backward compatibility)
  if (run.clusterData?.labels && Array.isArray(run.clusterData.labels)) {
    const uniqueLabels = new Set(run.clusterData.labels)
    return uniqueLabels.size
  }
  
  // Final fallback to selectedK if no clustering results available
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

const formatMetric = (val: number | undefined | null, digits: number = 3): string => {
  if (val === undefined || val === null || isNaN(val)) return 'N/A'
  return val.toFixed(digits)
}
</script>

<style scoped>
.run-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.run-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-color: #d1d5db;
}

.run-card.selected-run {
  border-color: #3b82f6;
  border-width: 2px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2);
  transform: translateY(-2px);
}

.run-card.active-run {
  border-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.card-checkbox {
  cursor: pointer;
  width: 18px;
  height: 18px;
  accent-color: #3b82f6;
}

.run-date {
  font-size: 0.875rem;
  color: #6b7280;
}

.card-content {
  margin-bottom: 1rem;
}

.run-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0 0 0.75rem 0;
  color: #1f2937;
}

.run-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.value {
  font-size: 0.875rem;
  color: #1f2937;
  font-weight: 600;
}

.algorithm-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.algorithm-ship {
  background: #dbeafe;
  color: #1d4ed8;
}

.algorithm-kmeans {
  background: #fef3c7;
  color: #d97706;
}

.algorithm-dbscan {
  background: #ecfdf5;
  color: #059669;
}

.algorithm-hierarchical {
  background: #fce7f3;
  color: #be185d;
}

.algorithm-default {
  background: #f3f4f6;
  color: #374151;
}

.metrics-section {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e5e7eb;
}

.metrics-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.metric-row {
  background: #f9fafb;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

.metric-value {
  font-family: monospace;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.card-action-btn {
  padding: 0.375rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.load-btn {
  background: #3b82f6;
  color: white;
}

.load-btn:hover {
  background: #2563eb;
}

.select-btn {
  background: #10b981;
  color: white;
}

.select-btn:hover {
  background: #059669;
}

.delete-btn {
  background: #ef4444;
  color: white;
}

.delete-btn:hover {
  background: #dc2626;
}

@media (max-width: 640px) {
  .run-card {
    padding: 0.75rem;
  }
  
  .card-actions {
    justify-content: stretch;
  }
  
  .card-action-btn {
    flex: 1;
    text-align: center;
  }
  
  .detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
  
  .value {
    margin-left: 0.5rem;
  }
}
</style>