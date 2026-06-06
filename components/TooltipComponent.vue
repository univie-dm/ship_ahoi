<template>
  <Teleport to="body">
    <Transition 
      name="tooltip"
      @after-enter="onAfterEnter"
      @before-leave="onBeforeLeave"
    >
      <div
        v-if="visible && content"
        ref="tooltipEl"
        class="tooltip-container"
        :class="[
          `tooltip-${position}`,
          `tooltip-${theme}`,
          `tooltip-${size}`,
          { 'tooltip-rich': isRichContent, 'tooltip-interactive': interactive }
        ]"
        :style="tooltipStyle"
        role="tooltip"
        :aria-describedby="ariaId"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
        @click="handleClick"
      >
        <div class="tooltip-arrow" v-if="showArrow"></div>
        <div 
          class="tooltip-content"
          :id="ariaId"
        >
          <div v-if="title" class="tooltip-title">{{ title }}</div>
          <div 
            v-if="isRichContent" 
            class="tooltip-body" 
            v-html="content"
          ></div>
          <div 
            v-else 
            class="tooltip-body"
          >{{ content }}</div>
          <div v-if="interactive && showClose" class="tooltip-close">
            <button 
              @click="$emit('close')"
              class="tooltip-close-btn"
              aria-label="Close tooltip"
            >
              ×
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue';

export interface TooltipPosition {
  top: number;
  left: number;
}

const props = defineProps({
  visible: { type: Boolean, default: false },
  content: { type: String, default: '' },
  title: { type: String, default: '' },
  position: { 
    type: String as () => 'top' | 'bottom' | 'left' | 'right' | 'auto',
    default: 'auto' 
  },
  theme: { 
    type: String as () => 'dark' | 'light' | 'info' | 'warning' | 'error',
    default: 'dark' 
  },
  size: { 
    type: String as () => 'small' | 'medium' | 'large',
    default: 'medium' 
  },
  targetElement: { type: Object as () => HTMLElement | null, default: null },
  offset: { type: Number, default: 8 },
  showArrow: { type: Boolean, default: true },
  interactive: { type: Boolean, default: false },
  showClose: { type: Boolean, default: false },
  maxWidth: { type: Number, default: 300 },
  delay: { type: Number, default: 0 },
  isRichContent: { type: Boolean, default: false },
  zIndex: { type: Number, default: 9999 },
});

const emit = defineEmits(['close', 'show', 'hide']);

const tooltipEl = ref<HTMLElement | null>(null);
const computedPosition = ref<'top' | 'bottom' | 'left' | 'right'>('top');
const ariaId = `tooltip-${Math.random().toString(36).substr(2, 9)}`;

const tooltipStyle = computed(() => {
  if (!props.targetElement) return {};

  const position = calculatePosition();
  
  return {
    top: `${position.top}px`,
    left: `${position.left}px`,
    maxWidth: `${props.maxWidth}px`,
    zIndex: props.zIndex,
  };
});

const calculatePosition = (): TooltipPosition => {
  if (!props.targetElement || !tooltipEl.value) {
    return { top: 0, left: 0 };
  }

  const targetRect = props.targetElement.getBoundingClientRect();
  const tooltipRect = tooltipEl.value.getBoundingClientRect();
  const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
  const scrollY = window.pageYOffset || document.documentElement.scrollTop;
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight,
  };

  let finalPosition = props.position;
  
  // Auto-calculate best position if needed
  if (props.position === 'auto') {
    finalPosition = getBestPosition(targetRect, tooltipRect, viewport);
  }
  
  computedPosition.value = finalPosition as typeof computedPosition.value;

  switch (finalPosition) {
    case 'top':
      return {
        top: targetRect.top + scrollY - tooltipRect.height - props.offset,
        left: targetRect.left + scrollX + (targetRect.width - tooltipRect.width) / 2,
      };
    case 'bottom':
      return {
        top: targetRect.bottom + scrollY + props.offset,
        left: targetRect.left + scrollX + (targetRect.width - tooltipRect.width) / 2,
      };
    case 'left':
      return {
        top: targetRect.top + scrollY + (targetRect.height - tooltipRect.height) / 2,
        left: targetRect.left + scrollX - tooltipRect.width - props.offset,
      };
    case 'right':
      return {
        top: targetRect.top + scrollY + (targetRect.height - tooltipRect.height) / 2,
        left: targetRect.right + scrollX + props.offset,
      };
    default:
      return { top: 0, left: 0 };
  }
};

