<template>  <div>    <div v-if="!dataSuccessfullyUploaded || showDataSourceSelection">
      <div class="upload-methods-container">
        <div class="method-option">
          <div class="method-header">
            <h6><span class="method-icon">📁</span> Upload Your Data</h6>
            <button @click="toggleUploadArea" class="toggle-method-btn" :class="{ active: showUploadAreaState }">
              {{ showUploadAreaState ? 'Hide' : 'Show' }}
            </button>
          </div>
          <div v-show="showUploadAreaState" class="file-upload-container">
            <div class="upload-zone" 
                 @drop.prevent="handleFileDrop"
                 @dragover.prevent 
                 @dragenter.prevent
                 @click="triggerFileInput"
                 :class="{ 'drag-over': isDragOver }"
                 @dragenter="isDragOver = true"
                 @dragleave="isDragOver = false"
                 @drop="isDragOver = false">
              <div class="upload-icon">📤</div>
              <div class="upload-text">
                <strong>Drop files here or click to browse</strong>
                <p>Supports CSV and JSON files</p>
              </div>
            </div>
            <input 
              ref="fileInput"
              type="file" 
              id="sidebar-file-upload-input" 
              accept=".json,.csv" 
              @change="handleFileChange" 
              style="display: none"
            />
            <div v-if="localFileUploadStatus" class="upload-status" :class="localFileUploadStatus.type">
              {{ localFileUploadStatus.message }}
            </div>
          </div>
        </div>

        <div class="method-divider">
          <span>OR</span>
        </div>        <div class="method-option">
          <div class="method-header">
            <h6><span class="method-icon">🎯</span> Try Sample Datasets</h6>
            <button @click="toggleSampleDatasets" class="toggle-method-btn" :class="{ active: showSampleDatasetsState }">
              {{ showSampleDatasetsState ? 'Hide' : 'Show' }}
            </button>
          </div>
          <p class="method-description">Perfect for exploring clustering without your own data</p>
          <div v-show="showSampleDatasetsState" class="sample-datasets-container">
            <ul class="dataset-list">
              <li v-for="opt in displayedSampleOptions" :key="opt.value" 
                  :class="['dataset-item', { selected: localSelectedSample === opt.value }]" 
                  @click="handleSelectToyDataset(opt.value)">
                  <div class="dataset-content">
                    <span class="dataset-icon">🎯</span>
                    <span class="dataset-label">{{ opt.label }}</span>
                    <span v-if="localSelectedSample === opt.value" class="selected-indicator">✓</span>
                  </div>
              </li>
            </ul>
            
            <!-- Size Selection for Selected Toy Dataset -->
            <div v-if="localSelectedSample" class="size-selection-container">
              <div class="size-selection-header">
                <h6>Dataset Size</h6>
                <span class="size-description">Number of data points to generate</span>
              </div>
              <div class="size-input-section">
                <div class="size-presets">
                  <button 
                    v-for="size in sizePresets" 
                    :key="size"
                    @click="selectedSampleSize = size"
                    :class="['size-preset-btn', { active: selectedSampleSize === size }]"
                  >
                    {{ size }}
                  </button>
                </div>
                <div class="custom-size-input">
                  <label for="custom-size">Custom:</label>
                  <input 
                    id="custom-size"
                    type="number"
                    v-model.number="selectedSampleSize"
                    :min="minSampleSize"
                    :max="maxSampleSize"
                    :step="50"
                    class="size-input"
                    placeholder="Enter size"
                  />
                </div>
              </div>
              <div class="size-info">
                <span v-if="selectedSampleSize < 200" class="size-warning">⚠️ Small datasets may produce poor clustering results</span>
                <span v-else-if="selectedSampleSize > 5000" class="size-warning">⚠️ Large datasets may take longer to process</span>
                <span v-else class="size-info-text">✓ Good size for clustering analysis</span>
              </div>
            </div>
            
            <button v-if="sampleOptions.length > 4 && !showAllToyDatasetsState" @click="showAllToyDatasetsState = true" class="show-more-btn">Show More Datasets</button>
            <button v-if="showAllToyDatasetsState && sampleOptions.length > 4" @click="showAllToyDatasetsState = false" class="show-more-btn">Show Less</button>
          </div>
        </div>
      </div>
    </div><div v-if="localUploadedFiles.length > 0 || localSelectedSample" class="data-summary-reworked">
      <h5>{{ localUploadedFiles.length > 0 ? 'Selected File:' : 'Selected Toy Dataset:'}}</h5>
      <div v-if="localUploadedFiles.length > 0 && localSelectedUploadId" class="selected-file-info">
          <p><strong>{{ localUploadedFiles.find(f => f.uploadId === localSelectedUploadId)?.fileName }}</strong></p>
          <p v-if="quickStats">
              <span class="icon-reworked">📊</span> {{ quickStats.pointCount }} points, {{ quickStats.featureCount }} features
          </p>
      </div>
      <div v-if="!(localUploadedFiles.length > 0) && localSelectedSample" class="selected-file-info">
          <p><strong>{{ sampleOptions.find(opt => opt.value === localSelectedSample)?.label }}</strong> (Toy Dataset)</p>
          <p v-if="selectedSampleSize">
              <span class="icon-reworked">📊</span> {{ selectedSampleSize }} points, 2 features
          </p>
      </div>      <button v-if="dataSuccessfullyUploaded && !showDataSourceSelection" @click="handleChangeDataSource" class="change-data-btn-reworked">
          <span class="icon-reworked">🔄</span> Change Data Source
      </button>
    </div>      <div v-if="(!dataSuccessfullyUploaded || showDataSourceSelection)" class="data-options-list">
      <div v-if="localUploadedFiles.length > 0" class="recent-uploads-reworked">
        <h6>Select an Uploaded File:</h6>
        <ul class="uploads-list-reworked">
          <li v-for="file in localUploadedFiles" :key="file.uploadId" 
              :class="['upload-item-reworked', { selected: localSelectedUploadId === file.uploadId }]" 
              @click="handleSelectUploadedFile(file.uploadId)">
              {{ file.fileName }} ({{ file.rowCount }} rows)
          </li>
        </ul>
      </div>
    </div>    <!-- Dataset confirmation button at the bottom -->
    <div v-if="(!dataSuccessfullyUploaded || showDataSourceSelection) && (localSelectedUploadId || localSelectedSample)" class="confirm-section">
      <button @click="handleConfirmDataSource" class="confirm-data-btn-reworked prominent-cta">
        <span class="icon-reworked">✔️</span> Confirm Data Source
      </button>
      <button v-if="showDataSourceSelection && dataSuccessfullyUploaded" @click="cancelChangeDataSource" class="cancel-change-btn">
        <span class="icon-reworked">❌</span> Cancel Change
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, toRefs } from 'vue';
import { useFileUpload } from '~/composables/useFileUpload'; // Assuming path is correct

