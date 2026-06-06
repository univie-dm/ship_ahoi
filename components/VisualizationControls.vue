<template>
  <div class="visualization-controls">
    <!-- Plot Layout Section (Primary) -->
    <div 
      class="accordion-section plot-layout-section"
      :class="{ expanded: isExpanded('plotLayout') }"
    >
      <button
        class="accordion-header"
        :aria-expanded="isExpanded('plotLayout')"
        :aria-controls="'section-content-plotLayout'"
        :id="'section-header-plotLayout'"
        @click="toggleSection('plotLayout')"
        @keydown="handleKeydown($event, 'plotLayout')"
        :disabled="!hasDataset"
      >
        <div class="section-icon" aria-hidden="true">📐</div>
        <div class="section-title-area">
          <h3 class="section-title">Plot Layout</h3>
          <p class="section-description">Arrange and configure your visualizations</p>
        </div>
        <div class="section-status" v-if="hasDataset">
          <span class="status-indicator active">●</span>
        </div>
        <div 
          class="expand-indicator" 
          :class="{ expanded: isExpanded('plotLayout') }" 
          aria-hidden="true"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6.22 4.22a.75.75 0 011.06 0L10.5 7.44a.75.75 0 010 1.06L7.28 11.72a.75.75 0 01-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 010-1.06z"/>
          </svg>
        </div>
      </button>
      
      <div
        v-if="isExpanded('plotLayout')"
        :id="'section-content-plotLayout'"
        class="accordion-content expanded"
        role="region"
        :aria-labelledby="'section-header-plotLayout'"
      >
        <div class="content-padding">
          <div class="control-group">
            <label class="enhanced-label">
              <span class="control-icon">🔄</span>
              Plot Arrangement
            </label>
            <div class="control-wrapper">
              <slot name="plot-arrangement-controls"></slot>
            </div>
          </div>
          
          <div v-if="showDendrogramLayout" class="control-group">
            <label class="enhanced-label">
              <span class="control-icon">🌲</span>
              Tree Layout
            </label>
            <div class="control-wrapper">
              <slot name="dendrogram-layout-controls"></slot>
            </div>
          </div>
          
          <div class="control-group">
            <label class="enhanced-label">
              <span class="control-icon">👁️</span>
              Visibility Options
            </label>
            <div class="control-wrapper visibility-controls">
              <slot name="visibility-controls"></slot>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Mapping Section (Secondary) -->
    <div 
      class="accordion-section data-mapping-section"
      :class="{ expanded: isExpanded('dataMapping') }"
    >
      <button
        class="accordion-header"
        :aria-expanded="isExpanded('dataMapping')"
        :aria-controls="'section-content-dataMapping'"
        :id="'section-header-dataMapping'"
        @click="toggleSection('dataMapping')"
        @keydown="handleKeydown($event, 'dataMapping')"
        :disabled="!hasDataset"
      >
        <div class="section-icon" aria-hidden="true">📊</div>
        <div class="section-title-area">
          <h3 class="section-title">Data Mapping</h3>
          <p class="section-description">Configure axes and coloring options</p>
        </div>
        <div class="section-status" v-if="hasDataset">
          <span class="status-indicator ready">●</span>
        </div>
        <div 
          class="expand-indicator" 
          :class="{ expanded: isExpanded('dataMapping') }" 
          aria-hidden="true"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6.22 4.22a.75.75 0 011.06 0L10.5 7.44a.75.75 0 010 1.06L7.28 11.72a.75.75 0 01-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 010-1.06z"/>
          </svg>
        </div>
      </button>
      
      <div
        v-if="isExpanded('dataMapping')"
        :id="'section-content-dataMapping'"
        class="accordion-content expanded"
        role="region"
        :aria-labelledby="'section-header-dataMapping'"
      >
        <div class="content-padding">
          <div class="axis-controls-grid">
            <div class="control-group">
              <label class="enhanced-label">
                <span class="control-icon">↔️</span>
                X-Axis
              </label>
              <div class="control-wrapper">
                <slot name="x-axis-select"></slot>
              </div>
            </div>
            <div class="control-group">
              <label class="enhanced-label">
                <span class="control-icon">↕️</span>
                Y-Axis
              </label>
              <div class="control-wrapper">
                <slot name="y-axis-select"></slot>
              </div>
            </div>
          </div>
          
          <div class="control-group">
            <label class="enhanced-label">
              <span class="control-icon">🎨</span>
              Color Points By
            </label>
            <div class="control-wrapper">
              <slot name="color-by-select"></slot>
              <div v-if="hasGroundTruth" class="ground-truth-badge">
                <span class="badge-icon">✅</span>
                Ground truth available
              </div>
            </div>
          </div>
          
          <div class="control-group">
            <label class="enhanced-label">
              <span class="control-icon">🔍</span>
              Outlier Display
            </label>
            <div class="control-wrapper">
              <slot name="outlier-style-select"></slot>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tree Settings Section (Tertiary) -->
    <div 
      v-if="showTreeSection"
      class="accordion-section tree-settings-section"
      :class="{ expanded: isExpanded('treeSettings') }"
    >
      <button
        class="accordion-header"
        :aria-expanded="isExpanded('treeSettings')"
        :aria-controls="'section-content-treeSettings'"
        :id="'section-header-treeSettings'"
        @click="toggleSection('treeSettings')"
        @keydown="handleKeydown($event, 'treeSettings')"
        :disabled="!hasDataset"
      >
        <div class="section-icon" aria-hidden="true">🌳</div>
        <div class="section-title-area">
          <h3 class="section-title">Tree Settings</h3>
          <p class="section-description">Advanced tree visualization options</p>
        </div>
        <div class="section-status" v-if="hasDataset && (isDendrogramVisible || isIcicleVisible)">
          <span class="status-indicator active">●</span>
        </div>
        <div 
          class="expand-indicator" 
          :class="{ expanded: isExpanded('treeSettings') }" 
          aria-hidden="true"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6.22 4.22a.75.75 0 011.06 0L10.5 7.44a.75.75 0 010 1.06L7.28 11.72a.75.75 0 01-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 010-1.06z"/>
          </svg>
        </div>
      </button>
      
      <div
        v-if="isExpanded('treeSettings')"
        :id="'section-content-treeSettings'"
        class="accordion-content expanded"
        role="region"
        :aria-labelledby="'section-header-treeSettings'"
      >
        <div class="content-padding">
          <div class="control-group">
            <label class="enhanced-label">
              <span class="control-icon">⚙️</span>
              Tree Visualization Type
            </label>
            <div class="control-wrapper">
              <slot name="tree-type-controls"></slot>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'