const getBestPosition = (
  targetRect: DOMRect,
  tooltipRect: DOMRect,
  viewport: { width: number; height: number }
): string => {
  const positions = ['top', 'bottom', 'left', 'right'];
  const spaceAvailable = {
    top: targetRect.top,
    bottom: viewport.height - targetRect.bottom,
    left: targetRect.left,
    right: viewport.width - targetRect.right,
  };

  // Find position with most space
  let bestPosition = 'top';
  let maxSpace = spaceAvailable.top;

  for (const position of positions) {
    if (spaceAvailable[position as keyof typeof spaceAvailable] > maxSpace) {
      maxSpace = spaceAvailable[position as keyof typeof spaceAvailable];
      bestPosition = position;
    }
  }

  return bestPosition;
};

const handleMouseEnter = () => {
  if (props.interactive) {
    // Keep tooltip open when hovering over it
  }
};

const handleMouseLeave = () => {
  if (props.interactive) {
    emit('close');
  }
};

const handleClick = (event: Event) => {
  if (props.interactive) {
    event.stopPropagation();
  }
};

const onAfterEnter = () => {
  emit('show');
};

const onBeforeLeave = () => {
  emit('hide');
};

// Update position when tooltip becomes visible
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (typeof window !== 'undefined') {
    // Watch for window resize
    window.addEventListener('resize', calculatePosition);
    
    // Watch for scroll
    window.addEventListener('scroll', calculatePosition, true);
    
    // Watch for tooltip element size changes
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(() => {
        if (props.visible) {
          nextTick(calculatePosition);
        }
      });
      
      if (tooltipEl.value) {
        resizeObserver.observe(tooltipEl.value);
      }
    }
  }
});

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', calculatePosition);
    window.removeEventListener('scroll', calculatePosition, true);
  }
  
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});

// Expose methods for external control
defineExpose({
  updatePosition: calculatePosition,
});
</script>

<style scoped>
/* Base tooltip styles using existing color system */
.tooltip-container {
  position: absolute;
  border-radius: 8px;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.875rem;
  line-height: 1.4;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  pointer-events: none;
  word-wrap: break-word;
  hyphens: auto;
}

.tooltip-interactive {
  pointer-events: auto;
  cursor: default;
}

/* Content structure */
.tooltip-content {
  padding: 12px 16px;
  position: relative;
}

.tooltip-title {
  font-weight: 600;
  font-size: 0.8125rem;
  margin-bottom: 6px;
  line-height: 1.2;
}

.tooltip-body {
  line-height: 1.4;
}

.tooltip-close {
  position: absolute;
  top: 8px;
  right: 8px;
}

.tooltip-close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}

/* Arrow styles */
.tooltip-arrow {
  position: absolute;
  width: 0;
  height: 0;
  border-style: solid;
}

/* Position-specific arrow placement */
.tooltip-top .tooltip-arrow {
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 6px 6px 0 6px;
}

.tooltip-bottom .tooltip-arrow {
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 0 6px 6px 6px;
}

.tooltip-left .tooltip-arrow {
  right: -6px;
  top: 50%;
  transform: translateY(-50%);
  border-width: 6px 0 6px 6px;
}

.tooltip-right .tooltip-arrow {
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  border-width: 6px 6px 6px 0;
}

/* Theme variations using existing color system */
.tooltip-dark {
  background: #37352f;
  color: #ffffff;
}

.tooltip-dark .tooltip-arrow {
  border-color: #37352f transparent transparent transparent;
}

.tooltip-dark.tooltip-bottom .tooltip-arrow {
  border-color: transparent transparent #37352f transparent;
}

.tooltip-dark.tooltip-left .tooltip-arrow {
  border-color: transparent transparent transparent #37352f;
}

.tooltip-dark.tooltip-right .tooltip-arrow {
  border-color: transparent #37352f transparent transparent;
}

.tooltip-dark .tooltip-close-btn {
  color: #ffffff;
}

.tooltip-dark .tooltip-close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.tooltip-light {
  background: #ffffff;
  color: #37352f;
  border: 1px solid #e9e9e7;
}

.tooltip-light .tooltip-arrow {
  border-color: #ffffff transparent transparent transparent;
}

.tooltip-light.tooltip-bottom .tooltip-arrow {
  border-color: transparent transparent #ffffff transparent;
}

.tooltip-light.tooltip-left .tooltip-arrow {
  border-color: transparent transparent transparent #ffffff;
}

.tooltip-light.tooltip-right .tooltip-arrow {
  border-color: transparent #ffffff transparent transparent;
}

.tooltip-light .tooltip-close-btn {
  color: #37352f;
}

.tooltip-light .tooltip-close-btn:hover {
  background: #f7f6f3;
}

.tooltip-info {
  background: #e3f2fd;
  color: #1565c0;
  border: 1px solid #2383e2;
}

.tooltip-info .tooltip-arrow {
  border-color: #e3f2fd transparent transparent transparent;
}

