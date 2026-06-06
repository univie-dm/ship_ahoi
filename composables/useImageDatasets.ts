import { ref, computed } from 'vue'

// Image datasets that can be visualized as pictures
export const IMAGE_DATASETS = {
  'digits_small': {
    name: 'digits_small',
    imageShape: [8, 8],
    channels: 1, // grayscale
    normalize: true,
    colormap: 'gray'
  },
  'optdigits': {
    name: 'optdigits',
    imageShape: [8, 8],
    channels: 1, // grayscale
    normalize: true,
    colormap: 'gray'
  },
  'olivetti_faces': {
    name: 'olivetti_faces',
    imageShape: [64, 64],
    channels: 1, // grayscale
    normalize: true,
    colormap: 'gray'
  },
  'mnist_full': {
    name: 'mnist_full',
    imageShape: [28, 28],
    channels: 1, // grayscale
    normalize: true,
    colormap: 'gray'
  },
  'fashion_mnist': {
    name: 'fashion_mnist',
    imageShape: [28, 28],
    channels: 1, // grayscale
    normalize: true,
    colormap: 'gray'
  },
  'dataset_2': {
    name: 'dataset_2',
    imageShape: [28, 28],
    channels: 1, // grayscale
    normalize: true,
    colormap: 'gray'
  }
} as const

export type ImageDatasetName = keyof typeof IMAGE_DATASETS

export interface ImageHoverState {
  isVisible: boolean
  imageData: number[] | null
  position: { x: number, y: number }
  pointIndex: number | null
  datasetName: string | null
}

// Throttling state to prevent loading too many images
const imageLoadQueue = ref<Set<number>>(new Set())
const maxConcurrentLoads = 3
const loadThrottleMs = 100

export const useImageDatasets = () => {
  const hoverState = ref<ImageHoverState>({
    isVisible: false,
    imageData: null,
    position: { x: 0, y: 0 },
    pointIndex: null,
    datasetName: null
  })

  // Check if a dataset supports image visualization
  const isImageDataset = (datasetName: string): boolean => {
    return datasetName in IMAGE_DATASETS
  }

  // Get image configuration for a dataset
  const getImageConfig = (datasetName: string) => {
    return IMAGE_DATASETS[datasetName as ImageDatasetName] || null
  }

  // Convert flat array to image data URL with throttling protection
  const createImageDataUrl = (
    flatData: number[],
    config: typeof IMAGE_DATASETS[ImageDatasetName],
    pointIndex: number
  ): string | null => {
    // Throttling: check if we're already loading too many images
    if (imageLoadQueue.value.size >= maxConcurrentLoads) {
      return null
    }

    // Add to load queue
    imageLoadQueue.value.add(pointIndex)

    // Clean up queue after throttle period
    setTimeout(() => {
      imageLoadQueue.value.delete(pointIndex)
    }, loadThrottleMs)

    try {
      const [height, width] = config.imageShape
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')

      if (!ctx) return null

      const imageData = ctx.createImageData(width, height)
      const data = imageData.data

      // Normalize data if needed
      let normalizedData = flatData
      if (config.normalize) {
        const min = Math.min(...flatData)
        const max = Math.max(...flatData)
        const range = max - min
        if (range > 0) {
          normalizedData = flatData.map(val => (val - min) / range)
        }
      }

      // Convert to RGBA
      for (let i = 0; i < normalizedData.length; i++) {
        const pixelValue = Math.floor(normalizedData[i] * 255)
        const pixelIndex = i * 4

        if (config.colormap === 'gray') {
          data[pixelIndex] = pixelValue     // R
          data[pixelIndex + 1] = pixelValue // G
          data[pixelIndex + 2] = pixelValue // B
          data[pixelIndex + 3] = 255        // A
        }
      }

      ctx.putImageData(imageData, 0, 0)
      return canvas.toDataURL()
    } catch (error) {
      console.error('Error creating image data URL:', error)
      return null
    }
  }

  // Show image hover with throttling
  const showImageHover = (
    pointIndex: number,
    imageData: number[],
    position: { x: number, y: number },
    datasetName: string
  ) => {
    // Don't show if we're throttling this point
    if (imageLoadQueue.value.has(pointIndex)) {
      return
    }

    hoverState.value = {
      isVisible: true,
      imageData,
      position,
      pointIndex,
      datasetName
    }
  }

  // Hide image hover
  const hideImageHover = () => {
    hoverState.value = {
      isVisible: false,
      imageData: null,
      position: { x: 0, y: 0 },
      pointIndex: null,
      datasetName: null
    }
  }

  // Update hover position without changing visibility
  const updateHoverPosition = (position: { x: number, y: number }) => {
    if (hoverState.value.isVisible) {
      hoverState.value.position = position
    }
  }

  // Clear throttling queue (useful for cleanup)
  const clearThrottleQueue = () => {
    imageLoadQueue.value.clear()
  }

  return {
    hoverState: computed(() => hoverState.value),
    isImageDataset,
    getImageConfig,
    createImageDataUrl,
    showImageHover,
    hideImageHover,
    updateHoverPosition,
    clearThrottleQueue,
    IMAGE_DATASETS
  }
}