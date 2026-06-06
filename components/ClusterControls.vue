<template>  <div class="controls-sidebar">    <!-- SHIP Configuration Section - Enhanced Design -->
    <div class="control-section primary-section">
      <div class="section-header">
        <h3 class="section-title">🚀 SHIP Configuration</h3>
        <div class="section-badge">Required</div>
      </div>
      <div class="info-box primary-info">
        <div class="info-icon-large">⚙️</div>
        <div>
          <strong>Configure your clustering pipeline</strong>
          <p>Set up the three core steps of the SHIP framework to customize your clustering approach.</p>
        </div>
      </div>
      
      <div class="algorithm-steps">
        <h4 class="steps-title">📋 Algorithm Steps</h4>
        <div class="steps-note">
          <strong>⚠️ All three steps must be configured before running the simulation</strong>
        </div>
        
        <div class="form-group enhanced">
          <label for="ultrametric-select" class="enhanced-label">
            <span class="step-number">1</span>
            Ultrametric Tree Type
          </label>
          <select
            id="ultrametric-select"
            :value="selectedTreeType"
            @change="$emit('update:selectedTreeType', ($event.target as HTMLSelectElement).value)"
            class="control-select enhanced-select"
          >
            <!-- <option value="radial">Radial Tree</option> -->
            <option v-for="opt in treeTypes" :key="opt" :value="opt">{{ opt }}</option>
          </select>
          <span class="info-icon enhanced-info">ⓘ</span>
        </div>        <div class="form-group enhanced">
          <label for="hierarchy-select" class="enhanced-label">
            <span class="step-number">2</span>
            Hierarchy Power
          </label>
          <select
            id="hierarchy-select"
            :value="selectedPower"
            @change="$emit('update:selectedPower', parseInt(($event.target as HTMLSelectElement).value, 10))"
            class="control-select enhanced-select"
          >
            <option value="1">Level 1 - Linear</option>
            <option value="2">Level 2 - Quadratic</option>
            <option value="3">Level 3 - Cubic</option>
            <option value="4">Level 4 - Quartic</option>
            <option value="5">Level 5 - Quintic</option>
          </select>
          <span class="info-icon enhanced-info">ⓘ</span>
        </div>

        <div class="form-group enhanced">
          <label for="partitioning-select" class="enhanced-label">
            <span class="step-number">3</span>
            Partitioning Method
          </label>
          <select
            id="partitioning-select"
            :value="selectedPartitionMethod"
            @change="$emit('update:selectedPartitionMethod', ($event.target as HTMLSelectElement).value)"
            class="control-select enhanced-select"
          >
            <option v-for="opt in partitionMethods" :key="opt" :value="opt">{{ opt }}</option>
          </select>
          <span class="info-icon enhanced-info">ⓘ</span>
        </div>
      </div>
    </div>    <!-- Parameters Section - Enhanced Design -->
    <div class="control-section secondary-section">
      <div class="section-header">
        <h3 class="section-title">🎯 Parameters</h3>
        <div class="section-badge secondary">Tuning</div>
      </div>
      <div class="form-group enhanced">
        <label for="k-input" class="enhanced-label">
          <span class="param-icon">🔢</span>
          Number of Clusters (K)
        </label>
        <div class="input-container">
          <input
            id="k-input"
            type="number"
            min="2"
            :max="maxK"
            :value="selectedK"
            @input="$emit('update:selectedK', +($event.target as HTMLInputElement).value)"
            class="control-input enhanced-input"
          />
          <span class="input-range-hint">Range: 2-{{ maxK }}</span>
        </div>
        <span class="info-icon enhanced-info">ⓘ</span>
      </div>
      <button class="run-button enhanced-run-button" @click="$emit('generate-clusters')">
        <span class="button-icon">▶️</span>
        Run Clustering Simulation
      </button>
    </div>    <!-- Visualization Options Section -->
    <div class="control-section tertiary-section">
      <div class="section-header">
        <h3 class="section-title">📊 Visualization Options</h3>
        <div class="section-badge tertiary">Optional</div>
      </div>
      <div class="info-box">
        Choose how to visualize your data in the scatter plot.
      </div>
      
      <div class="form-group">
        <label for="x-axis-select">X-Axis</label>
        <select
          id="x-axis-select"
          :value="selectedXAxis"
          @change="$emit('update:selectedXAxis', ($event.target as HTMLSelectElement).value)"
          class="control-select"
        >
          <option v-for="option in xAxisOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <span class="info-icon">ⓘ</span>
      </div>

      <div class="form-group">
        <label for="y-axis-select">Y-Axis</label>
        <select
          id="y-axis-select"
          :value="selectedYAxis"
          @change="$emit('update:selectedYAxis', ($event.target as HTMLSelectElement).value)"
          class="control-select"
        >
          <option v-for="option in yAxisOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <span class="info-icon">ⓘ</span>
      </div>

      <div class="form-group">
        <label for="color-by-select">Color Points By</label>
        <select
          id="color-by-select"
          :value="selectedColorBy"
          @change="$emit('update:selectedColorBy', ($event.target as HTMLSelectElement).value)"
          class="control-select"
        >
          <option value="predicted">Predicted Clusters</option>
          <option value="ground_truth" :disabled="!hasGroundTruth">Ground Truth Labels</option>
        </select>
        <span v-if="hasGroundTruth" class="info-icon ground-truth-available">✅</span>
        <span v-else class="info-icon">ⓘ</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue';