.tooltip-info.tooltip-bottom .tooltip-arrow {
  border-color: transparent transparent #e3f2fd transparent;
}

.tooltip-info.tooltip-left .tooltip-arrow {
  border-color: transparent transparent transparent #e3f2fd;
}

.tooltip-info.tooltip-right .tooltip-arrow {
  border-color: transparent #e3f2fd transparent transparent;
}

.tooltip-warning {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #f59e0b;
}

.tooltip-error {
  background: #ffeaea;
  color: #b91c1c;
  border: 1px solid #e03e3e;
}

/* Size variations */
.tooltip-small {
  font-size: 0.75rem;
}

.tooltip-small .tooltip-content {
  padding: 8px 12px;
}

.tooltip-small .tooltip-title {
  font-size: 0.75rem;
  margin-bottom: 4px;
}

.tooltip-medium {
  font-size: 0.875rem;
}

.tooltip-large {
  font-size: 1rem;
  max-width: 400px;
}

.tooltip-large .tooltip-content {
  padding: 16px 20px;
}

/* Rich content styling */
.tooltip-rich .tooltip-body {
  line-height: 1.5;
}

.tooltip-rich .tooltip-body h4 {
  margin: 0 0 8px 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: inherit;
}

.tooltip-rich .tooltip-body p {
  margin: 0 0 8px 0;
}

.tooltip-rich .tooltip-body ul {
  margin: 0 0 8px 0;
  padding-left: 20px;
}

.tooltip-rich .tooltip-body li {
  margin-bottom: 4px;
}

.tooltip-rich .tooltip-body code {
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
  font-size: 0.8em;
}

.tooltip-rich .tooltip-body strong {
  font-weight: 600;
}


.tooltip-metric-explanation p {
  margin: 8px 0;
  line-height: 1.5;
}

.tooltip-metric-explanation p:first-child {
  margin-top: 0;
}

.tooltip-metric-explanation p:last-child {
  margin-bottom: 0;
}

/* Transitions */
.tooltip-enter-active,
.tooltip-leave-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: center;
}

.tooltip-enter-from,
.tooltip-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-4px);
}

.tooltip-enter-to,
.tooltip-leave-from {
  opacity: 1;
  transform: scale(1) translateY(0);
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .tooltip-container {
    max-width: 280px !important;
    font-size: 0.8125rem;
  }
  
  .tooltip-content {
    padding: 10px 14px;
  }
  
  .tooltip-large {
    max-width: 320px !important;
  }
  
  .tooltip-small .tooltip-content {
    padding: 6px 10px;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .tooltip-enter-active,
  .tooltip-leave-active {
    transition: opacity 0.1s ease;
  }
  
  .tooltip-enter-from,
  .tooltip-leave-to {
    transform: none;
  }
}

/* High contrast support */
@media (prefers-contrast: high) {
  .tooltip-container {
    border-width: 2px;
  }
  
  .tooltip-light {
    border-color: #000000;
  }
}

/* Focus states for interactive tooltips */
.tooltip-interactive:focus-within {
  outline: 2px solid #2383e2;
  outline-offset: 2px;
}
</style>

<style>
/* Global metric tooltip specific styling (not scoped) */
.tooltip-metric-explanation .metric-ranges {
  margin: 12px 0;
}

.tooltip-metric-explanation .range-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
  font-size: 0.8125rem;
  line-height: 1.4;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.tooltip-metric-explanation .range-item .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tooltip-metric-explanation .range-item.excellent {
  background-color: rgba(16, 185, 129, 0.15);
  border-left: 3px solid #10b981;
}

.tooltip-metric-explanation .range-item.excellent .dot {
  background-color: #10b981;
}

.tooltip-metric-explanation .range-item.good {
  background-color: rgba(59, 130, 246, 0.15);
  border-left: 3px solid #3b82f6;
}

.tooltip-metric-explanation .range-item.good .dot {
  background-color: #3b82f6;
}

.tooltip-metric-explanation .range-item.fair {
  background-color: rgba(245, 158, 11, 0.15);
  border-left: 3px solid #f59e0b;
}

.tooltip-metric-explanation .range-item.fair .dot {
  background-color: #f59e0b;
}

.tooltip-metric-explanation .range-item.poor {
  background-color: rgba(239, 68, 68, 0.15);
  border-left: 3px solid #ef4444;
}

.tooltip-metric-explanation .range-item.poor .dot {
  background-color: #ef4444;
}

.tooltip-metric-explanation p {
  margin: 8px 0;
  line-height: 1.5;
}

.tooltip-metric-explanation p:first-child {
  margin-top: 0;
}

.tooltip-metric-explanation p:last-child {
  margin-bottom: 0;
}
</style>