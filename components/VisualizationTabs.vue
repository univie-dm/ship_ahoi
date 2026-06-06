<template>
  <div class="visualization-tabs">
    <!-- Tab Navigation -->
    <div class="tab-nav">
      <button
        v-for="tab in availableTabs"
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="['tab-btn', { active: activeTab === tab.id, disabled: tab.disabled }]"
        :disabled="tab.disabled"
        :title="tab.disabled ? tab.disabledReason : tab.tooltip"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
        <span v-if="tab.hasChanges" class="tab-indicator">●</span>
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <!-- Layout Tab -->
      <div v-if="activeTab === 'layout'" class="tab-panel">
        <div class="compact-section">
          <h6 class="section-title">Plot Arrangement</h6>
          <div class="button-group horizontal">
            <slot name="plot-arrangement-controls"></slot>
          </div>
        </div>

        <div v-if="showDendrogramLayout" class="compact-section">
          <h6 class="section-title">Tree Layout</h6>
          <div class="button-group horizontal">
            <slot name="dendrogram-layout-controls"></slot>
          </div>
        </div>

        <div class="compact-section">
          <h6 class="section-title">Tree Visualization</h6>
          <div class="control-group">
            <slot name="tree-type-controls"></slot>
          </div>
        </div>

        <div class="compact-section">
          <h6 class="section-title">Visibility</h6>
          <div class="visibility-grid">
            <slot name="visibility-controls"></slot>
          </div>
        </div>
      </div>

      <!-- Data Tab -->
      <div v-if="activeTab === 'data'" class="tab-panel">
        <div class="compact-section">
          <h6 class="section-title">Axes</h6>
          <div class="axis-controls">
            <div class="control-group">
              <label class="compact-label">X-Axis</label>
              <slot name="x-axis-select"></slot>
            </div>
            <div class="control-group">
              <label class="compact-label">Y-Axis</label>
              <slot name="y-axis-select"></slot>
            </div>
          </div>
        </div>

        <div class="compact-section">
          <h6 class="section-title">Ground Truth Comparison</h6>
          <div class="control-group">
            <slot name="color-by-select"></slot>
          </div>
        </div>

        <div class="compact-section">
          <h6 class="section-title">Color Accessibility</h6>
          <div class="control-group">
            <slot name="colorblind-toggle"></slot>
          </div>
        </div>

        <div v-if="hasSplitViewSlot" class="compact-section">
          <slot name="split-view-toggle"></slot>
        </div>

        <div class="compact-section">
          <h6 class="section-title">Outliers</h6>
          <div class="outlier-note-with-tooltip">
            <span class="note-text">Note: Outliers are only available for selected partition methods like "Stability"</span>
            <button 
              type="button"
              class="info-trigger"
              @mouseenter="showOutlierTooltip"
              @mouseleave="hideOutlierTooltip"
              @focus="showOutlierTooltip"
              @blur="hideOutlierTooltip"
              aria-label="More information about outlier visualization"
              title="Click for detailed outlier information"
            >
              ℹ️
            </button>
          </div>
          <div class="control-group">
            <slot name="outlier-style-select"></slot>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, useSlots, Comment, Text } from 'vue';

const props = defineProps({
  // Tree-specific visibility
  isDendrogramVisible: { type: Boolean, default: false },
  isIcicleVisible: { type: Boolean, default: false },
  currentTreeVisualizationType: { type: String, default: 'dendrogram' },
  hasGroundTruth: { type: Boolean, default: false },
  // Data state for determining tab availability
  hasDataset: { type: Boolean, default: false },
});

const emit = defineEmits(['show-outlier-tooltip', 'hide-outlier-tooltip']);

const slots = useSlots();
const activeTab = ref('layout');

// Show dendrogram layout controls only when dendrogram is selected
const showDendrogramLayout = computed(() => 
  props.currentTreeVisualizationType === 'dendrogram'
);

const hasSplitViewSlot = computed(() => {
  const slot = slots['split-view-toggle'];
  if (!slot) {
    return false;
  }
  return slot().some((node) => {
    if (node.type === Comment) {
      return false;
    }
    if (node.type === Text) {
      const content = typeof node.children === 'string' ? node.children.trim() : '';
      return content.length > 0;
    }
    return true;
  });
});

// Define available tabs based on current state
const availableTabs = computed(() => {
  return [
    {
      id: 'layout',
      label: 'Layout',
      icon: '📋',
      tooltip: 'Plot arrangement and visibility',
      disabled: !props.hasDataset,
      disabledReason: 'Upload data first',
      hasChanges: false
    },
    {
      id: 'data',
      label: 'Data',
      icon: '📊',
      tooltip: 'Axis selection and coloring options',
      disabled: !props.hasDataset,
      disabledReason: 'Upload data first',
      hasChanges: false
    }
  ];
});

