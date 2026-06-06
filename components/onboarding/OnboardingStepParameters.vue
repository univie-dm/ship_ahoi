<template>
  <div class="parameters-step">
    <div class="step-header">
      <h2>Configure Parameters</h2>
      <p>Choose the optimal clustering parameters for your analysis</p>
    </div>

    <div v-if="isLoadingOptions" class="loading-state">
      <div class="spinner"></div>
      <p>Loading parameter options...</p>
    </div>

    <div v-else class="parameters-container">
      <!-- Tree Type Selection -->
      <div class="parameter-group">
        <label class="parameter-label">Tree Type</label>
        <p class="parameter-description">
          Determines how the hierarchical structure is built from your data points
        </p>
        <select v-model="parameters.treeType" class="parameter-select">
          <option v-for="type in availableTreeTypes" :key="type" :value="type">
            {{ type }}
          </option>
        </select>
        <div class="parameter-help">
          <div v-if="parameters.treeType === 'MST'">
            <strong>MST (Minimum Spanning Tree):</strong> Creates a tree that connects all points with minimum total edge weight. Best for well-separated clusters.
          </div>
          <div v-else-if="parameters.treeType === 'KNN'">
            <strong>KNN (K-Nearest Neighbors):</strong> Each point connects to its K nearest neighbors. Good for varying densities and complex structures.
          </div>
          <div v-else-if="parameters.treeType === 'MCSM'">
            <strong>MCSM (Mutual Cluster Spanning Tree):</strong> Balances local and global structure. Suitable for overlapping clusters.
          </div>
        </div>
      </div>

      <!-- Partition Method Selection -->
      <div class="parameter-group">
        <label class="parameter-label">Partition Method</label>
        <p class="parameter-description">
          Method used to determine the optimal number of clusters in your data
        </p>
        <select v-model="parameters.partitionMethod" class="parameter-select">
          <option v-for="method in availablePartitionMethods" :key="method" :value="method">
            {{ method }}
          </option>
        </select>
        <div class="parameter-help">
          <div v-if="parameters.partitionMethod === 'K'">
            <strong>K (Fixed):</strong> Use a specific number of clusters that you define.
          </div>
          <div v-else-if="parameters.partitionMethod === 'SILHOUETTE'">
            <strong>SILHOUETTE:</strong> Automatically finds the number of clusters that maximizes cluster separation and cohesion.
          </div>
          <div v-else-if="parameters.partitionMethod === 'ARI'">
            <strong>ARI (Adjusted Rand Index):</strong> Optimizes clustering quality based on statistical measures.
          </div>
          <div v-else-if="parameters.partitionMethod === 'GAP'">
            <strong>GAP:</strong> Compares clustering structure against random data to find optimal cluster count.
          </div>
        </div>
      </div>

      <!-- Power Parameter -->
      <div class="parameter-group">
        <label class="parameter-label">Power Parameter: {{ parameters.power }}</label>
        <p class="parameter-description">
          Controls the influence of distance in the clustering algorithm (higher = more emphasis on close neighbors)
        </p>
        <div class="slider-container">
          <input 
            type="range" 
            min="1" 
            max="5" 
            step="1"
            v-model.number="parameters.power"
            class="parameter-slider"
          />
          <div class="slider-labels">
            <span>1</span>
            <span>2</span>
            <span>3</span>
            <span>4</span>
            <span>5</span>
          </div>
        </div>
      </div>

      <!-- K Parameter (only show if partition method is K) -->
      <div v-if="parameters.partitionMethod === 'K'" class="parameter-group">
        <label class="parameter-label">Number of Clusters: {{ parameters.k }}</label>
        <p class="parameter-description">
          Specify the exact number of clusters you want to create
        </p>
        <div class="slider-container">
          <input 
            type="range" 
            min="2" 
            max="20" 
            step="1"
            v-model.number="parameters.k"
            class="parameter-slider"
          />
          <div class="slider-labels">
            <span>2</span>
            <span>5</span>
            <span>10</span>
            <span>15</span>
            <span>20</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Preview -->
    <div v-if="!isLoadingOptions" class="parameter-preview">
      <h4>Parameter Summary</h4>
      <div class="preview-grid">
        <div class="preview-item">
          <span class="preview-label">Tree Type:</span>
          <span class="preview-value">{{ parameters.treeType }}</span>
        </div>
        <div class="preview-item">
          <span class="preview-label">Partition Method:</span>
          <span class="preview-value">{{ parameters.partitionMethod }}</span>
        </div>
        <div class="preview-item">
          <span class="preview-label">Power:</span>
          <span class="preview-value">{{ parameters.power }}</span>
        </div>
        <div v-if="parameters.partitionMethod === 'K'" class="preview-item">
          <span class="preview-label">Number of Clusters:</span>
          <span class="preview-value">{{ parameters.k }}</span>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <div class="navigation">
      <button @click="$emit('back')" class="back-btn">
        ← Back
      </button>
      <button 
        @click="confirmParameters" 
        class="continue-btn"
        :disabled="isLoadingOptions"
      >
        Start Analysis →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

