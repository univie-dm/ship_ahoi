import { useToast } from './useToast';

// API integration for backend file upload and processing
export interface FileUploadResponse {
  file_id: string
  data: any[][]
  headers: string[]
  has_headers: boolean
  row_count: number
  column_count: number
  column_info: ColumnInfo[]
  file_info: FileInfo
  missing_value_count: number
  data_types: Record<string, string>
  encoding?: string
  encoding_confidence?: number
  separator?: string
}

export interface ColumnInfo {
  name: string
  data_type: 'numeric' | 'integer' | 'categorical' | 'text' | 'mixed' | 'empty'
  non_null_count: number
  null_count: number
  unique_count: number
  sample_values: string[]
  is_categorical: boolean
  is_numeric: boolean
  unique_ratio: number
}

export interface FileInfo {
  filename: string
  size: number
  extension: string
  mime_type?: string
}

export interface DataProcessingConfig {
  missing_value_strategy: 'keep' | 'remove' | 'fill_mean' | 'fill_median' | 'fill_zero' | 'fill_mode'
  normalization: 'none' | 'standard' | 'minmax' | 'robust'
  categorical_encoding: 'none' | 'label' | 'onehot'
  feature_columns: number[]
  label_columns: number[]
  ignored_columns: number[]
  columns: ColumnConfig[]
}

export interface ColumnConfig {
  name: string
  index: number
  data_type: 'numeric' | 'integer' | 'categorical' | 'text' | 'mixed' | 'empty'
  usage: 'feature' | 'label' | 'ignore'
  normalize: boolean
  is_categorical: boolean
}

export interface ProcessedDataResponse {
  data: number[][]
  headers: string[]
  row_count: number
  column_count: number
  processing_info: {
    missing_strategy: string
    normalization: string
    categorical_encoding: string
    original_shape: number[]
    processed_shape: number[]
    removed_rows: number
    categorical_info: Record<string, any>
    normalization_info: Record<string, any>
  }
  feature_columns: number[]
  ignored_columns: number[]
}

export interface DataPreviewResponse {
  headers: string[]
  data: any[][]
  total_rows: number
  preview_rows: number
  column_info: ColumnInfo[]
  has_headers: boolean
}

export function useFileUploadAPI() {
  const { addToast } = useToast();

  const uploadFile = async (file: File): Promise<FileUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      return await $fetch(`/api/data/upload`, {
        method: 'POST',
        body: formData
      })
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'File upload failed'
      console.error('Backend upload error:', error)
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const processData = async (fileId: string, config: DataProcessingConfig): Promise<ProcessedDataResponse> => {
    try {
      // Log the request for debugging
      console.log('[processData] Request:', { file_id: fileId, processing_config: config });
      
      return await $fetch(`/api/data/process`, {
        method: 'POST',
        body: {
          file_id: fileId,
          processing_config: config
        }
      })
    } catch (error: any) {
      let errorMessage = error.data?.detail || error.message || 'Data processing failed';
      
      // Provide specific error handling for common issues
      if (error.statusCode === 422) {
        console.error('[processData] Validation error (422):', error);
        if (errorMessage.includes('column')) {
          errorMessage = 'Column configuration error. Please check your dataset column settings.';
        } else {
          errorMessage = 'Invalid data configuration. Please verify your file settings.';
        }
      } else if (error.statusCode === 404) {
        errorMessage = 'File not found. Please upload the file again.';
      }
      
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const getProcessedPreview = async (fileId: string, config: DataProcessingConfig): Promise<ProcessedDataResponse> => {
    try {
      return await $fetch(`/api/data/preview-processed`, {
        method: 'POST',
        body: {
          file_id: fileId,
          processing_config: config
        }
      })
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to get processed preview'
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const getPreview = async (fileId: string, numRows: number = 10): Promise<DataPreviewResponse> => {
    try {
      return await $fetch(`/api/data/preview`, {
        method: 'POST',
        body: {
          file_id: fileId,
          num_rows: numRows
        }
      })
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to get preview'
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const analyzeData = async (fileId: string) => {
    try {
      return await $fetch(`/api/data/analyze/${fileId}`)
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Data analysis failed'
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const deleteFile = async (fileId: string) => {
    try {
      return await $fetch(`/api/data/${fileId}`, {
        method: 'DELETE'
      })
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to delete file'
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const getSupportedFormats = async () => {
    try {
      return await $fetch(`/api/data/formats`)
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to get supported formats'
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const listFiles = async () => {
    try {
      return await $fetch(`/api/data/files`)
    } catch (error: any) {
      const errorMessage = error.data?.detail || error.message || 'Failed to list files'
      addToast(errorMessage, 'error');
      throw new Error(errorMessage)
    }
  }

  const healthCheck = async (): Promise<{ healthy: boolean, message: string, details?: any }> => {
    try {
      const data = await $fetch(`/api/health`, {
        method: 'GET',
        })
      return {
        healthy: true,
        message: 'Backend is healthy and ready',
        details: data
      }
    } catch (error: any) {
      const message = `Backend health check failed: ${error.data?.detail || error.message || 'Unknown error'}`;
      addToast(message, 'error');
      return {
        healthy: false,
        message,
        details: error
      }
    }
  }

  const testConnection = async (): Promise<{ connected: boolean, message: string }> => {
    try {
      // Try a simple request to test connectivity
      await $fetch(`/api/data/formats`, {
        method: 'GET',
        })
      
      return {
        connected: true,
        message: 'Backend connection successful'
      }
    } catch (error: any) {
      let message: string;
      
      if (error.cause && error.cause.code === 'ECONNREFUSED') {
        message = 'Cannot connect to backend server - network error';
      } else {
        message = `Connection test failed: ${error.data?.detail || error.message || 'Unknown error'}`;
      }
      
      addToast(message, 'error');
      return {
        connected: false,
        message
      }
    }
  }

  return {
    uploadFile,
    processData,
    getProcessedPreview,
    getPreview,
    analyzeData,
    deleteFile,
    getSupportedFormats,
    listFiles,
    healthCheck,
    testConnection
  }
}