interface SampleOption { label: string; value: string }
interface UploadedFileInfo {
  uploadId: string; fileName: string; fileType: string;
  rowCount: number; columnCount: number; hasHeaders?: boolean;
  uploadedAt: Date; parsedData: any; // Consider if parsedData needs to be here or just in parent
}
interface FileUploadStatus { type: 'success' | 'error'; message: string }

const props = defineProps({
  sampleOptions: { type: Array as () => SampleOption[], default: () => [] },
  selectedSample: { type: String, default: '' },
  quickStats: { type: Object, default: null },
  dataSuccessfullyUploaded: { type: Boolean, default: false },
  // Potentially pass initial uploaded files and selected ID if state is managed higher up
  // For now, this component manages its own list of uploads until confirmation
});

const emit = defineEmits([
  'file-processed', // Emits raw file info and parsed data for parent to handle
  'data-source-confirmed', // Confirms selection (either file or toy)
  'reset-data-source', // Signals to parent to reset data source state
  'update:selected-sample-candidate', // When a toy dataset is clicked (candidate)
  'update:selected-file-candidate' // When an uploaded file is clicked (candidate)
]);

const { handleFileUpload } = useFileUpload();

const localSelectedSample = ref(props.selectedSample);
const localFileUploadStatus = ref<FileUploadStatus | null>(null);
const showAllToyDatasetsState = ref(false);
const showUploadAreaState = ref(true);
const showSampleDatasetsState = ref(false);
const showDataSourceSelection = ref(false);
const isDragOver = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const localUploadedFiles = ref<UploadedFileInfo[]>([]);
const localSelectedUploadId = ref<string | null>(null);

// Size selection for toy datasets
const selectedSampleSize = ref<number>(200);
const sizePresets = [200, 500, 1000, 2000, 5000];
const minSampleSize = 50;
const maxSampleSize = 10000;


