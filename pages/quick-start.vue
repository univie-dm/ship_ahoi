<template>
  <AppLayout :showSidebar="false">
    <template #default>
      <div class="quick-start-page">
        <div class="container">
          <!-- Header -->
          <div class="page-header">
            <button @click="handleBack" class="back-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15,18 9,12 15,6"></polyline>
              </svg>
              Back
            </button>
            <div class="header-content">
              <h1>Quick Start with Sample Data</h1>
              <p>Explore SHIP clustering with curated datasets and pre-configured parameters</p>
            </div>
          </div>

          <!-- Sample Datasets -->
          <div class="samples-section">
            <div class="samples-grid">
              <!-- Iris Dataset -->
              <div 
                class="sample-card"
                :class="{ selected: selectedSample === 'iris' }"
                @click="selectSample('iris')"
              >
                <div class="sample-header">
                  <div class="sample-icon">🌸</div>
                  <h3>Iris Flowers</h3>
                </div>
                <div class="sample-preview">
                  <DatasetPreview dataset-type="iris" :size="120" />
                </div>
                <div class="sample-info">
                  <div class="sample-stats">
                    <span>150 points</span>
                    <span>4 features</span>
                    <span>3 species</span>
                  </div>
                  <p>Classic dataset with flower measurements. Perfect for demonstrating clear cluster separation.</p>
                  <div class="sample-features">
                    <span class="feature-tag">Clear Groups</span>
                    <span class="feature-tag">Small Dataset</span>
                  </div>
                </div>
              </div>

              <!-- Wine Dataset -->
              <div 
                class="sample-card"
                :class="{ selected: selectedSample === 'wine' }"
                @click="selectSample('wine')"
              >
                <div class="sample-header">
                  <div class="sample-icon">🍷</div>
                  <h3>Wine Analysis</h3>
                </div>
                <div class="sample-preview">
                  <DatasetPreview dataset-type="wine" :size="120" />
                </div>
                <div class="sample-info">
                  <div class="sample-stats">
                    <span>178 points</span>
                    <span>13 features</span>
                    <span>3 cultivars</span>
                  </div>
                  <p>Wine chemical analysis data with overlapping clusters and higher dimensionality.</p>
                  <div class="sample-features">
                    <span class="feature-tag">Overlapping</span>
                    <span class="feature-tag">High Dimensional</span>
                  </div>
                </div>
              </div>

              <!-- Blobs Dataset -->
              <div 
                class="sample-card"
                :class="{ selected: selectedSample === 'blobs' }"
                @click="selectSample('blobs')"
              >
                <div class="sample-header">
                  <div class="sample-icon">🎯</div>
                  <h3>Synthetic Blobs</h3>
                </div>
                <div class="sample-preview">
                  <DatasetPreview dataset-type="blobs" :size="120" />
                </div>
                <div class="sample-info">
                  <div class="sample-stats">
                    <span>300 points</span>
                    <span>2 features</span>
                    <span>4 centers</span>
                  </div>
                  <p>Synthetic dataset with well-separated circular clusters. Great for understanding basics.</p>
                  <div class="sample-features">
                    <span class="feature-tag">Perfect Separation</span>
                    <span class="feature-tag">2D Visualization</span>
                  </div>
                </div>
              </div>

              <!-- Moons Dataset -->
              <div 
                class="sample-card"
                :class="{ selected: selectedSample === 'moons' }"
                @click="selectSample('moons')"
              >
                <div class="sample-header">
                  <div class="sample-icon">🌙</div>
                  <h3>Interleaving Moons</h3>
                </div>
                <div class="sample-preview">
                  <DatasetPreview dataset-type="moons" :size="120" />
                </div>
                <div class="sample-info">
                  <div class="sample-stats">
                    <span>200 points</span>
                    <span>2 features</span>
                    <span>2 crescents</span>
                  </div>
                  <p>Challenging dataset with non-linear cluster shapes. Tests advanced clustering capabilities.</p>
                  <div class="sample-features">
                    <span class="feature-tag">Non-Linear</span>
                    <span class="feature-tag">Challenging</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Selected Sample Configuration -->
            <div v-if="selectedSample" class="sample-config">
              <h3>{{ getSampleInfo(selectedSample).title }} Configuration</h3>
              <p>{{ getSampleInfo(selectedSample).description }}</p>
              
              <div class="config-preview">
                <div class="config-item">
                  <label>Tree Method:</label>
                  <span>{{ getSampleInfo(selectedSample).config.treeType }}</span>
                </div>
                <div class="config-item">
                  <label>Power Parameter:</label>
                  <span>{{ getSampleInfo(selectedSample).config.power }}</span>
                </div>
                <div class="config-item">
                  <label>Partition Method:</label>
                  <span>{{ getSampleInfo(selectedSample).config.partitionMethod }}</span>
                </div>
                <div v-if="getSampleInfo(selectedSample).config.k" class="config-item">
                  <label>Number of Clusters:</label>
                  <span>{{ getSampleInfo(selectedSample).config.k }}</span>
                </div>
              </div>

              <button @click="startQuickAnalysis" class="start-btn">
                <span class="btn-icon">🚀</span>
                Start Analysis with {{ getSampleInfo(selectedSample).title }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useGlobalState } from '~/composables/useGlobalState';