import { computed } from 'vue';

interface SampleDataOption {
  value: string;
  label: string;
}

interface AxisOption {
  value: string;
  label: string;
}

const props = defineProps({
  // Data Source
  sampleOptions: {
    type: Array as PropType<SampleDataOption[]>,
    default: () => []
  },
  selectedSample: {
    type: String,
    default: ''
  },
  // SHIP Configuration
  treeTypes: {
    type: Array as PropType<string[]>,
    default: () => []
  },
  selectedTreeType: {
    type: String,
    default: 'DCTree'
  },
  selectedPower: {
    type: Number,
    default: 2
  },
  partitionMethods: {
    type: Array as PropType<string[]>,
    default: () => []
  },
  selectedPartitionMethod: {
    type: String,
    default: 'Elbow'
  },
  // Parameters
  selectedK: {
    type: Number,
    default: 5
  },
  maxK: {
    type: Number,
    default: 15
  },
  // Visualization Options
  selectedXAxis: {
    type: String,
    default: 'feature-0'
  },
  selectedYAxis: {
    type: String,
    default: 'feature-1'
  },
  selectedColorBy: {
    type: String,
    default: 'predicted'
  },
  hasGroundTruth: {
    type: Boolean,
    default: false
  },
  featureCount: {
    type: Number,
    default: 2
  },
  // Dimensionality reduction data for dynamic axis options
  dimensionalityReduction: {
    type: Object as PropType<{
      pca?: number[][] | null;
      umap?: number[][] | null;
      tsne?: number[][] | null;
    }>,
    default: () => ({})
  },
  // Loading indicators for dimensionality reduction methods
  loadingIndicators: {
    type: Object as PropType<{
      umap?: { isLoading: boolean; isReady: boolean; hasFailed: boolean };
      tsne?: { isLoading: boolean; isReady: boolean; hasFailed: boolean };
    }>,
    default: () => ({})
  }
});

// Generate axis options based on available features and dimensionality reduction methods
const xAxisOptions = computed<AxisOption[]>(() => {
  const options: AxisOption[] = [];
  
  // Add feature options
  for (let i = 0; i < props.featureCount; i++) {
    options.push({
      value: `feature-${i}`,
      label: `Feature ${i + 1}`
    });
  }
  
  // Add PCA options (always available)
  options.push(
    { value: 'pca-0', label: 'PCA Component 1' },
    { value: 'pca-1', label: 'PCA Component 2' }
  );
  
  // Add UMAP options if available or loading
  if (props.dimensionalityReduction?.umap || props.loadingIndicators?.umap?.isReady) {
    options.push(
      { value: 'umap-0', label: 'UMAP Dimension 1' },
      { value: 'umap-1', label: 'UMAP Dimension 2' }
    );
  } else if (props.loadingIndicators?.umap?.isLoading) {
    options.push(
      { value: 'umap-0', label: 'UMAP Dimension 1 ⏳' },
      { value: 'umap-1', label: 'UMAP Dimension 2 ⏳' }
    );
  }
  
  // Add t-SNE options if available or loading
  if (props.dimensionalityReduction?.tsne || props.loadingIndicators?.tsne?.isReady) {
    options.push(
      { value: 'tsne-0', label: 't-SNE Dimension 1' },
      { value: 'tsne-1', label: 't-SNE Dimension 2' }
    );
  } else if (props.loadingIndicators?.tsne?.isLoading) {
    options.push(
      { value: 'tsne-0', label: 't-SNE Dimension 1 ⏳' },
      { value: 'tsne-1', label: 't-SNE Dimension 2 ⏳' }
    );
  }
  
  return options;
});