// Auto-switch to first available tab if current tab becomes unavailable
const ensureValidTab = () => {
  const currentTabExists = availableTabs.value.some(tab => 
    tab.id === activeTab.value && !tab.disabled
  );
  
  if (!currentTabExists) {
    const firstAvailable = availableTabs.value.find(tab => !tab.disabled);
    if (firstAvailable) {
      activeTab.value = firstAvailable.id;
    }
  }
};

// Watch for changes that might affect tab availability
watch(() => props.hasDataset, ensureValidTab, { immediate: true });

// Tooltip methods for outliers
const showOutlierTooltip = (event: MouseEvent) => {
  emit('show-outlier-tooltip', event);
};

const hideOutlierTooltip = () => {
  emit('hide-outlier-tooltip');
};
</script>

<style scoped>
.visualization-tabs {
  --tab-height: 32px;
  --tab-padding: 6px 10px;
  --section-spacing: 12px;
}

/* Tab Navigation */
.tab-nav {
  display: flex;
  border-bottom: 1px solid var(--border-primary, #e9e9e7);
  margin-bottom: 12px;
  gap: 2px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--tab-padding);
  height: var(--tab-height);
  background: var(--bg-secondary, #f7f6f3);
  border: 1px solid var(--border-primary, #e9e9e7);
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  color: var(--text-secondary, #787774);
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  flex: 1;
  justify-content: center;
  min-width: 0;
}

.tab-btn:hover:not(:disabled) {
  background: var(--bg-hover, #f1f1ef);
  color: var(--text-primary, #37352f);
}

.tab-btn.active {
  background: var(--bg-primary, #ffffff);
  color: var(--text-primary, #37352f);
  border-color: var(--accent-primary, #2383e2);
  border-bottom-color: var(--bg-primary, #ffffff);
  z-index: 1;
}

.tab-btn:disabled {
  background: var(--bg-disabled, #f7f6f3);
  color: var(--text-disabled, #c7c7c5);
  cursor: not-allowed;
}

.tab-icon {
  font-size: 0.875rem;
  line-height: 1;
}

.tab-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-indicator {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  background: var(--accent-primary, #2383e2);
  border-radius: 50%;
  font-size: 0;
}

/* Tab Content */
.tab-content {
  min-height: 120px;
}

.tab-panel {
  display: flex;
  flex-direction: column;
  gap: var(--section-spacing);
}

/* Compact Sections */
.compact-section {
  padding: 8px 0;
}

.compact-section:not(:last-child) {
  border-bottom: 1px solid var(--border-secondary, #d9d9d7);
}

.section-title {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-secondary, #787774);
  margin: 0 0 6px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Control Layouts */
.button-group.horizontal {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.axis-controls {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.compact-label {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--text-primary, #37352f);
  margin: 0;
}

.visibility-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.outlier-note-with-tooltip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  color: var(--text-secondary, #787774);
  margin: 0 0 6px 0;
  padding: 4px 6px;
  background: var(--bg-secondary, #f7f6f3);
  border-radius: 4px;
  border: 1px solid var(--border-secondary, #d9d9d7);
}

.outlier-note-with-tooltip .note-text {
  flex: 1;
  line-height: 1.3;
  font-style: italic;
}

.outlier-note-with-tooltip .info-trigger {
  flex-shrink: 0;
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  color: var(--accent-primary, #2383e2);
  transition: all 0.2s ease;
}

.outlier-note-with-tooltip .info-trigger:hover {
  background: var(--accent-primary, #2383e2);
  color: white;
  transform: scale(1.1);
}

.outlier-note-with-tooltip .info-trigger:focus {
  outline: 2px solid var(--accent-primary, #2383e2);
  outline-offset: 1px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .visualization-tabs {
    --tab-height: 28px;
    --tab-padding: 4px 6px;
    --section-spacing: 8px;
  }
  
  .tab-btn {
    font-size: 0.7rem;
  }
  
  .tab-label {
    display: none;
  }
  
  .tab-icon {
    font-size: 1rem;
  }
  
  .axis-controls {
    grid-template-columns: 1fr;
    gap: 6px;
  }
  
  .section-title {
    font-size: 0.65rem;
    margin-bottom: 4px;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .tab-btn {
    border-width: 2px;
  }
  
  .tab-btn.active {
    border-width: 2px;
  }
}

/* Focus states for accessibility */
.tab-btn:focus {
  outline: 2px solid var(--accent-primary, #2383e2);
  outline-offset: -2px;
}

.tab-btn:focus:not(:focus-visible) {
  outline: none;
}
</style>
