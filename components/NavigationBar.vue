<script setup lang="ts">
import { useBackgroundKSelection } from '~/composables/useBackgroundKSelection'

const { isRunning: kSelectionRunning } = useBackgroundKSelection()
</script>

<template>
  <nav class="navigation-bar">
    <div class="nav-items">
      <NuxtLink to="/" class="nav-item">
        <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 8.5A1.5 1.5 0 1 0 8 5.5a1.5 1.5 0 0 0 0 3zM8 4a4 4 0 1 1 0 8 4 4 0 0 1 0-8z"/>
        </svg>
        <span>Onboarding</span>
      </NuxtLink>

      <NuxtLink to="/explanation" class="nav-item">
        <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
          <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
        </svg>
        <span>Explanations</span>
      </NuxtLink>
      
      <NuxtLink to="/clustering" class="nav-item">
        <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M2 4a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm7 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm-5 8a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm7 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0z"/>
        </svg>
        <span>Clustering</span>
      </NuxtLink>
      
      <NuxtLink to="/k-selection" class="nav-item">
        <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M1.5 2.5A1.5 1.5 0 0 1 3 1h10a1.5 1.5 0 0 1 1.5 1.5v11A1.5 1.5 0 0 1 13 15H3a1.5 1.5 0 0 1-1.5-1.5v-11zM3 2a.5.5 0 0 0-.5.5V5h11V2.5a.5.5 0 0 0-.5-.5H3zM2.5 6v7a.5.5 0 0 0 .5.5h10a.5.5 0 0 0 .5-.5V6h-11z"/>
        </svg>
        <span>K-Selection</span>
        <span v-if="kSelectionRunning" class="bg-activity-dot" title="K-Selection analysis running in background"></span>
      </NuxtLink>
      
      <NuxtLink to="/data-explorer" class="nav-item">
        <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M6 0H2a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h4V6.5a.5.5 0 0 1 .5-.5H8v-.5a2 2 0 0 0-2-2zM8 8v6h6a2 2 0 0 0 2-2V8H8z"/>
        </svg>
        <span>Data Explorer</span>
      </NuxtLink>
      
      <NuxtLink to="/clustering-explorer" class="nav-item">
        <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M2 4a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm7 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm-5 8a2 2 0 1 1 4 0 2 2 0 0 1-4 0zm7 0a2 2 0 1 1 4 0 2 2 0 0 1-4 0zM8 3a1 1 0 1 0 0 2 1 1 0 0 0 0-2zM3 8a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm8 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>
        </svg>
        <span>Clustering Explorer</span>
      </NuxtLink>
      
      <NuxtLink to="/history" class="nav-item">
        <svg class="nav-icon" width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M2.5 3A1.5 1.5 0 0 0 1 4.5v.793c.026.009.051.02.076.032L7.674 8.51c.206.1.446.1.652 0l6.598-3.185A.755.755 0 0 1 15 5.293V4.5A1.5 1.5 0 0 0 13.5 3h-11Z"/>
          <path d="M15 6.954 8.978 9.86a2.25 2.25 0 0 1-1.956 0L1 6.954V11.5A1.5 1.5 0 0 0 2.5 13h11a1.5 1.5 0 0 0 1.5-1.5V6.954Z"/>
        </svg>
        <span>History & Comarpison </span>
      </NuxtLink>
      
    </div>
  </nav>
</template>

<style scoped>
.navigation-bar {
  padding: 0;
  background-color: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.nav-items {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 0 16px;
  height: 48px;
  overflow-x: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

.nav-items::-webkit-scrollbar {
  display: none; /* Chrome/Safari */
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: #6b7280;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
  font-family: 'Inter', system-ui, sans-serif;
  white-space: nowrap;
  height: 32px;
}

.nav-item:hover {
  color: #111827;
  background-color: #f3f4f6;
  text-decoration: none;
}

.nav-item.router-link-active {
  color: #111827;
  background-color: #f3f4f6;
  font-weight: 600;
  text-decoration: none;
}

.nav-icon {
  width: 16px;
  height: 16px;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.nav-item:hover .nav-icon,
.nav-item.router-link-active .nav-icon {
  opacity: 1;
  color: #111827;
}

.nav-item span {
  font-size: 0.875rem;
}

.bg-activity-dot {
  width: 8px;
  height: 8px;
  min-width: 8px;
  border-radius: 50%;
  background-color: #3b82f6;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.75); }
}

/* Responsive Design */

/* Tablet */
@media (max-width: 1024px) {
  .nav-items {
    gap: 4px;
    padding: 0 12px;
  }
  
  .nav-item {
    padding: 6px 10px;
    font-size: 0.8125rem;
  }
}

/* Mobile */
@media (max-width: 768px) {
  .nav-items {
    gap: 4px;
    padding: 0 8px;
  }
  
  .nav-item {
    padding: 6px 8px;
  }
  
  .nav-item span {
    display: none;
  }
  
  .nav-icon {
    width: 18px;
    height: 18px;
  }
}

/* Small Mobile */
@media (max-width: 480px) {
  .nav-items {
    justify-content: space-between;
  }
  
  .nav-item {
    flex: 1;
    justify-content: center;
  }
}

/* Print styles */
@media print {
  .navigation-bar {
    display: none;
  }
}
</style>
