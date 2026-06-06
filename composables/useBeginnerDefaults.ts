// Enhanced beginner defaults with smart parameter selection
// Provides intelligent recommendations based on user experience and data characteristics

export interface BeginnerAnswers {
  dataType: 'clear-groups' | 'overlapping-groups' | 'mixed-noise';
  groupCount: 'few' | 'many';
  priority: 'ease-of-understanding' | 'accuracy';
}

// Extended interface for the new question-based system
export interface ExtendedBeginnerAnswers {
  dataType: 'clear-groups' | 'overlapping-groups' | 'mixed-noise';
  groupCount: 'few' | 'several' | 'auto';
  priority: 'ease-of-understanding' | 'accuracy';
  dataFamiliarity: 'familiar' | 'exploring';
  clusteringMethod?: 'elbow' | 'stability' | 'manual';
  clusterCount?: number | null;
}

export interface DataCharacteristics {
  sampleType?: string;
  dataSize?: number;
  experienceLevel?: 'beginner' | 'experienced';
}

export interface ClusterDefaults {
  treeType: string;
  partitionMethod: string;
  power: number;
  k: number;
}

// Enhanced function to suggest parameters based on user answers and data characteristics
export function getDefaultParamsForBeginner(answers: BeginnerAnswers): ClusterDefaults {
  let treeType = 'DCTree';
  let partitionMethod = 'Elbow';
  let power = 2;
  let k = 3;

  // Data type specific recommendations
  if (answers.dataType === 'clear-groups') {
    // Optimize for well-separated clusters
    treeType = 'DCTree';
    partitionMethod = 'Elbow';
    power = 2; // Standard Euclidean distance
    k = 3;
  } else if (answers.dataType === 'overlapping-groups') {
    // Better for overlapping or close clusters
    treeType = 'MST'; // MST handles overlapping better
    partitionMethod = 'Silhouette'; // Better for overlapping clusters
    power = 1; // Manhattan distance can help with overlaps
    k = 5;
  } else if (answers.dataType === 'mixed-noise') {
    // Robust to noise and varying densities
    treeType = 'DCTree'; // More robust to noise
    partitionMethod = 'Gap'; // Better with noisy data
    power = 2;
    k = 4;
  }

  // Group count adjustments
  if (answers.groupCount === 'few') {
    k = Math.max(2, k - 1); // Reduce k for fewer groups
  } else if (answers.groupCount === 'many') {
    k = k + 3; // Increase k for more groups
  }

  // Priority adjustments
  if (answers.priority === 'ease-of-understanding') {
    // Prefer simpler, more interpretable methods
    treeType = 'DCTree'; // Most interpretable
    partitionMethod = 'Elbow'; // Easiest to understand
  } else if (answers.priority === 'accuracy') {
    // Prioritize methods known for accuracy
    partitionMethod = 'Silhouette'; // Generally more accurate
    // Keep more sophisticated tree types
  }

  return { treeType, partitionMethod, power, k };
}

// Enhanced quick start defaults with better general-purpose settings
export function getQuickStartDefaults(): ClusterDefaults {
  return {
    treeType: 'DCTree', // Most versatile for general use
    partitionMethod: 'Elbow', // Good balance of speed and accuracy
    power: 2, // Standard Euclidean distance
    k: 5, // Reasonable default for most datasets
  };
}

