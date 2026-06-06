// Simplified data configuration for beginner users
// Provides smart defaults and auto-detection for CSV preprocessing

import { ref, computed } from 'vue';

export interface BeginnerDataConfig {
  useAllNumericColumns: boolean;
  selectedColumns: string[];
  preprocessing: {
    missingValueStrategy: 'auto' | 'remove' | 'fill';
    normalization: boolean;
    categoricalHandling: 'auto' | 'include' | 'exclude';
  };
}

export interface ColumnInfo {
  name: string;
  type: 'numeric' | 'categorical' | 'mixed';
  missingCount: number;
  sampleValues: any[];
  recommended: boolean;
}

export interface SmartConfigResult {
  config: BeginnerDataConfig;
  explanation: string;
  columns: ColumnInfo[];
  warnings: string[];
}

export function useBeginnerDataConfig() {
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // Smart analysis of CSV data for beginners
  const analyzeDataForBeginners = (
    parsedData: any[][],
    headers: string[],
    hasHeaders: boolean = true
  ): SmartConfigResult => {
    const startRow = hasHeaders ? 1 : 0;
    const dataRows = parsedData.slice(startRow);
    
    // Analyze each column
    const columns: ColumnInfo[] = headers.map((header, index) => {
      const columnData = dataRows.map(row => row[index]);
      const analysis = analyzeColumn(columnData, header);
      
      return {
        name: header,
        type: analysis.type,
        missingCount: analysis.missingCount,
        sampleValues: analysis.sampleValues,
        recommended: analysis.recommended
      };
    });

    // Generate smart configuration
    const config = generateSmartConfig(columns, dataRows.length);
    
    // Create explanation
    const explanation = generateExplanation(config, columns);
    
    // Generate warnings
    const warnings = generateWarnings(columns, dataRows.length);

    return {
      config,
      explanation,
      columns,
      warnings
    };
  };

  // Analyze individual column characteristics
  const analyzeColumn = (columnData: any[], columnName: string) => {
    const validValues = columnData.filter(v => 
      v !== null && 
      v !== undefined && 
      v !== '' && 
      v !== 'null' && 
      v !== 'NULL' &&
      v !== 'NaN' && 
      v !== 'nan' &&
      v !== 'N/A' &&
      v !== 'n/a' &&
      v !== '#N/A' &&
      v !== '-' &&
      !(typeof v === 'string' && v.trim() === '') &&
      !(typeof v === 'number' && isNaN(v))
    );

    const missingCount = columnData.length - validValues.length;
    const sampleValues = validValues.slice(0, 3);
    
    // Determine data type
    let type: 'numeric' | 'categorical' | 'mixed' = 'categorical';
    let recommended = false;

    if (validValues.length > 0) {
      const numericCount = validValues.filter(v => 
        typeof v === 'number' || (!isNaN(Number(v)) && !isNaN(parseFloat(v)))
      ).length;
      
      const numericRatio = numericCount / validValues.length;
      
      if (numericRatio > 0.9) {
        type = 'numeric';
        recommended = true; // Numeric columns are usually good for clustering
      } else if (numericRatio > 0.1) {
        type = 'mixed';
        recommended = false; // Mixed types need manual review
      } else {
        type = 'categorical';
        // Categorical with few unique values might be useful as labels
        const uniqueValues = new Set(validValues.map(v => String(v).toLowerCase()));
        recommended = uniqueValues.size > 1 && uniqueValues.size <= 20;
      }
    }

    // Don't recommend columns with too many missing values
    if (missingCount / columnData.length > 0.5) {
      recommended = false;
    }

    // Don't recommend ID-like columns
    const lowerName = columnName.toLowerCase();
    if (lowerName.includes('id') || lowerName.includes('key') || lowerName.includes('index')) {
      recommended = false;
    }

    return {
      type,
      missingCount,
      sampleValues,
      recommended
    };
  };

  // Generate smart configuration based on column analysis
  const generateSmartConfig = (columns: ColumnInfo[], rowCount: number): BeginnerDataConfig => {
    const numericColumns = columns.filter(col => col.type === 'numeric' && col.recommended);
    const categoricalColumns = columns.filter(col => col.type === 'categorical' && col.recommended);
    const highMissingColumns = columns.filter(col => col.missingCount / rowCount > 0.3);

    // Default to using all recommended numeric columns
    const useAllNumericColumns = numericColumns.length >= 2;
    const selectedColumns = useAllNumericColumns 
      ? numericColumns.map(col => col.name)
      : columns.filter(col => col.recommended).map(col => col.name);

    // Smart preprocessing decisions
    const missingValueStrategy: 'auto' | 'remove' | 'fill' = 
      highMissingColumns.length > columns.length * 0.3 ? 'fill' : 'auto';

    const normalization = numericColumns.some(col => {
      // Check if values vary significantly (rough heuristic)
      const samples = col.sampleValues.filter(v => typeof v === 'number' || !isNaN(Number(v)));
      if (samples.length < 2) return false;
      const numbers = samples.map(v => Number(v));
      const min = Math.min(...numbers);
      const max = Math.max(...numbers);
      return max - min > 100 || max / min > 10; // Significant scale differences
    });

    const categoricalHandling: 'auto' | 'include' | 'exclude' = 
      categoricalColumns.length > 0 ? 'auto' : 'exclude';

    return {
      useAllNumericColumns,
      selectedColumns,
      preprocessing: {
        missingValueStrategy,
        normalization,
        categoricalHandling
      }
    };
  };

  // Generate human-readable explanation
  const generateExplanation = (config: BeginnerDataConfig, columns: ColumnInfo[]): string => {
    const numericCount = columns.filter(col => col.type === 'numeric').length;
    const categoricalCount = columns.filter(col => col.type === 'categorical').length;
    const selectedCount = config.selectedColumns.length;

    let explanation = '';

    if (config.useAllNumericColumns) {
      explanation += `We'll use all ${numericCount} numeric columns for clustering as they contain the most useful patterns. `;
    } else {
      explanation += `We've selected ${selectedCount} columns that look most suitable for finding patterns. `;
    }

    if (config.preprocessing.normalization) {
      explanation += 'We\'ll normalize the data since your columns have different scales. ';
    }

    if (config.preprocessing.missingValueStrategy === 'fill') {
      explanation += 'Missing values will be filled with appropriate defaults. ';
    } else if (config.preprocessing.missingValueStrategy === 'remove') {
      explanation += 'Rows with missing values will be removed to ensure clean analysis. ';
    }

    if (categoricalCount > 0) {
      if (config.preprocessing.categoricalHandling === 'auto') {
        explanation += 'Text columns will be converted to numbers automatically. ';
      } else if (config.preprocessing.categoricalHandling === 'exclude') {
        explanation += 'Text columns will be excluded from the analysis. ';
      }
    }

    return explanation.trim();
  };

  // Generate warnings for potential issues
  const generateWarnings = (columns: ColumnInfo[], rowCount: number): string[] => {
    const warnings: string[] = [];

    const highMissingColumns = columns.filter(col => col.missingCount / rowCount > 0.5);
    if (highMissingColumns.length > 0) {
      warnings.push(`Some columns have a lot of missing values: ${highMissingColumns.map(c => c.name).join(', ')}`);
    }

    const mixedColumns = columns.filter(col => col.type === 'mixed');
    if (mixedColumns.length > 0) {
      warnings.push(`Some columns contain mixed data types: ${mixedColumns.map(c => c.name).join(', ')}`);
    }

    const numericColumns = columns.filter(col => col.type === 'numeric' && col.recommended);
    if (numericColumns.length < 2) {
      warnings.push('You need at least 2 numeric columns for meaningful clustering analysis.');
    }

    if (rowCount < 10) {
      warnings.push('Your dataset is very small. Results may not be reliable.');
    } else if (rowCount > 100000) {
      warnings.push('Your dataset is very large. Analysis may take some time.');
    }

    return warnings;
  };

  // Convert beginner config to technical config format
  const convertToTechnicalConfig = (
    beginnerConfig: BeginnerDataConfig,
    columns: ColumnInfo[]
  ) => {
    const columnConfigs = columns.map(col => ({
      name: col.name,
      usage: beginnerConfig.selectedColumns.includes(col.name) ? 'feature' : 'ignore',
      normalize: beginnerConfig.preprocessing.normalization && col.type === 'numeric',
      dataType: col.type,
      isCategorical: col.type === 'categorical',
      missingCount: col.missingCount,
      samples: col.sampleValues
    }));

    return {
      missingValueStrategy: beginnerConfig.preprocessing.missingValueStrategy === 'auto' 
        ? 'keep' 
        : beginnerConfig.preprocessing.missingValueStrategy === 'fill' 
          ? 'fill_mean' 
          : 'remove',
      normalization: beginnerConfig.preprocessing.normalization ? 'standard' : 'none',
      categoricalEncoding: beginnerConfig.preprocessing.categoricalHandling === 'exclude' 
        ? 'drop' 
        : 'onehot',
      columns: columnConfigs
    };
  };

  // Validate beginner configuration
  const validateBeginnerConfig = (config: BeginnerDataConfig, columns: ColumnInfo[]): string[] => {
    const errors: string[] = [];

    if (config.selectedColumns.length === 0) {
      errors.push('Please select at least one column for analysis.');
    }

    const selectedNumericColumns = columns.filter(col => 
      config.selectedColumns.includes(col.name) && col.type === 'numeric'
    );

    if (selectedNumericColumns.length < 2) {
      errors.push('You need at least 2 numeric columns for clustering analysis.');
    }

    return errors;
  };

  return {
    isLoading,
    error,
    analyzeDataForBeginners,
    convertToTechnicalConfig,
    validateBeginnerConfig
  };
}