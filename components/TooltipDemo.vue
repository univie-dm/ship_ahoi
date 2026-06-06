<template>
  <div class="tooltip-demo">
    <h2>Tooltip System Demo</h2>
    
    <div class="demo-section">
      <h3>Basic Tooltips</h3>
      <div class="demo-grid">
        <button v-tooltip="'Simple tooltip on hover'">
          Hover me (Simple)
        </button>
        
        <button v-tooltip.click="'Click tooltip - stays open until clicked again'">
          Click me (Click)
        </button>
        
        <button v-tooltip.focus="'Focus tooltip - shows on keyboard focus'">
          Focus me (Focus)
        </button>
      </div>
    </div>

    <div class="demo-section">
      <h3>Theme Variations</h3>
      <div class="demo-grid">
        <button v-tooltip.light="'Light theme tooltip'">
          Light Theme
        </button>
        
        <button v-tooltip.info="'Info theme with blue colors'">
          Info Theme
        </button>
        
        <button v-tooltip.warning="'Warning theme for alerts'">
          Warning Theme
        </button>
        
        <button v-tooltip.error="'Error theme for problems'">
          Error Theme
        </button>
      </div>
    </div>

    <div class="demo-section">
      <h3>Size Variations</h3>
      <div class="demo-grid">
        <button v-tooltip.small="'Small tooltip for brief hints'">
          Small Size
        </button>
        
        <button v-tooltip="'Medium size tooltip (default)'">
          Medium Size
        </button>
        
        <button v-tooltip.large="'Large tooltip with more content space for detailed explanations'">
          Large Size
        </button>
      </div>
    </div>

    <div class="demo-section">
      <h3>Position Control</h3>
      <div class="demo-grid">
        <button v-tooltip.top="'Tooltip positioned above'">
          Top Position
        </button>
        
        <button v-tooltip.bottom="'Tooltip positioned below'">
          Bottom Position
        </button>
        
        <button v-tooltip.left="'Tooltip positioned to the left'">
          Left Position
        </button>
        
        <button v-tooltip.right="'Tooltip positioned to the right'">
          Right Position
        </button>
      </div>
    </div>

    <div class="demo-section">
      <h3>Predefined Content</h3>
      <div class="demo-grid">
        <button v-tooltip="{ key: 'sidebar.ultrametricTreeType' }">
          Tree Type Info
        </button>
        
        <button v-tooltip="{ key: 'sidebar.powerParameter' }">
          Power Parameter Info
        </button>
        
        <button v-tooltip="{ key: 'sidebar.partitionMethod' }">
          Partition Method Info
        </button>
      </div>
    </div>

    <div class="demo-section">
      <h3>Rich Content</h3>
      <div class="demo-grid">
        <button v-tooltip="{ key: 'indexPage.welcome.title', isRichContent: true, size: 'large' }">
          Rich HTML Content
        </button>
        
        <button 
          v-tooltip.interactive.rich="{
            content: '<h4>Interactive Tooltip</h4><p>This tooltip is <strong>interactive</strong> - you can hover over it and click elements inside.</p><ul><li>Feature 1</li><li>Feature 2</li><li>Feature 3</li></ul>',
            size: 'large'
          }"
        >
          Interactive Rich Content
        </button>
      </div>
    </div>

    <div class="demo-section">
      <h3>Accessibility Features</h3>
      <div class="demo-grid">
        <button 
          v-tooltip.focus="'This tooltip is keyboard accessible. Use Tab to focus and Escape to close.'"
          tabindex="0"
        >
          Keyboard Accessible
        </button>
        
        <button 
          v-tooltip="'Screen readers will announce this tooltip content'"
          aria-describedby="tooltip-sr"
        >
          Screen Reader Friendly
        </button>
      </div>
    </div>

    <div class="demo-section">
      <h3>Mobile Optimized</h3>
      <div class="demo-grid">
        <button 
          v-tooltip.click="{
            content: 'This tooltip is optimized for mobile devices with touch-friendly interactions',
            theme: 'info'
          }"
        >
          Mobile Friendly
        </button>
      </div>
    </div>

    <div class="usage-guide">
      <h3>Usage Guide</h3>
      <div class="code-block">
        <h4>Basic Usage:</h4>
        <pre><code>&lt;button v-tooltip="'Simple tooltip'"&gt;Hover me&lt;/button&gt;</code></pre>
        
        <h4>With Modifiers:</h4>
        <pre><code>&lt;button v-tooltip.click.info.large="'Advanced tooltip'"&gt;Click me&lt;/button&gt;</code></pre>
        
        <h4>Predefined Content:</h4>
        <pre><code>&lt;button v-tooltip="{ key: 'sidebar.ultrametricTreeType' }"&gt;Info&lt;/button&gt;</code></pre>
        
        <h4>Rich Content:</h4>
        <pre><code>&lt;div v-tooltip.rich="{ content: '&lt;h4&gt;Title&lt;/h4&gt;&lt;p&gt;Content&lt;/p&gt;' }"&gt;Rich&lt;/div&gt;</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// This component demonstrates all tooltip functionality
// Can be used for testing and as documentation
</script>

<style scoped>
.tooltip-demo {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  font-family: 'Inter', system-ui, sans-serif;
}

.demo-section {
  margin-bottom: 32px;
  padding: 20px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e9e9e7;
}

.demo-section h3 {
  margin: 0 0 16px 0;
  color: #37352f;
  font-size: 1.125rem;
  font-weight: 600;
}

.demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  align-items: center;
}

.demo-grid button {
  padding: 12px 16px;
  background: #f7f6f3;
  border: 1px solid #e9e9e7;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  color: #37352f;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: 'Inter', system-ui, sans-serif;
}

.demo-grid button:hover {
  background: #e9e9e7;
  border-color: #d9d9d7;
}

.demo-grid button:focus {
  outline: 2px solid #2383e2;
  outline-offset: 2px;
}

.usage-guide {
  background: #f8fafc;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.usage-guide h3 {
  margin: 0 0 20px 0;
  color: #1a202c;
  font-size: 1.25rem;
  font-weight: 600;
}

.usage-guide h4 {
  margin: 16px 0 8px 0;
  color: #2d3748;
  font-size: 1rem;
  font-weight: 600;
}

.code-block {
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
}

.code-block pre {
  background: #1a202c;
  color: #e2e8f0;
  padding: 12px 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.875rem;
  line-height: 1.5;
  margin: 8px 0 16px 0;
}

@media (max-width: 768px) {
  .demo-grid {
    grid-template-columns: 1fr;
  }
  
  .tooltip-demo {
    padding: 16px;
  }
  
  .demo-section {
    padding: 16px;
  }
}
</style>