// New function for data-aware parameter recommendations
export function getSmartDefaults(characteristics: DataCharacteristics): ClusterDefaults {
  let treeType = 'DCTree';
  let partitionMethod = 'Elbow';
  let power = 2;
  let k = 5;

  // Sample-specific optimizations
  if (characteristics.sampleType) {
    const sampleType = characteristics.sampleType.toLowerCase();
    
    if (sampleType.includes('blob')) {
      // Blobs are well-separated spherical clusters
      treeType = 'DCTree';
      partitionMethod = 'Elbow';
      power = 2;
      k = 4;
    } else if (sampleType.includes('moon')) {
      // Crescents require non-spherical awareness
      treeType = 'MST';
      partitionMethod = 'Silhouette';
      power = 2;
      k = 2; // Typically 2 crescents
    } else if (sampleType.includes('circle')) {
      // Concentric circles
      treeType = 'MST';
      partitionMethod = 'Gap';
      power = 2;
      k = 2; // Usually inner and outer circle
    } else if (sampleType.includes('aniso')) {
      // Anisotropic clusters (elongated)
      treeType = 'Complete';
      partitionMethod = 'Silhouette';
      power = 2;
      k = 3;
    } else if (sampleType.includes('varied')) {
      // Varied sizes and densities
      treeType = 'DCTree';
      partitionMethod = 'Gap';
      power = 2;
      k = 4;
    }
  }

  // Data size considerations
  if (characteristics.dataSize) {
    if (characteristics.dataSize > 5000) {
      // Large datasets - prioritize efficiency
      if (treeType === 'MST') treeType = 'DCTree'; // DCTree is faster
      k = Math.min(k, 8); // Limit k for performance
    } else if (characteristics.dataSize < 100) {
      // Small datasets - can use more intensive methods
      partitionMethod = 'Silhouette'; // More reliable for small data
      k = Math.max(2, Math.min(k, Math.floor(characteristics.dataSize / 20))); // Reasonable k for small data
    }
  }

  // Experience level adjustments
  if (characteristics.experienceLevel === 'beginner') {
    // Prioritize interpretability
    treeType = 'DCTree'; // Most interpretable
    partitionMethod = 'Elbow'; // Easiest to understand
  }

  return { treeType, partitionMethod, power, k };
}

// Enhanced validation function with better fallback logic
export function validateClusterParams(
  defaults: ClusterDefaults,
  availableTreeTypes: string[],
  availablePartitionMethods: string[],
  maxK: number = 20
): ClusterDefaults {
  const validatedParams = { ...defaults };

  // Tree type validation with smart fallbacks
  if (!availableTreeTypes.includes(validatedParams.treeType)) {
    // Try common alternatives in order of preference
    const fallbackOrder = ['DCTree', 'MST', 'Complete', 'Average', 'Single'];
    const fallback = fallbackOrder.find(type => availableTreeTypes.includes(type));
    validatedParams.treeType = fallback || availableTreeTypes[0] || 'DCTree';
  }

  // Partition method validation with smart fallbacks
  if (!availablePartitionMethods.includes(validatedParams.partitionMethod)) {
    const fallbackOrder = ['Elbow', 'Silhouette', 'Gap', 'Davies-Bouldin', 'K'];
    const fallback = fallbackOrder.find(method => availablePartitionMethods.includes(method));
    validatedParams.partitionMethod = fallback || availablePartitionMethods[0] || 'Elbow';
  }

  // Enhanced k validation
  if (validatedParams.k < 2) {
    validatedParams.k = 2;
  } else if (validatedParams.k > maxK) {
    validatedParams.k = Math.min(maxK, 10); // Cap at reasonable maximum
  }

  // Power validation
  if (validatedParams.power < 0) {
    validatedParams.power = 0;
  } else if (validatedParams.power > 10) {
    validatedParams.power = 10;
  }

  return validatedParams;
}

// Helper function to get parameter descriptions for UI
export function getParameterExplanations() {
  return {
    treeTypes: {
      'DCTree': {
        name: 'Density-Based Tree',
        description: 'Builds clusters based on density, good for varied shapes and sizes',
        bestFor: 'General purpose, varied cluster shapes'
      },
      'MST': {
        name: 'Minimum Spanning Tree',
        description: 'Connects points with minimum cost, excellent for non-spherical clusters',
        bestFor: 'Elongated, curved, or irregular cluster shapes'
      },
      'Complete': {
        name: 'Complete Linkage',
        description: 'Measures maximum distance between clusters, creates compact clusters',
        bestFor: 'Spherical, well-separated clusters'
      }
    },
    partitionMethods: {
      'Elbow': {
        name: 'Elbow Method',
        description: 'Finds the "elbow" point where adding clusters provides diminishing returns',
        bestFor: 'Quick, intuitive cluster number selection'
      },
      'Silhouette': {
        name: 'Silhouette Analysis',
        description: 'Measures how well each point fits its cluster vs. neighboring clusters',
        bestFor: 'High-quality cluster validation, overlapping data'
      },
      'Gap': {
        name: 'Gap Statistic',
        description: 'Compares clustering quality against random data',
        bestFor: 'Robust selection, noisy or irregular data'
      },
      'K': {
        name: 'Manual K',
        description: 'Manually specify the exact number of clusters',
        bestFor: 'When you know the desired number of clusters'
      }
    }
  };
}

