// Global state management for dataset and run history
import { ref, computed, shallowRef, readonly } from 'vue'
import { useMemoryManagement } from './useMemoryManagement'
import { useDebugUtils } from './useDebugUtils'
import { useHistoryPersistence } from './useHistoryPersistence'

export interface ClusterRun {
  id: string
  timestamp: Date
  dataset: string
  treeType: string
  partitionMethod: string
  selectedK: number
  selectedPower: number
  actualClusterCount?: number
  clusterData: any
  treeData: any
  parameters: {
    sample: string
    uploadedFileName?: string
    n_samples?: number
    fileId?: string
    datasetInfo?: Partial<DatasetInfo>
  }
  metrics?: {
    silhouetteScore?: number
    dbIndex?: number
    calinskiHarabasz?: number
    ari?: number
    discoScore?: number
  }
}

export interface DatasetInfo {
  name: string
  type: 'sample' | 'uploaded' | 'imported'
  data?: number[][]
  fileName?: string
  pointCount?: number
  featureCount?: number
  originalData?: any[][]
  columnConfig?: any[]
  sampleName?: string;
  n_samples?: number;
  headers?: string[];
  hasHeaders?: boolean;
  missingValueStrategy?: string;
  normalization?: string;
  dataConfig?: {
    missingValueStrategy?: string;
    normalization: string;
    categoricalEncoding: string;
    columns: any[];
  }
  columnTypes?: string[];
  featureColumns?: number[];
  labelColumns?: number[];
  ignoredColumns?: number[];
  rawData?: any[][];
  // Backend integration fields
  fileId?: string;
  backendMetadata?: any;
  groundTruthColumn?: number;
  groundTruthColumnName?: string;
  // Enhanced dataset comparison fields
  contentHash?: string;
  fileSize?: number;
}

// Memory management and debugging utilities
const { trackLargeObject, clearComponentMemory } = useMemoryManagement()
const { debug, debugWarn, debugError } = useDebugUtils()

// History persistence - lazy loaded
let historyPersistence: ReturnType<typeof useHistoryPersistence> | null = null

const getHistoryPersistence = () => {
  if (!historyPersistence) {
    historyPersistence = useHistoryPersistence()
  }
  return historyPersistence
}

// Global reactive state - use shallowRef for large data structures
const currentDataset = ref<DatasetInfo | null>(null)
const clusterRuns = shallowRef<ClusterRun[]>([])
const activeRunId = ref<string | null>(null)
const sidebarHidden = ref<boolean>(false)
const onboardingCompleted = ref<boolean>(false)

// In-memory visualization preferences - persist across page navigations within a session
const visualizationPreferences = ref<{
  selectedXAxis: string | null
  selectedYAxis: string | null
  selectedPlotType: string | null
}>({
  selectedXAxis: null,
  selectedYAxis: null,
  selectedPlotType: null
})

// localStorage persistence constants for clustering history
const CLUSTER_RUNS_KEY = 'clusterRuns'
const CLUSTER_RUNS_VERSION_KEY = 'clusterRunsVersion'
const CURRENT_RUNS_VERSION = '1.0'
const MAX_LOCALSTORAGE_RUNS = 20 // Limit to avoid localStorage quota issues

// Helper function to save runs to localStorage
const saveRunsToLocalStorage = (runs: ClusterRun[]) => {
  if (typeof window === 'undefined') return

  try {
    // Limit the number of runs and strip large data to save space
    const runsToSave = runs.slice(0, MAX_LOCALSTORAGE_RUNS).map(run => ({
      ...run,
      timestamp: run.timestamp instanceof Date ? run.timestamp.toISOString() : run.timestamp,
      // Strip large data blobs to save localStorage space - keep essential metadata
      clusterData: run.clusterData ? {
        ...run.clusterData,
        // Keep cluster assignments and essential info, strip large arrays
        assignments: run.clusterData.assignments,
        clusterSizes: run.clusterData.clusterSizes,
        // Don't save raw point data in localStorage
        points: undefined,
        centroids: undefined
      } : undefined,
      // Strip tree visualization data (can be large)
      treeData: undefined
    }))

    localStorage.setItem(CLUSTER_RUNS_KEY, JSON.stringify(runsToSave))
    localStorage.setItem(CLUSTER_RUNS_VERSION_KEY, CURRENT_RUNS_VERSION)
    debug('[GlobalState] Saved', runsToSave.length, 'runs to localStorage')
  } catch (error) {
    debugWarn('[GlobalState] Failed to save runs to localStorage:', error)
    // If localStorage is full, try to clear old data
    try {
      localStorage.removeItem(CLUSTER_RUNS_KEY)
      localStorage.removeItem(CLUSTER_RUNS_VERSION_KEY)
    } catch { }
  }
}