interface Props {
  // Data state for determining section availability
  hasDataset: boolean
  isDendrogramVisible: boolean
  isIcicleVisible: boolean
  currentTreeVisualizationType: 'dendrogram' | 'icicle'
  hasGroundTruth: boolean
  
  // Progressive disclosure state
  expandedSections?: string[]
  defaultExpanded?: string[]
}

interface Emits {
  (e: 'update:expandedSections', sections: string[]): void
  (e: 'section-toggle', sectionId: string, isExpanded: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  hasDataset: false,
  isDendrogramVisible: false,
  isIcicleVisible: false,
  currentTreeVisualizationType: 'dendrogram',
  hasGroundTruth: false,
  expandedSections: () => [],
  defaultExpanded: () => []
})

const emit = defineEmits<Emits>()

// Internal expanded sections state
const internalExpandedSections = ref<string[]>([])

// Show dendrogram layout controls only when dendrogram is selected
const showDendrogramLayout = computed(() => 
  props.currentTreeVisualizationType === 'dendrogram'
)

// Show tree section only when tree visualizations are available
const showTreeSection = computed(() => 
  props.isDendrogramVisible || props.isIcicleVisible
)

// Get default expanded sections based on application state
const getDefaultExpandedSections = (): string[] => {
  const sections: string[] = []
  
  // Always expand plot layout if dataset exists
  if (props.hasDataset) {
    sections.push('plotLayout')
  }
  
  // Use user-provided defaults if available
  if (props.defaultExpanded.length > 0) {
    sections.push(...props.defaultExpanded)
  } else {
    // Smart defaults: expand data mapping if no ground truth clustering results
    if (props.hasDataset) {
      sections.push('dataMapping')
    }
    
    // Expand tree settings if user is actively using tree visualization
    if (showTreeSection.value) {
      sections.push('treeSettings')
    }
  }
  
  return [...new Set(sections)] // Remove duplicates
}