// New function for mapping question-based answers to technical parameters
export function getParamsFromQuestions(
  answers: ExtendedBeginnerAnswers,
  characteristics: DataCharacteristics = {}
): ClusterDefaults {
  let treeType = 'DCTree';
  let partitionMethod = 'Elbow';
  let power = 2;
  let k = 3;

  // Map data pattern to tree type and basic settings
  switch (answers.dataType) {
    case 'clear-groups':
      // Well-separated clusters - use density-based approach
      treeType = 'DCTree';
      partitionMethod = 'Elbow';
      power = 2; // Standard Euclidean distance
      break;
      
    case 'overlapping-groups':
      // Overlapping clusters - use tree-based method
      treeType = 'MST'; // Better for non-spherical and overlapping
      partitionMethod = 'Silhouette'; // Better validation for overlapping
      power = 1; // Manhattan can help with overlaps
      break;
      
    case 'mixed-noise':
      // Noisy data - use robust methods
      treeType = 'DCTree'; // More robust to noise
      partitionMethod = 'Gap'; // Better with noisy data
      power = 2;
      break;
  }

  // Handle clustering method selection
  if (answers.clusteringMethod) {
    switch (answers.clusteringMethod) {
      case 'elbow':
        partitionMethod = 'Elbow';
        break;
      case 'stability':
        partitionMethod = 'Silhouette'; // Use Silhouette for stability-based
        break;
      case 'manual':
        partitionMethod = 'K'; // Manual K selection
        k = answers.clusterCount || 3; // Use specified count or default to 3
        break;
    }
  }

  // Map group count to k value and method adjustments
  switch (answers.groupCount) {
    case 'few':
      // Only set k if not manually specified
      if (answers.clusteringMethod !== 'manual') {
        k = 3; // Start with few clusters
      }
      break;
      
    case 'several':
      // Only set k if not manually specified
      if (answers.clusteringMethod !== 'manual') {
        k = 6; // More clusters expected
      }
      break;
      
    case 'auto':
      // Let algorithm decide - use automatic methods
      if (partitionMethod === 'K') {
        partitionMethod = 'Elbow'; // Switch from manual to auto
      }
      k = 5; // Reasonable default for auto-detection
      break;
  }

  // Priority adjustments
  if (answers.priority === 'ease-of-understanding') {
    // Prefer interpretable methods
    treeType = 'DCTree'; // Most interpretable
    // Only override partitionMethod if it's not manually set
    if (answers.clusteringMethod !== 'manual') {
      partitionMethod = 'Elbow'; // Easiest to understand
    }
    
    // Use standard settings for simplicity
    if (power !== 2) {
      power = 2; // Standard Euclidean
    }
  } else if (answers.priority === 'accuracy') {
    // Use more sophisticated methods for accuracy
    // Only override partitionMethod if it's not manually set
    if (answers.clusteringMethod !== 'manual' && partitionMethod === 'Elbow') {
      partitionMethod = 'Silhouette'; // Generally more accurate
    }
    
    // Keep more sophisticated tree types that were selected
    // (don't override MST if it was chosen for overlapping groups)
  }

  // Data familiarity adjustments
  if (answers.dataFamiliarity === 'familiar') {
    // User knows what to expect - can use their group count preference more directly
    // Only adjust k if not manually specified
    if (answers.clusteringMethod !== 'manual') {
      if (answers.groupCount === 'few') {
        k = Math.max(2, k - 1); // Be more conservative
      } else if (answers.groupCount === 'several') {
        k = k + 1; // Trust their expectation
      }
    }
  } else if (answers.dataFamiliarity === 'exploring') {
    // User is exploring - use more exploratory methods
    // Only override partitionMethod if it's not manually set
    if (answers.clusteringMethod !== 'manual' && partitionMethod !== 'Gap') {
      // Gap statistic is good for exploration
      if (answers.priority !== 'ease-of-understanding') {
        partitionMethod = 'Gap';
      }
    }
    
    // Slightly increase k for exploration unless they specified few or manual
    if (answers.clusteringMethod !== 'manual' && answers.groupCount !== 'few') {
      k = k + 1;
    }
  }

  // Apply data characteristics adjustments (same as existing smartDefaults logic)
  const smartDefaults = getSmartDefaults({
    ...characteristics,
    experienceLevel: 'beginner'
  });

  // Blend our question-based params with smart defaults for data-specific optimization
  if (characteristics.sampleType) {
    const sampleType = characteristics.sampleType.toLowerCase();
    
    // Override with sample-specific optimizations while respecting user priorities
    // Only adjust k if not manually specified
    if (answers.clusteringMethod !== 'manual') {
      if (sampleType.includes('moon') && answers.dataType !== 'clear-groups') {
        k = 2; // Moons are typically 2 clusters
      } else if (sampleType.includes('circle') && answers.dataType !== 'clear-groups') {
        k = 2; // Circles are typically inner/outer
      } else if (sampleType.includes('blob')) {
        // Blobs work well with our clear-groups settings
        if (answers.dataType === 'clear-groups') {
          // Keep our settings as they're optimal for blobs
        }
      }
    }
  }

  // Data size considerations
  if (characteristics.dataSize) {
    if (characteristics.dataSize > 5000) {
      // Large datasets - ensure performance
      if (treeType === 'MST' && answers.priority === 'ease-of-understanding') {
        treeType = 'DCTree'; // Faster for large data when simplicity is preferred
      }
      // Only cap k if not manually specified
      if (answers.clusteringMethod !== 'manual') {
        k = Math.min(k, 8); // Cap k for performance
      }
    } else if (characteristics.dataSize < 100) {
      // Small datasets - adjust expectations
      // Only adjust k if not manually specified
      if (answers.clusteringMethod !== 'manual') {
        k = Math.max(2, Math.min(k, Math.floor(characteristics.dataSize / 15)));
      }
      
      // Silhouette is more reliable for small data
      // Only override partitionMethod if it's not manually set
      if (answers.clusteringMethod !== 'manual' && answers.priority === 'accuracy') {
        partitionMethod = 'Silhouette';
      }
    }
  }

  // Final validation and bounds checking
  // Only apply bounds to k if not manually specified, or apply more lenient bounds for manual
  if (answers.clusteringMethod === 'manual') {
    k = Math.max(2, Math.min(k, 50)); // More lenient bounds for manual selection
  } else {
    k = Math.max(2, Math.min(k, 15)); // Reasonable bounds for automatic methods
  }
  power = Math.max(0, Math.min(power, 10)); // Valid power range

  return { treeType, partitionMethod, power, k };
}

