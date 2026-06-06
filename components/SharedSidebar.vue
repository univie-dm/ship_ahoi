<template>
  <div v-if="isVisible" class="sidebar-container">
    <div class="shared-sidebar">
      <div class="sidebar-header">
        <div class="sidebar-title-wrapper">
          <div class="sidebar-icon">⚓</div>
          <h3 class="sidebar-title">Ship.Ahoi</h3>
        </div>
        <button class="sidebar-collapse-btn" @click="toggleSidebar" title="Toggle Sidebar (Ctrl+B)">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M9.78 4.22a.75.75 0 010 1.06L7.56 7.5l2.22 2.22a.75.75 0 11-1.06 1.06L5.94 8.06a.75.75 0 010-1.06l2.78-2.78a.75.75 0 011.06 0z"/>
          </svg>
        </button>
      </div>

      <div class="sidebar-scroll-area">
        <SidebarSection
          v-if="props.showDataSource"
          sectionId="dataSource"
          title="Current Dataset"
          description="Upload or select a dataset to begin analysis"
          variant="workflow"
          :isCollapsed="forceCollapseAll || sidebarState.sectionCollapsed.dataSource"
          @toggle="toggleSectionHandler"
          stepNumber="1"
          :statusIcon="dataSourceStatusIcon"
          :isActive="sidebarState.currentStep === 'dataSource'"
          :isCompleted="!!globalState.currentDataset.value"
        >
          <div v-if="globalState.currentDataset.value" class="current-dataset-info">
            <div class="dataset-header">
              <div class="dataset-icon">✅</div>
              <div class="dataset-info">
                <h4>{{ currentDatasetTitle }}</h4>
                <p>{{ currentDatasetType }}</p>
              </div>
            </div>
            <div class="dataset-details">
              <div v-if="globalState.currentDataset.value.pointCount" class="detail-item">
                <span class="detail-label">Points:</span>
                <span class="detail-value">{{ globalState.currentDataset.value.pointCount.toLocaleString() }}</span>
              </div>
              <div v-if="globalState.currentDataset.value.featureCount" class="detail-item">
                <span class="detail-label">Features:</span>
                <span class="detail-value">{{ globalState.currentDataset.value.featureCount }}</span>
              </div>
              <div v-if="hasFeatureNames" class="detail-item feature-names-section">
                <span class="detail-label">Feature Names:</span>
                <div class="feature-names-list">
                  <div v-if="!showAllFeatures && featureNames.length > 8" class="feature-names-preview">
                    <span v-for="(name, index) in featureNames.slice(0, 5)" :key="index" class="feature-name">{{ name }}</span>
                    <button @click="showAllFeatures = true" class="show-more-btn">
                      +{{ featureNames.length - 5 }} more...
                    </button>
                  </div>
                  <div v-else class="feature-names-full">
                    <span v-for="(name, index) in featureNames" :key="index" class="feature-name">{{ name }}</span>
                    <button v-if="featureNames.length > 8" @click="showAllFeatures = false" class="show-less-btn">
                      Show less
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <div class="dataset-actions">
              <button 
                @click="openDataUploadPage" 
                class="btn btn-secondary btn-sm btn-full"
                v-tooltip="'Navigate to data upload page to select a different dataset'"
              >
                🔄 Change Data
              </button>
            </div>
          </div>
          <div v-else class="no-dataset">
            <div class="no-dataset-content">
              <div class="no-dataset-icon">📊</div>
              <p>No dataset selected</p>
              <button 
                @click="openDataUploadPage" 
                class="btn btn-primary btn-sm btn-full"
                v-tooltip="{ key: 'helpIcons.dataUpload', theme: 'info' }"
              >
                📁 Upload or Select Data
              </button>
            </div>
          </div>
        </SidebarSection>
  
        <SidebarSection
          v-if="props.showParameters"
          sectionId="parameters"
          title="Configure Parameters"
          description="Set clustering algorithm parameters"
          variant="workflow"
          :isCollapsed="forceCollapseAll || sidebarState.sectionCollapsed.parameters"
          @toggle="toggleSectionHandler"
          stepNumber="2"
          :statusIcon="parametersStatusIcon"
          :isActive="sidebarState.currentStep === 'parameters'"
          :isDisabled="!globalState.currentDataset.value"
          lockedMessage="Upload and confirm data first"
          :isCompleted="sidebarState.parametersConfigured"
        >
          <div v-if="globalState.currentDataset.value" class="section-content-inner">
            <div class="form-group">
              <label 
                for="tree-type-select"
                v-tooltip="{ key: 'sidebar.ultrametricTreeType', trigger: 'hover', theme: 'info' }"
                class="form-label"
              >
                Tree Type
                <span class="help-icon">ℹ️</span>
              </label>
              <slot name="tree-type-select"></slot>
            </div>
            <div class="form-group">
              <label 
                for="power-select"
                v-tooltip="{ key: 'sidebar.powerParameter', trigger: 'hover', theme: 'info' }"
                class="form-label"
              >
                Power Parameter
                <span class="help-icon">ℹ️</span>
              </label>
              <slot name="power-select"></slot>
            </div>
            <div class="form-group">
              <label 
                for="partition-method-select"
                v-tooltip="{ key: 'sidebar.partitionMethod', trigger: 'hover', theme: 'info' }"
                class="form-label"
              >
                Partition Method
                <span class="help-icon">ℹ️</span>
              </label>
              <slot name="partition-method-select"></slot>
            </div>
            <div v-if="shouldShowKSlider" class="form-group">
              <label for="k-slider" class="form-label">Number of Clusters (K)</label>
              <slot name="k-slider"></slot>
            </div>
            <div class="form-group">
              <slot name="run-button"></slot>
            </div>
          </div>
        </SidebarSection>
        <!-- Visualization Options Section -->
        <SidebarSection
          v-if="props.showVisualizationOptions"
          sectionId="visualization"
          title="Visualization Options"
          description="Customize how your data is displayed"
          variant="workflow"
          :isCollapsed="forceCollapseAll || sidebarState.sectionCollapsed.visualization"
          @toggle="toggleSectionHandler"
          stepNumber="3"
          :statusIcon="visualizationStatusIcon"
          :isActive="sidebarState.currentStep === 'visualization'"
          :isDisabled="!globalState.currentDataset.value"
          lockedMessage="Upload and confirm data first"
          :isCompleted="false"
        >
          <div v-if="globalState.currentDataset.value" class="section-content-inner">
            <VisualizationTabs
              :isDendrogramVisible="props.isDendrogramVisible"
              :isIcicleVisible="props.isIcicleVisible"
              :currentTreeVisualizationType="props.currentTreeVisualizationType"
              :hasDataset="!!globalState.currentDataset.value"
              @show-outlier-tooltip="$emit('show-outlier-tooltip', $event)"
              @hide-outlier-tooltip="$emit('hide-outlier-tooltip')"
            >
              <!-- Pass through all the slots to the tabs component -->
              <template #plot-arrangement-controls>
                <slot name="plot-arrangement-controls"></slot>
              </template>
              <template #dendrogram-layout-controls>
                <slot name="dendrogram-layout-controls"></slot>
              </template>
              <template #visibility-controls>
                <slot name="visibility-controls"></slot>
              </template>
              <template #tree-type-controls>
                <slot name="tree-type-controls"></slot>
              </template>
              <template #x-axis-select>
                <slot name="x-axis-select"></slot>
              </template>
              <template #y-axis-select>
                <slot name="y-axis-select"></slot>
              </template>
              <template #color-by-select>
                <slot name="color-by-select"></slot>
              </template>
              <template #colorblind-toggle>
                <slot name="colorblind-toggle"></slot>
              </template>
              <template #split-view-toggle>
                <slot name="split-view-toggle"></slot>
              </template>
              <template #outlier-style-select>
                <slot name="outlier-style-select"></slot>
              </template>
            </VisualizationTabs>
          </div>
        </SidebarSection>
  
        <div class="sidebar-divider"></div>
        <div class="section-group-title">
          <h5>History & Tools</h5>
        </div>
  
  
        <SidebarSection
          v-if="props.showRecentRuns"
          sectionId="recentRuns"
          title="Recent Runs"
          description="View and manage your analysis history"
          variant="control"
          icon="📜"
          :isCollapsed="forceCollapseAll || sidebarState.sectionCollapsed.recentRuns"
          @toggle="toggleSectionHandler"
        >
          <template #header-actions>
            <button
              v-if="globalState.recentRuns.value.length > 0 && !sidebarState.sectionCollapsed.recentRuns"
              @click.stop="showAllRunsPage"
              class="btn btn-tertiary btn-sm"
            >
              View All
            </button>
          </template>
          
          <!-- Redis sync status for recent runs -->
          <div v-if="globalState.historyPersistence.value.state.value.syncEnabled && !sidebarState.sectionCollapsed.recentRuns" 
               class="sync-status-compact">
            <span class="sync-indicator-compact" :class="getSyncStatusClass()">
              {{ getSyncStatusText() }}
            </span>
          </div>
          
          <RecentRunsSection
            :runs="globalState.recentRuns.value"
            :activeRunId="globalState.activeRunId.value || undefined"
            @run-selected="selectRunHandler"
            @run-loaded="loadRunHandler"
            @run-deleted="deleteRunHandler"
          />
        </SidebarSection>
        <SidebarSection
          v-if="props.showPageControls"
          sectionId="pageControls"
          title="Page Controls"
          description="Page-specific settings and options"
          variant="control"
          icon="🔧"
          :isCollapsed="forceCollapseAll || sidebarState.sectionCollapsed.pageControls"
          @toggle="toggleSectionHandler"
        >
          <slot name="page-controls"></slot>
        </SidebarSection>
  
  
        <SidebarSection
          v-if="props.showDataManagement"
          sectionId="dataManagement"
          title="Data Management"
          description="Import, export, and manage your data"
          variant="control"
          icon="💾"
          :isCollapsed="forceCollapseAll || sidebarState.sectionCollapsed.dataManagement"
          @toggle="toggleSectionHandler"
        >
          <DataManagementSection 
            :hasActiveRun="!!(props.currentActiveRunId || globalState.activeRunId.value)"
            :isDendrogramVisible="props.isDendrogramVisible"
            :isScatterVisible="props.isScatterVisible"
            :isIcicleVisible="props.isIcicleVisible"
            :hasClusteringData="hasClusteringData"
            :hasTreeData="hasTreeData"
            :comparisonMode="props.comparisonMode"
            :showDownloads="props.showDownloads"
            @download-scatter="handleDownloadScatter"
            @download-tree="handleDownloadTree"
            @download-all="handleDownloadAll"
            @export-cluster-labels="exportClusterLabels"
            @export-analysis-report="exportCurrentRunReport"
            @export-detailed-report="$emit('export-detailed-report')"
            @export-visual-report="$emit('export-visual-report')"
            @export-all-visualizations="$emit('export-all-visualizations', $event)"
          />
        </SidebarSection>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useGlobalState, type ClusterRun } from '~/composables/useGlobalState';
import { useSidebarState } from '~/composables/useSidebarState';
import { useRouter } from 'vue-router';
import { useToast } from '~/composables/useToast';

// Import child components
import SidebarSection from '~/components/SidebarSection.vue';
import RecentRunsSection from '~/components/RecentRunsSection.vue';
import DataManagementSection from '~/components/DataManagementSection.vue';
import VisualizationTabs from '~/components/VisualizationTabs.vue';

interface SampleOption { label: string; value: string }