watch(() => props.selectedSample, (val) => {
  localSelectedSample.value = val; // Always update to reflect the current prop value
});
watch(() => props.dataSuccessfullyUploaded, (isConfirmed) => {
    if(isConfirmed) {
        // If data is confirmed from parent, ensure local state reflects it
        // This might involve parent passing down the confirmed file/sample
    } else {
        // If parent resets, clear local selections too
        localSelectedUploadId.value = null;
        // localSelectedSample.value = props.sampleOptions[0]?.value || ''; // Reset to default if needed
        localUploadedFiles.value = []; // Clear file list if data source is reset
        localFileUploadStatus.value = null;
        showSampleDatasetsState.value = false;
    }
});


const toggleUploadArea = () => showUploadAreaState.value = !showUploadAreaState.value;

const toggleSampleDatasets = () => showSampleDatasetsState.value = !showSampleDatasetsState.value;

const displayedSampleOptions = computed(() => {
  const options = props.sampleOptions as SampleOption[];
  return (options.length <= 4 || showAllToyDatasetsState.value) ? options : options.slice(0, 4);
});

const processFile = async (file: File) => {
  try {
    localFileUploadStatus.value = null;
    const result = await handleFileUpload(file); // from useFileUpload
    let successMessage = `${result.fileName} ready! ${result.rowCount}r, ${result.columnCount}c`;
    if (result.fileType === 'csv' && result.hasHeaders !== undefined) successMessage += result.hasHeaders ? ' (headers ✓)' : ' (no headers)';
    localFileUploadStatus.value = { type: 'success', message: successMessage };
    
    const uploadId = `${file.name}-${Date.now()}`;
    const newUpload: UploadedFileInfo = {
        uploadId, fileName: result.fileName, fileType: result.fileType,
        rowCount: result.rowCount, columnCount: result.columnCount,
        hasHeaders: result.hasHeaders, uploadedAt: new Date(), parsedData: result.data
    };
    localUploadedFiles.value.unshift(newUpload); // Add to list
    handleSelectUploadedFile(uploadId); // Auto-select the new upload as candidate

    // Emit raw processed info for parent to potentially use for quickStats or other logic
    emit('file-processed', {
        target: { files: [file] }, // Mimic event structure if needed by parent
        parsedData: result.data, 
        fileName: result.fileName,
        fileType: result.fileType, 
        hasHeaders: result.hasHeaders,
        rowCount: result.rowCount, 
        columnCount: result.columnCount,
        uploadId: newUpload.uploadId // Pass the internal ID too
    });

  } catch (error) {
    localFileUploadStatus.value = { type: 'error', message: error instanceof Error ? error.message : 'File processing failed' };
  }
};

const handleFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files?.[0]) await processFile(input.files[0]);
  input.value = ''; // Reset file input
};

const handleFileDrop = async (event: DragEvent) => {
  event.preventDefault();
  isDragOver.value = false;
  if (event.dataTransfer?.files?.[0]) await processFile(event.dataTransfer.files[0]);
};

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleSelectToyDataset = (value: string) => {
  localSelectedSample.value = value;
  localSelectedUploadId.value = null; // Clear file selection
  // localUploadedFiles.value = []; // Clear uploaded files list when toy dataset is chosen
  localFileUploadStatus.value = null;
  emit('update:selected-sample-candidate', value);
};

const handleSelectUploadedFile = (uploadId: string) => {
  localSelectedUploadId.value = uploadId;
  localSelectedSample.value = ''; // Clear toy dataset selection
  const fileInfo = localUploadedFiles.value.find(f => f.uploadId === uploadId);
  if (fileInfo) {
    emit('update:selected-file-candidate', fileInfo);
  }
};

const handleConfirmDataSource = () => {
    if (localSelectedUploadId.value) {
        const fileInfo = localUploadedFiles.value.find(f => f.uploadId === localSelectedUploadId.value);
        if (fileInfo) {
            emit('data-source-confirmed', { type: 'file', ...fileInfo });
            showDataSourceSelection.value = false; // Hide selection after confirming
        }
    } else if (localSelectedSample.value) {
        const sampleInfo = props.sampleOptions.find(opt => opt.value === localSelectedSample.value);
        if (sampleInfo) {
            emit('data-source-confirmed', { 
                type: 'toy', 
                ...sampleInfo,
                n_samples: selectedSampleSize.value
            });
            showDataSourceSelection.value = false; // Hide selection after confirming
        }
    }
};