// Test function to verify manual K selection works correctly
// Test function moved to development-only mode
// Use: if (process.env.NODE_ENV === 'development') { testManualKSelection() }
export function testManualKSelection() {
  // Test moved to development environment only to prevent production bundle bloat
  if (process.env.NODE_ENV !== 'development') return null;
  
  console.log('Testing manual K selection...');
  
  // Test case 1: Manual K with ease-of-understanding priority
  const test1 = getParamsFromQuestions({
    dataType: 'clear-groups',
    groupCount: 'few',
    priority: 'ease-of-understanding',
    dataFamiliarity: 'familiar',
    clusteringMethod: 'manual',
    clusterCount: 7
  });
  
  console.log('Test 1 - Manual K=7 with ease-of-understanding:', test1);
  console.assert(test1.partitionMethod === 'K', 'Test 1 failed: partitionMethod should be K');
  console.assert(test1.k === 7, 'Test 1 failed: k should be 7');
  
  // Test case 2: Manual K with accuracy priority
  const test2 = getParamsFromQuestions({
    dataType: 'overlapping-groups',
    groupCount: 'several',
    priority: 'accuracy',
    dataFamiliarity: 'exploring',
    clusteringMethod: 'manual',
    clusterCount: 4
  });
  
  console.log('Test 2 - Manual K=4 with accuracy:', test2);
  console.assert(test2.partitionMethod === 'K', 'Test 2 failed: partitionMethod should be K');
  console.assert(test2.k === 4, 'Test 2 failed: k should be 4');
  
  // Test case 3: Automatic method should not be overridden
  const test3 = getParamsFromQuestions({
    dataType: 'clear-groups',
    groupCount: 'few',
    priority: 'ease-of-understanding',
    dataFamiliarity: 'familiar',
    clusteringMethod: 'elbow',
    clusterCount: null
  });
  
  console.log('Test 3 - Automatic elbow method:', test3);
  console.assert(test3.partitionMethod === 'Elbow', 'Test 3 failed: partitionMethod should be Elbow');
  
  console.log('Manual K selection tests completed!');
  return { test1, test2, test3 };
} 