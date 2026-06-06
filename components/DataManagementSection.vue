<template>
  <div class="export-import-controls-reworked">

    <!-- Current Run Data Export -->
    <div class="section-group compact">
      <h6 class="section-subtitle">Data Export</h6>
      <div class="export-buttons-grid">
        <button @click="handleExportClusterLabels" :disabled="!hasClusteringData" class="export-btn">
          <span class="icon-reworked">🏷️</span> Cluster Labels
        </button>
        <button @click="handleExportAnalysisReport" :disabled="!hasActiveRun" class="export-btn">
          <span class="icon-reworked">📄</span> Analysis Report
        </button>
        <button v-if="!comparisonMode && showDownloads && isScatterVisible" @click="handleDownloadScatter('png')" class="export-btn">
          <span class="icon-reworked">📊</span> Scatter PNG
        </button>
        <button v-if="!comparisonMode && showDownloads && (isDendrogramVisible || isIcicleVisible)" @click="handleDownloadTree('png')" class="export-btn">
          <span class="icon-reworked">🌳</span> Tree Visualization PNG
        </button>
      </div>
      
      <!-- Compact status indicator -->
      <div class="status-indicator compact" v-if="!hasActiveRun">
        <span class="status-text">💡 Select a run to enable exports</span>
      </div>
    </div>


    <!-- Comparison Exports (only shown in comparison mode) -->
    <div v-if="comparisonMode" class="section-group compact">
      <h6 class="section-subtitle">Comparison</h6>
      <div class="export-buttons-grid">
        <button @click="handleExportDetailedReport" class="export-btn">
          <span class="icon-reworked">📊</span> Detailed Report
        </button>
        <button @click="handleExportVisualReport" class="export-btn">
          <span class="icon-reworked">📄</span> Visual Report
        </button>
        <button @click="handleExportAllVisualizations('png')" class="export-btn">
          <span class="icon-reworked">🖼️</span> Charts PNG
        </button>
        <button @click="handleExportAllVisualizations('svg')" class="export-btn">
          <span class="icon-reworked">📐</span> Charts SVG
        </button>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const props = defineProps({
  hasActiveRun: { type: Boolean, default: false },
  isDendrogramVisible: { type: Boolean, default: false },
  isScatterVisible: { type: Boolean, default: false },
  isIcicleVisible: { type: Boolean, default: false },
  hasClusteringData: { type: Boolean, default: false },
  hasTreeData: { type: Boolean, default: false },
  comparisonMode: { type: Boolean, default: false },
  showDownloads: { type: Boolean, default: true }
});

const emit = defineEmits([
  'download-scatter',
  'download-tree',
  'download-all',
  'export-cluster-labels',
  'export-analysis-report',
  'export-detailed-report',
  'export-visual-report',
  'export-all-visualizations'
]);


const hasVisibleVisualizations = computed(() => {
  return props.isDendrogramVisible || props.isScatterVisible || props.isIcicleVisible;
});


// New download functions
const handleDownloadScatter = (format: 'png' | 'svg') => {
  emit('download-scatter', format);
};

const handleDownloadTree = (format: 'png' | 'svg') => {
  emit('download-tree', format);
};

const handleDownloadAll = (format: 'png' | 'svg') => {
  emit('download-all', format);
};

// Data export functions
const handleExportClusterLabels = () => {
  emit('export-cluster-labels');
};


const handleExportAnalysisReport = () => {
  emit('export-analysis-report');
};


// Comparison export functions
const handleExportDetailedReport = () => {
  emit('export-detailed-report');
};

const handleExportVisualReport = () => {
  emit('export-visual-report');
};

const handleExportAllVisualizations = (format: 'png' | 'svg') => {
  emit('export-all-visualizations', format);
};
</script>

<style scoped>
/* Design System Variables */
.export-import-controls-reworked {
  --bg-primary: #ffffff;
  --bg-secondary: #f7f6f3;
  --bg-tertiary: #f1f1ef;
  --bg-hover: #f7f6f3;
  --bg-active: #e9e9e7;
  --bg-disabled: #f7f6f3;
  --border-primary: #e9e9e7;
  --border-secondary: #d9d9d7;
  --border-hover: #d9d9d7;
  --text-primary: #37352f;
  --text-secondary: #787774;
  --text-tertiary: #9b9a97;
  --text-disabled: #c7c7c5;
  --text-muted: #9b9a97;
  --accent-primary: #2383e2;
  --accent-hover: #1a73cc;
  --accent-subtle: #e3f2fd;
  --success-primary: #0f7b0f;
  --error-primary: #e03e3e;
  --warning-primary: #f59e0b;
}

/* Unified Button System */
.export-import-controls-reworked button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 10px 12px;
  margin: 0;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
  gap: 6px;
}

.export-import-controls-reworked button:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--border-hover);
  color: var(--text-primary);
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.export-import-controls-reworked button:active:not(:disabled) {
  background: var(--bg-active);
  transform: translateY(0);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.export-import-controls-reworked button:disabled {
  background: var(--bg-disabled);
  border-color: var(--border-primary);
  color: var(--text-disabled);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Icon Styling */
.icon-reworked {
  font-style: normal;
  font-size: 1em;
  line-height: 1;
}

/* Section Layout */
.section-group {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-primary);
}

.section-group.compact {
  margin-bottom: 16px;
  padding-bottom: 12px;
}

.section-group:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

/* Section Titles */
.section-subtitle {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  padding-left: 2px;
}

/* Button Grid Layout */
.export-buttons-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 0;
}

/* Single column for downloads when only one button */
.export-buttons-grid:has(button:only-child) {
  grid-template-columns: 1fr;
}

/* Handle 3+ buttons by wrapping to next row */
.export-buttons-grid:has(button:nth-child(3)) {
  grid-template-columns: 1fr 1fr;
}

/* Specific Button Styling */
.export-btn {
  padding: 8px 10px !important;
  font-size: 0.75rem !important;
  min-height: 36px;
}

/* Status Indicator */
.status-indicator {
  margin: 8px 0 0 0;
  padding: 8px 10px;
  background: var(--accent-subtle);
  border: 1px solid var(--accent-primary);
  border-radius: 4px;
  border-left: 3px solid var(--accent-primary);
}

.status-indicator.compact {
  margin: 6px 0 0 0;
  padding: 6px 8px;
}

.status-text {
  font-size: 0.7rem;
  color: var(--text-secondary);
  line-height: 1.3;
  font-weight: 500;
}

/* Responsive Design */
@media (max-width: 768px) {
  .export-buttons-grid {
    grid-template-columns: 1fr;
    gap: 6px;
  }
  
  .export-btn {
    font-size: 0.7rem !important;
    padding: 6px 8px !important;
    min-height: 32px;
  }
  
  .section-subtitle {
    font-size: 0.65rem;
    margin-bottom: 8px;
  }
}

/* Focus States for Accessibility */
.export-import-controls-reworked button:focus {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}

.export-import-controls-reworked button:focus:not(:focus-visible) {
  outline: none;
}
</style>
