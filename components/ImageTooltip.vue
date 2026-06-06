<template>
  <div
    v-if="isVisible"
    class="image-tooltip"
    :style="tooltipStyle"
    ref="tooltipRef"
  >
    <div class="image-container">
      <img
        v-if="imageUrl && !imageError"
        :src="imageUrl"
        :alt="`Data point ${pointIndex}`"
        @load="onImageLoad"
        @error="onImageError"
        class="tooltip-image"
      />
      <div v-else-if="isLoading" class="loading-placeholder">
        <div class="loading-spinner"></div>
        <span>Loading...</span>
      </div>
      <div v-else-if="imageError" class="error-placeholder">
        <span>Failed to load image</span>
      </div>
    </div>
    <div class="point-info">
      <div class="point-index">Point {{ pointIndex }}</div>
      <div v-if="cluster !== undefined" class="cluster-info">Cluster: {{ cluster }}</div>
      <div v-if="label !== undefined" class="label-info">Label: {{ label }}</div>
      <div class="coordinates">
        X: {{ x?.toFixed(3) }}, Y: {{ y?.toFixed(3) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

interface Props {
  pointIndex: number | null
  cluster?: number | string
  label?: number | string
  x?: number
  y?: number
  mouseX: number
  mouseY: number
  datasetName: string
  isVisible: boolean
}

const props = defineProps<Props>()

// Refs
const tooltipRef = ref<HTMLElement | null>(null)
const imageUrl = ref<string | null>(null)
const imageError = ref(false)
const isLoading = ref(false)

// Image loading cache to prevent repeated requests
const imageCache = new Map<string, { url: string; loaded: boolean; error: boolean }>()

// Debounce timer for rapid hovering protection
let loadImageTimer: NodeJS.Timeout | null = null

const tooltipStyle = computed(() => {
  const tooltipWidth = 200 // max-width from CSS
  const tooltipHeight = 140 // estimated height for compact version
  const offset = 15
  
  let left = props.mouseX + offset
  let top = props.mouseY - offset
  
  // Prevent tooltip from going off the right edge
  if (left + tooltipWidth > window.innerWidth) {
    left = props.mouseX - tooltipWidth - offset
  }
  
  // Prevent tooltip from going off the bottom edge
  if (top + tooltipHeight > window.innerHeight) {
    top = props.mouseY - tooltipHeight - offset
  }
  
  // Prevent tooltip from going off the top edge
  if (top < 0) {
    top = props.mouseY + offset
  }
  
  // Prevent tooltip from going off the left edge
  if (left < 0) {
    left = offset
  }
  
  return {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    zIndex: '9999',
    pointerEvents: 'none'
  }
})

// Check if dataset supports image tooltips
const isImageDataset = computed(() => {
  const imageDatasets = [
    'digits_full', 'digits_small', 'olivetti_faces', 'lfw_faces', 
    'coil20', 'coil100', 'mnist_full', 'fashion_mnist'
  ]
  return imageDatasets.includes(props.datasetName)
})

const shouldShowImageTooltip = computed(() => {
  return props.isVisible && 
         props.pointIndex !== null && 
         isImageDataset.value
})

// Watch for point changes and load image with debouncing
watch(() => [props.pointIndex, props.datasetName, shouldShowImageTooltip.value], 
  ([newPointIndex, newDatasetName, shouldShow]) => {
    // Reduce console noise - only log significant changes in development
    if (process.env.NODE_ENV === 'development' && (newPointIndex !== null || shouldShow)) {
      console.log('[TOOLTIP] Props changed:', { pointIndex: newPointIndex, datasetName: newDatasetName, shouldShow })
    }
    
    // Clear any pending image load
    if (loadImageTimer) {
      clearTimeout(loadImageTimer)
      loadImageTimer = null
    }

    if (!shouldShow || newPointIndex === null) {
      imageUrl.value = null
      imageError.value = false
      isLoading.value = false
      return
    }

    // Check cache first
    const cacheKey = `${newDatasetName}_${newPointIndex}`
    const cached = imageCache.get(cacheKey)
    
    if (cached) {
      if (cached.loaded) {
        imageUrl.value = cached.url
        imageError.value = false
        isLoading.value = false
      } else if (cached.error) {
        imageUrl.value = null
        imageError.value = true
        isLoading.value = false
      }
      return
    }

    // Debounce image loading to prevent rapid requests
    isLoading.value = true
    imageError.value = false
    
    loadImageTimer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/dataset-image/${newDatasetName}/${newPointIndex}`)
        
        if (!response.ok) {
          throw new Error(`Failed to load image: ${response.status}`)
        }
        
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        
        // Cache the result
        imageCache.set(cacheKey, { url, loaded: true, error: false })
        
        imageUrl.value = url
        imageError.value = false
        isLoading.value = false
      } catch (error) {
        console.warn(`Failed to load image for point ${newPointIndex}:`, error)
        imageCache.set(cacheKey, { url: '', loaded: false, error: true })
        imageUrl.value = null
        imageError.value = true
        isLoading.value = false
      }
    }, 150) // 150ms debounce delay
}, { immediate: true })

const onImageLoad = () => {
  isLoading.value = false
  imageError.value = false
}

const onImageError = () => {
  isLoading.value = false
  imageError.value = true
}

// Cleanup
const cleanup = () => {
  if (loadImageTimer) {
    clearTimeout(loadImageTimer)
    loadImageTimer = null
  }
  
  // Clean up object URLs to prevent memory leaks
  imageCache.forEach(cached => {
    if (cached.url && cached.url.startsWith('blob:')) {
      URL.revokeObjectURL(cached.url)
    }
  })
  imageCache.clear()
}

// Cleanup on unmount
import { onBeforeUnmount } from 'vue'
onBeforeUnmount(cleanup)
</script>

<style scoped>
.image-tooltip {
  background: rgba(0, 0, 0, 0.95);
  color: white;
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  max-width: 200px;
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 11px;
}

.image-container {
  margin-bottom: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.tooltip-image {
  max-width: 80px;
  max-height: 80px;
  object-fit: contain;
  border-radius: 4px;
  image-rendering: pixelated; /* For pixel art datasets like digits */
}

.loading-placeholder,
.error-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 15px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 10px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 6px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.point-info {
  font-size: 10px;
  line-height: 1.3;
}

.point-index {
  font-weight: bold;
  margin-bottom: 2px;
}

.cluster-info,
.label-info {
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 2px;
}

.coordinates {
  color: rgba(255, 255, 255, 0.7);
  font-size: 9px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .image-tooltip {
    max-width: 200px;
  }
  
  .tooltip-image {
    max-width: 100px;
    max-height: 100px;
  }
  
  .image-container {
    min-height: 100px;
  }
}
</style>
