<template>
  <div class="dataset-preview">
    <div class="preview-container">
      <svg
        :width="size"
        :height="size"
        viewBox="0 0 100 100"
        class="preview-svg"
      >
        <g v-if="datasetType === 'blobs'">
          <!-- Blobs dataset visualization -->
          <circle cx="30" cy="30" r="8" fill="#3b82f6" opacity="0.7"/>
          <circle cx="35" cy="25" r="6" fill="#3b82f6" opacity="0.7"/>
          <circle cx="25" cy="35" r="7" fill="#3b82f6" opacity="0.7"/>
          
          <circle cx="70" cy="30" r="8" fill="#ef4444" opacity="0.7"/>
          <circle cx="75" cy="35" r="6" fill="#ef4444" opacity="0.7"/>
          <circle cx="65" cy="25" r="7" fill="#ef4444" opacity="0.7"/>
          
          <circle cx="50" cy="70" r="8" fill="#10b981" opacity="0.7"/>
          <circle cx="45" cy="75" r="6" fill="#10b981" opacity="0.7"/>
          <circle cx="55" cy="65" r="7" fill="#10b981" opacity="0.7"/>
        </g>
        
        <g v-else-if="datasetType === 'moons'">
          <!-- Moons dataset visualization -->
          <path 
            d="M 20 50 Q 30 20, 50 30 Q 70 40, 80 50" 
            stroke="#3b82f6" 
            stroke-width="8" 
            fill="none" 
            opacity="0.7"
          />
          <path 
            d="M 80 50 Q 70 80, 50 70 Q 30 60, 20 50" 
            stroke="#ef4444" 
            stroke-width="8" 
            fill="none" 
            opacity="0.7"
          />
          <!-- Add some dots for scatter effect -->
          <circle cx="25" cy="45" r="2" fill="#3b82f6"/>
          <circle cx="35" cy="35" r="2" fill="#3b82f6"/>
          <circle cx="45" cy="40" r="2" fill="#3b82f6"/>
          <circle cx="65" cy="45" r="2" fill="#3b82f6"/>
          <circle cx="75" cy="55" r="2" fill="#3b82f6"/>
          
          <circle cx="75" cy="45" r="2" fill="#ef4444"/>
          <circle cx="65" cy="55" r="2" fill="#ef4444"/>
          <circle cx="55" cy="60" r="2" fill="#ef4444"/>
          <circle cx="35" cy="65" r="2" fill="#ef4444"/>
          <circle cx="25" cy="55" r="2" fill="#ef4444"/>
        </g>
        
        <g v-else-if="datasetType === 'circles'">
          <!-- Circles dataset visualization -->
          <circle cx="50" cy="50" r="30" stroke="#3b82f6" stroke-width="6" fill="none" opacity="0.7"/>
          <circle cx="50" cy="50" r="15" stroke="#ef4444" stroke-width="6" fill="none" opacity="0.7"/>
          <!-- Add some dots -->
          <circle cx="50" cy="20" r="2" fill="#3b82f6"/>
          <circle cx="70" cy="35" r="2" fill="#3b82f6"/>
          <circle cx="80" cy="50" r="2" fill="#3b82f6"/>
          <circle cx="70" cy="65" r="2" fill="#3b82f6"/>
          <circle cx="50" cy="80" r="2" fill="#3b82f6"/>
          <circle cx="30" cy="65" r="2" fill="#3b82f6"/>
          <circle cx="20" cy="50" r="2" fill="#3b82f6"/>
          <circle cx="30" cy="35" r="2" fill="#3b82f6"/>
          
          <circle cx="50" cy="35" r="2" fill="#ef4444"/>
          <circle cx="60" cy="50" r="2" fill="#ef4444"/>
          <circle cx="50" cy="65" r="2" fill="#ef4444"/>
          <circle cx="40" cy="50" r="2" fill="#ef4444"/>
        </g>
        
        <g v-else-if="datasetType === 'aniso'">
          <!-- Anisotropic dataset visualization -->
          <ellipse cx="30" cy="40" rx="15" ry="8" fill="#3b82f6" opacity="0.5" transform="rotate(-30 30 40)"/>
          <ellipse cx="70" cy="35" rx="12" ry="6" fill="#ef4444" opacity="0.5" transform="rotate(45 70 35)"/>
          <ellipse cx="50" cy="70" rx="18" ry="7" fill="#10b981" opacity="0.5" transform="rotate(15 50 70)"/>
          <!-- Add some dots -->
          <circle cx="25" cy="35" r="2" fill="#3b82f6"/>
          <circle cx="35" cy="45" r="2" fill="#3b82f6"/>
          <circle cx="65" cy="30" r="2" fill="#ef4444"/>
          <circle cx="75" cy="40" r="2" fill="#ef4444"/>
          <circle cx="45" cy="65" r="2" fill="#10b981"/>
          <circle cx="55" cy="75" r="2" fill="#10b981"/>
        </g>
        
        <g v-else-if="datasetType === 'varied'">
          <!-- Varied density dataset visualization -->
          <circle cx="25" cy="25" r="12" fill="#3b82f6" opacity="0.3"/>
          <circle cx="25" cy="25" r="3" fill="#3b82f6"/>
          <circle cx="20" cy="30" r="2" fill="#3b82f6"/>
          <circle cx="30" cy="20" r="2" fill="#3b82f6"/>
          
          <circle cx="75" cy="25" r="20" fill="#ef4444" opacity="0.2"/>
          <circle cx="75" cy="25" r="3" fill="#ef4444"/>
          <circle cx="70" cy="35" r="2" fill="#ef4444"/>
          <circle cx="80" cy="15" r="2" fill="#ef4444"/>
          <circle cx="65" cy="20" r="2" fill="#ef4444"/>
          <circle cx="85" cy="30" r="2" fill="#ef4444"/>
          
          <circle cx="50" cy="75" r="8" fill="#10b981" opacity="0.4"/>
          <circle cx="50" cy="75" r="3" fill="#10b981"/>
          <circle cx="45" cy="70" r="2" fill="#10b981"/>
          <circle cx="55" cy="80" r="2" fill="#10b981"/>
        </g>
        
        <g v-else-if="datasetType === 'nostructure'">
          <!-- No structure dataset visualization -->
          <circle cx="25" cy="30" r="2" fill="#6b7280"/>
          <circle cx="45" cy="25" r="2" fill="#6b7280"/>
          <circle cx="35" cy="45" r="2" fill="#6b7280"/>
          <circle cx="65" cy="35" r="2" fill="#6b7280"/>
          <circle cx="55" cy="55" r="2" fill="#6b7280"/>
          <circle cx="75" cy="25" r="2" fill="#6b7280"/>
          <circle cx="20" cy="60" r="2" fill="#6b7280"/>
          <circle cx="40" cy="70" r="2" fill="#6b7280"/>
          <circle cx="70" cy="65" r="2" fill="#6b7280"/>
          <circle cx="80" cy="45" r="2" fill="#6b7280"/>
          <circle cx="30" cy="75" r="2" fill="#6b7280"/>
          <circle cx="60" cy="15" r="2" fill="#6b7280"/>
          <circle cx="15" cy="40" r="2" fill="#6b7280"/>
          <circle cx="85" cy="60" r="2" fill="#6b7280"/>
          <circle cx="50" cy="35" r="2" fill="#6b7280"/>
        </g>
        
        <g v-else-if="datasetType === 'spiral'">
          <!-- Spiral dataset visualization -->
          <path 
            d="M 50 50 Q 55 45, 60 50 Q 65 60, 55 65 Q 40 70, 35 60 Q 30 40, 45 35 Q 70 30, 75 45" 
            stroke="#3b82f6" 
            stroke-width="4" 
            fill="none" 
            opacity="0.8"
          />
          <path 
            d="M 50 50 Q 45 55, 40 50 Q 35 40, 45 35 Q 60 30, 65 40 Q 70 60, 55 65 Q 25 70, 20 55" 
            stroke="#ef4444" 
            stroke-width="4" 
            fill="none" 
            opacity="0.8"
          />
        </g>
        
        <g v-else-if="datasetType === 'nested'">
          <!-- Nested circles dataset visualization -->
          <circle cx="50" cy="50" r="35" stroke="#3b82f6" stroke-width="4" fill="none" opacity="0.6"/>
          <circle cx="50" cy="50" r="25" stroke="#ef4444" stroke-width="4" fill="none" opacity="0.6"/>
          <circle cx="50" cy="50" r="15" stroke="#10b981" stroke-width="4" fill="none" opacity="0.6"/>
          <circle cx="50" cy="50" r="8" stroke="#f59e0b" stroke-width="4" fill="none" opacity="0.6"/>
        </g>
        
        <g v-else-if="datasetType === 'elongated'">
          <!-- Elongated clusters dataset visualization -->
          <ellipse cx="30" cy="30" rx="20" ry="6" fill="#3b82f6" opacity="0.5" transform="rotate(45 30 30)"/>
          <ellipse cx="70" cy="30" rx="18" ry="5" fill="#ef4444" opacity="0.5" transform="rotate(-45 70 30)"/>
          <ellipse cx="50" cy="70" rx="22" ry="7" fill="#10b981" opacity="0.5" transform="rotate(0 50 70)"/>
        </g>
        
        <g v-else-if="datasetType === 'dense_sparse'">
          <!-- Dense sparse dataset visualization -->
          <!-- Dense cluster -->
          <circle cx="25" cy="25" r="8" fill="#3b82f6" opacity="0.7"/>
          <circle cx="20" cy="30" r="2" fill="#3b82f6"/>
          <circle cx="30" cy="20" r="2" fill="#3b82f6"/>
          <circle cx="25" cy="35" r="2" fill="#3b82f6"/>
          <circle cx="35" cy="25" r="2" fill="#3b82f6"/>
          <circle cx="22" cy="22" r="2" fill="#3b82f6"/>
          <circle cx="28" cy="28" r="2" fill="#3b82f6"/>
          
          <!-- Sparse clusters -->
          <circle cx="75" cy="25" r="3" fill="#ef4444"/>
          <circle cx="70" cy="75" r="3" fill="#10b981"/>
          <circle cx="80" cy="60" r="3" fill="#f59e0b"/>
        </g>
        
        <g v-else-if="datasetType === 'manifold'">
          <!-- Manifold dataset visualization -->
          <path 
            d="M 15 20 Q 30 15, 45 25 Q 60 35, 75 30 Q 85 25, 90 35" 
            stroke="#3b82f6" 
            stroke-width="3" 
            fill="none" 
            opacity="0.8"
          />
          <path 
            d="M 10 40 Q 25 35, 40 45 Q 55 55, 70 50 Q 80 45, 85 55" 
            stroke="#ef4444" 
            stroke-width="3" 
            fill="none" 
            opacity="0.8"
          />
          <path 
            d="M 20 60 Q 35 55, 50 65 Q 65 75, 80 70 Q 90 65, 95 75" 
            stroke="#10b981" 
            stroke-width="3" 
            fill="none" 
            opacity="0.8"
          />
          <!-- Add some dots -->
          <circle cx="20" cy="22" r="2" fill="#3b82f6"/>
          <circle cx="40" cy="27" r="2" fill="#3b82f6"/>
          <circle cx="60" cy="32" r="2" fill="#3b82f6"/>
          <circle cx="15" cy="42" r="2" fill="#ef4444"/>
          <circle cx="35" cy="47" r="2" fill="#ef4444"/>
          <circle cx="55" cy="52" r="2" fill="#ef4444"/>
          <circle cx="25" cy="62" r="2" fill="#10b981"/>
          <circle cx="45" cy="67" r="2" fill="#10b981"/>
          <circle cx="65" cy="72" r="2" fill="#10b981"/>
        </g>
        
        <!-- NEW DATASET PREVIEWS -->
        
        <g v-else-if="datasetType === 's_curve'">
          <!-- S-Curve dataset visualization -->
          <path 
            d="M 20 20 Q 35 15, 50 25 Q 65 35, 80 30 Q 90 25, 95 35 Q 90 45, 80 50 Q 65 55, 50 60 Q 35 65, 20 70" 
            stroke="#3b82f6" 
            stroke-width="4" 
            fill="none" 
            opacity="0.8"
          />
          <circle cx="25" cy="22" r="2" fill="#3b82f6"/>
          <circle cx="40" cy="20" r="2" fill="#ef4444"/>
          <circle cx="55" cy="28" r="2" fill="#10b981"/>
          <circle cx="70" cy="32" r="2" fill="#f59e0b"/>
          <circle cx="85" cy="35" r="2" fill="#8b5cf6"/>
          <circle cx="85" cy="45" r="2" fill="#06b6d4"/>
          <circle cx="70" cy="48" r="2" fill="#f97316"/>
          <circle cx="55" cy="55" r="2" fill="#84cc16"/>
          <circle cx="40" cy="62" r="2" fill="#ec4899"/>
          <circle cx="25" cy="68" r="2" fill="#6b7280"/>
        </g>
        
        <!-- HIGH-DIMENSIONAL DATASET PREVIEWS -->
        
        <g v-else-if="datasetType === 'blobs_nd'">
          <!-- High-D Blobs visualization -->
          <rect x="20" y="20" width="15" height="15" fill="#3b82f6" opacity="0.6" rx="2"/>
          <rect x="65" y="20" width="15" height="15" fill="#ef4444" opacity="0.6" rx="2"/>
          <rect x="20" y="65" width="15" height="15" fill="#10b981" opacity="0.6" rx="2"/>
          <rect x="65" y="65" width="15" height="15" fill="#f59e0b" opacity="0.6" rx="2"/>
          <rect x="42" y="42" width="15" height="15" fill="#8b5cf6" opacity="0.6" rx="2"/>
          
          <!-- High-D indicators -->
          <text x="50" y="15" text-anchor="middle" font-size="8" fill="#6b7280">Multi-D</text>
          <circle cx="27" cy="27" r="1.5" fill="#3b82f6"/>
          <circle cx="72" cy="27" r="1.5" fill="#ef4444"/>
          <circle cx="27" cy="72" r="1.5" fill="#10b981"/>
          <circle cx="72" cy="72" r="1.5" fill="#f59e0b"/>
          <circle cx="49" cy="49" r="1.5" fill="#8b5cf6"/>
        </g>
        
        <g v-else-if="datasetType === 'classification_nd'">
          <!-- High-D Classification visualization -->
          <rect x="15" y="15" width="25" height="25" fill="#3b82f6" opacity="0.3" rx="3"/>
          <rect x="60" y="15" width="25" height="25" fill="#ef4444" opacity="0.3" rx="3"/>
          <rect x="15" y="60" width="25" height="25" fill="#10b981" opacity="0.3" rx="3"/>
          <rect x="60" y="60" width="25" height="25" fill="#f59e0b" opacity="0.3" rx="3"/>
          
          <!-- Noise indicators -->
          <circle cx="45" cy="30" r="1" fill="#6b7280" opacity="0.5"/>
          <circle cx="30" cy="45" r="1" fill="#6b7280" opacity="0.5"/>
          <circle cx="70" cy="45" r="1" fill="#6b7280" opacity="0.5"/>
          <circle cx="45" cy="70" r="1" fill="#6b7280" opacity="0.5"/>
          <circle cx="50" cy="50" r="1" fill="#6b7280" opacity="0.5"/>
          
          <text x="50" y="10" text-anchor="middle" font-size="7" fill="#6b7280">High-D + Noise</text>
        </g>
        
        <g v-else-if="datasetType === 'sparse_clusters'">
          <!-- Sparse Clusters visualization -->
          <rect x="10" y="10" width="20" height="5" fill="#3b82f6" opacity="0.6" rx="2"/>
          <rect x="70" y="25" width="5" height="20" fill="#ef4444" opacity="0.6" rx="2"/>
          <rect x="25" y="70" width="15" height="8" fill="#10b981" opacity="0.6" rx="2"/>
          <rect x="60" y="60" width="8" height="15" fill="#f59e0b" opacity="0.6" rx="2"/>
          
          <!-- Sparse dots -->
          <circle cx="45" cy="20" r="1" fill="#6b7280" opacity="0.3"/>
          <circle cx="55" cy="40" r="1" fill="#6b7280" opacity="0.3"/>
          <circle cx="35" cy="50" r="1" fill="#6b7280" opacity="0.3"/>
          <circle cx="85" cy="80" r="1" fill="#6b7280" opacity="0.3"/>
          
          <text x="50" y="95" text-anchor="middle" font-size="7" fill="#6b7280">Sparse Features</text>
        </g>
        
        <g v-else-if="datasetType === 'hypercube'">
          <!-- Hypercube visualization -->
          <rect x="25" y="25" width="15" height="15" fill="#3b82f6" opacity="0.7" rx="2"/>
          <rect x="60" y="25" width="15" height="15" fill="#ef4444" opacity="0.7" rx="2"/>
          <rect x="25" y="60" width="15" height="15" fill="#10b981" opacity="0.7" rx="2"/>
          <rect x="60" y="60" width="15" height="15" fill="#f59e0b" opacity="0.7" rx="2"/>
          
          <!-- Cube edges -->
          <line x1="40" y1="25" x2="60" y2="25" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          <line x1="40" y1="40" x2="60" y2="40" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          <line x1="40" y1="60" x2="60" y2="60" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          <line x1="40" y1="75" x2="60" y2="75" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          <line x1="25" y1="40" x2="25" y2="60" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          <line x1="40" y1="40" x2="40" y2="60" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          <line x1="60" y1="40" x2="60" y2="60" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          <line x1="75" y1="40" x2="75" y2="60" stroke="#6b7280" stroke-width="1" opacity="0.5"/>
          
          <text x="50" y="15" text-anchor="middle" font-size="7" fill="#6b7280">Hypercube</text>
        </g>
        
        <g v-else-if="datasetType === 'swiss_roll_3d'">
          <!-- Swiss Roll 3D visualization -->
          <path 
            d="M 20 30 Q 30 20, 50 25 Q 70 30, 80 40 Q 85 55, 75 70 Q 60 80, 40 75 Q 20 70, 15 55 Q 10 40, 20 30" 
            stroke="#3b82f6" 
            stroke-width="3" 
            fill="none" 
            opacity="0.6"
          />
          <path 
            d="M 30 35 Q 40 30, 55 32 Q 70 35, 75 45 Q 78 58, 70 68 Q 58 75, 45 72 Q 32 68, 28 58 Q 25 45, 30 35" 
            stroke="#ef4444" 
            stroke-width="3" 
            fill="none" 
            opacity="0.6"
          />
          <path 
            d="M 40 40 Q 45 37, 55 38 Q 65 40, 68 48 Q 70 58, 65 65 Q 58 68, 50 67 Q 42 65, 40 58 Q 38 48, 40 40" 
            stroke="#10b981" 
            stroke-width="3" 
            fill="none" 
            opacity="0.6"
          />
          
          <text x="50" y="15" text-anchor="middle" font-size="7" fill="#6b7280">3D Manifold</text>
        </g>
        
        <!-- REAL-WORLD DATASET PREVIEWS -->
        
        <g v-else-if="datasetType === 'iris'">
          <!-- Iris dataset visualization - Improved flower representation -->
          <g>
            <!-- Setosa cluster (compact) -->
            <g transform="translate(25, 25)">
              <circle cx="0" cy="0" r="12" fill="#3b82f6" opacity="0.2"/>
              <ellipse cx="-6" cy="-3" rx="4" ry="2" fill="#3b82f6" opacity="0.8" transform="rotate(45)"/>
              <ellipse cx="6" cy="-3" rx="4" ry="2" fill="#3b82f6" opacity="0.8" transform="rotate(-45)"/>
              <ellipse cx="-6" cy="3" rx="4" ry="2" fill="#3b82f6" opacity="0.8" transform="rotate(-45)"/>
              <ellipse cx="6" cy="3" rx="4" ry="2" fill="#3b82f6" opacity="0.8" transform="rotate(45)"/>
              <circle cx="0" cy="0" r="2" fill="#1e40af"/>
              <text x="0" y="20" text-anchor="middle" font-size="6" fill="#1e40af">Setosa</text>
            </g>
            
            <!-- Versicolor cluster (medium) -->
            <g transform="translate(75, 25)">
              <circle cx="0" cy="0" r="14" fill="#ef4444" opacity="0.2"/>
              <ellipse cx="-7" cy="-4" rx="5" ry="2.5" fill="#ef4444" opacity="0.8" transform="rotate(30)"/>
              <ellipse cx="7" cy="-4" rx="5" ry="2.5" fill="#ef4444" opacity="0.8" transform="rotate(-30)"/>
              <ellipse cx="-7" cy="4" rx="5" ry="2.5" fill="#ef4444" opacity="0.8" transform="rotate(-30)"/>
              <ellipse cx="7" cy="4" rx="5" ry="2.5" fill="#ef4444" opacity="0.8" transform="rotate(30)"/>
              <circle cx="0" cy="0" r="2" fill="#dc2626"/>
              <text x="0" y="20" text-anchor="middle" font-size="6" fill="#dc2626">Versicolor</text>
            </g>
            
            <!-- Virginica cluster (large) -->
            <g transform="translate(50, 70)">
              <circle cx="0" cy="0" r="16" fill="#10b981" opacity="0.2"/>
              <ellipse cx="-8" cy="-5" rx="6" ry="3" fill="#10b981" opacity="0.8" transform="rotate(0)"/>
              <ellipse cx="8" cy="-5" rx="6" ry="3" fill="#10b981" opacity="0.8" transform="rotate(0)"/>
              <ellipse cx="-8" cy="5" rx="6" ry="3" fill="#10b981" opacity="0.8" transform="rotate(0)"/>
              <ellipse cx="8" cy="5" rx="6" ry="3" fill="#10b981" opacity="0.8" transform="rotate(0)"/>
              <circle cx="0" cy="0" r="2" fill="#059669"/>
              <text x="0" y="20" text-anchor="middle" font-size="6" fill="#059669">Virginica</text>
            </g>
          </g>
          <text x="50" y="10" text-anchor="middle" font-size="6" fill="#6b7280" font-weight="bold">🌸 Iris</text>
        </g>
        
        <g v-else-if="datasetType === 'wine'">
          <!-- Wine dataset visualization - Enhanced wine bottles and grapes -->
          <g>
            <!-- Wine bottles with different wine types -->
            <!-- Red wine bottle -->
            <g transform="translate(20, 15)">
              <rect x="0" y="10" width="12" height="25" rx="1" fill="#1f2937" opacity="0.9"/>
              <rect x="1" y="12" width="10" height="20" rx="1" fill="#722f37" opacity="0.8"/>
              <rect x="4" y="0" width="4" height="12" fill="#1f2937"/>
              <ellipse cx="6" cy="0" rx="3" ry="2" fill="#6b7280"/>
              <text x="6" y="45" text-anchor="middle" font-size="5" fill="#dc2626" font-weight="bold">Red</text>
            </g>
            
            <!-- White wine bottle -->
            <g transform="translate(44, 15)">
              <rect x="0" y="10" width="12" height="25" rx="1" fill="#1f2937" opacity="0.9"/>
              <rect x="1" y="12" width="10" height="20" rx="1" fill="#fef3c7" opacity="0.9"/>
              <rect x="4" y="0" width="4" height="12" fill="#1f2937"/>
              <ellipse cx="6" cy="0" rx="3" ry="2" fill="#6b7280"/>
              <text x="6" y="45" text-anchor="middle" font-size="5" fill="#f59e0b" font-weight="bold">White</text>
            </g>
            
            <!-- Rosé wine bottle -->
            <g transform="translate(68, 15)">
              <rect x="0" y="10" width="12" height="25" rx="1" fill="#1f2937" opacity="0.9"/>
              <rect x="1" y="12" width="10" height="20" rx="1" fill="#fecaca" opacity="0.8"/>
              <rect x="4" y="0" width="4" height="12" fill="#1f2937"/>
              <ellipse cx="6" cy="0" rx="3" ry="2" fill="#6b7280"/>
              <text x="6" y="45" text-anchor="middle" font-size="5" fill="#ef4444" font-weight="bold">Rosé</text>
            </g>
            
            <!-- Grape clusters -->
            <g transform="translate(25, 55)">
              <circle cx="0" cy="0" r="2" fill="#7c3aed"/>
              <circle cx="3" cy="1" r="2" fill="#7c3aed"/>
              <circle cx="-3" cy="1" r="2" fill="#7c3aed"/>
              <circle cx="1" cy="4" r="2" fill="#7c3aed"/>
              <circle cx="-1" cy="4" r="2" fill="#7c3aed"/>
              <path d="M 0 -2 Q 2 -8, 6 -6 Q 8 -4, 6 -2" stroke="#16a34a" stroke-width="1" fill="#22c55e" opacity="0.7"/>
            </g>
            
            <g transform="translate(75, 55)">
              <circle cx="0" cy="0" r="2" fill="#eab308"/>
              <circle cx="3" cy="1" r="2" fill="#eab308"/>
              <circle cx="-3" cy="1" r="2" fill="#eab308"/>
              <circle cx="1" cy="4" r="2" fill="#eab308"/>
              <circle cx="-1" cy="4" r="2" fill="#eab308"/>
              <path d="M 0 -2 Q 2 -8, 6 -6 Q 8 -4, 6 -2" stroke="#16a34a" stroke-width="1" fill="#22c55e" opacity="0.7"/>
            </g>
          </g>
          <text x="50" y="80" text-anchor="middle" font-size="6" fill="#6b7280" font-weight="bold">🍷 Wine</text>
        </g>
        
        <g v-else-if="datasetType === 'breast_cancer'">
          <!-- Breast Cancer dataset visualization - Enhanced medical cells -->
          <g>
            <!-- Healthy cell structure -->
            <g transform="translate(25, 30)">
              <circle cx="0" cy="0" r="14" fill="#10b981" opacity="0.2" stroke="#10b981" stroke-width="2"/>
              <circle cx="0" cy="0" r="8" fill="#10b981" opacity="0.4"/>
              <circle cx="0" cy="0" r="4" fill="#059669"/>
              <!-- Organized cell structure -->
              <circle cx="-6" cy="-3" r="1.5" fill="#10b981" opacity="0.8"/>
              <circle cx="6" cy="-3" r="1.5" fill="#10b981" opacity="0.8"/>
              <circle cx="-6" cy="3" r="1.5" fill="#10b981" opacity="0.8"/>
              <circle cx="6" cy="3" r="1.5" fill="#10b981" opacity="0.8"/>
              <text x="0" y="22" text-anchor="middle" font-size="6" fill="#059669" font-weight="bold">Benign</text>
            </g>
            
            <!-- Malignant cell structure -->
            <g transform="translate(75, 30)">
              <circle cx="0" cy="0" r="14" fill="#ef4444" opacity="0.2" stroke="#ef4444" stroke-width="2"/>
              <circle cx="0" cy="0" r="8" fill="#ef4444" opacity="0.4"/>
              <circle cx="0" cy="0" r="4" fill="#dc2626"/>
              <!-- Irregular cell structure -->
              <ellipse cx="-8" cy="-4" rx="2" ry="1" fill="#ef4444" opacity="0.9" transform="rotate(30)"/>
              <ellipse cx="8" cy="-2" rx="1.5" ry="2" fill="#ef4444" opacity="0.9" transform="rotate(-45)"/>
              <ellipse cx="-4" cy="8" rx="2" ry="1.5" fill="#ef4444" opacity="0.9" transform="rotate(60)"/>
              <ellipse cx="6" cy="6" rx="1" ry="2" fill="#ef4444" opacity="0.9" transform="rotate(-30)"/>
              <circle cx="-10" cy="-8" r="1" fill="#ef4444" opacity="0.7"/>
              <circle cx="10" cy="8" r="1" fill="#ef4444" opacity="0.7"/>
              <text x="0" y="22" text-anchor="middle" font-size="6" fill="#dc2626" font-weight="bold">Malignant</text>
            </g>
            
            <!-- Medical stethoscope -->
            <g transform="translate(45, 65)">
              <circle cx="0" cy="0" r="4" fill="none" stroke="#6b7280" stroke-width="2"/>
              <circle cx="0" cy="0" r="2" fill="#6b7280"/>
              <path d="M 4 0 Q 8 -4, 12 0" stroke="#6b7280" stroke-width="2" fill="none"/>
              <circle cx="12" cy="0" r="1.5" fill="#6b7280"/>
            </g>
          </g>
          <text x="50" y="12" text-anchor="middle" font-size="6" fill="#6b7280" font-weight="bold">🏥 Medical</text>
        </g>
        
        <g v-else-if="datasetType === 'digits_small'">
          <!-- Digits dataset visualization - Enhanced pixel representations -->
          <g>
            <!-- Digit "1" with pixel grid -->
            <g transform="translate(15, 20)">
              <rect x="0" y="0" width="16" height="20" fill="#f1f5f9" stroke="#e2e8f0" stroke-width="0.5" rx="2"/>
              <!-- Pixel representation of "1" -->
              <rect x="6" y="2" width="2" height="2" fill="#3b82f6"/>
              <rect x="4" y="4" width="2" height="2" fill="#3b82f6"/>
              <rect x="6" y="4" width="2" height="2" fill="#3b82f6"/>
              <rect x="6" y="6" width="2" height="2" fill="#3b82f6"/>
              <rect x="6" y="8" width="2" height="2" fill="#3b82f6"/>
              <rect x="6" y="10" width="2" height="2" fill="#3b82f6"/>
              <rect x="6" y="12" width="2" height="2" fill="#3b82f6"/>
              <rect x="6" y="14" width="2" height="2" fill="#3b82f6"/>
              <rect x="2" y="16" width="12" height="2" fill="#3b82f6"/>
              <text x="8" y="26" text-anchor="middle" font-size="5" fill="#1e40af" font-weight="bold">1</text>
            </g>
            
            <!-- Digit "5" with pixel grid -->
            <g transform="translate(42, 20)">
              <rect x="0" y="0" width="16" height="20" fill="#f1f5f9" stroke="#e2e8f0" stroke-width="0.5" rx="2"/>
              <!-- Pixel representation of "5" -->
              <rect x="2" y="2" width="12" height="2" fill="#ef4444"/>
              <rect x="2" y="4" width="2" height="2" fill="#ef4444"/>
              <rect x="2" y="6" width="2" height="2" fill="#ef4444"/>
              <rect x="2" y="8" width="10" height="2" fill="#ef4444"/>
              <rect x="12" y="10" width="2" height="2" fill="#ef4444"/>
              <rect x="12" y="12" width="2" height="2" fill="#ef4444"/>
              <rect x="12" y="14" width="2" height="2" fill="#ef4444"/>
              <rect x="2" y="16" width="12" height="2" fill="#ef4444"/>
              <text x="8" y="26" text-anchor="middle" font-size="5" fill="#dc2626" font-weight="bold">5</text>
            </g>
            
            <!-- Digit "0" with pixel grid -->
            <g transform="translate(69, 20)">
              <rect x="0" y="0" width="16" height="20" fill="#f1f5f9" stroke="#e2e8f0" stroke-width="0.5" rx="2"/>
              <!-- Pixel representation of "0" -->
              <rect x="4" y="2" width="8" height="2" fill="#10b981"/>
              <rect x="2" y="4" width="2" height="2" fill="#10b981"/>
              <rect x="12" y="4" width="2" height="2" fill="#10b981"/>
              <rect x="2" y="6" width="2" height="2" fill="#10b981"/>
              <rect x="12" y="6" width="2" height="2" fill="#10b981"/>
              <rect x="2" y="8" width="2" height="2" fill="#10b981"/>
              <rect x="12" y="8" width="2" height="2" fill="#10b981"/>
              <rect x="2" y="10" width="2" height="2" fill="#10b981"/>
              <rect x="12" y="10" width="2" height="2" fill="#10b981"/>
              <rect x="2" y="12" width="2" height="2" fill="#10b981"/>
              <rect x="12" y="12" width="2" height="2" fill="#10b981"/>
              <rect x="2" y="14" width="2" height="2" fill="#10b981"/>
              <rect x="12" y="14" width="2" height="2" fill="#10b981"/>
              <rect x="4" y="16" width="8" height="2" fill="#10b981"/>
              <text x="8" y="26" text-anchor="middle" font-size="5" fill="#059669" font-weight="bold">0</text>
            </g>
          </g>
          <text x="50" y="52" text-anchor="middle" font-size="6" fill="#6b7280" font-weight="bold">🔢 Digits</text>
        </g>
        
        <!-- DEFAULT FALLBACK -->
        <g v-else>
          <!-- Generic dataset visualization -->
          <circle cx="30" cy="30" r="8" fill="#6b7280" opacity="0.5"/>
          <circle cx="70" cy="30" r="8" fill="#6b7280" opacity="0.5"/>
          <circle cx="50" cy="70" r="8" fill="#6b7280" opacity="0.5"/>
          <circle cx="30" cy="30" r="3" fill="#6b7280"/>
          <circle cx="70" cy="30" r="3" fill="#6b7280"/>
          <circle cx="50" cy="70" r="3" fill="#6b7280"/>
          <text x="50" y="15" text-anchor="middle" font-size="8" fill="#6b7280">Dataset</text>
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  datasetType: string
  size?: number
}

const props = withDefaults(defineProps<Props>(), {
  size: 100
})
</script>

<style scoped>
.dataset-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}

.preview-container {
  border-radius: 8px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  padding: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  width: 100%;
  height: 100%;
  min-height: 80px;
  max-height: 100px;
  overflow: hidden;
}

.preview-container:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.preview-svg {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 70px;
  max-height: 70px;
}

/* Enhanced visual effects for different dataset types */
.sample-card.high-d .preview-container {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border-color: #f59e0b;
}

.sample-card.real-world .preview-container {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  border-color: #10b981;
}

.sample-card:hover .preview-container {
  transform: scale(1.05);
}

.sample-card.active .preview-container {
  border-color: #3b82f6;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  box-shadow: 0 8px 16px rgba(59, 130, 246, 0.2);
}
</style>