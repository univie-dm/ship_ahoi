// composables/useSidebarState.ts
import { ref, reactive, computed, watch } from 'vue';

export type SidebarSectionKey =
  | 'dataSource'
  | 'parameters'
  | 'visualization'
  | 'recentRuns'
  | 'pageControls'
  | 'exportVisualizations'
  | 'dataManagement';

interface SidebarState {
  sectionCollapsed: Record<SidebarSectionKey, boolean>;
  currentStep: 'dataSource' | 'parameters' | 'visualization' | 'other';
  dataUploaded: boolean;
  parametersConfigured: boolean;
  selectedSample?: string | null;
}

const STORAGE_KEY = 'sidebarStateV3';

function loadState(): SidebarState {
  const defaultState = {
    sectionCollapsed: {
      dataSource: false,
      parameters: true,
      visualization: true,
      recentRuns: true,
      pageControls: true,
      exportVisualizations: true,
      dataManagement: true, // Always collapsed by default
    },
    currentStep: 'dataSource',
    dataUploaded: false,
    parametersConfigured: false,
    selectedSample: null,
  };

  if (typeof window !== 'undefined') {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        // Merge with default state to ensure all keys exist
        return {
          ...defaultState,
          ...parsed,
          sectionCollapsed: {
            ...defaultState.sectionCollapsed,
            ...parsed.sectionCollapsed,
          },
        };
      } catch {}
    }
  }
  return defaultState;
}

function saveState(state: SidebarState) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }
}

export function useSidebarState() {
  const state = reactive(loadState());

  watch(
    state,
    (val) => {
      saveState(val);
    },
    { deep: true }
  );

  function reset() {
    Object.assign(state, loadState());
  }

  function setStep(step: SidebarState['currentStep']) {
    state.currentStep = step;
  }

  function setSectionCollapsed(section: SidebarSectionKey, collapsed: boolean) {
    state.sectionCollapsed[section] = collapsed;
  }

  function setDataUploaded(val: boolean) {
    state.dataUploaded = val;
  }

  function setParametersConfigured(val: boolean) {
    state.parametersConfigured = val;
  }

  function setSelectedSample(val: string | null) {
    state.selectedSample = val;
  }

  function toggleSection(section: SidebarSectionKey) {
    state.sectionCollapsed[section] = !state.sectionCollapsed[section];
  }

  return {
    state,
    reset,
    setStep,
    setSectionCollapsed,
    setDataUploaded,
    setParametersConfigured,
    setSelectedSample,
    toggleSection,
  };
}
