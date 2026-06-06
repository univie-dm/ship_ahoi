<template>
  <div class="parameter-controls">
    <div class="form-group">
      <label for="tree-type-select">Tree Type</label>
      <select
        id="tree-type"
        v-model="localSelectedTreeType"
        class="control-select"
      >
        <option v-for="type in treeTypes" :key="type" :value="type">{{ type }}</option>
      </select>
    </div>
    
    <!-- Tree Visualization Options -->
    <div class="form-group">
      <label for="tree-visualization-select">Tree Visualization</label>
      <select
        id="tree-visualization"
        v-model="localTreeVisualizationType"
        class="control-select"
      >
        <option value="summarized">Tree Summarization (Optimized)</option>
        <option value="real">Real Tree (Full Detail)</option>
      </select>
      <div class="tree-option-description">
        <div v-if="localTreeVisualizationType === 'summarized'" class="option-explanation">
          <strong>Summarized Tree:</strong> {{ tooltips.sidebar.treeVisualizationType.summarized }}
        </div>
        <div v-if="localTreeVisualizationType === 'real'" class="option-explanation">
          <strong>Real Tree:</strong> {{ tooltips.sidebar.treeVisualizationType.real }}
        </div>
      </div>
    </div>
    
    <!-- Real Tree Depth Control (only shown when Real Tree is selected) -->
    <div v-if="localTreeVisualizationType === 'real'" class="form-group">
      <label for="real-tree-depth">
        <strong>Tree Depth (1-500)</strong>
      </label>
      <div class="depth-control-container">
        <input
          type="range"
          id="real-tree-depth"
          v-model="localRealTreeDepth"
          min="1"
          max="500"
          step="1"
          class="control-range"
        />
        <input
          type="number"
          v-model="localRealTreeDepth"
          min="1"
          max="500"
          class="control-input depth-number"
        />
      </div>
      <div class="depth-presets">
        <button 
          v-for="preset in depthPresets" 
          :key="preset.value"
          @click="localRealTreeDepth = preset.value"
          class="preset-button"
          :class="{ active: localRealTreeDepth === preset.value }"
        >
          {{ preset.label }}
        </button>
      </div>
    </div>
    <div class="form-group">
      <label for="power-select">Power Parameter</label>
      <input
        type="range"
        id="power"
        v-model="localSelectedPower"
        min="1"
        max="5"
        step="0.5"
        class="control-range"
      />
      <span class="range-value">{{ localSelectedPower }}</span>
    </div>
    <div class="form-group">
      <label for="partition-method-select">Partition Method</label>
      <select
        id="partition-method"
        v-model="localSelectedPartitionMethod"
        class="control-select"
      >
        <option v-for="method in partitionMethods" :key="method" :value="method">{{ method }}</option>
      </select>
    </div>
    <div class="form-group">
      <label for="k-input">Number of Clusters (K)</label>
      <input
        type="number"
        id="cluster-k"
        v-model="localSelectedK"
        min="2"
        :max="maxK"
        step="1"
        class="control-input"
      />
      <span class="input-hint">Range: 2-{{ maxK }}</span>
    </div>
    <div class="form-group">
      <button 
        @click="onRun"
        class="run-clustering-btn"
        :disabled="isClusteringRunning"
        v-tooltip="{
          key: isClusteringRunning ? '' : 'buttons.runClusteringEnabled',
          content: isClusteringRunning ? 'Clustering analysis is currently running...' : '',
          theme: 'info'
        }"
      >
        <span v-if="!isClusteringRunning">Run Clustering</span>
        <span v-else class="loading-content">
          <span class="spinner"></span>
          Running...
        </span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, ref, watch } from 'vue';
import { useTooltips } from '~/composables/useTooltips';

const props = defineProps({
  treeTypes: { type: Array, required: true },
  partitionMethods: { type: Array, required: true },
  selectedTreeType: { type: String, required: true },
  selectedPartitionMethod: { type: String, required: true },
  selectedPower: { type: Number, required: true },
  selectedK: { type: Number, required: true },
  maxK: { type: Number, required: true },
  isClusteringRunning: { type: Boolean, default: false },
  treeVisualizationType: { type: String, default: 'summarized' },
  realTreeDepth: { type: Number, default: 100 },
});

