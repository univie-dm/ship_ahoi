<template>
  <div class="questions-step">
    <div class="step-header">
      <h2>Configure Your Clustering Analysis</h2>
      <p>Answer these questions to automatically set the optimal clustering parameters</p>
    </div>

    <div class="questions-container">
      <Transition name="fade" mode="out-in">
        <div v-if="currentQuestion === 1" class="question-card" key="q1">
          <!-- Question 1: Partition Method Selection -->
          <h3>How do you want to determine the number of clusters?</h3>
          <p class="question-description">This directly sets your partition method parameter.</p>
          
          <div class="option-cards">
            <div 
              class="option-card" 
              :class="{ selected: answers.partitionMethod === 'K' }"
              @click="selectAnswer('partitionMethod', 'K')"
            >
              <div class="card-icon">🎯</div>
              <div class="card-content">
                <h4>I know the exact number (K)</h4>
                <p> I have a specific number of clusters in mind</p>
                <div class="card-example">K: Use when you know your data structure</div>
              </div>
            </div>

            <div 
              class="option-card" 
              :class="{ selected: answers.partitionMethod === 'Elbow' }"
              @click="selectAnswer('partitionMethod', 'Elbow')"
            >
              <div class="card-icon">📈</div>
              <div class="card-content">
                <h4>Find optimal using Elbow method</h4>
                <p>Automatically find the "elbow" point in clustering quality</p>
                <div class="card-example">Elbow: Use when you want automatic, interpretable results</div>
              </div>
            </div>

            <div 
              class="option-card" 
              :class="{ selected: answers.partitionMethod === 'Stability' }"
              @click="selectAnswer('partitionMethod', 'Stability')"
            >
              <div class="card-icon">⚖️</div>
              <div class="card-content">
                <h4>Find most stable clustering</h4>
                <p>Choose the number that gives most consistent results</p>
                <div class="card-example">Stability: Use when you need robust, reliable clusters</div>
              </div>
            </div>
          </div>

          <!-- Number input if K is selected -->
          <div v-if="answers.partitionMethod === 'K'" class="number-input-section">
            <label for="cluster-count">How many clusters do you expect?</label>
            <input 
              type="number" 
              id="cluster-count"
              v-model.number="answers.clusterCount"
              min="2" 
              max="20" 
              class="number-input"
            />
          </div>
        </div>

        <div v-else-if="currentQuestion === 2" class="question-card" key="q2">
          <!-- Question 2: Tree Type Selection -->
          <h3>What type of data structure do you expect?</h3>
          <p class="question-description">This determines the tree type used for hierarchical clustering.</p>
          
          <div class="option-cards">
            <div 
              class="option-card" 
              :class="{ selected: answers.treeType === 'DCTree' }"
              @click="selectAnswer('treeType', 'DCTree')"
            >
              <div class="card-icon">🌳</div>
              <div class="card-content">
                <h4>General purpose data</h4>
                <p>Works well for most datasets with mixed characteristics</p>
                <div class="card-example">DCTree: Balanced performance and interpretability</div>
              </div>
            </div>

            <div 
              class="option-card" 
              :class="{ selected: answers.treeType === 'CoverTree' }"
              @click="selectAnswer('treeType', 'CoverTree')"
            >
              <div class="card-icon">🎯</div>
              <div class="card-content">
                <h4>High-dimensional data</h4>
                <p>Optimized for data with many features or dimensions</p>
                <div class="card-example">CoverTree: Efficient for complex, high-D datasets</div>
              </div>
            </div>

            <div 
              class="option-card" 
              :class="{ selected: answers.treeType === 'BallTree' }"
              @click="selectAnswer('treeType', 'BallTree')"
            >
              <div class="card-icon">⚡</div>
              <div class="card-content">
                <h4>Fast processing needed</h4>
                <p>Optimized for speed with large datasets</p>
                <div class="card-example">BallTree: Quick results for time-sensitive analysis</div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="currentQuestion === 3" class="question-card" key="q3">
          <!-- Question 3: Power Parameter (Distance Sensitivity) -->
          <h3>How tight should your clusters be?</h3>
          <p class="question-description">This sets the power parameter that controls distance sensitivity in clustering.</p>
          
          <div class="option-cards">
            <div 
              class="option-card" 
              :class="{ selected: answers.power === 2 }"
              @click="selectAnswer('power', 2)"
            >
              <div class="card-icon">🎯</div>
              <div class="card-content">
                <h4>Balanced clustering (Power = 2)</h4>
                <p>Standard Euclidean distance - works for most cases</p>
                <div class="card-example">Best for: General datasets, moderate cluster tightness</div>
              </div>
            </div>

            <div 
              class="option-card" 
              :class="{ selected: answers.power === 4 }"
              @click="selectAnswer('power', 4)"
            >
              <div class="card-icon">🔒</div>
              <div class="card-content">
                <h4>Tight clusters (Power = 4)</h4>
                <p>Emphasizes closer points more strongly</p>
                <div class="card-example">Best for: Well-separated groups, clear boundaries</div>
              </div>
            </div>

            <div 
              class="option-card" 
              :class="{ selected: answers.power === 6 }"
              @click="selectAnswer('power', 6)"
            >
              <div class="card-icon">💎</div>
              <div class="card-content">
                <h4>Very tight clusters (Power = 6)</h4>
                <p>Maximum emphasis on very close points</p>
                <div class="card-example">Best for: Dense, compact clusters with outliers</div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <!-- Progress Indicator -->
    <div class="question-progress">
      <div class="progress-dots">
        <div v-for="i in totalQuestions" :key="i" class="progress-dot" :class="{ active: i <= currentQuestion }"></div>
      </div>
      <p>Question {{ currentQuestion }} of {{ totalQuestions }}</p>
    </div>

    <!-- Navigation -->
    <div class="navigation">
      <button 
        v-if="currentQuestion > 1" 
        @click="prevQuestion" 
        class="back-btn"
      >
        ← Previous
      </button>
      <button @click="$emit('back')" class="back-btn" v-else>
        ← Back to Data
      </button>
      
      <button 
        @click="nextQuestion" 
        class="continue-btn" 
        :disabled="!isCurrentQuestionAnswered"
      >
        {{ currentQuestion === totalQuestions ? 'Generate Parameters' : 'Next Question' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

const emit = defineEmits(['answers-provided', 'back']);

const currentQuestion = ref(1);
const totalQuestions = 3;

interface AnswersType {
  partitionMethod: string;
  clusterCount: number;
  treeType: string;
  power: number;
}

const answers = ref<AnswersType>({
  partitionMethod: '',
  clusterCount: 3,
  treeType: '',
  power: 2
});

const selectAnswer = (key: keyof AnswersType, value: string | number) => {
  if (key === 'clusterCount') {
    answers.value[key] = parseInt(value as string) || 3;
  } else if (key === 'power') {
    answers.value[key] = value as number;
  } else {
    (answers.value as any)[key] = value;
  }
};

const isCurrentQuestionAnswered = computed(() => {
  switch (currentQuestion.value) {
    case 1:
      return answers.value.partitionMethod !== '';
    case 2:
      return answers.value.treeType !== '';
    case 3:
      return answers.value.power !== null && answers.value.power !== undefined;
    default:
      return false;
  }
});

const prevQuestion = () => {
  if (currentQuestion.value > 1) {
    currentQuestion.value--;
  }
};

const nextQuestion = () => {
  if (currentQuestion.value < totalQuestions) {
    currentQuestion.value++;
  } else {
    // Emit answers to parent
    emit('answers-provided', answers.value);
  }
};
</script>

<style scoped>
.questions-step {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.step-header {
  text-align: center;
}

.step-header h2 {
  font-size: 1.75rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 8px 0;
}

.step-header p {
  color: #64748b;
  margin: 0;
}

.questions-container {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 32px;
  min-height: 400px;
}

.question-card h3 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 8px 0;
  text-align: center;
}

.question-description {
  font-size: 1rem;
  color: #64748b;
  text-align: center;
  margin: 0 0 32px 0;
}

.option-cards {
  display: grid;
  gap: 16px;
  margin-bottom: 24px;
}

.option-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: #ffffff;
  position: relative;
  overflow: hidden;
}

.option-card:hover {
  border-color: #93c5fd;
  transform: translateY(-4px);
  box-shadow: 0 12px 20px -5px rgba(59, 130, 246, 0.15), 0 8px 10px -6px rgba(59, 130, 246, 0.1);
}

.option-card.selected {
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1), 0 2px 4px -1px rgba(59, 130, 246, 0.06);
}