const props = defineProps({
  // Visibility of entire sections
  showDataSource: { type: Boolean, default: true },
  showParameters: { type: Boolean, default: true },
  showVisualizationOptions: { type: Boolean, default: true },
  showRecentRuns: { type: Boolean, default: true },
  showPageControls: { type: Boolean, default: true },
  showExportImport: { type: Boolean, default: true },
  showDataManagement: { type: Boolean, default: true },
  showDownloads: { type: Boolean, default: true },
  
  // Comparison mode for exports
  comparisonMode: { type: Boolean, default: false },
  
  // For data source section
  sampleOptions: { type: Array as () => SampleOption[], default: () => [
    { label: 'Blobs (default)', value: 'blobs' }, { label: 'Moons', value: 'moons' },
    { label: 'Circles', value: 'circles' }, { label: 'Anisotropic', value: 'aniso' },
    { label: 'Varied Density', value: 'varied' }, { label: 'No Structure', value: 'nostructure' },
    { label: 'Spirals', value: 'spiral' }, { label: 'Nested Circles', value: 'nested' },
    { label: 'Elongated', value: 'elongated' }, { label: 'Dense & Sparse', value: 'dense_sparse' },
    { label: 'Manifold', value: 'manifold' }
  ]},
  initialSelectedSample: { type: String, default: 'blobs' }, // Renamed from selectedSample to avoid clash
  // Visualization visibility props for export functionality
  isDendrogramVisible: { type: Boolean, default: true },
  isScatterVisible: { type: Boolean, default: true },
  isIcicleVisible: { type: Boolean, default: false },
  // Axis descriptions for dynamic labels
  xAxisDescription: { type: String, default: '' },
  yAxisDescription: { type: String, default: '' },
  // quickStats: { type: Object, default: null }, // This will now be derived from confirmed data
  forceCollapseAll: { type: Boolean, default: false },
  // Conditional K-value selection
  currentPartitionMethod: { type: String, default: 'Elbow' },
  isVisible: { type: Boolean, default: true },
  // Current tree visualization type for conditional layout controls
  currentTreeVisualizationType: { type: String, default: 'dendrogram' },
  // Current active run ID for proper export functionality
  currentActiveRunId: { type: String, default: '' },
});

const emit = defineEmits([
    'run-selected', 
    'run-loaded', 
    'sidebar-toggle',
    'parameters-updated', // Example, if parameters slot emits something
    'runs-imported-successfully',
    'runs-import-failed',
    'export-detailed-report',
    'export-visual-report',
    'export-all-visualizations',
    'auto-start-clustering',
    'show-outlier-tooltip',
    'hide-outlier-tooltip'
]);

const globalState = useGlobalState();
const sidebar = useSidebarState();
const sidebarState = sidebar.state;
const router = useRouter();
const { addToast } = useToast();

// Feature names display state
const showAllFeatures = ref(false);

// Known feature names for real-world sample datasets
const KNOWN_FEATURE_NAMES: Record<string, string[]> = {
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
};

// Feature names computed properties
const featureNames = computed(() => {
  const dataset = globalState.currentDataset.value;
  // Use known feature names for sample datasets if headers are generic
  if (dataset?.type === 'sample' && dataset.sampleName && KNOWN_FEATURE_NAMES[dataset.sampleName]) {
    return KNOWN_FEATURE_NAMES[dataset.sampleName];
  }
  return dataset?.headers || [];
});

const hasFeatureNames = computed(() => {
  return featureNames.value.length > 0;
});

// Current dataset computed from global state
const currentSelectedSample = computed(() => {
  const dataset = globalState.currentDataset.value;
  if (dataset && dataset.type === 'sample') {
    return dataset.name;
  }
  return '';
});

// Dataset display info
const currentDatasetTitle = computed(() => {
  const dataset = globalState.currentDataset.value;
  if (!dataset) return '';
  if (dataset.type === 'sample') {
    return `${dataset.name} (${dataset.n_samples?.toLocaleString() || 'N/A'} points)`;
  }
  return dataset.name || 'Uploaded Dataset';
});

const currentDatasetType = computed(() => {
  const dataset = globalState.currentDataset.value;
  if (!dataset) return '';
  return dataset.type === 'sample' ? 'Sample Dataset' : 'Uploaded File';
});

// Navigate to data upload page
const openDataUploadPage = () => {
  router.push('/data-upload');
};

// --- Computed properties for section statuses ---
const dataSourceStatusIcon = computed(() => '');
const parametersStatusIcon = computed(() => '');
const visualizationStatusIcon = computed(() => '');

// --- Computed property for conditional K slider visibility ---
const shouldShowKSlider = computed(() => {
  return props.currentPartitionMethod === 'K';
});

// --- Methods for Data Source Step ---
// Data source handling is now done on the upload page


// --- General Section Toggle ---
const toggleSectionHandler = (sectionId: keyof typeof sidebarState.sectionCollapsed) => {
  // Only prevent toggling truly disabled sections (e.g. parameters if data not uploaded)
  if ((sectionId === 'parameters' || sectionId === 'visualization') && !globalState.currentDataset.value) return;
  
  sidebar.toggleSection(sectionId);
  
  // Update current workflow step when opening workflow sections
  if (!sidebarState.sectionCollapsed[sectionId]) { // If section is being opened
    if (sectionId === 'dataSource') {
      sidebar.setStep('dataSource');
    } else if (sectionId === 'parameters') {
      sidebar.setStep('parameters');
    } else if (sectionId === 'visualization') {
      sidebar.setStep('visualization');
    }
  }
};

// --- Sidebar Toggle ---
const toggleSidebar = () => {
  globalState.toggleSidebar();
  emit('sidebar-toggle', globalState.sidebarHidden.value);
};

// --- Event Handlers for Child Component Emissions ---
const selectRunHandler = (runId: string) => {
  globalState.setActiveRun(runId);
  emit('run-selected', runId);
};
const loadRunHandler = async (runId: string) => {
  const run = await globalState.getRunByIdAsync(runId);
  if (run) {
    try {
      // Restore the dataset state based on the run's parameters
      if (run.parameters.datasetInfo && run.parameters.datasetInfo.type === 'uploaded') {
        const datasetInfoFromRun = run.parameters.datasetInfo;
        console.log('[SharedSidebar] Restoring uploaded dataset from run:', datasetInfoFromRun.name);
        
        // Debug logging for fileId sources
        console.log('[SharedSidebar] FileId sources:', {
          runParametersFileId: run.parameters.fileId,
          datasetInfoFileId: datasetInfoFromRun.fileId,
          finalFileId: run.parameters.fileId || datasetInfoFromRun.fileId
        });
        
        // Update global state with the dataset from the run
        globalState.setDataset({
          ...datasetInfoFromRun,
          // Ensure we have the fileId for potential backend operations
          fileId: run.parameters.fileId || datasetInfoFromRun.fileId
        });
        
      } else if (run.parameters.sample) {
        // Handle sample datasets
        console.log('[SharedSidebar] Restoring sample dataset from run:', run.parameters.sample);

        const sampleName = run.parameters.sample;
        // Get dimensions from global state sampleOptions instead of hardcoded mapping
        const sampleOption = globalState.sampleOptions.value.find(opt => opt.value === sampleName);
        const dimensions = sampleOption?.dimensions || 2;
        // Use known feature names for real-world datasets, fallback to generic
        const headers = KNOWN_FEATURE_NAMES[sampleName] || Array.from({ length: dimensions }, (_, i) => `Feature ${i + 1}`);
        
        globalState.setDataset({
          name: sampleName,
          type: 'sample',
          sampleName: sampleName,
          n_samples: run.parameters.n_samples || 200,
          headers,
          featureCount: dimensions
        });
      }
      
      // Set active run after dataset restoration
      globalState.setActiveRun(runId);
      
      // Auto-start clustering after dataset loading
      setTimeout(() => {
        router.push('/clustering');
      }, 100);
    } catch (error) {
      console.error('[SharedSidebar] Error restoring dataset from run:', error);
      // Still set active run even if dataset restoration fails
      globalState.setActiveRun(runId);
    }
  }
};
const deleteRunHandler = (runId: string) => {
  globalState.deleteRun(runId);
};
const showAllRunsPage = () => {
  router.push('/history');
};




// --- Export Functionality ---
const hasVisibleCharts = computed(() => {
  return props.isDendrogramVisible || props.isScatterVisible || props.isIcicleVisible;
});

const hasClusteringData = computed(() => {
  // Use currentActiveRunId prop if provided, otherwise fallback to global state
  const activeRunId = props.currentActiveRunId || globalState.activeRunId.value;
  const activeRun = globalState.getRunById(activeRunId || '');
  
  if (activeRun && activeRun.clusterData && (
    activeRun.clusterData.labels || 
    activeRun.clusterData.points ||
    activeRun.clusterData.centers
  )) {
    console.log('hasClusteringData: Using active run data', activeRunId);
    return true;
  }
  
  // Fallback: check if we have any recent runs with data
  const recentRuns = globalState.recentRuns.value;
  if (recentRuns.length > 0 && recentRuns[0].clusterData) {
    console.log('hasClusteringData: Using most recent run data');
    return true;
  }
  
  console.log('hasClusteringData: No data available');
  return false;
});

const hasTreeData = computed(() => {
  // Use currentActiveRunId prop if provided, otherwise fallback to global state
  const activeRunId = props.currentActiveRunId || globalState.activeRunId.value;
  const activeRun = globalState.getRunById(activeRunId || '');
  
  if (activeRun && activeRun.treeData) {
    console.log('hasTreeData: Using active run data', activeRunId);
    return true;
  }
  
  // Fallback: check if we have any recent runs with tree data
  const recentRuns = globalState.recentRuns.value;
  if (recentRuns.length > 0 && recentRuns[0].treeData) {
    console.log('hasTreeData: Using most recent run data');
    return true;
  }
  
  console.log('hasTreeData: No tree data available');
  return false;
});

// Helper function to export canvas with white background
const exportCanvasWithWhiteBackground = (canvas: HTMLCanvasElement, filename: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    // Create a temporary canvas for compositing
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');
    
    if (!tempCtx) {
      reject(new Error('Failed to create temporary canvas context'));
      return;
    }
    
    // Set the same dimensions as the original canvas
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    
    // Fill with white background
    tempCtx.fillStyle = 'white';
    tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);
    
    // Draw the original canvas content on top
    tempCtx.drawImage(canvas, 0, 0);
    
    // Export the composite canvas
    tempCanvas.toBlob((blob) => {
      if (blob) {
        downloadBlob(blob, filename);
        resolve();
      } else {
        reject(new Error('Failed to create PNG blob with white background'));
      }
    }, 'image/png');
  });
};