const emit = defineEmits([
  'update:selectedTreeType',
  'update:selectedPartitionMethod',
  'update:selectedPower',
  'update:selectedK',
  'update:treeVisualizationType',
  'update:realTreeDepth',
  'run',
]);

const { tooltips } = useTooltips();

const localSelectedTreeType = ref(props.selectedTreeType);
const localSelectedPartitionMethod = ref(props.selectedPartitionMethod);
const localSelectedPower = ref(props.selectedPower);
const localSelectedK = ref(props.selectedK);
const localTreeVisualizationType = ref(props.treeVisualizationType);
const localRealTreeDepth = ref(props.realTreeDepth);

// Preset depth options for quick selection
const depthPresets = [
  { label: 'Shallow (50)', value: 50 },
  { label: 'Balanced (100)', value: 100 },
  { label: 'Deep (200)', value: 200 },
  { label: 'Very Deep (350)', value: 350 },
  { label: 'Maximum (500)', value: 500 }
];

watch(() => props.selectedTreeType, val => { localSelectedTreeType.value = val; });
watch(localSelectedTreeType, val => { emit('update:selectedTreeType', val); });

watch(() => props.selectedPartitionMethod, val => { localSelectedPartitionMethod.value = val; });
watch(localSelectedPartitionMethod, val => { emit('update:selectedPartitionMethod', val); });

watch(() => props.selectedPower, val => { localSelectedPower.value = val; });
watch(localSelectedPower, val => { emit('update:selectedPower', val); });

watch(() => props.selectedK, val => { localSelectedK.value = val; });
watch(localSelectedK, val => { emit('update:selectedK', val); });

watch(() => props.treeVisualizationType, val => { localTreeVisualizationType.value = val; });
watch(localTreeVisualizationType, val => { emit('update:treeVisualizationType', val); });

watch(() => props.realTreeDepth, val => { localRealTreeDepth.value = val; });
watch(localRealTreeDepth, val => { emit('update:realTreeDepth', val); });

const onRun = () => emit('run');
</script>

<style scoped>
.parameter-controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 100%;
  overflow-x: hidden;
  box-sizing: border-box;
}

.form-group {
  margin-bottom: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.control-input {
  width: 100%;
  max-width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  box-sizing: border-box;
  transition: all 0.2s ease;
  font-family: inherit;
  background-color: #ffffff;
  color: #374151;
}

.control-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.control-input[type="number"] {
  text-align: center;
  font-weight: 500;
  -moz-appearance: textfield;
}

.control-input[type="number"]::-webkit-outer-spin-button,
.control-input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.input-hint {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 4px;
  text-align: center;
  display: block;
}

.control-select {
  width: 100%;
  max-width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.875rem;
  box-sizing: border-box;
  transition: all 0.2s ease;
  font-family: inherit;
  background-color: #ffffff;
  color: #374151;
}

.control-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
  display: block;
}

.tree-depth-label,
.tree-visualization-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  font-size: 12px;
  cursor: help;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.info-icon:hover {
  opacity: 1;
}

.tree-option-description {
  margin-top: 8px;
}

.option-explanation {
  font-size: 0.8rem;
  color: #6b7280;
  line-height: 1.4;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
}

.run-clustering-btn {
  width: 100%;
  padding: 12px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.run-clustering-btn:hover:not(:disabled) {
  background-color: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
}

.run-clustering-btn:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.loading-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Tree visualization specific styles */
.depth-control-container {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.control-range {
  flex: 1;
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  outline: none;
  -webkit-appearance: none;
}

.control-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: #3b82f6;
  border-radius: 50%;
  cursor: pointer;
}

.control-range::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: #3b82f6;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.depth-number {
  width: 80px !important;
  flex-shrink: 0;
}

.depth-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.preset-button {
  padding: 4px 8px;
  font-size: 0.75rem;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #374151;
}

.preset-button:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

.preset-button.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}
</style>