const yAxisOptions = computed<AxisOption[]>(() => {
  const options: AxisOption[] = [];
  
  // Add feature options
  for (let i = 0; i < props.featureCount; i++) {
    options.push({
      value: `feature-${i}`,
      label: `Feature ${i + 1}`
    });
  }
  
  // Add PCA options (always available)
  options.push(
    { value: 'pca-0', label: 'PCA Component 1' },
    { value: 'pca-1', label: 'PCA Component 2' }
  );
  
  // Add UMAP options if available or loading
  if (props.dimensionalityReduction?.umap || props.loadingIndicators?.umap?.isReady) {
    options.push(
      { value: 'umap-0', label: 'UMAP Dimension 1' },
      { value: 'umap-1', label: 'UMAP Dimension 2' }
    );
  } else if (props.loadingIndicators?.umap?.isLoading) {
    options.push(
      { value: 'umap-0', label: 'UMAP Dimension 1 ⏳' },
      { value: 'umap-1', label: 'UMAP Dimension 2 ⏳' }
    );
  }
  
  // Add t-SNE options if available or loading
  if (props.dimensionalityReduction?.tsne || props.loadingIndicators?.tsne?.isReady) {
    options.push(
      { value: 'tsne-0', label: 't-SNE Dimension 1' },
      { value: 'tsne-1', label: 't-SNE Dimension 2' }
    );
  } else if (props.loadingIndicators?.tsne?.isLoading) {
    options.push(
      { value: 'tsne-0', label: 't-SNE Dimension 1 ⏳' },
      { value: 'tsne-1', label: 't-SNE Dimension 2 ⏳' }
    );
  }
  
  return options;
});

const emit = defineEmits([
  'update:selectedSample',
  'update:selectedTreeType',
  'update:selectedPower',
  'update:selectedPartitionMethod',
  'update:selectedK',
  'update:selectedXAxis',
  'update:selectedYAxis',
  'update:selectedColorBy',
  'generate-clusters'
]);

</script>

