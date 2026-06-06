<template>
  <div class="app-layout">
    <!-- Floating Toggle Button (outside of sidebar container) -->
    <button 
      v-if="globalState.sidebarHidden.value && showSidebar"
      class="floating-toggle" 
      @click="toggleSidebar"
      title="Show Sidebar (Ctrl+B)"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="9" y1="3" x2="9" y2="21"></line>
      </svg>
    </button>
    
    <header class="app-header">
      <div class="logo-title">
        <h1>SHIP.AHOI Clustering Exploration</h1>
      </div>
      <NavigationBar v-if="showNavbar" />
    </header>
    <div class="main-content-wrapper">
      <aside v-if="showSidebar" class="sidebar" :class="{ 'sidebar-hidden': globalState.sidebarHidden.value }">
        <slot name="sidebar"></slot>
      </aside>
      <main class="content-area" :class="{ 'sidebar-hidden': globalState.sidebarHidden.value && showSidebar }">
        <slot></slot>
      </main>
    </div>
    
    <!-- Global Tooltip Manager -->
    <GlobalTooltipManager />
  </div>
</template>

<script setup lang="ts">
import { useGlobalState } from '~/composables/useGlobalState'
import { onMounted, onUnmounted, defineProps } from 'vue'

const globalState = useGlobalState()

const props = defineProps({
  showSidebar: {
    type: Boolean,
    default: true
  },
  showNavbar: {
    type: Boolean,
    default: true
  }
})

const toggleSidebar = () => {
  globalState.toggleSidebar()
}

// Keyboard shortcut for sidebar toggle
const handleKeydown = (event: KeyboardEvent) => {
  if (event.ctrlKey && event.key === 'b') {
    event.preventDefault()
    toggleSidebar()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--page-bg-alternate);
  font-family: var(--font-family-primary);
  /* Global scroll optimization */
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  transform: translateZ(0);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-6);
  background-color: var(--bg-primary);
  border-bottom: 1px solid var(--border-primary);
  z-index: 10;
  flex-shrink: 0;
}

.logo-title h1 {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
  letter-spacing: -0.025em;
}

.main-content-wrapper {
  display: flex;
  flex-grow: 1;
  overflow: hidden;
  /* Optimize main content scrolling */
  contain: layout style;
  transform: translateZ(0);
}

.sidebar {
  width: 320px;
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: var(--border-secondary) transparent;
  /* Optimized transitions - reduced duration */
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), width 0.2s cubic-bezier(0.4, 0, 0.2, 1), margin-left 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  /* Advanced scroll performance */
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  transform: translateZ(0);
  will-change: transform;
  /* Prevent scroll lag */
  overflow-anchor: none;
  touch-action: pan-y;
  contain: layout style;
}

.sidebar.sidebar-hidden {
  transform: translateX(-100%);
  width: 0;
  border-right: none;
  margin-left: -320px; /* Pull it off screen completely */
}

.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar::-webkit-scrollbar-thumb {
  background: var(--border-secondary);
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

.content-area {
  flex-grow: 1;
  padding: var(--space-6);
  overflow-y: auto;
  background-color: var(--page-bg-alternate);
  scrollbar-width: thin;
  scrollbar-color: var(--border-secondary) transparent;
  transition: margin-left 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.content-area.sidebar-hidden {
  margin-left: 0;
}

.content-area::-webkit-scrollbar {
  width: 6px;
}

.content-area::-webkit-scrollbar-track {
  background: transparent;
}

.content-area::-webkit-scrollbar-thumb {
  background: var(--border-secondary);
  border-radius: 3px;
}

.content-area::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

/* Floating toggle button */
.floating-toggle {
  position: fixed;
  top: 70px;
  left: 20px;
  z-index: 9999;
  background-color: var(--bg-primary);
  color: var(--text-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-base);
  padding: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-md);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  min-height: 36px;
}

.floating-toggle:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
  box-shadow: var(--shadow-lg);
  transform: translateY(-1px);
}

/* Responsive Design */

/* Small laptops and large tablets */
@media (max-width: 1200px) {
  .sidebar {
    width: 280px;
  }
  
  .sidebar.sidebar-hidden {
    margin-left: -280px;
  }
  
  .content-area {
    padding: var(--space-4);
  }
  
  .app-header {
    padding: var(--space-3) var(--space-4);
  }
}

/* Medium tablets */
@media (max-width: 1024px) {
  .sidebar {
    width: 260px;
  }
  
  .sidebar.sidebar-hidden {
    margin-left: -260px;
  }
  
  .content-area {
    padding: var(--space-3);
  }
}

/* Small tablets and mobile landscape */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 60px;
    left: 0;
    bottom: 0;
    width: 280px;
    z-index: 1000;
    box-shadow: var(--shadow-xl);
    border-right: 1px solid var(--border-primary);
    margin-left: 0;
  }
  
  .sidebar.sidebar-hidden {
    transform: translateX(-100%);
    width: 280px; /* Keep width for proper animation */
    margin-left: 0;
  }
  
  .content-area {
    padding: var(--space-3);
    margin-left: 0 !important; /* Always full width on mobile */
  }
  
  .app-header {
    padding: var(--space-2) var(--space-4);
    position: relative;
    z-index: 1001; /* Above sidebar */
  }
  
  .logo-title h1 {
    font-size: var(--font-size-base);
  }
  
  .floating-toggle {
    top: 12px;
    left: 12px;
    padding: 6px;
    min-width: 32px;
    min-height: 32px;
  }
}

/* Mobile portrait */
@media (max-width: 480px) {
  .sidebar {
    width: 260px;
    top: 56px; /* Adjust for smaller header */
  }
  
  .sidebar.sidebar-hidden {
    width: 260px;
  }
  
  .content-area {
    padding: var(--space-2);
  }
  
  .app-header {
    padding: var(--space-2) var(--space-3);
    min-height: 56px;
  }
  
  .logo-title h1 {
    font-size: var(--font-size-sm);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
  }
  
  .floating-toggle {
    top: 10px;
    left: 10px;
  }
}

/* Very small screens */
@media (max-width: 320px) {
  .sidebar {
    width: 240px;
  }
  
  .sidebar.sidebar-hidden {
    width: 240px;
  }
  
  .logo-title h1 {
    font-size: 0.85rem;
    max-width: 160px;
  }
}

/* Touch device optimizations */
@media (hover: none) and (pointer: coarse) {
  .floating-toggle {
    min-width: 44px;
    min-height: 44px;
    padding: 8px;
  }
  
  .sidebar {
    /* Larger touch scrollbar */
    scrollbar-width: auto;
  }
  
  .sidebar::-webkit-scrollbar {
    width: 12px;
  }
  
  .sidebar::-webkit-scrollbar-thumb {
    background: var(--border-secondary);
    border-radius: 6px;
  }
}

/* High DPI screens */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .sidebar,
  .content-area {
    /* Sharper scrollbars on high DPI */
    scrollbar-width: thin;
  }
  
  .sidebar::-webkit-scrollbar,
  .content-area::-webkit-scrollbar {
    width: 4px;
  }
}

/* Landscape orientation on mobile */
@media (max-width: 768px) and (orientation: landscape) {
  .app-header {
    padding: 4px 16px;
    min-height: 48px;
  }
  
  .sidebar {
    top: 48px;
    width: 260px;
  }
  
  .floating-toggle {
    top: 8px;
    left: 8px;
  }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .sidebar,
  .content-area,
  .floating-toggle {
    transition: none;
  }
}
</style>
