<template>
  <div 
    class="sidebar-section"
    :class="[
      variant,
      {
        'is-disabled': isDisabled,
        'is-active': isActive,
        'is-completed': isCompleted,
        'is-collapsed': isCollapsed,
        'has-error': hasError
      }
    ]"
  >
    <!-- Section Header -->
    <div 
      class="section-header"
      @click="handleToggle"
      :class="{ 'is-clickable': !isDisabled }"
      role="button"
      :tabindex="isDisabled ? -1 : 0"
      :aria-expanded="!isCollapsed"
      :aria-controls="`section-content-${sectionId}`"
      @keydown.enter="handleToggle"
      @keydown.space.prevent="handleToggle"
    >
      <!-- Step Number (for workflow steps) -->
      <div v-if="stepNumber" class="step-number">
        {{ stepNumber }}
      </div>

      <!-- Icon -->
      <div v-if="displayIcon" class="section-icon" v-html="displayIcon"></div>

      <!-- Title and Description -->
      <div class="section-title-area">
        <h3 class="section-title">{{ title }}</h3>
        <p v-if="description" class="section-description">{{ description }}</p>
      </div>

      <!-- Status Badge -->
      <div v-if="statusBadge" class="status-badge" :class="statusBadge.type">
        {{ statusBadge.text }}
      </div>

      <!-- Header Actions Slot -->
      <div v-if="$slots['header-actions']" class="header-actions">
        <slot name="header-actions"></slot>
      </div>

      <!-- Collapse Indicator -->
      <div class="collapse-indicator" :class="{ 'is-collapsed': isCollapsed }">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M6 4l4 4-4 4V4z"/>
        </svg>
      </div>
    </div>

    <!-- Section Content -->
    <div 
      v-if="!isCollapsed"
      :id="`section-content-${sectionId}`"
      class="section-content"
      :class="{ 'is-disabled': isDisabled }"
    >
      <div v-if="isDisabled && lockedMessage" class="locked-message">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M4 4a4 4 0 0 1 8 0v2h1a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h1V4zm2 0v2h4V4a2 2 0 1 0-4 0z"/>
        </svg>
        <span>{{ lockedMessage }}</span>
      </div>
      
      <div v-else-if="$slots.default || !isEmpty" class="content-wrapper">
        <slot></slot>
      </div>
      
      <div v-else class="empty-content">
        <p>No content available</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface StatusBadge {
  text: string
  type: 'success' | 'warning' | 'error' | 'info' | 'neutral'
}

const props = defineProps({
  // Core props
  sectionId: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  
  // State props
  isCollapsed: { type: Boolean, default: false },
  isDisabled: { type: Boolean, default: false },
  isActive: { type: Boolean, default: false },
  isCompleted: { type: Boolean, default: false },
  hasError: { type: Boolean, default: false },
  isEmpty: { type: Boolean, default: false },
  
  // Appearance props
  variant: { 
    type: String as () => 'workflow' | 'control' | 'info',
    default: 'control'
  },
  stepNumber: { type: [String, Number], default: null },
  icon: { type: String, default: '' },
  statusIcon: { type: String, default: '' },
  statusBadge: { type: Object as () => StatusBadge | null, default: null },
  
  // Messages
  lockedMessage: { type: String, default: 'This section is currently locked.' }
})

const emit = defineEmits(['toggle', 'headerClick'])

// Computed properties
const displayIcon = computed(() => {
  if (props.statusIcon) return props.statusIcon
  if (props.icon) return props.icon
  return ''
})

// Methods
const handleToggle = () => {
  if (props.isDisabled) return
  
  emit('toggle', props.sectionId)
  emit('headerClick', props.sectionId)
}
</script>

<style scoped>
.sidebar-section {
  background: var(--card-bg);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-base);
  margin-bottom: var(--space-2);
  overflow: hidden;
  transition: var(--transition-fast);
}

.sidebar-section:hover {
  border-color: var(--border-hover);
  background: var(--bg-hover);
}

/* Variant styles */
.sidebar-section.workflow {
  border-left: 3px solid var(--border-primary);
}

.sidebar-section.workflow.is-active {
  background: var(--card-bg);
  border-left-color: var(--accent-primary);
  box-shadow: var(--shadow-sm);
}

.sidebar-section.workflow.is-completed {
  background: var(--card-bg);
  border-left-color: var(--success-primary);
}

.sidebar-section.is-disabled {
  background: var(--bg-disabled);
  opacity: 0.7;
  pointer-events: none;
}

.sidebar-section.has-error {
  background: var(--error-subtle);
  border-color: var(--error-primary);
  border-left-color: var(--error-primary);
}

/* Header styles */
.section-header {
  display: flex;
  align-items: center;
  padding: var(--space-3);
  gap: var(--space-3);
  transition: background-color 0.15s ease;
  user-select: none;
  cursor: pointer;
}

.section-header:hover {
  background: var(--bg-hover);
}

.section-header:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: -2px;
}

/* Step number */
.step-number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0;
}

.is-active .step-number {
  background: var(--accent-primary);
  color: var(--accent-text);
}

.is-completed .step-number {
  background: var(--success-primary);
  color: var(--accent-text);
}

/* Section icon */
.section-icon {
  font-size: var(--font-size-base);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: var(--text-secondary);
}

/* Title area */
.section-title-area {
  flex: 1;
  min-width: 0;
}

.section-title {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  line-height: 1.4;
}

.section-description {
  margin: 2px 0 0 0;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  line-height: 1.3;
}

/* Status badge */
.status-badge {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  flex-shrink: 0;
}

.status-badge.success { background: var(--success-subtle); color: var(--success-primary); }
.status-badge.warning { background: var(--warning-subtle); color: var(--warning-primary); }
.status-badge.error { background: var(--error-subtle); color: var(--error-primary); }
.status-badge.info { background: var(--info-subtle); color: var(--info-primary); }
.status-badge.neutral { background: var(--bg-tertiary); color: var(--text-secondary); }

/* Header actions */
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* Collapse indicator */
.collapse-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.collapse-indicator.is-collapsed {
  transform: rotate(-90deg);
}

/* Content styles */
.section-content {
  border-top: 1px solid var(--border-subtle);
  background: var(--card-bg);
}

.content-wrapper {
  padding: 0; /* Padding is handled by inner content */
}

.locked-message {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  background: var(--bg-secondary);
}

.locked-message svg {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.empty-content {
  padding: var(--space-4);
  text-align: center;
  color: var(--text-tertiary);
  font-style: italic;
}

.empty-content p {
  margin: 0;
  font-size: var(--font-size-sm);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .section-header {
    padding: var(--space-2) var(--space-3);
  }
  
  .section-title {
    font-size: var(--font-size-sm);
  }
  
  .section-description {
    font-size: 11px;
  }
}
</style>