// Helper function to load runs from localStorage
const loadRunsFromLocalStorage = (): ClusterRun[] => {
  if (typeof window === 'undefined') return []

  try {
    const savedVersion = localStorage.getItem(CLUSTER_RUNS_VERSION_KEY)
    if (savedVersion !== CURRENT_RUNS_VERSION) {
      // Version mismatch, clear old data
      localStorage.removeItem(CLUSTER_RUNS_KEY)
      localStorage.removeItem(CLUSTER_RUNS_VERSION_KEY)
      return []
    }

    const savedRuns = localStorage.getItem(CLUSTER_RUNS_KEY)
    if (!savedRuns) return []

    const parsedRuns = JSON.parse(savedRuns)
    if (!Array.isArray(parsedRuns)) return []

    // Convert timestamp strings back to Date objects and validate
    return parsedRuns.map((run: any) => ({
      ...run,
      timestamp: new Date(run.timestamp)
    })).filter((run: any) => run.id && run.timestamp && !isNaN(run.timestamp.getTime()))
  } catch (error) {
    debugWarn('[GlobalState] Failed to load runs from localStorage:', error)
    return []
  }
}

// Flag to track if initial load has been done
let initialLoadDone = false

// Initialize clusterRuns from localStorage on module load
if (typeof window !== 'undefined' && !initialLoadDone) {
  const savedRuns = loadRunsFromLocalStorage()
  if (savedRuns.length > 0) {
    clusterRuns.value = savedRuns
    debug('[GlobalState] Restored', savedRuns.length, 'runs from localStorage on init')
  }
  initialLoadDone = true
}