const handleResetDataUpload = () => {
  localSelectedSample.value = props.sampleOptions[0]?.value || ''; // Reset to default or first
  localSelectedUploadId.value = null;
  localUploadedFiles.value = [];
  localFileUploadStatus.value = null;
  showUploadAreaState.value = true;
  showSampleDatasetsState.value = false;
  showDataSourceSelection.value = false;
  emit('reset-data-source');
};

const handleChangeDataSource = () => {
  // Show the data source selection area again
  showDataSourceSelection.value = true;
  // Always expand the upload area and collapse sample datasets when changing
  showUploadAreaState.value = true;
  showSampleDatasetsState.value = false;
  // Reset any previous selections to start fresh
  localSelectedUploadId.value = null;
  localSelectedSample.value = '';
  selectedSampleSize.value = 200; // Reset to default size
  localFileUploadStatus.value = null;
  // Don't emit reset-data-source yet, just show the selection interface
};

const cancelChangeDataSource = () => {
  // Hide the data source selection area and keep existing data
  showDataSourceSelection.value = false;
  showUploadAreaState.value = true;
  showSampleDatasetsState.value = false;
};

</script>

<style scoped>
/* New upload area styling */
.upload-methods-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 20px;
}

.method-option {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: white;
}

.method-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
}

.method-header h6 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.method-icon {
  font-size: 1.2rem;
}

.method-description {
  margin: 0;
  padding: 0 20px 16px;
  font-size: 0.9rem;
  color: #64748b;
}

.toggle-method-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-method-btn:hover {
  background: #2563eb;
}

.toggle-method-btn.active {
  background: #059669;
}

.file-upload-container {
  padding: 20px;
}

.sample-datasets-container {
  padding: 20px;
}

.upload-zone {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f8fafc;
}

.upload-zone:hover,
.upload-zone.drag-over {
  border-color: #3b82f6;
  background: #eff6ff;
  transform: translateY(-2px);
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}

.upload-text strong {
  display: block;
  font-size: 1.1rem;
  color: #1e293b;
  margin-bottom: 8px;
}

.upload-text p {
  margin: 0;
  font-size: 0.9rem;
  color: #64748b;
}

.upload-status {
  margin-top: 12px;
  padding: 12px;
  border-radius: 8px;
  font-size: 0.9rem;
}

.upload-status.success {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #10b981;
}

.upload-status.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #ef4444;
}

.method-divider {
  text-align: center;
  position: relative;
  margin: 10px 0;
}

.method-divider span {
  background: white;
  padding: 0 16px;
  font-size: 0.9rem;
  font-weight: 600;
  color: #64748b;
  position: relative;
  z-index: 1;
}

.method-divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #e2e8f0;
  z-index: 0;
}