const router = useRouter();
const globalState = useGlobalState();

const selectedSample = ref('');

const sampleConfigurations = {
  iris: {
    title: 'Iris Flowers',
    description: 'Perfect for beginners - demonstrates clear cluster separation with the classic iris dataset.',
    config: {
      treeType: 'MST',
      power: 2,
      partitionMethod: 'K',
      k: 3
    }
  },
  wine: {
    title: 'Wine Analysis', 
    description: 'More challenging with overlapping clusters and higher dimensionality.',
    config: {
      treeType: 'MCSM',
      power: 1,
      partitionMethod: 'SILHOUETTE'
    }
  },
  blobs: {
    title: 'Synthetic Blobs',
    description: 'Clean synthetic data with perfect separation - ideal for understanding SHIP fundamentals.',
    config: {
      treeType: 'MST',
      power: 2,
      partitionMethod: 'K',
      k: 4
    }
  },
  moons: {
    title: 'Interleaving Moons',
    description: 'Non-linear cluster shapes that challenge traditional clustering methods.',
    config: {
      treeType: 'KNN',
      power: 3,
      partitionMethod: 'ARI'
    }
  }
};

const handleBack = () => {
  router.push('/');
};

const selectSample = (sample: string) => {
  selectedSample.value = sample;
};

const getSampleInfo = (sample: string) => {
  return sampleConfigurations[sample] || sampleConfigurations.iris;
};

const startQuickAnalysis = async () => {
  if (!selectedSample.value) return;
  
  try {
    // Load the sample data
    await globalState.loadSampleData(selectedSample.value, 300);
    
    // Set the pre-configured parameters
    const config = getSampleInfo(selectedSample.value).config;
    globalState.setClusteringParameters(config);
    
    // Navigate to clustering page
    router.push('/clustering');
  } catch (error) {
    console.error('Error starting quick analysis:', error);
  }
};
</script>

<style scoped>
.quick-start-page {
  min-height: 100vh;
  background-color: #ffffff;
  font-family: 'Inter', sans-serif;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 24px;
}

/* Header */
.page-header {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 40px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px 12px;
  color: #4b5563;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-btn:hover {
  background: #f9fafb;
  color: #111827;
  border-color: #d1d5db;
}

.header-content h1 {
  font-size: 2rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
}

.header-content p {
  font-size: 1rem;
  color: #6b7280;
  margin: 0;
  line-height: 1.5;
}

/* Samples Section */
.samples-section {
  background: transparent;
  padding: 0;
  box-shadow: none;
}

.samples-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 40px;
}

.sample-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}

.sample-card:hover {
  border-color: #d1d5db;
  background: #f9fafb;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.sample-card.selected {
  border-color: #111827;
  background: #f9fafb;
  box-shadow: 0 0 0 1px #111827;
}

.sample-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.sample-icon {
  font-size: 1.5rem;
}

.sample-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.sample-preview {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #f3f4f6;
}

.sample-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.sample-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 0.75rem;
  color: #4b5563;
  flex-wrap: wrap;
}

.sample-stats span {
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.sample-info p {
  color: #6b7280;
  margin: 0 0 16px 0;
  line-height: 1.5;
  font-size: 0.875rem;
  flex: 1;
}

.sample-features {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.feature-tag {
  background: #f3f4f6;
  color: #4b5563;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

/* Sample Config */
.sample-config {
  border-top: 1px solid #e5e7eb;
  padding-top: 32px;
  margin-top: 32px;
}

.sample-config h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 8px 0;
}

.sample-config > p {
  color: #6b7280;
  margin: 0 0 24px 0;
  font-size: 0.95rem;
}

.config-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
  padding: 24px;
  background: #f9fafb;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-item label {
  font-weight: 500;
  color: #6b7280;
  font-size: 0.75rem;
  text-transform: uppercase;
}

.config-item span {
  font-weight: 600;
  color: #111827;
  font-size: 1rem;
}

.start-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #111827;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 14px 28px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  justify-content: center;
  max-width: 400px;
  margin: 0 auto;
}

.start-btn:hover {
  background: #000000;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.btn-icon {
  font-size: 1.25rem;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .header-content h1 {
    font-size: 1.75rem;
  }
  
  .samples-grid {
    grid-template-columns: 1fr;
  }
  
  .config-preview {
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
}
</style>