.option-card.selected::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 6px;
  height: 100%;
  background: #3b82f6;
}

.card-icon {
  font-size: 2.5rem;
  flex-shrink: 0;
  background: #f1f5f9;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.option-card:hover .card-icon {
  background: #dbeafe;
  transform: scale(1.1);
}

.option-card.selected .card-icon {
  background: #3b82f6;
  color: white;
}

.card-content {
  flex: 1;
}

.card-content h4 {
  font-size: 1.125rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 4px 0;
}

.card-content p {
  font-size: 0.95rem;
  color: #64748b;
  margin: 0 0 12px 0;
  line-height: 1.5;
}

.card-example {
  font-size: 0.8rem;
  color: #3b82f6;
  font-weight: 600;
  background: rgba(59, 130, 246, 0.1);
  padding: 6px 12px;
  border-radius: 20px;
  display: inline-block;
}

.number-input-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: #f8fafc;
  border-radius: 12px;
  margin-top: 24px;
  border: 1px solid #e2e8f0;
}

.number-input-section label {
  font-weight: 600;
  color: #374151;
}

.number-input {
  padding: 10px 16px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
  width: 100px;
  transition: border-color 0.2s;
}

.number-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.question-progress {
  text-align: center;
  margin-top: 8px;
}

.progress-dots {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 12px;
}

.progress-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #e2e8f0;
  transition: all 0.3s ease;
}

.progress-dot.active {
  background: #3b82f6;
  transform: scale(1.2);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

.question-progress p {
  color: #64748b;
  margin: 0;
  font-size: 0.875rem;
  font-weight: 500;
}

.navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

.back-btn {
  background: white;
  color: #64748b;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: #f8fafc;
  color: #475569;
  border-color: #cbd5e1;
}

.continue-btn {
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px 32px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
}

.continue-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 6px 8px -1px rgba(59, 130, 246, 0.3);
}

.continue-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  box-shadow: none;
}

/* Responsive Design */
@media (max-width: 768px) {
  .questions-container {
    padding: 20px;
  }
  
  .option-card {
    flex-direction: column;
    text-align: center;
  }
  
  .number-input-section {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
