<template>
  <div class="onboarding-overlay">
    <div class="onboarding-container">
      <!-- Header -->
      <div class="onboarding-header">
        <div class="header-content">
          <h1>Configure Your Analysis</h1>
          <p>Let's set up your clustering analysis with guided recommendations</p>
        </div>
        <button @click="$emit('close')" class="close-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>


      <!-- Content Area -->
      <div class="content-area">
        <!-- Questions (beginner mode) -->
        <OnboardingStepQuestions 
          v-if="currentStep === 'questions'"
          @answers-provided="handleAnswersProvided"
          @back="$emit('close')"
        />
        
        <!-- Parameters (fallback - should not be used in beginner mode) -->
        <OnboardingStepParameters 
          v-if="currentStep === 'parameters'"
          @parameters-set="handleParametersSet"
          @back="goToStep('questions')"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useGlobalState } from '~/composables/useGlobalState';
// OnboardingStepWelcome removed - always use beginner mode
import OnboardingStepQuestions from './OnboardingStepQuestions.vue';
import OnboardingStepParameters from './OnboardingStepParameters.vue';

const emit = defineEmits(['close', 'finish']);
const router = useRouter();
const globalState = useGlobalState();

// State management
const currentStep = ref<'welcome' | 'questions' | 'parameters'>('questions');
const experienceLevel = ref<'beginner' | 'experienced' | null>('beginner');
const dataSummary = ref<any>(null);

// Check if resuming onboarding from a specific step
onMounted(() => {
  // Always clear any existing session storage to ensure fresh start
  const isResuming = sessionStorage.getItem('onboardingStep') === 'parameters';
  
  if (isResuming) {
    const currentDataset = globalState.currentDataset.value;
    const storedExperienceLevel = sessionStorage.getItem('onboardingExperienceLevel') as 'beginner' | 'experienced' | null;
    
    if (currentDataset && storedExperienceLevel) {
      // We're resuming after data upload - set up the state
      console.log('Resuming onboarding at questions step (beginner mode)');
      
      // Restore experience level from session storage
      experienceLevel.value = storedExperienceLevel;
      
      // Set the data summary from the current dataset
      dataSummary.value = {
        type: currentDataset.type === 'sample' ? 'sample' : 'upload',
        name: currentDataset.name,
        value: currentDataset.sampleName,
        n_samples: currentDataset.n_samples,
        rows: currentDataset.pointCount,
        columns: currentDataset.featureCount,
        headers: currentDataset.headers,
        featureCount: currentDataset.featureCount
      };
      
      // Always go to questions step (beginner mode)
      currentStep.value = 'questions';
      
      // Clear the session storage flags
      sessionStorage.removeItem('onboardingStep');
      sessionStorage.removeItem('onboardingExperienceLevel');
      return;
    }
  }
  
  // Fresh start - clear all session storage and reset state
  sessionStorage.removeItem('onboardingInProgress');
  sessionStorage.removeItem('onboardingStep');
  sessionStorage.removeItem('onboardingExperienceLevel');
  sessionStorage.removeItem('returningFromDataUpload');
  
  // Reset all state - always start with beginner mode
  currentStep.value = 'questions';
  experienceLevel.value = 'beginner';
  dataSummary.value = null;
  
  console.log('Starting fresh onboarding from questions step (beginner mode)');
});

// Computed properties

// Step navigation
const goToStep = (step: typeof currentStep.value) => {
  currentStep.value = step;
};

// Event handlers (experience selection removed - always beginner)
// This function is no longer used but kept for compatibility

const redirectToDataUpload = () => {
  // Store onboarding state to track that we're in onboarding (always beginner)
  sessionStorage.setItem('onboardingInProgress', 'true');
  sessionStorage.setItem('onboardingStep', 'questions');
  sessionStorage.setItem('onboardingExperienceLevel', 'beginner');
  
  // Navigate to data upload page
  router.push('/data-upload?from=onboarding');
};