// Enhanced sample options with categories and descriptions
const sampleOptions = shallowRef([
  // === 2D Synthetic Datasets ===
  {
    label: 'Blobs',
    value: 'blobs',
    category: 'synthetic_2d',
    description: 'Gaussian clusters with clear separation - ideal for basic clustering',
    difficulty: 'easy',
    dimensions: 2,
    typical_samples: 200
  },
  {
    label: 'Moons',
    value: 'moons',
    category: 'synthetic_2d',
    description: 'Two interleaving half-circles - tests non-linear clustering',
    difficulty: 'medium',
    dimensions: 2,
    typical_samples: 200
  },
  {
    label: 'Circles',
    value: 'circles',
    category: 'synthetic_2d',
    description: 'Concentric circles pattern - challenges density-based clustering',
    difficulty: 'medium',
    dimensions: 2,
    typical_samples: 200
  },
  {
    label: 'Anisotropic',
    value: 'aniso',
    category: 'synthetic_2d',
    description: 'Elongated clusters at different angles - tests shape sensitivity',
    difficulty: 'medium',
    dimensions: 2,
    typical_samples: 200
  },
  {
    label: 'Varied Density',
    value: 'varied',
    category: 'synthetic_2d',
    description: 'Clusters with different sizes and densities',
    difficulty: 'medium',
    dimensions: 2,
    typical_samples: 200
  },
  {
    label: 'Spirals',
    value: 'spiral',
    category: 'synthetic_2d',
    description: 'Two interleaving spiral patterns - very challenging',
    difficulty: 'hard',
    dimensions: 2,
    typical_samples: 200
  },

  // === High-Dimensional Synthetic Datasets ===
  {
    label: 'Cosmic Web Simulation',
    value: 'blobs_nd',
    category: 'synthetic_nd',
    description: 'Multi-dimensional galaxy clusters in cosmic web (5-20D) - simulates dark matter halos',
    difficulty: 'medium',
    dimensions: 10,
    typical_samples: 500,
    supports_custom_dims: true,
    max_dims: 20
  },
  {
    label: 'Gene Expression Network',
    value: 'classification_nd',
    category: 'synthetic_nd',
    description: 'High-dimensional gene regulation patterns with noise - models cellular pathways',
    difficulty: 'hard',
    dimensions: 15,
    typical_samples: 1000,
    supports_custom_dims: true,
    max_dims: 50
  },
  {
    label: 'Quantum State Manifold',
    value: 'sparse_clusters',
    category: 'synthetic_nd',
    description: 'Sparse clusters in quantum Hilbert space - tests curse of dimensionality',
    difficulty: 'hard',
    dimensions: 20,
    typical_samples: 800,
    supports_custom_dims: true,
    max_dims: 100
  },
  {
    label: 'Crystalline Lattice',
    value: 'hypercube',
    category: 'synthetic_nd',
    description: 'Atomic positions in crystal structures - clusters on hypercube vertices',
    difficulty: 'hard',
    dimensions: 8,
    typical_samples: 512,
    supports_custom_dims: true,
    max_dims: 15
  },
  {
    label: 'Protein Folding Space',
    value: 'swiss_roll_3d',
    category: 'synthetic_nd',
    description: 'Protein conformational space manifold - models amino acid interactions',
    difficulty: 'hard',
    dimensions: 3,
    typical_samples: 1000
  },
  {
    label: 'Neural Network Embedding',
    value: 'neural_embedding',
    category: 'synthetic_nd',
    description: 'High-dimensional word embeddings with semantic clusters - NLP-inspired',
    difficulty: 'hard',
    dimensions: 25,
    typical_samples: 1200,
    supports_custom_dims: true,
    max_dims: 50
  },

  // === Real-World Datasets ===
  {
    label: 'Iris',
    value: 'iris',
    category: 'real_world',
    description: 'Classic iris flower dataset - 4 features, 3 species, 150 samples',
    difficulty: 'easy',
    dimensions: 4,
    typical_samples: 150
  },
  {
    label: 'Dataset 1',
    value: 'dataset_1',
    category: 'study',
    description: '178 samples · 13 features',
    difficulty: 'medium',
    dimensions: 13,
    typical_samples: 178
  },
  {
    label: 'Breast Cancer',
    value: 'breast_cancer',
    category: 'real_world',
    description: 'Breast cancer diagnosis - 30 features, 2 classes, 569 samples',
    difficulty: 'medium',
    dimensions: 30,
    typical_samples: 569
  },
  {
    label: 'Digits (Small)',
    value: 'digits_small',
    category: 'real_world',
    description: 'Handwritten digits - 64 pixels (8x8), 10 classes, 1797 samples',
    difficulty: 'hard',
    dimensions: 64,
    typical_samples: 1797
  },
  {
    label: 'COIL20',
    value: 'coil20',
    category: 'real_world',
    description: 'COIL20 object recognition - 20 objects, 72 angles each, 1440 grayscale images',
    difficulty: 'hard',
    dimensions: 1024,
    typical_samples: 1440,
    requiresDownload: true
  },
  {
    label: 'Olivetti Faces',
    value: 'olivetti_faces',
    category: 'real_world',
    description: 'Olivetti faces - 40 people, 10 images each, 400 grayscale face images',
    difficulty: 'hard',
    dimensions: 4096,
    typical_samples: 400,
    requiresDownload: true
  },
  {
    label: 'Digits (Big)',
    value: 'digits_full',
    category: 'real_world',
    description: 'Full handwritten digits - 64 pixels (8x8), 10 classes, 5620 samples',
    difficulty: 'medium',
    dimensions: 64,
    typical_samples: 5620
  },
  {
    label: 'California Housing',
    value: 'california_housing',
    category: 'real_world',
    description: 'California housing prices - 8 features, 20640 samples',
    difficulty: 'medium',
    dimensions: 8,
    typical_samples: 20640,
    requiresDownload: true
  },
  {
    label: 'Diabetes',
    value: 'diabetes',
    category: 'real_world',
    description: 'Diabetes dataset - 10 features, 442 samples',
    difficulty: 'medium',
    dimensions: 10,
    typical_samples: 442
  },
  {
    label: 'Palmer Penguins',
    value: 'palmer_penguins',
    category: 'real_world',
    description: 'Palmer Penguins - Antarctic penguin species with bill and body measurements, 3 species, 344 samples',
    difficulty: 'easy',
    dimensions: 8,
    typical_samples: 344,
    requiresDownload: true
  },
  {
    label: 'Dataset 2',
    value: 'dataset_2',
    category: 'study',
    description: '5,000 samples · 784 features',
    difficulty: 'medium',
    dimensions: 784,
    typical_samples: 5000,
    requiresDownload: true
  },
  {
    label: 'Wheats',
    value: 'wheats',
    category: 'study',
    description: '210 samples · 7 features · 3 wheat varieties',
    difficulty: 'easy',
    dimensions: 7,
    typical_samples: 210
  },
  {
    label: 'Olive Oil',
    value: 'olive_oil',
    category: 'study',
    description: '572 samples · 8 features · 3 regions (9 areas)',
    difficulty: 'easy',
    dimensions: 8,
    typical_samples: 572,
    requiresDownload: true
  },
  {
    label: 'Zoo',
    value: 'zoo',
    category: 'study',
    description: '101 samples · 16 features · 7 animal classes',
    difficulty: 'easy',
    dimensions: 16,
    typical_samples: 101,
    requiresDownload: true
  }
])