// Initialize expanded sections
onMounted(() => {
  if (props.expandedSections.length > 0) {
    internalExpandedSections.value = [...props.expandedSections]
  } else {
    internalExpandedSections.value = getDefaultExpandedSections()
  }
})

// Watch for external changes to expandedSections prop
watch(() => props.expandedSections, (newSections) => {
  internalExpandedSections.value = [...newSections]
}, { deep: true })

// Watch for data changes to auto-expand relevant sections
watch(() => props.hasDataset, (hasDataset) => {
  if (hasDataset && internalExpandedSections.value.length === 0) {
    internalExpandedSections.value = ['plotLayout']
    emit('update:expandedSections', internalExpandedSections.value)
  }
})

// Check if a section is expanded
const isExpanded = (sectionId: string): boolean => {
  return internalExpandedSections.value.includes(sectionId)
}

// Toggle a section's expanded state
const toggleSection = (sectionId: string): void => {
  const currentIndex = internalExpandedSections.value.indexOf(sectionId)
  const newExpanded = [...internalExpandedSections.value]
  
  if (currentIndex > -1) {
    newExpanded.splice(currentIndex, 1)
  } else {
    newExpanded.push(sectionId)
  }
  
  internalExpandedSections.value = newExpanded
  emit('update:expandedSections', newExpanded)
  emit('section-toggle', sectionId, currentIndex === -1)
  
  // Announce to screen readers
  announceToggle(getSectionTitle(sectionId), currentIndex === -1)
}

// Get section title for announcements
const getSectionTitle = (sectionId: string): string => {
  const titles: Record<string, string> = {
    plotLayout: 'Plot Layout',
    dataMapping: 'Data Mapping', 
    treeSettings: 'Tree Settings'
  }
  return titles[sectionId] || sectionId
}

// Screen reader announcements
const announceToggle = (sectionTitle: string, isExpanded: boolean): void => {
  const message = `${sectionTitle} section ${isExpanded ? 'expanded' : 'collapsed'}`
  // Simple announcement - could be enhanced with a proper screen reader service
  console.log(`[Screen Reader]: ${message}`)
}

// Keyboard navigation
const handleKeydown = (event: KeyboardEvent, sectionId: string): void => {
  switch (event.key) {
    case 'Enter':
    case ' ':
      event.preventDefault()
      toggleSection(sectionId)
      break
    case 'ArrowDown':
      event.preventDefault()
      focusNextSection(sectionId)
      break  
    case 'ArrowUp':
      event.preventDefault()
      focusPreviousSection(sectionId)
      break
  }
}

// Focus navigation helpers
const getSectionOrder = (): string[] => {
  const sections = ['plotLayout', 'dataMapping']
  if (showTreeSection.value) {
    sections.push('treeSettings')
  }
  return sections
}

const focusNextSection = (currentSectionId: string): void => {
  const sections = getSectionOrder()
  const currentIndex = sections.indexOf(currentSectionId)
  const nextIndex = (currentIndex + 1) % sections.length
  const nextSection = sections[nextIndex]
  
  const nextButton = document.getElementById(`section-header-${nextSection}`)
  nextButton?.focus()
}

const focusPreviousSection = (currentSectionId: string): void => {
  const sections = getSectionOrder()
  const currentIndex = sections.indexOf(currentSectionId)
  const previousIndex = currentIndex === 0 ? sections.length - 1 : currentIndex - 1
  const previousSection = sections[previousIndex]
  
  const previousButton = document.getElementById(`section-header-${previousSection}`)
  previousButton?.focus()
}
</script>