const handleAnswersProvided = (answers: any) => {
  // Apply the selected dataset to global state
  if (answers.selectedDataset) {
    const datasetOption = globalState.getSampleOption(answers.selectedDataset);
    globalState.setCurrentDataset({
      name: datasetOption?.label || answers.selectedDataset,
      type: 'sample',
      sampleName: answers.selectedDataset,
      pointCount: datasetOption?.typical_samples || 0,
      featureCount: datasetOption?.dimensions || 0,
      n_samples: datasetOption?.typical_samples || 0,
    });
  }

  // Convert answers to parameters for beginners and immediately finish
  const parameters = generateParametersFromAnswers(answers);
  finishOnboarding(parameters);
};

const handleParametersSet = (parameters: any) => {
  // Immediately finish with the parameters
  finishOnboarding(parameters);
};

const finishOnboarding = (parameters: any) => {
  console.log('Finishing onboarding with parameters:', parameters);
  
  // Set clustering parameters in global state
  globalState.setClusteringParameters(parameters);
  
  // Store parameters in session storage for persistence
  sessionStorage.setItem('onboardingParameters', JSON.stringify(parameters));
  
  // Mark onboarding as completed
  globalState.setOnboardingCompleted(true);
  
  // Clear onboarding flow session storage but keep parameters
  sessionStorage.removeItem('onboardingInProgress');
  sessionStorage.removeItem('onboardingStep');
  sessionStorage.removeItem('onboardingExperienceLevel');
  sessionStorage.removeItem('returningFromDataUpload');
  
  // Close wizard and redirect to clustering page
  emit('close');
  router.push('/clustering');
};

// Helper function to generate parameters from beginner answers
const generateParametersFromAnswers = (answers: any) => {
  const params: any = {};
  
  console.log('Generating parameters from answers:', answers);
  
  // Use the power parameter directly from answers if provided
  if (answers.power !== undefined) {
    params.power = answers.power;
  }
  
  // Use partition method directly from answers if provided
  if (answers.partitionMethod) {
    params.partitionMethod = answers.partitionMethod;
    if (answers.partitionMethod === 'K' && answers.clusterCount) {
      params.k = answers.clusterCount;
    }
  } else {
    // Fallback: partition method based on cluster expectation
    if (answers.expectedClusters === 'yes') {
      params.partitionMethod = 'K';
      params.k = answers.clusterCount || 5;
    } else {
      // Auto-select partition method based on data pattern
      switch (answers.dataPattern) {
        case 'clear-groups':
          params.partitionMethod = 'SILHOUETTE';
          break;
        case 'overlapping-groups':
          params.partitionMethod = 'ARI';
          break;
        case 'mixed-noise':
          params.partitionMethod = 'GAP';
          break;
        default:
          params.partitionMethod = 'SILHOUETTE';
      }
    }
  }
  
  // Tree type - use direct answer or infer from data pattern
  if (answers.treeType) {
    params.treeType = answers.treeType;
  } else {
    // Fallback: tree type based on data pattern
    switch (answers.dataPattern) {
      case 'clear-groups':
        params.treeType = 'MST';
        if (!params.power) params.power = 2;
        break;
      case 'overlapping-groups':
        params.treeType = 'MCSM';
        if (!params.power) params.power = 1;
        break;
      case 'mixed-noise':
        params.treeType = 'KNN';
        if (!params.power) params.power = 3;
        break;
      default:
        params.treeType = 'MST';
        if (!params.power) params.power = 2;
    }
  }
  
  // Ensure power is set if not already
  if (!params.power) {
    params.power = 2; // Default fallback
  }
  
  console.log('Generated parameters:', params);
  return params;
};
</script>

<style scoped>
.onboarding-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.onboarding-container {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

.onboarding-header {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 32px 32px 0;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 24px;
  position: relative;
  text-align: center;
}

.header-content h1 {
  font-size: 1.875rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 8px 0;
}

.header-content p {
  color: #64748b;
  margin: 0;
}

.close-btn {
  position: absolute;
  right: 32px;
  top: 32px;
  background: #f1f5f9;
  border: none;
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #e2e8f0;
  color: #475569;
}


.content-area {
  padding: 32px;
  min-height: 400px;
}

/* Responsive Design */
@media (max-width: 768px) {
  .onboarding-overlay {
    padding: 10px;
  }
  
  .onboarding-container {
    max-height: 95vh;
  }
  
  .onboarding-header,
  .content-area {
    padding-left: 20px;
    padding-right: 20px;
  }
  
  .header-content h1 {
    font-size: 1.5rem;
  }
}
</style> 