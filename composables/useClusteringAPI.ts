import { useToast } from './useToast';

// Clustering API integration with backend file handling
import { useGlobalState } from './useGlobalState'

export interface ClusteringParams {
  sample?: string
  data?: number[][]
  n_samples?: number
  n_clusters?: number
  treeType?: string
  partitioningMethod?: string
  power?: number
  random_state?: number
  isPreprocessed?: boolean
  hasHeaders?: boolean
  featureHeaders?: string[]
  dataConfig?: any
  fileId?: string
  // Tree visualization options
  treeVisualizationType?: 'summarized' | 'real'
  realTreeDepth?: number
  // Settings parameters
  umap_params?: any
  tree_target_nodes?: number
  skip_umap?: boolean
  skip_tsne?: boolean
  fast_mode?: boolean
}

export function useClusteringAPI() {
  const globalState = useGlobalState()
  const { addToast } = useToast();
  
  // Default clustering settings (hardcoded)
  const defaultSettings = {
    umap_params: {
      n_neighbors: 15,
      min_dist: 0.1,
      metric: 'euclidean'
    },
    tree_target_nodes: 50,
    real_tree_depth: 3,
    skip_umap: false,
    skip_tsne: false,
    fast_mode: false
  };

  const clusterData = async (params: ClusteringParams, colored: boolean = true) => {
    const currentDataset = globalState.currentDataset.value
    
    // Use default settings for clustering
    const currentSettings = defaultSettings
    
    // Build clustering parameters
    const clusterParams: ClusteringParams = {
      ...params,
      // Ensure tree visualization parameters are included
      treeVisualizationType: params.treeVisualizationType || 'summarized',
      realTreeDepth: params.realTreeDepth || currentSettings.real_tree_depth,
      // Add settings parameters
      umap_params: currentSettings.umap_params,
      tree_target_nodes: currentSettings.tree_target_nodes,
      skip_umap: currentSettings.skip_umap,
      skip_tsne: currentSettings.skip_tsne,
      fast_mode: currentSettings.fast_mode
    }

    // If we have a current dataset with a fileId, use it
    if (currentDataset) {
      if (currentDataset.fileId) {
        clusterParams.fileId = currentDataset.fileId;
      }
      clusterParams.isPreprocessed = true
      clusterParams.hasHeaders = currentDataset.hasHeaders || false
      if (currentDataset.headers) {
        clusterParams.featureHeaders = currentDataset.headers
      }
      if (currentDataset.groundTruthColumn !== undefined) {
        (clusterParams as any).groundTruthColumn = currentDataset.groundTruthColumn;
      }
    }
    
    // Use the regular data parameter if no fileId is available
    if (!clusterParams.fileId && currentDataset?.data) {
      clusterParams.data = currentDataset.data
      clusterParams.isPreprocessed = true
      clusterParams.hasHeaders = currentDataset.hasHeaders || false
      if (currentDataset.headers) {
        clusterParams.featureHeaders = currentDataset.headers
      }
    }

    // Choose endpoint based on color requirement
    const endpoint = colored ? '/api/cluster/colored' : '/api/cluster/regular'

    try {
      const response = await $fetch(endpoint, {
        method: 'POST',
        body: clusterParams
      })

      return response
    } catch (error: any) {
      // $fetch throws on error responses, error.data contains response body
      const errorData = error.data || {}
      
      // Check for SHiP tree generation errors
      if (errorData.detail && errorData.detail.error_code) {
        const errorCode = errorData.detail.error_code;
        if (errorCode === 'SHIP_001') {
          addToast('Tree generation failed. Please choose another tree type.', 'error');
          throw new Error('Tree generation failed. Please choose another tree type.')
        } else if (errorCode === 'SHIP_002') {
          addToast('This tree type is not compatible with your dataset. Please select a different tree type.', 'error');
          throw new Error('This tree type is not compatible with your dataset. Please select a different tree type.')
        }
      }
      
      const errorMessage = errorData.message || error.message || 'Clustering failed'
      addToast(errorMessage, 'error');
      throw new Error(errorMessage);
    }
  }

  const clusterDataColored = async (params: ClusteringParams) => {
    return clusterData(params, true)
  }

  const clusterDataRegular = async (params: ClusteringParams) => {
    return clusterData(params, false)
  }

  return {
    clusterData,
    clusterDataColored,
    clusterDataRegular
  }
}