/* Dataset list styling */
.dataset-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.dataset-item {
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.dataset-item:hover {
  border-color: #3b82f6;
  background: #f8fafc;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
}

.dataset-item.selected {
  border-color: #10b981;
  background: #ecfdf5;
}

.dataset-content {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 12px;
}

.dataset-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.dataset-label {
  flex: 1;
  font-size: 0.95rem;
  font-weight: 500;
  color: #1e293b;
}

.selected-indicator {
  color: #10b981;
  font-weight: 700;
  font-size: 1.1rem;
}

.show-more-btn {
  background: none;
  border: 1px solid #e2e8f0;
  color: #3b82f6;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.9rem;
  cursor: pointer;
  width: 100%;
  margin-top: 12px;
  transition: all 0.2s ease;
}

.show-more-btn:hover {
  background: #f8fafc;
  border-color: #3b82f6;
}

/* Size Selection Styles */
.size-selection-container {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.size-selection-header {
  margin-bottom: 12px;
}

.size-selection-header h6 {
  margin: 0 0 4px 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #374151;
}

.size-description {
  font-size: 0.8rem;
  color: #6b7280;
}

.size-input-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.size-presets {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.size-preset-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  background: white;
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.size-preset-btn:hover {
  border-color: #3b82f6;
  background: #f8fafc;
}

.size-preset-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.custom-size-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.custom-size-input label {
  font-size: 0.8rem;
  font-weight: 500;
  color: #374151;
  min-width: 55px;
}

.size-input {
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.8rem;
  width: 120px;
  transition: border-color 0.2s;
}

.size-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.size-info {
  margin-top: 8px;
  font-size: 0.75rem;
}

.size-warning {
  color: #f59e0b;
  font-weight: 500;
}

.size-info-text {
  color: #10b981;
  font-weight: 500;
}

/* Fix white-on-white text issues */
.data-summary-reworked h5, 
.selected-file-info p,
.recent-uploads-reworked h6, 
.toy-datasets-reworked h6,
.step-instruction {
  color: #374151 !important;
}

.upload-item-reworked {
  color: #374151;
  background-color: #f8fafc;
}

.upload-item-reworked:hover {
  background-color: #e2e8f0;
}

.upload-item-reworked.selected {
  background-color: #3b82f6;
  color: white;
}

/* Styles specific to DataSourceSection, using existing class names */
/* .step-instruction, .upload-toggle-btn-reworked, etc. are assumed to be styled by parent/global CSS */
.prominent-cta { /* Ensure this style is available if used */
  background-color: var(--color-primary); color: white;
  border: none; padding: 10px 15px; border-radius: 6px;
  font-size: 1rem; font-weight: 500; cursor: pointer;
  transition: background-color 0.2s ease;
  display: flex; align-items: center; justify-content: center;
}
.prominent-cta:hover { background-color: #0056b3; }

.confirm-section {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #e2e8f0;
}

.confirm-data-btn-reworked {
  width: 100%;
  background-color: #10b981;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  margin-bottom: 8px;
}

.confirm-data-btn-reworked:hover {
  background-color: #059669;
}

.cancel-change-btn {
  width: 100%;
  background-color: #6b7280;
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: 0.9rem;
}

.cancel-change-btn:hover {
  background-color: #4b5563;
}

.change-data-btn-reworked { 
  background-color: #f59e0b; 
  color: white; 
  border: none;
  padding: 8px 12px; 
  border-radius: 4px; 
  font-size: 0.9rem; 
  margin-top: 10px; 
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.change-data-btn-reworked:hover { 
  background-color: #d97706; 
}

.data-options-list { margin-top: 15px; }
.recent-uploads-reworked h6, .toy-datasets-reworked h6 {
  font-size: 0.9rem; color: var(--text-color-secondary); margin-bottom: 8px; font-weight: 500;
}
.uploads-list-reworked { list-style: none; padding: 0; margin: 0; }
.upload-item-reworked {
  padding: 8px 10px; border-radius: 4px; cursor: pointer;
  margin-bottom: 5px; background-color: #f1f3f5; font-size: 0.85rem;
  transition: background-color 0.2s ease;
}
.upload-item-reworked:hover { background-color: #e9ecef; }
.upload-item-reworked.selected { background-color: var(--color-info); color: white; font-weight: 500; }

.show-more-btn-reworked {
  background: none; 
  border: none; 
  color: #3b82f6; 
  font-size: 0.85rem;
  cursor: pointer; 
  padding: 5px 0; 
  width: 100%; 
  text-align: left;
  transition: color 0.2s ease;
}

.show-more-btn-reworked:hover {
  color: #2563eb;
  text-decoration: underline;
}
.file-upload-area-reworked { 
  margin-top: 15px; 
  max-width: 100%;
}

.file-drop-zone-reworked {
  border: 2px dashed var(--color-primary); 
  border-radius: 8px; 
  padding: 20px 15px;
  text-align: center; 
  cursor: pointer; 
  background-color: #fdfdff;
  color: var(--color-primary); 
  font-weight: 500;
  font-size: 0.9rem;
  max-width: 100%;
  box-sizing: border-box;
}

.file-drop-zone-reworked:hover { 
  background-color: #e7f3ff; 
}

.file-drop-zone-reworked span .icon-reworked { 
  font-size: 1.2rem; 
  display: block; 
  margin-bottom: 5px;
}

.upload-status-reworked {
  padding: 10px; margin-top: 10px; border-radius: 6px; font-size: 0.9rem;
}
.upload-status-reworked.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.upload-status-reworked.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }

.data-summary-reworked {
  margin-top: 15px; padding: 10px; background-color: #e9f5ff;
  border-left: 4px solid var(--color-info); border-radius: 4px;
}
.data-summary-reworked h5 { margin: 0 0 8px 0; font-size: 0.95rem; color: var(--text-color-primary); }
.selected-file-info p { margin: 3px 0; font-size: 0.9rem; }
.toy-datasets-prompt { margin-top: 20px; }
.step-instruction { 
  font-size: 0.9rem; 
  color: #374151 !important; 
  margin-bottom: 15px; 
}

</style>
