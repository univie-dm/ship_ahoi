import { ref, computed, nextTick, watch } from 'vue'
import type { ClusterRun } from './useGlobalState'

export const useRunComparison = (getRunById: (id: string) => ClusterRun | null) => {
  // Selection and comparison state
  const selectedRuns = ref<string[]>([])
  const comparisonMode = ref(false)
  
  // Axis selection state for scatter plot previews
  const selectedXAxis = ref('pca-0')
  const selectedYAxis = ref('pca-1')
  
  // Metrics comparison state
  const selectedMetric = ref('silhouetteScore')
  const availableMetrics = ref([
    { 
      key: 'silhouetteScore', 
      name: 'Silhouette Score', 
      color: '#3b82f6', 
      higher_better: true,
      description: 'Measures how similar objects are to their own cluster compared to other clusters'
    },
    { 
      key: 'dbIndex', 
      name: 'Davies-Bouldin Index', 
      color: '#ef4444', 
      higher_better: false,
      description: 'Measures the average similarity between clusters (lower values indicate better clustering)'
    },
    { 
      key: 'calinskiHarabasz', 
      name: 'Calinski-Harabasz Index', 
      color: '#10b981', 
      higher_better: true,
      description: 'Measures the ratio of between-cluster dispersion to within-cluster dispersion'
    },
    { 
      key: 'ari', 
      name: 'Adjusted Rand Index (ARI)', 
      color: '#f59e0b', 
      higher_better: true,
      description: 'Measures clustering similarity to ground truth labels (requires labeled data)'
    },
    { 
      key: 'discoScore', 
      name: 'DISCO Score', 
      color: '#8b5cf6', 
      higher_better: true,
      description: 'Measures cluster quality using density-connectivity relationships within hierarchical structures'
    }
  ])

  // Mobile view toggle
  const mobileViewMode = ref<'table' | 'cards'>('cards')
  
  // Reactive window width for responsive layout
  const windowWidth = ref(1024)
  
  // Computed properties
  const selectedRunsData = computed(() => {
    return selectedRuns.value
      .map(id => getRunById(id))
      .filter(run => run !== null) as ClusterRun[]
  })

  const selectedMetricInfo = computed(() => {
    return availableMetrics.value.find(m => m.key === selectedMetric.value)
  })

  const availableAxes = computed(() => {
    console.log('Computing available axes...');

    const axes = [
      { value: 'pca-0', label: 'PCA Component 1' },
      { value: 'pca-1', label: 'PCA Component 2' }
    ]
    
    console.log('Selected runs data:', selectedRunsData.value);

    // Only offer UMAP if ALL selected runs have UMAP data
    const hasUmapForAll = selectedRunsData.value.length > 0 && selectedRunsData.value.every(run => 
      run.clusterData?.dimensionality_reduction?.umap && 
      Array.isArray(run.clusterData.dimensionality_reduction.umap) &&
      run.clusterData.dimensionality_reduction.umap.length > 0
    )
    console.log('Has UMAP for all runs:', hasUmapForAll);
    
    if (hasUmapForAll) {
      axes.push(
        { value: 'umap-0', label: 'UMAP Dimension 1' },
        { value: 'umap-1', label: 'UMAP Dimension 2' }
      )
    }
    
    // Only offer t-SNE if ALL selected runs have t-SNE data
    const hasTsneForAll = selectedRunsData.value.length > 0 && selectedRunsData.value.every(run => 
      run.clusterData?.dimensionality_reduction?.tsne && 
      Array.isArray(run.clusterData.dimensionality_reduction.tsne) &&
      run.clusterData.dimensionality_reduction.tsne.length > 0
    )
    console.log('Has t-SNE for all runs:', hasTsneForAll);
    
    if (hasTsneForAll) {
      axes.push(
        { value: 'tsne-0', label: 't-SNE Dimension 1' },
        { value: 'tsne-1', label: 't-SNE Dimension 2' }
      )
    }
    
    console.log('Final available axes:', axes);
    return axes
  })

  const showMobileViewToggle = computed(() => {
    return comparisonMode.value && windowWidth.value <= 768
  })

  // Constants
  const MAX_COMPARISON_RUNS = 5

  // Methods
  const toggleRunSelection = (runId: string) => {
    const index = selectedRuns.value.indexOf(runId)
    if (index === -1) {
      // Check if we would exceed the maximum
      if (selectedRuns.value.length >= MAX_COMPARISON_RUNS) {
        // Return false to indicate the selection was rejected
        return false
      }
      selectedRuns.value.push(runId)
    } else {
      selectedRuns.value.splice(index, 1)
    }
    return true
  }

  const selectAllRuns = (runIds: string[]) => {
    // Limit to maximum runs
    const currentlySelected = selectedRuns.value
    const availableSlots = MAX_COMPARISON_RUNS - currentlySelected.length
    const newSelections = runIds.filter(id => !currentlySelected.includes(id)).slice(0, availableSlots)
    selectedRuns.value = [...currentlySelected, ...newSelections]
  }

  const deselectAllRuns = (runIds: string[]) => {
    selectedRuns.value = selectedRuns.value.filter(id => !runIds.includes(id))
  }

  const clearSelection = () => {
    selectedRuns.value = []
  }

  const startComparison = async () => {
    comparisonMode.value = true
    await nextTick()
    // Trigger chart rendering (to be handled by parent component)
    return true
  }

  const exitComparison = () => {
    comparisonMode.value = false
    selectedRuns.value = []
  }

  // Helper function to extract axis values from point data
  const getAxisValue = (point: number[], run: ClusterRun, axisKey: string): number => {
    if (axisKey.startsWith('feature-')) {
      const featureIndex = parseInt(axisKey.replace('feature-', ''))
      return point[featureIndex] || 0
    } else if (axisKey.startsWith('pca-')) {
      const pcaIndex = parseInt(axisKey.replace('pca-', ''))
      const pcaData = run.clusterData?.dimensionality_reduction?.pca
      
      // Check if PCA data is available as an array of points
      if (Array.isArray(pcaData) && pcaData.length > 0) {
        const pointIndex = run.clusterData.points.indexOf(point)
        return pcaData[pointIndex]?.[pcaIndex] || 0
      }
      // Fallback to original point data (assumes first two dimensions are PCA-transformed)
      return point[pcaIndex] || 0
    } else if (axisKey.startsWith('umap-')) {
      const umapIndex = parseInt(axisKey.replace('umap-', ''))
      const umapData = run.clusterData?.dimensionality_reduction?.umap
      
      // Only proceed if UMAP data is properly available
      if (Array.isArray(umapData) && umapData.length > 0) {
        const pointIndex = run.clusterData.points.indexOf(point)
        if (pointIndex !== -1 && umapData[pointIndex] && umapData[pointIndex][umapIndex] !== undefined) {
          return umapData[pointIndex][umapIndex]
        }
      }
      
      // If UMAP data is not available or invalid, this should not happen
      // since availableAxes only shows UMAP when all runs have it
      console.error(`UMAP data not available for run ${run.id}, axis ${axisKey}`)
      return 0
    } else if (axisKey.startsWith('tsne-')) {
      const tsneIndex = parseInt(axisKey.replace('tsne-', ''))
      const tsneData = run.clusterData?.dimensionality_reduction?.tsne
      
      // Only proceed if t-SNE data is properly available
      if (Array.isArray(tsneData) && tsneData.length > 0) {
        const pointIndex = run.clusterData.points.indexOf(point)
        if (pointIndex !== -1 && tsneData[pointIndex] && tsneData[pointIndex][tsneIndex] !== undefined) {
          return tsneData[pointIndex][tsneIndex]
        }
      }
      
      // If t-SNE data is not available or invalid, this should not happen
      // since availableAxes only shows t-SNE when all runs have it
      console.error(`t-SNE data not available for run ${run.id}, axis ${axisKey}`)
      return 0
    }
    return point[0] || 0
  }

  // Update window width for responsive behavior
  const updateWindowWidth = () => {
    if (typeof window !== 'undefined') {
      windowWidth.value = window.innerWidth
    }
  }
  
  // Initialize window width on client side
  if (typeof window !== 'undefined') {
    windowWidth.value = window.innerWidth
  }

  // Watch for changes in available axes and reset to PCA if current selection becomes unavailable
  watch(availableAxes, (newAxes, oldAxes) => {
    const currentXAvailable = newAxes.some(axis => axis.value === selectedXAxis.value)
    const currentYAvailable = newAxes.some(axis => axis.value === selectedYAxis.value)
    
    if (!currentXAvailable) {
      console.log(`Selected X axis ${selectedXAxis.value} no longer available, resetting to PCA Component 1`)
      selectedXAxis.value = 'pca-0'
    }
    
    if (!currentYAvailable) {
      console.log(`Selected Y axis ${selectedYAxis.value} no longer available, resetting to PCA Component 2`)
      selectedYAxis.value = 'pca-1'
    }
  }, { deep: true })

  return {
    // State
    selectedRuns,
    comparisonMode,
    selectedXAxis,
    selectedYAxis,
    selectedMetric,
    availableMetrics,
    mobileViewMode,
    windowWidth,
    
    // Computed
    selectedRunsData,
    selectedMetricInfo,
    availableAxes,
    showMobileViewToggle,
    
    // Constants
    MAX_COMPARISON_RUNS,
    
    // Methods
    toggleRunSelection,
    selectAllRuns,
    deselectAllRuns,
    clearSelection,
    startComparison,
    exitComparison,
    getAxisValue,
    updateWindowWidth
  }
}