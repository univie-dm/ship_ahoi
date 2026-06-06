import { useToast } from './useToast';

// Centralized dataset management for consistent handling across pages
import { ref, computed, watch } from 'vue'
import { useGlobalState, type DatasetInfo } from '~/composables/useGlobalState'
import { useDebugUtils } from '~/composables/useDebugUtils'

export const useDatasetManager = () => {
  const globalState = useGlobalState()
  const { debug } = useDebugUtils()
  const { addToast } = useToast();

  // Local state for current page data
  const localDataset = ref<DatasetInfo | null>(null)
  const isDatasetLoading = ref(false)
  const datasetError = ref<string | null>(null)

  // Sample dataset configurations - synchronized with ToyDatasetService
  const SAMPLE_CONFIGURATIONS = {
    // === 2D Synthetic Datasets ===
    'blobs': { dimensions: 2, defaultSamples: 200 },
    'moons': { dimensions: 2, defaultSamples: 200 },
    'circles': { dimensions: 2, defaultSamples: 200 },
    'aniso': { dimensions: 2, defaultSamples: 200 },
    'varied': { dimensions: 2, defaultSamples: 200 },
    'nostructure': { dimensions: 2, defaultSamples: 200 },
    'spiral': { dimensions: 2, defaultSamples: 200 },
    'nested': { dimensions: 2, defaultSamples: 200 },
    'elongated': { dimensions: 2, defaultSamples: 200 },
    'dense_sparse': { dimensions: 2, defaultSamples: 200 },
    'manifold': { dimensions: 2, defaultSamples: 200 },
    's_curve': { dimensions: 2, defaultSamples: 200 },

    // === High-Dimensional Synthetic Datasets ===
    'blobs_nd': { dimensions: 10, defaultSamples: 500 },
    'classification_nd': { dimensions: 15, defaultSamples: 1000 },
    'sparse_clusters': { dimensions: 20, defaultSamples: 800 },
    'hypercube': { dimensions: 8, defaultSamples: 512 },
    'swiss_roll_3d': { dimensions: 3, defaultSamples: 1000 },

    // === Real-World Datasets ===
    'iris': { dimensions: 4, defaultSamples: 150 },
    'wine': { dimensions: 13, defaultSamples: 178 },
    'breast_cancer': { dimensions: 30, defaultSamples: 569 },
    'digits_small': { dimensions: 64, defaultSamples: 1797 },
    'coil20': { dimensions: 1024, defaultSamples: 1440 },
    'olivetti_faces': { dimensions: 4096, defaultSamples: 400 },
    'newsgroups': { dimensions: 10000, defaultSamples: 18000 },
    'digits_full': { dimensions: 64, defaultSamples: 5620 },
    'california_housing': { dimensions: 8, defaultSamples: 20640 },
    'coil100': { dimensions: 49152, defaultSamples: 7200 },
    'lfw_faces': { dimensions: 5828, defaultSamples: 13000 },
    'mnist_full': { dimensions: 784, defaultSamples: 70000 },
    'diabetes': { dimensions: 10, defaultSamples: 442 },
    'palmer_penguins': { dimensions: 8, defaultSamples: 344 },
    'covtype': { dimensions: 54, defaultSamples: 581012 },
    'fashion_mnist': { dimensions: 784, defaultSamples: 10000 },
    'dataset_1': { dimensions: 13, defaultSamples: 178 },
    'dataset_2': { dimensions: 784, defaultSamples: 5000 },
    'wheats': { dimensions: 7, defaultSamples: 210 },
    'olive_oil': { dimensions: 8, defaultSamples: 572 },
    'zoo': { dimensions: 16, defaultSamples: 101 },
  } as const

  // Computed properties
  const currentDataset = computed(() => localDataset.value || globalState.currentDataset.value)

  const isDatasetAvailable = computed(() =>
    currentDataset.value !== null && !isDatasetLoading.value
  )

  const datasetSummary = computed(() => {
    const dataset = currentDataset.value
    if (!dataset) return null

    return {
      name: dataset.name,
      type: dataset.type,
      pointCount: dataset.pointCount || (dataset.data?.length || 0),
      featureCount: dataset.featureCount || (dataset.data?.[0]?.length || 0),
      hasHeaders: dataset.hasHeaders || Boolean(dataset.headers?.length),
      headers: dataset.headers || []
    }
  })

  const isUploadedDataset = computed(() => currentDataset.value?.type === 'uploaded')
  const isSampleDataset = computed(() => currentDataset.value?.type === 'sample')

  // Dataset validation
  const validateDataset = (dataset: DatasetInfo): { isValid: boolean; error?: string } => {
    if (!dataset) {
      return { isValid: false, error: 'Dataset is null or undefined' }
    }

    if (!dataset.name || !dataset.type) {
      return { isValid: false, error: 'Dataset missing required name or type' }
    }

    if (dataset.type === 'uploaded') {
      // For uploaded datasets, check if we have either data or fileId (for lazy loading)
      const hasData = dataset.data && Array.isArray(dataset.data) && dataset.data.length > 0;
      const hasFileId = dataset.fileId && typeof dataset.fileId === 'string';

      if (!hasData && !hasFileId) {
        return { isValid: false, error: 'Uploaded dataset has no data or file reference' }
      }

      // If we have data, validate it
      if (hasData) {
        const firstRow = dataset.data[0]
        if (!Array.isArray(firstRow) || firstRow.length === 0) {
          return { isValid: false, error: 'Dataset has no features' }
        }

        // Check for consistent row lengths
        const expectedLength = firstRow.length
        for (let i = 1; i < Math.min(dataset.data.length, 100); i++) {
          if (!Array.isArray(dataset.data[i]) || dataset.data[i].length !== expectedLength) {
            return { isValid: false, error: `Inconsistent row length at row ${i}` }
          }
        }
      }

      // If we only have fileId, we assume the data is valid (will be validated when loaded)
    } else if (dataset.type === 'sample') {
      if (!dataset.sampleName && !dataset.name) {
        return { isValid: false, error: 'Sample dataset missing sample name' }
      }

      const sampleName = dataset.sampleName || dataset.name.toLowerCase()
      if (!(sampleName in SAMPLE_CONFIGURATIONS)) {
        return { isValid: false, error: `Unknown sample type: ${sampleName}` }
      }
    } else if (dataset.type === 'imported') {
      // Imported datasets should have either data or proper metadata
      if (!dataset.data && !dataset.featureCount) {
        return { isValid: false, error: 'Imported dataset missing data and metadata' }
      }

      if (dataset.data && Array.isArray(dataset.data) && dataset.data.length > 0) {
        const firstRow = dataset.data[0]
        if (!Array.isArray(firstRow) || firstRow.length === 0) {
          return { isValid: false, error: 'Imported dataset has no features' }
        }
      }
    }

    return { isValid: true }
  }

  // Dataset loading and synchronization
  const loadDataset = async (dataset: DatasetInfo): Promise<boolean> => {
    isDatasetLoading.value = true
    datasetError.value = null

    try {
      // Validate dataset first
      const validation = validateDataset(dataset)
      if (!validation.isValid) {
        datasetError.value = validation.error || 'Invalid dataset'
        addToast(datasetError.value, 'error');
        return false
      }

      // Normalize dataset structure
      const normalizedDataset = normalizeDataset(dataset)

      // Update local state
      localDataset.value = normalizedDataset

      // Update global state if this is a new dataset
      if (!globalState.currentDataset.value ||
        globalState.currentDataset.value.name !== normalizedDataset.name ||
        globalState.currentDataset.value.type !== normalizedDataset.type) {
        globalState.setDataset(normalizedDataset)
      }

      debug('[DatasetManager] Successfully loaded dataset:', normalizedDataset.name)
      return true

    } catch (error) {
      datasetError.value = error instanceof Error ? error.message : 'Unknown error loading dataset'
      addToast(datasetError.value, 'error');
      console.error('[DatasetManager] Error loading dataset:', error)
      return false
    } finally {
      isDatasetLoading.value = false
    }
  }

  // Normalize dataset structure for consistency
  const normalizeDataset = (dataset: DatasetInfo): DatasetInfo => {
    const normalized = { ...dataset }

    if (dataset.type === 'sample') {
      const sampleName = dataset.sampleName || dataset.name.toLowerCase()
      const config = SAMPLE_CONFIGURATIONS[sampleName as keyof typeof SAMPLE_CONFIGURATIONS]

      if (config) {
        normalized.sampleName = sampleName
        normalized.featureCount = config.dimensions
        normalized.n_samples = dataset.n_samples || config.defaultSamples

        // Generate default headers for sample data
        if (!normalized.headers) {
          normalized.headers = Array.from({ length: config.dimensions }, (_, i) => `Feature ${i + 1}`)
        }
      }
    } else if (dataset.type === 'uploaded' && dataset.data) {
      // Calculate missing metadata for uploaded data
      if (!normalized.pointCount) {
        normalized.pointCount = dataset.data.length
      }

      if (!normalized.featureCount && dataset.data.length > 0) {
        normalized.featureCount = dataset.data[0].length
      }

      // Generate default headers if not provided
      if (!normalized.headers && normalized.featureCount) {
        normalized.headers = Array.from({ length: normalized.featureCount }, (_, i) => `Column ${i + 1}`)
      }

      // Set hasHeaders flag
      if (normalized.hasHeaders === undefined) {
        normalized.hasHeaders = Boolean(dataset.headers?.length)
      }
    } else if (dataset.type === 'imported') {
      // Handle imported datasets - they should already have proper metadata
      if (!normalized.pointCount && dataset.data) {
        normalized.pointCount = dataset.data.length
      }

      if (!normalized.featureCount) {
        if (dataset.headers) {
          normalized.featureCount = dataset.headers.length
        } else if (dataset.data && dataset.data.length > 0) {
          normalized.featureCount = dataset.data[0].length
        }
      }

      // Ensure headers are set
      if (!normalized.headers && normalized.featureCount) {
        normalized.headers = Array.from({ length: normalized.featureCount }, (_, i) => `Feature_${i + 1}`)
      }

      // Set hasHeaders flag
      if (normalized.hasHeaders === undefined) {
        normalized.hasHeaders = Boolean(dataset.headers?.length)
      }
    }

    return normalized
  }

  // Sync with global state changes
  const syncWithGlobalState = () => {
    const globalDataset = globalState.currentDataset.value
    if (globalDataset && (!localDataset.value ||
      localDataset.value.name !== globalDataset.name ||
      localDataset.value.type !== globalDataset.type)) {

      debug('[DatasetManager] Syncing with global state:', globalDataset.name)
      loadDataset(globalDataset)
    }
  }

  // Clear dataset
  const clearDataset = () => {
    localDataset.value = null
    datasetError.value = null
    globalState.clearDataset()
    debug('[DatasetManager] Cleared dataset')
  }

  // Get feature names with fallbacks
  const getFeatureNames = (): string[] => {
    const dataset = currentDataset.value
    if (!dataset) return []

    // Known feature names for specific sample datasets
    const knownFeatureNames: Record<string, string[]> = {
      'palmer_penguins': [
        'bill_length_mm', 'bill_depth_mm', 'flipper_length_mm', 'body_mass_g',
        'sex', 'island_Biscoe', 'island_Dream', 'island_Torgersen'
      ],
      'wheats': [
        'Area', 'Perimeter', 'Compactness', 'Kernel Length',
        'Kernel Width', 'Asymmetry Coeff.', 'Groove Length'
      ],
      'olive_oil': [
        'Palmitic', 'Palmitoleic', 'Stearic', 'Oleic',
        'Linoleic', 'Linolenic', 'Arachidic', 'Eicosenoic'
      ],
      'zoo': [
        'Hair', 'Feathers', 'Eggs', 'Milk', 'Airborne', 'Aquatic',
        'Predator', 'Toothed', 'Backbone', 'Breathes', 'Venomous',
        'Fins', 'Legs', 'Tail', 'Domestic', 'Catsize'
      ],
    }

    // Check if this is a known sample dataset
    if (dataset.type === 'sample' && dataset.sampleName && knownFeatureNames[dataset.sampleName]) {
      return knownFeatureNames[dataset.sampleName]
    }

    if (dataset.headers && dataset.headers.length > 0) {
      return dataset.headers
    }

    const featureCount = dataset.featureCount || 0
    return Array.from({ length: featureCount }, (_, i) => `Feature ${i + 1}`)
  }

  // Get data sample for preview
  const getDataSample = (maxRows: number = 10): number[][] => {
    const dataset = currentDataset.value
    if (!dataset || dataset.type !== 'uploaded' || !dataset.data) {
      return []
    }

    return dataset.data.slice(0, maxRows)
  }

  // Check if two datasets are the same
  const isSameDataset = (dataset1: DatasetInfo | null, dataset2: DatasetInfo | null): boolean => {
    if (!dataset1 || !dataset2) return dataset1 === dataset2

    return dataset1.name === dataset2.name &&
      dataset1.type === dataset2.type &&
      (dataset1.type === 'sample' ?
        (dataset1.sampleName === dataset2.sampleName) :
        (dataset1.fileName === dataset2.fileName))
  }

  // Generate dataset signature for caching/comparison
  const getDatasetSignature = (dataset?: DatasetInfo): string => {
    const ds = dataset || currentDataset.value
    if (!ds) return 'no-dataset'

    if (ds.type === 'sample') {
      return `sample_${ds.sampleName || ds.name}_${ds.n_samples || 200}`
    } else if (ds.type === 'uploaded') {
      return `uploaded_${ds.fileName || ds.name}_${ds.pointCount || 0}_${ds.featureCount || 0}`
    }

    return 'unknown-dataset'
  }

  // Watch for global state changes
  watch(() => globalState.currentDataset.value, (newDataset, oldDataset) => {
    if (newDataset && !isSameDataset(newDataset, localDataset.value)) {
      debug('[DatasetManager] Global dataset changed, syncing...')
      loadDataset(newDataset)
    } else if (!newDataset && localDataset.value) {
      debug('[DatasetManager] Global dataset cleared, clearing local state')
      localDataset.value = null
    }
  }, { immediate: true })

  return {
    // State
    currentDataset: currentDataset,
    isDatasetLoading: isDatasetLoading,
    datasetError: datasetError,
    datasetSummary: datasetSummary,

    // Computed
    isDatasetAvailable,
    isUploadedDataset,
    isSampleDataset,

    // Methods
    loadDataset,
    clearDataset,
    validateDataset,
    normalizeDataset,
    syncWithGlobalState,
    getFeatureNames,
    getDataSample,
    isSameDataset,
    getDatasetSignature,

    // Constants
    SAMPLE_CONFIGURATIONS
  }
}
