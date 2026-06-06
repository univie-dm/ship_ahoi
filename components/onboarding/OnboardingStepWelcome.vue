<template>
  <div class="welcome-step">
    <div class="welcome-header">
      <div class="welcome-icon">👋</div>
      <h2>Welcome to SHIP.ahoi</h2>
      <p>Let's get started with your clustering analysis. First, tell us about your experience level.</p>
    </div>

    <div class="experience-options">
      <div 
        class="experience-card"
        :class="{ selected: selectedExperience === 'beginner' }"
        @click="selectExperience('beginner')"
      >
        <div class="card-icon">🎓</div>
        <div class="card-content">
          <h3>I'm New to Clustering</h3>
          <p>Get guided through the process with intelligent recommendations based on your data and goals.</p>
          <ul class="feature-list">
            <li>✓ Smart parameter suggestions</li>
            <li>✓ Step-by-step guidance</li>
            <li>✓ Best practices included</li>
          </ul>
        </div>
      </div>

      <div 
        class="experience-card"
        :class="{ selected: selectedExperience === 'experienced' }"
        @click="selectExperience('experienced')"
      >
        <div class="card-icon">🔧</div>
        <div class="card-content">
          <h3>I Know Clustering Analysis</h3>
          <p>Jump directly to parameter configuration with full control over the SHIP framework settings.</p>
          <ul class="feature-list">
            <li>✓ Direct parameter control</li>
            <li>✓ Advanced options</li>
            <li>✓ Fast setup</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="navigation">
      <div></div> <!-- Empty div for spacing -->
      <button 
        @click="proceedToNext"
        class="continue-btn"
        :disabled="!selectedExperience"
      >
        Continue →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits(['experience-selected']);

const selectedExperience = ref<'beginner' | 'experienced' | null>(null);

const selectExperience = (level: 'beginner' | 'experienced') => {
  selectedExperience.value = level;
};

const proceedToNext = () => {
  if (selectedExperience.value) {
    emit('experience-selected', selectedExperience.value);
  }
};
</script>

<style scoped>
.welcome-step {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.welcome-header {
  text-align: center;
  margin-bottom: 16px;
}

.welcome-icon {
  font-size: 4rem;
  margin-bottom: 16px;
}

.welcome-header h2 {
  font-size: 2rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 12px 0;
}

.welcome-header p {
  font-size: 1.125rem;
  color: #64748b;
  margin: 0;
}

.experience-options {
  display: grid;
  gap: 24px;
  grid-template-columns: 1fr 1fr;
}

.experience-card {
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  padding: 32px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.experience-card:hover {
  border-color: #93c5fd;
  transform: translateY(-4px);
  box-shadow: 0 12px 20px -5px rgba(59, 130, 246, 0.15), 0 8px 10px -6px rgba(59, 130, 246, 0.1);
}

.experience-card.selected {
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1), 0 2px 4px -1px rgba(59, 130, 246, 0.06);
}

.experience-card.selected::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 6px;
  background: #3b82f6;
}

.card-icon {
  font-size: 3.5rem;
  margin-bottom: 24px;
  background: #f1f5f9;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.experience-card:hover .card-icon {
  background: #dbeafe;
  transform: scale(1.1);
}

.experience-card.selected .card-icon {
  background: #3b82f6;
  color: white;
}

.card-content h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 12px 0;
}

.card-content p {
  color: #64748b;
  margin: 0 0 24px 0;
  line-height: 1.6;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
  width: 100%;
  background: #f8fafc;
  padding: 16px;
  border-radius: 8px;
}

.feature-list li {
  color: #16a34a;
  font-size: 0.9rem;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.feature-list li:last-child {
  margin-bottom: 0;
}

.navigation {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #f1f5f9;
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
  .experience-options {
    grid-template-columns: 1fr;
  }
  
  .welcome-header h2 {
    font-size: 1.5rem;
  }
  
  .welcome-icon {
    font-size: 3rem;
  }
  
  .card-icon {
    font-size: 2.5rem;
    width: 64px;
    height: 64px;
  }
}
</style> 