// Visualization export functionality
const exportVisualization = async (vizType: 'dendrogram' | 'scatter' | 'icicle', format: 'png' | 'svg') => {
  try {
    const activeRunId = props.currentActiveRunId || globalState.activeRunId.value || 'current';
    let selectors = [];
    let filename = '';
    
    switch (vizType) {
      case 'dendrogram':
        selectors = [
          '.visualization-panel.tree-panel svg',
          '.tree-panel svg',
          '.dendrogram svg',
          '#dendrogram svg',
          '#cluster-dendrogram svg',
          '.ClusterDendrogram svg',
          '.panel-content svg'
        ];
        filename = `dendrogram-${activeRunId}`;
        break;
      case 'scatter':
        selectors = [
          '.visualization-panel.scatter-panel svg',
          '.scatter-panel svg:not(.tree-panel svg)', 
          '.scatter-plot svg',
          '#scatter-plot svg',
          '#cluster-scatter-plot svg',
          '.CanvasScatterPlot svg',
          '.scatter-container svg',
          '.scatter-svg-container svg',
          '[class*="scatter"]:not([class*="tree"]):not([class*="icicle"]):not([class*="dendrogram"]) svg'
        ];
        filename = `scatter-plot-${activeRunId}`;
        break;
      case 'icicle':
        selectors = [
          '.visualization-panel.tree-panel svg',
          '.tree-panel svg',
          '.icicle svg',
          '#icicle svg',
          '#cluster-icicle-plot svg',
          '.IciclePlot svg',
          '.icicle-container svg'
        ];
        filename = `icicle-plot-${activeRunId}`;
        break;
    }

    console.log(`Attempting to export ${vizType} with selectors:`, selectors);
    
    let svgElement = null;
    let canvasElement = null;
    
    // First try to find SVG
    for (const selector of selectors) {
      const element = document.querySelector(selector) as SVGElement;
      if (element && element.tagName === 'svg') {
        const hasContent = element.children.length > 0 || element.textContent?.trim();
        if (hasContent) {
          // Additional validation for scatter plot to avoid picking up wrong charts
          if (vizType === 'scatter') {
            const parentClasses = element.parentElement?.className || '';
            const svgId = element.id || '';
            
            // Skip if this is clearly a tree visualization
            if (parentClasses.includes('tree') || parentClasses.includes('icicle') || 
                parentClasses.includes('dendrogram') || svgId.includes('icicle') || 
                svgId.includes('dendrogram')) {
              console.log(`Skipping SVG for ${vizType} - appears to be tree visualization:`, {selector, parentClasses, svgId});
              continue;
            }
          }
          
          svgElement = element;
          console.log(`Found ${vizType} SVG with selector: ${selector}, parent: ${element.parentElement?.className}, id: ${element.id}`);
          break;
        }
      }
    }
    
    // If no SVG found and this is scatter plot, try canvas
    if (!svgElement && vizType === 'scatter') {
      const canvasSelectors = [
        '.visualization-panel.scatter-panel canvas',
        '.scatter-panel canvas:not(.tree-panel canvas)',
        '.CanvasScatterPlot canvas',
        '.scatter-container canvas',
        '[class*="scatter"]:not([class*="tree"]):not([class*="icicle"]) canvas'
      ];
      
      console.log('Searching for scatter canvas with selectors:', canvasSelectors);
      
      for (const selector of canvasSelectors) {
        const element = document.querySelector(selector) as HTMLCanvasElement;
        if (element && element.tagName === 'CANVAS' && element.width > 0 && element.height > 0) {
          // Additional validation: make sure this is not in a tree/icicle container
          const parentClasses = element.parentElement?.className || '';
          if (!parentClasses.includes('tree') && !parentClasses.includes('icicle') && !parentClasses.includes('dendrogram')) {
            canvasElement = element;
            console.log(`Found ${vizType} Canvas with selector: ${selector}, parent classes: ${parentClasses}`);
            break;
          }
        }
      }
    }

    if (!svgElement && !canvasElement) {
      console.error(`${vizType} visualization not found. Available SVGs:`, 
        Array.from(document.querySelectorAll('svg')).filter(svg => svg.children.length > 0).map((svg, index) => ({
          index,
          parent: svg.parentElement?.className || 'no-class',
          parentTag: svg.parentElement?.tagName || 'no-parent',
          id: svg.id || 'no-id',
          hasContent: svg.children.length > 0,
          dimensions: { width: svg.getAttribute('width'), height: svg.getAttribute('height') },
          viewBox: svg.getAttribute('viewBox'),
          isTreeViz: (svg.parentElement?.className || '').includes('tree') || 
                    (svg.parentElement?.className || '').includes('icicle') || 
                    (svg.id || '').includes('icicle')
        }))
      );
      
      // Also check for canvas elements
      const canvasElements = Array.from(document.querySelectorAll('canvas')).map((canvas, index) => ({
        index,
        parent: canvas.parentElement?.className || 'no-class',
        id: canvas.id || 'no-id',
        dimensions: { width: canvas.width, height: canvas.height }
      }));
      
      if (canvasElements.length > 0) {
        console.log('Available Canvas elements:', canvasElements);
      }
      
      // Show user-friendly error
      alert(`Cannot export ${vizType}: Visualization not found or not fully loaded. Please ensure the chart is visible and try again.`);
      return;
    }

    // Final validation - make sure we didn't pick up the wrong chart
    if (svgElement && vizType === 'scatter') {
      const svgContent = svgElement.outerHTML.toLowerCase();
      if (svgContent.includes('icicle') || svgContent.includes('dendrogram') || svgContent.includes('tree')) {
        console.warn('Detected that found SVG might be wrong chart type, searching more broadly...');
        svgElement = null;
        
        // Try a broader search excluding known tree visualizations
        const allSvgs = Array.from(document.querySelectorAll('svg')).filter(svg => {
          if (svg.children.length === 0) return false;
          const parent = svg.parentElement?.className || '';
          const id = svg.id || '';
          const content = svg.outerHTML.toLowerCase();
          
          return !parent.includes('tree') && !parent.includes('icicle') && !parent.includes('dendrogram') &&
                 !id.includes('icicle') && !id.includes('dendrogram') && !id.includes('tree') &&
                 !content.includes('icicle') && !content.includes('dendrogram');
        });
        
        if (allSvgs.length > 0) {
          svgElement = allSvgs[0] as SVGElement;
          console.log('Found alternative SVG for scatter plot:', svgElement.parentElement?.className, svgElement.id);
        }
      }
    }

    // Handle Canvas export
    if (canvasElement) {
      console.log(`Exporting ${vizType} from Canvas element`);
      if (format === 'svg') {
        // Canvas cannot be exported as SVG directly, convert to PNG first then inform user
        alert('Canvas-based visualizations cannot be exported as SVG. Exporting as PNG instead.');
        await exportCanvasWithWhiteBackground(canvasElement, `${filename}.png`);
      } else {
        // Export canvas as PNG with white background
        await exportCanvasWithWhiteBackground(canvasElement, `${filename}.png`);
      }
    } 
    // Handle SVG export
    else if (svgElement) {
      console.log(`Exporting ${vizType} from SVG element:`, svgElement.parentElement?.className, svgElement.id);
      if (format === 'svg') {
        const svgData = new XMLSerializer().serializeToString(svgElement);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        downloadBlob(blob, `${filename}.svg`);
      } else {
        await exportSVGToPNG(svgElement, `${filename}.png`);
      }
    }
    
    console.log(`Successfully exported ${vizType} as ${format}`);
  } catch (error) {
    console.error(`Error exporting ${vizType}:`, error);
    alert(`Failed to export ${vizType}: ${error.message}`);
  }
};

const exportAllVisualizations = async (format: 'png' | 'svg') => {
  const visibleCharts = [];
  if (props.isDendrogramVisible) visibleCharts.push('dendrogram');
  if (props.isScatterVisible) visibleCharts.push('scatter');
  if (props.isIcicleVisible) visibleCharts.push('icicle');

  for (const chart of visibleCharts) {
    await exportVisualization(chart as any, format);
    await new Promise(resolve => setTimeout(resolve, 100));
  }
};