const emit = defineEmits(['parameters-set', 'back']);

// Loading state
const isLoadingOptions = ref(true);

// Available options from backend
const availableTreeTypes = ref<string[]>([]);
const availablePartitionMethods = ref<string[]>([]);

// Parameters
const parameters = ref({
  treeType: '',
  partitionMethod: '',
  power: 2,
  k: 5
});

// Load available options from backend
const loadParameterOptions = async () => {
  try {
    isLoadingOptions.value = true;
    
    const options = await $fetch('/api/cluster/options');
    availableTreeTypes.value = options.treeTypes || [];
    availablePartitionMethods.value = options.partitionMethods || [];
    
    // Set default values from first available options
    if (availableTreeTypes.value.length > 0 && !parameters.value.treeType) {
      parameters.value.treeType = availableTreeTypes.value[0];
    }
    if (availablePartitionMethods.value.length > 0 && !parameters.value.partitionMethod) {
      parameters.value.partitionMethod = availablePartitionMethods.value[0];
    }
    
    console.log('Loaded parameter options:', {
      treeTypes: availableTreeTypes.value,
      partitionMethods: availablePartitionMethods.value
    });
  } catch (error) {
    console.error('Error loading parameter options:', error);
    // Fallback to default options
    availableTreeTypes.value = ['MST', 'KNN', 'MCSM'];
    availablePartitionMethods.value = ['SILHOUETTE', 'K', 'ARI', 'GAP'];
    parameters.value.treeType = 'MST';
    parameters.value.partitionMethod = 'SILHOUETTE';
  } finally {
    isLoadingOptions.value = false;
  }
};

const confirmParameters = () => {
  emit('parameters-set', parameters.value);
};

// Load options when component mounts
onMounted(() => {
  loadParameterOptions();
});
</script>

<style scoped>
.parameters-step {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.step-header {
  text-align: center;
}

.step-header h2 {
  font-size: 1.75rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 8px 0;
}

.step-header p {
  color: #64748b;
  margin: 0;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.parameters-container {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.parameter-group {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
}

.parameter-label {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1a202c;
  display: block;
  margin-bottom: 8px;
}

.parameter-description {
  color: #64748b;
  margin-bottom: 16px;
  line-height: 1.5;
}

.parameter-select {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
  background: white;
  color: #1a202c;
  transition: border-color 0.2s ease;
}

.parameter-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.parameter-help {
  margin-top: 12px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #475569;
  line-height: 1.4;
}

.parameter-help strong {
  color: #1a202c;
}

.slider-container {
  margin-top: 12px;
}

.parameter-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  -webkit-appearance: none;
  margin-bottom: 12px;
}

.parameter-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.parameter-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #9ca3af;
}

.parameter-preview {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
}

.parameter-preview h4 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 16px 0;
}

.preview-grid {
  display: grid;
  gap: 12px;
}

.preview-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
}

.preview-label {
  font-weight: 500;
  color: #64748b;
}

.preview-value {
  font-weight: 600;
  color: #1a202c;
}

.navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: #e2e8f0;
  color: #475569;
}

.continue-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.continue-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
}

.continue-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
}
</style>