<style scoped>
.visualization-controls {
  --primary-gradient: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
  --secondary-gradient: linear-gradient(135deg, #10b981 0%, #047857 100%);
  --tertiary-gradient: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  --section-spacing: 16px;
  --content-padding: 20px;
  --border-radius: 12px;
  --transition-timing: cubic-bezier(0.4, 0, 0.2, 1);
}

/* Base component styles */
.visualization-controls {
  padding: 16px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
}

/* Accordion Section Base */
.accordion-section {
  border-radius: var(--border-radius);
  margin-bottom: var(--section-spacing);
  overflow: hidden;
  transition: all 0.3s var(--transition-timing);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.accordion-section:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

/* Section-specific styling */
.plot-layout-section {
  background: var(--primary-gradient);
  color: white;
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.25);
}

.data-mapping-section {
  background: var(--secondary-gradient);
  color: white;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2);
}

.tree-settings-section {
  background: var(--tertiary-gradient);
  color: white;
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.2);
}

/* Accordion Header */
.accordion-header {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 16px 20px;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  font-family: inherit;
  position: relative;
  transition: all 0.2s ease;
  min-height: 44px; /* Touch-friendly minimum */
  text-align: left;
}

.accordion-header:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.accordion-header:focus {
  outline: 2px solid rgba(255, 255, 255, 0.8);
  outline-offset: -2px;
}

.accordion-header:focus:not(:focus-visible) {
  outline: none;
}

/* Header content */
.section-icon {
  font-size: 1.2rem;
  margin-right: 12px;
  flex-shrink: 0;
}

.section-title-area {
  flex: 1;
  min-width: 0;
}

.section-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 2px 0;
  color: rgba(255, 255, 255, 0.95);
}

.section-description {
  font-size: 0.85rem;
  margin: 0;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.3;
}

.section-status {
  margin-right: 12px;
  flex-shrink: 0;
}

.status-indicator {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  font-size: 0;
}

.status-indicator.active {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}

.status-indicator.ready {
  background: #eab308;
  box-shadow: 0 0 8px rgba(234, 179, 8, 0.5);
}

.expand-indicator {
  flex-shrink: 0;
  transition: transform 0.3s var(--transition-timing);
  opacity: 0.8;
}

.expand-indicator.expanded {
  transform: rotate(90deg);
}

/* Accordion Content */
.accordion-content {
  overflow: hidden;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.content-padding {
  padding: var(--content-padding);
}

/* Control Groups */
.control-group {
  margin-bottom: 20px;
}

.control-group:last-child {
  margin-bottom: 0;
}

.enhanced-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
  margin-bottom: 8px;
}

.control-icon {
  font-size: 1rem;
  opacity: 0.9;
}

.control-wrapper {
  position: relative;
}

/* Axis controls grid */
.axis-controls-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

/* Visibility controls specific styling */
.visibility-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Ground truth badge */
.ground-truth-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  padding: 4px 8px;
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 6px;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.9);
}

.badge-icon {
  font-size: 0.8rem;
}

/* Responsive design */
@media (max-width: 768px) {
  .visualization-controls {
    padding: 12px;
    --section-spacing: 12px;
    --content-padding: 16px;
  }
  
  .accordion-header {
    padding: 12px 16px;
  }
  
  .section-title {
    font-size: 1rem;
  }
  
  .section-description {
    display: none; /* Hide on mobile to save space */
  }
  
  .axis-controls-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .section-icon {
    font-size: 1rem;
    margin-right: 8px;
  }
  
  .enhanced-label {
    font-size: 0.85rem;
  }
  
  .control-icon {
    font-size: 0.9rem;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .accordion-header:focus {
    outline: 3px solid white;
  }
  
  .status-indicator {
    border: 2px solid white;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .accordion-content,
  .expand-indicator,
  .accordion-header,
  .accordion-section {
    transition: none;
  }
}

/* Touch device optimizations */
@media (hover: none) and (pointer: coarse) {
  .accordion-section:hover {
    transform: none;
  }
  
  .accordion-header {
    min-height: 48px; /* Larger touch target */
  }
}

/* Force GPU acceleration for smooth animations */
.accordion-content,
.expand-indicator {
  will-change: transform, opacity;
  transform: translateZ(0);
}
</style>