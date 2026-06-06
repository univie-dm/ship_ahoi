<template>
  <div class="history-controls">
    <div class="filter-section">
      <select :value="filterDataset" @input="$emit('update:filterDataset', $event.target.value)" class="filter-select">
        <option value="">All Datasets</option>
        <option v-for="dataset in uniqueDatasets" :key="dataset" :value="dataset">
          {{ dataset }}
        </option>
      </select>
      
      <select :value="filterAlgorithm" @input="$emit('update:filterAlgorithm', $event.target.value)" class="filter-select">
        <option value="">All Algorithms</option>
        <option v-for="algo in uniqueAlgorithms" :key="algo" :value="algo">
          {{ algo }}
        </option>
      </select>
      
      <select :value="sortBy" @input="$emit('update:sortBy', $event.target.value)" class="filter-select">
        <option value="timestamp">Sort by Date</option>
        <option value="dataset">Sort by Dataset</option>
        <option value="treeType">Sort by Algorithm</option>
        <option value="selectedK">Sort by K Value</option>
        <option value="silhouetteScore">Sort by Silhouette Score</option>
        <option value="dbIndex">Sort by DB Index</option>
        <option value="calinskiHarabasz">Sort by Calinski-Harabasz Index</option>
        <option value="ari">Sort by ARI</option>
        <option value="discoScore">Sort by DISCO Score</option>
      </select>
    </div>

    <div class="view-controls">
      <button 
        :class="['view-btn', { active: viewMode === 'list' }]"
        @click="$emit('update:viewMode', 'list')"
      >
        📋 List
      </button>
      <button 
        :class="['view-btn', { active: viewMode === 'cards' }]"
        @click="$emit('update:viewMode', 'cards')"
      >
        🎴 Cards
      </button>
    </div>
    
    <div v-if="selectedCount > 0" class="selection-controls">
      <span class="selection-count">{{ selectedCount }} selected</span>
      <button @click="$emit('clearSelection')" class="clear-btn">
        Clear Selection
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  uniqueDatasets: string[]
  uniqueAlgorithms: string[]
  viewMode: 'list' | 'cards'
  selectedCount: number
  filterDataset: string
  filterAlgorithm: string
  sortBy: string
}

interface Emits {
  (e: 'update:filterDataset', value: string): void
  (e: 'update:filterAlgorithm', value: string): void
  (e: 'update:sortBy', value: string): void
  (e: 'update:viewMode', value: 'list' | 'cards'): void
  (e: 'clearSelection'): void
}

defineProps<Props>()
defineEmits<Emits>()
</script>

<style scoped>
.history-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  padding: 1rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.filter-section {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-select {
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  min-width: 140px;
}

.view-controls {
  display: flex;
  gap: 0.25rem;
}

.view-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.view-btn:hover {
  background: #f3f4f6;
}

.view-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.selection-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: auto;
}

.selection-count {
  font-size: 0.875rem;
  color: #6b7280;
}

.compare-btn, .clear-btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.compare-btn {
  background: #10b981;
  color: white;
  border: none;
}

.compare-btn:hover {
  background: #059669;
}

.clear-btn {
  background: #ef4444;
  color: white;
  border: none;
}

.clear-btn:hover {
  background: #dc2626;
}

@media (max-width: 768px) {
  .history-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .filter-section {
    order: 1;
  }
  
  .view-controls {
    order: 2;
    justify-content: center;
  }
  
  .selection-controls {
    order: 3;
    margin-left: 0;
    justify-content: center;
  }
  
  .filter-select {
    min-width: 120px;
  }
}
</style>