const exportCurrentRunReport = async () => {
  console.log('exportCurrentRunReport called');
  
  // Use currentActiveRunId prop if provided, otherwise fallback to global state
  const activeRunId = props.currentActiveRunId || globalState.activeRunId.value;
  let targetRun = globalState.getRunById(activeRunId || '');
  
  if (!targetRun) {
    const recentRuns = globalState.recentRuns.value;
    if (recentRuns.length > 0) {
      targetRun = recentRuns[0];
      console.log('Using most recent run for report export:', targetRun.id);
    }
  }
  
  if (!targetRun) {
    console.error('No run available for report export');
    return;
  }

  try {
    // Generate comprehensive HTML report
    const htmlReport = await generateHTMLAnalysisReport(targetRun);
    
    const blob = new Blob([htmlReport], { type: 'text/html' });
    const datePart = new Date().toISOString().substring(0, 10);
    downloadBlob(blob, `clustering-analysis-report-${targetRun.id}-${datePart}.html`);
  } catch (error) {
    console.error('Error generating HTML report:', error);
    // Fallback to basic JSON export on error
    const basicReport = {
      metadata: {
        exportDate: new Date().toISOString(),
        runId: targetRun.id,
        runDate: targetRun.timestamp,
        exportType: 'Individual Run Report (Fallback)'
      },
      runDetails: targetRun
    };
    const dataStr = JSON.stringify(basicReport, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const datePart = new Date().toISOString().substring(0, 10);
    downloadBlob(blob, `clustering-analysis-${targetRun.id}-${datePart}.json`);
  }
};

const generateHTMLAnalysisReport = async (targetRun: any): Promise<string> => {
  console.log('Generating comprehensive HTML analysis report for run:', targetRun.id);
  
  // Fetch additional analysis data from backend
  let datasetInsights = null;
  let clusterSummary = null;
  let featureImportance = null;
  let featureStatistics = null;
  
  try {
    // Prepare dataset for analysis
    const dataset = globalState.currentDataset.value;
    if (dataset?.data && targetRun.clusterData) {
      
      // Dataset insights
      try {
        datasetInsights = await $fetch('/api/analyze/dataset-insights', {
          method: 'POST',
          body: {
            data: dataset.data,
            headers: dataset.headers || [],
            include_correlations: true,
            include_outliers: true
          }
        });
      } catch (e) {
        console.warn('Could not fetch dataset insights:', e);
      }

      // Cluster summary
      try {
        clusterSummary = await $fetch('/api/analyze/cluster-summary', {
          method: 'POST',
          body: {
            data: dataset.data,
            labels: targetRun.clusterData.labels || targetRun.clusterData.assignments,
            include_centroids: true,
            include_metrics: true
          }
        });
      } catch (e) {
        console.warn('Could not fetch cluster summary:', e);
      }

      // Feature importance
      try {
        featureImportance = await $fetch('/api/analyze/feature-importance', {
          method: 'POST',
          body: {
            data: dataset.data,
            labels: targetRun.clusterData.labels || targetRun.clusterData.assignments,
            headers: dataset.headers || []
          }
        });
      } catch (e) {
        console.warn('Could not fetch feature importance:', e);
      }

      // Feature statistics
      try {
        featureStatistics = await $fetch('/api/analyze/feature-statistics', {
          method: 'POST',
          body: {
            data: dataset.data,
            headers: dataset.headers || []
          }
        });
      } catch (e) {
        console.warn('Could not fetch feature statistics:', e);
      }
    }
  } catch (error) {
    console.warn('Error fetching analysis data:', error);
  }

  // Extract visualizations as SVG with a small delay to ensure rendering
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Debug: Log all available SVG elements
  const allSvgs = document.querySelectorAll('svg');
  console.log(`Found ${allSvgs.length} SVG elements total`);
  allSvgs.forEach((svg, index) => {
    const parent = svg.parentElement;
    const classes = parent?.className || 'no-class';
    const id = svg.id || parent?.id || 'no-id';
    console.log(`SVG ${index}: parent classes: ${classes}, id: ${id}, content: ${svg.children.length > 0}`);
  });
  
  // Only extract the tree visualization that's currently visible
  let dendrogramSvg = '';
  let icicleSvg = '';
  
  if (props.isDendrogramVisible) {
    dendrogramSvg = extractVisualizationSVG('dendrogram');
  } else if (props.isIcicleVisible) {
    icicleSvg = extractVisualizationSVG('icicle');
  } else {
    // Fallback: try to detect which one is actually visible
    const dendrogramElement = document.querySelector('.visualization-panel.tree-panel svg, .tree-panel svg, .dendrogram svg, #dendrogram svg');
    const icicleElement = document.querySelector('.icicle svg, #icicle svg, #cluster-icicle-plot svg');
    
    if (dendrogramElement && dendrogramElement.children.length > 0) {
      dendrogramSvg = extractVisualizationSVG('dendrogram');
    } else if (icicleElement && icicleElement.children.length > 0) {
      icicleSvg = extractVisualizationSVG('icicle');
    }
  }
  
  const scatterSvg = extractVisualizationSVG('scatter');
  
  console.log('Visualization extraction results:', {
    dendrogram: !!dendrogramSvg,
    scatter: !!scatterSvg,
    icicle: !!icicleSvg
  });

  // Generate quality assessment
  const qualityAssessment = generateQualityAssessment(targetRun.metrics);
  
  // Build comprehensive HTML report
  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clustering Analysis Report - ${targetRun.id}</title>
    <style>
        ${getReportCSS()}
    </style>
</head>
<body>
    <div class="report-container">
        <header class="report-header">
            <h1>Clustering Analysis Report</h1>
            <div class="report-meta">
                <p><strong>Dataset:</strong> ${targetRun.dataset} (${targetRun.parameters.sample})</p>
                <p><strong>Algorithm:</strong> ${targetRun.treeType} / ${targetRun.partitionMethod}</p>
                <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
            </div>
        </header>

        ${generateExecutiveSummary(targetRun, qualityAssessment, clusterSummary)}
        
        ${generateDatasetAnalysisSection(datasetInsights, featureStatistics, targetRun)}
        
        ${generateClusteringResultsSection(targetRun, clusterSummary, featureImportance)}
        
        ${generateVisualizationsSection(dendrogramSvg, scatterSvg, icicleSvg)}
        
        ${generateTechnicalDetailsSection(targetRun)}
        
        <footer class="report-footer">
            <p>Generated by SHiP Clustering Application - <a href="#">Documentation</a></p>
            <p>Export Date: ${new Date().toISOString()}</p>
        </footer>
    </div>
</body>
</html>`;

  return html;
};

const extractVisualizationSVG = (vizType: 'dendrogram' | 'scatter' | 'icicle'): string => {
  try {
    let selectors = [];
    let canvasSelectors = [];
    
    if (vizType === 'dendrogram') {
      selectors = [
        '.visualization-panel.tree-panel svg',
        '.tree-panel svg',
        '.dendrogram svg',
        '#dendrogram svg',
        '.ClusterDendrogram svg',
        '.panel-content svg'
      ];
    } else if (vizType === 'scatter') {
      selectors = [
        '.visualization-panel.scatter-panel svg',
        '.scatter-panel svg:not(.tree-panel svg)', 
        '.scatter-plot svg',
        '#scatter-plot svg',
        '.CanvasScatterPlot svg',
        '.scatter-container svg',
        '.scatter-svg-container svg',
        '[class*="scatter"]:not([class*="tree"]):not([class*="icicle"]):not([class*="dendrogram"]) svg'
      ];
      canvasSelectors = [
        '.visualization-panel.scatter-panel canvas',
        '.scatter-panel canvas:not(.tree-panel canvas)',
        '.CanvasScatterPlot canvas',
        '.scatter-container canvas',
        '[class*="scatter"]:not([class*="tree"]):not([class*="icicle"]) canvas'
      ];
    } else if (vizType === 'icicle') {
      selectors = [
        '.visualization-panel.tree-panel svg',
        '.tree-panel svg',
        '.icicle svg',
        '#icicle svg',
        '.IciclePlot svg',
        '.icicle-container svg'
      ];
    }
    
    console.log(`HTML Report: Searching for ${vizType} with selectors:`, selectors);
    
    // First try to find SVG
    let svgElement = null;
    for (const selector of selectors) {
      const element = document.querySelector(selector) as SVGElement;
      if (element && element.tagName === 'svg') {
        const hasContent = element.children.length > 0 || element.textContent?.trim();
        if (hasContent) {
          // Additional validation for scatter plot to avoid picking up wrong charts
          if (vizType === 'scatter') {
            const parentClasses = element.parentElement?.className || '';
            const svgId = element.id || '';
            
            // Skip if this is clearly a tree visualization
            if (parentClasses.includes('tree') || parentClasses.includes('icicle') || 
                parentClasses.includes('dendrogram') || svgId.includes('icicle') || 
                svgId.includes('dendrogram')) {
              console.log(`HTML Report: Skipping SVG for ${vizType} - appears to be tree visualization:`, {selector, parentClasses, svgId});
              continue;
            }
          }
          
          svgElement = element;
          console.log(`HTML Report: Found ${vizType} SVG with selector: ${selector}, parent: ${element.parentElement?.className}, id: ${element.id}`);
          break;
        }
      }
    }
    
    // Final validation for scatter plot - make sure we didn't pick up the wrong chart
    if (svgElement && vizType === 'scatter') {
      const svgContent = svgElement.outerHTML.toLowerCase();
      if (svgContent.includes('icicle') || svgContent.includes('dendrogram') || svgContent.includes('tree')) {
        console.warn('HTML Report: Detected that found SVG might be wrong chart type, searching more broadly...');
        svgElement = null;
        
        // Try a broader search excluding known tree visualizations
        const allSvgs = Array.from(document.querySelectorAll('svg')).filter(svg => {
          if (svg.children.length === 0) return false;
          const parent = svg.parentElement?.className || '';
          const id = svg.id || '';
          const content = svg.outerHTML.toLowerCase();
          
          return !parent.includes('tree') && !parent.includes('icicle') && !parent.includes('dendrogram') &&
                 !id.includes('icicle') && !id.includes('dendrogram') && !id.includes('tree') &&
                 !content.includes('icicle') && !content.includes('dendrogram');
        });
        
        if (allSvgs.length > 0) {
          svgElement = allSvgs[0] as SVGElement;
          console.log('HTML Report: Found alternative SVG for scatter plot:', svgElement.parentElement?.className, svgElement.id);
        }
      }
    }
    
    // If no SVG found and this is scatter plot, try to convert canvas to SVG data
    if (!svgElement && vizType === 'scatter' && canvasSelectors.length > 0) {
      console.log('HTML Report: No SVG found for scatter, trying canvas...');
      
      for (const selector of canvasSelectors) {
        const element = document.querySelector(selector) as HTMLCanvasElement;
        if (element && element.tagName === 'CANVAS' && element.width > 0 && element.height > 0) {
          // Additional validation: make sure this is not in a tree/icicle container
          const parentClasses = element.parentElement?.className || '';
          if (!parentClasses.includes('tree') && !parentClasses.includes('icicle') && !parentClasses.includes('dendrogram')) {
            console.log(`HTML Report: Found ${vizType} Canvas with selector: ${selector}, converting to image data`);
            
            // Convert canvas to data URL and embed as image in SVG with proper sizing
            try {
              const dataURL = element.toDataURL('image/png');
              
              // Ensure minimum dimensions for better visibility in reports
              const minWidth = Math.max(element.width, 800);
              const minHeight = Math.max(element.height, 500);
              
              const svgWithImage = `
                <svg width="${minWidth}" height="${minHeight}" viewBox="0 0 ${minWidth} ${minHeight}" style="background: white; border: 1px solid #ddd;" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
                  <image x="0" y="0" width="${minWidth}" height="${minHeight}" xlink:href="${dataURL}" preserveAspectRatio="xMidYMid meet"/>
                </svg>
              `;
              console.log(`HTML Report: Successfully converted ${vizType} canvas to SVG`);
              return svgWithImage;
            } catch (error) {
              console.error(`HTML Report: Error converting canvas to SVG:`, error);
              continue;
            }
          }
        }
      }
    }
    
    if (svgElement) {
      let svgString = new XMLSerializer().serializeToString(svgElement as SVGElement);
      
      // Ensure proper dimensions and styling for better display
      const svgEl = svgElement as SVGElement;
      const currentWidth = svgEl.getAttribute('width') || svgEl.getBoundingClientRect().width || 800;
      const currentHeight = svgEl.getAttribute('height') || svgEl.getBoundingClientRect().height || 600;
      
      // Set minimum dimensions for better visibility in reports
      const minWidth = Math.max(parseInt(currentWidth.toString()), 800);
      const minHeight = Math.max(parseInt(currentHeight.toString()), 500);
      
      // Update SVG with better dimensions and styling
      svgString = svgString.replace(/<svg[^>]*>/, (match) => {
        let newSvg = match;
        
        // Update or add width and height
        if (match.includes('width=')) {
          newSvg = newSvg.replace(/width="[^"]*"/, `width="${minWidth}"`);
        } else {
          newSvg = newSvg.replace('<svg', `<svg width="${minWidth}"`);
        }
        
        if (match.includes('height=')) {
          newSvg = newSvg.replace(/height="[^"]*"/, `height="${minHeight}"`);
        } else {
          newSvg = newSvg.replace('<svg', `<svg height="${minHeight}"`);
        }
        
        // Add viewBox if not present to ensure proper scaling
        if (!match.includes('viewBox=')) {
          newSvg = newSvg.replace('<svg', `<svg viewBox="0 0 ${minWidth} ${minHeight}"`);
        }
        
        // Add background styling
        if (!match.includes('style=')) {
          newSvg = newSvg.replace('<svg', '<svg style="background: white; border: 1px solid #ddd;"');
        }
        
        return newSvg;
      });
      
      console.log(`HTML Report: Successfully extracted ${vizType} SVG`);
      return svgString;
    }
    
    console.warn(`HTML Report: No valid visualization found for ${vizType}`);
  } catch (error) {
    console.error(`HTML Report: Error extracting ${vizType}:`, error);
  }
  return '';
};

const generateQualityAssessment = (metrics: any) => {
  if (!metrics) return { overall: 'unknown', details: [] };
  
  const assessments = [];
  let overallScore = 0;
  let scoreCount = 0;
  
  if (metrics.silhouetteScore !== undefined) {
    const score = metrics.silhouetteScore;
    let quality = 'poor';
    if (score > 0.7) quality = 'excellent';
    else if (score > 0.5) quality = 'good';
    else if (score > 0.25) quality = 'fair';
    
    assessments.push({ metric: 'Silhouette Score', value: score.toFixed(3), quality });
    overallScore += score;
    scoreCount++;
  }
  
  if (metrics.dbIndex !== undefined) {
    const score = metrics.dbIndex;
    let quality = 'excellent';
    if (score > 2.0) quality = 'poor';
    else if (score > 1.5) quality = 'fair';
    else if (score > 1.0) quality = 'good';
    
    assessments.push({ metric: 'Davies-Bouldin Index', value: score.toFixed(3), quality });
    overallScore += (1 / score); // Invert since lower is better
    scoreCount++;
  }
  
  if (metrics.calinskiHarabasz !== undefined) {
    const score = metrics.calinskiHarabasz;
    let quality = 'good';
    if (score > 100) quality = 'excellent';
    else if (score > 50) quality = 'good';
    else if (score > 20) quality = 'fair';
    else quality = 'poor';
    
    assessments.push({ metric: 'Calinski-Harabasz Score', value: score.toFixed(2), quality });
    overallScore += Math.min(score / 100, 1); // Normalize to 0-1
    scoreCount++;
  }
  
  const avgScore = scoreCount > 0 ? overallScore / scoreCount : 0;
  let overall = 'unknown';
  if (avgScore > 0.7) overall = 'excellent';
  else if (avgScore > 0.5) overall = 'good';
  else if (avgScore > 0.3) overall = 'fair';
  else if (scoreCount > 0) overall = 'poor';
  
  return { overall, details: assessments };
};

const generateExecutiveSummary = (targetRun: any, qualityAssessment: any, clusterSummary: any): string => {
  const qualityClass = `quality-${qualityAssessment.overall}`;
  const clusterCount = targetRun.actualClusterCount || targetRun.selectedK;
  
  return `
    <section class="report-section">
        <h2>📊 Executive Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Key Results</h3>
                <p><strong>Number of Clusters:</strong> ${clusterCount}</p>
                <p><strong>Data Points:</strong> ${targetRun.parameters.n_samples || targetRun.parameters.datasetInfo?.pointCount || 'N/A'}</p>
                <p><strong>Features:</strong> ${targetRun.parameters.datasetInfo?.featureCount || 'N/A'}</p>
                <div class="quality-indicator ${qualityClass}">
                    <span class="quality-badge">${qualityAssessment.overall.toUpperCase()}</span>
                </div>
            </div>
            <div class="summary-card">
                <h3>Best Metrics</h3>
                ${qualityAssessment.details.slice(0, 3).map(detail => 
                    `<p><strong>${detail.metric}:</strong> ${detail.value} <span class="quality-${detail.quality}">(${detail.quality})</span></p>`
                ).join('')}
            </div>
            ${clusterSummary && clusterSummary.cluster_sizes ? `
            <div class="summary-card">
                <h3>Cluster Balance</h3>
                <p><strong>Largest Cluster:</strong> ${Math.max(...clusterSummary.cluster_sizes)} points</p>
                <p><strong>Smallest Cluster:</strong> ${Math.min(...clusterSummary.cluster_sizes)} points</p>
                <p><strong>Average Size:</strong> ${(clusterSummary.cluster_sizes.reduce((a, b) => a + b, 0) / clusterSummary.cluster_sizes.length).toFixed(1)} points</p>
            </div>
            ` : ''}
        </div>
    </section>`;
};

const generateDatasetAnalysisSection = (datasetInsights: any, featureStatistics: any, targetRun: any): string => {
  const dataset = globalState.currentDataset.value;
  
  return `
    <section class="report-section">
        <h2>📈 Dataset Analysis</h2>
        
        <div class="subsection">
            <h3>Basic Dataset Information</h3>
            <div class="insights-grid">
                <div class="insight-card">
                    <h4>Dataset Overview</h4>
                    <p><strong>Name:</strong> ${targetRun.dataset}</p>
                    <p><strong>Sample Type:</strong> ${targetRun.parameters.sample}</p>
                    <p><strong>Data Points:</strong> ${targetRun.parameters.datasetInfo?.pointCount || targetRun.parameters.n_samples || 'N/A'}</p>
                    <p><strong>Features:</strong> ${targetRun.parameters.datasetInfo?.featureCount || dataset?.featureCount || 'N/A'}</p>
                    ${targetRun.parameters.uploadedFileName ? `<p><strong>Source File:</strong> ${targetRun.parameters.uploadedFileName}</p>` : ''}
                </div>
                
                <div class="insight-card">
                    <h4>Data Configuration</h4>
                    ${dataset?.dataConfig ? `
                    <p><strong>Normalization:</strong> ${dataset.dataConfig.normalization || 'None'}</p>
                    <p><strong>Missing Value Strategy:</strong> ${dataset.dataConfig.missingValueStrategy || 'Default'}</p>
                    <p><strong>Categorical Encoding:</strong> ${dataset.dataConfig.categoricalEncoding || 'None'}</p>
                    ` : `
                    <p><strong>Normalization:</strong> ${dataset?.normalization || 'Standard'}</p>
                    <p><strong>Missing Value Strategy:</strong> ${dataset?.missingValueStrategy || 'Default'}</p>
                    `}
                    <p><strong>Dataset Type:</strong> ${dataset?.type || 'Sample'}</p>
                </div>
                
                ${dataset?.headers?.length ? `
                <div class="insight-card">
                    <h4>Feature Names</h4>
                    <div class="feature-list">
                        ${dataset.headers.map((header, idx) => `<span class="feature-tag">Feature ${idx + 1}: ${header}</span>`).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
        </div>
        
        ${featureStatistics ? `
        <div class="subsection">
            <h3>Feature Statistics</h3>
            <div class="table-container">
                <table class="statistics-table">
                    <thead>
                        <tr>
                            <th>Feature</th>
                            <th>Mean</th>
                            <th>Std Dev</th>
                            <th>Min</th>
                            <th>Max</th>
                            <th>Missing</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${featureStatistics.features ? featureStatistics.features.map(feature => `
                        <tr>
                            <td><strong>${feature.name}</strong></td>
                            <td>${feature.mean?.toFixed(3) || 'N/A'}</td>
                            <td>${feature.std?.toFixed(3) || 'N/A'}</td>
                            <td>${feature.min?.toFixed(3) || 'N/A'}</td>
                            <td>${feature.max?.toFixed(3) || 'N/A'}</td>
                            <td>${feature.missing_count || 0}</td>
                        </tr>
                        `).join('') : '<tr><td colspan="6">No feature statistics available</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        ` : ''}
        
        ${datasetInsights ? `
        <div class="subsection">
            <h3>Data Quality Insights</h3>
            <div class="insights-grid">
                ${datasetInsights.clustering_suitability ? `
                <div class="insight-card">
                    <h4>Clustering Suitability</h4>
                    <p><strong>Recommended:</strong> ${datasetInsights.clustering_suitability.recommended ? 'Yes' : 'No'}</p>
                    <p><strong>Confidence:</strong> ${(datasetInsights.clustering_suitability.confidence * 100).toFixed(1)}%</p>
                    ${datasetInsights.clustering_suitability.reasons ? `
                    <p><strong>Reasons:</strong></p>
                    <ul>
                        ${datasetInsights.clustering_suitability.reasons.map(reason => `<li>${reason}</li>`).join('')}
                    </ul>
                    ` : ''}
                </div>
                ` : ''}
                
                ${datasetInsights.basic_statistics ? `
                <div class="insight-card">
                    <h4>Advanced Statistics</h4>
                    <p><strong>Data Points:</strong> ${datasetInsights.basic_statistics.row_count}</p>
                    <p><strong>Features:</strong> ${datasetInsights.basic_statistics.column_count}</p>
                    <p><strong>Missing Values:</strong> ${datasetInsights.basic_statistics.missing_values} (${datasetInsights.basic_statistics.missing_percentage?.toFixed(1)}%)</p>
                </div>
                ` : ''}
            </div>
        </div>
        ` : ''}
    </section>`;
};

const generateClusteringResultsSection = (targetRun: any, clusterSummary: any, featureImportance: any): string => {
  // Generate basic cluster information from available data
  const clusterCount = targetRun.actualClusterCount || targetRun.selectedK;
  const hasClusterData = targetRun.clusterData && (targetRun.clusterData.labels || targetRun.clusterData.assignments);
  
  let basicClusterInfo = '';
  if (hasClusterData) {
    const labels = targetRun.clusterData.labels || targetRun.clusterData.assignments;
    const clusterCounts = {};
    labels.forEach(label => {
      clusterCounts[label] = (clusterCounts[label] || 0) + 1;
    });
    
    basicClusterInfo = `
    <div class="subsection">
        <h3>Cluster Distribution</h3>
        <div class="cluster-distribution-grid">
            ${Object.entries(clusterCounts).map(([clusterId, count]) => `
            <div class="cluster-info-card">
                <h4>Cluster ${clusterId}</h4>
                <div class="cluster-size">${count}</div>
                <p>${((count / labels.length) * 100).toFixed(1)}% of data</p>
            </div>
            `).join('')}
        </div>
    </div>`;
  }
  
  return `
    <section class="report-section">
        <h2>🎯 Clustering Results</h2>
        
        <div class="subsection">
            <h3>Performance Analysis</h3>
            <div class="insights-grid">
                <div class="insight-card">
                    <h4>Algorithm Performance</h4>
                    ${targetRun.metrics ? `
                    <p><strong>Overall Quality:</strong> ${getQualityDescription(targetRun.metrics)}</p>
                    <p><strong>Best Performing Metric:</strong> ${getBestMetric(targetRun.metrics)}</p>
                    <p><strong>Cluster Separation:</strong> ${getSeparationQuality(targetRun.metrics)}</p>
                    ` : '<p>No performance metrics available</p>'}
                </div>
                
                <div class="insight-card">
                    <h4>Algorithm Details</h4>
                    <p><strong>Clusters Found:</strong> ${clusterCount}</p>
                    <p><strong>Partition Method:</strong> ${targetRun.partitionMethod}</p>
                    <p><strong>Tree Algorithm:</strong> ${targetRun.treeType}</p>
                    <p><strong>Power Parameter:</strong> ${targetRun.selectedPower}</p>
                </div>
            </div>
        </div>
        
        ${basicClusterInfo}
        
        ${clusterSummary ? `
        <div class="subsection">
            <h3>Detailed Cluster Summary</h3>
            <div class="table-container">
                <table class="cluster-table">
                    <thead>
                        <tr>
                            <th>Cluster</th>
                            <th>Size</th>
                            <th>Percentage</th>
                            <th>Compactness</th>
                            <th>Separation</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${clusterSummary.clusters ? clusterSummary.clusters.map((cluster, idx) => `
                        <tr>
                            <td><strong>Cluster ${idx}</strong></td>
                            <td>${cluster.size || 'N/A'}</td>
                            <td>${cluster.percentage ? cluster.percentage.toFixed(1) + '%' : 'N/A'}</td>
                            <td>${cluster.compactness ? cluster.compactness.toFixed(3) : 'N/A'}</td>
                            <td>${cluster.separation ? cluster.separation.toFixed(3) : 'N/A'}</td>
                        </tr>
                        `).join('') : '<tr><td colspan="5">No detailed cluster summary available</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        ` : ''}
        
        <div class="subsection">
            <h3>Evaluation Metrics</h3>
            <div class="metrics-grid">
                ${targetRun.metrics?.silhouetteScore ? `
                <div class="metric-card">
                    <h4>Silhouette Score</h4>
                    <div class="metric-value">${targetRun.metrics.silhouetteScore.toFixed(3)}</div>
                    <p>Measures how similar points are to their own cluster vs. other clusters. Range: [-1, 1], higher is better.</p>
                </div>
                ` : ''}
                
                ${targetRun.metrics?.dbIndex ? `
                <div class="metric-card">
                    <h4>Davies-Bouldin Index</h4>
                    <div class="metric-value">${targetRun.metrics.dbIndex.toFixed(3)}</div>
                    <p>Measures cluster separation and compactness. Lower values indicate better clustering.</p>
                </div>
                ` : ''}
                
                ${targetRun.metrics?.calinskiHarabasz ? `
                <div class="metric-card">
                    <h4>Calinski-Harabasz Score</h4>
                    <div class="metric-value">${targetRun.metrics.calinskiHarabasz.toFixed(2)}</div>
                    <p>Ratio of between-cluster to within-cluster dispersion. Higher values indicate better clustering.</p>
                </div>
                ` : ''}
                
                ${targetRun.metrics?.ari ? `
                <div class="metric-card">
                    <h4>Adjusted Rand Index</h4>
                    <div class="metric-value">${targetRun.metrics.ari.toFixed(3)}</div>
                    <p>Measures agreement between clustering and ground truth. Range: [-1, 1], higher is better.</p>
                </div>
                ` : ''}
                
                ${targetRun.metrics?.discoScore ? `
                <div class="metric-card">
                    <h4>DISCO Score</h4>
                    <div class="metric-value">${targetRun.metrics.discoScore.toFixed(3)}</div>
                    <p>Density-based clustering validation metric. Higher values indicate better clustering quality.</p>
                </div>
                ` : ''}
            </div>
        </div>
        
        ${featureImportance ? `
        <div class="subsection">
            <h3>Feature Importance</h3>
            <div class="importance-container">
                ${featureImportance.feature_scores ? featureImportance.feature_scores.map((feature, idx) => `
                <div class="importance-bar">
                    <span class="feature-name">${feature.name || `Feature ${idx}`}</span>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: ${(feature.importance * 100).toFixed(1)}%"></div>
                        <span class="importance-value">${feature.importance.toFixed(3)}</span>
                    </div>
                </div>
                `).join('') : '<p>No feature importance data available</p>'}
            </div>
        </div>
        ` : ''}
    </section>`;
};

const generateVisualizationsSection = (dendrogramSvg: string, scatterSvg: string, icicleSvg: string): string => {
  const vizAvailable = { scatter: !!scatterSvg, dendrogram: !!dendrogramSvg, icicle: !!icicleSvg };
  const hasTreeVisualization = vizAvailable.dendrogram || vizAvailable.icicle;
  const hasAnyVisualization = vizAvailable.scatter || hasTreeVisualization;
  
  const generatePlaceholder = (type: string) => `
    <div class="visualization-container">
        <h3>${type}</h3>
        <div class="viz-placeholder">
            <div class="placeholder-icon">📊</div>
            <p>Visualization not captured</p>
            <small>Check that ${type.toLowerCase()} is visible when generating report</small>
        </div>
    </div>
  `;
  
  return `
    <section class="report-section">
        <h2>📊 Visualizations</h2>
        <div class="visualizations-grid-large">
            ${vizAvailable.scatter ? `
            <div class="visualization-container-large">
                <h3>Scatter Plot</h3>
                <div class="svg-container-large">
                    ${scatterSvg}
                </div>
            </div>
            ` : generatePlaceholder('Scatter Plot')}
            
            ${vizAvailable.dendrogram ? `
            <div class="visualization-container-large">
                <h3>Dendrogram</h3>
                <div class="svg-container-large">
                    ${dendrogramSvg}
                </div>
            </div>
            ` : ''}
            
            ${vizAvailable.icicle ? `
            <div class="visualization-container-large">
                <h3>Icicle Plot</h3>
                <div class="svg-container-large">
                    ${icicleSvg}
                </div>
            </div>
            ` : ''}
            
            ${!hasTreeVisualization ? generatePlaceholder('Tree Visualization') : ''}
        </div>
        
        ${!hasAnyVisualization ? `
        <div class="no-visualizations">
            <div class="insight-card">
                <h4>⚠️ Visualization Capture Failed</h4>
                <p>None of the clustering visualizations could be captured. To fix this:</p>
                <ol>
                    <li>Make sure all charts are fully loaded and visible</li>
                    <li>Wait for animations to complete</li>
                    <li>Try switching between chart types to ensure they're rendered</li>
                    <li>Generate the report again</li>
                </ol>
            </div>
        </div>
        ` : ''}
    </section>`;
};

const generateTechnicalDetailsSection = (targetRun: any): string => {
  const dataset = globalState.currentDataset.value;
  const clusterCount = targetRun.actualClusterCount || targetRun.selectedK;
  
  return `
    <section class="report-section">
        <h2>⚙️ Technical Details</h2>
        <div class="technical-grid">
            <div class="technical-card">
                <h3>Algorithm Settings</h3>
                <p><strong>Tree Algorithm:</strong> ${targetRun.treeType}</p>
                <p><strong>Partition Method:</strong> ${targetRun.partitionMethod}</p>
                <p><strong>Power Parameter:</strong> ${targetRun.selectedPower}</p>
                <p><strong>Final Clusters:</strong> ${clusterCount}</p>
            </div>
            
            <div class="technical-card">
                <h3>Data Processing</h3>
                ${dataset?.dataConfig ? `
                <p><strong>Normalization:</strong> ${dataset.dataConfig.normalization || 'Standard'}</p>
                <p><strong>Missing Values:</strong> ${dataset.dataConfig.missingValueStrategy || 'Default handling'}</p>
                <p><strong>Encoding:</strong> ${dataset.dataConfig.categoricalEncoding || 'None'}</p>
                ` : `
                <p><strong>Data Type:</strong> ${dataset?.type || 'Sample dataset'}</p>
                <p><strong>Processing:</strong> Standard normalization</p>
                <p><strong>Format:</strong> Numerical data</p>
                `}
            </div>
            
            <div class="technical-card">
                <h3>Export Metadata</h3>
                <p><strong>Run ID:</strong> <code>${targetRun.id}</code></p>
                <p><strong>Analysis Date:</strong> ${new Date(targetRun.timestamp).toLocaleDateString()}</p>
                <p><strong>Report Generated:</strong> ${new Date().toLocaleString()}</p>
                <p><strong>Report Version:</strong> Enhanced HTML v1.0</p>
            </div>
        </div>
    </section>`;
};

const getReportCSS = (): string => {
  return `
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #333;
        background-color: #f8f9fa;
    }
    
    .report-container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: white;
        box-shadow: 0 0 20px rgba(0,0,0,0.1);
    }
    
    .report-header {
        text-align: center;
        padding: 30px 0;
        border-bottom: 3px solid #007bff;
        margin-bottom: 30px;
    }
    
    .report-header h1 {
        color: #007bff;
        font-size: 2.5em;
        margin-bottom: 20px;
    }
    
    .report-meta {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 10px;
        font-size: 1.1em;
    }
    
    .report-section {
        margin-bottom: 40px;
        padding: 20px;
        border-radius: 8px;
        background: #fff;
        border: 1px solid #e9ecef;
    }
    
    .report-section h2 {
        color: #495057;
        border-bottom: 2px solid #007bff;
        padding-bottom: 10px;
        margin-bottom: 20px;
        font-size: 1.8em;
    }
    
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
    }
    
    .summary-card {
        padding: 20px;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        background: #f8f9fa;
    }
    
    .summary-card h3 {
        color: #495057;
        margin-bottom: 15px;
        border-bottom: 1px solid #dee2e6;
        padding-bottom: 5px;
    }
    
    .quality-indicator {
        text-align: center;
        margin: 15px 0;
    }
    
    .quality-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        color: white;
        font-size: 0.9em;
    }
    
    .quality-excellent .quality-badge {
        background-color: #28a745;
    }
    
    .quality-good .quality-badge {
        background-color: #17a2b8;
    }
    
    .quality-fair .quality-badge {
        background-color: #ffc107;
        color: #212529;
    }
    
    .quality-poor .quality-badge {
        background-color: #dc3545;
    }
    
    .quality-unknown .quality-badge {
        background-color: #6c757d;
    }
    
    .quality-excellent { color: #28a745; font-weight: bold; }
    .quality-good { color: #17a2b8; font-weight: bold; }
    .quality-fair { color: #ffc107; font-weight: bold; }
    .quality-poor { color: #dc3545; font-weight: bold; }
    
    .subsection {
        margin-bottom: 30px;
    }
    
    .subsection h3 {
        color: #495057;
        margin-bottom: 15px;
        font-size: 1.4em;
    }
    
    .table-container {
        overflow-x: auto;
        margin: 15px 0;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
    }
    
    th, td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #dee2e6;
    }
    
    th {
        background-color: #f8f9fa;
        font-weight: 600;
        color: #495057;
    }
    
    tr:hover {
        background-color: #f8f9fa;
    }
    
    .insights-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
    }
    
    .insight-card {
        padding: 20px;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        background: white;
    }
    
    .insight-card h4 {
        color: #007bff;
        margin-bottom: 10px;
    }
    
    .feature-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
    }
    
    .feature-tag {
        display: inline-block;
        background: #e9ecef;
        color: #495057;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 500;
        border: 1px solid #dee2e6;
    }
    
    .cluster-distribution-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }
    
    .cluster-info-card {
        text-align: center;
        padding: 20px;
        border: 2px solid #007bff;
        border-radius: 12px;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .cluster-info-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,123,255,0.2);
    }
    
    .cluster-info-card h4 {
        color: #007bff;
        margin-bottom: 10px;
        font-size: 1.1em;
    }
    
    .cluster-size {
        font-size: 2.2em;
        font-weight: bold;
        color: #495057;
        margin: 10px 0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    .cluster-info-card p {
        color: #6c757d;
        font-weight: 500;
        margin: 0;
    }
    
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    
    .metric-card {
        padding: 20px;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        background: white;
        text-align: center;
    }
    
    .metric-card h4 {
        color: #495057;
        margin-bottom: 10px;
    }
    
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #007bff;
        margin: 10px 0;
    }
    
    .metric-card p {
        font-size: 0.9em;
        color: #6c757d;
        margin-top: 10px;
    }
    
    .importance-container {
        margin: 20px 0;
    }
    
    .importance-bar {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        padding: 8px;
        border-radius: 4px;
        background: #f8f9fa;
    }
    
    .feature-name {
        min-width: 120px;
        font-weight: 500;
        margin-right: 15px;
    }
    
    .bar-container {
        flex: 1;
        position: relative;
        height: 20px;
        background: #e9ecef;
        border-radius: 10px;
        overflow: hidden;
    }
    
    .bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #007bff, #0056b3);
        border-radius: 10px;
        transition: width 0.3s ease;
    }
    
    .importance-value {
        position: absolute;
        right: 8px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.8em;
        font-weight: bold;
        color: #495057;
    }
    
    .visualizations-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
        gap: 30px;
        margin: 20px 0;
    }
    
    .visualizations-grid-large {
        display: grid;
        grid-template-columns: 1fr;
        gap: 40px;
        margin: 30px 0;
    }
    
    .visualization-container {
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 20px;
        background: white;
    }
    
    .visualization-container-large {
        border: 1px solid #dee2e6;
        border-radius: 12px;
        padding: 30px;
        background: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .visualization-container h3,
    .visualization-container-large h3 {
        text-align: center;
        margin-bottom: 15px;
        color: #495057;
        font-size: 1.3em;
        font-weight: 600;
    }
    
    .svg-container {
        text-align: center;
        overflow: hidden;
    }
    
    .svg-container-large {
        text-align: center;
        overflow: visible;
        min-height: 600px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .svg-container svg {
        max-width: 100%;
        height: auto;
        border: 1px solid #e9ecef;
        border-radius: 4px;
    }
    
    .svg-container-large svg {
        width: 100% !important;
        min-width: 800px;
        max-width: 1200px;
        min-height: 500px;
        height: auto !important;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        background: white;
    }
    
    .viz-placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 200px;
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        border: 2px dashed #dee2e6;
        border-radius: 8px;
        text-align: center;
        color: #6c757d;
    }
    
    .placeholder-icon {
        font-size: 3em;
        margin-bottom: 10px;
        opacity: 0.5;
    }
    
    .viz-placeholder p {
        font-weight: 600;
        margin: 5px 0;
        color: #495057;
    }
    
    .viz-placeholder small {
        font-style: italic;
        color: #6c757d;
    }
    
    code {
        background: #f8f9fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        border: 1px solid #e9ecef;
    }
    
    .technical-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
    }
    
    .technical-card {
        padding: 20px;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        background: #f8f9fa;
    }
    
    .technical-card h3 {
        color: #495057;
        margin-bottom: 15px;
        border-bottom: 1px solid #dee2e6;
        padding-bottom: 5px;
    }
    
    .report-footer {
        margin-top: 40px;
        padding: 20px;
        border-top: 2px solid #dee2e6;
        text-align: center;
        color: #6c757d;
        font-size: 0.9em;
    }
    
    .report-footer a {
        color: #007bff;
        text-decoration: none;
    }
    
    .report-footer a:hover {
        text-decoration: underline;
    }
    
    @media print {
        body {
            background: white;
        }
        
        .report-container {
            box-shadow: none;
            margin: 0;
            padding: 10px;
        }
        
        .report-section {
            break-inside: avoid;
            page-break-inside: avoid;
        }
        
        .visualization-container {
            break-inside: avoid;
        }
    }
    
    @media (max-width: 768px) {
        .report-container {
            padding: 10px;
        }
        
        .report-header h1 {
            font-size: 2em;
        }
        
        .report-meta {
            grid-template-columns: 1fr;
        }
        
        .summary-grid,
        .metrics-grid,
        .technical-grid {
            grid-template-columns: 1fr;
        }
        
        .visualizations-grid,
        .visualizations-grid-large {
            grid-template-columns: 1fr;
        }
        
        .svg-container-large svg {
            min-width: 300px;
            min-height: 300px;
        }
    }
  `;
};

// Helper functions for clustering analysis
const getQualityDescription = (metrics: any): string => {
  if (!metrics) return 'Unknown';
  
  let qualityScores = 0;
  let scoreCount = 0;
  
  if (metrics.silhouetteScore !== undefined) {
    qualityScores += metrics.silhouetteScore > 0.5 ? 1 : metrics.silhouetteScore > 0.25 ? 0.5 : 0;
    scoreCount++;
  }
  
  if (metrics.dbIndex !== undefined) {
    qualityScores += metrics.dbIndex < 1.0 ? 1 : metrics.dbIndex < 1.5 ? 0.5 : 0;
    scoreCount++;
  }
  
  if (metrics.calinskiHarabasz !== undefined) {
    qualityScores += metrics.calinskiHarabasz > 100 ? 1 : metrics.calinskiHarabasz > 50 ? 0.5 : 0;
    scoreCount++;
  }
  
  const avgQuality = scoreCount > 0 ? qualityScores / scoreCount : 0;
  
  if (avgQuality > 0.7) return 'Excellent clustering quality';
  if (avgQuality > 0.5) return 'Good clustering quality';
  if (avgQuality > 0.3) return 'Fair clustering quality';
  return 'Poor clustering quality';
};

const getBestMetric = (metrics: any): string => {
  if (!metrics) return 'None available';
  
  const scores = [];
  
  if (metrics.silhouetteScore !== undefined) {
    scores.push({ name: 'Silhouette Score', value: metrics.silhouetteScore, quality: metrics.silhouetteScore > 0.5 ? 'good' : 'fair' });
  }
  
  if (metrics.calinskiHarabasz !== undefined) {
    scores.push({ name: 'Calinski-Harabasz', value: metrics.calinskiHarabasz, quality: metrics.calinskiHarabasz > 100 ? 'good' : 'fair' });
  }
  
  if (scores.length === 0) return 'No metrics available';
  
  const bestScore = scores.reduce((best, current) => 
    current.quality === 'good' && best.quality !== 'good' ? current : best
  );
  
  return `${bestScore.name} (${bestScore.quality})`;
};

const getSeparationQuality = (metrics: any): string => {
  if (!metrics) return 'Unknown';
  
  if (metrics.dbIndex !== undefined) {
    if (metrics.dbIndex < 1.0) return 'Excellent separation';
    if (metrics.dbIndex < 1.5) return 'Good separation';
    if (metrics.dbIndex < 2.0) return 'Fair separation';
    return 'Poor separation';
  }
  
  if (metrics.silhouetteScore !== undefined) {
    if (metrics.silhouetteScore > 0.7) return 'Excellent separation';
    if (metrics.silhouetteScore > 0.5) return 'Good separation';
    if (metrics.silhouetteScore > 0.25) return 'Fair separation';
    return 'Poor separation';
  }
  
  return 'Cannot determine separation quality';
};

const exportClusterLabels = () => {
  console.log('exportClusterLabels called');
  
  // Use currentActiveRunId prop if provided, otherwise fallback to global state
  const activeRunId = props.currentActiveRunId || globalState.activeRunId.value;
  let targetRun = globalState.getRunById(activeRunId || '');
  
  if (!targetRun || !targetRun.clusterData) {
    const recentRuns = globalState.recentRuns.value;
    if (recentRuns.length > 0 && recentRuns[0].clusterData) {
      targetRun = recentRuns[0];
      console.log('Using most recent run for export:', targetRun.id);
    }
  }
  
  if (!targetRun) {
    console.error('No run available for export');
    return;
  }
  
  if (!targetRun.clusterData) {
    console.error('No cluster data available');
    return;
  }

  if (!targetRun.clusterData.labels && !targetRun.clusterData.points) {
    console.error('No cluster labels or points to export');
    return;
  }

  const labels = targetRun.clusterData.labels;
  const points = targetRun.clusterData.points;
  
  // Create CSV content with headers
  let csvContent = 'Point_Index,X,Y';
  
  // Add feature headers if available - use actual feature names when possible
  if (points && points.length > 0) {
    const numFeatures = points[0].length;
    const dataset = globalState.currentDataset.value;
    const featureHeaders = dataset?.headers || [];
    
    for (let i = 2; i < numFeatures; i++) {
      // Use actual feature name if available, otherwise fall back to generic name
      const featureName = featureHeaders[i] || `Feature_${i + 1}`;
      csvContent += `,${featureName}`;
    }
  }
  csvContent += ',Cluster_Label\n';
  
  // Add data rows
  labels.forEach((label, index) => {
    let row = `${index}`;
    
    // Add point coordinates if available
    if (points && points[index]) {
      points[index].forEach(coord => {
        row += `,${coord}`;
      });
    }
    
    row += `,${label}`;
    csvContent += row + '\n';
  });

  const blob = new Blob([csvContent], { type: 'text/csv' });
  const datePart = new Date().toISOString().substring(0, 10);
  downloadBlob(blob, `cluster-labels-${targetRun.id}-${datePart}.csv`);
};



const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  URL.revokeObjectURL(url);
  a.remove();
};

// Helper function to convert SVG to PNG
const exportSVGToPNG = async (svgElement: SVGElement, filename: string) => {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const svgData = new XMLSerializer().serializeToString(svgElement);
  const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);

  const img = new Image();
  
  return new Promise<void>((resolve, reject) => {
    img.onload = () => {
      // Get dimensions from SVG attributes or use defaults
      const svgRect = svgElement.getBoundingClientRect();
      canvas.width = svgRect.width || 800;
      canvas.height = svgRect.height || 600;
      
      // Set white background
      ctx.fillStyle = 'white';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      ctx.drawImage(img, 0, 0);
      
      canvas.toBlob((blob) => {
        if (blob) {
          downloadBlob(blob, filename);
          resolve();
        } else {
          reject(new Error('Failed to create PNG blob'));
        }
      }, 'image/png');
      
      URL.revokeObjectURL(url);
    };
    
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load SVG as image'));
    };
    
    img.src = url;
  });
};

// --- Download Handlers for DataManagementSection ---
const handleDownloadScatter = async (format: 'png' | 'svg') => {
  await exportVisualization('scatter', format);
};

const handleDownloadTree = async (format: 'png' | 'svg') => {
  // Determine which tree visualization is active
  if (props.isDendrogramVisible) {
    await exportVisualization('dendrogram', format);
  } else if (props.isIcicleVisible) {
    await exportVisualization('icicle', format);
  } else {
    // Try dendrogram first, then icicle if visibility props are not accurate
    console.log('No tree visualization marked as visible, trying dendrogram first...');
    try {
      await exportVisualization('dendrogram', format);
    } catch (error) {
      console.log('Dendrogram failed, trying icicle...');
      await exportVisualization('icicle', format);
    }
  }
};

const handleDownloadAll = async (format: 'png' | 'svg') => {
  await exportAllVisualizations(format);
};


// --- Keyboard Shortcut for Sidebar Toggle ---
let keydownHandler: ((event: KeyboardEvent) => void) | null = null;
onMounted(() => {
  if (typeof window !== 'undefined') {
    keydownHandler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
        event.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener('keydown', keydownHandler);
  }
});
onUnmounted(() => {
  if (typeof window !== 'undefined' && keydownHandler) {
    window.removeEventListener('keydown', keydownHandler);
  }
});

// Watch for changes in parameters slot that might indicate configuration
// This is a placeholder; actual logic depends on how parameters slot communicates completion.
// For example, the component in the 'parameters' slot could emit an event.
// watch(() => props.parameters, (newVal) => {
//   if (dataSuccessfullyUploaded.value && newVal /* some condition indicating configured */) {
//     parametersConfiguredPlaceholder.value = true;
//   }
// }, { deep: true });

// Redis sync status helpers
const getSyncStatusClass = (): string => {
  const state = globalState.historyPersistence.value.state.value
  if (state.isLoading) return 'sync-loading'
  if (!state.isConnected) return 'sync-disconnected'
  if (state.error) return 'sync-error'
  return 'sync-connected'
}

const getSyncStatusText = (): string => {
  const state = globalState.historyPersistence.value.state.value
  if (state.isLoading) return 'Syncing...'
  if (!state.isConnected) return 'Offline'
  if (state.error) return 'Error'
  return 'Synced'
}

</script>

<style scoped>
:root {
  /* Notion-like Minimalist Color Palette - Fixed and Consistent */
  --bg-primary: #ffffff;
  --bg-secondary: #f7f6f3;
  --bg-tertiary: #f1f1ef;
  --bg-hover: #f7f6f3;
  --bg-active: #e9e9e7;
  --bg-disabled: #f7f6f3;
  
  --border-primary: #e9e9e7;
  --border-secondary: #d9d9d7;
  --border-hover: #d9d9d7;
  
  --text-primary: #37352f;
  --text-secondary: #787774;
  --text-tertiary: #9b9a97;
  --text-disabled: #c7c7c5;
  --text-muted: #9b9a97;
  
  --accent-primary: #2383e2;
  --accent-hover: #1a73cc;
  --accent-subtle: #e3f2fd;
  
  --success-primary: #0f7b0f;
  --success-subtle: #e8f5e8;
  --error-primary: #e03e3e;
  --error-subtle: #ffeaea;
  --warning-primary: #f59e0b;
  --warning-subtle: #fef3c7;
}

/* Compact sync status styles */
.sync-status-compact {
  padding: 0.25rem 0.5rem;
  margin-bottom: 0.5rem;
  background: var(--bg-secondary);
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  font-size: 0.75rem;
  text-align: center;
}

.sync-indicator-compact {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.sync-indicator-compact::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

.sync-indicator-compact.sync-connected::before {
  background: var(--success-primary);
}

.sync-indicator-compact.sync-loading::before {
  background: var(--warning-primary);
  animation: pulse 1.5s ease-in-out infinite;
}

.sync-indicator-compact.sync-disconnected::before {
  background: var(--error-primary);
}

.sync-indicator-compact.sync-error::before {
  background: var(--error-primary);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Main container for the sidebar content */
.sidebar-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg-primary);
}

.shared-sidebar-reworked {
  padding: 16px;
  flex-grow: 1;
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* Header section of the sidebar */
.sidebar-header-reworked {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: 16px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-primary);
}

.sidebar-title-reworked h3 {
  margin: 0 0 4px 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.015em;
}

.sidebar-title-reworked p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 400;
  line-height: 1.4;
}

.sidebar-collapse-btn {
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  color: var(--text-tertiary);
  border-radius: 6px;
  padding: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  min-width: 28px;
  min-height: 28px;
}

.sidebar-collapse-btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
  color: var(--text-secondary);
}

.sidebar-collapse-btn:active {
  background: var(--bg-active);
}

/* Other sections title */
.other-sections-title-reworked {
  margin: 24px 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-primary);
}

.other-sections-title-reworked h5 {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-family: 'Inter', system-ui, sans-serif;
}

/* View All Button */
.view-all-btn-reworked {
  background: var(--bg-primary);
  color: var(--accent-primary);
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  text-decoration: none;
  font-family: 'Inter', system-ui, sans-serif;
}

.view-all-btn-reworked:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
  color: var(--accent-hover);
}

.view-all-btn-reworked:active {
  background: var(--bg-active);
  transform: translateY(1px);
}

/* Section content wrapper */
.section-content {
  padding: 0;
  background: transparent;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
  font-family: 'Inter', system-ui, sans-serif;
}

.form-description {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 8px;
  line-height: 1.4;
  font-style: italic;
}

/* Tooltip label styling */
.tooltip-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: help;
  transition: color 0.15s ease;
}

.tooltip-label:hover {
  color: var(--accent-primary);
}

.help-icon {
  font-size: 0.75rem;
  opacity: 0.7;
  transition: opacity 0.15s ease;
}

.tooltip-label:hover .help-icon {
  opacity: 1;
}

.form-group:last-child {
  margin-bottom: 0;
}

/* Export functionality styles moved to DataManagementSection */

/* Responsive Design for Shared Sidebar */

/* Small laptops and large tablets */
@media (max-width: 1200px) {
  .shared-sidebar-reworked {
    padding: 16px;
  }
  
  .sidebar-title-reworked h3 {
    font-size: 1rem;
  }
  
  .sidebar-title-reworked p {
    font-size: 0.8rem;
  }
  
  .form-group {
    margin-bottom: 14px;
  }
  
  .export-grid {
    grid-template-columns: 1fr;
    gap: 6px;
  }
}

/* Medium tablets */
@media (max-width: 1024px) {
  .shared-sidebar-reworked {
    padding: 14px;
  }
  
  .sidebar-header-reworked {
    padding-bottom: 14px;
    margin-bottom: 16px;
  }
  
  .form-group {
    margin-bottom: 12px;
  }
  
  .form-group label {
    font-size: 0.7rem;
    margin-bottom: 4px;
  }
}

/* Small tablets and mobile landscape */
@media (max-width: 768px) {
  .shared-sidebar-reworked {
    padding: 12px;
  }
  
  .sidebar-header-reworked {
    flex-direction: row;
    align-items: center;
    padding-bottom: 12px;
    margin-bottom: 16px;
  }
  
  .sidebar-title-reworked {
    flex: 1;
  }
  
  .sidebar-title-reworked h3 {
    font-size: 0.95rem;
    line-height: 1.2;
  }
  
  .sidebar-title-reworked p {
    font-size: 0.75rem;
    line-height: 1.3;
  }
  
  .sidebar-collapse-btn {
    padding: 8px;
    min-width: 36px;
    min-height: 36px;
    border-radius: 6px;
  }
  
  .other-sections-title-reworked {
    margin: 20px 0 10px 0;
    padding-bottom: 6px;
  }
  
  .other-sections-title-reworked h5 {
    font-size: 0.65rem;
  }
  
  .form-group {
    margin-bottom: 14px;
  }
  
  .form-group label {
    font-size: 0.75rem;
    margin-bottom: 6px;
    font-weight: 600;
  }
  
  .export-section {
    margin-bottom: 16px;
    padding: 12px;
  }
  
  .export-grid {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
  
  .export-viz-btn {
    padding: 8px 6px;
    font-size: 0.7rem;
    min-height: 36px;
  }
  
  .export-all-btn,
  .export-report-btn {
    padding: 10px 8px;
    font-size: 0.75rem;
    min-height: 40px;
  }
  
  .view-all-btn-reworked {
    padding: 6px 10px;
    font-size: 0.7rem;
    min-height: 32px;
  }
}

/* Mobile portrait */
@media (max-width: 480px) {
  .shared-sidebar-reworked {
    padding: 10px;
  }
  
  .sidebar-header-reworked {
    padding-bottom: 10px;
    margin-bottom: 14px;
  }
  
  .sidebar-title-reworked h3 {
    font-size: 0.9rem;
  }
  
  .sidebar-title-reworked p {
    font-size: 0.7rem;
    display: none; /* Hide description on very small screens */
  }
  
  
  .sidebar-collapse-btn {
    padding: 6px;
    min-width: 32px;
    min-height: 32px;
  }
  
  .sidebar-collapse-btn svg {
    width: 14px;
    height: 14px;
  }
  
  .other-sections-title-reworked {
    margin: 16px 0 8px 0;
    padding-bottom: 4px;
  }
  
  .form-group {
    margin-bottom: 12px;
  }
  
  .form-group label {
    font-size: 0.7rem;
    margin-bottom: 4px;
  }
  
  .export-section {
    padding: 10px;
    margin-bottom: 14px;
  }
  
  .export-subsection-title {
    font-size: 0.65rem;
    margin-bottom: 8px;
  }
  
  .export-grid {
    grid-template-columns: 1fr;
    gap: 6px;
  }
  
  .export-viz-btn {
    padding: 10px 8px;
    font-size: 0.7rem;
    min-height: 40px;
  }
  
  .export-all-btn,
  .export-report-btn {
    padding: 12px 10px;
    font-size: 0.75rem;
    min-height: 44px;
  }
  
  .view-all-btn-reworked {
    padding: 8px 12px;
    font-size: 0.7rem;
    min-height: 36px;
  }
}

/* Very small screens */
@media (max-width: 320px) {
  .shared-sidebar-reworked {
    padding: 8px;
  }
  
  .sidebar-title-reworked h3 {
    font-size: 0.85rem;
  }
  
  .sidebar-collapse-btn {
    padding: 4px;
    min-width: 28px;
    min-height: 28px;
  }
  
  .form-group {
    margin-bottom: 10px;
  }
  
  .form-group label {
    font-size: 0.65rem;
  }
  
  .export-section {
    padding: 8px;
  }
  
  .export-viz-btn {
    padding: 8px 6px;
    font-size: 0.65rem;
    min-height: 36px;
  }
  
  .export-all-btn,
  .export-report-btn {
    padding: 10px 8px;
    font-size: 0.7rem;
    min-height: 40px;
  }
}

/* Touch device optimizations */
@media (hover: none) and (pointer: coarse) {
  .sidebar-collapse-btn {
    min-width: 44px;
    min-height: 44px;
    padding: 10px;
  }
  
  .export-viz-btn {
    min-height: 44px;
    padding: 12px 8px;
  }
  
  .export-all-btn,
  .export-report-btn {
    min-height: 48px;
    padding: 14px 12px;
  }
  
  .view-all-btn-reworked {
    min-height: 44px;
    padding: 12px 16px;
  }
  
  /* Larger touch targets for form elements */
  .form-group label {
    padding: 4px 0;
    margin-bottom: 8px;
  }
}

/* Landscape orientation on mobile */
@media (max-width: 768px) and (orientation: landscape) {
  .shared-sidebar-reworked {
    padding: 8px 12px;
  }
  
  .sidebar-header-reworked {
    padding-bottom: 8px;
    margin-bottom: 12px;
  }
  
  .sidebar-title-reworked p {
    display: none; /* Hide description in landscape */
  }
  
  .form-group {
    margin-bottom: 10px;
  }
  
  .other-sections-title-reworked {
    margin: 14px 0 8px 0;
  }
  
  .export-section {
    padding: 8px;
    margin-bottom: 12px;
  }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .sidebar-collapse-btn,
  .view-all-btn-reworked,
  .export-viz-btn,
  .export-all-btn,
  .export-report-btn {
    transition: none;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .sidebar-collapse-btn {
    border-width: 2px;
  }
  
  .export-viz-btn,
  .export-all-btn,
  .export-report-btn,
  .view-all-btn-reworked {
    border-width: 2px;
  }
  
  .export-section {
    border-width: 2px;
  }
}



/* Dataset display styles */
.current-dataset-info {
  padding: 16px;
}

.dataset-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.dataset-icon {
  font-size: 1.5rem;
}

.dataset-info h4 {
  margin: 0 0 4px 0;
  color: #2d3748;
  font-size: 0.95rem;
  font-weight: 600;
}

.dataset-info p {
  margin: 0;
  color: #718096;
  font-size: 0.8rem;
}

.dataset-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f7fafc;
  border-radius: 6px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.detail-label {
  font-weight: 600;
  color: #4a5568;
}

.detail-value {
  color: #2d3748;
}

/* Feature names section styles */
.feature-names-section {
  flex-direction: column;
  align-items: flex-start;
}

.feature-names-list {
  width: 100%;
  margin-top: 4px;
}

.feature-names-preview,
.feature-names-full {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.feature-name {
  background: #e2e8f0;
  color: #4a5568;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.show-more-btn,
.show-less-btn {
  background: none;
  border: none;
  color: #4299e1;
  font-size: 0.75rem;
  cursor: pointer;
  padding: 2px 4px;
  text-decoration: underline;
  transition: color 0.15s ease;
}

.show-more-btn:hover,
.show-less-btn:hover {
  color: #3182ce;
}

.dataset-actions {
  display: flex;
  gap: 8px;
}

.change-data-btn {
  flex: 1;
  padding: 8px 12px;
  background: #edf2f7;
  color: #4a5568;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.change-data-btn:hover {
  background: #e2e8f0;
  border-color: #cbd5e0;
}

.no-dataset {
  padding: 16px;
}

.no-dataset-content {
  text-align: center;
  padding: 20px 16px;
}

.no-dataset-icon {
  font-size: 2rem;
  margin-bottom: 12px;
  opacity: 0.6;
}

.no-dataset p {
  margin: 0 0 16px 0;
  color: #718096;
  font-size: 0.9rem;
}

.upload-data-btn {
  width: 100%;
  padding: 12px 16px;
  background: #4299e1;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-data-btn:hover {
  background: #3182ce;
  transform: translateY(-1px);
}
<style scoped>
.sidebar-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
}

.shared-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-secondary);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-4);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.sidebar-title-wrapper {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.sidebar-icon {
  font-size: var(--font-size-lg);
}

.sidebar-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.01em;
}

.sidebar-collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition-fast);
}

.sidebar-collapse-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.sidebar-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3);
  scrollbar-width: thin;
  scrollbar-color: var(--border-secondary) transparent;
}

.sidebar-scroll-area::-webkit-scrollbar {
  width: 6px;
}

.sidebar-scroll-area::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-scroll-area::-webkit-scrollbar-thumb {
  background-color: var(--border-secondary);
  border-radius: 3px;
}

.sidebar-scroll-area::-webkit-scrollbar-thumb:hover {
  background-color: var(--text-tertiary);
}

/* Section Content Styles */
.section-content-inner {
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Dataset Info Styles */
.current-dataset-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.dataset-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
}

.dataset-icon {
  font-size: var(--font-size-xl);
}

.dataset-info h4 {
  margin: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.dataset-info p {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.dataset-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family-mono);
}

.feature-names-section {
  flex-direction: column;
  gap: var(--space-1);
}

.feature-names-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.feature-name {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-family: var(--font-family-mono);
  font-size: 11px;
}

.show-more-btn,
.show-less-btn {
  background: none;
  border: none;
  padding: 0;
  color: var(--accent-primary);
  font-size: 11px;
  cursor: pointer;
  margin-left: var(--space-1);
}

.show-more-btn:hover,
.show-less-btn:hover {
  text-decoration: underline;
}

.dataset-actions {
  margin-top: var(--space-2);
}

/* No Dataset Styles */
.no-dataset {
  padding: var(--space-4);
  text-align: center;
  background: var(--bg-tertiary);
  border-radius: var(--radius-base);
  border: 1px dashed var(--border-secondary);
}

.no-dataset-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.no-dataset-icon {
  font-size: var(--font-size-2xl);
  opacity: 0.5;
}

.no-dataset p {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* Divider & Group Titles */
.sidebar-divider {
  height: 1px;
  background: var(--border-primary);
  margin: var(--space-4) 0;
}

.section-group-title {
  padding: 0 var(--space-1) var(--space-2);
}

.section-group-title h5 {
  margin: 0;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Sync Status */
.sync-status-compact {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-2);
}

.sync-indicator-compact {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--radius-full);
  background: var(--bg-tertiary);
  color: var(--text-tertiary);
}

/* Tooltip Label */
.tooltip-label {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  cursor: help;
}

.help-icon {
  font-size: var(--font-size-xs);
  opacity: 0.5;
}

.tooltip-label:hover .help-icon {
  opacity: 1;
}

/* Responsive */
@media (max-width: 768px) {
  
  .show-more-btn,
  .show-less-btn {
    font-size: 0.7rem;
  }
}
</style>
