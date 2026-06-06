<template>
  <div v-if="isLoading" class="loading-bar">
    <div class="loading-content">
      <div class="spinner"></div>
      <span class="loading-message">{{ message }}</span>
    </div>
    <button @click="onAbort" class="abort-btn" :disabled="isAborting">
      {{ isAborting ? 'Aborting...' : 'Abort' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  isLoading: boolean
  message?: string
  onAbort?: () => void
}

const props = withDefaults(defineProps<Props>(), {
  message: 'Processing...',
  onAbort: () => {}
})

const isAborting = ref(false)

const handleAbort = () => {
  isAborting.value = true
  props.onAbort()
  // Reset aborting state after a short delay
  setTimeout(() => {
    isAborting.value = false
  }, 1000)
}
</script>

<style scoped>
.loading-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 20px;
  margin: 16px 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.loading-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-message {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  font-family: 'Inter', system-ui, sans-serif;
}

.abort-btn {
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Inter', system-ui, sans-serif;
}

.abort-btn:hover:not(:disabled) {
  background: #dc2626;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
}

.abort-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.abort-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
}

/* Responsive design */
@media (max-width: 768px) {
  .loading-bar {
    flex-direction: column;
    gap: 12px;
    padding: 16px;
  }
  
  .loading-content {
    justify-content: center;
  }
  
  .abort-btn {
    align-self: center;
    min-width: 120px;
  }
}

@media (max-width: 480px) {
  .loading-bar {
    padding: 12px;
  }
  
  .loading-message {
    font-size: 0.8rem;
  }
  
  .abort-btn {
    padding: 10px 20px;
    font-size: 0.8rem;
  }
}
</style>