export const useGlobalState = () => {
  // Computed properties
  const activeRun = computed(() => {
    if (!activeRunId.value) return null
    return clusterRuns.value.find(run => run.id === activeRunId.value) || null
  })

  const recentRuns = computed(() => {
    return clusterRuns.value
      .slice()
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, 10)
  })

  const hasData = computed(() => currentDataset.value !== null)

  // Dataset category helpers
  const sampleOptionsByCategory = computed(() => {
    const categories = {
      synthetic_2d: [],
      synthetic_nd: [],
      real_world: [],
      study: []
    } as Record<string, any[]>

    sampleOptions.value.forEach(option => {
      if (categories[option.category]) {
        categories[option.category].push(option)
      }
    })

    return categories
  })

  const getSampleOption = (value: string) => {
    return sampleOptions.value.find(option => option.value === value)
  }

  // Dataset comparison helpers
  const isUploadedDatasetChanged = (current: DatasetInfo, dataset: DatasetInfo): boolean => {
    // First check if we have content hashes for comparison
    if (current.contentHash && dataset.contentHash) {
      return current.contentHash !== dataset.contentHash
    }

    // Check fileId comparison - important for backend processing
    if (current.fileId && dataset.fileId) {
      return current.fileId !== dataset.fileId
    }

    // If one has fileId and the other doesn't, consider it a change
    if (current.fileId !== dataset.fileId) {
      return true
    }

    // Fallback to file size and basic metadata comparison if no content hash
    if (current.fileSize && dataset.fileSize && current.fileSize !== dataset.fileSize) {
      return true
    }

    // More permissive file name comparison - only compare base names
    if (current.fileName && dataset.fileName) {
      const currentBaseName = current.fileName.split('/').pop()?.split('.')[0]
      const newBaseName = dataset.fileName.split('/').pop()?.split('.')[0]
      if (currentBaseName && newBaseName && currentBaseName !== newBaseName) {
        return true
      }
    }

    return false
  }

  const isSignificantDatasetChange = (current: DatasetInfo, dataset: DatasetInfo): boolean => {
    // Dataset name or type change is always significant
    if (current.name !== dataset.name || current.type !== dataset.type) {
      return true
    }

    // For uploaded datasets, use enhanced comparison
    if (dataset.type === 'uploaded') {
      return isUploadedDatasetChanged(current, dataset)
    }

    // For sample datasets, only significant if it's a different sample type
    if (dataset.type === 'sample') {
      return current.name !== dataset.name
    }

    return false
  }

  // Dataset management
  const setDataset = (dataset: DatasetInfo) => {
    const current = currentDataset.value

    // Enhanced dataset comparison logic
    const isDatasetChange = !current ||
      current.name !== dataset.name ||
      current.type !== dataset.type ||
      (dataset.type === 'sample' && current.n_samples !== dataset.n_samples) ||
      (dataset.type === 'uploaded' && isUploadedDatasetChanged(current, dataset))

    if (isDatasetChange) {
      debug('[GlobalState] Dataset change detected:', {
        old: current ? {
          name: current.name,
          type: current.type,
          n_samples: current.n_samples,
          fileName: current.fileName,
          contentHash: current.contentHash,
          fileId: current.fileId
        } : null,
        new: {
          name: dataset.name,
          type: dataset.type,
          n_samples: dataset.n_samples,
          fileName: dataset.fileName,
          contentHash: dataset.contentHash,
          fileId: dataset.fileId
        }
      })

      // Clear clustering parameters when dataset changes to prevent incompatible parameters
      clearClusteringParameters()
      debug('[GlobalState] Cleared clustering parameters due to dataset change')

      // NEVER clear runs automatically - preserve ALL runs for history functionality
      debug('[GlobalState] Dataset change detected - preserving all existing runs for history:', {
        preservedRuns: clusterRuns.value.length,
        oldDataset: current ? {
          name: current.name,
          type: current.type,
          n_samples: current.n_samples
        } : null,
        newDataset: {
          name: dataset.name,
          type: dataset.type,
          n_samples: dataset.n_samples
        }
      })

      // Always update the current dataset to the new one
      // Ensure featureCount and headers are properly calculated if missing
      if (dataset.data && dataset.data.length > 0 && Array.isArray(dataset.data[0])) {
        if (!dataset.featureCount) {
          dataset.featureCount = dataset.data[0].length
          debug('[GlobalState] Calculated missing featureCount:', dataset.featureCount)
        }
        if (!dataset.headers || dataset.headers.length !== dataset.featureCount) {
          dataset.headers = Array.from({ length: dataset.featureCount }, (_, i) => `Feature ${i + 1}`)
          debug('[GlobalState] Generated missing headers:', dataset.headers.length, 'headers')
        }
      }

      // Validate and clean column configuration if present
      if (dataset.columnConfig && dataset.columnConfig.length > 0) {
        const originalLength = dataset.columnConfig.length;
        dataset.columnConfig = validateColumnConfig(dataset.columnConfig);
        if (dataset.columnConfig.length !== originalLength) {
          debug('[GlobalState] Cleaned column config:', originalLength, '->', dataset.columnConfig.length, 'valid columns');
        }
      }

      currentDataset.value = dataset
      debug('[GlobalState] Dataset updated with fileId:', dataset.fileId)
    } else {
      // Even if no change detected, ensure we update the dataset reference
      // Ensure featureCount and headers are properly calculated if missing
      if (dataset.data && dataset.data.length > 0 && Array.isArray(dataset.data[0])) {
        if (!dataset.featureCount) {
          dataset.featureCount = dataset.data[0].length
          debug('[GlobalState] Calculated missing featureCount (no change):', dataset.featureCount)
        }
        if (!dataset.headers || dataset.headers.length !== dataset.featureCount) {
          dataset.headers = Array.from({ length: dataset.featureCount }, (_, i) => `Feature ${i + 1}`)
          debug('[GlobalState] Generated missing headers (no change):', dataset.headers.length, 'headers')
        }
      }

      // Validate and clean column configuration if present
      if (dataset.columnConfig && dataset.columnConfig.length > 0) {
        const originalLength = dataset.columnConfig.length;
        dataset.columnConfig = validateColumnConfig(dataset.columnConfig);
        if (dataset.columnConfig.length !== originalLength) {
          debug('[GlobalState] Cleaned column config (no change):', originalLength, '->', dataset.columnConfig.length, 'valid columns');
        }
      }

      currentDataset.value = dataset
      debug('[GlobalState] Dataset updated (no change) with fileId:', dataset.fileId)
    }
  }

  const setCurrentDataset = (dataset: DatasetInfo) => {
    // Ensure featureCount and headers are properly calculated if missing
    if (dataset.data && dataset.data.length > 0 && Array.isArray(dataset.data[0])) {
      if (!dataset.featureCount) {
        dataset.featureCount = dataset.data[0].length
        debug('[GlobalState] Calculated missing featureCount in setCurrentDataset:', dataset.featureCount)
      }
      if (!dataset.headers || dataset.headers.length !== dataset.featureCount) {
        dataset.headers = Array.from({ length: dataset.featureCount }, (_, i) => `Feature ${i + 1}`)
        debug('[GlobalState] Generated missing headers in setCurrentDataset:', dataset.headers.length, 'headers')
      }
    }

    // Validate and clean column configuration if present
    if (dataset.columnConfig && dataset.columnConfig.length > 0) {
      const originalLength = dataset.columnConfig.length;
      dataset.columnConfig = validateColumnConfig(dataset.columnConfig);
      if (dataset.columnConfig.length !== originalLength) {
        debug('[GlobalState] Cleaned column config in setCurrentDataset:', originalLength, '->', dataset.columnConfig.length, 'valid columns');
      }
    }

    currentDataset.value = dataset
  }

  const clearDataset = () => {
    currentDataset.value = null
    // Clear parameters when dataset changes to prevent stale parameters
    clearClusteringParameters()
    debug('[GlobalState] Cleared dataset and clustering parameters')
  }

  const clearCurrentDataset = () => {
    currentDataset.value = null
    // Clear parameters when dataset changes to prevent stale parameters
    clearClusteringParameters()
    debug('[GlobalState] Cleared current dataset and clustering parameters')
  }

  // Clustering parameters management with versioning
  const CLUSTERING_PARAMS_KEY = 'clusteringParameters';
  const CLUSTERING_PARAMS_VERSION_KEY = 'clusteringParametersVersion';
  const CURRENT_PARAMS_VERSION = '1.0';
  const clusteringParameters = ref<any>(null);

  // Onboarding completion tracking
  const ONBOARDING_COMPLETED_KEY = 'onboardingCompleted';

  // Validate and clean column configuration
  const validateColumnConfig = (columnConfig: any[]): any[] => {
    if (!Array.isArray(columnConfig)) {
      debugWarn('[GlobalState] columnConfig is not an array, using empty array');
      return [];
    }

    return columnConfig.filter((col, index) => {
      // Check if column object is valid
      if (!col || typeof col !== 'object') {
        debugWarn(`[GlobalState] Invalid column config at index ${index}:`, col);
        return false;
      }

      // Ensure required properties exist
      const hasRequiredProps = col.name !== undefined &&
        col.index !== undefined &&
        col.data_type !== undefined &&
        col.usage !== undefined;

      if (!hasRequiredProps) {
        debugWarn(`[GlobalState] Column config missing required properties at index ${index}:`, col);
        return false;
      }

      return true;
    }).map(col => ({
      name: String(col.name),
      index: Number(col.index),
      data_type: String(col.data_type),
      usage: String(col.usage),
      normalize: Boolean(col.normalize),
      is_categorical: Boolean(col.is_categorical)
    }));
  };

  // Validate clustering parameters structure
  const validateClusteringParameters = (params: any): boolean => {
    if (!params || typeof params !== 'object') return false;

    // Check for required parameter structure
    const requiredFields = ['treeType', 'partitionMethod'];
    const hasRequiredFields = requiredFields.some(field => params[field] !== undefined);

    if (!hasRequiredFields) {
      debugWarn('[GlobalState] Invalid clustering parameters: missing required fields');
      return false;
    }

    return true;
  };

  // Restore from localStorage if available and valid
  if (typeof window !== 'undefined') {
    const savedParams = localStorage.getItem(CLUSTERING_PARAMS_KEY);
    const savedVersion = localStorage.getItem(CLUSTERING_PARAMS_VERSION_KEY);

    if (savedParams && savedVersion === CURRENT_PARAMS_VERSION) {
      try {
        const parsedParams = JSON.parse(savedParams);
        if (validateClusteringParameters(parsedParams)) {
          clusteringParameters.value = parsedParams;
          debug('[GlobalState] Restored valid clusteringParameters from localStorage:', clusteringParameters.value);
        } else {
          debugWarn('[GlobalState] Invalid clustering parameters found in localStorage, clearing...');
          localStorage.removeItem(CLUSTERING_PARAMS_KEY);
          localStorage.removeItem(CLUSTERING_PARAMS_VERSION_KEY);
        }
      } catch (e) {
        debugWarn('[GlobalState] Failed to parse clusteringParameters from localStorage:', e);
        localStorage.removeItem(CLUSTERING_PARAMS_KEY);
        localStorage.removeItem(CLUSTERING_PARAMS_VERSION_KEY);
      }
    } else if (savedParams) {
      debugWarn('[GlobalState] Clustering parameters version mismatch, clearing old parameters');
      localStorage.removeItem(CLUSTERING_PARAMS_KEY);
      localStorage.removeItem(CLUSTERING_PARAMS_VERSION_KEY);
    }

    // Restore onboarding completion state
    const savedOnboardingState = localStorage.getItem(ONBOARDING_COMPLETED_KEY);
    if (savedOnboardingState) {
      try {
        onboardingCompleted.value = JSON.parse(savedOnboardingState);
        debug('[GlobalState] Restored onboarding completion state:', onboardingCompleted.value);
      } catch (e) {
        debugWarn('[GlobalState] Failed to parse onboarding completion state:', e);
      }
    }
  }

  const setClusteringParameters = (params: any) => {
    // Validate parameters before setting
    if (!validateClusteringParameters(params)) {
      debugWarn('[GlobalState] Attempting to set invalid clustering parameters:', params);
      return;
    }

    clusteringParameters.value = params;
    if (typeof window !== 'undefined') {
      localStorage.setItem(CLUSTERING_PARAMS_KEY, JSON.stringify(params));
      localStorage.setItem(CLUSTERING_PARAMS_VERSION_KEY, CURRENT_PARAMS_VERSION);
      debug('[GlobalState] Saved validated clusteringParameters to localStorage:', params);
    }
  }

  const updateClusteringParameter = (key: string, value: any) => {
    if (!clusteringParameters.value) {
      clusteringParameters.value = {};
    }
    clusteringParameters.value[key] = value;
    if (typeof window !== 'undefined') {
      localStorage.setItem(CLUSTERING_PARAMS_KEY, JSON.stringify(clusteringParameters.value));
      debug('[GlobalState] Updated clustering parameter:', key, '=', value);
    }
  }

  const clearClusteringParameters = () => {
    clusteringParameters.value = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem(CLUSTERING_PARAMS_KEY);
      localStorage.removeItem(CLUSTERING_PARAMS_VERSION_KEY);
      debug('[GlobalState] Cleared clusteringParameters and version from localStorage');
    }
  }

  // Onboarding completion management
  const setOnboardingCompleted = (completed: boolean) => {
    onboardingCompleted.value = completed;
    if (typeof window !== 'undefined') {
      localStorage.setItem(ONBOARDING_COMPLETED_KEY, JSON.stringify(completed));
      debug('[GlobalState] Set onboarding completion state:', completed);
    }
  }

  const resetOnboardingState = () => {
    onboardingCompleted.value = false;
    if (typeof window !== 'undefined') {
      localStorage.removeItem(ONBOARDING_COMPLETED_KEY);
      debug('[GlobalState] Reset onboarding state');
    }
  }

  const isOnboardingCompleted = computed(() => {
    return onboardingCompleted.value && currentDataset.value !== null;
  })

  // Helper function to create a run signature for duplicate detection
  const createRunSignature = (runData: Omit<ClusterRun, 'id' | 'timestamp'> | ClusterRun) => {
    // Include n_samples from run parameters to differentiate runs with different sample sizes
    const sampleSize = runData.parameters?.n_samples || 'unknown';
    return `${runData.dataset}_${runData.treeType}_${runData.partitionMethod}_${runData.selectedK}_${runData.selectedPower}_${sampleSize}`;
  }

  // Check if a run with the same parameters already exists
  const isDuplicateRun = (runData: Omit<ClusterRun, 'id' | 'timestamp'>) => {
    const signature = createRunSignature(runData);
    return clusterRuns.value.some(existingRun => {
      const existingSignature = createRunSignature(existingRun);
      return existingSignature === signature;
    });
  }

  // Run management
  const addRun = async (runData: Omit<ClusterRun, 'id' | 'timestamp'>) => {
    const signature = createRunSignature(runData);
    const existingRun = clusterRuns.value.find(run => createRunSignature(run) === signature);

    debug('[GlobalState] Adding run with signature:', signature);
    debug('[GlobalState] Run data n_samples:', runData.parameters?.n_samples);

    // Check for duplicates
    if (existingRun) {
      debug('[GlobalState] Duplicate run detected, updating with fresh data:', signature);

      // Create a new object with fresh data from runData (existing run may have stripped clusterData from localStorage)
      const updatedRun = { ...existingRun, ...runData, id: existingRun.id, timestamp: new Date() };

      // Create a new array with the updated run at the front
      const otherRuns = clusterRuns.value.filter(run => run.id !== existingRun.id);
      clusterRuns.value = [updatedRun, ...otherRuns];

      // Save to localStorage for persistence across page refreshes
      saveRunsToLocalStorage(clusterRuns.value);

      // Save to Redis in background (non-blocking)
      const hp = getHistoryPersistence()
      if (hp.state.value.syncEnabled) {
        debug('[GlobalState] Redis is ENABLED - saving run to Redis...', { runId: updatedRun.id });
        hp.saveRun(updatedRun).then(() => {
          debug('[GlobalState] ✓ Run saved to Redis successfully:', updatedRun.id);
        }).catch(error => {
          debugWarn('[GlobalState] ✗ Failed to save updated run to Redis (continuing without Redis):', error);
        });
      } else {
        debug('[GlobalState] Redis is DISABLED - run saved to localStorage only');
      }

      return existingRun.id;
    }

    const run: ClusterRun = {
      ...runData,
      id: `run_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date()
    }

    // Create a new array
    let newRuns = [run, ...clusterRuns.value];

    // Keep only last 50 runs to prevent memory issues
    if (newRuns.length > 50) {
      newRuns = newRuns.slice(0, 50);
    }

    clusterRuns.value = newRuns;
    debug('[GlobalState] Added new run to history:', createRunSignature(runData));

    // Save to localStorage for persistence across page refreshes
    saveRunsToLocalStorage(clusterRuns.value);

    // Track large cluster data for memory management
    if (runData.clusterData) {
      trackLargeObject(runData.clusterData, 'cluster-run-data');
    }
    if (runData.treeData) {
      trackLargeObject(runData.treeData, 'cluster-tree-data');
    }

    // Save to Redis in background (non-blocking)
    const hp = getHistoryPersistence()
    if (hp.state.value.syncEnabled) {
      debug('[GlobalState] Redis is ENABLED - saving run to Redis...', { runId: run.id });
      hp.saveRun(run).then(() => {
        debug('[GlobalState] ✓ Run saved to Redis successfully:', run.id);
      }).catch(error => {
        debugWarn('[GlobalState] ✗ Failed to save run to Redis (continuing without Redis):', error);
      });
    } else {
      debug('[GlobalState] Redis is DISABLED - run saved to localStorage only');
    }

    return run.id
  }

  const setActiveRun = (runId: string | null) => {
    activeRunId.value = runId
  }

  const clearActiveRun = () => {
    activeRunId.value = null
    debug('[GlobalState] Cleared active run')
  }

  const deleteRun = async (runId: string) => {
    const runExists = clusterRuns.value.some(run => run.id === runId);
    if (runExists) {
      clusterRuns.value = clusterRuns.value.filter(run => run.id !== runId);
      if (activeRunId.value === runId) {
        activeRunId.value = null
      }

      // Save to localStorage for persistence across page refreshes
      saveRunsToLocalStorage(clusterRuns.value);

      // Delete from Redis in background
      const hp = getHistoryPersistence()
      if (hp.state.value.syncEnabled) {
        hp.deleteRun(runId).catch(error => {
          debugWarn('[GlobalState] Failed to delete run from Redis (continuing without Redis):', error);
        });
      }
    }
  }


  const getRunById = (id: string) => {
    // Synchronous method for immediate local lookups
    return clusterRuns.value.find(run => run.id === id) || null;
  }

  const getRunByIdAsync = async (id: string) => {
    // First try to find in local cache
    const localRun = clusterRuns.value.find(run => run.id === id);
    if (localRun) {
      return localRun;
    }

    // If not found locally and Redis is enabled, try Redis
    const hp = getHistoryPersistence()
    if (hp.state.value.syncEnabled) {
      try {
        const redisRun = await hp.getRun(id);
        if (redisRun) {
          // Add to local cache
          clusterRuns.value = [redisRun, ...clusterRuns.value];
          return redisRun;
        }
      } catch (error) {
        debugWarn('[GlobalState] Failed to fetch run from Redis:', error);
      }
    }

    return null;
  }

  const updateRun = (updatedRun: ClusterRun) => {
    const index = clusterRuns.value.findIndex(run => run.id === updatedRun.id)
    if (index !== -1) {
      const newRuns = [...clusterRuns.value];
      newRuns[index] = updatedRun;
      clusterRuns.value = newRuns;
      debug('[GlobalState] Updated run:', updatedRun.id)
    } else {
      debugError('[GlobalState] Run not found for update:', updatedRun.id)
    }
  }

  // Sidebar management
  const toggleSidebar = () => {
    sidebarHidden.value = !sidebarHidden.value
  }

  const setSidebarHidden = (hidden: boolean) => {
    sidebarHidden.value = hidden
  }

  // Load runs from Redis history
  const loadHistoryRuns = async (page: number = 1, limit: number = 50) => {
    const hp = getHistoryPersistence()
    if (!hp.state.value.syncEnabled) {
      return { runs: [], total: 0, hasMore: false };
    }

    try {
      const result = await hp.listRuns(page, limit);

      // Merge unique runs with local cache
      const existingIds = new Set(clusterRuns.value.map(run => run.id));
      const newRuns = result.runs.filter(run => !existingIds.has(run.id));

      if (newRuns.length > 0) {
        clusterRuns.value = [...clusterRuns.value, ...newRuns];
        debug('[GlobalState] Loaded', newRuns.length, 'runs from Redis history');
      }

      return result;
    } catch (error) {
      debugError('[GlobalState] Failed to load runs from Redis:', error);
      return { runs: [], total: 0, hasMore: false };
    }
  }

  // Sync local runs to Redis
  const syncToRedis = async () => {
    const hp = getHistoryPersistence()
    if (!hp.state.value.syncEnabled) {
      return { success: 0, failed: 0 };
    }

    debug('[GlobalState] Syncing', clusterRuns.value.length, 'runs to Redis');
    return await hp.syncRuns(clusterRuns.value);
  }

  // Initialize history persistence and load runs from Redis
  const initializeHistoryPersistence = async () => {
    try {
      const hp = getHistoryPersistence()
      await hp.initialize();
      debug('[GlobalState] History persistence initialized');

      // If Redis is enabled and connected, load runs from Redis
      if (hp.state.value.syncEnabled && hp.state.value.isConnected) {
        debug('[GlobalState] Loading runs from Redis...');
        const result = await hp.listRuns(1, 50);

        if (result.runs && result.runs.length > 0) {
          // Merge Redis runs with existing runs (localStorage runs)
          const existingIds = new Set(clusterRuns.value.map(run => run.id));
          const newRuns = result.runs.filter(run => !existingIds.has(run.id));

          if (newRuns.length > 0) {
            // Combine and sort by timestamp (newest first)
            const allRuns = [...clusterRuns.value, ...newRuns]
              .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
              .slice(0, 50); // Limit to 50 runs

            clusterRuns.value = allRuns;
            debug('[GlobalState] Loaded', newRuns.length, 'new runs from Redis, total:', allRuns.length);

            // Update localStorage with merged data
            saveRunsToLocalStorage(clusterRuns.value);
          } else {
            debug('[GlobalState] All Redis runs already in local cache');
          }
        }
      }
    } catch (error) {
      debugError('[GlobalState] Failed to initialize history persistence:', error);
    }
  }



  return {
    // State
    currentDataset: readonly(currentDataset),
    clusterRuns: readonly(clusterRuns),
    activeRunId: readonly(activeRunId),
    sampleOptions: readonly(sampleOptions),
    sidebarHidden: readonly(sidebarHidden),
    clusteringParameters: clusteringParameters,
    onboardingCompleted: readonly(onboardingCompleted),
    visualizationPreferences: readonly(visualizationPreferences),

    // Computed
    activeRun,
    recentRuns,
    hasData,
    isOnboardingCompleted,
    sampleOptionsByCategory,

    // Dataset helpers
    getSampleOption,

    // Methods
    setDataset,
    setCurrentDataset,
    clearDataset,
    clearCurrentDataset,
    setClusteringParameters,
    updateClusteringParameter,
    clearClusteringParameters,
    setOnboardingCompleted,
    resetOnboardingState,
    addRun,
    isDuplicateRun,
    setActiveRun,
    clearActiveRun,
    deleteRun,
    getRunById,
    updateRun,
    toggleSidebar,
    setSidebarHidden,
    setVisualizationPreferences: (prefs: { selectedXAxis?: string | null, selectedYAxis?: string | null, selectedPlotType?: string | null }) => {
      if (prefs.selectedXAxis !== undefined) visualizationPreferences.value.selectedXAxis = prefs.selectedXAxis
      if (prefs.selectedYAxis !== undefined) visualizationPreferences.value.selectedYAxis = prefs.selectedYAxis
      if (prefs.selectedPlotType !== undefined) visualizationPreferences.value.selectedPlotType = prefs.selectedPlotType
    },

    // Redis history integration
    loadHistoryRuns,
    syncToRedis,
    initializeHistoryPersistence,
    historyPersistence: computed(() => getHistoryPersistence()),
    getRunByIdAsync
  }
}
