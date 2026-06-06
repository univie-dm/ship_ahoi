<template>
  <div> <div v-if="runs.length === 0" class="no-runs empty-state-reworked">
      <div class="empty-icon-reworked">🔬</div> <p>No clustering runs yet.</p>
    </div>
    <div v-else class="runs-list-reworked">
      <div 
        v-for="run in runs.slice(0, showAll ? runs.length : 10)" 
        :key="run.id" 
        :class="['run-item-reworked', { active: activeRunId === run.id }]" 
        @click="handleSelectRun(run.id)"
      >
        <div class="run-header">
          <span class="run-dataset">{{ run.dataset }}</span>
          <span class="run-time">{{ formatTime(run.timestamp) }}</span>
        </div>
        <div class="run-details">
          <span class="run-algorithm">{{ run.treeType }}</span>
          <span class="run-clusters">K={{ run.actualClusterCount || run.selectedK }}</span>
          <span class="run-points">{{ run.clusterData?.points?.length || 'N/A' }} pts</span>
        </div>
        <div class="run-actions">
          <button 
            @click.stop="handleSelectRun(run.id)" 
            title="Load Run"
          >
            📊
          </button>
          <button @click.stop="handleDeleteRun(run.id)" title="Delete Run">🗑️</button>
        </div>
      </div>
       <button 
        v-if="runs.length > 10 && !showAll" 
        @click="showAll = true" 
        class="show-more-btn-reworked"
        style="margin-top: 5px;"
        >
        Show All {{ runs.length }} Runs
        </button>
        <button 
        v-if="runs.length > 10 && showAll" 
        @click="showAll = false" 
        class="show-more-btn-reworked"
        style="margin-top: 5px;"
        >
        Show Less
        </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface Run {
  id: string;
  dataset: string;
  timestamp: Date;
  treeType: string;
  selectedK: number;
  // Add other run properties as needed
}

const props = defineProps({
  runs: { type: Array as () => Run[], default: () => [] },
  activeRunId: { type: String, default: null },
});

const emit = defineEmits(['run-selected', 'run-deleted', 'view-all-runs-page']);

const showAll = ref(false);

const formatTime = (dateInput: Date | string): string => {
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (!(date instanceof Date) || isNaN(date.getTime())) {
    return 'Invalid date';
  }
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMs / 3600000);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

const handleSelectRun = (runId: string) => emit('run-selected', runId);

const handleLoadRun = async (runId: string) => {
  // Prevent rapid clicking and duplicate loading
  if (isLoadingRun.value || loadingRunId.value === runId) {
    console.log('Load already in progress for run:', runId);
    return;
  }
  
  try {
    isLoadingRun.value = true;
    loadingRunId.value = runId;
    
    console.log(`[RecentRunsSection] Attempting to load run: ${runId}`);
    
    // Emit the load event to parent (SharedSidebar)
    emit('run-loaded', runId);
    
    console.log(`[RecentRunsSection] Successfully emitted run-loaded event for: ${runId}`);
    
  } catch (error) {
    console.error(`[RecentRunsSection] Error loading run ${runId}:`, error);
    
    // Show user-friendly error message
    alert(`Failed to load clustering run: ${error instanceof Error ? error.message : 'Unknown error'}`);
    
  } finally {
    // Reset loading state with a small delay to allow for visual feedback
    setTimeout(() => {
      isLoadingRun.value = false;
      loadingRunId.value = null;
    }, 500);
  }
};
const handleDeleteRun = (runId: string) => {
  // Confirmation should ideally be handled by a modal in the parent or global state
  // For now, using a simple confirm. Replace with a better UX.
  if (confirm('Are you sure you want to delete this run?')) {
    emit('run-deleted', runId);
  }
};

// The "View All" button in the header is handled by the parent slot.
// This component's "showAll" is for expanding the list in-place.
// If a separate page is desired, the parent's "View All" button should emit 'view-all-runs-page'.
</script>

<style scoped>
/* Styles for RecentRunsSection, using existing class names */
.no-runs.empty-state-reworked { /* Styles from original */
  text-align: center; padding: 20px; color: var(--text-color-muted); 
}
.empty-icon-reworked { font-size: 1.8rem; margin-bottom: 8px; opacity: 0.7; }

.runs-list-reworked { /* Styles from original */ }
.run-item-reworked {
  background-color: #fff; border: 1px solid #eee; border-radius: 6px;
  padding: 10px; margin-bottom: 8px; font-size: 0.85rem; cursor: pointer;
  transition: all 0.2s ease-in-out;
}
.run-item-reworked:hover {
  border-color: #ddd;
  box-shadow: 0 2px 4px rgba(0,0,0,0.07);
  transform: translateY(-1px);
}
.run-item-reworked.active {
  border-color: var(--color-primary);
  background-color: #f0f6ff;
  box-shadow: 0 0 0 2px var(--color-primary-transparent, rgba(0,123,255,0.25)); /* Use a variable if defined */
}

.run-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.run-dataset { font-weight: 500; color: var(--text-color-primary); }
.run-time { font-size: 0.8rem; color: var(--text-color-muted); }
.run-details { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.85rem; }
.run-algorithm { color: var(--text-color-secondary); }
.run-clusters { color: var(--color-info); font-weight: 500; }
.run-points { color: var(--text-color-muted); font-size: 0.8rem; }
.run-actions button {
  background: none; border: none; cursor: pointer; padding: 2px 4px;
  font-size: 1rem; color: var(--text-color-muted);
}
.run-actions button:hover { color: var(--color-primary); }
.run-actions button:disabled { 
  cursor: not-allowed; 
  opacity: 0.6; 
}
.run-actions button.loading { 
  animation: pulse 1s ease-in-out infinite; 
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.run-actions button[title="Delete Run"]:hover { color: var(--color-danger); }

.show-more-btn-reworked { /* Copied from original */
  background: none; border: none; color: var(--color-primary); font-size: 0.85rem;
  cursor: pointer; padding: 5px 0; width: 100%; text-align: left;
}
.show-more-btn-reworked:hover { text-decoration: underline; }
</style>
