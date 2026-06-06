<template>
  <AppLayout>
    <template #sidebar>
      <SharedSidebar
        :sampleOptions="currentSampleOptions"
        :selectedSample="selectedSample"
        :initialSelectedSample="selectedSample"
        :showParameters="true"
        :quickStats="quickStatsDisplay"
        :showExportImport="true"
        :showRecentRuns="true"
        :showPageControls="false"
        :isDendrogramVisible="showDendrogram && treeVisualizationType === 'dendrogram'"
        :isScatterVisible="showScatterPlot"
        :isIcicleVisible="showDendrogram && treeVisualizationType === 'icicle'"
        :showVisualizationOptions="true"
        :xAxisDescription="selectedXAxisLabel"
        :yAxisDescription="selectedYAxisLabel"
        :currentPartitionMethod="selectedPartitionMethod"
        :currentTreeVisualizationType="treeVisualizationType"
        :currentActiveRunId="globalState.activeRunId.value || ''"
        @run-selected="handleRunSelected"
        @auto-start-clustering="handleAutoStartClustering"
        @show-outlier-tooltip="showOutlierTooltip"
        @hide-outlier-tooltip="hideOutlierTooltip"
      >
        <!-- Tree Type Selection -->
        <template #tree-type-select>
          <select
            id="tree-type"
            v-model="selectedTreeType"
            class="control-select"
            @change="() => {}"
          >
            <option v-for="type in treeTypes" :key="type" :value="type">{{ type }}</option>
          </select>
        </template>

        <!-- Power Parameter Selection -->
        <template #power-select>
          <input
            type="range"
            id="power"
            v-model="selectedPower"
            min="0"
            max="10"
            step="1"
            class="control-range"
          />
          <span class="range-value">{{ selectedPower }}</span>
        </template>

        <!-- Partition Method Selection -->
        <template #partition-method-select>
          <select
            id="partition-method"
            v-model="selectedPartitionMethod"
            class="control-select"
            @change="() => {}"
          >
            <option v-for="method in partitionMethods" :key="method" :value="method">{{ method }}</option>
          </select>
        </template>

        <!-- K Input -->
        <template #k-slider>
          <div class="k-input-container">
            <input
              type="number"
              id="cluster-k"
              v-model="selectedK"
              min="2"
              :max="maxAllowedK"
              step="1"
              class="k-number-input"
            />
            <span class="k-input-hint">Range: 2-{{ maxAllowedK }}</span>
          </div>
        </template>

        <!-- Run Button -->
        <template #run-button>
          <button 
            @click="fetchClusters" 
            :disabled="isClusteringRunning"
            class="run-clustering-btn"
          >
            Run Clustering
          </button>
          <button 
            @click="openCheatSheet" 
            class="cheatsheet-btn"
            style="margin-top: 0.75rem; width: 100%; padding: 0.75rem 1rem; background-color: #f8fafc; color: #1e40af; border: 1px solid #bfdbfe; border-radius: 6px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 0.5rem; transition: all 0.2s;"
            onmouseover="this.style.backgroundColor='#eff6ff'; this.style.borderColor='#93c5fd';"
            onmouseout="this.style.backgroundColor='#f8fafc'; this.style.borderColor='#bfdbfe';"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            Quick Help / Cheatsheet
          </button>
        </template>

        <!-- Plot Arrangement Controls -->
        <template #plot-arrangement-controls>
          <div class="plot-arrangement-controls">
            <button 
              @click="layoutMode = 'stacked'"
              :class="['layout-btn', { active: layoutMode === 'stacked' }]"
              title="Stack dendogram and scatter plot vertically"
            >
              📚 Stacked
            </button>
            <button 
              @click="layoutMode = 'side-by-side'"
              :class="['layout-btn', { active: layoutMode === 'side-by-side' }]"
              title="Place dendogram and scatter plot side by side"
            >
              📋 Side by Side
            </button>
          </div>
        </template>

        <!-- Dendrogram Tree Layout Controls -->
        <template #dendrogram-layout-controls>
          <div class="dendrogram-layout-controls">
            <button 
              @click="dendrogramLayout = 'radial'"
              :class="['layout-btn', { active: dendrogramLayout === 'radial' }]"
              title="Switch to Radial/Circular Tree Layout"
            >
              🔄 Radial
            </button>
            <button 
              @click="dendrogramLayout = 'cartesian'"
              :class="['layout-btn', { active: dendrogramLayout === 'cartesian' }]"
              title="Switch to Left to Right Tree Layout"
            >
              ➡️ Left to Right
            </button>
          </div>
        </template>

        <!-- Visibility Controls -->
        <template #visibility-controls>
          <div class="visibility-controls">
            <label class="checkbox-label">
              <input type="checkbox" v-model="showDendrogram" />
              <span>Show Tree Visualization</span>
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="showScatterPlot" />
              <span>Show Scatter Plot</span>
            </label>
          </div>
        </template>

        <!-- Tree Type Controls -->
        <template #tree-type-controls>
          <select
            id="tree-visualization-type"
            v-model="treeVisualizationType"
            class="control-select"
          >
            <option v-for="option in treeVisualizationOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </template>

        <!-- X-Axis Selection -->
        <template #x-axis-select>
          <select
            id="x-axis-select"
            v-model="selectedXAxis"
            class="control-select"
          >
            <template v-if="showFeatureAxisOptions">
              <option v-for="(featureName, index) in localFeatureNames" :key="`feature-${index}`" :value="`feature-${index}`">
                {{ featureName }}
              </option>
            </template>
            <option v-if="clusterData.dimensionality_reduction?.pca" value="pca-0">PCA Component 1</option>
            <option v-if="clusterData.dimensionality_reduction?.pca" value="pca-1">PCA Component 2</option>
            <option v-if="clusterData.dimensionality_reduction?.umap || isLoadingDR" value="umap-0">
              UMAP Component 1{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
            <option v-if="clusterData.dimensionality_reduction?.umap || isLoadingDR" value="umap-1">
              UMAP Component 2{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
            <option v-if="clusterData.dimensionality_reduction?.tsne || isLoadingDR" value="tsne-0">
              t-SNE Component 1{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
            <option v-if="clusterData.dimensionality_reduction?.tsne || isLoadingDR" value="tsne-1">
              t-SNE Component 2{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
          </select>
        </template>

        <!-- Y-Axis Selection -->
        <template #y-axis-select>
          <select
            id="y-axis-select"
            v-model="selectedYAxis"
            class="control-select"
          >
            <template v-if="showFeatureAxisOptions">
              <option v-for="(featureName, index) in localFeatureNames" :key="`feature-${index}`" :value="`feature-${index}`">
                {{ featureName }}
              </option>
            </template>
            <option v-if="clusterData.dimensionality_reduction?.pca" value="pca-0">PCA Component 1</option>
            <option v-if="clusterData.dimensionality_reduction?.pca" value="pca-1">PCA Component 2</option>
            <option v-if="clusterData.dimensionality_reduction?.umap || isLoadingDR" value="umap-0">
              UMAP Component 1{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
            <option v-if="clusterData.dimensionality_reduction?.umap || isLoadingDR" value="umap-1">
              UMAP Component 2{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
            <option v-if="clusterData.dimensionality_reduction?.tsne || isLoadingDR" value="tsne-0">
              t-SNE Component 1{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
            <option v-if="clusterData.dimensionality_reduction?.tsne || isLoadingDR" value="tsne-1">
              t-SNE Component 2{{ isLoadingDR ? ' ⏳' : '' }}
            </option>
          </select>
        </template>

        <!-- Ground Truth Status and Split-View -->
        <template #color-by-select>
          <div class="ground-truth-section">
            <!-- Ground Truth Availability Status -->
            <div class="form-note-with-tooltip" :class="{ success: hasGroundTruth }">
              <span class="note-icon">{{ hasGroundTruth ? '✅' : 'ℹ️' }}</span>
              <span>{{ hasGroundTruth ? 'Ground truth available' : 'Ground truth not available' }}</span>
              <button 
                type="button"
                class="info-trigger"
                @mouseenter="showGroundTruthTooltip"
                @mouseleave="hideGroundTruthTooltip"
                @focus="showGroundTruthTooltip"
                @blur="hideGroundTruthTooltip"
                aria-label="More information about ground truth labels"
              >
                ℹ️
              </button>
            </div>
            
            <!-- Single-View Color Toggle (when ground truth available and NOT in split-view) -->
            <div v-if="hasGroundTruth && !useSplitView" class="color-toggle-container">
              <div class="color-toggle-buttons">
                <button 
                  @click="selectedColorBy = 'predicted'"
                  :class="['color-toggle-btn', { active: selectedColorBy === 'predicted' }]"
                >
                  Predicted Clusters
                </button>
                <button 
                  @click="selectedColorBy = 'ground_truth'"
                  :class="['color-toggle-btn', { active: selectedColorBy === 'ground_truth' }]"
                >
                  Ground Truth Labels
                </button>
              </div>
            </div>
            
            <!-- Split-View Toggle (when ground truth is available) -->
            <div v-if="hasGroundTruth" class="split-view-toggle-container">
              <label class="toggle-label">
                <input 
                  type="checkbox" 
                  v-model="useSplitView"
                  class="toggle-checkbox"
                />
                <span class="toggle-text">Split-View Comparison</span>
                <div class="toggle-hint">Compare ground truth vs predicted side-by-side</div>
              </label>
            </div>
          </div>
        </template>

        <!-- Colorblind-Friendly Mode Toggle -->
        <template #colorblind-toggle>
          <label class="toggle-label">
            <input
              type="checkbox"
              v-model="colorblindMode"
              class="toggle-checkbox"
            />
            <span class="toggle-text">Colorblind-friendly mode</span>
            <div class="toggle-hint">Use a colorblind-safe color palette for clusters</div>
          </label>
        </template>

        <!-- Outlier Style Selection -->
        <template #outlier-style-select>
          <select
            id="outlier-style-select"
            v-model="selectedOutlierStyle"
            class="control-select"
          >
            <option value="subtle">Subtle (Black)</option>
            <option value="prominent">Prominent (Red with Border)</option>
          </select>
        </template>
      </SharedSidebar>
    </template>

    <template #default>
      <div class="clustering-page">
        <!-- Welcome State (when no dataset selected or no clustering results) -->
        <div v-if="!hasValidDataset || (!clusterData?.points?.length && !isClusteringRunning)" class="welcome-state">
          <div class="welcome-container">
            <div class="welcome-header">
              <div class="welcome-icon">🔬</div>
              <h1>Clustering Visualization</h1>
              <p v-if="!hasValidDataset">No dataset selected. Choose a dataset to begin clustering analysis.</p>
              <p v-else-if="hasValidDataset && !clusterData?.points?.length">Dataset loaded: {{ currentDatasetName }}. Configure parameters and run clustering to see visualizations.</p>
              <p v-else>Configure your parameters in the sidebar and run clustering to see interactive visualizations</p>
            </div>
            
            <div class="welcome-actions">
              <div v-if="!hasValidDataset" class="action-card" @click="startOnboarding">
                <div class="action-icon">📊</div>
                <div class="action-content">
                  <h3>Select Dataset</h3>
                  <p>Choose sample data or upload your own file</p>
                </div>
              </div>
              
              <div v-if="!hasValidDataset" class="action-divider">
                <span>or</span>
              </div>
              
              <div class="action-hint">
                <p v-if="!hasValidDataset">Use the sidebar to select a sample dataset or upload your own data</p>
                <p v-else-if="hasValidDataset && !clusterData?.points?.length">Ready to cluster! Click "Run Clustering" in the sidebar when you're ready.</p>
                <p v-else>Click "Run Clustering" to refresh results with the current dataset.</p>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Loading State -->
        <LoadingBar
          v-if="isClusteringRunning"
          :isLoading="isClusteringRunning"
          message="Running clustering analysis..."
          :onAbort="abortClustering"
        />
        
        <!-- Static Split-View Layout (when ground truth is available and enabled) -->
        <div v-if="clusterData?.points?.length && useSplitView && hasGroundTruth" class="split-view-layout">
          <StaticSplitView
            :key="`split-view-${globalState.activeRunId.value || 'default'}-${selectedColorBy}-${selectedOutlierStyle}-${colorblindMode}`"
            :treeData="displayTreeData"
            :treeVisualizationType="treeVisualizationType"
            :dendrogramLayout="dendrogramLayout"
            :nodeData="displayClusterData"
            :highlightedNodeInTree="highlightedNodeInTree"
            :selectedXAxis="selectedXAxis"
            :selectedYAxis="selectedYAxis"
            :selectedOutlierStyle="selectedOutlierStyle"
            :datasetName="datasetNameForImages"
            :featureNames="featureNames"
            :width="visualizationContainerWidth"
            :height="visualizationContainerHeight"
            :activeRunId="globalState.activeRunId.value || 'default'"
            :groundTruthClusterCount="groundTruthClusterCount"
            :predictedClusterCount="actualClusterCount || selectedK"
            @update:highlightedPoints="handleHighlightedPointsUpdate"
            @pointClicked="handlePointClicked"
            @pointHovered="handlePointHovered"
            @nodesSelected="handleNodesSelected"
          />
        </div>

        <!-- Full-Screen Visualization Layout -->
        <div v-else-if="clusterData?.points?.length" class="visualization-layout" :class="{ 'side-by-side': layoutMode === 'side-by-side' }">
          <!-- Analysis Summary Bar -->
          <div v-if="showInfoBar" class="analysis-summary">
            <div class="summary-content">
              <div class="summary-metric">
                <span class="summary-label">Dataset</span>
                <span class="summary-value">{{ currentDatasetName }}</span>
              </div>
              
              <div class="summary-divider"></div>
              
              <div class="summary-metric">
                <span class="summary-label">Algorithm</span>
                <div class="summary-value-group">
                  <span class="summary-value">{{ selectedTreeType }}</span>
                  <span class="summary-sub-value">/ {{ selectedPartitionMethod }}</span>
                </div>
              </div>
              
              <div class="summary-divider"></div>
              
              <div class="summary-metric">
                <span class="summary-label">Clusters</span>
                <span class="summary-value">{{ actualClusterCount || selectedK }}</span>
              </div>
              
              <!-- Ground Truth Cluster Count (when ARI selection is active) -->
              <template v-if="selectedColorBy === 'ground_truth' && hasGroundTruth">
                <div class="summary-divider"></div>
                <div class="summary-metric">
                  <span class="summary-label">Ground Truth</span>
                  <span class="summary-value">{{ groundTruthClusterCount }} <span class="summary-unit">clusters</span></span>
                </div>
              </template>
            </div>
            <button @click="showInfoBar = false" class="hide-summary-btn" title="Hide summary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <!-- Main Visualizations Container -->
          <div class="visualizations-container" :class="{ 'side-by-side': layoutMode === 'side-by-side' }">
            <!-- Tree Visualization Panel -->
            <div 
              v-if="showDendrogram" 
              class="visualization-panel tree-panel"
              :class="{ 'resizable-panel': layoutMode === 'side-by-side' }"
            >
              <div class="panel-header">
                <h3>{{ treeVisualizationType === 'dendrogram' ? 'Dendrogram' : 'Icicle Plot' }}</h3>
                <div class="panel-actions">
                  <button v-if="!showInfoBar" @click="showInfoBar = true" class="panel-action-btn" title="Show info bar">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="1"></circle>
                      <path d="M20.1 15.1c.4-.6.7-1.3.7-2.1s-.3-1.5-.7-2.1l-2.1-2.8c-.4-.6-1-.9-1.7-.9h-4.6c-.7 0-1.3.3-1.7.9l-2.1 2.8c-.4.6-.7 1.3-.7 2.1s.3 1.5.7 2.1l2.1 2.8c.4.6 1 .9 1.7.9h4.6c.7 0 1.3-.3 1.7-.9l2.1-2.8z"></path>
                    </svg>
                  </button>
                </div>
              </div>
              <div class="panel-content">
                <ClusterDendrogram
                  v-if="treeVisualizationType === 'dendrogram'"
                  :key="`dendrogram-${globalState.activeRunId.value || 'default'}-${selectedColorBy}-${selectedOutlierStyle}-${colorblindMode}`"
                  :tree="displayTreeData"
                  :width="dendrogramWidth"
                  :height="dendrogramHeight"
                  :nodeData="displayClusterData"
                  :layout="dendrogramLayout"
                  :selectedColorBy="selectedColorBy"
                  :selectedOutlierStyle="selectedOutlierStyle"
                  :highlightedNode="highlightedNodeInTree"
                  :selectedNodes="selectedNodesForFullscreen"
                  @update:highlightedPoints="handleHighlightedPointsUpdate" 
                  @nodeSelected="handleNodeSelectionFromTree"
                />
                <IciclePlot
                  v-else-if="treeVisualizationType === 'icicle'"
                  :key="`icicle-${globalState.activeRunId.value || 'default'}-${selectedColorBy}-${selectedOutlierStyle}-${colorblindMode}`"
                  :tree="displayTreeData"
                  :width="dendrogramWidth"
                  :height="dendrogramHeight"
                  :nodeData="displayClusterData"
                  :selectedColorBy="selectedColorBy"
                  :selectedOutlierStyle="selectedOutlierStyle"
                  :highlightedNode="highlightedNodeInTree"
                  :selectedNodes="selectedNodesForFullscreen"
                  @update:highlightedPoints="handleHighlightedPointsUpdate"
                  @nodeSelected="handleNodeSelectionFromTree"
                />
              </div>
            </div>

            <!-- Resizer for side-by-side layout -->
            <div 
              v-if="showDendrogram && showScatterPlot && layoutMode === 'side-by-side'" 
              class="panel-resizer"
              @mousedown="startResize"
            ></div>

            <!-- Scatter Plot Panel -->
            <div 
              v-if="showScatterPlot" 
              class="visualization-panel scatter-panel"
              :class="{ 'resizable-panel': layoutMode === 'side-by-side' }"
            >
              <div class="panel-header">
                <h3>Scatter Plot</h3>
                <div class="panel-actions">
                </div>
              </div>
              <div class="panel-content">
                <!-- Always use Canvas scatter plot for all datasets -->
                <CanvasScatterPlot
                  :data="displayClusterData"
                  :width="scatterWidth"
                  :height="scatterHeight" 
                  :highlightedIndices="combinedHighlightedPoints" 
                  :selectedXAxis="selectedXAxis" 
                  :selectedYAxis="selectedYAxis"
                  :selectedColorBy="selectedColorBy"
                  :selectedOutlierStyle="selectedOutlierStyle"
                  :datasetName="datasetNameForImages"
                  :featureNames="featureNames"
                  @pointHovered="handlePointHovered"
                  @pointClicked="handlePointClicked"
                />
              </div>
            </div>
          </div>

        </div>
      </div>
      
      <!-- Dataset Change Notification -->
      <div v-if="showDatasetChangeNotification" class="dataset-notification">
        <div class="notification-content">
          <div class="notification-icon">✅</div>
          <span class="notification-message">{{ datasetChangeNotification }}</span>
          <button @click="showDatasetChangeNotification = false" class="notification-close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>
    </template>
  </AppLayout>

  <!-- Onboarding Wizard -->
  <Suspense v-if="showOnboardingWizard">
    <template #default>
      <OnboardingWizard
        :startFresh="true"
        @close="showOnboardingWizard = false"
        @finish="handleOnboardingFinish"
      />
    </template>
    <template #fallback>
      <div class="wizard-loading-overlay">
        <div class="wizard-loading-spinner"></div>
        <p>Loading onboarding...</p>
      </div>
    </template>
  </Suspense>

  <!-- Tooltips -->
  <TooltipComponent
    :visible="outlierTooltipVisible"
    :target-element="outlierTooltipTarget"
    :content="outlierTooltipContent"
    title="Outlier Visualization"
    theme="info"
    size="large"
    :is-rich-content="true"
    position="auto"
    @close="hideOutlierTooltip"
  />
  
  <TooltipComponent
    :visible="groundTruthTooltipVisible"
    :target-element="groundTruthTooltipTarget"
    :content="groundTruthTooltipContent"
    title="Ground Truth Labels"
    :theme="hasGroundTruth ? 'info' : 'warning'"
    size="large"
    :is-rich-content="true"
    position="auto"
    @close="hideGroundTruthTooltip"
  />

  <CheatSheetModal ref="cheatSheetModal" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, defineAsyncComponent, shallowRef } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useGlobalState, type DatasetInfo } from '~/composables/useGlobalState';
import { useStudySession } from '~/composables/useStudySession';
import { useSidebarState } from '~/composables/useSidebarState';
import { useMemoryManagement } from '~/composables/useMemoryManagement';
import { useDatasetManager } from '~/composables/useDatasetManager';
import { useFileUploadAPI } from '~/composables/useFileUploadAPI';
import { convertTreeToStandardFormat } from '~/composables/useTreeUtils';
import { getColorblindPalette } from '~/composables/useScientificColors';
import { useToast } from '~/composables/useToast';
import { useTooltips } from '~/composables/useTooltips';
import CanvasScatterPlot from '~/components/CanvasScatterPlot.vue';
import LoadingBar from '~/components/LoadingBar.vue';
import TooltipComponent from '~/components/TooltipComponent.vue';
import StaticSplitView from '~/components/StaticSplitView.vue';
import CheatSheetModal from '~/components/CheatSheetModal.vue';

// Lazy load onboarding wizard
const OnboardingWizard = defineAsyncComponent(() => import('~/components/onboarding/OnboardingWizard.vue'));

interface SampleOption {
  value: string;
  label: string;
}

const router = useRouter();
const route = useRoute();
const globalState = useGlobalState();
const studySession = useStudySession();
const sidebar = useSidebarState();
const sidebarState = sidebar.state;
const datasetManager = useDatasetManager();
const fileUploadAPI = useFileUploadAPI();
const { tooltips } = useTooltips();

// Memory management
const memoryManager = useMemoryManagement();
const { 
  trackLargeObject, 
  forceGarbageCollection, 
  startMemoryMonitoring, 
  isMemoryUsageHigh,
  formatMemorySize,
  checkMemoryUsage 
} = memoryManager;

// Toast notifications
const { addToast } = useToast();

// Clustering state
const isClusteringRunning = ref(false);
const clusteringAbortController = ref<AbortController | null>(null);

// Simple dimensionality reduction state
const isLoadingDR = ref(false);
const currentClusterId = ref<string | null>(null);
let drPollingInterval: NodeJS.Timeout | null = null;

// Cheat Sheet definition
const cheatSheetModal = ref<InstanceType<typeof CheatSheetModal> | null>(null);

const openCheatSheet = () => {
  if (cheatSheetModal.value) {
    cheatSheetModal.value.open();
  }
};

// Onboarding wizard state and functions
const showOnboardingWizard = ref(false);

const startOnboarding = () => {
  showOnboardingWizard.value = true;
};

const handleOnboardingFinish = (onboardingState: any) => {
  showOnboardingWizard.value = false;

  // Use nextTick to ensure DOM updates before navigation
  nextTick(async () => {
    // Set global state from onboarding wizard
    if (onboardingState.data.type === 'sample') {
      const sampleName = onboardingState.data.value;
      // Get dimensions from global state sampleOptions instead of hardcoded mapping
      const sampleOption = globalState.sampleOptions.find(opt => opt.value === sampleName);
      const dimensions = sampleOption?.dimensions || 2;
      const headers = Array.from({ length: dimensions }, (_, i) => `Feature ${i + 1}`);
      
      globalState.setDataset({
        name: onboardingState.data.name,
        type: 'sample',
        sampleName: onboardingState.data.value,
        n_samples: onboardingState.data.n_samples,
        headers,
        featureCount: dimensions
      });

    } else if (onboardingState.data.type === 'upload') {
      // Set uploaded data in global state
      globalState.setDataset({
        name: onboardingState.data.name,
        type: 'uploaded',
        data: onboardingState.data.parsedData,
        headers: onboardingState.data.headers,
        pointCount: onboardingState.data.rowCount,
        featureCount: onboardingState.data.columnCount,
        hasHeaders: onboardingState.data.hasHeaders,
        missingValueStrategy: onboardingState.data.missingValueStrategy,
        normalization: onboardingState.data.normalization
      });
    }

    // Set clustering parameters
    globalState.setClusteringParameters({
      treeType: onboardingState.parameters.treeType,
      partitionMethod: onboardingState.parameters.partitionMethod,
      power: onboardingState.parameters.power,
      selectedK: onboardingState.parameters.k
    });

    // Mark onboarding as completed
    globalState.setOnboardingCompleted(true);

    console.log('Onboarding completed, data and parameters set');

    // Automatically trigger clustering
    console.log('[Clustering] Auto-starting clustering after onboarding...');
    addToast('Starting initial clustering with recommended parameters...', 'info');
    
    // Slight delay to ensure parameters are fully applied and UI updates
    setTimeout(() => {
      fetchClusters();
    }, 100);
  });
};

// Auto-load active run data
const loadActiveRun = async () => {
  const activeRun = globalState.activeRun.value;
  if (activeRun) {
    console.log('Clustering page: Auto-loading active run:', activeRun.dataset, 'ID:', activeRun.id);
    await handleRunLoaded(activeRun);
  } else {
    console.log('Clustering page: No active run to load');
  }
};

// Watch for changes to the active run and auto-load
watch(() => globalState.activeRun.value, async (newActiveRun, oldActiveRun) => {
  console.log('Clustering page: Active run watcher triggered', {
    newId: newActiveRun?.id,
    oldId: oldActiveRun?.id,
    newDataset: newActiveRun?.dataset,
    oldDataset: oldActiveRun?.dataset
  });
  
  // Only process if the run actually changed
  if (newActiveRun?.id === oldActiveRun?.id) {
    console.log('Clustering page: Same run ID, skipping');
    return
  }
  
  console.log('Clustering page: Active run changed from', oldActiveRun?.dataset, 'to', newActiveRun?.dataset);
  
  if (newActiveRun && !isLoadingRun.value) {
    console.log('Clustering page: Loading new active run:', newActiveRun.dataset, 'ID:', newActiveRun.id);
    await handleRunLoaded(newActiveRun);
  } else if (!newActiveRun) {
    // Clear visualizations when no active run
    console.log('Clustering page: No active run, clearing visualizations');
    clusterData.value = { points: [], labels: [], centers: [], dimensionality_reduction: { pca: null, umap: null } }
    treeData.value = null
    evaluationMetrics.value = null
    showMetrics.value = false
  }
}, { immediate: false });

// Consolidated onMounted function to fix parameter loading order
onMounted(async () => {
  console.log('Clustering page: onMounted called');
  componentMounted = true; // Set component mounted state
  
  // Add global error handler for Vue component errors
  if (typeof window !== 'undefined') {
    window.addEventListener('error', (error) => {
      if (error.message?.includes('Cannot set properties of null') || 
          error.message?.includes('Cannot read properties of null')) {
        console.warn('[CLUSTERING] Caught component lifecycle error:', error.message);
        // Prevent the error from bubbling up and breaking navigation
        error.preventDefault();
      }
    });
    
    window.addEventListener('unhandledrejection', (event) => {
      if (event.reason?.message?.includes('Cannot set properties of null') ||
          event.reason?.message?.includes('Cannot read properties of null')) {
        console.warn('[CLUSTERING] Caught unhandled promise rejection:', event.reason.message);
        // Prevent the error from bubbling up
        event.preventDefault();
      }
    });
  }
  
  if (sidebarState.selectedSample) {
    selectedSample.value = sidebarState.selectedSample;
  }
  
  // STEP 1: Auto-load active run FIRST (if exists) to set parameters
  console.log('Clustering page: Checking for active run on mount...');
  const activeRun = globalState.activeRun.value;
  const hasActiveRun = !!activeRun;
  
  if (hasActiveRun) {
    // Enhanced dataset matching with better validation for uploaded files
    const currentDataset = globalState.currentDataset.value;
    const runMatchesDataset = currentDataset && validateDatasetMatch(activeRun, currentDataset);
    
    if (runMatchesDataset) {
      console.log('Clustering page: Loading active run parameters (dataset matches):', activeRun.dataset);
      await loadActiveRun();
    } else {
      // Special handling for imported runs - don't clear them immediately, let them try to restore their dataset
      const isImportedRun = activeRun.parameters?.loadedFromComplete || activeRun.parameters?.loadedFromTree;
      
      if (isImportedRun) {
        console.log('Clustering page: Imported run detected, attempting to restore dataset context:', activeRun.dataset);
        try {
          // Try to restore dataset context from imported run
          if (activeRun.parameters?.sample) {
            const sampleOption = globalState.getSampleOption(activeRun.parameters.sample);
            if (sampleOption) {
              const datasetInfo = {
                name: sampleOption.label,
                type: 'sample' as const,
                sampleName: sampleOption.value,
                n_samples: activeRun.parameters.n_samples || sampleOption.typical_samples,
                featureCount: sampleOption.dimensions,
                pointCount: activeRun.parameters.n_samples || sampleOption.typical_samples,
                headers: Array.from({ length: sampleOption.dimensions }, (_, i) => `Feature ${i + 1}`)
              };
              globalState.setDataset(datasetInfo);
              console.log('Clustering page: Restored dataset context for imported run:', datasetInfo.name);
              await loadActiveRun();
              return;
            }
          }
        } catch (error) {
          console.warn('Clustering page: Failed to restore dataset for imported run:', error);
        }
      }
      
      console.log('Clustering page: Not loading active run - dataset mismatch. Current:', currentDataset?.name, 'Run:', activeRun.dataset);
      // Only clear non-imported runs or imported runs that failed restoration
      if (!isImportedRun) {
        globalState.setActiveRun(null);
      }
    }
  }
  
  // STEP 2: Then fetch backend options and validate
  try {
    const res = await fetch('/api/cluster/options');
    if (res.ok) {
      const opts = await res.json();
      treeTypes.value = opts.treeTypes || [];
      partitionMethods.value = opts.partitionMethods || [];
      
      if (treeTypes.value.length === 0) console.warn('No tree types loaded.');
      if (partitionMethods.value.length === 0) console.warn('No partition methods loaded.');
      
      // STEP 3: Load parameters in priority order:
      // 1. Active run (already loaded above)
      // 2. Global state parameters (from other pages)
      // 3. Backend defaults (fallback)
      
      if (!hasActiveRun) {
        // Check for saved parameters from global state
        const savedParams = globalState.clusteringParameters.value;
        
        if (savedParams) {
          console.log('Clustering page: Loading parameters from global state:', savedParams);
          
          // Load saved parameters if they're valid
          if (savedParams.treeType && treeTypes.value.includes(savedParams.treeType)) {
            selectedTreeType.value = savedParams.treeType;
          } else if (treeTypes.value.length > 0) {
            selectedTreeType.value = treeTypes.value[0];
          }
          
          if (savedParams.partitionMethod && partitionMethods.value.includes(savedParams.partitionMethod)) {
            selectedPartitionMethod.value = savedParams.partitionMethod;
          } else if (partitionMethods.value.length > 0) {
            selectedPartitionMethod.value = partitionMethods.value[0];
          }
          
          if (savedParams.power) {
            selectedPower.value = savedParams.power;
          }
          if (savedParams.selectedK) {
            selectedK.value = savedParams.selectedK;
          } else if (savedParams.k) {
            // Handle onboarding parameters that use 'k' instead of 'selectedK'
            selectedK.value = savedParams.k;
          }
        } else {
          console.log('Clustering page: No saved parameters, using backend defaults');
          // Use backend defaults if no saved parameters exist
          if (treeTypes.value.length > 0) {
            selectedTreeType.value = treeTypes.value[0];
          }
          if (partitionMethods.value.length > 0) {
            selectedPartitionMethod.value = partitionMethods.value[0];
          }
        }
      } else {
        console.log('Clustering page: Active run loaded, preserving parameters:', {
          treeType: selectedTreeType.value,
          partitionMethod: selectedPartitionMethod.value
        });
      }
    } else {
      console.error('Failed to fetch cluster options:', res.status, res.statusText);
      treeTypes.value = []; 
      partitionMethods.value = [];
    }
  } catch (err) {
    console.error('Error fetching cluster options onMounted:', err);
    treeTypes.value = []; 
    partitionMethods.value = [];
  }
  
  // STEP 4: Load UI preferences from localStorage
  try {
    const savedUseSplitView = localStorage.getItem('clustering-use-split-view');
    if (savedUseSplitView === 'true') {
      useSplitView.value = true;
    }
    
    console.log('Clustering page: Loaded UI preferences from localStorage');
  } catch (err) {
    console.warn('Failed to load UI preferences from localStorage:', err);
  }
  
  // STEP 4b: Restore visualization preferences from global state (persisted across page navigations)
  const savedVizPrefs = globalState.visualizationPreferences.value;
  if (savedVizPrefs.selectedXAxis && savedVizPrefs.selectedYAxis) {
    selectedXAxis.value = savedVizPrefs.selectedXAxis;
    selectedYAxis.value = savedVizPrefs.selectedYAxis;
    console.log('Clustering page: Restored axis selections from global state:', savedVizPrefs.selectedXAxis, savedVizPrefs.selectedYAxis);
  }
  
  // STEP 5: Setup dimensions and event listeners
  updateVisualizationDimensions();
  window.addEventListener('resize', updateVisualizationDimensions);
  
  // Initialize to prevent undefined errors on first render
  if (!hasActiveRun) {
    clusterData.value = { points: [], labels: [], centers: [] };
    treeData.value = null;
    evaluationMetrics.value = null;
  }
  
  // STEP 5: Handle onboarding flow (only if no active run)
  if (!hasActiveRun) {
    // Check for global state from onboarding
    if (globalState.currentDataset.value) {
      const dataset = globalState.currentDataset.value;
      console.log('Loading dataset from global state:', dataset);
      
      if (dataset.type === 'sample') {
        selectedSample.value = dataset.sampleName || dataset.name.toLowerCase();
        uploadedData.value = null;
        uploadedFileName.value = null;
      } else if (dataset.type === 'uploaded' && dataset.data) {
        uploadedData.value = dataset.data as number[][];
        uploadedFileName.value = dataset.fileName || dataset.name;
      } else if (dataset.type === 'imported' && dataset.data) {
        // Handle imported datasets - treat them like uploaded data
        uploadedData.value = dataset.data as number[][];
        uploadedFileName.value = dataset.fileName || dataset.name;
        selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + (dataset.fileName || dataset.name);
      }
    }
    
    // Check for clustering parameters from global state  
    if (globalState.clusteringParameters.value) {
      const params = globalState.clusteringParameters.value;
      console.log('Loading parameters from global state:', params);
      
      if (params.treeType && treeTypes.value.includes(params.treeType)) {
        selectedTreeType.value = params.treeType;
      }
      if (params.partitionMethod && partitionMethods.value.includes(params.partitionMethod)) {
        selectedPartitionMethod.value = params.partitionMethod;
      }
      if (params.power) {
        selectedPower.value = params.power;
      }
      if (params.selectedK) {
        selectedK.value = params.selectedK;
      } else if (params.k) {
        // Handle onboarding parameters that use 'k' instead of 'selectedK'
        selectedK.value = params.k;
      }
      
      // REMOVED: Auto-run clustering
      // We should only run clustering when the user explicitly clicks the button
      // This prevents unwanted clustering runs when just navigating between pages
    }
  }

  // Check for auto-start request from history
  if (route.query.autostart === 'true') {
    setTimeout(() => {
      console.log('[Clustering] Auto-start requested via query parameter');
      addToast('Auto-starting clustering with historical parameters...', 'info');
      fetchClusters();
    }, 500);
  }
});

onUnmounted(() => {
  // Save visualization preferences to global state for persistence across page navigations
  globalState.setVisualizationPreferences({
    selectedXAxis: selectedXAxis.value,
    selectedYAxis: selectedYAxis.value,
  });
  
  window.removeEventListener('resize', updateVisualizationDimensions);
  // Clean up dimensionality reduction polling
  if (drPollingInterval) {
    clearInterval(drPollingInterval);
    drPollingInterval = null;
  }
  // Clean up highlight update timeout to prevent memory leaks
  if (highlightUpdateTimeout) {
    clearTimeout(highlightUpdateTimeout);
    highlightUpdateTimeout = null;
  }
});

const UPLOADED_FILE_MARKER_PREFIX = "Uploaded: ";
const uploadedFileName = ref<string | null>(null);

// UI state
const showInfoBar = ref(true); // Show infobar by default
const showMetrics = ref(false);

// Responsive dimensions - calculated based on available viewport space
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280);
const viewportHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 800);

const updateVisualizationDimensions = () => {
  viewportWidth.value = window.innerWidth;
  viewportHeight.value = window.innerHeight;
};

// Computed dimensions for maximum space utilization
const availableWidth = computed(() => {
  // Account for sidebar (380px) and padding
  return viewportWidth.value - 380 - 40;
});

const availableHeight = computed(() => {
  // Account for header, info bar, and metrics panel
  const headerHeight = showInfoBar.value ? 60 : 0;
  const metricsHeight = showMetrics.value ? 200 : 40;
  return viewportHeight.value - 60 - headerHeight - metricsHeight - 40; // 60 for app header, 40 for padding
});

const dendrogramWidth = computed(() => {
  if (layoutMode.value === 'side-by-side') {
    return Math.max(400, (availableWidth.value * dendrogramPanelSize.value / 100) - 60);
  }
  return Math.max(600, availableWidth.value - 40);
});

const dendrogramHeight = computed(() => {
  if (layoutMode.value === 'side-by-side') {
    return Math.max(400, availableHeight.value - 80); // Account for panel header
  }
  return Math.max(300, (availableHeight.value / 2) - 60);
});

const scatterWidth = computed(() => {
  if (layoutMode.value === 'side-by-side') {
    return Math.max(400, (availableWidth.value * scatterPanelSize.value / 100) - 60);
  }
  return Math.max(600, availableWidth.value - 40);
});

const scatterHeight = computed(() => {
  if (layoutMode.value === 'side-by-side') {
    return Math.max(400, availableHeight.value - 80); // Account for panel header
  }
  return Math.max(300, (availableHeight.value / 2) - 60);
});

const treeTypes = shallowRef<string[]>([]);
const partitionMethods = shallowRef<string[]>([]);
const selectedTreeType = ref('');
const selectedPartitionMethod = ref('');

// Tooltip state
const outlierTooltipVisible = ref(false);
const groundTruthTooltipVisible = ref(false);
const outlierTooltipTarget = ref<HTMLElement | null>(null);
const groundTruthTooltipTarget = ref<HTMLElement | null>(null);

// Tooltip handlers
const showOutlierTooltip = (event: MouseEvent) => {
  outlierTooltipTarget.value = event.target as HTMLElement;
  outlierTooltipVisible.value = true;
};

const hideOutlierTooltip = () => {
  outlierTooltipVisible.value = false;
  outlierTooltipTarget.value = null;
};

const showGroundTruthTooltip = (event: MouseEvent) => {
  groundTruthTooltipTarget.value = event.target as HTMLElement;
  groundTruthTooltipVisible.value = true;
};

const hideGroundTruthTooltip = () => {
  groundTruthTooltipVisible.value = false;
  groundTruthTooltipTarget.value = null;
};

// Tooltip content
const outlierTooltipContent = computed(() => `
  <p><strong>What are outliers?</strong></p>
  <p>Outliers are data points that are marked with label <code>-1</code> by the clustering algorithm. These points don't fit well into any of the identified clusters.</p>
  
  <p><strong>Visualization Options:</strong></p>
  <ul>
    <li><strong>Subtle (Black):</strong> Outliers appear as small black dots that blend into the background</li>
    <li><strong>Prominent (Red with Border):</strong> Outliers are highlighted in red with a distinct border for easy identification</li>
  </ul>
  
  <p><strong>Note:</strong> This styling only applies when "Predicted Clusters" is selected for coloring. When using ground truth labels, outlier styling is determined by the original data.</p>
`);

const groundTruthTooltipContent = computed(() => {
  if (hasGroundTruth.value) {
    return `
      <p><strong>Ground Truth Available!</strong></p>
      <p>Your dataset contains ground truth labels, which allows for:</p>
      
      <ul>
        <li><strong>Accuracy Assessment:</strong> Compare predicted clusters against known correct labels</li>
        <li><strong>Performance Metrics:</strong> Calculate metrics like Adjusted Rand Index (ARI) and silhouette scores</li>
        <li><strong>Visualization Options:</strong> Switch between predicted clusters and actual labels to see how well the algorithm performed</li>
        <li><strong>Model Validation:</strong> Validate clustering quality and adjust parameters as needed</li>
      </ul>
      
      <p>Use the dropdown to switch between "Predicted Clusters" and "Ground Truth Labels" visualization modes.</p>
    `;
  } else {
    return `
      <p><strong>Ground Truth Not Available</strong></p>
      <p>Your dataset doesn't contain ground truth labels. Ground truth labels are the "correct" or known classifications for your data points.</p>
      
      <p><strong>To add ground truth:</strong></p>
      <ul>
        <li>Include a column with true labels/categories in your dataset</li>
        <li>During data upload, mark this column as the ground truth column</li>
        <li>Supported formats: categorical labels, numeric class IDs, or string categories</li>
      </ul>
      
      <p><strong>Benefits of ground truth:</strong></p>
      <ul>
        <li>Measure clustering accuracy with metrics like ARI</li>
        <li>Validate algorithm performance</li>
        <li>Compare different clustering approaches</li>
        <li>Visualize both predicted and actual classifications</li>
      </ul>
    `;
  }
});
const selectedPower = ref(2);
const selectedK = ref(3);
const selectedSample = ref<string | null>(null);
const uploadedData = shallowRef<number[][] | null>(null);
const clusterData = shallowRef<any>({ points: [], labels: [], centers: [], dimensionality_reduction: { pca: null, umap: null, tsne: null } });
const treeData = ref<any>(null);

// Performance optimization - automatic Canvas vs SVG switching
const pointCount = computed(() => {
  return clusterData.value?.points?.length || 0;
});


const scatterPlotPerformanceInfo = computed(() => {
  const count = pointCount.value;
  if (count === 0) return null;
  
  if (count <= 1000) {
    return { level: 'optimal', message: `${count} points - optimal performance (Canvas)` };
  } else if (count <= 5000) {
    return { level: 'good', message: `${count} points - good performance (Canvas)` };
  } else if (count <= 10000) {
    return { level: 'optimized', message: `${count} points - using Canvas for better performance` };
  } else {
    return { level: 'high-performance', message: `${count} points - high-performance Canvas mode` };
  }
});

// Enhanced performance monitoring for large datasets
const performanceMetrics = ref({
  clusteringTime: 0,
  renderingTime: 0,
  memoryUsage: 0,
  dataSize: 0,
  lastUpdate: null as Date | null
});

const startPerformanceMonitoring = () => {
  if (pointCount.value > 500) {
    console.log(`[Performance] Starting monitoring for dataset with ${pointCount.value} points`);
    const memoryInfo = (performance as any).memory;
    if (memoryInfo) {
      performanceMetrics.value.memoryUsage = memoryInfo.usedJSHeapSize / 1024 / 1024; // MB
    }
    performanceMetrics.value.dataSize = pointCount.value;
    performanceMetrics.value.lastUpdate = new Date();
  }
};

const trackRenderingTime = (startTime: number, component: string) => {
  const duration = performance.now() - startTime;
  if (pointCount.value > 500) {
    console.log(`[Performance] ${component} rendering took ${duration.toFixed(2)}ms for ${pointCount.value} points`);
    if (component === 'clustering') {
      performanceMetrics.value.clusteringTime = duration;
    } else if (component === 'visualization') {
      performanceMetrics.value.renderingTime = duration;
    }
  }
};

const performanceWarnings = computed(() => {
  const warnings = [];
  const count = pointCount.value;
  
  if (count > 5000) {
    warnings.push({
      type: 'info',
      message: `Large dataset (${count.toLocaleString()} points) - optimizations active`
    });
  }
  
  if (performanceMetrics.value.renderingTime > 2000) {
    warnings.push({
      type: 'warning',
      message: `Slow rendering detected (${(performanceMetrics.value.renderingTime / 1000).toFixed(1)}s)`
    });
  }
  
  if (performanceMetrics.value.memoryUsage > 100) {
    warnings.push({
      type: 'warning',
      message: `High memory usage (${performanceMetrics.value.memoryUsage.toFixed(1)} MB)`
    });
  }
  
  return warnings;
});

// Memory management - clear large objects when not needed
const clearLargeData = () => {
  // Keep essential data but clear large arrays
  if (clusterData.value && clusterData.value.original_points) {
    // Don't keep original points in memory after processing
    delete clusterData.value.original_points;
  }
  
  // Force garbage collection hint
  if (typeof window !== 'undefined' && (window as any).gc) {
    (window as any).gc();
  }
};
const pointsToHighlightInScatter = shallowRef<number[]>([]);
// Selection support for full-screen layout (union with hover highlights)
const selectedNodesForFullscreen = ref<Set<string>>(new Set());
const nodeIdToPointsFullscreen = ref<Map<string, number[]>>(new Map());
const selectedPointsFromNodesFullscreen = shallowRef<number[]>([]);
let selectionTimeoutFS: NodeJS.Timeout | null = null;

const combinedHighlightedPoints = computed(() => {
  const combined = new Set<number>();
  for (const p of pointsToHighlightInScatter.value) combined.add(p);
  for (const p of selectedPointsFromNodesFullscreen.value) combined.add(p);
  return Array.from(combined);
});

function clearSelectionsFullscreen() {
  try {
    // Remove visual selection styling directly (no full re-render)
    // Dendrogram circles
    const dendrogramCircles = document.querySelectorAll('.node circle');
    dendrogramCircles.forEach((circle) => {
      const el = circle as SVGCircleElement;
      el.style.stroke = '#fff';
      el.style.strokeWidth = '2px';
      el.style.filter = '';
    });

    // Icicle rectangles
    const icicleRects = document.querySelectorAll('.icicle-cell rect');
    icicleRects.forEach((rect) => {
      const el = rect as SVGRectElement;
      el.style.stroke = '#ffffff';
      el.style.strokeWidth = '0.5px';
      el.style.filter = '';
    });

    // Clear selection state
    selectedNodesForFullscreen.value.clear();
    nodeIdToPointsFullscreen.value.clear();
    selectedPointsFromNodesFullscreen.value = [];
  } finally {
    if (selectionTimeoutFS) {
      clearTimeout(selectionTimeoutFS);
      selectionTimeoutFS = null;
    }
  }
}
const highlightedNodeInTree = ref<any>(null);
const evaluationMetrics = ref<any>(null);
const optimizationInfo = ref<any>(null);

const selectedXAxis = ref('feature-0'); // Default X-axis
const selectedYAxis = ref('feature-1'); // Default Y-axis
const selectedColorBy = ref('predicted');
const selectedOutlierStyle = ref('subtle'); // Default to subtle (black) // Default color by predicted clusters
const useSplitView = ref(false); // Split-view comparison toggle
const colorblindMode = ref(false); // Colorblind-friendly palette toggle

// Colors that represent special states and must NOT be remapped by colorblind mode
const PRESERVED_COLORS = new Set(['#000000', '#000', '#ff0000', '#cccccc', '#ccc']);

// Build a map from each cluster's original color -> a colorblind-safe color.
// Covers both predicted cluster colors and ground-truth colors so the swap is
// consistent across the scatter plot, tree views and split view.
const colorblindRemap = computed<Map<string, string>>(() => {
  const map = new Map<string, string>();
  if (!colorblindMode.value) return map;

  const data: any = clusterData.value;
  if (!data) return map;

  // Collect unique original colors in a stable order (predicted clusters first,
  // then ground-truth labels), skipping special/preserved colors.
  const originals: string[] = [];
  const seen = new Set<string>();
  const collect = (colorMap: Record<string, any> | undefined) => {
    if (!colorMap) return;
    const keys = Object.keys(colorMap).sort((a, b) => {
      const na = Number(a), nb = Number(b);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      return a < b ? -1 : a > b ? 1 : 0;
    });
    for (const key of keys) {
      const color = colorMap[key];
      if (typeof color !== 'string') continue;
      const norm = color.toLowerCase();
      if (PRESERVED_COLORS.has(norm) || seen.has(norm)) continue;
      seen.add(norm);
      originals.push(color);
    }
  };
  collect(data.color_map);
  collect(data.ground_truth?.color_map);

  const palette = getColorblindPalette(originals.length);
  originals.forEach((orig, i) => map.set(orig, palette[i % palette.length]));
  return map;
});

// Helper: remap a single color string through the colorblind map (identity if off)
const remapColor = (color: any): any => {
  if (typeof color !== 'string') return color;
  return colorblindRemap.value.get(color) || color;
};

// clusterData with colorblind-safe colors applied to the color-bearing fields.
// Only the color fields are rewritten; heavy fields (points, etc.) are shared.
const displayClusterData = computed(() => {
  const data: any = clusterData.value;
  if (!data || !colorblindMode.value || colorblindRemap.value.size === 0) return data;

  const remapMap = (cm: Record<string, any> | undefined) =>
    cm ? Object.fromEntries(Object.entries(cm).map(([k, v]) => [k, remapColor(v)])) : cm;
  const remapArr = (arr: any) =>
    Array.isArray(arr) ? arr.map(remapColor) : arr;

  const result: any = {
    ...data,
    color_map: remapMap(data.color_map),
    scatter_colors: remapArr(data.scatter_colors),
  };
  if (data.ground_truth) {
    result.ground_truth = {
      ...data.ground_truth,
      color_map: remapMap(data.ground_truth.color_map),
      colors: remapArr(data.ground_truth.colors),
    };
  }
  return result;
});

// Recursively remap any `color`/`colors`/`color_map` fields within tree data.
const deepRemapTreeColors = (node: any): any => {
  if (Array.isArray(node)) return node.map(deepRemapTreeColors);
  if (node && typeof node === 'object') {
    const out: any = {};
    for (const [key, value] of Object.entries(node)) {
      if (key === 'color') {
        out[key] = remapColor(value);
      } else if (key === 'colors' && Array.isArray(value)) {
        out[key] = value.map(remapColor);
      } else if (key === 'color_map' && value && typeof value === 'object') {
        out[key] = Object.fromEntries(
          Object.entries(value as Record<string, any>).map(([k, v]) => [k, remapColor(v)])
        );
      } else {
        out[key] = deepRemapTreeColors(value);
      }
    }
    return out;
  }
  return node;
};

// Computed properties for axis descriptions
const selectedXAxisLabel = computed(() => {
  const value = selectedXAxis.value;
  if (value.startsWith('feature-')) {
    const featureIndex = parseInt(value.replace('feature-', ''));
    if (featureNames.value[featureIndex]) {
      return featureNames.value[featureIndex];
    }
    return `Feature ${featureIndex}`;
  } else if (value === 'pca-0') {
    return 'PCA Component 1';
  } else if (value === 'pca-1') {
    return 'PCA Component 2';
  } else if (value === 'umap-0') {
    return 'UMAP Component 1';
  } else if (value === 'umap-1') {
    return 'UMAP Component 2';
  } else if (value === 'tsne-0') {
    return 't-SNE Component 1';
  } else if (value === 'tsne-1') {
    return 't-SNE Component 2';
  }
  return 'Unknown';
});

const selectedYAxisLabel = computed(() => {
  const value = selectedYAxis.value;
  if (value.startsWith('feature-')) {
    const featureIndex = parseInt(value.replace('feature-', ''));
    if (featureNames.value[featureIndex]) {
      return featureNames.value[featureIndex];
    }
    return `Feature ${featureIndex}`;
  } else if (value === 'pca-0') {
    return 'PCA Component 1';
  } else if (value === 'pca-1') {
    return 'PCA Component 2';
  } else if (value === 'umap-0') {
    return 'UMAP Component 1';
  } else if (value === 'umap-1') {
    return 'UMAP Component 2';
  } else if (value === 'tsne-0') {
    return 't-SNE Component 1';
  } else if (value === 'tsne-1') {
    return 't-SNE Component 2';
  }
  return 'Unknown';
});

// Ground truth availability check
const hasGroundTruth = computed(() => {
  return !!(clusterData.value?.ground_truth?.labels?.length);
});

// Computed tree data that changes colors based on selectedColorBy
const displayTreeData = computed(() => {
  if (!treeData.value) {
    console.log('[CLUSTERING-PAGE] No tree data available');
    return null;
  }
  
  console.log('[CLUSTERING-PAGE] Raw tree data:', {
    type: typeof treeData.value,
    hasRoot: !!(treeData.value && treeData.value.root),
    keys: treeData.value ? Object.keys(treeData.value) : []
  });
  
  // Parse tree data if it's a JSON string
  let parsedTree = treeData.value;
  if (typeof treeData.value === 'string') {
    try {
      parsedTree = JSON.parse(treeData.value);
      console.log('[CLUSTERING-PAGE] Parsed tree data from JSON string');
    } catch (e) {
      console.error('Error parsing tree data:', e);
      return null;
    }
  }
  
  // Apply colorblind-safe palette to tree node colors when enabled
  if (colorblindMode.value && colorblindRemap.value.size > 0) {
    return deepRemapTreeColors(parsedTree);
  }

  // Don't convert here - let the components handle the conversion
  // The components expect the raw tree data with a 'root' property
  console.log('[CLUSTERING-PAGE] Returning raw tree data for components');
  return parsedTree;
});

// Computed properties for split-view dimensions
const visualizationContainerWidth = computed(() => {
  return Math.max(1200, viewportWidth.value - 320); // Account for sidebar width
});

const visualizationContainerHeight = computed(() => {
  return Math.max(800, viewportHeight.value - 100); // Account for header/footer
});


// Layout and visibility controls
const showDendrogram = ref(true);
const showScatterPlot = ref(true);
const layoutMode = ref<'stacked' | 'side-by-side'>('stacked'); // Default to stacked
const dendrogramLayout = ref<'radial' | 'cartesian'>('cartesian');
const dendrogramPanelSize = ref(50); // Percentage for resizable panels
const scatterPanelSize = ref(50); // Percentage for resizable panels

// Tree visualization type selection
const treeVisualizationType = ref<'dendrogram' | 'icicle' | 'radial'>('icicle');
const treeVisualizationOptions = [
  { value: 'dendrogram', label: 'Dendrogram' },
  { value: 'icicle', label: 'Icicle Plot' },
];

// Tree content controls
const treeContentType = ref<'summarized' | 'real'>('summarized');
const realTreeDepth = ref(100);

const currentOperationId = ref<string | null>(null);


// Function to normalize column configuration to expected format
const normalizeColumnConfig = (rawColumnConfig: any[], headers: string[], featureColumns: number[] = [], labelColumns: number[] = []): any[] => {
  if (!rawColumnConfig || rawColumnConfig.length === 0) {
    // Reconstruct from headers if no column config exists
    console.log('[normalizeColumnConfig] Reconstructing column config from headers');
    return headers.map((header: string, index: number) => ({
      name: header,
      index: index,
      usage: featureColumns.includes(index) ? 'feature' : (labelColumns.includes(index) ? 'label' : 'ignore'),
      data_type: 'numeric',
      is_categorical: false,
      normalize: true
    }));
  }

  // Normalize existing column configuration
  return rawColumnConfig.map((col: any, index: number) => {
    // Handle different property name variations
    const name = col.name || `Column_${index}`;
    const colIndex = typeof col.index === 'number' ? col.index : index;
    const usage = col.usage || 'feature';
    const dataType = col.data_type || col.dataType || 'numeric';
    const isCategorical = col.is_categorical || col.isCategorical || false;
    const normalize = col.normalize !== undefined ? col.normalize : true;

    return {
      name,
      index: colIndex,
      usage,
      data_type: dataType,
      is_categorical: isCategorical,
      normalize
    };
  });
};

// Function to fetch uploaded file data by fileId
const fetchUploadedFileData = async (fileId: string): Promise<number[][] | null> => {
  try {
    console.log('[fetchUploadedFileData] Attempting to fetch data for fileId:', fileId);
    
    // Get the current dataset to extract processing configuration
    const currentDataset = globalState.currentDataset.value;
    if (!currentDataset) {
      console.error('[fetchUploadedFileData] No current dataset available');
      return null;
    }

    // Normalize column configuration to handle different formats
    const normalizedColumnConfig = normalizeColumnConfig(
      currentDataset.columnConfig || [],
      currentDataset.headers || [],
      currentDataset.featureColumns || [],
      currentDataset.labelColumns || []
    );

    console.log('[fetchUploadedFileData] Normalized column config:', normalizedColumnConfig);

    const processingConfig = {
      missing_value_strategy: (currentDataset.missingValueStrategy as 'keep' | 'remove' | 'fill_mean' | 'fill_median' | 'fill_zero' | 'fill_mode') || 'keep',
      normalization: (currentDataset.normalization as 'none' | 'standard' | 'minmax' | 'robust') || 'none',
      categorical_encoding: 'none' as const,
      feature_columns: Array.from(currentDataset.featureColumns || []),
      label_columns: Array.from(currentDataset.labelColumns || []),
      ignored_columns: Array.from(currentDataset.ignoredColumns || []),
      columns: normalizedColumnConfig
    };

    console.log('[fetchUploadedFileData] Using processing config:', processingConfig);
    console.log('[fetchUploadedFileData] Column config length:', processingConfig.columns.length);

    // Basic validation
    if (!processingConfig.columns || processingConfig.columns.length === 0) {
      console.error('[fetchUploadedFileData] Invalid column configuration - no columns defined');
      return null;
    }

    // Validate that each column has minimum required properties
    const validColumns = processingConfig.columns.every((col: any) => {
      return col && 
             typeof col.name === 'string' && 
             typeof col.index === 'number' && 
             ['feature', 'label', 'ignore'].includes(col.usage);
    });

    if (!validColumns) {
      console.error('[fetchUploadedFileData] Invalid column configuration after normalization');
      console.error('[fetchUploadedFileData] First invalid column:', processingConfig.columns.find((col: any) => !col || typeof col.name !== 'string' || typeof col.index !== 'number' || !['feature', 'label', 'ignore'].includes(col.usage)));
      return null;
    }

    // Call the processData API to get the processed data
    const response = await fileUploadAPI.processData(fileId, processingConfig);
    
    if (response && response.data) {
      console.log('[fetchUploadedFileData] Successfully fetched data:', response.data.length, 'rows');
      return response.data;
    } else {
      console.error('[fetchUploadedFileData] No data in response');
      return null;
    }
  } catch (error) {
    console.error('[fetchUploadedFileData] Error fetching file data:', error);
    
    // Provide more specific error information for debugging
    if (error.message && error.message.includes('422')) {
      console.error('[fetchUploadedFileData] Validation error (422) - likely column configuration issue');
    }
    return null;
  }
};


// Poll for clustering completion
const pollForClusteringCompletion = async (operationId: string): Promise<any | null> => {
  const maxAttempts = 3600; // 60 minutes at 1 second intervals
  let attempts = 0;
  let consecutiveErrors = 0;
  const maxConsecutiveErrors = 30;
  const startTime = Date.now();
  
  console.log(`[Clustering] Starting polling for operation ${operationId} at ${new Date().toISOString()}`);
  
  while (attempts < maxAttempts && currentOperationId.value === operationId) {
    try {
      const attemptStartTime = Date.now();
      console.log(`[Clustering] Polling attempt ${attempts + 1}/${maxAttempts} for operation ${operationId} (elapsed: ${((Date.now() - startTime) / 1000).toFixed(1)}s)`);
      
      // Add timeout to individual requests to prevent hanging
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minute timeout per request for large datasets
      
      const response = await fetch(`/api/cluster/status/${operationId}`, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        console.error(`[Clustering] Status check failed with HTTP ${response.status}`);
        throw new Error(`Status check failed: ${response.status}`);
      }
      
      const status = await response.json();
      console.log(`[Clustering] Status response:`, status);
      
      // Log additional details for completed responses
      if (status.status === 'completed' && status.result) {
        const result = status.result;
        console.log(`[Clustering] Result details:`, {
          points_count: result.points?.length || 0,
          features_count: result.points?.[0]?.length || 0,
          has_tree: !!result.tree,
          has_pca: !!result.dimensionality_reduction?.pca,
          has_umap: !!result.dimensionality_reduction?.umap,
          has_tsne: !!result.dimensionality_reduction?.tsne,
          pca_replaced: result._pca_replaced || false,
          original_features: result._original_features || 'N/A'
        });
      }
      
      // Reset consecutive errors on successful response
      consecutiveErrors = 0;
      
      if (status.status === 'completed') {
        console.log('[Clustering] Operation completed successfully, result received');
        console.log('[Clustering] Result keys:', Object.keys(status.result || {}));
        console.log('[Clustering] Result points length:', status.result?.points?.length);
        console.log('[Clustering] Result tree available:', !!status.result?.tree);
        return status.result;
      } else if (status.status === 'failed') {
        console.error('[Clustering] Operation failed:', status.error);
        
        // Check for SHiP errors (structured error objects)
        if (status.error && typeof status.error === 'object' && status.error.error_code) {
          const errorMsg = status.error.message || 'Operation failed';
          const suggestion = status.error.suggestion || 'Please try different parameters.';
          const shipError = new Error(`${errorMsg}. ${suggestion}`);
          shipError.shipError = status.error; // Attach structured error for better handling
          throw shipError;
        }
        
        // Handle string error messages or fallback
        const errorMessage = typeof status.error === 'string' ? status.error : 'Clustering operation failed';
        throw new Error(errorMessage);
      } else if (status.status === 'not_found') {
        console.error('[Clustering] Operation not found');
        consecutiveErrors++;
        
        // Give it a few more tries in case it's a temporary issue (e.g., backend restart)
        // But don't wait too long - if it's not found after 5 attempts, it's likely permanent
        if (attempts < 5) {
          console.warn('[Clustering] Operation not found, but still early - will retry');
        } else {
          // After 5 attempts, treat as permanent error
          throw new Error('Clustering operation not found. The operation may have failed or timed out. Please try starting a new clustering operation.');
        }
      } else if (status.status === 'running') {
        console.log(`[Clustering] Operation still running, elapsed: ${status.elapsed_time?.toFixed(2)}s`);
      } else {
        console.log(`[Clustering] Unknown status: ${status.status}`);
      }
      
      // Dynamic polling interval - start fast, then slow down
      let pollInterval = 1000; // Start with 1 second
      if (attempts > 30) pollInterval = 2000; // After 30 seconds, poll every 2 seconds
      if (attempts > 120) pollInterval = 5000; // After 2 minutes, poll every 5 seconds
      
      await new Promise(resolve => setTimeout(resolve, pollInterval));
      attempts++;
      
    } catch (error: any) {
      if (currentOperationId.value !== operationId) {
        // Operation was aborted
        console.log('[Clustering] Polling stopped due to abort');
        return null;
      }
      
      // Handle AbortError specifically - this is usually a timeout, not a permanent error
      if (error.name === 'AbortError') {
        console.warn(`[Clustering] Request timeout on attempt ${attempts + 1}, will retry`);
        // Don't increment consecutive errors for timeouts, just continue
      } else if (error.message && (error.message.includes('not found') || error.message.includes('operation failed') || error.message.includes('Tree generation failed') || error.message.includes('SHiP tree generation failed') || error.shipError)) {
        console.error('[Clustering] Permanent error - stopping polling:', error.message);
        throw error; // Re-throw immediately for permanent errors
      } else {
        consecutiveErrors++;
      }
      
      console.error(`[Clustering] Polling error on attempt ${attempts + 1} (consecutive errors: ${consecutiveErrors}):`, error);
      
      // If too many consecutive errors, give up
      if (consecutiveErrors >= maxConsecutiveErrors) {
        console.error(`[Clustering] Too many consecutive errors (${consecutiveErrors}), giving up`);
        throw new Error(`Polling failed after ${consecutiveErrors} consecutive errors. Last error: ${error.message}`);
      }
      
      // For network errors or timeouts, wait a bit longer before retrying
      const errorWaitTime = Math.min(2000 * consecutiveErrors, 10000); // Exponential backoff, max 10 seconds
      console.log(`[Clustering] Waiting ${errorWaitTime}ms before retry due to error`);
      await new Promise(resolve => setTimeout(resolve, errorWaitTime));
      attempts++;
    }
  }
  
  // Timeout
  console.error('[Clustering] Polling timeout reached after', attempts, 'attempts');
  throw new Error(`Clustering operation timed out`);
};

// Loading state for run operations
const isLoadingRun = ref(false);
const isRestoringRun = ref(false);

// User experience state
const datasetChangeNotification = ref<string | null>(null);
const showDatasetChangeNotification = ref(false);

// Function to show dataset change notifications
const showDatasetNotification = (message: string) => {
  datasetChangeNotification.value = message;
  showDatasetChangeNotification.value = true;
  
  // Auto-hide after 4 seconds
  setTimeout(() => {
    showDatasetChangeNotification.value = false;
  }, 4000);
};

// Store resize handler for cleanup
let resizeHandler: (() => void) | null = null;

const rawFeatureCount = computed(() => {
  // First, try to get count from global dataset state (most reliable)
  const currentDataset = globalState.currentDataset.value;
  if (currentDataset && currentDataset.featureCount && currentDataset.featureCount > 0) {
    console.log('[rawFeatureCount] Using global dataset featureCount:', currentDataset.featureCount);
    return currentDataset.featureCount;
  }
  
  // Fallback: get from uploaded data
  if (uploadedData.value && uploadedData.value.length > 0 && uploadedData.value[0]?.length > 0) {
    const count = uploadedData.value[0].length;
    console.log('[rawFeatureCount] Using uploaded data length:', count);
    return count;
  }
  
  // Fallback: get from cluster data original points
  if (clusterData.value?.original_points && clusterData.value.original_points.length > 0 && clusterData.value.original_points[0]?.length > 0) {
    const count = clusterData.value.original_points[0].length;
    console.log('[rawFeatureCount] Using cluster data original points length:', count);
    return count;
  } 
  
  // Fallback: get from cluster data points (when no DR was applied)
  if (clusterData.value?.points?.length > 0 && clusterData.value.points[0]?.length > 0 && (!clusterData.value.dimensionality_reduction || (!clusterData.value.dimensionality_reduction.pca && !clusterData.value.dimensionality_reduction.umap))){
    const count = clusterData.value.points[0].length;
    console.log('[rawFeatureCount] Using cluster data points length:', count);
    return count;
  }
  
  // Known sample data defaults
  const sampleDimensions: Record<string, number> = {
    'blobs': 2,
    'moons': 2,
    'circles': 2,
    'aniso': 2,
    'varied': 2,
    'nostructure': 2,
    'spiral': 2,
    'nested': 2,
    'elongated': 2,
    'dense_sparse': 2,
    'manifold': 2
  };
  
  if (selectedSample.value && sampleDimensions[selectedSample.value]) {
    console.log('[rawFeatureCount] Using sample dimensions for', selectedSample.value, ':', sampleDimensions[selectedSample.value]);
    return sampleDimensions[selectedSample.value];
  }
  
  console.log('[rawFeatureCount] No feature count found, returning 0');
  return 0;
});

const showFeatureAxisOptions = computed(() => {
  const count = rawFeatureCount.value;
  const shouldShow = count > 0 && count <= 50;
  console.log('[showFeatureAxisOptions] rawFeatureCount:', count, 'shouldShow:', shouldShow);
  return shouldShow;
});

const localFeatureNames = ref<string[]>([]);

// Hardcoded feature names for known sample datasets
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

// Add computed property for feature names (including real column names)
const featureNames = computed(() => {
  // Check hardcoded names first
  if (selectedSample.value && KNOWN_FEATURE_NAMES[selectedSample.value]) {
    return KNOWN_FEATURE_NAMES[selectedSample.value];
  }
  return datasetManager.getFeatureNames();
});

const quickStatsDisplay = computed(() => {
  const summary = datasetManager.datasetSummary.value;
  if (summary) {
    return {
      pointCount: summary.pointCount,
      featureCount: summary.featureCount
    };
  }
  
  // Fallback to manual calculation if dataset manager doesn't have data
  let pointCount = 0;
  if (uploadedData.value && uploadedData.value.length > 0) {
    pointCount = uploadedData.value.length;
  } else if (clusterData.value?.points?.length > 0) {
    pointCount = clusterData.value.points.length;
  } else if (clusterData.value?.original_points?.length > 0){
    pointCount = clusterData.value.original_points.length;
  }
  return {
    pointCount: pointCount,
    featureCount: rawFeatureCount.value
  };
});

const actualClusterCount = computed(() => {
  // Count unique cluster labels from the clustering results
  if (clusterData.value?.labels && Array.isArray(clusterData.value.labels)) {
    const uniqueLabels = new Set(clusterData.value.labels);
    return uniqueLabels.size;
  }
  // If no clustering results yet, return 0
  return 0;
});

// Ground truth cluster count
const groundTruthClusterCount = computed(() => {
  if (clusterData.value?.ground_truth?.unique_labels) {
    return clusterData.value.ground_truth.unique_labels.length;
  }
  return 0;
});

const featureCount = computed(() => {
  // This featureCount is specifically for populating axis selection options.
  // It should reflect the features of the data *currently being plotted* if it's raw data,
  // or the original features if DR data is being plotted (to allow switching back).
  return rawFeatureCount.value; // Keep this reflecting original features for consistency in dropdowns
});

const handleRunSelected = (runId: string) => {
  if (globalState.activeRunId.value === runId) {
    console.log('Run already active, skipping:', runId);
    return;
  }
  globalState.setActiveRun(runId);
};

// Handle auto-start clustering after tree import
const handleAutoStartClustering = async () => {
  console.log('[Clustering] Auto-start clustering triggered after tree import');
  
  // Wait a brief moment to ensure the run is fully loaded
  await nextTick();
  
  // Check if we have a valid dataset and parameters
  if (!hasValidDataset.value) {
    console.warn('[Clustering] Cannot auto-start clustering: no valid dataset');
    addToast('Cannot start clustering: no valid dataset loaded', 'warning');
    return;
  }
  
  if (!selectedTreeType.value || !selectedPartitionMethod.value) {
    console.warn('[Clustering] Cannot auto-start clustering: missing parameters');
    addToast('Cannot start clustering: missing tree type or partition method', 'warning');
    return;
  }
  
  // Check if clustering is already running
  if (isClusteringRunning.value) {
    console.log('[Clustering] Clustering already running, skipping auto-start');
    return;
  }
  
  console.log('[Clustering] Starting automatic clustering with parameters:', {
    treeType: selectedTreeType.value,
    partitionMethod: selectedPartitionMethod.value,
    k: selectedK.value,
    power: selectedPower.value,
    dataset: currentDatasetName.value
  });
  
  // Show notification about auto-start
  addToast('Automatically starting clustering after tree import...', 'info');
  
  // Trigger clustering
  try {
    await fetchClusters();
    console.log('[Clustering] Auto-start clustering completed successfully');
  } catch (error) {
    console.error('[Clustering] Auto-start clustering failed:', error);
    addToast('Auto-start clustering failed. You can manually start clustering using the Run button.', 'error');
  }
};

const resetVisualizationOptions = async (runData: any, features: string[]) => {
  console.log('[ResetViz] Resetting visualization options...');

  // Force refresh feature names to ensure they're up to date with current dataset
  await nextTick(); // Ensure reactive updates are complete
  console.log(`[ResetViz] Current feature names (${features.length}):`, features.slice(0, 5));

  const dr = runData.clusterData?.dimensionality_reduction;

  // 1. Completely reset axis selections to ensure clean state
  console.log('[ResetViz] Clearing previous axis selections...');
  selectedXAxis.value = '';
  selectedYAxis.value = '';
  
  await nextTick(); // Allow reactivity to process clearing

  // 2. Set new axis selections based on available data
  // Priority: t-SNE > PCA > UMAP > Features (t-SNE is the preferred default visualization)
  if (dr?.tsne && dr.tsne.length > 0) {
    selectedXAxis.value = 'tsne-0';
    selectedYAxis.value = 'tsne-1';
    console.log('[ResetViz] Setting axes to t-SNE (preferred default)');
  } else if (dr?.pca && dr.pca.length > 0) {
    selectedXAxis.value = 'pca-0';
    selectedYAxis.value = 'pca-1';
    console.log('[ResetViz] Setting axes to PCA');
  } else if (dr?.umap && dr.umap.length > 0) {
    selectedXAxis.value = 'umap-0';
    selectedYAxis.value = 'umap-1';
    console.log('[ResetViz] Setting axes to UMAP');
  } else if (features.length > 0) {
    selectedXAxis.value = 'feature-0';
    selectedYAxis.value = features.length > 1 ? 'feature-1' : 'feature-0';
    console.log(`[ResetViz] Setting axes to features: X=${features[0]}, Y=${features[1] || features[0]}`);
  } else {
    // Fallback if no data is available at all
    selectedXAxis.value = '';
    selectedYAxis.value = '';
    console.log('[ResetViz] No axes data available, clearing selection.');
  }

  // 3. Reset Color, Layout, and Visibility
  selectedColorBy.value = 'predicted';
  treeVisualizationType.value = 'icicle';
  layoutMode.value = 'stacked';
  dendrogramLayout.value = 'radial';
  showDendrogram.value = true;
  showScatterPlot.value = true;
  useSplitView.value = false;
  showInfoBar.value = true; // Show summary bar for context
  showMetrics.value = false; // Collapse metrics panel by default

  console.log(`[ResetViz] Visualization options reset complete. Final axes: X=${selectedXAxis.value}, Y=${selectedYAxis.value}`);
};

const validateDatasetMatch = (run: any, currentDataset: any): boolean => {
  console.log(`[DatasetMatch] Validating match between run dataset and current dataset`);
  
  // Special handling for imported runs - be more lenient
  const isImportedRun = run.parameters?.loadedFromComplete || run.parameters?.loadedFromTree;
  
  // Sample dataset matching
  if (currentDataset.type === 'sample' && run.parameters?.sample) {
    const sampleMatches = run.parameters.sample === currentDataset.sampleName;
    const sizeMatches = !run.parameters.n_samples || run.parameters.n_samples === currentDataset.n_samples;
    
    console.log(`[DatasetMatch] Sample: ${sampleMatches}, Size: ${sizeMatches}, IsImported: ${isImportedRun}`);
    
    // For imported runs, be more lenient - allow if sample type matches even if size differs slightly
    if (isImportedRun && sampleMatches) {
      console.log(`[DatasetMatch] Imported run with matching sample type - allowing load`);
      return true;
    }
    
    return sampleMatches && sizeMatches;
  }
  
  // Uploaded file matching with enhanced validation
  if (currentDataset.type === 'uploaded' && run.parameters?.datasetInfo?.type === 'uploaded') {
    const runDataset = run.parameters.datasetInfo;
  }
  
  // Imported dataset matching - also handle cases where run was created from imported data
  if (currentDataset.type === 'imported' && (run.parameters?.datasetInfo?.type === 'imported' || isImportedRun)) {
    const runDataset = run.parameters.datasetInfo || {};
    
    // Primary match: filename
    const nameMatches = runDataset.name === currentDataset.name || 
                       run.parameters.uploadedFileName === currentDataset.name;
    
    // Secondary validation: feature structure
    const featureCountMatches = !runDataset.featureCount || !currentDataset.featureCount || 
                               runDataset.featureCount === currentDataset.featureCount;
    
    // Tertiary validation: point count (allow some variance for different uploads of same file)
    const pointCountMatches = !runDataset.pointCount || !currentDataset.pointCount ||
                             Math.abs(runDataset.pointCount - currentDataset.pointCount) <= 1;
    
    // Header comparison (if both exist)
    const headersMatch = !runDataset.headers || !currentDataset.headers ||
                        JSON.stringify(runDataset.headers) === JSON.stringify(currentDataset.headers);
    
    console.log(`[DatasetMatch] Uploaded file - Name: ${nameMatches}, Features: ${featureCountMatches}, Points: ${pointCountMatches}, Headers: ${headersMatch}`);
    
    // Name must match, and at least one structural validation should pass
    return nameMatches && featureCountMatches && pointCountMatches && headersMatch;
  }
  
  // Fallback to legacy uploadedFileName check
  if (currentDataset.type === 'uploaded' && run.parameters?.uploadedFileName) {
    return run.parameters.uploadedFileName === currentDataset.name;
  }
  
  console.log(`[DatasetMatch] No matching criteria found`);
  return false;
};

const validateRunParameters = (run: any, currentDataset: any): { isValid: boolean; error?: string } => {
  console.log(`[LoadRun] Validating parameters for run ${run.id}`);
  
  // Check if run has required parameter structure
  if (!run.parameters) {
    return { isValid: false, error: 'Run has no parameters object' };
  }

  // Validate dataset compatibility for uploaded files
  if (run.parameters.datasetInfo?.type === 'uploaded' && currentDataset?.type === 'uploaded') {
    const runDataset = run.parameters.datasetInfo;
    // Check feature count compatibility
    if (runDataset.featureCount && currentDataset.featureCount && 
        runDataset.featureCount !== currentDataset.featureCount) {
      return { 
        isValid: false, 
        error: `Feature count mismatch: run has ${runDataset.featureCount}, current dataset has ${currentDataset.featureCount}` 
      };
    }
    
    // Check if headers are compatible (if both exist)
    if (runDataset.headers && currentDataset.headers && 
        JSON.stringify(runDataset.headers) !== JSON.stringify(currentDataset.headers)) {
      console.warn('[LoadRun] Header mismatch detected - may cause parameter issues');
    }
  }

  // Validate sample dataset compatibility
  if (run.parameters.sample && currentDataset?.type === 'sample') {
    if (run.parameters.sample !== currentDataset.sampleName) {
      return { 
        isValid: false, 
        error: `Sample mismatch: run uses '${run.parameters.sample}', current dataset is '${currentDataset.sampleName}'` 
      };
    }
  }

  // Check if essential parameters exist
  const requiredParams = ['treeType', 'partitionMethod', 'selectedK'];
  for (const param of requiredParams) {
    if (run[param] === undefined || run[param] === null) {
      return { isValid: false, error: `Missing required parameter: ${param}` };
    }
  }

  console.log(`[LoadRun] Parameter validation passed for run ${run.id}`);
  return { isValid: true };
};

const handleRunLoaded = async (run: any) => {
  if (isLoadingRun.value) {
    console.warn('Already loading a run, skipping new request for:', run.id);
    return;
  }
  console.log(`[LoadRun] Starting to load run ${run.id} for dataset "${run.dataset}"`);
  isLoadingRun.value = true;

  try {
    // STEP 0: RESTORE DATASET CONTEXT FIRST (before validation)
    console.log('[LoadRun] Step 0: Restoring dataset context for validation...');
    if (run.parameters.datasetInfo && run.parameters.datasetInfo.type === 'uploaded') {
      const datasetInfo = run.parameters.datasetInfo as DatasetInfo;
      // Ensure we include the fileId from the run parameters for uploaded datasets
      const fileIdSources = {
        runParametersFileId: run.parameters.fileId,
        datasetInfoFileId: datasetInfo.fileId,
        finalFileId: run.parameters.fileId || datasetInfo.fileId
      };
      
      console.log(`[LoadRun] FileId sources for dataset restoration:`, fileIdSources);
      
      const restoredDataset = {
        ...datasetInfo,
        fileId: run.parameters.fileId || datasetInfo.fileId
      };
      globalState.setDataset(restoredDataset);
      console.log(`[LoadRun] Restored uploaded dataset: ${datasetInfo.name} with fileId: ${restoredDataset.fileId}`);
    } else if (run.parameters.sample) {
      const sampleOption = globalState.getSampleOption(run.parameters.sample);
      if (sampleOption) {
        const datasetInfo: DatasetInfo = {
          name: sampleOption.label,
          type: 'sample',
          sampleName: run.parameters.sample,
          n_samples: run.parameters.n_samples || sampleOption.typical_samples,
          featureCount: sampleOption.dimensions,
          pointCount: run.parameters.n_samples || sampleOption.typical_samples,
          headers: Array.from({ length: sampleOption.dimensions }, (_, i) => `Feature ${i + 1}`)
        };
        globalState.setDataset(datasetInfo);
        console.log(`[LoadRun] Restored sample dataset: ${datasetInfo.name}`);
      }
    }

    await nextTick();

    // STEP 1: VALIDATE PARAMETERS AFTER DATASET RESTORATION
    console.log('[LoadRun] Step 1: Validating run parameters...');
    const currentDataset = globalState.currentDataset.value;
    const validation = validateRunParameters(run, currentDataset);
    
    if (!validation.isValid) {
      console.error(`[LoadRun] Parameter validation failed: ${validation.error}`);
      
      // Clear stored parameters that might be incompatible
      globalState.clearClusteringParameters();
      
      // Show user-friendly error instead of throwing
      console.warn(`[LoadRun] Validation failed but continuing with dataset restoration: ${validation.error}`);
      // Don't throw error - continue with loading but warn user
    }

    // STEP 2: FULL CLEANUP INCLUDING PARAMETERS
    console.log('[LoadRun] Step 2: Cleaning up previous state...');
    if (drPollingInterval) {
      clearInterval(drPollingInterval);
      drPollingInterval = null;
      console.log('[LoadRun] Stopped previous DR polling.');
    }
    
    // Reset all DR-related state to prevent stale polling
    currentClusterId.value = null;
    isLoadingDR.value = false;
    
    // Ensure no residual polling state
    if (currentClusterId.value) {
      console.log('[LoadRun] Clearing stale cluster ID:', currentClusterId.value);
      currentClusterId.value = null;
    }

    clusterData.value = { points: [], labels: [], centers: [], dimensionality_reduction: {} };
    treeData.value = null;
    evaluationMetrics.value = null;
    optimizationInfo.value = null;

    // Clear any stale clustering parameters before loading new ones
    globalState.clearClusteringParameters();
    let featureNamesForRun: string[] = [];
    if (currentDataset?.headers) {
      featureNamesForRun = currentDataset.headers;
    } else if (currentDataset?.featureCount) {
      featureNamesForRun = Array.from({ length: currentDataset.featureCount }, (_, i) => `Feature ${i + 1}`);
    }
    localFeatureNames.value = featureNamesForRun;

    console.log(`[LoadRun] Step 2 complete. Directly computed feature names for dataset "${currentDataset?.name}" (${featureNamesForRun.length}):`, featureNamesForRun.slice(0, 5));
    console.log(`[LoadRun] At step 2, global dataset featureCount is: ${currentDataset?.featureCount}`);

    // STEP 3: LOAD RUN-SPECIFIC DATA WITH PARAMETER VALIDATION
    console.log('[LoadRun] Step 3: Loading run-specific data...');
    
    // Validate and set parameters one by one with fallbacks
    selectedTreeType.value = run.treeType || 'complete';
    selectedPartitionMethod.value = run.partitionMethod || 'fixed_k';
    selectedK.value = run.selectedK || 2;
    selectedPower.value = run.selectedPower || 2;
    
    // Set validated parameters in global state
    globalState.setClusteringParameters({
      treeType: selectedTreeType.value,
      partitionMethod: selectedPartitionMethod.value,
      selectedK: selectedK.value,
      power: selectedPower.value
    });
    
    // Check if this is an imported run that needs fresh color data from backend
    const clusterBackendId = run.clusterData?.cluster_id;
    const isImportedRun = run.parameters?.loadedFromComplete || run.parameters?.loadedFromTree;
    
    if (isImportedRun && clusterBackendId) {
      console.log(`[LoadRun] Imported run detected, fetching fresh data with colors for cluster ${clusterBackendId}`);
      try {
        // Fetch fresh data from backend to get colors
        const response = await fetch(`/api/cluster/${clusterBackendId}/result`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
          const freshData = await response.json();
          
          // Update cluster data with fresh backend data including colors
          clusterData.value = {
            ...run.clusterData,
            scatter_colors: freshData.scatter_colors || run.clusterData.scatter_colors,
            color_map: freshData.color_map || run.clusterData.color_map,
            points: freshData.points || run.clusterData.points,
            labels: freshData.labels || run.clusterData.labels,
            centers: freshData.centers || run.clusterData.centers,
            dimensionality_reduction: freshData.dimensionality_reduction || run.clusterData.dimensionality_reduction
          };
          
          console.log(`[LoadRun] Refreshed imported run data with ${freshData.scatter_colors?.length || 0} colors`);
        } else {
          console.warn(`[LoadRun] Failed to fetch fresh data for imported run, using stored data`);
          clusterData.value = run.clusterData;
        }
      } catch (error) {
        console.warn(`[LoadRun] Error fetching fresh data for imported run:`, error);
        clusterData.value = run.clusterData;
      }
    } else {
      clusterData.value = run.clusterData;
    }
    
    treeData.value = run.treeData;
    evaluationMetrics.value = normalizeMetrics(run.metrics || null);
    console.log(`[LoadRun] Loaded data for run ${run.id}. Points: ${clusterData.value?.points?.length}`);

    // STEP 4: RESET VISUALIZATION OPTIONS
    console.log('[LoadRun] Step 4: Resetting visualization options...');
    await resetVisualizationOptions(run, featureNamesForRun);

    // STEP 5: RESTART BACKGROUND TASKS
    const backendClusterId = run.clusterData?.cluster_id;
    if (backendClusterId) {
      console.log(`[LoadRun] Step 5: Starting DR polling for new run ${run.id} using backend cluster_id ${backendClusterId}...`);
      startDimensionalityReductionPolling(backendClusterId);
    } else {
      console.warn(`[LoadRun] Step 5: Could not start DR polling for run ${run.id} - backend cluster_id not found.`);
    }

    console.log(`[LoadRun] Successfully finished loading run ${run.id}.`);

  } catch (error) {
    console.error(`[LoadRun] CRITICAL ERROR loading run ${run.id}:`, error);
    
    // Show user-friendly error message
    if (error instanceof Error) {
      // You might want to show this in a toast or modal instead
      alert(`Failed to load clustering run: ${error.message}`);
    }
    
    // Ensure we don't leave the system in a broken state
    globalState.setActiveRun(null);
  } finally {
    isLoadingRun.value = false;
  }
};

const currentSampleOptions = computed<SampleOption[]>(() => {
  if (uploadedFileName.value) {
    const uploadedFileOptionValue = UPLOADED_FILE_MARKER_PREFIX + uploadedFileName.value;
    return [{ value: uploadedFileOptionValue, label: uploadedFileName.value }];
  }
  return globalState.sampleOptions.value.map(opt => ({ ...opt }));
});

// Sample options are now managed globally via useGlobalState()

class ClusteringApiBridge {
  private baseUrl: string;
  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }
  async getClusters(params: any, abortSignal?: AbortSignal) {    try {
      // Use the colored endpoint to get tree with color properties
      console.log('[API] Sending request to backend at:', new Date().toISOString());
      const fetchStartTime = performance.now();
      
      const res = await fetch(`${this.baseUrl}/api/cluster/colored`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal: abortSignal
      });
      
      const fetchEndTime = performance.now();
      console.log('[API] Fetch completed at:', new Date().toISOString());
      console.log('[API] Fetch took:', (fetchEndTime - fetchStartTime).toFixed(2), 'ms');
      
      if (!res.ok) {
        const errorBody = await res.text();
        console.error('Backend error response:', errorBody);
        throw new Error(`Failed to fetch clustering data. Status: ${res.status}. Message: ${errorBody}`);
      }
      
      console.log('[API] Starting JSON parsing at:', new Date().toISOString());
      const jsonStartTime = performance.now();
      
      const result = await res.json();
      
      const jsonEndTime = performance.now();
      console.log('[API] JSON parsing completed at:', new Date().toISOString());
      console.log('[API] JSON parsing took:', (jsonEndTime - jsonStartTime).toFixed(2), 'ms');
      
      return result;
    } catch (err) {
      console.error('Error in getClusters API call:', err);
      throw err;
    }
  }
}
const clusteringApi = new ClusteringApiBridge();

// Watch for changes in global dataset state
watch(() => globalState.currentDataset.value, (newDataset, oldDataset) => {
  console.log('Global dataset changed, syncing local state:', newDataset);
  
  if (newDataset) {
    // If the dataset changed to a different dataset, clear the active run to prevent conflicts
    // BUT only if we're not currently loading a run
    // Check name, type, and n_samples to detect toy dataset size changes
    const isDatasetChanged = oldDataset && (
      oldDataset.name !== newDataset.name || 
      oldDataset.type !== newDataset.type || 
      (newDataset.type === 'sample' && oldDataset.n_samples !== newDataset.n_samples) ||
      (newDataset.type === 'uploaded' && oldDataset.fileName !== newDataset.fileName) ||
      oldDataset.pointCount !== newDataset.pointCount
    );
    
    if (isDatasetChanged) {
      // Check if we're loading a run and the new dataset matches the run being loaded
      const currentActiveRun = globalState.activeRun.value;
      const isRestoringDatasetForRun = (isLoadingRun.value || isRestoringRun.value) && currentActiveRun && 
        (currentActiveRun.dataset === newDataset.name.toLowerCase() || 
         currentActiveRun.dataset === newDataset.sampleName ||
         currentActiveRun.dataset === newDataset.name ||
         (currentActiveRun.parameters?.sample === newDataset.sampleName) ||
         (currentActiveRun.parameters?.loadedFromComplete && currentActiveRun.dataset.toLowerCase() === newDataset.sampleName));
      
      // Check if this is just a size change for the same dataset type
      const isSizeChangeOnly = oldDataset.name === newDataset.name && 
        oldDataset.type === newDataset.type && 
        newDataset.type === 'sample' &&
        oldDataset.n_samples !== newDataset.n_samples;
      
      // Don't clear active run if we're loading/restoring a run or just restoring a dataset for a run being loaded
      if (!isLoadingRun.value && !isRestoringRun.value && !isRestoringDatasetForRun) {
        console.log('Dataset changed, clearing active run and results to prevent conflicts:', {
          oldName: oldDataset.name,
          newName: newDataset.name,
          oldType: oldDataset.type,
          newType: newDataset.type,
          oldSamples: oldDataset.n_samples,
          newSamples: newDataset.n_samples,
          oldPointCount: oldDataset.pointCount,
          newPointCount: newDataset.pointCount
        });
        globalState.clearActiveRun();
        // Clear existing results completely
        clusterData.value = { points: [], labels: [], centers: [], dimensionality_reduction: { pca: null, umap: null, tsne: null } };
        treeData.value = null;
        evaluationMetrics.value = null;
        optimizationInfo.value = null;
        showMetrics.value = false;
        actualClusterCount.value = 0;
        
        // Show appropriate notification based on change type
        if (isSizeChangeOnly) {
          showDatasetNotification(`Dataset size changed to ${newDataset.n_samples} samples. Previous clustering results cleared.`);
        } else {
          const datasetName = newDataset.type === 'sample' ? newDataset.name : (newDataset.fileName || newDataset.name);
          showDatasetNotification(`Dataset changed to "${datasetName}". Previous clustering results cleared.`);
        }
      } else {
        console.log('Dataset changed while loading run - skipping clear to allow run loading:', {
          isLoadingRun: isLoadingRun.value,
          isRestoringRun: isRestoringRun.value,
          isRestoringDatasetForRun: isRestoringDatasetForRun,
          currentActiveRun: currentActiveRun?.dataset,
          newDatasetName: newDataset.name,
          newDatasetSampleName: newDataset.sampleName
        });
      }
    }
    
    if (newDataset.type === 'sample') {
      selectedSample.value = newDataset.sampleName || newDataset.name.toLowerCase();
      uploadedData.value = null;
      uploadedFileName.value = null;
      
      // Ensure sample datasets have proper headers if not already set
      const sampleName = newDataset.sampleName || newDataset.name.toLowerCase();
      
      // Use hardcoded feature names for known datasets
      if (KNOWN_FEATURE_NAMES[sampleName]) {
        localFeatureNames.value = KNOWN_FEATURE_NAMES[sampleName];
        if (!newDataset.headers || newDataset.headers.every((h: string) => /^Feature[_ ]\d+$/i.test(h))) {
          const updatedDataset: DatasetInfo = {
            name: newDataset.name,
            type: newDataset.type,
            sampleName: newDataset.sampleName,
            n_samples: newDataset.n_samples,
            headers: KNOWN_FEATURE_NAMES[sampleName],
            featureCount: KNOWN_FEATURE_NAMES[sampleName].length
          };
          globalState.setDataset(updatedDataset);
        }
      } else if (!newDataset.headers) {
        // Get dimensions from global state sampleOptions instead of hardcoded mapping
        const sampleOption = globalState.sampleOptions.find(opt => opt.value === sampleName);
        const dimensions = sampleOption?.dimensions || 2;
        const headers = Array.from({ length: dimensions }, (_, i) => `Feature ${i + 1}`);
        localFeatureNames.value = headers;
        
        // Update the global dataset with headers
        const updatedDataset: DatasetInfo = {
          name: newDataset.name,
          type: newDataset.type,
          sampleName: newDataset.sampleName,
          n_samples: newDataset.n_samples,
          headers,
          featureCount: dimensions
        };
        globalState.setDataset(updatedDataset);
      } else {
        localFeatureNames.value = newDataset.headers;
      }
    } else if (newDataset.type === 'uploaded' && newDataset.data) {
      uploadedData.value = newDataset.data.map(row => [...row]);
      uploadedFileName.value = newDataset.fileName || newDataset.name;
      selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + (newDataset.fileName || newDataset.name);
    } else if (newDataset.type === 'imported' && newDataset.data) {
      // Handle imported datasets - treat them like uploaded data
      uploadedData.value = newDataset.data.map(row => [...row]);
      uploadedFileName.value = newDataset.fileName || newDataset.name;
      selectedSample.value = UPLOADED_FILE_MARKER_PREFIX + (newDataset.fileName || newDataset.name);
    }
  } else {
    // Dataset cleared - clear all associated state
    console.log('Dataset cleared, resetting all state');
    selectedSample.value = null;
    uploadedData.value = null;
    uploadedFileName.value = null;
    
    // Also clear clustering results when dataset is removed
    clusterData.value = { points: [], labels: [], centers: [], dimensionality_reduction: { pca: null, umap: null, tsne: null } };
    treeData.value = null;
    evaluationMetrics.value = null;
    optimizationInfo.value = null;
    showMetrics.value = false;
    actualClusterCount.value = 0;
    globalState.clearActiveRun();
  }
}, { immediate: true });

// Watch for parameter changes and save to global state for persistence
watch([selectedTreeType, selectedPartitionMethod, selectedPower, selectedK], 
  ([newTreeType, newPartitionMethod, newPower, newK]) => {
    // Save current parameters to global state
    const currentParams = {
      treeType: newTreeType,
      partitionMethod: newPartitionMethod,
      power: newPower,
      selectedK: newK
    };
    
    // Only update if parameters have actually changed to avoid infinite loops
    const existing = globalState.clusteringParameters.value;
    if (!existing || 
        existing.treeType !== newTreeType || 
        existing.partitionMethod !== newPartitionMethod || 
        existing.power !== newPower || 
        existing.selectedK !== newK) {
      
      console.log('[Clustering] Saving parameters to global state:', currentParams);
      globalState.setClusteringParameters(currentParams);
      
      // Ensure uploaded data is synchronized when parameters change
      const currentDataset = globalState.currentDataset.value;
      if (currentDataset && (currentDataset.type === 'uploaded' || currentDataset.type === 'imported') && currentDataset.data) {
        if (!uploadedData.value || uploadedData.value.length === 0) {
          uploadedData.value = currentDataset.data.map(row => [...row]);
          console.log('[Clustering] Synchronized uploaded/imported data from global state:', uploadedData.value.length, 'rows');
        }
      }
    }
  }, 
  { deep: false } // Don't need deep watching for primitive values
);

// Watch for outlier style changes and force re-render of visualizations
watch(selectedOutlierStyle, (newStyle) => {
  // Force re-render of scatter plot and tree components by updating their keys
  // This ensures the outlier styling is applied immediately without re-running clustering
  console.log('[Clustering] Outlier style changed to:', newStyle);
  
  // The key changes in the template will automatically trigger re-renders
  // since the keys include selectedOutlierStyle
}, { immediate: false });

watch(showFeatureAxisOptions, (show) => {
  if (!show) {
    selectedXAxis.value = 'pca-0';
    selectedYAxis.value = 'pca-1';
  }
});

// Lazy polling function for dimensionality reduction (UMAP/t-SNE)
// Starts 2 seconds after clustering completes, polls every 5 seconds
// Non-blocking and runs in background without affecting main UI
const startDimensionalityReductionPolling = (clusterId: string) => {
  // Prevent duplicate polling sessions
  if (drPollingInterval) {
    console.log('[Clustering] Stopping existing DR polling before starting new one');
    clearInterval(drPollingInterval);
    drPollingInterval = null;
  }
  
  // Early termination if DR data already exists
  if (clusterData.value?.dimensionality_reduction?.umap && clusterData.value?.dimensionality_reduction?.tsne) {
    console.log('[Clustering] DR data already available, skipping polling');
    return;
  }
  
  // Validate cluster ID
  if (!clusterId || clusterId.trim() === '') {
    console.warn('[Clustering] Invalid cluster ID provided for DR polling:', clusterId);
    return;
  }
  
  currentClusterId.value = clusterId;
  let pollingAttempts = 0;
  const maxPollingAttempts = 120; // 10 minutes at 5-second intervals
  let consecutiveErrors = 0;
  const maxConsecutiveErrors = 3;
  
  // Start in background after a short delay to avoid blocking main clustering display
  setTimeout(() => {
    isLoadingDR.value = true;
    console.log('[Clustering] Starting lazy background polling for cluster:', clusterId);
    
    // Don't block UI - poll in background without affecting main interface
    drPollingInterval = setInterval(async () => {
      try {
        // Stop polling if cluster ID changed (new clustering started)
        if (currentClusterId.value !== clusterId) {
          console.log('[Clustering] Stopping DR polling - cluster ID changed from', clusterId, 'to', currentClusterId.value);
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          return;
        }
        
        // Early termination if DR data already exists (prevents redundant polling)
        if (clusterData.value?.dimensionality_reduction?.umap && clusterData.value?.dimensionality_reduction?.tsne) {
          console.log('[Clustering] DR data already complete, stopping polling');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          return;
        }
        
        pollingAttempts++;
        if (pollingAttempts > maxPollingAttempts) {
          console.warn('[Clustering] DR polling timeout - stopping after', maxPollingAttempts, 'attempts');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          return;
        }
        
        // Check status with fetch (not $fetch) to avoid Nuxt overhead
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 second timeout
        
        const statusResponse = await fetch(`/api/cluster/${clusterId}/dimensionality-reduction/status`, {
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!statusResponse.ok) {
          throw new Error(`Status check failed: ${statusResponse.status}`);
        }
        
        const statusData = await statusResponse.json();
        console.log(`[Clustering] DR status check ${pollingAttempts}/${maxPollingAttempts}:`, statusData);
        
        // Reset consecutive errors on successful response
        consecutiveErrors = 0;
      
        if (statusData.status === 'completed') {
          // Get results using regular fetch for consistency
          const resultController = new AbortController();
          const resultTimeoutId = setTimeout(() => resultController.abort(), 8000);
          
          const resultResponse = await fetch(`/api/cluster/${clusterId}/dimensionality-reduction/result`, {
            signal: resultController.signal
          });
          
          clearTimeout(resultTimeoutId);
          
          if (!resultResponse.ok) {
            throw new Error(`Result fetch failed: ${resultResponse.status}`);
          }
          
          const resultData = await resultResponse.json();
          console.log('[Clustering] DR results received:', {
            hasUmap: !!resultData.umap,
            hasTsne: !!resultData.tsne,
            umapStatus: resultData.umap_status,
            tsneStatus: resultData.tsne_status
          });
        
          if (resultData && !resultData.error) {
            // Batch dimensionality reduction updates to prevent multiple re-renders
            await nextTick();
            if (clusterData.value?.dimensionality_reduction) {
              if (resultData.umap && resultData.umap_status === 'completed') {
                clusterData.value.dimensionality_reduction.umap = resultData.umap;
                console.log('[Clustering] Added UMAP to clusterData');
              }
              if (resultData.tsne && resultData.tsne_status === 'completed') {
                clusterData.value.dimensionality_reduction.tsne = resultData.tsne;
                console.log('[Clustering] Added t-SNE to clusterData');
              }
              
              // Force reactivity update
              clusterData.value = { ...clusterData.value };
            }
          }
        
          // Stop polling - task completed
          console.log('[Clustering] UMAP/t-SNE polling completed successfully - stopping');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
          return; // Exit the polling function
        
        } else if (statusData.status === 'failed') {
          console.error('[Clustering] Dimensionality reduction failed:', statusData.error || 'Unknown error');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
        } else if (statusData.status === 'not_found') {
          console.warn('[Clustering] Dimensionality reduction task not found for cluster:', clusterId);
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
        } else if (statusData.status === 'not_started') {
          console.log('[Clustering] Dimensionality reduction not started yet for cluster:', clusterId);
          // Keep polling - it might start soon
        } else if (statusData.status === 'completed' && 
                   (statusData.umap_status === 'skipped' && statusData.tsne_status === 'skipped')) {
          console.log('[Clustering] UMAP/t-SNE skipped for 2D data');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
        } else if (statusData.status === 'processing') {
          // Log progress if available
          if (statusData.progress_percent !== undefined) {
            console.log(`[Clustering] DR progress: ${statusData.progress_percent}% (UMAP: ${statusData.umap_status}, t-SNE: ${statusData.tsne_status})`);
          }
          
          // Check for partial results - fetch results even if still processing
          try {
            const resultController = new AbortController();
            const resultTimeoutId = setTimeout(() => resultController.abort(), 5000);
            
            const resultResponse = await fetch(`/api/cluster/${clusterId}/dimensionality-reduction/result`, {
              signal: resultController.signal
            });
            
            clearTimeout(resultTimeoutId);
            
            if (resultResponse.ok) {
              const resultData = await resultResponse.json();
              
              // Apply partial results if available
              if (resultData && !resultData.error && clusterData.value?.dimensionality_reduction) {
                let updated = false;
                
                if (resultData.umap && resultData.umap_status === 'completed' && !clusterData.value.dimensionality_reduction.umap) {
                  clusterData.value.dimensionality_reduction.umap = resultData.umap;
                  console.log('[Clustering] Added partial UMAP result to clusterData');
                  updated = true;
                }
                
                if (resultData.tsne && resultData.tsne_status === 'completed' && !clusterData.value.dimensionality_reduction.tsne) {
                  clusterData.value.dimensionality_reduction.tsne = resultData.tsne;
                  console.log('[Clustering] Added partial t-SNE result to clusterData');
                  updated = true;
                }
                
                if (updated) {
                  // Force reactivity update
                  clusterData.value = { ...clusterData.value };
                }
              }
            }
          } catch (partialError) {
            console.warn('[Clustering] Failed to fetch partial DR results:', partialError);
          }
        }
        // Continue polling if status is 'processing' or other intermediate status
      
      } catch (error: any) {
        consecutiveErrors++;
        console.error(`[Clustering] DR polling error ${consecutiveErrors}/${maxConsecutiveErrors}:`, error.message);
        
        // Stop polling if too many consecutive errors
        if (consecutiveErrors >= maxConsecutiveErrors) {
          console.error('[Clustering] Too many consecutive DR polling errors - stopping');
          clearInterval(drPollingInterval!);
          drPollingInterval = null;
          isLoadingDR.value = false;
        }
      }
    }, 5000); // Poll every 5 seconds for lazy loading
  }, 2000); // Start polling after 2 second delay to let main clustering finish
};

// Event handlers for sidebar
// Data upload handling is now done on the upload page

// Abort clustering function
const abortClustering = async () => {
  if (currentOperationId.value) {
    try {
      // Call backend abort endpoint to kill the process
      await fetch(`/api/abort/${currentOperationId.value}`, {
        method: 'POST'
      });
      console.log('[Clustering] Backend process abort requested');
    } catch (error) {
      console.error('[Clustering] Failed to abort backend process:', error);
    }
  }
  
  // Also cancel frontend request if still active
  if (clusteringAbortController.value) {
    clusteringAbortController.value.abort();
    clusteringAbortController.value = null;
  }
  
  // Reset state
  isClusteringRunning.value = false;
  currentOperationId.value = null;
  addToast('Clustering operation was aborted', 'warning');
};

const fetchClusters = async () => {
  if (!selectedTreeType.value || !selectedPartitionMethod.value) {
    addToast('Please ensure a tree type and partition method are selected.', 'error');
    return;
  }
  
  // Warn if using BallTree/KDTree with high-dimensional data
  const featureCount = globalState.currentDataset.value?.featureCount || 0;
  const spatialTrees = ['BallTree', 'KDTree'];
  if (spatialTrees.includes(selectedTreeType.value) && featureCount > 50) {
    addToast(
      `Warning: ${selectedTreeType.value} performs poorly with high-dimensional data (${featureCount} features). Consider using DCTree or CoverTree instead.`,
      'warning'
    );
  }

  // Set loading state and create abort controller
  isClusteringRunning.value = true;
  clusteringAbortController.value = new AbortController();

  try {
    // Memory check - prevent loading extremely large datasets in browser
    if (uploadedData.value && uploadedData.value.length > 100000) {
      const proceed = confirm(
        `Large dataset detected (${uploadedData.value.length.toLocaleString()} points). ` +
        `This may use significant memory. Continue?`
      );
      if (!proceed) {
        isClusteringRunning.value = false;
        return;
      }
    }
    
    // Set K value based on partition method
    const effectiveK = selectedPartitionMethod.value === 'K' ? selectedK.value : 5;
    
    let params: any = {
      n_clusters: effectiveK,
      random_state: 42,
      treeType: selectedTreeType.value,
      partitioningMethod: selectedPartitionMethod.value,
      power: selectedPower.value,
      // Tree visualization parameters
      treeVisualizationType: treeContentType.value,
      realTreeDepth: realTreeDepth.value,
      // Outlier visualization style
      outlier_style: selectedOutlierStyle.value
    };
    
    console.log('[Clustering] Preparing parameters:', {
      effectiveK,
      treeType: selectedTreeType.value,
      partitioningMethod: selectedPartitionMethod.value,
      power: selectedPower.value,
      treeVisualizationType: treeContentType.value,
      realTreeDepth: realTreeDepth.value,
      isManualK: selectedPartitionMethod.value === 'K'
    });
    
    let sourcePointsForStats: number[][] | null = null;
    
    // Use global state to determine data source
    const currentDataset = globalState.currentDataset.value;
    if (!currentDataset) {
      alert('Please select a sample dataset or upload a file.');
      isClusteringRunning.value = false;
      return;
    }
    
    // Debug logging for dataset state
    console.log('[Clustering] fetchClusters called with dataset:', {
      name: currentDataset.name,
      type: currentDataset.type,
      hasFileId: !!currentDataset.fileId,
      fileId: currentDataset.fileId,
      hasData: !!currentDataset.data,
      dataLength: currentDataset.data?.length
    });
    
    // Additional debug logging for uploaded datasets
    if (currentDataset.type === 'uploaded') {
      const activeRun = globalState.activeRun.value;
      console.log('[Clustering] Uploaded dataset debug info:', {
        datasetFileId: currentDataset.fileId,
        datasetFileName: currentDataset.fileName,
        hasActiveRun: !!activeRun,
        activeRunId: activeRun?.id,
        activeRunFileId: activeRun?.parameters?.fileId,
        activeRunDatasetInfo: activeRun?.parameters?.datasetInfo,
        uploadedDataLength: uploadedData.value?.length
      });
    }
    
    if (currentDataset.type === 'uploaded' || currentDataset.type === 'imported') {
      // Handle uploaded/imported data - prioritize global state over local state
      let dataToUse: number[][] | null = uploadedData.value;
      
      // If local state is empty, use global state data
      if (!dataToUse || dataToUse.length === 0) {
        if (currentDataset.data && currentDataset.data.length > 0) {
          // Create a mutable copy of the readonly data
          dataToUse = currentDataset.data.map(row => [...row]);
          uploadedData.value = dataToUse; // Sync local state
          console.log('[Clustering] Using data from global state:', dataToUse.length, 'rows');
        } else {
          // IMMEDIATE DATA FETCH APPROACH
          // Check if we have an active run with a fileId to fetch data
          const activeRun = globalState.activeRun.value;
          let fileIdToUse = null;
          
          // First check if active run has fileId
          if (activeRun && activeRun.parameters.fileId) {
            fileIdToUse = activeRun.parameters.fileId;
            console.log('[Clustering] Using fileId from active run:', fileIdToUse);
          }
          // If no fileId in active run, check if current dataset has fileId  
          else if (currentDataset && currentDataset.fileId) {
            fileIdToUse = currentDataset.fileId;
            console.log('[Clustering] Using fileId from current dataset:', fileIdToUse);
          }
          
          // Debug logging to understand the state
          console.log('[Clustering] Debug - Current dataset state:', {
            hasDataset: !!currentDataset,
            datasetType: currentDataset?.type,
            hasFileId: !!currentDataset?.fileId,
            fileId: currentDataset?.fileId,
            hasActiveRun: !!activeRun,
            activeRunFileId: activeRun?.parameters?.fileId,
            finalFileIdToUse: fileIdToUse
          });
          
          // Additional fallback strategies for fileId retrieval
          if (!fileIdToUse && activeRun && activeRun.parameters) {
            // Try to get fileId from run parameters as backup
            if (activeRun.parameters.fileId) {
              fileIdToUse = activeRun.parameters.fileId;
              console.log('[Clustering] Using fileId from run parameters as fallback:', fileIdToUse);
            }
            // Check if fileId is in the datasetInfo within run parameters
            else if (activeRun.parameters.datasetInfo && activeRun.parameters.datasetInfo.fileId) {
              fileIdToUse = activeRun.parameters.datasetInfo.fileId;
              console.log('[Clustering] Using fileId from run datasetInfo as fallback:', fileIdToUse);
            }
          }
          
          // Ultimate fallback - check if we can restore from uploaded/imported filename
          if (!fileIdToUse && currentDataset?.fileName && (currentDataset.type === 'uploaded' || currentDataset.type === 'imported')) {
            console.log('[Clustering] No fileId found, dataset info:', {
              fileName: currentDataset.fileName,
              type: currentDataset.type,
              name: currentDataset.name
            });
            // This is a critical issue - uploaded dataset without fileId cannot be processed
            console.error('[Clustering] Critical issue: Uploaded dataset has no fileId for backend processing');
            
            // Provide user feedback
            alert(`Cannot change parameters for this dataset. The uploaded file "${currentDataset.fileName}" is no longer available on the server. Please upload the file again to continue clustering.`);
            isClusteringRunning.value = false;
            return;
          }
          
          if (fileIdToUse) {
            console.log('[Clustering] Data not available, attempting immediate fetch with fileId:', fileIdToUse);
            
            // Try to fetch the data immediately with a more robust approach
            try {
              console.log('[Clustering] Calling fetchUploadedFileData with fileId:', fileIdToUse);
              const fetchedData = await fetchUploadedFileData(fileIdToUse);
              console.log('[Clustering] fetchUploadedFileData response:', {
                hasData: !!fetchedData,
                dataLength: fetchedData?.length,
                dataType: typeof fetchedData
              });
              
              if (fetchedData && fetchedData.length > 0) {
                dataToUse = fetchedData;
                uploadedData.value = dataToUse;
                
                // Update the global state with the fetched data
                // IMPORTANT: Maintain all original dataset properties to preserve SHiP object consistency
                const updatedDatasetInfo = {
                  ...currentDataset,
                  data: dataToUse as number[][],
                  pointCount: dataToUse.length,
                  featureCount: dataToUse[0]?.length || 0,
                  fileId: fileIdToUse,  // Ensure fileId is preserved
                  // Preserve all original preprocessing information for SHiP consistency
                  originalData: (currentDataset.originalData || dataToUse) as number[][],
                  hasHeaders: currentDataset.hasHeaders ?? true,
                  missingValueStrategy: currentDataset.missingValueStrategy || 'keep',
                  normalization: currentDataset.normalization || 'none',
                  featureColumns: currentDataset.featureColumns,
                  labelColumns: currentDataset.labelColumns,
                  columnConfig: currentDataset.columnConfig,
                  dataConfig: currentDataset.dataConfig
                };
                globalState.setDataset(updatedDatasetInfo);
                
                console.log('[Clustering] Successfully fetched and set data before clustering:', dataToUse.length, 'rows');
                console.log('[Clustering] Updated global dataset state with fetched data and preserved SHiP consistency');
              } else {
                console.error('[Clustering] Failed to fetch data - empty response');
                alert('Unable to load uploaded file data. The file may no longer be available on the server.');
                isClusteringRunning.value = false;
                return;
              }
            } catch (error) {
              console.error('[Clustering] Error fetching file data:', error);
              alert('Error loading uploaded file data. Please try uploading the file again.');
              isClusteringRunning.value = false;
              return;
            }
          } else {
            console.error('[Clustering] No fileId available - cannot fetch data');
            alert(`Cannot process clustering request. The uploaded file "${currentDataset?.fileName || 'unknown'}" is no longer available on the server. Please upload the file again to continue clustering.`);
            isClusteringRunning.value = false;
            return;
          }
        }
      }
      
      // Ensure dataToUse is not null before using it
      if (!dataToUse) {
        alert('No data available for clustering.');
        isClusteringRunning.value = false;
        return;
      }
      
      params.data = dataToUse;
      params.n_samples = dataToUse.length;
      sourcePointsForStats = dataToUse;
      
      // Add preprocessing information
      params.isPreprocessed = true;
      params.featureHeaders = currentDataset.headers;
      params.dataConfig = currentDataset.dataConfig;
      
      // Add fileId for backend processing if available
      if (currentDataset.fileId) {
        params.fileId = currentDataset.fileId;
        console.log('[Clustering] Using backend file processing with fileId:', currentDataset.fileId);
      } else {
        // If no fileId in current dataset, check active run
        const activeRun = globalState.activeRun.value;
        if (activeRun && activeRun.parameters.fileId) {
          params.fileId = activeRun.parameters.fileId;
          console.log('[Clustering] Using backend file processing with fileId from active run:', activeRun.parameters.fileId);
        }
      }
      
      // Log comprehensive dataset info for debugging
      console.log('[Clustering] Dataset info for backend:', {
        name: currentDataset.name,
        fileId: currentDataset.fileId,
        hasData: !!currentDataset.data,
        dataRows: currentDataset.data?.length || 0,
        backendProcessed: currentDataset.backendProcessed,
        paramFileId: params.fileId,
        hasHeaders: currentDataset.hasHeaders,
        normalization: currentDataset.normalization
      });
      
      if (currentDataset.groundTruthColumn !== undefined) {
        params.groundTruthColumn = currentDataset.groundTruthColumn;
      }

      // Add label data for ARI calculation if available
      if (currentDataset.labelColumns && currentDataset.labelColumns.length > 0) {
        const labelColumnIndex = currentDataset.labelColumns[0]; // Use first label column
        if (currentDataset.originalData && 
            currentDataset.originalData.length > 0 && 
            currentDataset.originalData[0] && 
            labelColumnIndex < currentDataset.originalData[0].length) {
          // Extract label data from original data
          const labelData = currentDataset.originalData.map(row => row[labelColumnIndex]);
          params.labelColumns = currentDataset.labelColumns;
          params.labelData = labelData;
          console.log('[Clustering] Adding ground truth labels for ARI calculation:', labelData.slice(0, 5), '...');
        }
      }
      
      console.log('[Clustering] Sending preprocessed data with configuration:', params.dataConfig);
      
    } else if (currentDataset.type === 'sample') {
      // Handle sample data
      params.sample = currentDataset.sampleName || currentDataset.name.toLowerCase();
      params.n_samples = currentDataset.n_samples || 200;
      console.log('[Clustering] Using sample data:', params.sample, 'with', params.n_samples, 'samples');
      
    } else if (currentDataset.type === 'imported') {
      // Handle imported datasets - treat them like uploaded data
      let dataToUse: number[][] | null = uploadedData.value;
      
      if (!dataToUse && currentDataset.data) {
        dataToUse = currentDataset.data;
        uploadedData.value = dataToUse;
      }
      
      if (!dataToUse || dataToUse.length === 0) {
        alert('No data available for imported dataset. Please re-import the dataset.');
        isClusteringRunning.value = false;
        return;
      }
      
      // Use backend file processing if fileId is available
      if (currentDataset.fileId) {
        console.log('[Clustering] Using backend file processing for imported dataset with fileId:', currentDataset.fileId);
        params.fileId = currentDataset.fileId;
        params.isPreprocessed = true;
      } else {
        // Send data directly
        console.log('[Clustering] Sending imported data directly to backend');
        params.data = dataToUse;
        params.featureHeaders = currentDataset.headers || Array.from({ length: dataToUse[0]?.length || 0 }, (_, i) => `Feature_${i + 1}`);
        params.hasHeaders = currentDataset.hasHeaders || false;
      }
      
    } else {
      console.error('[Clustering] Invalid dataset type:', currentDataset.type);
      alert(`Invalid dataset type: ${currentDataset.type}. Please select a sample dataset or upload a file.`);
      isClusteringRunning.value = false;
      return;
    }
    
    // Performance optimization: Skip t-SNE and UMAP in main thread for faster response
    // They will be computed in background and polled separately
    params.skip_tsne = true;
    params.skip_umap = true;
    
    console.log('[Clustering] Final parameters being sent to API (with non-blocking DR):', params);
    
    const apiStartTime = performance.now();
    console.log('[Clustering] Starting API call at:', new Date().toISOString());
    
    // Start clustering - this now returns immediately with operation ID
    const startResponse = await clusteringApi.getClusters(params, clusteringAbortController.value?.signal);
    
    // Store operation ID for abort functionality
    if (startResponse.operation_id) {
      currentOperationId.value = startResponse.operation_id;
      console.log('[Clustering] Received operation ID:', startResponse.operation_id);
      
      // Poll for completion
      const data = await pollForClusteringCompletion(startResponse.operation_id);
      if (!data) {
        // Polling was aborted or failed
        console.log('[Clustering] No data returned from polling - operation was aborted or failed');
        return;
      }
      
      console.log('[Clustering] Successfully received data from polling:', {
        hasPoints: !!data.points,
        pointsLength: data.points?.length,
        hasTree: !!data.tree,
        hasLabels: !!data.labels,
        labelsLength: data.labels?.length
      });
      
      const apiEndTime = performance.now();
      console.log('[Clustering] API call completed at:', new Date().toISOString());
      console.log('[Clustering] API call took:', (apiEndTime - apiStartTime).toFixed(2), 'ms');
      
      // Continue with the rest of the processing using the received data
      await processClusteringResult(data, sourcePointsForStats, params, currentDataset);
      
    } else {
      throw new Error('No operation ID received from clustering start');
    }
  } catch (err: any) {
    // Check if the error is from abortion
    if (err.name === 'AbortError') {
      console.log('[Clustering] Request was aborted by user');
      // Don't show alert for user-initiated abort
    } else {
      // Handle specific error types with user-friendly messages
      let errorMessage = 'Error during clustering';
      if (err.message) {
        if (err.message.includes('Tree generation failed') || err.message.includes('SHiP tree generation failed')) {
          errorMessage = 'Tree generation failed. Please try selecting a different tree type or partition method.';
        } else if (err.message.includes('This tree type is not compatible with your dataset')) {
          errorMessage = 'The selected tree type is not compatible with your dataset. Please choose a different tree type.';
        } else if (err.message.includes('operation failed') && err.message.includes('ultrametric')) {
          errorMessage = 'Clustering failed due to tree generation issues. Please try a different tree type or parameters.';
        } else if (err.message.includes('Operation not found')) {
          errorMessage = 'The clustering operation failed or timed out. Please try again with different parameters.';
        } else {
          errorMessage = err.message;
        }
      }
      
      // Check if error has structured SHiP error details (from polling)
      if (err.shipError && typeof err.shipError === 'object') {
        if (err.shipError.error_code && err.shipError.message) {
          const message = err.shipError.message;
          const suggestion = err.shipError.suggestion || '';
          errorMessage = suggestion ? `${message}. ${suggestion}` : message;
        }
      }
      
      addToast(errorMessage, 'error');
      console.error('Full error in fetchClusters:', err);
      
      // Abort the current operation
      if (currentOperationId.value && clusteringAbortController.value) {
        console.log('[Clustering] Aborting current operation due to error');
        clusteringAbortController.value.abort();
        currentOperationId.value = null;
      }
      
      // Reset all clustering state
      clusterData.value = { points: [], labels: [], centers: [], dimensionality_reduction: { pca: null, umap: null, tsne: null }, original_points: null };
      treeData.value = null;
      evaluationMetrics.value = null;
    }
  } finally {
    // Always clear loading state and abort controller
    isClusteringRunning.value = false;
    clusteringAbortController.value = null;
  }
};

// Process clustering result (extracted from the main function)
const processClusteringResult = async (data: any, sourcePointsForStats: number[][] | null, params: any, currentDataset: any) => {
  try {
    console.log('[Clustering] Starting processClusteringResult with data:', {
      hasData: !!data,
      hasPoints: !!data?.points,
      pointsLength: data?.points?.length,
      hasTree: !!data?.tree,
      hasLabels: !!data?.labels,
      labelsLength: data?.labels?.length,
      dataKeys: data ? Object.keys(data) : []
    });
    
    // Validate required data structure
    if (!data) {
      console.error('[Clustering] No data provided to processClusteringResult');
      throw new Error('No clustering data received');
    }
    
    if (!data.points || !Array.isArray(data.points) || data.points.length === 0) {
      console.error('[Clustering] Invalid or empty points data:', data.points);
      throw new Error('Invalid points data in clustering result');
    }
    
    if (!data.labels || !Array.isArray(data.labels) || data.labels.length === 0) {
      console.error('[Clustering] Invalid or empty labels data:', data.labels);
      throw new Error('Invalid labels data in clustering result');
    }
    
    console.log('[Clustering] Data validation passed, proceeding with result processing');
    
    // Track large result data for memory management
    if (data && data.points) {
      trackLargeObject(data.points);
      trackLargeObject(data);
    }
    
    // Defensive: ensure DR arrays are always arrays of arrays or null
    if (data.dimensionality_reduction) {
      if (!Array.isArray(data.dimensionality_reduction.pca)) data.dimensionality_reduction.pca = null;
      if (!Array.isArray(data.dimensionality_reduction.umap)) data.dimensionality_reduction.umap = null;
      if (!Array.isArray(data.dimensionality_reduction.tsne)) data.dimensionality_reduction.tsne = null;
    }
    
    // Store cluster ID for later use (polling will be started from handleRunLoaded)
    if (data.cluster_id) {
      console.log('[Clustering] Received cluster ID:', data.cluster_id);
      // Don't start polling here - it will be handled by handleRunLoaded when the active run changes
    }
    
    // Build labelToColor map from tree leaves
    function getLeafColors(tree: any) {
      const map: Record<string, string> = {};
      function traverse(node: any) {
        if (!node.children || node.children.length === 0) {
          const label = node.label !== undefined ? node.label : node.id;
          map[String(label)] = node.color;
        } else {
          node.children.forEach(traverse);
        }
      }
      if (tree && tree.root) traverse(tree.root);
      return map;
    }
    
    const labelToColor = getLeafColors(data.tree);
    clusterData.value = {
      ...data,
      labelToColor,
      original_points: sourcePointsForStats || data.points // Store original points if available, or the initial points from response
    };
    // --- FIX: Always set treeData.value from backend ---
    treeData.value = data.tree || data.treeData || null;
    // --- END FIX ---

    // Update feature names from backend result if available
    const backendFeatureNames = data.feature_names || data.feature_headers;
    if (backendFeatureNames && Array.isArray(backendFeatureNames) && backendFeatureNames.length > 0) {
      // Check if they're not just generic names (Feature_0, Feature_1, etc.)
      const isGeneric = backendFeatureNames.every((n: string) => /^Feature[_ ]\d+$/i.test(n));
      if (!isGeneric) {
        console.log('[Clustering] Updating feature names from backend result:', backendFeatureNames.slice(0, 5));
        localFeatureNames.value = backendFeatureNames;
        // Also update dataset headers so other components pick them up
        const currentDataset = globalState.currentDataset.value;
        if (currentDataset && (!currentDataset.headers || currentDataset.headers.every((h: string) => /^Feature[_ ]\d+$/i.test(h)))) {
          currentDataset.headers = backendFeatureNames;
          globalState.setCurrentDataset({ ...currentDataset });
        }
      }
    }

    evaluationMetrics.value = normalizeMetrics(data.evaluation_metrics || data.metrics || null);
    
    // Don't auto-show metrics panel - let user decide
    // But keep metrics data available for when user expands it
    
    // Set optimization info
    optimizationInfo.value = {
      dataset_size: data.original_data_size || data.points?.length || 0,
      cache_hit: false, // Would need to track this from backend
      tree_pruned: data.tree?.pruning_info?.was_pruned || false,
      data_sampled: data.sampling_info?.was_sampled || false
    };
    
    // Don't auto-show metrics panel - let user decide
    
    // Calculate actual cluster count from clustering results
    const actualCount = clusterData.value?.labels && Array.isArray(clusterData.value.labels) 
      ? new Set(clusterData.value.labels).size 
      : 0;
    
    // Save run to global state for history
    const datasetName = uploadedFileName.value 
      ? `${uploadedFileName.value} (Uploaded)`
      : `${selectedSample.value} (${params.n_samples || 'unknown'} samples)`;
    
    // Debug logging for fileId capture
    const availableFileIds = {
      currentDatasetFileId: currentDataset?.fileId,
      paramsFileId: params.fileId,
      activeRunFileId: globalState.activeRun.value?.parameters?.fileId
    };
    console.log('[Clustering] Available fileIds for run creation:', availableFileIds);
    
    const run = {
      dataset: datasetName,
      treeType: selectedTreeType.value,
      partitionMethod: selectedPartitionMethod.value,
      selectedK: selectedK.value,
      selectedPower: selectedPower.value,
      actualClusterCount: actualCount,
      clusterData: clusterData.value,
      treeData: treeData.value,
      parameters: {
        sample: (uploadedFileName.value) ? 'custom_data' : selectedSample.value,
        ...(uploadedFileName.value && { uploadedFileName: uploadedFileName.value }),
        // Capture fileId from any available source for uploaded datasets
        ...(currentDataset?.type === 'uploaded' && (
          currentDataset?.fileId || 
          params.fileId || 
          (globalState.activeRun.value?.parameters?.fileId)
        ) && { 
          fileId: currentDataset?.fileId || 
                  params.fileId || 
                  globalState.activeRun.value?.parameters?.fileId 
        }),
        n_samples: params.n_samples,
        datasetInfo: {
          ...currentDataset,
          data: undefined, // Avoid storing large data in history
        }
      },
      metrics: {
        silhouetteScore: data.evaluation_metrics?.silhouette_score,
        dbIndex: data.evaluation_metrics?.db_index,
        calinskiHarabasz: data.evaluation_metrics?.calinski_harabasz,
        ari: data.evaluation_metrics?.ari,
        discoScore: data.evaluation_metrics?.disco_score
      }
    };
    
    // Add run and set it as active immediately
    // Set isLoadingRun to prevent the activeRun watcher from re-clearing and reloading
    // the data we just set (handleRunLoaded would unnecessarily reset clusterData)
    const runId = await globalState.addRun(run);
    isLoadingRun.value = true;
    globalState.setActiveRun(runId);
    isLoadingRun.value = false;
    console.log('[Clustering] Added new run and set as active:', runId);
    
    // Log to study session
    studySession.logParameterSet('clustering', {
      treeType: selectedTreeType.value,
      partitionMethod: selectedPartitionMethod.value,
      power: selectedPower.value,
      k: selectedK.value,
      sample: currentDataset.sampleName,
      uploadedFileName: currentDataset.fileName,
      fileId: currentDataset.fileId
    }, {
      silhouetteScore: evaluationMetrics.value?.silhouette_score,
      dbIndex: evaluationMetrics.value?.db_index,
      calinskiHarabasz: evaluationMetrics.value?.calinski_harabasz,
      discoScore: evaluationMetrics.value?.disco_score,
      ari: evaluationMetrics.value?.ari
    });
    
    // Debug logging for run parameters
    console.log('[Clustering] Run parameters saved:', {
      runId: runId,
      hasFileId: !!run.parameters.fileId,
      fileId: run.parameters.fileId,
      datasetType: run.parameters.datasetInfo?.type,
      datasetName: run.parameters.datasetInfo?.name
    });
    
    // Confirm final state after processing
    console.log('[Clustering] Final result state:', {
      clusterDataPointsLength: clusterData.value?.points?.length,
      treeDataAvailable: !!treeData.value,
      evaluationMetricsAvailable: !!evaluationMetrics.value,
      currentClusterIdSet: !!currentClusterId.value,
      shouldShowVisualizations: !(!hasValidDataset.value || (!clusterData.value?.points?.length && !isClusteringRunning.value))
    });
    
    // Clear large data after processing to save memory
    setTimeout(() => {
      clearLargeData();
    }, 1000);
    
  } catch (err: any) {
    console.error('Error processing clustering result:', err);
    alert(`Error processing clustering result: ${err.message}`);
    clusterData.value = { points: [], labels: [], centers: [], dimensionality_reduction: { pca: null, umap: null, tsne: null }, original_points: null };
    treeData.value = null;
    evaluationMetrics.value = null;
  } finally {
    // Always reset loading state
    isClusteringRunning.value = false;
    currentOperationId.value = null;
  }
};

// Note: Second onMounted removed - consolidated into main onMounted above

// Panel resizing functionality
let isResizing = false;

const startResize = (event: MouseEvent) => {
  isResizing = true;
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
  event.preventDefault();
};

const handleResize = (event: MouseEvent) => {
  if (!isResizing) return;
  
  const container = document.querySelector('.visualizations-container');
  if (!container) return;
  
  const containerRect = container.getBoundingClientRect();
  const percentage = ((event.clientX - containerRect.left) / containerRect.width) * 100;
  
  // Constrain between 20% and 80%
  const constrainedPercentage = Math.max(20, Math.min(80, percentage));
  
  dendrogramPanelSize.value = constrainedPercentage;
  scatterPanelSize.value = 100 - constrainedPercentage;
};

const stopResize = () => {
  isResizing = false;
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
};

// Update CSS custom properties when panel sizes change
const updatePanelSizeStyles = () => {
  if (typeof document === 'undefined') return; // SSR guard
  
  const container = document.querySelector('.visualizations-container.side-by-side') as HTMLElement;
  if (container) {
    container.style.setProperty('--dendrogram-width', `${dendrogramPanelSize.value}%`);
    container.style.setProperty('--scatter-width', `${scatterPanelSize.value}%`);
  }
};

// Watch for panel size changes and update CSS
watch([dendrogramPanelSize, scatterPanelSize], () => {
  nextTick(updatePanelSizeStyles);
});

// Also update on layout mode change to ensure proper setup
watch(layoutMode, (newMode) => {
  if (newMode === 'side-by-side') {
    // Ensure we have the correct initial sizes
    dendrogramPanelSize.value = 50;
    scatterPanelSize.value = 50;
    nextTick(updatePanelSizeStyles);
  }
});

// Watch for split-view toggle changes and persist to localStorage
watch(useSplitView, (newValue) => {
  try {
    localStorage.setItem('clustering-use-split-view', newValue.toString());
    console.log('Split-view preference saved to localStorage:', newValue);
  } catch (err) {
    console.warn('Failed to save split-view preference to localStorage:', err);
  }
});

// Initialize panel styles on mount
onMounted(() => {
  if (layoutMode.value === 'side-by-side') {
    nextTick(updatePanelSizeStyles);
  }
});

onUnmounted(() => {
  // Set component unmounted state
  componentMounted = false;
  
  // Clean up resize listener
  if (typeof window !== 'undefined' && resizeHandler) {
    window.removeEventListener('resize', resizeHandler);
  }
  // Clean up panel resize listeners
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
  
  // Clean up highlight update timeouts and flags
  if (highlightUpdateTimeout) {
    clearTimeout(highlightUpdateTimeout);
    highlightUpdateTimeout = null;
  }
  updateInProgress = false;
  lastUpdateTime = 0;
  
  // Clear all large data structures
  uploadedData.value = null;
  clusterData.value = { points: [], labels: [], centers: [], dimensionality_reduction: { pca: null, umap: null } };
  treeData.value = null;
  evaluationMetrics.value = null;
  optimizationInfo.value = null;
  
  // Force garbage collection if available
  clearLargeData();
});

// Use a debounced approach with enhanced performance optimizations
let updateInProgress = false;
let lastUpdateTime = 0;
let highlightUpdateTimeout: NodeJS.Timeout | null = null;
const MIN_UPDATE_INTERVAL = 16; // ~60fps

// Component lifecycle tracking
let componentMounted = false;

// Fast array equality check using Set for better performance
function arraysEqual(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false;
  
  // For small arrays, use simple comparison
  if (a.length <= 10) {
    return a.every((val, idx) => b[idx] === val);
  }
  
  // For larger arrays, use Set-based comparison (faster than sorting)
  const setA = new Set(a);
  const setB = new Set(b);
  
  if (setA.size !== setB.size) return false;
  
  for (const val of setA) {
    if (!setB.has(val)) return false;
  }
  return true;
}

const handleHighlightedPointsUpdate = (newPoints: number[]) => {
  // Early exit if component is not mounted
  if (!componentMounted) {
    return;
  }
  
  try {
    // Validate input and filter valid indices early
    const validPoints = Array.isArray(newPoints) 
      ? newPoints.filter(idx => typeof idx === 'number' && !isNaN(idx) && idx >= 0)
      : [];
    
    // Performance optimization - check if update is needed before any processing
    const current = pointsToHighlightInScatter.value;
    if (arraysEqual(validPoints, current)) {
      return;
    }
    
    // Advanced throttling with timeout cancellation
    const now = performance.now();
    if (updateInProgress || (now - lastUpdateTime) < MIN_UPDATE_INTERVAL) {
      // Cancel any pending update and schedule a new one
      if (highlightUpdateTimeout) {
        clearTimeout(highlightUpdateTimeout);
      }
      
      highlightUpdateTimeout = setTimeout(() => {
        handleHighlightedPointsUpdate(newPoints);
      }, MIN_UPDATE_INTERVAL);
      return;
    }
    
    // Clear any pending timeout since we're processing now
    if (highlightUpdateTimeout) {
      clearTimeout(highlightUpdateTimeout);
      highlightUpdateTimeout = null;
    }
    
    // Set flag and update synchronously to avoid component unmounting issues
    updateInProgress = true;
    lastUpdateTime = now;
    
    try {
      // Direct synchronous update without nextTick/requestAnimationFrame
      // Extra safety check before reactive assignment
      if (!componentMounted) {
        updateInProgress = false;
        return;
      }
      
      pointsToHighlightInScatter.value = validPoints.length > 0 ? [...validPoints] : [];
      // Auto-clear hover highlights after 20 seconds of inactivity
      resetHoverAutoClear();
      updateInProgress = false;
    } catch (error) {
      console.warn('[CLUSTERING] Error updating highlighted points:', error);
      updateInProgress = false;
    }
  } catch (error: any) {
    // Global error handler for any issues in the function
    console.warn('[CLUSTERING] Error in handleHighlightedPointsUpdate:', error?.message || error);
    updateInProgress = false;
  }
};

let hoverAutoClearTimeout: NodeJS.Timeout | null = null;
function resetHoverAutoClear() {
  if (hoverAutoClearTimeout) clearTimeout(hoverAutoClearTimeout);
  if (pointsToHighlightInScatter.value.length > 0) {
    hoverAutoClearTimeout = setTimeout(() => {
      pointsToHighlightInScatter.value = [];
    }, 20000);
  }
}

// Handle Shift+Click node selection from tree components (full-screen layout)
const handleNodeSelectionFromTree = (event: { nodeId: string; points: number[]; isSelected: boolean }) => {
  try {
    if (event.isSelected) {
      selectedNodesForFullscreen.value.add(event.nodeId);
      nodeIdToPointsFullscreen.value.set(event.nodeId, event.points || []);
    } else {
      selectedNodesForFullscreen.value.delete(event.nodeId);
      nodeIdToPointsFullscreen.value.delete(event.nodeId);
    }

    // Recompute union of selected points
    const combined = new Set<number>();
    for (const nodeId of selectedNodesForFullscreen.value) {
      const pts = nodeIdToPointsFullscreen.value.get(nodeId) || [];
      for (const idx of pts) combined.add(idx);
    }
    selectedPointsFromNodesFullscreen.value = Array.from(combined);

    // Reset selection auto-clear timer (20s)
    if (selectionTimeoutFS) clearTimeout(selectionTimeoutFS);
    if (selectedNodesForFullscreen.value.size > 0) {
      selectionTimeoutFS = setTimeout(() => {
        clearSelectionsFullscreen();
      }, 20000);
    }
  } catch (e) {
    console.warn('[CLUSTERING] Error handling node selection:', e);
  }
};

// Canvas scatter plot event handlers
const handlePointHovered = (event: any) => {
  // Handle point hover events from Canvas component
  if (event && event.originalIndex !== undefined) {
    // You can add custom hover behavior here if needed
  }
};

// Cleanup timers on unmount
onUnmounted(() => {
  componentMounted = false;
  if (selectionTimeoutFS) {
    clearTimeout(selectionTimeoutFS);
    selectionTimeoutFS = null;
  }
  if (hoverAutoClearTimeout) {
    clearTimeout(hoverAutoClearTimeout);
    hoverAutoClearTimeout = null;
  }
});

const handlePointClicked = async (event: any) => {
  try {
    console.log('[CLUSTERING-PAGE] handlePointClicked called with:', event);
    
    // Early exit if component is not mounted
    if (!componentMounted) {
      return;
    }
    
    if (!event || event.originalIndex === undefined) {
      console.warn('[CLUSTERING-PAGE] Invalid event received:', event);
      return;
    }

    if (!displayTreeData.value) {
      console.warn('[CLUSTERING-PAGE] No tree data available for highlighting');
      return;
    }

    const pointIndex = event.originalIndex;
    console.log('[CLUSTERING-PAGE] Point clicked:', pointIndex);

    try {
      // Import the new tree utilities
      const { 
        findDeepestVisibleNodeContainingPoint, 
        findDeepestVisibleNodeForIcicle,
        findNodeInCutTree,
        getPathToNode 
      } = await import('~/composables/useTreeUtils');

      // Convert the tree data to standard format for point-to-node mapping
      const standardTree = convertTreeToStandardFormat(displayTreeData.value);
      if (!standardTree) {
        console.warn('[CLUSTERING-PAGE] Tree conversion failed');
        // Use safe state update
        try {
          highlightedNodeInTree.value = null;
        } catch (reactivityError) {
          console.warn('[CLUSTERING-PAGE] Reactivity error while clearing highlight:', reactivityError);
        }
        return;
      }

      let targetNode = null;

      // Different logic for dendrogram vs icicle plot
      if (treeVisualizationType.value === 'dendrogram') {
        // For depth-cut trees, we need special handling since nodes at the cut depth become leaves
        // and contain all their descendant points
        if (treeContentType.value === 'real') {
          console.log(`[CLUSTERING-PAGE] Handling depth-cut dendrogram (depth: ${realTreeDepth.value})`);
          
          // Use specialized cut tree search that prioritizes cut nodes with merged descendants
          targetNode = findNodeInCutTree(standardTree, pointIndex);
          console.log('[CLUSTERING-PAGE] Cut tree search: Found node:', targetNode?.id);
          
          // If no node found with specialized search, try standard deepest search as fallback
          if (!targetNode) {
            console.log('[CLUSTERING-PAGE] Cut tree search failed, trying standard deepest search...');
            targetNode = findDeepestNodeContainingPoint(standardTree, pointIndex);
            console.log('[CLUSTERING-PAGE] Standard search fallback: Found node:', targetNode?.id);
          }
          
          // If still no node found, try with expanded nodes approach as final fallback
          if (!targetNode) {
            console.log('[CLUSTERING-PAGE] Standard search failed, trying expanded nodes fallback...');
            const expandedNodes = new Set<string>();
            
            // Collect all nodes that would be visible after cutting at the specified depth
            const collectVisibleNodes = (node: any, currentDepth: number = 0) => {
              if (!node) return;
              
              // All nodes up to and including the cut depth are visible
              if (currentDepth <= realTreeDepth.value) {
                expandedNodes.add(node.id);
                // Only traverse children if we haven't reached the cut depth
                if (currentDepth < realTreeDepth.value && node.children) {
                  node.children.forEach((child: any) => collectVisibleNodes(child, currentDepth + 1));
                }
              }
            };
            
            collectVisibleNodes(standardTree, 0);
            console.log(`[CLUSTERING-PAGE] Final fallback: Collected ${expandedNodes.size} expanded nodes for depth-cut tree`);
            
            targetNode = findDeepestVisibleNodeContainingPoint(standardTree, pointIndex, expandedNodes);
            console.log('[CLUSTERING-PAGE] Final fallback search: Found node:', targetNode?.id);
          }
        } else {
          // For summarized trees, use the original expanded nodes approach
          console.log('[CLUSTERING-PAGE] Handling summarized dendrogram');
          const expandedNodes = new Set<string>();
          
          const collectVisibleNodes = (node: any, currentDepth: number = 0) => {
            if (!node) return;
            
            // For summarized trees, use a more permissive expansion (depth <= 3)
            if (currentDepth <= 3) {
              expandedNodes.add(node.id);
              if (node.children) {
                node.children.forEach((child: any) => collectVisibleNodes(child, currentDepth + 1));
              }
            }
          };
          
          collectVisibleNodes(standardTree, 0);
          console.log(`[CLUSTERING-PAGE] Summarized dendrogram: Collected ${expandedNodes.size} visible nodes`);
          
          targetNode = findDeepestVisibleNodeContainingPoint(standardTree, pointIndex, expandedNodes);
          console.log('[CLUSTERING-PAGE] Summarized dendrogram: Found deepest visible node:', targetNode?.id);
        }
      } else if (treeVisualizationType.value === 'icicle') {
        // For icicle plot, all nodes in the current tree are visible (after depth cutting)
        // Use the deepest search which should work correctly with cut trees
        console.log('[CLUSTERING-PAGE] Handling icicle plot');
        targetNode = findDeepestVisibleNodeForIcicle(standardTree, pointIndex);
        console.log('[CLUSTERING-PAGE] Icicle: Found deepest node:', targetNode?.id);
      }

      if (targetNode) {
        console.log('[CLUSTERING-PAGE] Found target node:', targetNode.id, 'at depth:', targetNode.depth || 'unknown');
        
        // Get the path to this node for expansion if needed
        const pathToNode = getPathToNode(standardTree, targetNode);
        console.log('[CLUSTERING-PAGE] Path to node:', pathToNode.map(n => n.id));
        
        // Safe state update with error handling
        try {
          // Set the highlighted node - this will trigger the tree components to highlight
          highlightedNodeInTree.value = {
            nodeId: targetNode.id,
            pathToNode: pathToNode,
            pointIndex: pointIndex,
            visualizationType: treeVisualizationType.value,
            enhancedVisibility: true // Flag for better visibility
          };
          console.log('[CLUSTERING-PAGE] Highlighted node set:', highlightedNodeInTree.value);
        } catch (reactivityError) {
          console.warn('[CLUSTERING-PAGE] Reactivity error while setting highlight:', reactivityError);
        }
      } else {
        console.warn('[CLUSTERING-PAGE] No node found containing point:', pointIndex);
        // Clear any existing highlight with error handling
        try {
          highlightedNodeInTree.value = null;
        } catch (reactivityError) {
          console.warn('[CLUSTERING-PAGE] Reactivity error while clearing highlight:', reactivityError);
        }
      }
    } catch (error) {
      console.error('[CLUSTERING-PAGE] Error in handlePointClicked:', error);
      // Safe error recovery with additional protection
      try {
        highlightedNodeInTree.value = null;
      } catch (reactivityError) {
        console.warn('[CLUSTERING-PAGE] Reactivity error during error recovery:', reactivityError);
      }
    }
  } catch (globalError: any) {
    // Ultimate error boundary - prevent any error from bubbling to Vue router
    console.error('[CLUSTERING-PAGE] Global error in handlePointClicked:', globalError?.message || globalError);
    // Don't attempt any state updates in this catch block to avoid further errors
  }
};

// Handle node selection events from tree visualizations
const handleNodesSelected = (selectedNodeIds: string[]) => {
  console.log('[CLUSTERING-PAGE] Nodes selected:', selectedNodeIds);
  
  // For now, we just log the selected nodes
  // In the future, this could be extended to:
  // - Update the sidebar with selection info
  // - Show selected points in a different color
  // - Enable bulk operations on selected nodes
  // - Display selection statistics
  
  if (selectedNodeIds.length === 0) {
    console.log('[CLUSTERING-PAGE] All selections cleared');
  } else {
    console.log(`[CLUSTERING-PAGE] ${selectedNodeIds.length} nodes currently selected`);
  }
};

// Check if we have a valid dataset selected
const hasValidDataset = computed(() => {
  return globalState.currentDataset.value !== null;
});

// Check if clustering results match current dataset
const clusteringResultsValid = computed(() => {
  if (!hasValidDataset.value || !clusterData.value?.points?.length) {
    return false;
  }
  
  // Additional validation could be added here to check if the clustering results
  // are actually for the current dataset
  return true;
});

const currentDatasetName = computed(() => {
  // Check global state first for uploaded data
  const currentDataset = globalState.currentDataset.value;
  if (currentDataset) {
    if (currentDataset.type === 'uploaded') {
      return currentDataset.fileName || currentDataset.name;
    } else if (currentDataset.type === 'sample') {
      return currentDataset.name;
    } else if (currentDataset.type === 'imported') {
      return currentDataset.fileName || currentDataset.name;
    }
  }
  
  // Fallback to local state
  if (uploadedFileName.value) {
    return uploadedFileName.value;
  }
  const sampleOption = currentSampleOptions.value.find(s => s.value === selectedSample.value);
  return sampleOption?.label || 'No dataset selected';
});

// Get dataset name suitable for image API (sample name for sample datasets)
const datasetNameForImages = computed(() => {
  const currentDataset = globalState.currentDataset.value;
  if (currentDataset?.type === 'sample' && currentDataset.sampleName) {
    return currentDataset.sampleName;
  }
  return '';
});

// Computed property for maximum allowed K (dataset size - 1)
const maxAllowedK = computed(() => {
  const currentDataset = globalState.currentDataset.value;
  if (!currentDataset) return maxK.value;
  
  let datasetSize = 0;
  
  if (currentDataset.type === 'uploaded' || currentDataset.type === 'imported') {
    // For uploaded/imported data, use pointCount or data length
    if (currentDataset.pointCount) {
      datasetSize = currentDataset.pointCount;
    } else if (currentDataset.data && currentDataset.data.length > 0) {
      datasetSize = currentDataset.data.length;
    } else if (uploadedData.value && uploadedData.value.length > 0) {
      datasetSize = uploadedData.value.length;
    }
  } else if (currentDataset.type === 'sample') {
    // For sample data, use n_samples
    datasetSize = currentDataset.n_samples || 200;
  }
  
  // K can't be more than dataset size - 1 (you need at least 1 point per cluster)
  // But also respect the original maxK limit for UI performance
  const maxPossibleK = Math.max(2, datasetSize - 1);
  return Math.min(maxPossibleK, 500); // Cap at 500 for UI performance
});

const datasetProcessingInfo = computed(() => {
  const currentDataset = globalState.currentDataset.value;
  if (!currentDataset) return null;
  
  // Check for processing configuration in dataConfig or direct properties
  const dataConfig = currentDataset.dataConfig;
  const missingStrategy = dataConfig?.missingValueStrategy || currentDataset.missingValueStrategy;
  const normalization = dataConfig?.normalization || currentDataset.normalization;
  const categoricalEncoding = dataConfig?.categoricalEncoding;
  
  // Only show if processing was actually applied
  if (!missingStrategy && !normalization && !categoricalEncoding) {
    return null;
  }
  
  return {
    missingValueStrategy: missingStrategy,
    normalization: normalization,
    categoricalEncoding: categoricalEncoding,
    hasProcessing: !!(missingStrategy || normalization || categoricalEncoding)
  };
});

const formatProcessingStrategy = (strategy: string): string => {
  if (!strategy) return '';
  
  // Convert enum-like values to user-friendly labels
  const strategyMap: Record<string, string> = {
    // Missing value strategies
    'keep': 'Keep',
    'remove': 'Remove',
    'fill_mean': 'Fill Mean',
    'fill_median': 'Fill Median', 
    'fill_zero': 'Fill Zero',
    'fill_mode': 'Fill Mode',
    
    // Normalization methods
    'none': 'None',
    'standard': 'Standard',
    'minmax': 'Min-Max',
    'robust': 'Robust',
    
    // Categorical encoding
    'label': 'Label',
    'onehot': 'One-Hot'
  };
  
  // Handle enum-like format (e.g., "MissingValueStrategy.fill_mean")
  const parts = strategy.split('.');
  const actualStrategy = parts.length > 1 ? parts.at(1) : strategy;
  
  return strategyMap[actualStrategy] || actualStrategy;
};


// Export functionality
const exportVisualization = async (vizType: 'dendrogram' | 'scatter' | 'icicle', format: 'png' | 'svg') => {
  try {
    let selector = '';
    let filename = '';
    
    switch (vizType) {
      case 'dendrogram':
        selector = '#cluster-dendrogram';
        filename = `dendrogram-${globalState.activeRunId.value}`;
        break;
      case 'scatter':
        selector = '#cluster-scatter-plot';
        filename = `scatter-plot-${globalState.activeRunId.value}`;
        break;
      case 'icicle':
        selector = '#cluster-icicle-plot';
        filename = `icicle-plot-${globalState.activeRunId.value}`;
        break;
    }

    const svgElement = document.querySelector(selector) as SVGElement;
    if (!svgElement) {
      console.error(`${vizType} visualization not found`);
      return;
    }

    if (format === 'svg') {
      // Export as SVG
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const blob = new Blob([svgData], { type: 'image/svg+xml' });
      downloadBlob(blob, `${filename}.svg`);
    } else {
      // Export as PNG
      await exportSVGToPNG(svgElement, `${filename}.png`);
    }
  } catch (error) {
    console.error(`Error exporting ${vizType}:`, error);
  }
};

// Helper function to download blob
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

// Watch for cluster data changes and validate axis selections
watch(() => clusterData.value, (newClusterData) => {
  if (!newClusterData || !newClusterData.points || newClusterData.points.length === 0) {
    return;
  }
  
  // Check if current axis selections are valid for the new data
  const availableFeatureCount = rawFeatureCount.value;
  const hasPCA = newClusterData.dimensionality_reduction?.pca;
  const hasUMAP = newClusterData.dimensionality_reduction?.umap;
  const hasTSNE = newClusterData.dimensionality_reduction?.tsne;
  
  let xAxisValid = false;
  let yAxisValid = false;
  
  // Validate X axis
  if (selectedXAxis.value.startsWith('feature-')) {
    const featureIndex = parseInt(selectedXAxis.value.replace('feature-', ''));
    xAxisValid = featureIndex < availableFeatureCount;
  } else if (selectedXAxis.value.startsWith('pca-')) {
    xAxisValid = hasPCA;
  } else if (selectedXAxis.value.startsWith('umap-')) {
    xAxisValid = hasUMAP;
  } else if (selectedXAxis.value.startsWith('tsne-')) {
    xAxisValid = hasTSNE;
  }
  
  // Validate Y axis
  if (selectedYAxis.value.startsWith('feature-')) {
    const featureIndex = parseInt(selectedYAxis.value.replace('feature-', ''));
    yAxisValid = featureIndex < availableFeatureCount;
  } else if (selectedYAxis.value.startsWith('pca-')) {
    yAxisValid = hasPCA;
  } else if (selectedYAxis.value.startsWith('umap-')) {
    yAxisValid = hasUMAP;
  } else if (selectedYAxis.value.startsWith('tsne-')) {
    yAxisValid = hasTSNE;
  }
  
  // Reset to valid defaults if current selections are invalid
  if (!xAxisValid) {
    if (hasPCA) {
      selectedXAxis.value = 'pca-0';
    } else if (hasUMAP) {
      selectedXAxis.value = 'umap-0';
    } else if (hasTSNE) {
      selectedXAxis.value = 'tsne-0';
    } else if (availableFeatureCount > 0) {
      selectedXAxis.value = 'feature-0';
    }
  }
  
  if (!yAxisValid) {
    if (hasPCA) {
      selectedYAxis.value = 'pca-1';
    } else if (hasUMAP) {
      selectedYAxis.value = 'umap-1';
    } else if (hasTSNE) {
      selectedYAxis.value = 'tsne-1';
    } else if (availableFeatureCount > 1) {
      selectedYAxis.value = 'feature-1';
    } else if (availableFeatureCount > 0) {
      selectedYAxis.value = 'feature-0';
    }
  }
  
  console.log('[Clustering] Axis validation complete:', {
    xAxis: selectedXAxis.value,
    yAxis: selectedYAxis.value,
    xValid: xAxisValid,
    yValid: yAxisValid,
    availableFeatures: availableFeatureCount,
    hasPCA, hasUMAP, hasTSNE
  });
}, { deep: false });

// after existing formatMetric declaration earlier? Actually we need to add if not present.
// ... existing code (formatProcessingStrategy helper below) ...
const safeFormat = (val: number | undefined | null, digits: number = 3) => {
  if (val === undefined || val === null || isNaN(val)) return 'N/A'
  return val.toFixed(digits)
}
// Replace metric display lines: silhouette, db_index, calinski, disco etc.
// metric cards lines earlier: change metric-value inner expression to safeFormat(...)

// ... after existing safeFormat helper in script section (around 2410) ...
const normalizeMetrics = (m: any) => {
  if (!m) return m;
  const mappings: [string, string][] = [
    ['silhouetteScore', 'silhouette_score'],
    ['dbIndex', 'db_index'],
    ['calinskiHarabasz', 'calinski_harabasz'],
    ['ari', 'ari'],
    ['discoScore', 'disco_score']
  ]
  mappings.forEach(([camel, snake]) => {
    if (m[camel] === undefined && m[snake] !== undefined) m[camel] = m[snake];
    if (m[snake] === undefined && m[camel] !== undefined) m[snake] = m[camel];
  })
  return m;
}

const getMetric = (nameCamel: string, nameSnake: string) => {
  const m = evaluationMetrics.value || {};
  return m[nameSnake] ?? m[nameCamel];
}

</script>

<style scoped>
@import '~/assets/css/pages/clustering.css';
</style>

