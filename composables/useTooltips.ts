export const useTooltips = () => {
  const tooltips = {
    indexPage: {
      welcome: {
        title: 'Welcome to SHIP.ahoi - Interactive Clustering Visualization',
        description: 'SHIP.ahoi is an interactive visualization tool for the SHIP (Similarity-HIerarchy-Partition) clustering framework. This framework enables rapid exploration of diverse clustering solutions by decomposing the clustering process into three modular components, allowing you to find optimal clusterings for your data efficiently.',
        detailedInfo: '<h4>Welcome to SHIP.ahoi</h4><p><strong>SHIP.ahoi</strong> is an interactive visualization tool for the SHIP (Similarity-HIerarchy-Partition) clustering framework.</p><p><strong>Key Features:</strong></p><ul><li><strong>Fast Exploration:</strong> Generate multiple clustering solutions in milliseconds</li><li><strong>Modular Design:</strong> Mix and match different tree types, hierarchies, and partitioning methods</li><li><strong>Interactive Visualization:</strong> Explore results through dendrograms, scatter plots, and icicle plots</li><li><strong>Research-Based:</strong> Built on established clustering theory with O(n log n) optimal solutions</li></ul>',
        keyFeatures: {
          fastExploration: 'Fast Exploration: Generate multiple clustering solutions in milliseconds after initial computation',
          modularDesign: 'Modular Design: Mix and match different hierarchies and partitioning methods for the same ultrametric hierarchy in no time',
          interactiveViz: 'Interactive Visualization: Explore clustering results through dendrograms, scatter plots, and icicle plots',
          researchBased: 'Research-Based: Built on established clustering theory with O(n log n) optimal solutions'
        },
        gettingStarted: {
          step1: 'Upload Your Data or select a sample dataset',
          step2: 'Configure the three SHIP components (Tree, Hierarchy, Partition)',
          step3: 'Run the clustering and explore results interactively',
          step4: 'Fine-tune parameters to find the optimal clustering for your needs'
        },
      },
    },
    sidebar: {
      ultrametricTreeType: 'The ultrametric tree encodes pairwise distances between data points in a hierarchical structure. Different tree types capture different notions of similarity and work better for different data characteristics.',
      powerParameter: 'Controls the distance metric used in tree construction. Power=2 gives Euclidean distance, Power=1 gives Manhattan distance. Higher values emphasize larger differences between points.',
      partitionMethod: 'Determines how to select the optimal number of clusters (k) from the hierarchy. Different methods use various criteria to identify natural clustering structures in your data.',
      treeDepth: 'Controls the depth of the real tree visualization. Real trees show the full hierarchical structure up to the specified depth (1-500). Summarized trees automatically merge nodes with similar costs until around 100 nodes remain, providing a cleaner overview of the clustering structure.',
      treeVisualizationType: {
        summarized: 'Summarized Tree: Automatically reduces large trees to ~100 nodes by merging branches with similar clustering costs. Provides optimal performance and clean visualization for large datasets. Recommended for datasets with >1000 points or when you need a clear overview of major clustering patterns.',
        real: 'Real Tree: Shows the complete hierarchical structure up to your specified depth limit. Use when you need to examine detailed branching patterns or work with smaller datasets (<1000 points). Performance may decrease with very large or deep trees.'
      },
    },
    visualizations: {
      dendrogram: {
        node: 'Node represents a cluster containing [X] data points. Click to explore this subtree. Distance from parent: [Y]',
        link: 'Hierarchical relationship. Length represents distance between merged clusters.',
        description: 'Interactive dendrogram showing the hierarchical clustering structure of your data'
      },
      scatterPlot: {
        point: 'Data point [ID]. Cluster: [X]. Features: [show first 3 feature values]',
        clusterRegion: 'Cluster [X]: [N] points. Click to highlight. Double-click to zoom.',
        description: 'Scatter plot visualization showing data points colored by cluster assignment'
      },
      iciclePlot: {
        rectangle: 'Hierarchical cluster containing [N] points across [M] original clusters. Depth: [D]. Click for details.',
        description: 'Icicle plot providing an alternative view of the hierarchical clustering structure'
      },
    },
    metrics: {
      silhouette: {
        title: 'Silhouette Score',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> -1 to 1 (Higher is better)</p>
          <p><strong>What it measures:</strong> How similar points are to their own cluster vs. neighboring clusters.</p>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> ≥ 0.7: Excellent separation</div>
            <div class="range-item good"><span class="dot"></span> 0.5 - 0.7: Good cluster structure</div>
            <div class="range-item fair"><span class="dot"></span> 0.3 - 0.5: Weak structure, some overlap</div>
            <div class="range-item poor"><span class="dot"></span> < 0.3: Poor separation, consider fewer clusters</div>
          </div>
          <p><em>Less sensitive to dataset size than other metrics. Reliable for datasets of any size.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 350
      },
      daviesBouldin: {
        title: 'Davies-Bouldin Index',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> 0+ (Lower is better)</p>
          <p><strong>What it measures:</strong> Ratio of within-cluster to between-cluster distances. Measures cluster compactness vs separation.</p>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> ≤ 0.5: Very compact, well-separated clusters</div>
            <div class="range-item good"><span class="dot"></span> 0.5 - 1.0: Good cluster compactness</div>
            <div class="range-item fair"><span class="dot"></span> 1.0 - 1.5: Moderate overlap between clusters</div>
            <div class="range-item poor"><span class="dot"></span> > 1.5: High overlap, poor clustering</div>
          </div>
          <p><em>Works well for globular clusters. Less effective for irregular cluster shapes.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 350
      },
      calinskiHarabasz: {
        title: 'Calinski-Harabasz Index',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> 0+ (Higher is better)</p>
          <p><strong>What it measures:</strong> Ratio of between-cluster to within-cluster variance.</p>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> ≥ 1000: Very good (medium/large datasets)</div>
            <div class="range-item good"><span class="dot"></span> 500 - 1000: Good separation</div>
            <div class="range-item fair"><span class="dot"></span> 100 - 500: Moderate (depends on data size)</div>
            <div class="range-item poor"><span class="dot"></span> < 100: Poor (or very small dataset)</div>
          </div>
          <p><em><strong>Important:</strong> Scales with dataset size - larger datasets naturally have higher scores. Compare relative values, not absolute thresholds.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 350
      },
      ari: {
        title: 'Adjusted Rand Index (ARI)',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> -1 to 1 (Higher is better)</p>
          <p><strong>What it measures:</strong> Agreement between clustering results and ground truth labels, adjusted for chance.</p>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> ≥ 0.8: Strong agreement with true labels</div>
            <div class="range-item good"><span class="dot"></span> 0.6 - 0.8: Good clustering accuracy</div>
            <div class="range-item fair"><span class="dot"></span> 0.4 - 0.6: Moderate agreement</div>
            <div class="range-item poor"><span class="dot"></span> < 0.4: Poor match to ground truth</div>
          </div>
          <p><em><strong>Note:</strong> Only available when ground truth labels are provided. Perfect for evaluating clustering accuracy against known classifications.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 350
      },
      disco: {
        title: 'DISCO Score',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> 0 to 1 (Higher is better)</p>
          <p><strong>What it measures:</strong> Density-based cluster quality, measuring contrast between cluster density and surrounding areas.</p>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> ≥ 0.7: High density contrast</div>
            <div class="range-item good"><span class="dot"></span> 0.5 - 0.7: Good density-based separation</div>
            <div class="range-item fair"><span class="dot"></span> 0.3 - 0.5: Moderate density differences</div>
            <div class="range-item poor"><span class="dot"></span> < 0.3: Low density contrast</div>
          </div>
          <p><em>Particularly useful for detecting clusters with varying densities and irregular shapes.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 350
      },
      compactness: {
        title: 'Cluster Compactness',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> 0+ (Lower is better)</p>
          <p><strong>What it measures:</strong> Average distance from all points in the cluster to the cluster center. Indicates how tightly clustered the points are.</p>
          <div class="formula-section">
            <p><strong>Formula:</strong> Compactness = Σ distance(point, centroid) / number_of_points</p>
            <p><em>Where centroid = average position of all points in the cluster</em></p>
          </div>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> < 0.5: Very compact cluster</div>
            <div class="range-item good"><span class="dot"></span> 0.5 - 1.0: Well-formed cluster</div>
            <div class="range-item fair"><span class="dot"></span> 1.0 - 2.0: Moderately spread cluster</div>
            <div class="range-item poor"><span class="dot"></span> > 2.0: Loose, spread-out cluster</div>
          </div>
          <p><em>Lower values indicate points are closer to their cluster center, suggesting a more coherent cluster.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 380
      },
      separation: {
        title: 'Cluster Separation',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> 0+ (Higher is better)</p>
          <p><strong>What it measures:</strong> Distance from this cluster's center to the nearest other cluster's center. Indicates how well-separated clusters are.</p>
          <div class="formula-section">
            <p><strong>Formula:</strong> Separation = min(distance(centroid_i, centroid_j))</p>
            <p><em>Where j represents all other cluster centroids</em></p>
          </div>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> > 3.0: Very well separated</div>
            <div class="range-item good"><span class="dot"></span> 2.0 - 3.0: Good separation</div>
            <div class="range-item fair"><span class="dot"></span> 1.0 - 2.0: Moderate separation</div>
            <div class="range-item poor"><span class="dot"></span> < 1.0: Clusters may overlap</div>
          </div>
          <p><em>Higher values indicate clusters are farther apart, reducing the risk of misclassification between clusters.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 380
      },
      density: {
        title: 'Cluster Density',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> 0+ (Higher is better)</p>
          <p><strong>What it measures:</strong> Number of points per unit "volume" in the cluster. Calculated as cluster size divided by the compactness area.</p>
          <div class="formula-section">
            <p><strong>Formula:</strong> Density = cluster_size / (compactness² + 1)</p>
            <p><em>The "+1" prevents division by zero when compactness is very small</em></p>
          </div>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> > 10: Very dense cluster</div>
            <div class="range-item good"><span class="dot"></span> 5 - 10: Well-concentrated</div>
            <div class="range-item fair"><span class="dot"></span> 1 - 5: Moderately dense</div>
            <div class="range-item poor"><span class="dot"></span> < 1: Sparse cluster</div>
          </div>
          <p><em>Higher density indicates points are packed more tightly together, suggesting a strong clustering pattern.</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 380
      },
      cohesion: {
        title: 'Cluster Cohesion',
        content: `<div class="tooltip-metric-explanation">
          <p><strong>Range:</strong> 0+ (Higher is better)</p>
          <p><strong>What it measures:</strong> Ratio of cluster separation to compactness. Combines both measures to indicate overall cluster quality.</p>
          <div class="formula-section">
            <p><strong>Formula:</strong> Cohesion = separation / (compactness + 0.001)</p>
            <p><em>The "+0.001" prevents division by zero when compactness is extremely small</em></p>
          </div>
          <div class="metric-ranges">
            <div class="range-item excellent"><span class="dot"></span> > 5.0: Excellent cluster quality</div>
            <div class="range-item good"><span class="dot"></span> 2.0 - 5.0: Good cluster formation</div>
            <div class="range-item fair"><span class="dot"></span> 1.0 - 2.0: Acceptable clustering</div>
            <div class="range-item poor"><span class="dot"></span> < 1.0: Poor cluster definition</div>
          </div>
          <p><em>High cohesion means the cluster is both compact (low compactness value) and well-separated from others (high separation value).</em></p>
        </div>`,
        isRichContent: true,
        theme: 'dark',
        size: 'large',
        maxWidth: 380
      },
    },
    buttons: {
      runClusteringDisabled: 'Please configure all three SHIP components before running: [list missing components]',
      runClusteringEnabled: 'Execute SHIP clustering with current configuration. Approximate runtime: < 1 second for datasets up to 10,000 points.',
    },
    performance: {
      treeConstructionTime: 'Time to build the ultrametric tree. This is a one-time cost; subsequent operations are near-instantaneous.',
      hierarchyExtractionTime: 'Time to compute the k-clustering hierarchy. Typically milliseconds due to optimal O(n) algorithms.',
      partitionTime: 'Time to determine optimal k. Varies by method: Elbow/Stability are fast, Gap statistic requires more computation.',
    },
    helpIcons: {
      dataUpload: 'Supported formats: CSV with numeric features. First row should contain column headers. Missing values will be imputed with column means.',
      parameterLock: 'This parameter is locked because it depends on your data selection. Complete the previous step to unlock.',
      resetParameters: 'Reset all parameters to intelligent defaults based on your data characteristics.',
      exportResults: 'Download clustering results as CSV, including cluster assignments and computed metrics.',
      infoIcon: 'Click or hover for detailed information about this feature',
    },
  };

  return {
    tooltips,
  };
};