<style scoped>
.controls-sidebar {
  padding: 24px;
  background-color: #ffffff;
  color: #374151;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}

.control-section {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f3f4f6;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.control-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

/* Enhanced Primary Section (SHIP Configuration) */
.primary-section {
  background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
  color: white;
  padding: 24px;
  border: none;
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.25);
  transform: scale(1.02);
  margin-bottom: 40px;
}

.primary-section .section-title {
  color: white;
  font-size: 1.25rem;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.primary-section .enhanced-label {
  color: #f1f5f9;
  font-weight: 600;
}

.primary-section .enhanced-select {
  background-color: rgba(255, 255, 255, 0.95);
  border: 2px solid rgba(255, 255, 255, 0.3);
  color: #1e293b;
  font-weight: 500;
}

.primary-section .enhanced-select:focus {
  border-color: #fbbf24;
  box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.3);
}

/* Secondary Section (Parameters) */
.secondary-section {
  background: linear-gradient(135deg, #10b981 0%, #047857 100%);
  color: white;
  padding: 20px;
  border: none;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
}

.secondary-section .section-title {
  color: white;
  font-size: 1.15rem;
}

.secondary-section .enhanced-label {
  color: #f0fdf4;
  font-weight: 600;
}

/* Tertiary Section (Visualization) */
.tertiary-section {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
  letter-spacing: -0.025em;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-badge {
  background-color: #dc2626;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  animation: pulse 2s infinite;
}

.section-badge.secondary {
  background-color: #059669;
}

.section-badge.tertiary {
  background-color: #6b7280;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.info-box {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #3b82f6;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  margin-bottom: 20px;
  color: #475569;
  line-height: 1.5;
}

.primary-info {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-left: 4px solid #fbbf24;
  color: #f1f5f9;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  backdrop-filter: blur(10px);
}

.info-icon-large {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.primary-info strong {
  color: white;
  display: block;
  margin-bottom: 4px;
}

.algorithm-steps {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
  backdrop-filter: blur(5px);
}

.steps-title {
  color: white;
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 16px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-group {
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
}

.form-group.enhanced {
  margin-bottom: 24px;
}

.form-group label,
.form-group h4 {
  margin-bottom: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  letter-spacing: 0.025em;
}

.enhanced-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 10px;
}

.step-number {
  background-color: #fbbf24;
  color: #1e293b;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
  flex-shrink: 0;
}

.param-icon {
  font-size: 1.1rem;
}

.control-section h4 {
  font-size: 1rem;
  font-weight: 600;
  margin-top: 24px;
  margin-bottom: 16px;
  color: #1f2937;
}

.control-select,
.control-slider,
.browse-button,
.run-button {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  font-size: 0.875rem;
  box-sizing: border-box;
  transition: all 0.2s ease;
  font-family: inherit;
}

.control-select {
  background-color: #ffffff;
  color: #374151;
}

.enhanced-select {
  border: 2px solid #d1d5db;
  padding: 12px 14px;
  font-weight: 500;
  border-radius: 10px;
}

.control-select:focus,
.enhanced-select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(255, 255, 255, 0.1);
  padding: 12px;
  border-radius: 8px;
  backdrop-filter: blur(5px);
}

.control-input {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  font-size: 0.875rem;
  box-sizing: border-box;
  transition: all 0.2s ease;
  font-family: inherit;
  background-color: #ffffff;
  color: #374151;
  width: 100%;
  max-width: 100%;
}

.enhanced-input {
  background-color: rgba(255, 255, 255, 0.95);
  border: 2px solid rgba(255, 255, 255, 0.3);
  color: #1e293b;
  font-weight: 500;
  border-radius: 10px;
  padding: 12px 14px;
}

.control-input:focus,
.enhanced-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.enhanced-input:focus {
  border-color: #fbbf24;
  box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.3);
}

.input-range-hint {
  background: rgba(255, 255, 255, 0.9);
  color: #6b7280;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  text-align: center;
  margin-top: 4px;
}

.form-group span:not(.info-icon):not(.file-limit-text):not(.step-number):not(.param-icon):not(.input-range-hint):not(.button-icon) {
  margin-left: 12px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  align-self: center;
  min-width: 24px;
}

.info-icon {
  font-size: 0.75rem;
  color: #9ca3af;
  margin-left: 8px;
  cursor: help;
  align-self: center;
}

.enhanced-info {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.8rem;
}

.ground-truth-available {
  color: #10b981;
  font-size: 0.9rem;
}

.form-group.checkbox-group {
  flex-direction: row;
  align-items: center;
}

.form-group.checkbox-group label {
  margin-bottom: 0;
  margin-left: 8px;
  font-size: 0.875rem;
}

.form-group.checkbox-group input[type="checkbox"] {
  margin-right: 0;
  width: 16px;
  height: 16px;
  accent-color: #3b82f6;
}

.browse-button,
.run-button {
  background-color: #3b82f6;
  color: white;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 12px 20px;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.025em;
}

.browse-button:hover,
.run-button:hover {
  background-color: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
}

.run-button {
  background-color: #10b981;
  margin-top: 16px;
}

.enhanced-run-button {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #1e293b;
  font-weight: 700;
  font-size: 0.95rem;
  padding: 14px 24px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  box-shadow: 0 4px 15px rgba(251, 191, 36, 0.3);
  border: none;
  margin-top: 20px;
}

.enhanced-run-button:hover {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(251, 191, 36, 0.4);
}

.button-icon {
  font-size: 1rem;
}

.run-button:hover {
  background-color: #059669;
  box-shadow: 0 4px 8px rgba(16, 185, 129, 0.3);
}

.control-select:disabled,
input[type="checkbox"]:disabled + label {
  background-color: #f3f4f6;
  cursor: not-allowed;
  opacity: 0.6;
}

input[type="checkbox"]:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* Ensure proper container sizing and prevent overflow */
.controls-sidebar {
  max-width: 100%;
  overflow-x: hidden;
  box-sizing: border-box;
}

.input-container,
.form-group {
  max-width: 100%;
  box-sizing: border-box;
}

.control-input,
.enhanced-input {
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

/* Ensure number input arrows are visible */
.control-input[type="number"],
.enhanced-input[type="number"] {
  -moz-appearance: textfield;
}

.control-input[type="number"]::-webkit-outer-spin-button,
.control-input[type="number"]::-webkit-inner-spin-button,
.enhanced-input[type="number"]::-webkit-outer-spin-button,
.enhanced-input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* Add custom number input styling */
.enhanced-input[type="number"] {
  text-align: center;
  font-weight: 600;
}
</style>
